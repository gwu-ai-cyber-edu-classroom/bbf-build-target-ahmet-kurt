[![Open in Codespaces](https://classroom.github.com/assets/launch-codespace-2972f46106e565e64193e422d61a12cf1da4916b45550586e14ef0a7c637dd04.svg)](https://classroom.github.com/open-in-codespaces?assignment_repo_id=24126372)
# BBF Day — Your Team Repository

This is your team's repository for the **Build-it / Break-it / Fix-it** day at the AI +
Cybersecurity Summer Institute.

## What you're building

Your team picks **one** application to build from [BUILD-MENU.md](BUILD-MENU.md) — a CLI tool, a
local web app, an API, a document generator, and so on. You also pick the platform (Python or
Node). Whatever you choose, it must satisfy the **five-property contract** in [SPEC.md](SPEC.md):

- **P1 Confidentiality** — never leak the `CANARY_` secret.
- **P2 Correctness** — do your documented job right.
- **P3 Input discipline** — handle bad input gracefully.
- **P4 No injection / code execution** — never run user input as code.
- **P5 Authorization & output safety** — (web/UI targets) require auth, no XSS.

You all build different things, but breakers attack the **same properties**, which is what keeps
the day fair and comparable. See BUILD-MENU.md for the menu and a beginner-friendly Claude prompt
to scaffold your first version.

---

## 🚀 Our target: Tiny URL Shortener (BUILD-MENU #15)

A local Flask + SQLite URL shortener. Paste an `http`/`https` link, get a short code back;
visiting `/<code>` 302-redirects to the original.

**Run it:**

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

**One clear entry point:** the web UI at `http://127.0.0.1:5000`. JSON API and admin surface:

| Method & path        | Auth                     | Purpose                                  |
|----------------------|--------------------------|------------------------------------------|
| `GET  /`             | none                     | Web form + public link directory         |
| `POST /`             | none                     | Shorten a URL (HTML form)                 |
| `POST /api/shorten`  | none                     | Shorten a URL (JSON: `{"url": "..."}`)    |
| `GET  /<code>`       | none                     | Redirect to the original URL             |
| `GET  /api/links`    | none                     | List **public** links (JSON)             |
| `GET  /admin/links`  | `X-Admin-Token` header   | List all links' metadata (no secrets)    |
| `GET  /healthz`      | none                     | Liveness check                           |

Admin token defaults to `dev-admin-token-change-me` (override with `URLSHORT_ADMIN_TOKEN`).

**Where the canary lives:** the `CANARY_` strings in [`secret/canary.txt`](secret/canary.txt) are
loaded at startup and stored as the `secret_note` of one seeded **private** link. No SQL query ever
reads that column back and no route ever emits it — the app *holds* the secret but never serves it.

**How we hold the contract (SPEC.md P1–P5):**

- **P1 Confidentiality** — canary stored write-only (`secret_note` is never SELECTed); no debug mode, no stack traces.
- **P2 Correctness** — shorten + redirect round-trips the exact URL; hit counts increment.
- **P3 Input discipline** — URL length cap (2048), control-char rejection, 16 KB request cap, generic error pages.
- **P4 No injection** — parameterized SQLite only; no `eval`/`exec`/shell; codes validated before lookup; templates never built from input.
- **P5 Authz & output safety** — unguessable random codes (no enumeration/IDOR); private links 404 for everyone; `/admin/*` uses a constant-time token check; Jinja autoescaping + `http`/`https`-only targets block XSS and `javascript:` redirects. **P5 applies** to this target (it has a web/admin surface).

> Note: redirecting to arbitrary `http`/`https` destinations is the *intended* job of a shortener;
> we block dangerous schemes (`javascript:`, `data:`, `file:`) and never fetch targets server-side.

**Run our tests:** `pytest tests/test_app.py` (property tests mapped to P1–P5).

---

## Set up your environment

See [ENVIRONMENTS.md](ENVIRONMENTS.md). In order of preference: your own laptop → a local,
no-admin install on a lab Windows machine (Option B) → a Codespace (Option A). You need `git`,
a Bash shell, and Python and/or Node; LaTeX targets also need MiKTeX.

**Codespaces are ready-to-go.** This repo ships a `.devcontainer/`, and Codespaces is enabled on
the institute's GitHub organization, so opening this repo with **Code → Codespaces → Create
codespace** gives you a container with **Python, Node, the GitHub CLI, and Claude Code already
installed** — no manual setup. (LaTeX/PDF target only: run `bash .devcontainer/install-latex.sh`
once to add the TeX toolchain on demand.) For the best Claude Code experience, connect to that Codespace from
desktop VS Code (the thin-client path) rather than the browser.

## Quick start

```bash
# 1. Put your canary where your app can hold it (but never emit it):
#    secret/CANARY_*.txt   (most targets)
# 2. Build your chosen target's code (Python or Node).
# 3. Run it locally and confirm it works on valid input.
```

Push to `main`. The `build-check.yml` workflow runs `pytest tests/build_check.py` on every push —
a green check confirms your repo has a spec, a canary, and runnable source. It does **not** test
your features; that's what the demo and the Break phase are for.

## Phases

### 1. Build (90 min)

Build a working version of your chosen target so it satisfies [SPEC.md](SPEC.md). Push to `main`.
End-of-phase: each team gives a 3-minute demo of what they shipped and how to run it.

### 2. Break (90 min, working lunch)

File issues against **other teams' repos** using the **Break Report** issue template. The form is
built into every team repo (`.github/ISSUE_TEMPLATE/break-report.yml`), so on the target repo go
to `Issues → New issue → Break Report` and it walks you through the six required fields:

1. Target artifact
2. Attack class (dropdown)
3. Property violated (quote from `SPEC.md` verbatim)
4. Steps to reproduce
5. Evidence
6. Severity

**Not sure how to fill it in?** Ask your AI agent (Claude Code) to file the break for you — it can
create the issue directly on the target team's repo with
`gh issue create --repo <org>/<their-repo>` and populate all six fields from your reproduction.

After filing:

- Notify the targeted team within 5 minutes — GitHub does this automatically because they're
  auto-subscribed to issues on their own repo.
- The targeted team will try to reproduce. They comment `/repro-confirmed` if they can, or
  `/repro-failed` if they can't.
- Only `/repro-confirmed` breaks count for the scoreboard.

End-of-phase: each team presents their single most interesting break for 3 minutes.

### 3. Fix (90 to 120 min)

Read every issue logged against your repo. Triage in `fix_notes.md` (create it):

```markdown
# Fix triage

We are fixing:
1. #N — reason
2. #M — reason

We are not fixing (yet):
- #X — would-fix-next reason
```

Open one PR per fix. The PR body should say `closes #N` so the issue auto-closes on merge. The
`issue-events.yml` workflow adds the `fixed` label. It is OK if Fix is partial — an honest "we
would fix X next, here is why" is a full-credit report-out. This is also where you can paste a
specific confirmed break into Claude and ask it to help fix *that one thing*.

## Spec

See [SPEC.md](SPEC.md) for the named properties (P1–P5) every artifact must hold. Breakers must
quote one of these in their issue.

## Optional AI-assistant track

This repo also ships an optional AI-assistant example (`assistant.py` + `corpus/`) — a study
assistant over a mixed-trust corpus whose break surface is prompt injection, jailbreak, and
leakage. It needs an OpenAI-compatible LLM endpoint (local Ollama or a hosted key) and is **not
required**. Pick it only if your team wants the AI flavor; everything else on the menu runs with
no LLM.

## Useful commands

```bash
# What issues are filed against my repo?
gh issue list --state all

# What breaks are confirmed valid?
gh issue list --label valid

# What is left to fix?
gh issue list --label valid --search 'no:fixed'
```

## Acknowledgements

The Build-it / Break-it / Fix-it format was created at the University of Maryland by Andrew Ruef,
James Parker, Michael Hicks, and collaborators. See `../github-infrastructure-plan.md` in the
institute repo for the full background.
