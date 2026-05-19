# Wedding Digest Agent

Daily 07:00 ET email summarizing the state of the "Official Wedding Tasks" Notion database. Runs as an Anthropic Routine wired to this repo — Claude itself, inside the routine session, does the fetching, reasoning, and composition by bash-running scripts in this repo.

Read-only with respect to Notion. Burndown snapshots persist to this repo at `snapshots/YYYY-MM-DD.json` via the GitHub Contents API.

## Architecture

```
Routine (07:00 ET, wired to this repo)
        │
        ▼
   Claude session in repo working dir, env vars from Routine secrets
        │
        ├─ bash:  pip install + python scripts/fetch.py > /tmp/wedding-data.json
        │           → helpers.notion.fetch_all_tasks()         [Notion REST v2026-03-11]
        │           → helpers.snapshot.load_latest/recent()    [GitHub Contents API]
        │           → helpers.digest.compute_counts()
        │
        ├─ reason: bucket tasks, compute burndown, apply strict template
        │
        ├─ write:  digest-draft.json  {subject, html, text, snapshot}
        │
        └─ bash:  python scripts/send.py ./digest-draft.json
                    → helpers.email.send()                     [Resend]
                    → helpers.snapshot.save_today()            [GitHub Contents API]
                    → RESULT: EMAIL SENT | id=...
```

- **`routine-prompt.md`** — paste this into Console → Routines. Contains the step-by-step instructions Claude follows in the session and the strict email template.
- **`scripts/fetch.py`** — fetches Notion + prior snapshots + computes counts, prints one JSON to stdout.
- **`scripts/send.py`** — reads `digest-draft.json`, sends via Resend, commits today's snapshot.
- **`helpers/`** — underlying library (Notion REST, Resend, GitHub Contents API, date/phase math, count math).

## One-time setup

1. **Notion** — create an internal integration at https://www.notion.so/profile/integrations, share the "Official Wedding Tasks" database with it, copy the token.
2. **Resend** — sign up at https://resend.com under the email you want digests delivered to (so the sandbox sender `onboarding@resend.dev` delivers to that address). Copy the API key.
3. **GitHub** — repo lives at https://github.com/minikdj/wedding-digest-agent. Create a fine-grained PAT with `Contents: read & write` scoped to just this repo.
4. **Anthropic** — your existing API key is what the Routine uses.

## Routine configuration

In Anthropic Console → Routines, create a new routine wired to `minikdj/wedding-digest-agent`. Paste the contents of [`routine-prompt.md`](./routine-prompt.md) (between START and END markers) into the prompt field.

Schedule: `0 11 * * *` (07:00 ET in DST; switch to `0 12 * * *` when EST resumes Nov 1).

Set these six secrets in the Routine's environment:

| Secret | Value |
|---|---|
| `NOTION_TOKEN` | from step 1 |
| `RESEND_API_KEY` | from step 2 |
| `GITHUB_TOKEN` | from step 3 |
| `GITHUB_REPO` | `minikdj/wedding-digest-agent` |
| `RECIPIENT_EMAIL` | your Resend account email |
| `SENDER_EMAIL` | `onboarding@resend.dev` |

## Local testing

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                        # 39 tests: date math, snapshot, Notion parse, counts
```

Smoke-test the fetch script against real Notion (no email sent):

```bash
export NOTION_TOKEN=secret_... GITHUB_TOKEN=ghp_... GITHUB_REPO=minikdj/wedding-digest-agent
python scripts/fetch.py | head -40
```

You should see a JSON object with `today`, `phase`, `counts`, `tasks`, etc.

## Updating the prompt or helpers

Edit `routine-prompt.md` or anything under `helpers/` / `scripts/`, commit, push. The next routine run picks up the change because the routine clones a fresh copy of the repo each time.

If you edit `routine-prompt.md`, also paste the updated prompt into the Routine UI — the Routine stores a copy of the prompt, not a reference to the file.

## Troubleshooting

**No email arrived.** Check the routine run logs in Console. The final lines should be `RESULT: EMAIL SENT | id=...` and `RESULT: SNAPSHOT SAVED | ...`. If `RESULT: SEND FAILED` shows up, the message has the reason.

**Email landed but to: address wasn't allowed.** Resend sandbox (`onboarding@resend.dev`) only delivers to the account-owner's verified email. Confirm `RECIPIENT_EMAIL` matches the email your Resend account was registered under.

**Notion returned 401.** The integration isn't shared with the database. Open the database in Notion → ••• → Connections → add the integration.

**Notion returned 404.** Data-source ID is wrong. Update `DATA_SOURCE_ID` in `helpers/notion.py`.

**Snapshot 403/404 from GitHub.** Token missing `Contents: write` on the repo, or `GITHUB_REPO` is wrong.

**Burndown shows "(no trend yet)" forever.** Expected for the first ~3 runs. If it persists, check that snapshots are landing in `snapshots/` in the repo.

**Claude wrote a malformed `digest-draft.json`.** `scripts/send.py` prints `RESULT: SEND FAILED | invalid JSON: ...` or `draft missing keys: [...]`. The routine prompt instructs Claude to build the draft via a `/tmp/` Python helper rather than hand-escape — if you see this error, the prompt was probably ignored or modified.

## What's out of scope

- Writing back to Notion (read-only).
- Email replies / interactive features.
- Multiple recipients with per-person filtering.
- Honeymoon tracking after 6/21 — the routine sends a wind-down email and should then be disabled.
