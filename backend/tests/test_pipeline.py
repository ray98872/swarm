"""Pipeline tests that don't require a Groq key or live network.

Run from the repo root:  python -m backend.tests.test_pipeline
Verifies: agent timeout/degradation, orchestrator event ordering, the
"never hang" guarantee, synthesis fallback, and the FastAPI SSE endpoint.
"""

from __future__ import annotations

import asyncio

from .. import orchestrator as orch_mod
from ..agents.base import BaseAgent
from ..models import AgentResult, Report


# --- fake agents ------------------------------------------------------------
class FastOK(BaseAgent):
    name = "web_search"

    async def _run(self, q, context=None):
        await asyncio.sleep(0.05)
        return AgentResult(self.name, ["finding A", "finding B"], ["https://a.example"], 0.8)


class SlowOK(BaseAgent):
    name = "docs"

    async def _run(self, q, context=None):
        await asyncio.sleep(0.15)
        return AgentResult(self.name, ["doc finding"], ["https://docs.example"], 0.6)


class Boom(BaseAgent):
    name = "benchmark"

    async def _run(self, q, context=None):
        raise RuntimeError("synthetic explosion")


class TimesOut(BaseAgent):
    name = "community"

    def __init__(self):
        super().__init__(timeout_s=0.05)

    async def _run(self, q, context=None):
        await asyncio.sleep(1.0)  # exceeds the 0.05s timeout
        return AgentResult(self.name, ["never"], [], 0.9)


class EmptyOK(BaseAgent):
    name = "risk"

    async def _run(self, q, context=None):
        return AgentResult(self.name, ["risk: vendor lock-in"], ["https://risk.example"], 0.5)


FAKE_AGENTS = [FastOK, SlowOK, Boom, TimesOut, EmptyOK]


async def fake_synthesize(question, results):
    ok = [r for r in results if r.ok]
    return Report(
        summary=f"merged {len(ok)} ok agents",
        verdict="Proceed",
        pros=["p"],
        cons=["c"],
        risks=["r"],
        citations=[],
        confidence_overall=0.5,
    )


def _passed(name):
    print(f"  PASS  {name}")


async def test_base_agent_guarantees():
    # Boom -> error, confidence 0, but still an AgentResult.
    r = await Boom().run("q")
    assert isinstance(r, AgentResult) and r.confidence == 0.0 and r.error
    assert r.elapsed_ms >= 0
    _passed("BaseAgent converts exceptions into a degraded AgentResult")

    # TimesOut -> timeout error.
    r2 = await TimesOut().run("q")
    assert r2.confidence == 0.0 and "timed out" in (r2.error or "")
    _passed("BaseAgent enforces per-agent timeout")


async def test_orchestrator_events(monkeypatch_attrs):
    events = []
    async for ev in orch_mod.run_swarm("should I use X over Y?"):
        events.append(ev)

    types = [e["type"] for e in events]
    assert types.count("agent_start") == 5, types
    assert types.count("agent_done") == 5, types
    assert "synthesis_start" in types
    assert types[-1] == "report_ready", "report_ready must be the final event"
    _passed("orchestrator emits 5x start/done + synthesis_start + final report_ready")

    # Fast agent should finish before the slow one (real completion order).
    done_order = [e["data"]["agent"] for e in events if e["type"] == "agent_done"]
    assert done_order.index("web_search") < done_order.index("docs")
    _passed("agent_done events arrive in real completion order (fast before slow)")

    # Degradation: 3 ok (web_search, docs, risk), 2 failed (benchmark, community).
    report = events[-1]["data"]["report"]
    assert report["summary"] == "merged 3 ok agents"
    assert report["elapsed_ms_total"] > 0
    assert report["elapsed_ms_sequential_estimate"] >= report["elapsed_ms_total"]
    assert len(report["agents"]) == 5
    _passed("synthesis runs with 3/5 agents; telemetry (parallel<seq) attached")


async def test_never_hangs_when_all_fail():
    class AllBoom(BaseAgent):
        name = "x"

        async def _run(self, q, context=None):
            raise RuntimeError("nope")

    orig = orch_mod.SUB_AGENTS
    orch_mod.SUB_AGENTS = [AllBoom, AllBoom, AllBoom, AllBoom, AllBoom]
    try:
        events = [e async for e in orch_mod.run_swarm("q")]
        assert events[-1]["type"] == "report_ready"
        _passed("stream still terminates with report_ready when every agent fails")
    finally:
        orch_mod.SUB_AGENTS = orig


async def test_sse_endpoint():
    import httpx
    from ..main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        h = await client.get("/health")
        assert h.status_code == 200 and h.json()["status"] == "ok"
        _passed("/health responds ok")

        q = await client.post("/query", json={"question": "X vs Y?"})
        assert q.status_code == 200
        sid = q.json()["session_id"]

        async with client.stream("GET", f"/stream/{sid}") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body = ""
            async for chunk in resp.aiter_text():
                body += chunk
            assert "event: report_ready" in body
            assert "event: agent_start" in body
        _passed("/stream emits a well-formed SSE sequence ending in report_ready")

        missing = await client.get("/stream/does-not-exist")
        assert missing.status_code == 404
        _passed("/stream returns 404 for unknown session")


async def main():
    # Patch agents + synthesis to avoid network / Groq.
    orig_agents = orch_mod.SUB_AGENTS
    orig_synth = orch_mod.synthesize
    orch_mod.SUB_AGENTS = FAKE_AGENTS
    orch_mod.synthesize = fake_synthesize
    try:
        print("BaseAgent:")
        await test_base_agent_guarantees()
        print("Orchestrator:")
        await test_orchestrator_events(None)
        await test_never_hangs_when_all_fail()
        print("FastAPI SSE:")
        await test_sse_endpoint()
    finally:
        orch_mod.SUB_AGENTS = orig_agents
        orch_mod.synthesize = orig_synth
    print("\nALL TESTS PASSED ✓")


if __name__ == "__main__":
    asyncio.run(main())
