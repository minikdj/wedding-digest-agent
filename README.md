# Wedding Digest Agent

Daily 07:00 ET email summarizing the state of the "Official Wedding Tasks" Notion database. Runs as a GitHub Actions cron workflow that executes a Python script — the script fetches Notion data, pre-computes counts, asks Claude (Sonnet 4.6) to compose the email body via a tool-forced call, sends via Resend, and commits today's snapshot back to this repo.

Read-only with respect to Notion. Burndown snapshots persist to `snapshots/YYYY-MM-DD.json` via the GitHub Contents API.

Why GitHub Actions and not an Anthropic Routine? The routine sandbox blocks raw outbound HTTPS to `api.notion.com`, `api.resend.com`, and `api.github.com`; only MCP-routed traffic gets through, and there's no email-send MCP. Actions has unrestricted network and native cron — the right fit.

## Architecture

```
.github/workflows/digest.yml  (cron: 0 11 * * *)
        │
        ▼
   python run_digest.py
        │
        ├─ helpers.dates       → today (America/New_York) + current phase
        ├─ helpers.notion      → fetch_all_tasks()            [Notion REST v2026-03-11]
        ├─ helpers.snapshot    → load_latest, load_recent      [GitHub Contents API]
        ├─ helpers.digest      → compute_counts(), build_snapshot()
        │
        ▼
   helpers.claude_summary.compose_digest()
        → one client.messages.create() with tool_choice=emit_digest
        → returns {subject, html, text}
        │
        ▼
   helpers.email.send()                                       [Resend]
   helpers.snapshot.save_today()                              [GitHub Contents API]
   stdout: "RUN OK | sent=<msg_id> | snapshot=snapshots/<date>.json"
```

## One-time setup

1. **Notion** — at https://www.notion.so/profile/integrations create an internal integration, share the "Official Wedding Tasks" database with it, copy the token.
2. **Resend** — sign up at https://resend.com under the email you want digests delivered to (so the sandbox sender `onboarding@resend.dev` is allowed to that address). Copy the API key.
3. **Anthropic** — your existing API key works.
4. **GitHub repo secrets** — Settings → Secrets and variables → Actions → "New repository secret". Add these five:

   | Secret name | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | from step 3 |
   | `NOTION_TOKEN` | from step 1 |
   | `RESEND_API_KEY` | from step 2 |
   | `RECIPIENT_EMAIL` | the email your Resend account is registered under |
   | `SENDER_EMAIL` | `onboarding@resend.dev` |

   `GITHUB_TOKEN` and `GITHUB_REPO` are auto-provided by Actions — you do not add them yourself. The workflow's `permissions: contents: write` block grants the auto-token the access it needs to commit snapshots.

## Run it once before the cron fires

GitHub → Actions tab → "Wedding Digest Daily" → "Run workflow" → "Run workflow" (against `main`). Watch the run; success looks like `RUN OK | sent=… | snapshot=…` in the final step's log. A `snapshots/<today>.json` commit will appear in the repo.

## Schedule

Cron is hard-coded to `0 11 * * *` (11:00 UTC = 07:00 ET during DST). When EST resumes (first Sunday of November), edit `.github/workflows/digest.yml` to `0 12 * * *` and commit. GitHub Actions cron has no DST handling.

## Local testing

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                       # 39 tests: date math, snapshot, Notion parse, counts
```

Dry-run end-to-end (hits Notion + Claude for real, skips Resend + snapshot commit):

```bash
export NOTION_TOKEN=secret_... ANTHROPIC_API_KEY=sk-ant-... \
       RESEND_API_KEY=re_dummy RECIPIENT_EMAIL=you@example.com \
       SENDER_EMAIL=onboarding@resend.dev \
       GITHUB_TOKEN=ghp_dummy GITHUB_REPO=minikdj/wedding-digest-agent \
       DRY_RUN=true
python run_digest.py
```

This costs ~$0.05 for the Claude call and prints the digest to stdout.

## Updating the prompt or helpers

Edit `prompts/system.md` or anything under `helpers/`, commit, push. The next cron run picks it up.

## Troubleshooting

**Workflow failed.** Click the failed run in the Actions tab. The final step's log has the stack trace. The script also tries to email a copy of the traceback to `RECIPIENT_EMAIL` before exiting on error — check your inbox too.

**Email landed but to: address wasn't allowed.** Resend sandbox (`onboarding@resend.dev`) only delivers to the account-owner's verified email. Confirm `RECIPIENT_EMAIL` matches the email your Resend account was registered under.

**Notion returned 401.** The integration isn't shared with the database. Open the database in Notion → ••• → Connections → add the integration.

**Notion returned 404.** Database ID has changed (or the API endpoint shape changed). Update `DATABASE_ID` in `helpers/notion.py`; check the URL in Notion (the 32-char hex string after the last `/`).

**Snapshot commit didn't appear.** The auto `GITHUB_TOKEN` needs `contents: write`. The workflow already requests that via `permissions: contents: write` at the job level — if you removed that block, restore it.

**Burndown shows "(no trend yet)" forever.** Expected for the first ~3 runs. If still missing after a week, check that snapshots are landing in `snapshots/` in the repo.

**Claude didn't call emit_digest.** Rare — bumps to `MAX_TOKENS` in `helpers/claude_summary.py` (currently 8192) usually fix it.

## What's out of scope

- Writing back to Notion (read-only).
- Email replies / interactive features.
- Multiple recipients with per-person filtering.
- Honeymoon tracking after 6/21 — the script sends a wind-down message; disable the workflow afterwards.
