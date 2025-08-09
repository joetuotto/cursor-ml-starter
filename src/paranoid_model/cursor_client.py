import json
import os
import time
from typing import Any, Dict, Optional

import requests

DEFAULT_MODEL = os.getenv("CURSOR_MODEL", "gpt-5")
API_BASE = os.getenv("CURSOR_API_BASE", "https://api.cursor.sh/v1")
API_KEY = os.getenv("CURSOR_API_KEY")


class CursorError(RuntimeError): ...


def call_cursor_gpt5(
    *,
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 2200,
    seed: int = 42,
    retries: int = 2,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Calls Cursor's GPT-5-compatible chat endpoint and returns parsed JSON content.
    Expects the model to return a single JSON object in the message content.
    """
    if not API_KEY:
        raise CursorError("Missing CURSOR_API_KEY")

    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "seed": seed,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    backoffs = [2, 5]
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code >= 400:
                raise CursorError(f"HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()

            content: Optional[str] = None
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                content = msg.get("content")
            if not content:
                content = data.get("content") or data.get("output")
            if not content:
                raise CursorError("Empty content from model")

            return json.loads(content)
        except (requests.RequestException, ValueError, CursorError):
            if attempt > (retries + 1):
                raise
            time.sleep(backoffs[min(attempt - 1, len(backoffs) - 1)])
