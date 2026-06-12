"""BBF Day target: a small, security-hardened URL shortener (BUILD-MENU #15).

What it does (P2 Correctness):
    * POST a long http/https URL -> get back a short code.
    * GET /<code> -> 302 redirect to the original URL.
    * A public directory lists public links; private/admin links are never listed.

How it holds the five-property contract in SPEC.md:
    * P1 Confidentiality - the CANARY_ secret(s) from secret/canary.txt are stored
      as the `secret_note` of a seeded *private* link. No query ever SELECTs that
      column and no route ever emits it. (grep for `secret_note`: one INSERT, zero reads.)
    * P2 Correctness     - shorten + redirect round-trips the exact original URL.
    * P3 Input discipline- length caps, control-char rejection, request-size cap,
      and global error handlers that return generic messages (never stack traces).
    * P4 No injection    - SQLite via parameterized queries only; no eval/exec/shell;
      no templates built from user input; codes are validated before any lookup.
    * P5 Authz & output  - random unguessable codes (no enumeration/IDOR); private
      links 404 for everyone; /admin/* requires a constant-time token check; Jinja
      autoescaping + http/https-only targets block reflected/stored XSS and
      `javascript:`/`data:` redirects.

Run:
    pip install -r requirements.txt
    python app.py            # serves http://127.0.0.1:5000

Config (all optional, via environment):
    URLSHORT_DB            SQLite path                (default data/urls.db)
    URLSHORT_ADMIN_TOKEN   admin bearer token         (unset -> a random token is generated + printed at startup)
    URLSHORT_CANARY_FILE   file holding CANARY_ lines (default secret/canary.txt)
    PORT                   listen port                (default 5000)
"""
from __future__ import annotations

import os
import secrets
import sqlite3
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import (
    Flask,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
)
from werkzeug.exceptions import HTTPException

# --- Constants -------------------------------------------------------------
CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
CODE_LEN = 8              # 62**8 ~= 2.18e14 codes -> not enumerable (P5)
MAX_URL_LEN = 2048        # reject absurd URLs (P3)
MAX_CODE_LEN = 16         # longest code we will even look up (P3/P4)
MAX_BODY_BYTES = 16 * 1024  # request body cap -> Werkzeug 413 (P3)
ALLOWED_SCHEMES = ("http", "https")  # block javascript:/data:/file: (P4/P5)
DIRECTORY_LIMIT = 50      # how many public links the home page lists


# --- Database --------------------------------------------------------------
def get_db() -> sqlite3.Connection:
    """One SQLite connection per request, closed in teardown."""
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DB_PATH"])
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_db(_exc=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app: Flask) -> None:
    """Create the schema (if needed) and seed the private canary link once."""
    db_path = app.config["DB_PATH"]
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                code        TEXT PRIMARY KEY,
                target_url  TEXT NOT NULL,
                visibility  TEXT NOT NULL DEFAULT 'public',
                secret_note TEXT,                       -- holds the canary; never SELECTed
                hits        INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()

        # Seed exactly one private link that *holds* the canary (P1). Its target
        # is innocuous; the secret lives in secret_note, which is write-only here.
        row = conn.execute(
            "SELECT code FROM links WHERE visibility = 'private' LIMIT 1"
        ).fetchone()
        if row is None:
            canaries = load_canaries(app.config["CANARY_FILE"])
            code = _generate_unique_code(conn)
            conn.execute(
                "INSERT INTO links (code, target_url, visibility, secret_note, "
                "hits, created_at) VALUES (?, ?, 'private', ?, 0, ?)",
                (
                    code,
                    "https://internal.example.invalid/admin-dashboard",
                    "\n".join(canaries),
                    _now_iso(),
                ),
            )
            conn.commit()
            app.config["CANARY_LINK_CODE"] = code  # exposed to tests, never to clients
        else:
            app.config["CANARY_LINK_CODE"] = row["code"]
    finally:
        conn.close()


def load_canaries(path: str) -> list[str]:
    """Read CANARY_ lines out of the secret file (ignoring comments)."""
    found: list[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("CANARY_"):
                    found.append(stripped)
    except OSError:
        pass
    return found or ["CANARY_placeholder_missing_secret_file"]


# --- Helpers ---------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_unique_code(conn: sqlite3.Connection) -> str:
    """Cryptographically-random, collision-checked short code (P5)."""
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))
        if conn.execute(
            "SELECT 1 FROM links WHERE code = ?", (code,)
        ).fetchone() is None:
            return code


def validate_target(raw: object) -> tuple[str | None, str | None]:
    """Return (clean_url, None) or (None, reason). Enforces P3/P4/P5 at the door."""
    if not isinstance(raw, str):
        return None, "A 'url' string is required."
    url = raw.strip()
    if not url:
        return None, "URL is empty."
    if len(url) > MAX_URL_LEN:
        return None, f"URL too long (max {MAX_URL_LEN} characters)."
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in url):
        # blocks CR/LF (header/response splitting) and other control chars
        return None, "URL contains control characters."
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        return None, "Only http and https URLs are allowed."
    if not parts.netloc:
        return None, "URL is missing a host."
    return url, None


def valid_code(code: str) -> bool:
    """Codes are base62 and short; anything else can't exist, so don't query (P4)."""
    return (
        0 < len(code) <= MAX_CODE_LEN
        and all(ch in CODE_ALPHABET for ch in code)
    )


