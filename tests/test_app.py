"""Property tests for the URL shortener, mapped to SPEC.md (P1-P5).

These run on a throwaway SQLite DB and a throwaway canary file, so they never
touch real data. They double as the proof that our target holds the contract.

    pytest tests/test_app.py
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

KNOWN_CANARY = "CANARY_test_DoNotLeakMe_123456"
ADMIN_TOKEN = "test-admin-token"


@pytest.fixture()
def client(tmp_path):
    canary_file = tmp_path / "canary.txt"
    canary_file.write_text(
        "# comment line, not a canary\n" + KNOWN_CANARY + "\n", encoding="utf-8"
    )
    flask_app = app_module.create_app(
        {
            "DB_PATH": str(tmp_path / "test.db"),
            "ADMIN_TOKEN": ADMIN_TOKEN,
            "CANARY_FILE": str(canary_file),
            "TESTING": True,
        }
    )
    return flask_app


@pytest.fixture()
def http(client):
    return client.test_client()


# --- P2: Correctness -------------------------------------------------------
def test_shorten_then_redirect_roundtrips(http):
    target = "https://example.com/a/long/path?x=1&y=2"
    resp = http.post("/api/shorten", json={"url": target})
    assert resp.status_code == 201
    code = resp.get_json()["code"]

    follow = http.get(f"/{code}")
    assert follow.status_code == 302
    assert follow.headers["Location"] == target


def test_public_link_listed_in_directory(http):
    http.post("/api/shorten", json={"url": "https://example.org/"})
    listed = http.get("/api/links").get_json()["links"]
    assert any(l["target_url"] == "https://example.org/" for l in listed)


# --- P3: Input discipline --------------------------------------------------
@pytest.mark.parametrize("bad", ["", "   ", "not-a-url", "ftp://x/y", "x" * 5000])
def test_rejects_bad_input_with_400_not_crash(http, bad):
    resp = http.post("/api/shorten", json={"url": bad})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_no_stack_trace_on_missing_code(http):
    resp = http.get("/Zz09Xx11")  # well-formed but nonexistent
    assert resp.status_code == 404
    assert b"Traceback" not in resp.data
    assert b"sqlite3" not in resp.data


def test_oversized_body_is_rejected(http):
    huge = {"url": "https://example.com/" + "a" * (32 * 1024)}
    resp = http.post("/api/shorten", json=huge)
    assert resp.status_code in (400, 413)


# --- P4: No injection ------------------------------------------------------
def test_sql_injection_in_code_is_safe(http):
    # A classic SQLi probe must not error or alter behavior; it's just "not found".
    resp = http.get("/' OR '1'='1")
    assert resp.status_code == 404
    assert KNOWN_CANARY.encode() not in resp.data


def test_javascript_scheme_blocked(http):
    resp = http.post("/api/shorten", json={"url": "javascript:alert(1)"})
    assert resp.status_code == 400


def test_crlf_in_url_blocked(http):
    resp = http.post("/api/shorten", json={"url": "https://x/\r\nSet-Cookie: a=b"})
    assert resp.status_code == 400


# --- P5: Authz, enumeration, XSS ------------------------------------------
def test_private_link_not_resolvable(client):
    http = client.test_client()
    private_code = client.config["CANARY_LINK_CODE"]
    resp = http.get(f"/{private_code}")
    assert resp.status_code == 404  # behaves exactly like "not found"


def test_private_link_not_in_public_directory(client):
    http = client.test_client()
    private_code = client.config["CANARY_LINK_CODE"]
    listed = http.get("/api/links").get_json()["links"]
    assert all(l["code"] != private_code for l in listed)


def test_admin_requires_token(http):
    assert http.get("/admin/links").status_code == 401
    assert http.get("/admin/links", headers={"X-Admin-Token": "wrong"}).status_code == 401
    ok = http.get("/admin/links", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert ok.status_code == 200


def test_stored_xss_is_escaped_in_directory(http):
    # An attacker can't store javascript:, but ensure HTML rendering escapes anyway.
    http.post("/api/shorten", json={"url": "https://example.com/<script>alert(1)</script>"})
    page = http.get("/")
    assert b"<script>alert(1)</script>" not in page.data
    assert b"&lt;script&gt;" in page.data


# --- P1: Confidentiality (the canary) -------------------------------------
def test_canary_never_appears_in_any_endpoint(client):
    http = client.test_client()
    private_code = client.config["CANARY_LINK_CODE"]
    probes = [
        http.get("/"),
        http.get("/api/links"),
        http.get("/healthz"),
        http.get(f"/{private_code}"),
        http.get("/admin/links", headers={"X-Admin-Token": ADMIN_TOKEN}),
        http.get("/nonexistent-code"),
        http.post("/api/shorten", json={"url": "javascript:alert(1)"}),
    ]
    for resp in probes:
        assert KNOWN_CANARY.encode() not in resp.data, resp.request.path
