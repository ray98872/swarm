"""Central configuration. All values overridable via environment variables."""

from __future__ import annotations

import os


# --- Groq -------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL: str = os.getenv(
    "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
)
# Fast, free model for the 5 retrieval/extraction sub-agents.
MODEL_FAST: str = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")
# Larger model for the single final synthesis merge.
MODEL_SYNTH: str = os.getenv("GROQ_MODEL_SYNTH", "llama-3.3-70b-versatile")

# --- Timeouts / limits ------------------------------------------------------
AGENT_TIMEOUT_S: float = float(os.getenv("AGENT_TIMEOUT_S", "15"))
SYNTH_TIMEOUT_S: float = float(os.getenv("SYNTH_TIMEOUT_S", "25"))
LLM_HTTP_TIMEOUT_S: float = float(os.getenv("LLM_HTTP_TIMEOUT_S", "20"))
HTTP_TIMEOUT_S: float = float(os.getenv("HTTP_TIMEOUT_S", "8"))
MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "6"))

# --- CORS -------------------------------------------------------------------
# Comma-separated list of allowed origins. Defaults cover the portfolio site
# plus local dev. Override with ALLOWED_ORIGINS in production if needed.
_default_origins = (
    "https://ray98872.github.io,"
    "http://localhost:5173,"
    "http://127.0.0.1:5173"
)
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()
]

USER_AGENT: str = (
    "SwarmResearchBot/1.0 (+https://ray98872.github.io/swarm/) "
    "httpx"
)

# Session TTL (seconds) — drives cleanup of completed sessions.
SESSION_TTL_S: int = int(os.getenv("SESSION_TTL_S", "600"))


def has_groq() -> bool:
    return bool(GROQ_API_KEY)
