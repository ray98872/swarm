import { useCallback, useRef, useState } from "react";
import { API_BASE, AGENTS } from "./config.js";
import QueryInput from "./components/QueryInput.jsx";
import AgentPanel from "./components/AgentPanel.jsx";
import ReportView from "./components/ReportView.jsx";

export default function App() {
  const [agentStates, setAgentStates] = useState({});
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const esRef = useRef(null);

  const reset = () => {
    setReport(null);
    setError(null);
    // Seed every agent as "waiting" so all five cards render immediately.
    setAgentStates(
      Object.fromEntries(AGENTS.map((a) => [a.id, { status: "waiting" }]))
    );
  };

  const updateAgent = (id, patch) =>
    setAgentStates((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));

  const run = useCallback(async (question) => {
    if (esRef.current) esRef.current.close();
    reset();
    setBusy(true);

    let sessionId;
    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error(`server returned ${res.status}`);
      ({ session_id: sessionId } = await res.json());
    } catch (e) {
      setError(
        `Couldn't reach the backend (${e.message}). The free Fly.io instance may be waking up — try again in a few seconds.`
      );
      setBusy(false);
      return;
    }

    const es = new EventSource(`${API_BASE}/stream/${sessionId}`);
    esRef.current = es;

    const finish = () => {
      setBusy(false);
      es.close();
      esRef.current = null;
    };

    es.addEventListener("agent_start", (ev) => {
      const { agent } = JSON.parse(ev.data);
      updateAgent(agent, { status: "searching" });
    });

    es.addEventListener("agent_done", (ev) => {
      const d = JSON.parse(ev.data);
      updateAgent(d.agent, {
        status: d.ok ? "done" : "failed",
        confidence: d.confidence,
        elapsed_ms: d.elapsed_ms,
        findings_count: d.findings_count,
      });
    });

    es.addEventListener("report_ready", (ev) => {
      const { report: rep } = JSON.parse(ev.data);
      setReport(rep);
      finish();
    });

    es.addEventListener("error", (ev) => {
      // Two cases: an explicit error event (has data) or a transport drop.
      if (ev.data) {
        try {
          const d = JSON.parse(ev.data);
          setError(d.message || "The swarm reported an error.");
        } catch {
          setError("The swarm reported an error.");
        }
      } else {
        setError("Connection to the swarm was interrupted.");
      }
      finish();
    });
  }, []);

  return (
    <div className="wrap">
      <header className="masthead">
        <div>
          <p className="eyebrow">Multi-agent · RAG · SSE</p>
          <h1 className="title">Research Agent Swarm</h1>
          <p className="subtitle">
            Ask a technical comparison question. An orchestrator fans out to five
            specialist agents in parallel — web search, docs, benchmarks, community
            signals and risk — then a synthesis agent merges their findings into a
            cited report.
          </p>
        </div>
        <a className="backlink" href="https://ray98872.github.io">
          ← portfolio
        </a>
      </header>

      <QueryInput onSubmit={run} busy={busy} />

      {error && <div className="error-banner">{error}</div>}

      <AgentPanel states={agentStates} />

      <ReportView report={report} />

      <footer className="footer">
        custom asyncio orchestration · groq llama-3.1-8b + 3.3-70b ·{" "}
        <a href="writeup/">read the write-up →</a>
      </footer>
    </div>
  );
}
