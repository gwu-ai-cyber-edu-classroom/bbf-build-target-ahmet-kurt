# AGENTS_BREAK.md — Break-phase agent instructions

You are the **breaking agent** for a team attacking **another team's running web app** during the
Break phase of a Build-it / Break-it / Fix-it lab. These rules travel with the app you are
attacking; follow them.

## Learning objective (read this first)

The point is **not** to discover that a `CANARY_` secret exists — it obviously does. The point is
to learn **how the app breaks**: which request triggers the failure, what the app does wrong, and
why its guardrail (if any) didn't hold. **A break you cannot explain is not a finding** — even if
you read the source, you must still *show* the break through the running app.

## The rules — black box first, then source (a gate, not a wall)

Break in **two phases, in order**. Do not skip ahead.

### Phase 1 — Black box (required first)

Attack the **running app over HTTP only**. Start it via [START_APP.md](START_APP.md) and interact
through its interface — requests, forms, endpoints — exactly as a user would. Try every angle you
can across P1–P5 (see *Probe angles* below) and log each attempt in the gate. **Stay in Phase 1
until you have genuinely exhausted your black-box ideas** — not after the first failure. This
struggle is where most of the learning is.

### Gate → Phase 2

Only after you have made a real black-box effort and ticked **"black-box exhausted"** in the
verification gate may you open the target's source. Be honest with yourself about the gate.

### Phase 2 — Source-assisted (white box)

Now you may read the target's source / config to **locate and understand** a flaw. Two things
still hold:

- **Reading a file to copy the `CANARY_` out of `secret/` is NOT a break.** Finding the secret in
  a file proves nothing — anyone can `cat` a file.
- **A valid break is still demonstrated through the running app's interface**: an input (or short
  sequence) that makes the app violate a property, with the request + response as evidence, and the
  mechanism explained. Use the source to *find* the bug; then *prove* it against the app.

### Always

A valid break is **reproducible from inputs alone** and **classroom-safe** (no real exploits
against real systems, no destructive payloads, no private content). If unsure, ask the facilitator.

## Probe angles (per property)

- **P1 Confidentiality:** can any request make the app return the `CANARY_` secret (directly, in an
  error/stack trace, in JSON, reflected, base64'd, via a verbose/debug path)?
- **P2 Correctness:** does ordinary valid input ever return the wrong result?
- **P3 Input discipline:** do malformed / empty / oversized inputs crash it or dump internals?
- **P4 Injection / code execution:** SQL injection, command injection, path traversal, template
  injection (SSTI) through the inputs the app accepts.
- **P5 Authorization / output safety:** can you read another user's resource by changing an ID
  (IDOR) or hitting an endpoint without auth? Does user content render as HTML (XSS)?

## Verification gate (update this section as you go)

This is your team's working tracker for this target (local to your clone — not pushed to the
target). **Do not file an issue for a finding whose gate is not `[x] verified`, and do not re-file
a finding already listed here.**

```
## This target
- [ ] Black-box exhausted (Phase 1 done) — source review allowed only after this is ticked

## Verified findings
<!-- One line per candidate. Mark [x] only after you reproduced it against the RUNNING app and
     captured request+response evidence. Note whether you found it black-box or via the source. -->
- [ ] P?: <one-line mechanism> — found: black-box|source — evidence captured: no — issue: #___
```

Example once verified:

```
- [x] Black-box exhausted (Phase 1 done)
- [x] P1: /notes/2 returns another user's note containing the canary (no auth check) — found: black-box — evidence captured: yes — issue: #14
```

## Filing the break — what the issue must contain

Once a finding is gated `[x] verified`, file it as a **Break Report** on the **target team's
repo**. Whether you use the web form or `gh`, the issue must contain these six fields (the web
form enforces them):

