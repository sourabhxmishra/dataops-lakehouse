"""Optional Slack notification for the data-quality gate.

Posts a message to a Slack **incoming webhook** if `SLACK_WEBHOOK_URL` is set; otherwise it's a
clean no-op, so CI stays green whether or not a webhook is configured. Dependency-free (stdlib
`urllib`) so CI needs no extra install.

Security: the URL is restricted to the Slack webhook host (`https://hooks.slack.com/`) so a
misconfigured secret can't be used to reach an arbitrary endpoint (SSRF), and any network error is
swallowed — a notification must never break the build.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SLACK_WEBHOOK_PREFIX = "https://hooks.slack.com/"


def notify(text: str, webhook: str | None = None) -> bool:
    """Post `text` to Slack. Returns True if sent, False if skipped (no/invalid webhook or error)."""
    url = (webhook or os.environ.get("SLACK_WEBHOOK_URL", "")).strip()
    if not url.startswith(SLACK_WEBHOOK_PREFIX):
        return False
    payload = json.dumps({"text": text}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=15).read()
        return True
    except (urllib.error.URLError, TimeoutError):
        return False
