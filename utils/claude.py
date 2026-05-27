"""
Minimal Claude API client used by the in-app AI assistant.
"""
from __future__ import annotations

import json
from urllib import error, request


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def ask_claude(api_key: str, model: str, prompt: str, *, max_tokens: int = 800) -> str:
    if not api_key:
        raise ValueError("Claude API key is not configured")
    if not model:
        raise ValueError("Claude model is not configured")
    if not prompt.strip():
        raise ValueError("Prompt is empty")

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        raise RuntimeError(f"Claude request failed ({exc.code}): {body or exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError(f"Claude request failed: {exc}") from exc

    parts = []
    for block in response_data.get("content", []):
        if block.get("type") == "text" and block.get("text"):
            parts.append(block["text"])
    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("Claude returned no text response")
    return text