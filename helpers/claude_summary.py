from __future__ import annotations

import json
import re
import sys
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
            result = dict(block.input)
            if not result.get("subject"):
                raise RuntimeError(f"emit_digest returned no subject; keys={sorted(result)}")
            if not result.get("html"):
                raise RuntimeError(f"emit_digest returned no html; keys={sorted(result)}")
            if not result.get("text", "").strip():
                # Anthropic's tool-schema enforcement is best-effort; Claude
                # occasionally omits required fields. Derive text from html
                # so the digest still ships rather than crashing the run.
                sys.stderr.write(
                    "WARN: emit_digest missing 'text' field, deriving from html\n"
                )
                result["text"] = _html_to_text(result["html"])
            return result

    raise RuntimeError(
        f"Claude did not call emit_digest. stop_reason={resp.stop_reason!r}"
    )


_BLOCK_CLOSE_RE = re.compile(r"</(p|div|h[1-6]|li|pre)\s*>", re.I)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_BLANKS_RE = re.compile(r"\n{3,}")


def _html_to_text(html: str) -> str:
    """Best-effort fallback: convert HTML body to readable plain text.

    Only used when Claude omits the required `text` field. Not a general HTML
    sanitizer — the system prompt forbids HTML entities in the body, so we
    decode only the small allowed set.
    """
    s = _BR_RE.sub("\n", html)
    s = _BLOCK_CLOSE_RE.sub("\n", s)
    s = _TAG_RE.sub("", s)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                          ("&quot;", '"'), ("&nbsp;", " ")):
        s = s.replace(entity, char)
    s = _BLANKS_RE.sub("\n\n", s)
    return s.strip()