1. **Target artifact** — the endpoint/page you attacked (e.g., `GET /notes/{id}`).
2. **Attack class** — the closest category (idor-authz, xss, sql-injection, leakage, ...).
3. **Property violated** — the SPEC property quoted verbatim (e.g., `P1: Confidentiality`).
4. **Steps to reproduce** — numbered, copy-pasteable requests against the running app.
5. **Evidence** — the actual request and the response that proves it (the leaked `CANARY_`, the
   other user's record, the reflected script, …).
6. **Severity** — low / medium / high.

In the steps/evidence, **explain the mechanism in one or two sentences** — *why* the app failed.
That explanation is the learning objective; a finding without it is not done.

### Before you file: check for a duplicate

Another team may have already filed the **same** break against this target. **Always check the
target repo's existing issues first** and do not file a duplicate:

```bash
# Scan existing Break Reports on the target (open and closed):
gh issue list --repo <org>/<target-repo> --state all --limit 200 \
  --json number,title,state,labels --jq '.[] | "\(.number) [\(.state)] \(.title)"'
```

**What counts as the "same" break: the root cause, not the path.** A single underlying defect
(e.g., one missing authorization check, one unescaped field) is **one break** even if you can
reach it through several routes, parameters, or payload encodings. The scoreboard groups by
`target + property + attack class`, so a second route into the *same* defect is treated as a
duplicate. The test is the **fix**: if one patch closes all the variants you found, it is one
break — file the clearest single repro, and list the other paths in that issue's body as extra
evidence.

If an issue already reports the **same break** (same target + property + attack class, same root
cause), you **may still file it** — but **the first team to file earns full points**, and later
duplicates **decay** (halved roughly every 5 minutes, toward zero). So a late duplicate is worth
little or nothing. Usually the better move is to **comment on the existing issue** with your
additional path/evidence and spend your time finding a **different, new** break.

A **genuinely distinct break is a different root cause** — a separate defect that needs its own
fix — even if it shares an attack class with one already filed (e.g., two independent injection
bugs in two unrelated queries). File those separately and note in the body why the fix differs.
If you and the facilitator disagree about whether two issues are the same defect, the facilitator
can merge them (`/duplicate-of #N`) or split them (`/distinct`).

### Two ways to file

- **Web form (preferred):** on the target repo, **Issues → New issue** opens the Break Report form
  directly (or go to `https://github.com/<org>/<target-repo>/issues/new`). It enforces all six
  fields.
- **Via `gh` (your agent can do this for you):**

  ```bash
  gh issue create --repo <org>/<target-repo> \
    --title "[BREAK] P1: /notes/{id} returns another user's note (IDOR)" \
    --body "$(cat <<'BODY'
  ### Target artifact
  GET /notes/2

  ### Attack class
  idor-authz

  ### Property violated
  P1: Confidentiality

  ### Steps to reproduce
  1. Start the app per START_APP.md (e.g. http://localhost:8000).
  2. Log in as user A, then request GET /notes/2 (a note owned by user B).
  3. Observe the response.

  ### Evidence
  Request:  GET /notes/2
  Response: 200 {"note": "... CANARY_alpha_7Fz9pQrK2mE1Lv3X ..."}
  Mechanism: the handler loads a note by id with no owner/authorization check, so
  any logged-in user can read any note — including one holding the canary.

  ### Severity
  high
  BODY
  )"
  ```

### Student prompt — tell your agent how to break

Paste this to your agent when you start attacking a target:

```
Attack the target app at <URL>. Work BLACK-BOX FIRST: only interact with the
running app over HTTP, try to violate P1–P5, and keep going until you've exhausted
black-box ideas — note what you tried in AGENTS_BREAK.md and tick "black-box
exhausted". ONLY THEN, if needed, read the target's source to locate a bug — but a
finding must still be reproduced through the running app. Do NOT just grep the
CANARY_ out of secret/; finding the secret in a file is not a break. For each
confirmed break, capture the exact request + response, explain the mechanism (why
the app failed), and note the discovery method (black-box or white-box). Before
filing, list the target repo's existing issues (gh issue list); if the same break
is already reported you MAY still file it, but it will score little (first finder
wins; duplicates decay), so prefer commenting and finding a NEW break. Otherwise
mark it [x] verified in AGENTS_BREAK.md and file a Break Report with all six fields
on <org>/<target-repo>.
```

After filing, a member of the target team comments `/repro-confirmed` to validate it — only then
does it count on the scoreboard.

## Confirming a fix (the Fix-review round)

When a team you broke ships a fix, **you** (the team that filed the break) verify it — a fix is
not credited on the target's say-so:

1. The target opens a PR with `closes #N` and merges it. The issue closes and is labeled
   `fix-claimed` (it shows as **fix-review** in the Break feed). It does **not** score the fix yet.
2. **Re-run your exact break** against the target's now-fixed running app.
   - If the break is **gone**, comment **`/fix-confirmed`** on the issue → it's labeled `fixed`
     and the fix scores for the target.
   - If the break **still reproduces**, comment **`/fix-failed`** with the evidence → the issue
     reopens (`fix-rejected`) and the target must try again.

Only the **breaker who filed the issue** (or a facilitator) may confirm or reject a fix.
