"""Synthesis Agent — merges all sub-agent results into one cited report.

Uses the larger model (llama-3.3-70b-versatile) because this is the step where
quality matters most: it has to weigh confidence, resolve contradictions across
agents, attach citations, and commit to a verdict. It degrades gracefully —
if only some agents succeeded, it synthesises from what's available and lowers
the overall confidence accordingly.
"""

from __future__ import annotations

from .. import config
from ..llm import GroqError, extract_json
from ..models import AgentResult, Citation, Report


_SYSTEM = (
    "You are the synthesis agent of a multi-agent research swarm. Five specialist "
    "agents (web search, official docs, benchmarks, community sentiment, risk) "
    "have each returned findings, citations, and a confidence score for a "
    "technical comparison question. Merge them into one decisive, balanced, "
    "well-cited report.\n\n"
    "Rules:\n"
    "- Ground every claim in the supplied findings; do not invent facts.\n"
    "- Weight higher-confidence agents more, but surface meaningful minority "
    "signals (especially from the risk agent).\n"
    "- Use inline citation markers like [1], [2] in pros/cons/risks/summary that "
    "refer to entries in the citations array.\n"
    "- The verdict is a SHORT chip (<= 6 words), e.g. 'Migrate, with caveats'.\n"
    "- confidence_overall (0-1) should reflect agreement across agents and how "
    "many agents succeeded.\n\n"
    "Return STRICT JSON with exactly these keys: summary (string), verdict "
    "(string), pros (string[]), cons (string[]), risks (string[]), citations "
    "(array of {n:int, title:string, url:string, source_agent:string}), "
    "confidence_overall (number)."
)


def _build_user_prompt(question: str, results: list[AgentResult]) -> str:
    blocks: list[str] = [f"QUESTION:\n{question}\n"]
    # Build a global, de-duplicated citation pool with stable numbering.
    citation_pool: list[tuple[str, str]] = []  # (url, agent)
    seen: set[str] = set()
    for r in results:
        for url in r.citations:
            if url and url not in seen:
                seen.add(url)
                citation_pool.append((url, r.agent_name))

    cite_lines = "\n".join(
        f"[{i+1}] {url}  (from {agent})" for i, (url, agent) in enumerate(citation_pool)
    )
    blocks.append("AVAILABLE CITATIONS (reuse these numbers in your markers):\n" + (cite_lines or "(none)"))

    for r in results:
        status = "OK" if r.ok else f"FAILED ({r.error or 'no findings'})"
        flist = "\n".join(f"  - {f}" for f in r.findings) or "  (no findings)"
        blocks.append(
            f"AGENT {r.agent_name} [{status}] confidence={r.confidence} "
            f"elapsed={r.elapsed_ms}ms\n{flist}"
        )

    ok_count = sum(1 for r in results if r.ok)
    blocks.append(
        f"\n{ok_count} of {len(results)} agents returned usable findings. "
        "If several failed, lower confidence_overall and note the gap."
    )
    return "\n\n".join(blocks)


def _fallback_report(question: str, results: list[AgentResult]) -> Report:
    """Deterministic report when the synthesis LLM is unavailable.

    Guarantees the pipeline still produces *something* citable rather than
    leaving the client hanging — important for the zero-cost demo and for the
    'never hang' SSE guarantee.
    """
    citations: list[Citation] = []
    n = 1
    seen: set[str] = set()
    all_findings: list[str] = []
    for r in results:
        all_findings.extend(r.findings)
        for url in r.citations:
            if url and url not in seen:
                seen.add(url)
                citations.append(Citation(n=n, title=url, url=url, source_agent=r.agent_name))
                n += 1
    ok = [r for r in results if r.ok]
    conf = round(sum(r.confidence for r in ok) / len(ok), 2) if ok else 0.0
    return Report(
        summary=(
            "Synthesis model unavailable — showing raw aggregated findings from "
            f"{len(ok)} of {len(results)} agents. "
            + (" ".join(all_findings[:6]))
        ),
        verdict="Inconclusive (no synthesis)",
        pros=[f for r in results if r.agent_name in ("web_search", "docs", "benchmark") for f in r.findings][:6],
        cons=[],
        risks=[f for f in next((r.findings for r in results if r.agent_name == "risk"), [])][:6],
        citations=citations,
        confidence_overall=conf,
    )


async def synthesize(question: str, results: list[AgentResult]) -> Report:
    if not config.has_groq():
        return _fallback_report(question, results)

    try:
        data = await extract_json(
            model=config.MODEL_SYNTH,
            system=_SYSTEM,
            user=_build_user_prompt(question, results),
            timeout=config.SYNTH_TIMEOUT_S,
            max_tokens=1800,
        )
    except GroqError:
        return _fallback_report(question, results)

    if not data:
        return _fallback_report(question, results)

    # Validate / coerce into the Report model, tolerating loose LLM output.
    try:
        raw_citations = data.get("citations") or []
        citations = []
        for i, c in enumerate(raw_citations):
            if isinstance(c, dict):
                citations.append(
                    Citation(
                        n=int(c.get("n", i + 1)),
                        title=str(c.get("title", "")),
                        url=str(c.get("url", "")),
                        source_agent=str(c.get("source_agent", "")),
                    )
                )
        report = Report(
            summary=str(data.get("summary", "")),
            verdict=str(data.get("verdict", "")),
            pros=[str(x) for x in (data.get("pros") or [])],
            cons=[str(x) for x in (data.get("cons") or [])],
            risks=[str(x) for x in (data.get("risks") or [])],
            citations=citations,
            confidence_overall=float(data.get("confidence_overall", 0.0) or 0.0),
        )
    except (TypeError, ValueError):
        return _fallback_report(question, results)

    # Ensure there's always at least the agents' citations available to the UI.
    if not report.citations:
        report = report.model_copy(update={"citations": _fallback_report(question, results).citations})
    return report
