"""FastAPI application: REST entry + Server-Sent Events stream.

Flow:
  1. Client POSTs a question to /query -> gets a session_id.
  2. Client opens GET /stream/{session_id} (EventSource) and receives live
     events as the swarm runs: agent_start, agent_done, synthesis_start,
     report_ready (or error).

Sessions are kept in-process (a dict). That's fine for a single always-on
Fly.io instance serving demo traffic; the "what I'd do at scale" section of the
write-up covers Redis pub/sub for multi-worker deployments.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import config
from .models import QueryRequest, QueryResponse
from .orchestrator import run_swarm

app = FastAPI(title="Swarm", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# In-memory session registry
# --------------------------------------------------------------------------- #
@dataclass
class Session:
    question: str
    created_at: float = field(default_factory=time.time)
    consumed: bool = False


SESSIONS: dict[str, Session] = {}


def _gc_sessions() -> None:
    now = time.time()
    stale = [
        sid for sid, s in SESSIONS.items() if now - s.created_at > config.SESSION_TTL_S
    ]
    for sid in stale:
        SESSIONS.pop(sid, None)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "groq": config.has_groq(),
        "models": {"fast": config.MODEL_FAST, "synth": config.MODEL_SYNTH},
        "active_sessions": len(SESSIONS),
    }


@app.post("/query", response_model=QueryResponse)
async def create_query(req: QueryRequest) -> QueryResponse:
    _gc_sessions()
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = Session(question=req.question.strip())
    return QueryResponse(session_id=session_id)


def _sse(event_type: str, data: dict) -> str:
    """Format one SSE frame. The `event:` line lets EventSource route by type."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/stream/{session_id}")
async def stream(session_id: str) -> StreamingResponse:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown or expired session_id")

    async def event_generator():
        # Initial comment frame opens the stream promptly and defeats proxy buffering.
        yield ": stream open\n\n"
        try:
            async for event in run_swarm(session.question):
                yield _sse(event["type"], event["data"])
        except asyncio.CancelledError:  # client disconnected
            raise
        except Exception as exc:  # never leave the client hanging
            yield _sse("error", {"message": f"{type(exc).__name__}: {exc}"})
        finally:
            SESSIONS.pop(session_id, None)

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # disable nginx-style buffering
    }
    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=headers
    )


@app.get("/")
async def root() -> dict:
    return {
        "name": "Swarm",
        "description": "Multi-agent research system. POST /query then GET /stream/{id}.",
        "health": "/health",
        "docs": "/docs",
    }
