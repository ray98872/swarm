"""Community Agent — real-world developer sentiment.

Primary source: the Hacker News Algolia search API (free, no auth). We pull the
most relevant stories/comments and combine them with a DuckDuckGo pass biased
toward discussion sites (Reddit, forums). The goal is lived experience and
gotchas, not marketing copy.
"""

from __future__ import annotations

import httpx

from .. import config
from ..models import AgentResult
from ..retrieval import web_search
from .base import BaseAgent
from .extract import extract_findings

HN_API = "https://hn.algolia.com/api/v1/search"


class CommunityAgent(BaseAgent):
    name = "community"

    async def _hn(self, question: str) -> tuple[list[str], list[str]]:
        """Return (text_blocks, urls) from Hacker News."""
        params = {"query": question, "tags": "(story,comment)", "hitsPerPage": 8}
        try:
            async with httpx.AsyncClient(
                timeout=config.HTTP_TIMEOUT_S,
                headers={"User-Agent": config.USER_AGENT},
            ) as client:
                resp = await client.get(HN_API, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            return [], []

        blocks: list[str] = []
        urls: list[str] = []
        for hit in data.get("hits", []):
            title = hit.get("title") or hit.get("story_title") or ""
            text = (hit.get("comment_text") or hit.get("story_text") or "").strip()
            points = hit.get("points")
            obj_id = hit.get("objectID")
            body = " ".join(f"{title} {text}".split())
            if not body:
                continue
            tag = f" (HN, {points} pts)" if points else " (HN)"
            blocks.append(body[:800] + tag)
            if obj_id:
                urls.append(f"https://news.ycombinator.com/item?id={obj_id}")
        return blocks, urls

    async def _run(self, question: str, context: dict | None = None) -> AgentResult:
        hn_blocks, hn_urls = await self._hn(question)

        ddg_hits = await web_search(
            f"{question} reddit OR forum developer experience opinion",
            max_results=config.MAX_SEARCH_RESULTS,
        )
        ddg_blocks = [f"{h.title}\n{h.snippet}" for h in ddg_hits if h.snippet]
        ddg_urls = [h.url for h in ddg_hits if h.url]

        if not hn_blocks and not ddg_blocks:
            return AgentResult(agent_name=self.name, confidence=0.0)

        corpus = "\n\n".join(hn_blocks + ddg_blocks)
        findings, llm_conf = await extract_findings(
            role="developer community sentiment specialist (capture real-world "
            "experiences, gotchas, migration pain, and consensus or disagreement)",
            question=question,
            corpus=corpus,
        )
        citations = (hn_urls + ddg_urls)[:5]
        confidence = max(
            llm_conf, self._confidence_from(findings, len(hn_blocks) + len(ddg_blocks))
        )
        return AgentResult(
            agent_name=self.name,
            findings=findings,
            citations=citations,
            confidence=confidence,
        )
