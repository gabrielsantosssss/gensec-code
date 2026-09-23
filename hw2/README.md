# HW2 - Custom LangChain RAG Application

A NotebookLM-style RAG app built on top of the Lab 02.3 example
(`02_LangChain/07_RAG`), extended with LangChain's built-in `JSONLoader` -
a pre-built loader not used anywhere in the lab code - so the app can also
index structured JSON knowledge files, not just txt/pdf/docx/md/csv.

## Setup

```bash
cd hw2
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env   # then fill in your own values
```

## Run

```bash
python app.py
```

The first run builds a local Chroma vector database at `rag_data/.chromadb`
from every file under `rag_data/` (txt, pdf, docx, md, csv, and json).
Subsequent runs reuse the existing database. Ask questions at the `llm>>`
prompt; press Enter on a blank line to quit.

## Custom functionality: JSON loader

`load_json()` in `app.py` uses
`langchain_community.document_loaders.JSONLoader` to load
`rag_data/json/tech_facts.json`, a small set of AI-security glossary
entries. `jq_schema=".[]"` iterates each object in the JSON array,
`content_key="content"` picks the field to embed, and a custom
`metadata_func` copies the `title` field into the chunk's metadata so it
shows up as a readable source in query results.
