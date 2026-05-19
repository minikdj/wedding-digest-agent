#!/usr/bin/env python3
"""Fetch everything the routine needs and print it as one JSON blob to stdout.

The routine agent runs this once, captures the output, and reasons over it
to compose the digest email. All deterministic plumbing happens here so the
agent only does composition.

Env: NOTION_TOKEN (required), GITHUB_TOKEN + GITHUB_REPO (required for prior
snapshots — empty repo is fine, just returns null/[]).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as `python scripts/fetch.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpers.dates import current_phase, days_until_wedding, today_ny
from helpers.digest import build_snapshot, compute_counts, task_to_jsonable
from helpers.notion import fetch_all_tasks
from helpers.snapshot import load_latest, load_recent


def main() -> int:
    today = today_ny()
    phase = current_phase(today)
    days_left = days_until_wedding(today)

    tasks = fetch_all_tasks()
    counts = compute_counts(tasks)
    today_snapshot = build_snapshot(today, counts)

    try:
        prior = load_latest()
        recent = load_recent(days=14)
    except Exception as exc:
        print(f"snapshot load failed (treating as first run): {exc}", file=sys.stderr)
        prior, recent = None, []

    payload = {
        "today": today.isoformat(),
        "phase": phase,
        "days_until_wedding": days_left,
        "counts": counts,
        "today_snapshot": today_snapshot,
        "prior_snapshot": prior,
        "recent_snapshots": recent,
        "tasks": [task_to_jsonable(t) for t in tasks],
    }
    json.dump(payload, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
