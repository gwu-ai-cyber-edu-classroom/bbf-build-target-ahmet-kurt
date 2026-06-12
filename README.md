# BBF Day — Your Team Repository

This is your team's repository for the **Build-it / Break-it / Fix-it** day at the AI +
Cybersecurity Summer Institute.

## What you're building

This run, every team builds a small **web app** — pick one from [BUILD-MENU.md](BUILD-MENU.md) and
the platform (Python with Flask/FastAPI, or Node with Express). A running web app gives breakers
an obvious HTTP surface to probe. Whatever you choose must satisfy the **five-property contract**
in [SPEC.md](SPEC.md):

- **P1 Confidentiality** — never leak the `CANARY_` secret through the interface.
- **P2 Correctness** — do your documented job right.
- **P3 Input discipline** — handle bad input gracefully.
- **P4 No injection / code execution** — never run user input as code/SQL/path/template.
- **P5 Authorization & output safety** — require auth for private data; no XSS.

You all build different apps, but breakers attack the **same properties**, which is what keeps the
day fair and comparable. See BUILD-MENU.md for the menu and a beginner-friendly Claude prompt to
scaffold your first version, and **[AGENTS.md](AGENTS.md)** for how your AI agent should behave in
each phase (Build / Break / Fix).

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
# 1. The canary your app must never leak is in secret/canary.txt — load it into
#    your app's data (e.g., a private record), but never return it over HTTP.
# 2. Build your chosen web app (Python with Flask/FastAPI, or Node with Express).
# 3. Run it locally on a high localhost port and confirm it works for a normal user.
# 4. Fill in START_APP.md so other teams can start and probe your app.
```

Push to `main`. The `build-check.yml` workflow runs `pytest tests/build_check.py` on every push —
a green check confirms your repo has a spec and a canary. It does **not** test your features or
whether your app runs; that's what the demo and the Break phase are for.

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

Open one PR per fix. The PR body should say `closes #N` so the issue auto-closes on merge — that
marks it `fix-claimed`; the **breaker** then confirms with `/fix-confirmed` (a two-step round) for
the fix to score. It is OK if Fix is partial — an honest "we would fix X next, here is why" is a
full-credit report-out. This is also where you can paste a specific confirmed break into Claude
and ask it to help fix *that one thing*.

**Duplicates.** The same defect via a different path is one break (one fix closes it) — file the
clearest repro and list the other paths as evidence. A facilitator can merge two issues with
`/duplicate-of #N` (and `/distinct` to undo); the optional `dup-detect.yml` workflow uses an LLM
to *suggest* likely duplicates as a comment, never merging on its own.

## Spec

See [SPEC.md](SPEC.md) for the five properties (P1–P5) every app must hold. Breakers must quote
one of these in their issue.

## Key files

- **[AGENTS.md](AGENTS.md)** — how your AI agent must behave; it gates on the current phase
  (Build / Break / Fix). Read it first.
- **[AGENTS_BREAK.md](AGENTS_BREAK.md)** — the rules for attacking another team's app: black-box
  first, then source-assisted once you've exhausted it (but you must still prove the break through
  the running app), plus the verification gate before filing.
- **[START_APP.md](START_APP.md)** — you fill this in so other teams can start and probe your app.
- **[BUILD-MENU.md](BUILD-MENU.md)**, **[SPEC.md](SPEC.md)**, **[ENVIRONMENTS.md](ENVIRONMENTS.md)**.

Want an AI flavor? Build a web app whose backend calls an LLM (add `openai` to
`requirements.txt`); the canary still lives in `secret/`. See BUILD-MENU.md.

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
