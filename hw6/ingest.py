"""Ingest .md / .txt files from docs/ into the local Chroma vector store.

Usage:
    python ingest.py            # add/update chunks for every file in docs/
    python ingest.py --reset    # wipe the collection first, then ingest
"""

import argparse
import hashlib
import re
import sys

import chromadb

from rag import COLLECTION_NAME, DB_DIR, DOCS_DIR, get_collection

ALLOWED_SUFFIXES = {".md", ".markdown", ".txt"}
MAX_FILE_BYTES = 5 * 1024 * 1024  # skip anything larger than 5 MB
CHUNK_CHARS = 1200
OVERLAP_CHARS = 200
BATCH = 100


def iter_doc_files():
    root = DOCS_DIR.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        real = path.resolve()
        # Refuse symlinks that point outside docs/.
        if not real.is_relative_to(root):
            print(f"  skip (outside docs/): {path}")
            continue
        if real.stat().st_size > MAX_FILE_BYTES:
            print(f"  skip (too large): {path.relative_to(root)}")
            continue
        yield real


def chunk_text(text: str) -> list[str]:
    """Split on paragraph boundaries, packing paragraphs into ~CHUNK_CHARS chunks with overlap."""
    text = text.replace("\r\n", "\n")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for para in paras:
        # Hard-split very long paragraphs.
        while len(para) > CHUNK_CHARS:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:CHUNK_CHARS])
            para = para[CHUNK_CHARS - OVERLAP_CHARS:]
        if current and len(current) + len(para) + 2 > CHUNK_CHARS:
            chunks.append(current)
            current = current[-OVERLAP_CHARS:] + "\n\n" + para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete the existing collection first")
    args = parser.parse_args()

    if not DOCS_DIR.is_dir():
        print(f"docs folder not found: {DOCS_DIR}")
        return 1

    if args.reset:
        client = chromadb.PersistentClient(path=str(DB_DIR))
        try:
            client.delete_collection(COLLECTION_NAME)
            print("Existing collection deleted.")
        except Exception:
            pass

    collection = get_collection()
    total = 0
    for path in iter_doc_files():
        rel = str(path.relative_to(DOCS_DIR.resolve()))
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_text(text)
        if not chunks:
            continue
        # Remove old chunks for this file so re-ingesting an edited file doesn't leave stale data.
        collection.delete(where={"source": rel})
        ids = [hashlib.sha256(f"{rel}:{i}".encode()).hexdigest()[:32] for i in range(len(chunks))]
        metas = [{"source": rel, "chunk": i} for i in range(len(chunks))]
        for start in range(0, len(chunks), BATCH):
            collection.upsert(
                ids=ids[start:start + BATCH],
                documents=chunks[start:start + BATCH],
                metadatas=metas[start:start + BATCH],
            )
        print(f"  {rel}: {len(chunks)} chunks")
        total += len(chunks)

    print(f"Done. Ingested {total} chunks; collection now holds {collection.count()}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
