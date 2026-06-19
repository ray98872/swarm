import { AGENTS } from "../config.js";

const LABELS = Object.fromEntries(AGENTS.map((a) => [a.id, a.label]));

function List({ items }) {
  if (!items || items.length === 0) return <p style={{ color: "var(--text-faint)", fontSize: 13 }}>None reported.</p>;
  return (
    <ul>
      {items.map((it, i) => (
        <li key={i}>{it}</li>
      ))}
    </ul>
  );
}

export default function ReportView({ report }) {
  if (!report) return null;
  const conf = Math.round((report.confidence_overall || 0) * 100);

  const total = report.elapsed_ms_total || 0;
  const seq = report.elapsed_ms_sequential_estimate || 0;
  const saved = seq > total ? ((seq - total) / 1000).toFixed(1) : null;

  // Agents that returned no findings, with the reason the orchestrator recorded.
  const agents = report.agents || [];
  const failed = agents.filter((a) => !a.findings || a.findings.length === 0);

  return (
    <div className="report">
      <div className="verdict-row">
        {report.verdict && <span className="verdict-chip">{report.verdict}</span>}
        <span className="conf">
          overall confidence <b>{conf}%</b>
        </span>
      </div>

      <h2>Summary</h2>
      <p className="summary">{report.summary}</p>

      <div className="cols">
        <div className="col pros">
          <h3>Pros</h3>
          <List items={report.pros} />
        </div>
        <div className="col cons">
          <h3>Cons</h3>
          <List items={report.cons} />
        </div>
      </div>

      <div className="risks-block">
        <div className="col risks">
          <h3>Risks &amp; caveats</h3>
          <List items={report.risks} />
        </div>
      </div>

      {report.citations && report.citations.length > 0 && (
        <div className="citations">
          <h3>Citations</h3>
          <ol>
            {report.citations.map((c) => (
              <li key={c.n} value={c.n}>
                <a href={c.url} target="_blank" rel="noreferrer noopener">
                  {c.title || c.url}
                </a>
                {c.source_agent && <span className="cite-agent">· {c.source_agent}</span>}
              </li>
            ))}
          </ol>
        </div>
      )}

      {failed.length > 0 && (
        <div className="diagnostics">
          <h3>Agent diagnostics</h3>
          <p className="diag-note">
            {failed.length} of {agents.length} agents returned no findings — the report
            above was synthesised from the rest (graceful degradation).
          </p>
          <ul>
            {failed.map((a) => (
              <li key={a.agent_name}>
                <span className="diag-agent">{LABELS[a.agent_name] || a.agent_name}</span>
                <span className="diag-reason">{a.error || "no findings returned"}</span>
                {a.elapsed_ms != null && (
                  <span className="diag-time">{(a.elapsed_ms / 1000).toFixed(1)}s</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="timing">
        Completed in <b>{(total / 1000).toFixed(1)}s</b>
        {saved && (
          <>
            {" "}— roughly <b>{saved}s</b> faster than running the agents sequentially
            (~{(seq / 1000).toFixed(1)}s). Cost per query: <b>£0</b>.
          </>
        )}
      </div>
    </div>
  );
}
