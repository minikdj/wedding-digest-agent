from __future__ import annotations

from datetime import date
from typing import Any


def compute_counts(tasks: list[dict]) -> dict[str, int]:
    """Deterministic count math. The LLM should never have to count 75 things."""
    cp = [t for t in tasks if t["critical_path"]]
    return {
        "total": len(tasks),
        "done": sum(1 for t in tasks if t["status"] == "Done"),
        "in_progress": sum(1 for t in tasks if t["status"] == "In progress"),
        "not_started": sum(1 for t in tasks if t["status"] == "Not started"),
        "critical_path_total": len(cp),
        "critical_path_done": sum(1 for t in cp if t["status"] == "Done"),
    }


def build_snapshot(today: date, counts: dict[str, int]) -> dict[str, Any]:
    pct = round(counts["done"] / max(counts["total"], 1) * 100, 1)
    return {
        "date": today.isoformat(),
        **counts,
        "percent_complete": pct,
    }


def task_to_jsonable(t: dict) -> dict:
    """Strip non-JSON-serializable fields (datetime/date) before sending to Claude."""
    return {
        "id": t["id"],
        "url": t["url"],
        "title": t["title"],
        "status": t["status"],
        "start_date": t["start_date"].isoformat() if t["start_date"] else None,
        "due_date": t["due_date"].isoformat() if t["due_date"] else None,
        "phase": t["phase"],
        "owner": t["owner"],
        "category": t["category"],
        "critical_path": t["critical_path"],
        "context": t["context"],
        "source": t["source"],
        "last_edited_time": t["last_edited_time"].isoformat(),
    }
