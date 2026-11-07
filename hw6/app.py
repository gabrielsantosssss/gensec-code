"""Flask front end for the security-docs RAG pipeline.

Run:  python app.py      (debug is OFF unless FLASK_DEBUG=true)
"""

import logging
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, render_template, request, session

load_dotenv()

import rag  # noqa: E402  (import after .env is loaded)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=4 * 1024,  # requests are tiny JSON bodies
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    JSON_SORT_KEYS=False,
)
log = logging.getLogger("rag-app")
logging.basicConfig(level=logging.INFO)

# --- Simple in-memory rate limit: N requests per window per client IP ---------------
RATE_LIMIT, RATE_WINDOW = 10, 60
_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = threading.Lock()


def rate_limited(ip: str) -> bool:
    now = time.monotonic()
    with _hits_lock:
        q = _hits[ip]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return True
        q.append(now)
        return False


# --- Security headers -----------------------------------------------------------------
@app.after_request
def set_security_headers(resp):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
        "form-action 'self'"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.get("/")
def index():
    return render_template("index.html", csrf_token=csrf_token(), max_chars=rag.MAX_QUERY_CHARS)


@app.post("/api/ask")
def ask():
    if not request.is_json:
        abort(415)
    sent = request.headers.get("X-CSRF-Token", "")
    if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
        return jsonify(error="Invalid or missing CSRF token. Reload the page."), 403
    if rate_limited(request.remote_addr or "unknown"):
        return jsonify(error="Too many requests. Please wait a minute."), 429

    data = request.get_json(silent=True) or {}
    try:
        query = rag.sanitize_query(data.get("query"))
    except ValueError as e:
        return jsonify(error=str(e)), 400

    try:
        hits = rag.retrieve(query)
    except Exception:
        log.exception("retrieval failed")
        return jsonify(error="Search index unavailable. Has ingest.py been run?"), 500
    if not hits:
        return jsonify(answer="No documents are indexed yet. Run ingest.py first.", sources=[])

    try:
        answer = rag.generate_answer(query, hits)
    except Exception:
        # Log details server-side only; never echo exception text (could include keys/URLs).
        log.exception("generation failed")
        return jsonify(error="The language model request failed. Check the server logs."), 502

    sources = [
        {"n": i, "source": h["source"], "chunk": h["chunk"], "score": h["score"], "text": h["text"]}
        for i, h in enumerate(hits, 1)
    ]
    return jsonify(answer=answer, sources=sources)


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Request too large."), 413


@app.errorhandler(415)
def bad_type(_):
    return jsonify(error="Expected a JSON request."), 415


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=debug,
    )
