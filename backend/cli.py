"""Command-line harness for testing agents and the full pipeline without the
HTTP layer. Useful for local verification before deploying.

Usage:
    python -m backend.cli agent web_search "Should I migrate from Redis to Valkey?"
    python -m backend.cli run "Should I migrate from Redis to Valkey?"
"""

from __future__ import annotations

import asyncio
import json
import sys

from .agents import SUB_AGENTS
from .orchestrator import run_swarm


def _agent_map():
    return {cls.name: cls for cls in SUB_AGENTS}


async def _run_agent(name: str, question: str) -> None:
    cls = _agent_map().get(name)
    if not cls:
        print(f"unknown agent '{name}'. choices: {list(_agent_map())}")
        sys.exit(1)
    result = await cls().run(question)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


async def _run_pipeline(question: str) -> None:
    async for event in run_swarm(question):
        etype = event["type"]
        if etype == "report_ready":
            print("\n=== REPORT ===")
            print(json.dumps(event["data"]["report"], indent=2, ensure_ascii=False))
        else:
            print(f"[event] {etype}: {json.dumps(event['data'], ensure_ascii=False)}")


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    mode = sys.argv[1]
    if mode == "agent":
        asyncio.run(_run_agent(sys.argv[2], " ".join(sys.argv[3:]) or "test"))
    elif mode == "run":
        asyncio.run(_run_pipeline(" ".join(sys.argv[2:])))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
