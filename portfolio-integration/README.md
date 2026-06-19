# Portfolio integration (do this once `ray98872.github.io` is mounted)

This folder holds everything needed to add the **Research Agent Swarm** card to
the portfolio's `Bento.jsx` (Engineered section). Nothing here is part of the
deployed Swarm app — it's a staging area for the portfolio edit.

## Steps

1. **Copy the graphic component.** Move `SwarmFanout.jsx` into the portfolio's
   `src/components/` (or paste the function inline next to the other graphic
   components like `RAGFlow` / `BlueGreenFlow` in `Bento.jsx`, matching whatever
   pattern that file already uses).

2. **Import it** at the top of `Bento.jsx`:
   ```jsx
   import SwarmFanout from "./SwarmFanout.jsx"; // or inline, to match the file's style
   ```

3. **Add the card** to the Engineered section's card array/JSX, using these
   exact props:
   ```jsx
   {
     label: "Multi-agent · RAG · SSE",
     title: "Research Agent Swarm",
     desc: "Five specialist agents fan out in parallel over a technical question — web search, docs, benchmarks, community signals and risk — then a synthesis agent merges their findings into a cited report.",
     meta: "python · groq · fastapi · fly.io · sse",
     href: "https://ray98872.github.io/swarm/",          // live demo
     // writeup: "https://ray98872.github.io/swarm/writeup/", // if cards support a 2nd link
     graphic: <SwarmFanout />,
   }
   ```
   Match the field names to whatever the existing cards in `Bento.jsx` use
   (e.g. the link prop might be `link`, `url`, or an `<a href>` wrapper — copy a
   neighbouring card's shape rather than assuming).

4. **Check the palette.** `SwarmFanout` already uses the copper `#c97e4e`,
   dark `#161618`/`#0a0a0b`, and green `#5fa873`. If `Bento.jsx` exposes these
   as CSS variables, swap the hex literals for the variables to stay DRY.

5. **Verify** the animation pauses offscreen / respects `prefers-reduced-motion`
   the same way the other cards do, then commit and let Pages redeploy.

> When you mount the portfolio repo in a later session, I can do all of this
> directly against the real `Bento.jsx` instead of you pasting by hand.
