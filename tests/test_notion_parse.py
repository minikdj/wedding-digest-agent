"""Test the Notion response normalizer against a fixture (no network)."""
import json
from datetime import date
from pathlib import Path

from helpers.notion import _normalize

FIXTURE = Path(__file__).parent / "fixtures" / "notion_response.json"


def test_normalize_fully_specified_task():
    data = json.loads(FIXTURE.read_text())
    task = _normalize(data["results"][0])
    assert task["id"] == "task-1"
    assert task["title"] == "Look into marriage license"
    assert task["status"] == "In progress"
    assert task["start_date"] == date(2026, 5, 18)
    assert task["due_date"] == date(2026, 5, 19)
    assert task["phase"] == ["This Week (5/19-22)"]
    assert task["owner"] == ["Both"]
    assert task["category"] == ["Logistics"]
    assert task["critical_path"] is True
    assert task["context"].startswith("Need to apply")
    assert task["source"] == "Carried from original"


def test_normalize_metadata_gap_task():
    data = json.loads(FIXTURE.read_text())
    task = _normalize(data["results"][1])
    assert task["status"] is None
    assert task["start_date"] is None
    assert task["due_date"] is None
    assert task["phase"] == []
    assert task["context"] == ""


def test_normalize_completed_task():
    data = json.loads(FIXTURE.read_text())
    task = _normalize(data["results"][2])
    assert task["status"] == "Done"
    assert task["critical_path"] is True
    assert task["last_edited_time"].tzinfo is not None
