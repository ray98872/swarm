"""Custom async orchestration — the heart of the swarm.

Star topology: one orchestrator dispatches all five specialist sub-agents
simultaneously with ``asyncio.gather``; results flow back to a single synthesis
step. No LangGraph, no CrewAI — just asyncio.

The orchestrator is an async generator that *yields events* as work progresses.
The FastAPI layer turns those events into an SSE stream. Decoupling event
generation from transport keeps the orchestration logic testable in isolation.
"""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator

from .agents import SUB_AGENTS
from .agents.base import BaseAgent
from .agents.synthesis import synthesize
from .models import AgentResult, Report


class Event(dict):
    """A simple typed-ish event: {"type": ..., "data": {...}}."""

    def __init__(self, type_: str, **data):
        super().__init__(type=type_, data=data)


async def _run_and_announce(
    agent: BaseAgent,
    question: str,
    queue: asyncio.Queue,
) -> AgentResult:
    """Run one agent, pushing start/done events onto the shared queue.

    Because all agents share one queue, the orchestrator can emit events in the
    real order work completes — fast agents report ``agent_done`` first, which
    is exactly what the live UI shows.
    """
    await queue.put(Event("agent_start", agent=agent.name))
    result = await agent.run(question)
    await queue.put(
        Event(
            "agent_done",
            agent=agent.name,
            confidence=result.confidence,
            elapsed_ms=result.elapsed_ms,
            findings_count=len(result.findings),
            ok=result.ok,
            error=result.error,
        )
    )
    return result


async def run_swarm(question: str) -> AsyncIterator[Event]:
    """Drive the full pipeline, yielding events suitable for an SSE stream.

    Guarantees: a ``report_ready`` (or ``error``) event is always emitted, even
    if every agent fails — the client never waits forever.
    """
    t0 = time.perf_counter()
    agents = [cls() for cls in SUB_AGENTS]
    queue: asyncio.Queue = asyncio.Queue()

    # Fan out: launch every agent concurrently.
    tasks = [
        asyncio.create_task(_run_and_announce(a, question, queue)) for a in agents
    ]
    # gather() already returns an awaitable Future aggregating the tasks.
    gather_task = asyncio.gather(*tasks, return_exceptions=True)

    # Drain the event queue in real time until all agent tasks settle.
    pending = len(tasks)
    started = 0
    while pending > 0 or not queue.empty():
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.25)
            yield event
            if event["type"] == "agent_done":
                pending -= 1
            elif event["type"] == "agent_start":
                started += 1
        except asyncio.TimeoutError:
            if gather_task.done() and queue.empty():
                break

    results: list[AgentResult] = await gather_task
    # asyncio.gather(return_exceptions=True) may surface raw exceptions; coerce.
    clean: list[AgentResult] = []
    for agent, res in zip(agents, results):
        if isinstance(res, AgentResult):
            clean.append(res)
        else:
            clean.append(
                AgentResult(agent_name=agent.name, confidence=0.0, error=str(res))
            )

    # Synthesis — runs even if 1–2 sub-agents failed (graceful degradation).
    yield Event("synthesis_start")
    report: Report = await synthesize(question, clean)

    # Attach telemetry: parallel wall-clock vs. naive sequential estimate.
    elapsed_total = int((time.perf_counter() - t0) * 1000)
    sequential_estimate = sum(r.elapsed_ms for r in clean)
    report.agents = [r.to_dict() for r in clean]
    report.elapsed_ms_total = elapsed_total
    report.elapsed_ms_sequential_estimate = sequential_estimate

    yield Event("report_ready", report=report.model_dump())


async def run_swarm_collect(question: str) -> Report:
    """Convenience: run the whole pipeline and return just the final Report.

    Used by the CLI / tests where streaming isn't needed.
    """
    report: Report | None = None
    async for event in run_swarm(question):
        if event["type"] == "report_ready":
            report = Report(**event["data"]["report"])
    assert report is not None  # run_swarm always emits report_ready
    return report
