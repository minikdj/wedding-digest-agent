from __future__ import annotations

import os

import resend


def send(subject: str, html: str, text: str | None = None) -> str:
    resend.api_key = os.environ["RESEND_API_KEY"]
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
    recipient = os.environ["RECIPIENT_EMAIL"]

    params: dict = {
        "from": f"Wedding Digest <{sender}>",
        "to": [recipient],
        "subject": subject,
        "html": html,
    }
    if text:
        params["text"] = text

    resp = resend.Emails.send(params)
    return resp["id"]
