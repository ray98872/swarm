"""Shared LLM extraction step used by the retrieval agents.

Each agent gathers raw text (search snippets, scraped docs, forum threads) and
hands it to the fast model with a role-specific instruction. The model returns
a small JSON object: a list of concise factual findings and a self-assessed
confidence. Keeping this in one place keeps every agent's extraction
behaviour consistent.
"""

from __future__ import annotations

from .. import config
from ..llm import GroqError, extract_json


_SYSTEM_TMPL = (
    "You are the {role} of a research swarm answering a technical comparison "
    "question. From the SOURCE MATERIAL, extract only concrete, verifiable "
    "findings that bear on the question. Each finding must be one short, "
    "self-contained sentence and must be grounded in the sources — never "
    "invent facts. Prefer numbers, version specifics, and concrete behaviours. "
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
) -> tuple[list[str], float]:
    """Return (findings, confidence). Empty/0.0 on any failure."""
    if not corpus.strip():
        return [], 0.0

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
    except GroqError:
        return [], 0.0

    findings = data.get("findings") or []
    if not isinstance(findings, list):
        return [], 0.0
    findings = [str(f).strip() for f in findings if str(f).strip()][:max_findings]

    try:
        conf = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(conf, 0.95))
    return findings, conf
