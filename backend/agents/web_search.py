"""Web Search Agent — broad, current coverage of the question.

Runs a DuckDuckGo search (no API key, no cost), pulls the top snippets, and
extracts the most relevant findings. This is the swarm's generalist.
"""

from __future__ import annotations

from .. import config
from ..models import AgentResult
from ..retrieval import web_search
from .base import BaseAgent
from .extract import extract_findings


class WebSearchAgent(BaseAgent):
    name = "web_search"

    async def _run(self, question: str, context: dict | None = None) -> AgentResult:
        hits = await web_search(question, max_results=config.MAX_SEARCH_RESULTS)
        if not hits:
            return AgentResult(agent_name=self.name, confidence=0.0)

        corpus = "\n\n".join(
            f"[{i+1}] {h.title}\n{h.snippet}\n({h.url})" for i, h in enumerate(hits)
        )
        findings, llm_conf = await extract_findings(
            role="web search specialist",
            question=question,
            corpus=corpus,
        )
        citations = [h.url for h in hits if h.url][:5]
        confidence = max(llm_conf, self._confidence_from(findings, len(hits)))
        return AgentResult(
            agent_name=self.name,
            findings=findings,
            citations=citations,
            confidence=confidence,
        )
