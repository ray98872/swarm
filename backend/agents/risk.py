"""Risk Agent — gaps, contradictions, caveats, and failure modes.

Design note: to preserve the pure star fan-out (all five agents run
concurrently via ``asyncio.gather``), the Risk agent does its *own* targeted
retrieval — it searches explicitly for downsides, breaking changes, migration
pain, and known issues, rather than waiting on its peers. Cross-agent
contradiction resolution then happens in the synthesis step, which is the one
place that sees every agent's output at once.

The agent also accepts an optional ``context`` dict carrying peer findings; if
the orchestrator ever runs it in a second wave, it will fold those in. In the
default parallel topology that context is absent, and the agent stands alone.
"""

from __future__ import annotations

from .. import config
from ..models import AgentResult
from ..retrieval import web_search
from .base import BaseAgent
from .extract import extract_findings


class RiskAgent(BaseAgent):
    name = "risk"

    async def _run(self, question: str, context: dict | None = None) -> AgentResult:
        hits = await web_search(
            f"{question} risks problems downsides breaking changes caveats migration issues",
            max_results=config.MAX_SEARCH_RESULTS,
        )

        corpus_parts = [f"{h.title}\n{h.snippet}\n({h.url})" for h in hits if h.snippet]
        citations = [h.url for h in hits if h.url][:5]

        # If peer findings are supplied (non-default topology), let the model
        # reason over them for contradictions and gaps too.
        peer_findings = (context or {}).get("peer_findings") if context else None
        if peer_findings:
            corpus_parts.append(
                "PEER AGENT FINDINGS (look for contradictions, gaps, unverified "
                "claims):\n" + "\n".join(f"- {f}" for f in peer_findings)
            )

        if not corpus_parts:
            return AgentResult(agent_name=self.name, confidence=0.0)

        corpus = "\n\n".join(corpus_parts)
        findings, llm_conf = await extract_findings(
            role="risk and caveat analyst (enumerate concrete risks, gaps, "
            "contradictions, breaking changes, and conditions under which the "
            "answer flips)",
            question=question,
            corpus=corpus,
        )
        confidence = max(llm_conf, self._confidence_from(findings, len(hits)))
        return AgentResult(
            agent_name=self.name,
            findings=findings,
            citations=citations,
            confidence=confidence,
        )
