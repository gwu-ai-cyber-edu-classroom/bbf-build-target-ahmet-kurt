# Build Menu

**This run, every team builds a small web app.** A running web app gives breakers an obvious,
interactive surface to attack — they probe it over HTTP like any user, instead of reading your
source. (That black-box rule is enforced for the breaking agent in
[AGENTS_BREAK.md](AGENTS_BREAK.md).)

Pick **one** web app below (or bring your own), and the platform (Python or Node). Every target
satisfies the **same five-property contract** in [SPEC.md](SPEC.md) (P1–P5), so breaks stay
comparable no matter what you chose.

Your app must:

- **expose an HTTP interface on `localhost`** (a high port) that a user — or an attacking agent —
  can interact with;
- **hold a `CANARY_` secret** in its data (e.g., a private record, another user's data, an admin
  field) that the app may use internally but must never leak through the interface;
- **document how to start it** in [START_APP.md](START_APP.md) so other teams can run and probe it.

## Constraints (so it runs in the workshop environments)

- **Stack:** Python (**Flask** or **FastAPI**) or Node (**Express**); an optional React/plain
  front-end is fine.
- **Runs on:** `localhost`, a high port (no admin, no privileged ports).
- **Storage:** SQLite (file-based), JSON, or flat files — **no system database server, no Docker.**
- **Buildable in ~90 minutes** with AI assistance.

---

## The web-app menu

| #  | App | Platform | Canary lives in | What breakers probe for |
|----|-----|----------|-----------------|--------------------------|
| 1  | **Paste-bin / snippet** service | Flask / FastAPI / Express | a private paste | IDOR, guessable IDs, stored XSS |
| 2  | **Notes / journal** app with login | Flask / FastAPI / Express | another user's note | authorization bypass, IDOR |
| 3  | **URL shortener** service | Flask / FastAPI / Express | a private / admin link | enumeration, open redirect |
| 4  | **Blog + comments** board | Flask / FastAPI / Express | an admin draft | stored XSS, authorization |
| 5  | **Contact / feedback** API | FastAPI / Flask / Express | internal recipient / secret | header / email injection, SSRF |
| 6  | **File upload + preview** | Flask / FastAPI / Express | a protected file | path traversal, content-type XSS |
| 7  | **Bookmark manager** REST API | FastAPI / Flask / Express | a private bookmark | IDOR, missing authorization on GET |
| 8  | **Key-value store** API | FastAPI / Flask / Express | a reserved key | namespace / authorization bypass |
| 9  | **Quiz / poll** app | Flask / FastAPI / Express | the answer key | answer-key leak via API, IDOR |
| 10 | **Webhook receiver / proxy** | FastAPI / Flask / Express | a secret token | SSRF, token leak in responses/logs |
| 11 | **Local doc search** service | Flask / FastAPI / Express | a private document | query injection returning private docs |

It's fine to bring your own web app instead — as long as it meets the three bullets above.

### Want an AI flavor?

Build a **web app whose backend calls an LLM** (e.g., a small chat/Q&A endpoint over your data) —
that's still a web app with an HTTP surface, so it fits this run. Add `openai` to
`requirements.txt`, point it at an OpenAI-compatible endpoint, and keep the canary in `secret/`.
An LLM endpoint adds prompt-injection / jailbreak / leakage to the break surface on top of P1–P5.

---

## Getting started with Claude (beginner-friendly)

In the **Build** phase, paste this into Claude to scaffold a working first version. Fill in the
one bracket with your menu choice:

```
We're a team at a Build-it / Break-it / Fix-it workshop and we don't have much
coding experience. Help us build a small, WORKING web app: [PICK ONE FROM THE
MENU, e.g. "a paste-bin service"]. It should run on our own laptop with NO admin
rights, on localhost (Python with Flask/FastAPI, or Node with Express).

Our app needs to hold a secret string starting with CANARY_ somewhere in its data
(for example, in a private record the app stores).

Please:
1. Choose the simplest stack (Python or Node) and say why in one sentence.
2. Create the project files step by step, explaining each file in plain language.
3. Give us the exact commands to install and run it locally, and the local URL.
4. Tell us where the CANARY_ secret lives.

Don't try too hard to make it secure yet — build the straightforward, naive
version. This is a lab and the next phase needs real weaknesses to find. Don't
add extra hardening, input sanitizing, auth, or output escaping unless we ask.

Go one step at a time and pause after each step so we can keep up. Assume we're
beginners.
```

When it works, fill in [START_APP.md](START_APP.md) with the start command and URL so other teams
can run and probe your app. During the **Fix** phase, paste a specific confirmed break from your
Issues and ask Claude to help fix *that one thing* — that is where the security learning lands.
See [AGENTS.md](AGENTS.md) for how your AI agent should behave in each phase.
