// Backend base URL.
//
// Resolution order:
//   1. VITE_API_BASE (set at build time, e.g. in the GitHub Action) — wins.
//   2. localhost dev -> local FastAPI on :8080.
//   3. Production default -> the Fly.io app (rename if you choose a different app name).
const fromEnv = import.meta.env.VITE_API_BASE;

const isLocal =
  typeof window !== "undefined" &&
  ["localhost", "127.0.0.1"].includes(window.location.hostname);

export const API_BASE =
  fromEnv || (isLocal ? "http://localhost:8080" : "https://swarm-backend.fly.dev");

// The five agents, in display order. Keep names in sync with backend/agents.
export const AGENTS = [
  { id: "web_search", label: "Web Search", blurb: "Broad current coverage" },
  { id: "docs", label: "Docs", blurb: "Official documentation" },
  { id: "benchmark", label: "Benchmark", blurb: "Performance data" },
  { id: "community", label: "Community", blurb: "Developer sentiment (HN)" },
  { id: "risk", label: "Risk", blurb: "Gaps & caveats" },
];
