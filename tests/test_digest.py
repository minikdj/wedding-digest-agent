"""Tests for the deterministic count/snapshot helpers."""
from datetime import date

from helpers.digest import build_snapshot, compute_counts, task_to_jsonable


def _t(**kw):
    base = {
        "id": "x", "url": "u", "title": "t", "status": None,
        "start_date": None, "due_date": None,
        "phase": [], "owner": [], "category": [],
        "critical_path": False, "context": "", "source": None,
        "last_edited_time": None,
    }
    base.update(kw)
    return base


def test_compute_counts_basic():
    tasks = [
        _t(status="Done", critical_path=True),
        _t(status="Done"),
        _t(status="In progress", critical_path=True),
        _t(status="Not started", critical_path=True),
        _t(status=None),
    ]
    c = compute_counts(tasks)
    assert c == {
        "total": 5,
        "done": 2,
        "in_progress": 1,
        "not_started": 1,
        "critical_path_total": 3,
        "critical_path_done": 1,
    }


def test_compute_counts_empty():
    c = compute_counts([])
    assert c["total"] == 0
    assert c["critical_path_total"] == 0


def test_build_snapshot_percent():
    counts = {
        "total": 75, "done": 3, "in_progress": 10,
        "not_started": 62, "critical_path_total": 22, "critical_path_done": 1,
    }
    snap = build_snapshot(date(2026, 5, 19), counts)
    assert snap["date"] == "2026-05-19"
    assert snap["percent_complete"] == 4.0
    assert snap["total"] == 75


def test_build_snapshot_zero_total():
    snap = build_snapshot(date(2026, 5, 19), {
        "total": 0, "done": 0, "in_progress": 0, "not_started": 0,
        "critical_path_total": 0, "critical_path_done": 0,
    })
    assert snap["percent_complete"] == 0.0


def test_task_to_jsonable_strips_datetimes():
    from datetime import datetime, timezone
    task = _t(
        start_date=date(2026, 5, 19),
        due_date=date(2026, 5, 22),
        last_edited_time=datetime(2026, 5, 18, 13, 0, tzinfo=timezone.utc),
    )
    j = task_to_jsonable(task)
    assert j["start_date"] == "2026-05-19"
    assert j["due_date"] == "2026-05-22"
    assert "T" in j["last_edited_time"]
    # Round-trips through json
    import json as _json
    _json.dumps(j)  # would raise if non-serializable
