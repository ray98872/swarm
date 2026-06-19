"""Shared retrieval helpers: web search (DuckDuckGo) and page fetching.

These are deliberately framework-free. The DuckDuckGo library is synchronous,
so we run it inside ``asyncio.to_thread`` to avoid blocking the event loop while
the five agents fan out concurrently.

Reliability note: four of the five agents call ``web_search`` and the swarm
fires them at the same instant. From a single (datacenter) IP that burst trips
DuckDuckGo's rate limiter, so we funnel all DDG calls through a module-level
semaphore — the agents still run in parallel, only the search *network call* is
serialised — and retry with backoff, rotating across the metasearch engines
(`ddgs` aggregates Bing, Brave, DuckDuckGo, Mojeek, Startpage and more).
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import httpx

from . import config

# Serialise search network calls to avoid burst rate-limiting (default: 1 at a time).
_DDG_SEM = asyncio.Semaphore(config.DDG_CONCURRENCY)
# ddgs 9.x is a metasearch lib. Keep the engine set small and fast: "auto" first,
# then a short two-engine fallback. A long fallback list multiplies latency on a
# weak query (each engine request can take up to the HTTP timeout), which is what
# pushed the benchmark agent past its budget. The web_search() deadline below is
# the real guard; this just keeps the common path quick and deterministic.
_DDG_BACKENDS = ("auto", "duckduckgo, bing")


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


def _import_ddgs():
    """Return the DDGS class from whichever package is installed (ddgs preferred)."""
    try:
        from ddgs import DDGS  # maintained successor to duckduckgo-search

        return DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # type: ignore

            return DDGS
        except ImportError:
            return None


def _to_hits(results) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for r in results or []:
        hits.append(
            SearchHit(
                title=(r.get("title") or "").strip(),
                url=(r.get("href") or r.get("url") or "").strip(),
                snippet=(r.get("body") or "").strip(),
            )
        )
    return hits


def _ddg_search_sync(query: str, max_results: int) -> list[SearchHit]:
    """Blocking metasearch (ddgs), trying each backend group until one yields hits."""
    DDGS = _import_ddgs()
    if DDGS is None:  # pragma: no cover - dependency present in prod
        return []

    try:
        client = DDGS(timeout=int(config.HTTP_TIMEOUT_S))
    except TypeError:  # very old signature with no timeout kwarg
        client = DDGS()

    for backend in _DDG_BACKENDS:
        try:
            # ddgs 9.x accepts `backend=` (engine name, comma-list, or "auto").
            results = client.text(query, max_results=max_results, backend=backend)
        except TypeError:
            # Fallback for an older library signature with no `backend` kwarg.
            try:
                results = client.text(query, max_results=max_results)
            except Exception:
                continue
        except Exception:
            # Rate limit / transient error → try the next backend group.
            continue
        hits = _to_hits(results)
        if hits:
            return hits
    return []


async def web_search(query: str, max_results: int | None = None) -> list[SearchHit]:
    """Throttled, retrying, time-bounded metasearch.

    Hard-capped at ``SEARCH_TIMEOUT_S`` total wall-clock across all retries, so a
    slow metasearch can never eat an agent's whole budget. Returns [] if the cap
    is hit or every attempt comes back empty (the agent then degrades cleanly).
    """
    n = max_results or config.MAX_SEARCH_RESULTS
    loop = asyncio.get_event_loop()
    deadline = loop.time() + config.SEARCH_TIMEOUT_S
    async with _DDG_SEM:
        hits: list[SearchHit] = []
        for attempt in range(config.DDG_RETRIES):
            remaining = deadline - loop.time()
            if remaining <= 0.5:
                break
            try:
                hits = await asyncio.wait_for(
                    asyncio.to_thread(_ddg_search_sync, query, n), timeout=remaining
                )
            except asyncio.TimeoutError:
                break  # search budget exhausted — degrade rather than hang
            if hits:
                return hits
            # Backoff with jitter, but never sleep past the deadline.
            nap = min(0.7 * (attempt + 1) + random.random() * 0.4, max(0.0, deadline - loop.time()))
            if nap > 0:
                await asyncio.sleep(nap)
        return hits


async def fetch_text(url: str, max_chars: int = 6000) -> str:
    """Fetch a URL and return a roughly de-tagged text body, truncated.

    BeautifulSoup is used to strip markup. Failures return an empty string so a
    single dead link never breaks an agent.
    """
    try:
        async with httpx.AsyncClient(
            timeout=config.HTTP_TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": config.USER_AGENT},
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200 or "text/html" not in resp.headers.get(
                "content-type", ""
            ):
                # Non-HTML (e.g. PDF) — return raw text best-effort.
                if resp.status_code == 200:
                    return resp.text[:max_chars]
                return ""
            html = resp.text
    except httpx.HTTPError:
        return ""

    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:max_chars]
    except ImportError:  # pragma: no cover
        return html[:max_chars]


async def fetch_many(urls: list[str], max_chars: int = 4000) -> list[tuple[str, str]]:
    """Fetch several URLs concurrently. Returns (url, text) pairs (text may be '')."""
    tasks = [fetch_text(u, max_chars=max_chars) for u in urls]
    texts = await asyncio.gather(*tasks, return_exceptions=True)
    out: list[tuple[str, str]] = []
    for url, t in zip(urls, texts):
        out.append((url, t if isinstance(t, str) else ""))
    return out
