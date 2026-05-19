from __future__ import annotations

import os
import time
from datetime import date, datetime
from typing import Any

import requests

NOTION_VERSION = "2026-03-11"
DATA_SOURCE_ID = "72b92312-f2da-4785-8be9-f33cabf0e388"
BASE_URL = f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query"
MAX_RETRIES = 3


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _post_with_retry(payload: dict) -> dict:
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        resp = requests.post(BASE_URL, headers=_headers(), json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", 2 ** attempt))
            time.sleep(wait)
            continue
        if 500 <= resp.status_code < 600:
            time.sleep(2 ** attempt)
            last_err = RuntimeError(f"Notion {resp.status_code}: {resp.text[:200]}")
            continue
        resp.raise_for_status()
    raise RuntimeError(f"Notion fetch failed after {MAX_RETRIES} retries: {last_err}")


def _parse_date(prop: dict) -> date | None:
    d = prop.get("date")
    if not d or not d.get("start"):
        return None
    return date.fromisoformat(d["start"][:10])


def _parse_multi_select(prop: dict) -> list[str]:
    return [opt["name"] for opt in prop.get("multi_select") or []]


def _parse_status(prop: dict) -> str | None:
    s = prop.get("status")
    return s["name"] if s else None


def _parse_select(prop: dict) -> str | None:
    s = prop.get("select")
    return s["name"] if s else None


def _parse_rich_text(prop: dict) -> str:
    return "".join(rt.get("plain_text", "") for rt in prop.get("rich_text") or [])


def _parse_title(prop: dict) -> str:
    return "".join(rt.get("plain_text", "") for rt in prop.get("title") or [])


def _normalize(page: dict) -> dict[str, Any]:
    props = page["properties"]
    return {
        "id": page["id"],
        "url": page["url"],
        "last_edited_time": datetime.fromisoformat(
            page["last_edited_time"].replace("Z", "+00:00")
        ),
        "title": _parse_title(props.get("Task", {})),
        "status": _parse_status(props.get("Status", {})),
        "start_date": _parse_date(props.get("Start Date", {})),
        "due_date": _parse_date(props.get("Due Date", {})),
        "phase": _parse_multi_select(props.get("Phase", {})),
        "owner": _parse_multi_select(props.get("Owner", {})),
        "category": _parse_multi_select(props.get("Category", {})),
        "critical_path": props.get("Critical Path", {}).get("checkbox", False),
        "context": _parse_rich_text(props.get("Context", {})),
        "source": _parse_select(props.get("Source", {})),
    }


def fetch_all_tasks() -> list[dict[str, Any]]:
    results: list[dict] = []
    payload: dict = {"page_size": 100}
    while True:
        data = _post_with_retry(payload)
        results.extend(data["results"])
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return [_normalize(p) for p in results]
