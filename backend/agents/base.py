"""Abstract base class for every specialist sub-agent.

Subclasses implement ``_run`` (the real work). ``run`` wraps it with timing and
an enforced timeout, guaranteeing that *something* — an ``AgentResult`` — always
comes back, even on failure. This is what lets the orchestrator fan out with
``asyncio.gather`` and never hang.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod

from ..config import AGENT_TIMEOUT_S
from ..models import AgentResult


class BaseAgent(ABC):
    #: Stable identifier surfaced to the frontend (matches SSE event payloads).
    name: str = "base"

    def __init__(self, timeout_s: float = AGENT_TIMEOUT_S) -> None:
        self.timeout_s = timeout_s

    @abstractmethod
    async def _run(self, question: str, context: dict | None = None) -> AgentResult:
        """Do the actual retrieval + extraction. Must return an AgentResult."""
        raise NotImplementedError

    async def run(self, question: str, context: dict | None = None) -> AgentResult:
        """Public entry point: enforces timeout + timing, never raises."""
        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self._run(question, context), timeout=self.timeout_s
            )
            result.elapsed_ms = int((time.perf_counter() - start) * 1000)
            return result
        except asyncio.TimeoutError:
            return AgentResult(
                agent_name=self.name,
                findings=[],
                citations=[],
                confidence=0.0,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
                error=f"timed out after {self.timeout_s:.0f}s",
            )
        except Exception as exc:  # defensive: any agent bug degrades, not crashes
            return AgentResult(
                agent_name=self.name,
                findings=[],
                citations=[],
                confidence=0.0,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
                error=f"{type(exc).__name__}: {exc}",
            )

    # ---- helpers shared by subclasses ------------------------------------ #
    @staticmethod
    def _confidence_from(findings: list[str], hits_used: int) -> float:
        """Heuristic confidence: scales with evidence gathered, capped at 0.95.

        The synthesis model gets the raw findings anyway; this score is a
        lightweight signal for the UI and for weighting in the merge prompt.
        """
        if not findings:
            return 0.0
        base = min(len(findings) / 5.0, 1.0) * 0.6
        corroboration = min(hits_used / 4.0, 1.0) * 0.35
        return round(min(base + corroboration, 0.95), 2)
