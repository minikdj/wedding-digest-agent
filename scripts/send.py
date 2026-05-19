#!/usr/bin/env python3
"""Send the composed digest and commit today's snapshot.

Reads the draft JSON written by the routine agent. Schema:

    {
      "subject": "...",
      "html": "...",
      "text": "...",
      "snapshot": { "date": "YYYY-MM-DD", "total": ..., "done": ..., ... }
    }

Steps (in order):
  1. Validate the draft has all four keys.
  2. Send via Resend.
  3. Commit today's snapshot to snapshots/<date>.json via GitHub Contents API.

Prints one RESULT line at the end so the routine agent can parse it.

Env: RESEND_API_KEY, RECIPIENT_EMAIL, SENDER_EMAIL, GITHUB_TOKEN, GITHUB_REPO.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpers.email import send
from helpers.snapshot import save_today

REQUIRED_KEYS = ("subject", "html", "text", "snapshot")
REQUIRED_SNAPSHOT_KEYS = ("date", "total", "done", "in_progress", "not_started")


def _fail(msg: str, code: int = 1) -> int:
    print(f"RESULT: SEND FAILED | {msg}")
    return code


def main(argv: list[str]) -> int:
    draft_path = Path(argv[1] if len(argv) > 1 else "./digest-draft.json")
    if not draft_path.exists():
        return _fail(f"draft not found at {draft_path}")

    try:
        draft = json.loads(draft_path.read_text())
    except json.JSONDecodeError as exc:
        return _fail(f"invalid JSON: {exc}")

    missing = [k for k in REQUIRED_KEYS if k not in draft]
    if missing:
        return _fail(f"draft missing keys: {missing}")

    snap = draft["snapshot"]
    missing_snap = [k for k in REQUIRED_SNAPSHOT_KEYS if k not in snap]
    if missing_snap:
        return _fail(f"snapshot missing keys: {missing_snap}")

    try:
        msg_id = send(
            subject=draft["subject"], html=draft["html"], text=draft["text"]
        )
    except Exception as exc:
        return _fail(f"resend error: {exc}")

    print(f"RESULT: EMAIL SENT | id={msg_id}")

    try:
        save_today(snap)
        print(f"RESULT: SNAPSHOT SAVED | path=snapshots/{snap['date']}.json")
    except Exception as exc:
        # Email already delivered — snapshot failure is non-fatal but logged.
        print(f"RESULT: SNAPSHOT FAILED (non-fatal) | {exc}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
