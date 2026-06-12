# Fix triage

All three open breaks (#1 from heena7sept, #2 and #3 from AbdunabiRamadan) are the
**same defect**: `GET /admin/links` accepted a hardcoded shipped admin token
(`dev-admin-token-change-me`), so any caller who read it from the source/README could
authenticate as admin and list the seeded **private** link — a P5 default-credential
authorization bypass (CWE-798). It does not leak the `CANARY_` (the `secret_note` column
is still never selected), so this was correctly scoped as P5, not P1. One fix closes all three.

## We are fixing
1. **#1, #2, #3** — Removed the shipped default admin token. `app.py` now reads
   `URLSHORT_ADMIN_TOKEN` if set; otherwise it generates a **strong random token per run**
   (`secrets.token_urlsafe(32)`) and prints it once to the console, so `/admin/*` is
   unreachable without a value the operator alone holds. `require_admin()` additionally
   **fails closed** if the token is empty. README/docstring updated.
   Verified: old default `dev-admin-token-change-me` → `401`; the random per-run token →
   `200`; no token → `401`. All 20 tests still pass.

## We are not fixing (yet)
- Nothing outstanding — these were the only breaks filed against this repo.
