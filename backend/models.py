"""Shared data models for the Swarm multi-agent system.

`AgentResult` is the contract every sub-agent returns. `Report` is the
structured output produced by the synthesis agent and shipped to the client.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Sub-agent contract
# --------------------------------------------------------------------------- #
@dataclass
class AgentResult:
    """The uniform contract returned by every specialist sub-agent.

    A timed-out or failed agent still returns an instance of this class with
    ``confidence == 0.0`` so the orchestrator never has to special-case
    missing results.
    """

    agent_name: str
    findings: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0–1.0
    elapsed_ms: int = 0
    error: str | None = None  # populated on timeout / failure

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def ok(self) -> bool:
        return self.error is None and self.confidence > 0.0


# --------------------------------------------------------------------------- #
# Synthesis output (validated, serialised to the client)
# --------------------------------------------------------------------------- #
class Citation(BaseModel):
    n: int = Field(..., description="1-based citation index used in the report body")
    title: str = ""
    url: str = ""
    source_agent: str = ""


class Report(BaseModel):
    summary: str = ""
    verdict: str = ""  # short chip text, e.g. "Migrate with caveats"
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence_overall: float = 0.0

    # Telemetry attached by the orchestrator (not produced by the LLM).
    agents: list[dict[str, Any]] = Field(default_factory=list)
    elapsed_ms_total: int = 0
    elapsed_ms_sequential_estimate: int = 0


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class QueryResponse(BaseModel):
    session_id: str
