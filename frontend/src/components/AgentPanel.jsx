import { AGENTS } from "../config.js";

const STATUS_TEXT = {
  waiting: "waiting",
  searching: "searching…",
  done: "done",
  failed: "failed",
};

function AgentCard({ agent, state }) {
  const status = state?.status || "waiting";
  return (
    <div className={`agent-card ${status}`}>
      <div className="name">
        <span className="dot" />
        {agent.label}
      </div>
      <div className="blurb">{agent.blurb}</div>
      <div className="status">
        <span>{STATUS_TEXT[status]}</span>
        {status === "done" && state?.confidence != null && (
          <span className="badge">{Math.round(state.confidence * 100)}%</span>
        )}
        {status === "failed" && <span className="badge" style={{ color: "var(--red)" }}>—</span>}
      </div>
      {status === "done" && (
        <div className="status">
          <span>
            {state.findings_count ?? 0} findings
          </span>
          <span>{state.elapsed_ms != null ? `${(state.elapsed_ms / 1000).toFixed(1)}s` : ""}</span>
        </div>
      )}
      <div className="shimmer" />
    </div>
  );
}

export default function AgentPanel({ states }) {
  const anyActive = Object.keys(states).length > 0;
  if (!anyActive) return null;
  return (
    <div>
      <div className="section-label">
        <span>Agent swarm · star fan-out</span>
        <span>5 parallel</span>
      </div>
      <div className="agent-grid">
        {AGENTS.map((a) => (
          <AgentCard key={a.id} agent={a} state={states[a.id]} />
        ))}
      </div>
    </div>
  );
}
