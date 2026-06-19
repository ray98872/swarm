"""Thin async Groq client (OpenAI-compatible chat completions endpoint).

We talk to Groq over plain HTTP via httpx rather than pulling in the official
SDK: it keeps the dependency surface small, gives us precise timeout control,
and is trivial to mock in tests. Groq's API is OpenAI-compatible, so the
request/response shapes match the familiar `chat/completions` schema.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from . import config


class GroqError(RuntimeError):
    pass


async def chat(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1024,
    json_mode: bool = False,
    timeout: float | None = None,
) -> str:
    """Call Groq chat completions and return the assistant message content.

    Raises ``GroqError`` on any non-recoverable failure so callers can decide
    whether to degrade gracefully.
    """
    if not config.GROQ_API_KEY:
        raise GroqError("GROQ_API_KEY is not set")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{config.GROQ_BASE_URL}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=timeout or config.LLM_HTTP_TIMEOUT_S) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise GroqError(f"network error calling Groq: {exc}") from exc

    if resp.status_code != 200:
        raise GroqError(f"Groq returned {resp.status_code}: {resp.text[:300]}")

    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise GroqError(f"unexpected Groq response shape: {exc}") from exc


async def extract_json(
    *,
    model: str,
    system: str,
    user: str,
    timeout: float | None = None,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Run an LLM call in JSON mode and parse the result into a dict.

    Returns an empty dict if the model emits malformed JSON rather than raising,
    so a single bad extraction never takes down an agent.
    """
    content = await chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
        json_mode=True,
        timeout=timeout,
    )
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Best-effort: pull the first {...} block out of the text.
        start, end = content.find("{"), content.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}
