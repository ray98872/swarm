// Backend base URL.
//
// Resolution order:
//   1. VITE_API_BASE (set at build time, e.g. in the GitHub Action) — wins.
//   2. localhost dev -> local FastAPI on :8080.
//   3. Production default -> the Hugging Face Space.
//      URL pattern is https://<owner>-<space-name>.hf.space — update this if you
//      name the Space something other than "swarm-backend".
const fromEnv = import.meta.env.VITE_API_BASE;

const isLocal =
  typeof window !== "undefined" &&
  ["localhost", "127.0.0.1"].includes(window.location.hostname);

export const API_BASE =
  fromEnv ||
  (isLocal ? "http://localhost:8080" : "https://ray98872-swarm-backend.hf.space");

// The five agents, in display order. Keep names in sync with backend/agents.
export const AGENTS = [
  { id: "web_search", label: "Web Search", blurb: "Broad current coverage" },
  { id: "docs", label: "Docs", blurb: "Official documentation" },
  { id: "benchmark", label: "Benchmark", blurb: "Performance data" },
  { id: "community", label: "Community", blurb: "Developer sentiment (HN)" },
  { id: "risk", label: "Risk", blurb: "Gaps & caveats" },
];
