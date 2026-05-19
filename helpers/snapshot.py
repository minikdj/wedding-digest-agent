from __future__ import annotations

import base64
import json
import os
from typing import Any

import requests

SNAPSHOTS_DIR = "snapshots"
API_ROOT = "https://api.github.com"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo() -> str:
    return os.environ["GITHUB_REPO"]


def _list_snapshot_files() -> list[str]:
    """Returns sorted snapshot filenames (oldest first)."""
    url = f"{API_ROOT}/repos/{_repo()}/contents/{SNAPSHOTS_DIR}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    items = resp.json()
    names = [it["name"] for it in items if it["type"] == "file" and it["name"].endswith(".json")]
    names.sort()
    return names


def _read_snapshot(filename: str) -> dict[str, Any]:
    url = f"{API_ROOT}/repos/{_repo()}/contents/{SNAPSHOTS_DIR}/{filename}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    content = base64.b64decode(payload["content"]).decode("utf-8")
    return json.loads(content)


def load_latest() -> dict[str, Any] | None:
    files = _list_snapshot_files()
    if not files:
        return None
    return _read_snapshot(files[-1])


def load_recent(days: int = 14) -> list[dict[str, Any]]:
    files = _list_snapshot_files()[-days:]
    return [_read_snapshot(f) for f in files]


def save_today(snapshot: dict[str, Any]) -> None:
    """Write snapshots/<date>.json to the configured repo. Overwrites if present."""
    filename = f"{snapshot['date']}.json"
    path = f"{SNAPSHOTS_DIR}/{filename}"
    url = f"{API_ROOT}/repos/{_repo()}/contents/{path}"

    # Look up existing file's sha if present (required for update)
    sha: str | None = None
    head = requests.get(url, headers=_headers(), timeout=30)
    if head.status_code == 200:
        sha = head.json()["sha"]
    elif head.status_code != 404:
        head.raise_for_status()

    body = base64.b64encode(
        json.dumps(snapshot, indent=2, sort_keys=True).encode("utf-8")
    ).decode("ascii")

    payload: dict = {
        "message": f"snapshot: {snapshot['date']}",
        "content": body,
        "committer": {"name": "wedding-digest-agent", "email": "agent@noreply.local"},
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
