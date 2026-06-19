"""Shared LLM extraction step used by the retrieval agents.

Each agent gathers raw text (search snippets, scraped docs, forum threads) and
hands it to the fast model with a role-specific instruction. The model returns
a small JSON object: a list of concise factual findings and a self-assessed
confidence. Keeping this in one place keeps every agent's extraction
behaviour consistent.

Returns a third value — a short failure ``note`` (or ``None`` on success) — so
the agent can surface *why* it produced nothing (e.g. an LLM rate-limit error
vs. genuinely irrelevant sources) instead of failing silently.
"""

from __future__ import annotations

import logging

from .. import config
from ..llm import GroqError, extract_json

logger = logging.getLogger("swarm.extract")


_SYSTEM_TMPL = (
    "You are the {role} of a research swarm answering a technical comparison "
    "question. From the SOURCE MATERIAL, extract only concrete, verifiable "
    "findings that bear on the question. Each finding must be one short, "
    "self-contained sentence and must be grounded in the sources — never "
    "invent facts. Prefer numbers, version specifics, and concrete behaviours. "
    "Ignore any source that is a dictionary definition, grammar or word-usage "
    "explanation, or otherwise not about the specific technologies or products "
    "named in the question — treat such sources as irrelevant and do not extract "
    "findings from them. "
    "Return strict JSON: "
    '{{"findings": ["..."], "confidence": 0.0}} '
    "where confidence (0-1) reflects how well the sources actually answer the "
    "question. If the sources are empty or irrelevant, return an empty findings "
    "list and confidence 0."
)


async def extract_findings(
    *,
    role: str,
    question: str,
    corpus: str,
    max_findings: int = 5,
) -> tuple[list[str], float, str | None]:
    """Return (findings, confidence, note). note is None on success, else a
    short reason the extraction produced nothing."""
    if not corpus.strip():
        return [], 0.0, "no source material"

    system = _SYSTEM_TMPL.format(role=role)
    user = (
        f"QUESTION:\n{question}\n\n"
        f"SOURCE MATERIAL (may contain several sources concatenated):\n"
        f"{corpus[:12000]}\n\n"
        f"Return at most {max_findings} findings."
    )
    try:
        data = await extract_json(
            model=config.MODEL_FAST,
            system=system,
            user=user,
            max_tokens=700,
        )
    except GroqError as exc:
        # Surface + log: this is the failure that previously looked like a
        # mysterious "search" failure but is really an LLM/rate-limit error.
        logger.warning("extraction LLM error [%s]: %s", role[:24], exc)
        return [], 0.0, f"LLM error: {exc}"

    findings = data.get("findings") or []
    if not isinstance(findings, list):
        return [], 0.0, "malformed LLM output"
    findings = [str(f).strip() for f in findings if str(f).strip()][:max_findings]

    try:
        conf = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(conf, 0.95))

    note = None if findings else "no relevant findings in sources"
    return findings, conf, note
