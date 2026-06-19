// SwarmFanout — bespoke animated graphic for the "Research Agent Swarm" Bento
// card, matching the copper/dark palette and the animated-SVG style of the
// other Engineered cards (RAGFlow, BlueGreenFlow, …).
//
// A central orchestrator node pulses and fans travelling particles out to five
// agent nodes; the agents in turn feed a synthesis node. Pure SVG/SMIL — no
// runtime deps, no JS animation loop, GPU-cheap, and it pauses when offscreen
// like the others.
//
// Drop this into src/components/ (or inline alongside the other graphic
// components in Bento.jsx) and reference it from the card's `graphic` slot.

export default function SwarmFanout() {
  // Five agent endpoints on the right; orchestrator on the left.
  const orch = { x: 26, y: 60 };
  const synth = { x: 174, y: 60 };
  const agents = [
    { x: 100, y: 18 },
    { x: 100, y: 39 },
    { x: 100, y: 60 },
    { x: 100, y: 81 },
    { x: 100, y: 102 },
  ];

  return (
    <svg
      viewBox="0 0 200 120"
      width="100%"
      height="100%"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
      style={{ display: "block" }}
    >
      <defs>
        <radialGradient id="swarmCore" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#d99a6e" />
          <stop offset="100%" stopColor="#c97e4e" />
        </radialGradient>
      </defs>

      {/* spokes: orchestrator -> agents */}
      <g stroke="#2d2d33" strokeWidth="0.8" fill="none">
        {agents.map((a, i) => (
          <line key={`o${i}`} x1={orch.x} y1={orch.y} x2={a.x} y2={a.y} />
        ))}
        {/* agents -> synthesis */}
        {agents.map((a, i) => (
          <line key={`s${i}`} x1={a.x} y1={a.y} x2={synth.x} y2={synth.y} opacity="0.75" />
        ))}
      </g>

      {/* travelling particles: dispatch (copper) */}
      <g fill="#d99a6e">
        {agents.map((a, i) => (
          <circle key={`pd${i}`} r="1.6">
            <animateMotion
              dur="1.6s"
              begin={`${i * 0.1}s`}
              repeatCount="indefinite"
              path={`M${orch.x},${orch.y} L${a.x},${a.y}`}
            />
            <animate
              attributeName="opacity"
              values="0;1;1;0"
              dur="1.6s"
              begin={`${i * 0.1}s`}
              repeatCount="indefinite"
            />
          </circle>
        ))}
      </g>

      {/* travelling particles: results (green) */}
      <g fill="#5fa873">
        {agents.map((a, i) => (
          <circle key={`pr${i}`} r="1.4">
            <animateMotion
              dur="1.8s"
              begin={`${0.8 + i * 0.12}s`}
              repeatCount="indefinite"
              path={`M${a.x},${a.y} L${synth.x},${synth.y}`}
            />
            <animate
              attributeName="opacity"
              values="0;1;1;0"
              dur="1.8s"
              begin={`${0.8 + i * 0.12}s`}
              repeatCount="indefinite"
            />
          </circle>
        ))}
      </g>

      {/* agent nodes */}
      <g>
        {agents.map((a, i) => (
          <circle
            key={`a${i}`}
            cx={a.x}
            cy={a.y}
            r="4.2"
            fill="#161618"
            stroke="#3a3a40"
            strokeWidth="0.8"
          >
            <animate
              attributeName="stroke"
              values="#3a3a40;#5fa873;#3a3a40"
              dur="2.4s"
              begin={`${0.9 + i * 0.12}s`}
              repeatCount="indefinite"
            />
          </circle>
        ))}
      </g>

      {/* synthesis node */}
      <circle cx={synth.x} cy={synth.y} r="6.5" fill="#161618" stroke="#5fa873" strokeWidth="1" />

      {/* orchestrator (pulsing core) */}
      <circle cx={orch.x} cy={orch.y} r="8" fill="url(#swarmCore)">
        <animate attributeName="r" values="8;9.2;8" dur="2.4s" repeatCount="indefinite" />
      </circle>
      <circle cx={orch.x} cy={orch.y} r="8" fill="none" stroke="#c97e4e" strokeWidth="0.8" opacity="0.5">
        <animate attributeName="r" values="8;15;8" dur="2.4s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.5;0;0.5" dur="2.4s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}
