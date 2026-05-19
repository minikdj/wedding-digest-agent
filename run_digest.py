#!/usr/bin/env python3
"""Wedding digest agent — main entry point.

Invoked by the GitHub Actions workflow `.github/workflows/digest.yml` once
per day at 07:00 ET. Also runnable locally with DRY_RUN=true.

Sequence:
  1. Resolve today's date + phase
  2. Fetch all tasks from Notion
  3. Load prior snapshot + recent trend from the snapshots/ dir
  4. Pre-compute counts deterministically
  5. Ask Claude to compose the digest email (one tool-forced call)
  6. Send via Resend
  7. Commit today's snapshot back to the repo

Environment:
  ANTHROPIC_API_KEY, NOTION_TOKEN, RESEND_API_KEY, GITHUB_TOKEN,
  GITHUB_REPO, RECIPIENT_EMAIL, SENDER_EMAIL
  Optional: DRY_RUN=true (print instead of send/save)
"""
from __future__ import annotations

import os
import sys
import traceback

from helpers.claude_summary import compose_digest
from helpers.dates import current_phase, days_until_wedding, today_ny
from helpers.digest import build_snapshot, compute_counts
from helpers.email import send
from helpers.notion import fetch_all_tasks
from helpers.snapshot import load_latest, load_recent, save_today


def _dry_run() -> bool:
    return os.environ.get("DRY_RUN", "").lower() in ("true", "1", "yes")


def _send_error_email(exc: Exception) -> None:
    """Best-effort error notification. Never raises further."""
    try:
        send(
            subject="⚠ Wedding digest — run failed",
            html=f"<pre>{traceback.format_exc()}</pre>",
            text=traceback.format_exc(),
        )
    except Exception as e:
        print(f"could not send error email: {e}", file=sys.stderr)


def main() -> int:
    today = today_ny()
    phase = current_phase(today)
    days_left = days_until_wedding(today)
    print(f"start | today={today} | phase={phase!r} | days_left={days_left}")

    try:
        tasks = fetch_all_tasks()
    except Exception as exc:
        print(f"notion fetch failed: {exc}", file=sys.stderr)
        if not _dry_run():
            _send_error_email(exc)
        return 1

    prior = load_latest() if not _dry_run() else None
    trend = load_recent(days=14) if not _dry_run() else []
    counts = compute_counts(tasks)
    snapshot = build_snapshot(today, counts)

    print(
        f"fetched | tasks={counts['total']} | done={counts['done']} | "
        f"in_progress={counts['in_progress']} | not_started={counts['not_started']}"
    )

    try:
        result = compose_digest(
            today=today,
            phase=phase,
            days_left=days_left,
            tasks=tasks,
            counts=counts,
            prior_snapshot=prior,
            recent_snapshots=trend,
        )
    except Exception as exc:
        print(f"claude compose failed: {exc}", file=sys.stderr)
        if not _dry_run():
            _send_error_email(exc)
        return 1

    if _dry_run():
        print("=== DRY RUN ===")
        print(f"SUBJECT: {result['subject']}")
        print("--- TEXT ---")
        print(result["text"])
        print("--- HTML (first 400 chars) ---")
        print(result["html"][:400])
        print("--- SNAPSHOT ---")
        print(snapshot)
        return 0

    msg_id = send(subject=result["subject"], html=result["html"], text=result["text"])
    save_today(snapshot)
    print(f"RUN OK | sent={msg_id} | snapshot=snapshots/{snapshot['date']}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
