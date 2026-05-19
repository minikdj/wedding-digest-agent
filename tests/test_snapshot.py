"""Tests for snapshot helpers. Mocks GitHub Contents API."""
import base64
import json
from unittest.mock import patch

import pytest

from helpers import snapshot


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("GITHUB_REPO", "djm/wedding-digest-agent")


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def test_load_latest_returns_none_when_dir_missing():
    with patch("helpers.snapshot.requests.get") as mock_get:
        mock_get.return_value.status_code = 404
        assert snapshot.load_latest() is None


def test_load_latest_picks_newest_filename():
    listing = [
        {"name": "2026-05-18.json", "type": "file"},
        {"name": "2026-05-20.json", "type": "file"},
        {"name": "2026-05-19.json", "type": "file"},
        {"name": "README.md", "type": "file"},
    ]
    file_payload = {"content": _b64(json.dumps({"date": "2026-05-20", "done": 5}))}

    def side_effect(url, **_):
        m = type("R", (), {})()
        m.raise_for_status = lambda: None
        if url.endswith("/snapshots"):
            m.status_code = 200
            m.json = lambda: listing
        else:
            assert "2026-05-20.json" in url
            m.status_code = 200
            m.json = lambda: file_payload
        return m

    with patch("helpers.snapshot.requests.get", side_effect=side_effect):
        result = snapshot.load_latest()
        assert result == {"date": "2026-05-20", "done": 5}


def test_save_today_creates_new_file_when_absent():
    saved: dict = {}

    def get(url, **_):
        m = type("R", (), {})()
        m.status_code = 404
        m.raise_for_status = lambda: None
        return m

    def put(url, json=None, **_):
        saved["url"] = url
        saved["payload"] = json
        m = type("R", (), {})()
        m.status_code = 201
        m.raise_for_status = lambda: None
        return m

    with patch("helpers.snapshot.requests.get", side_effect=get), \
         patch("helpers.snapshot.requests.put", side_effect=put):
        snapshot.save_today({"date": "2026-05-18", "total": 75, "done": 1})

    assert saved["url"].endswith("/snapshots/2026-05-18.json")
    assert "sha" not in saved["payload"]
    decoded = json.loads(base64.b64decode(saved["payload"]["content"]))
    assert decoded["date"] == "2026-05-18"
    assert decoded["done"] == 1


def test_save_today_overwrites_with_sha_when_present():
    saved: dict = {}

    def get(url, **_):
        m = type("R", (), {})()
        m.status_code = 200
        m.raise_for_status = lambda: None
        m.json = lambda: {"sha": "abc123"}
        return m

    def put(url, json=None, **_):
        saved["payload"] = json
        m = type("R", (), {})()
        m.status_code = 200
        m.raise_for_status = lambda: None
        return m

    with patch("helpers.snapshot.requests.get", side_effect=get), \
         patch("helpers.snapshot.requests.put", side_effect=put):
        snapshot.save_today({"date": "2026-05-18", "total": 75})

    assert saved["payload"]["sha"] == "abc123"
