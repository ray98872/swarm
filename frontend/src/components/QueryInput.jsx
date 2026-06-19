import { useState } from "react";

const EXAMPLES = [
  "Should I migrate from Redis to Valkey?",
  "Postgres vs MongoDB for a new analytics product?",
  "Is Bun production-ready as a Node.js replacement?",
  "Rust vs Go for a high-throughput API gateway?",
];

export default function QueryInput({ onSubmit, busy }) {
  const [value, setValue] = useState("");

  const submit = (q) => {
    const question = (q ?? value).trim();
    if (question.length < 3 || busy) return;
    setValue(question);
    onSubmit(question);
  };

  return (
    <div>
      <div className="query">
        <input
          type="text"
          value={value}
          placeholder="Ask a technical comparison question…"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          disabled={busy}
          aria-label="Technical comparison question"
        />
        <button onClick={() => submit()} disabled={busy || value.trim().length < 3}>
          {busy ? "Running…" : "Dispatch swarm"}
        </button>
      </div>
      <div className="suggestions">
        {EXAMPLES.map((ex) => (
          <button key={ex} className="chip" onClick={() => submit(ex)} disabled={busy}>
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
