"""Benchmark Agent — finds and extracts performance / benchmark data.

Searches for benchmark-flavoured articles, scrapes the most promising ones, and
asks the model to pull out quantitative performance claims (throughput,
latency, ops/sec, memory, percentage deltas). Numbers are the goal here.
"""

from __future__ import annotations

from .. import config
from ..models import AgentResult
from ..retrieval import fetch_many, web_search
from .base import BaseAgent
from .extract import extract_findings


class BenchmarkAgent(BaseAgent):
    name = "benchmark"

    async def _run(self, question: str, context: dict | None = None) -> AgentResult:
        # ONE lightly-qualified search. A heavier "benchmark throughput latency
        # comparison" query returns little for niche topics, which used to
        # trigger retries + a second fallback search and push this agent past its
        # timeout. A single reliable search keeps it inside budget; the
        # benchmark-focused extraction below applies the performance lens to the
        # full fetched pages.
        hits = await web_search(
            f"{question} performance",
            max_results=config.MAX_SEARCH_RESULTS,
        )
        if not hits:
            return AgentResult(agent_name=self.name, confidence=0.0, error="no search results")

        target_urls = [h.url for h in hits if h.url][:3]
        pages = await fetch_many(target_urls, max_chars=5000)

        corpus_parts: list[str] = []
        used_urls: list[str] = []
        for url, text in pages:
            if text:
                corpus_parts.append(f"SOURCE: {url}\n{text}")
                used_urls.append(url)
        if not corpus_parts:
            corpus_parts = [f"{h.title}\n{h.snippet}\n({h.url})" for h in hits[:4]]
            used_urls = [h.url for h in hits if h.url][:4]

        corpus = "\n\n".join(corpus_parts)
        findings, llm_conf, note = await extract_findings(
            role="performance benchmarking specialist (focus on concrete numbers, "
            "throughput, latency, memory, and measured deltas)",
            question=question,
            corpus=corpus,
        )
        confidence = max(llm_conf, self._confidence_from(findings, len(used_urls)))
        return AgentResult(
            agent_name=self.name,
            findings=findings,
            citations=used_urls[:5],
            confidence=confidence,
            error=note,
        )
