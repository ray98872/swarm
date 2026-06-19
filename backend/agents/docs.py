"""Docs Agent — scrapes official documentation relevant to the question.

Strategy: search specifically for official docs (biasing the query toward
documentation domains), then fetch and de-tag the top pages with
httpx + BeautifulSoup before extraction. Official docs are the most
authoritative source, so a successful scrape earns a confidence floor.
"""

from __future__ import annotations

from .. import config
from ..models import AgentResult
from ..retrieval import fetch_many, web_search
from .base import BaseAgent
from .extract import extract_findings

# Domains we treat as "official documentation" for prioritisation.
_DOC_HINTS = (
    "docs.",
    "documentation",
    "/docs",
    "developer.",
    "readthedocs",
    "wiki",
    ".dev/",
    "manual",
)


class DocsAgent(BaseAgent):
    name = "docs"

    async def _run(self, question: str, context: dict | None = None) -> AgentResult:
        # Bias the search toward documentation pages.
        hits = await web_search(
            f"{question} official documentation docs", max_results=config.MAX_SEARCH_RESULTS
        )
        if not hits:
            return AgentResult(agent_name=self.name, confidence=0.0)

        # Prefer doc-like URLs, then fall back to the rest.
        doc_like = [h for h in hits if any(k in h.url.lower() for k in _DOC_HINTS)]
        ordered = doc_like + [h for h in hits if h not in doc_like]
        target_urls = [h.url for h in ordered if h.url][:3]

        pages = await fetch_many(target_urls, max_chars=5000)
        corpus_parts: list[str] = []
        used_urls: list[str] = []
        for url, text in pages:
            if text:
                corpus_parts.append(f"SOURCE: {url}\n{text}")
                used_urls.append(url)

        # Fall back to snippets if nothing scraped cleanly.
        if not corpus_parts:
            corpus_parts = [f"{h.title}\n{h.snippet}\n({h.url})" for h in ordered[:4]]
            used_urls = [h.url for h in ordered if h.url][:4]

        corpus = "\n\n".join(corpus_parts)
        findings, llm_conf = await extract_findings(
            role="official documentation specialist",
            question=question,
            corpus=corpus,
        )
        confidence = max(llm_conf, self._confidence_from(findings, len(used_urls)))
        return AgentResult(
            agent_name=self.name,
            findings=findings,
            citations=used_urls[:5],
            confidence=confidence,
        )
