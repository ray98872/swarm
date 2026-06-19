"""Thin async Groq client (OpenAI-compatible chat completions endpoint).

We talk to Groq over plain HTTP via httpx rather than pulling in the official
SDK: it keeps the dependency surface small, gives us precise timeout control,
and is trivial to mock in tests. Groq's API is OpenAI-compatible, so the
request/response shapes match the familiar `chat/completions` schema.

Resilience: all five sub-agents fire their extraction calls at almost the same
instant, and the Groq free tier caps requests-per-minute. Bursting straight
into that limit returns HTTP 429 for the unlucky callers. So this client (a)
caps how many Groq requests run concurrently via a semaphore, and (b) retries
429/5xx responses with backoff, honouring any ``Retry-After`` header. Errors are
logged so the real failure reason shows up in the server logs instead of being
silently swallowed upstream.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any

import httpx

from . import config

logger = logging.getLogger("swarm.llm")

# Cap concurrent Groq requests so the 5 agents don't all hit the per-minute
# limit in the same instant.
_GROQ_SEM = asyncio.Semaphore(config.GROQ_CONCURRENCY)


class GroqError(RuntimeError):
    pass


def _retry_after_seconds(resp: httpx.Response, attempt: int) -> float:
    """Honour Retry-After if present, else exponential backoff with jitter."""
    ra = resp.headers.get("retry-after")
    if ra:
        try:
            return min(float(ra), 8.0)
        except ValueError:
            pass
    return min(0.6 * (2 ** attempt) + random.random() * 0.4, 8.0)


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

    Retries on 429/5xx; raises ``GroqError`` only once retries are exhausted or
    on a non-recoverable error, so callers can degrade gracefully.
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

    last_err = "unknown error"
    async with _GROQ_SEM:
        for attempt in range(config.GROQ_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout or config.LLM_HTTP_TIMEOUT_S
                ) as client:
                    resp = await client.post(url, headers=headers, json=payload)
            except httpx.HTTPError as exc:
                last_err = f"network error: {exc}"
                logger.warning("groq %s attempt %d/%d: %s", model, attempt + 1, config.GROQ_RETRIES, last_err)
                await asyncio.sleep(_retry_after_seconds_default(attempt))
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, json.JSONDecodeError) as exc:
                    raise GroqError(f"unexpected Groq response shape: {exc}") from exc

            # Retryable: rate limit (429) or transient server error (5xx).
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = _retry_after_seconds(resp, attempt)
                last_err = f"HTTP {resp.status_code} (rate-limited)" if resp.status_code == 429 else f"HTTP {resp.status_code}"
                logger.warning(
                    "groq %s attempt %d/%d: %s — backing off %.1fs",
                    model, attempt + 1, config.GROQ_RETRIES, last_err, wait,
                )
                await asyncio.sleep(wait)
                continue

            # Non-retryable (e.g. 400/401) — fail fast.
            raise GroqError(f"Groq returned {resp.status_code}: {resp.text[:300]}")

    raise GroqError(f"Groq call failed after {config.GROQ_RETRIES} attempts: {last_err}")


def _retry_after_seconds_default(attempt: int) -> float:
    return min(0.6 * (2 ** attempt) + random.random() * 0.4, 8.0)


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
