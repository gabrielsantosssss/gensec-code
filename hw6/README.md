# HW6 – Security Docs RAG (Flask + ChromaDB + Gemini)

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then set GOOGLE_API_KEY (and RAG_MODEL if needed)
```

## Ingest documents
Put `.md` / `.txt` files (OWASP cheat sheets, NIST excerpts, CVE summaries…) in `docs/`, then:
```bash
python ingest.py --reset     # --reset rebuilds the index from scratch
```
Embeddings are computed locally (Chroma's default all-MiniLM-L6-v2 model) and stored in `chroma_db/`.

## Run
```bash
python app.py                # http://127.0.0.1:5000, debug off
```

## Files
| File | Purpose |
|---|---|
| `ingest.py` | Chunks files in `docs/` and upserts them into Chroma |
| `rag.py` | Input sanitizing, retrieval, prompt building, Gemini call |
| `app.py` | Flask routes, CSRF, rate limit, security headers |
| `templates/index.html`, `static/` | Search UI |

## Security measures
- **Input:** queries are type-checked, Unicode-normalized, stripped of control/invisible characters, and capped at 500 chars; request bodies capped at 4 KB.
- **Prompt injection:** retrieved text and the question are wrapped in delimiters (with `<`/`>` escaped so they can't break out), and the system prompt tells the model to treat them as data.
- **XSS:** the frontend renders all answer/source text with `textContent`; a strict CSP blocks inline scripts.
- **Secrets:** the API key is read from `.env` on the server only; it never reaches the browser, and error responses are generic (details go to server logs). `.env` is git-ignored.
- **Request forgery / abuse:** per-session CSRF token on the API, `SameSite=Strict` cookies, JSON-only endpoint, 10 requests/min per IP.
- **Server:** `debug=False` unless `FLASK_DEBUG=true`; binds to `127.0.0.1` by default.
- **Ingest:** only `.md`/`.txt` files under `docs/` (symlinks escaping it are skipped), 5 MB max per file.
