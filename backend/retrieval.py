"""Shared retrieval helpers: web search (DuckDuckGo) and page fetching.

These are deliberately framework-free. The DuckDuckGo library is synchronous,
so we run it inside ``asyncio.to_thread`` to avoid blocking the event loop while
the five agents fan out concurrently.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from . import config


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


def _ddg_search_sync(query: str, max_results: int) -> list[SearchHit]:
    """Blocking DuckDuckGo text search. Imported lazily so the module loads
    even if the optional dependency is missing in a given environment."""
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except ImportError:  # pragma: no cover - dependency always present in prod
        try:
            # The library was renamed to `ddgs`; support both.
            from ddgs import DDGS  # type: ignore
        except ImportError:
            return []

    hits: list[SearchHit] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                hits.append(
                    SearchHit(
                        title=(r.get("title") or "").strip(),
                        url=(r.get("href") or r.get("url") or "").strip(),
                        snippet=(r.get("body") or "").strip(),
                    )
                )
    except Exception:
        # Rate limits / transient network errors → empty list, agent degrades.
        return hits
    return hits


async def web_search(query: str, max_results: int | None = None) -> list[SearchHit]:
    n = max_results or config.MAX_SEARCH_RESULTS
    return await asyncio.to_thread(_ddg_search_sync, query, n)


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
