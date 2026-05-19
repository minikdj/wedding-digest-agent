from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from .digest import task_to_jsonable

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system.md"

EMIT_TOOL = {
    "name": "emit_digest",
    "description": "Emit the daily digest email content. Call this exactly once.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "Email subject line."},
            "html": {"type": "string", "description": "HTML email body, inline styles only."},
            "text": {"type": "string", "description": "Plain-text email body, same content."},
        },
        "required": ["subject", "html", "text"],
        "additionalProperties": False,
    },
}


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text()


def compose_digest(
    *,
    today: date,
    phase: str,
    days_left: int,
    tasks: list[dict],
    counts: dict[str, int],
    prior_snapshot: dict | None,
    recent_snapshots: list[dict],
) -> dict[str, str]:
    """Single Claude call that returns {subject, html, text}.

    All counts and date math are pre-computed in Python; Claude's job is
    bucketing the tasks per the strict template, writing the prose, and
    formatting the email body.
    """
    payload: dict[str, Any] = {
        "today": today.isoformat(),
        "phase": phase,
        "days_until_wedding": days_left,
        "counts": counts,
        "prior_snapshot": prior_snapshot,
        "recent_snapshots": recent_snapshots,
        "tasks": [task_to_jsonable(t) for t in tasks],
    }

    client = Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_load_system_prompt(),
        tools=[EMIT_TOOL],
        tool_choice={"type": "tool", "name": "emit_digest"},
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )

    for block in resp.content:
        if block.type == "tool_use" and block.name == "emit_digest":
            return dict(block.input)

    raise RuntimeError(
        f"Claude did not call emit_digest. stop_reason={resp.stop_reason!r}"
    )