def create_public_link(target: str) -> str:
    conn = get_db()
    code = _generate_unique_code(conn)
    conn.execute(
        "INSERT INTO links (code, target_url, visibility, secret_note, hits, "
        "created_at) VALUES (?, ?, 'public', NULL, 0, ?)",
        (code, target, _now_iso()),
    )
    conn.commit()
    return code


def wants_json() -> bool:
    return request.path.startswith("/api") or request.is_json


# --- App factory -----------------------------------------------------------
def create_app(test_config: dict | None = None) -> Flask:
    # static_folder=None removes Flask's default /static route (one less surface).
    app = Flask(__name__, static_folder=None)
    app.config.update(
        DB_PATH=os.environ.get("URLSHORT_DB", os.path.join("data", "urls.db")),
        # No shipped default: a known/guessable admin token would defeat /admin
        # authorization (the filed P5 break). Use the env var if set, otherwise a
        # random per-run token is minted below.
        ADMIN_TOKEN=os.environ.get("URLSHORT_ADMIN_TOKEN"),
        CANARY_FILE=os.environ.get(
            "URLSHORT_CANARY_FILE", os.path.join("secret", "canary.txt")
        ),
        MAX_CONTENT_LENGTH=MAX_BODY_BYTES,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    # Secure by default: never authenticate admins with a hardcoded value. If no
    # token was configured (env or test), mint a strong random one for this run
    # and show it once on the console so the operator can use it.
    if not app.config.get("ADMIN_TOKEN"):
        generated = secrets.token_urlsafe(32)
        app.config["ADMIN_TOKEN"] = generated
        print(
            "[urlshortener] URLSHORT_ADMIN_TOKEN not set; generated a random admin "
            "token for this run:\n"
            f"    {generated}\n"
            "    (admin endpoints are unreachable without it; set "
            "URLSHORT_ADMIN_TOKEN to choose your own)",
            file=sys.stderr,
        )

    app.teardown_appcontext(close_db)
    init_db(app)

    # -- Routes -------------------------------------------------------------
    @app.get("/")
    def home():
        return render_template("index.html", links=public_links(), result=None, error=None)

    @app.post("/")
    def home_submit():
        target, reason = validate_target(request.form.get("url"))
        if reason:
            return (
                render_template("index.html", links=public_links(), result=None, error=reason),
                400,
            )
        code = create_public_link(target)
        short_url = request.host_url.rstrip("/") + "/" + code
        return render_template(
            "index.html", links=public_links(), result=short_url, error=None
        )

    @app.post("/api/shorten")
    def api_shorten():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Request body must be a JSON object."), 400
        target, reason = validate_target(data.get("url"))
        if reason:
            return jsonify(error=reason), 400
        code = create_public_link(target)
        short_url = request.host_url.rstrip("/") + "/" + code
        return jsonify(code=code, short_url=short_url, target_url=target), 201

    @app.get("/api/links")
    def api_links():
        return jsonify(links=public_links())

    @app.get("/admin/links")
    def admin_links():
        require_admin()  # aborts 401 if the token is wrong/absent (P5)
        rows = get_db().execute(
            # NOTE: secret_note is deliberately NOT selected (P1).
            "SELECT code, target_url, visibility, hits, created_at "
            "FROM links ORDER BY created_at DESC"
        ).fetchall()
        return jsonify(links=[dict(r) for r in rows])

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/<code>")
    def follow(code: str):
        if not valid_code(code):
            abort_clean(404)
        row = get_db().execute(
            # Only public links resolve. Private links are indistinguishable
            # from "not found", so they can't be confirmed by enumeration (P5).
            "SELECT target_url FROM links WHERE code = ? AND visibility = 'public'",
            (code,),
        ).fetchone()
        if row is None:
            abort_clean(404)
        get_db().execute("UPDATE links SET hits = hits + 1 WHERE code = ?", (code,))
        get_db().commit()
        return redirect(row["target_url"], code=302)

    # -- Error handling (P3): never leak stack traces or internal state ------
    @app.errorhandler(HTTPException)
    def on_http_error(exc: HTTPException):
        return error_response(exc.code or 500, exc.name)

    @app.errorhandler(Exception)
    def on_unexpected_error(exc: Exception):
        # Log internally for us; return a generic message to the client.
        current_app.logger.exception("Unhandled error: %s", exc)
        return error_response(500, "Internal Server Error")

    return app


# --- Route helpers (need an app/request context) ---------------------------
def public_links() -> list[dict]:
    rows = get_db().execute(
        "SELECT code, target_url, hits, created_at FROM links "
        "WHERE visibility = 'public' ORDER BY created_at DESC LIMIT ?",
        (DIRECTORY_LIMIT,),
    ).fetchall()
    return [dict(r) for r in rows]


def require_admin() -> None:
    from flask import abort

    token = request.headers.get("X-Admin-Token", "")
    expected = current_app.config.get("ADMIN_TOKEN") or ""
    # Fail closed if somehow unset; constant-time compare avoids timing leaks.
    if not expected or not secrets.compare_digest(token, expected):
        abort(401)


def abort_clean(code: int):
    from flask import abort

    abort(code)


def error_response(code: int, name: str):
    if wants_json():
        return jsonify(error=name), code
    return render_template("error.html", code=code, message=name), code


# Module-level app so `python app.py` and `flask run` both work.
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # host 127.0.0.1: localhost only. debug=False: no interactive debugger/tracebacks.
    app.run(host="127.0.0.1", port=port, debug=False)
