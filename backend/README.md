---
title: Swarm Backend
emoji: 🐝
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# Swarm — backend (FastAPI)

Custom-orchestrated multi-agent research API. An orchestrator fans out to five
specialist agents in parallel (`asyncio.gather`), then a synthesis agent merges
their findings into a cited report streamed to the client over Server-Sent
Events.

This Space hosts the backend only. The live frontend lives at
**https://ray98872.github.io/swarm/** and the write-up at
**https://ray98872.github.io/swarm/writeup/**. Source:
**https://github.com/ray98872/swarm**.

## Endpoints

- `POST /query` → `{ session_id }`
- `GET /stream/{session_id}` → SSE: `agent_start`, `agent_done`, `synthesis_start`, `report_ready`, `error`
- `GET /health` → status + model info

## Configuration

Set as a **Space secret** (Settings → Variables and secrets):

- `GROQ_API_KEY` — free key from https://console.groq.com (no card)

Optional `ALLOWED_ORIGINS` (comma-separated) defaults to the GitHub Pages site
plus localhost.

> Runs on free **CPU Basic** hardware. A free Space sleeps after ~48h of
> inactivity and cold-starts on the next request.
