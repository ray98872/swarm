# Swarm — multi-agent research system

Ask a technical comparison question (*“Should I migrate from Redis to
Valkey?”*). An orchestrator fans out to **five specialist agents in parallel**,
each retrieving from a different kind of source and returning structured
findings with a confidence score. A **synthesis agent** merges everything into a
cited report. The frontend streams live agent status over **SSE**, then renders
the report.

**Zero cost.** No paid tiers, no trials, no credit card — Groq free tier,
DuckDuckGo + Hacker News (no keys), Fly.io free VM, GitHub Pages.

- **Live demo:** https://ray98872.github.io/swarm/
- **Write-up:** https://ray98872.github.io/swarm/writeup/
- **Portfolio:** https://ray98872.github.io

---

## Architecture

Star fan-out, custom `asyncio` orchestration — **no LangGraph / CrewAI / AutoGen.**

```
                 ┌──> web_search ─┐
                 ├──> docs ───────┤
  orchestrator ──┼──> benchmark ──┼──> synthesis (70B) ──> Report
  (asyncio.gather)├──> community ─┤
                 └──> risk ───────┘
        5 agents run concurrently        single merge step
```

Every agent returns the same contract:

```python
@dataclass
class AgentResult:
    agent_name: str
    findings: list[str]
    citations: list[str]
    confidence: float   # 0.0–1.0
    elapsed_ms: int
```

Each sub-agent has a **15s timeout**; a timeout/failure returns
`confidence=0.0` and the pipeline continues. Synthesis runs even if 1–2 agents
fail (graceful degradation). The SSE stream **always** ends in `report_ready`
or `error` — it never hangs.

| Layer | Choice |
|---|---|
| Backend | FastAPI + `asyncio`, Fly.io free VM (always-on) |
| Sub-agent LLM | Groq `llama-3.1-8b-instant` |
| Synthesis LLM | Groq `llama-3.3-70b-versatile` |
| Web search | `duckduckgo-search` (no key) |
| Community data | Hacker News Algolia API (no auth) |
| Docs/benchmarks | `httpx` + `BeautifulSoup` scraping |
| Frontend | React + Vite, GitHub Pages |

---

## Repo layout

```
backend/      FastAPI app, orchestrator, 5 agents + synthesis, Dockerfile, fly.toml
frontend/     React + Vite SPA (live agent cards + report view)
writeup/      Standalone write-up page (dark/copper editorial design)
portfolio-integration/   SwarmFanout.jsx + card snippet for the portfolio Bento grid
.github/workflows/deploy.yml   Builds frontend + writeup, publishes to Pages
```

---

## Run locally

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GROQ_API_KEY=...        # see "Get a Groq key" below;  Windows: set GROQ_API_KEY=...
uvicorn backend.main:app --reload --port 8080   # run from the repo root
```

Quick checks without the HTTP layer:

```bash
python -m backend.cli agent web_search "Should I migrate from Redis to Valkey?"
python -m backend.cli run "Postgres vs MongoDB for analytics?"
python -m backend.tests.test_pipeline    # offline tests (no key/network needed)
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (auto-targets localhost:8080 backend)
```

---

## Get a free Groq key (no card)

1. Go to **https://console.groq.com** and sign in (Google/GitHub works).
2. **API Keys → Create API Key**, copy it (starts with `gsk_`).
3. Local: `export GROQ_API_KEY=gsk_...`  ·  Fly.io: `fly secrets set GROQ_API_KEY=gsk_...`

Free tier is ~30 requests/min per model; one query uses 6 calls (5 agents + 1
synthesis), so it stays well inside the limit for a demo. The key is read from
the environment only — it is never committed (`.env` is git-ignored).

---

## Deploy

See [`DEPLOY.md`](./DEPLOY.md) for the full step-by-step (GitHub repo, Fly.io
backend, GitHub Pages frontend, and portfolio card).

Built by Raihan Mahbub.
