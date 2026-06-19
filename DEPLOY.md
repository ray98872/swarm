# Deploying Swarm (all free tiers)

Three pieces ship independently: the **GitHub repo**, the **Fly.io backend**,
and the **GitHub Pages frontend**. Do them in this order.

---

## 1. Initialise git and create the repo `ray98872/swarm`

Run this on your own machine from the project folder
(`C:\Users\Raihan\ClaudeCowork\swarm`). There's a harmless leftover `.git/`
folder from the build environment — delete it first, then init cleanly:

```powershell
# PowerShell, from the swarm/ folder
Remove-Item -Recurse -Force .git   # clear the leftover partial repo
git init
git add -A
git commit -m "Swarm: zero-cost multi-agent research system"
```

Then publish to GitHub:

```bash
# Option A — GitHub CLI
gh repo create ray98872/swarm --public --source=. --remote=origin --push

# Option B — manual: create an empty repo named "swarm" at github.com/new, then
git remote add origin https://github.com/ray98872/swarm.git
git branch -M main
git push -u origin main
```

`.gitignore` already excludes `node_modules/`, `dist/`, `__pycache__/`, and
`.env`, so only source is committed.

---

## 2. Deploy the backend to Fly.io

Free tier, always-on, no credit card needed for the small shared VM.

```bash
# Install flyctl once: https://fly.io/docs/flyctl/install/
fly auth signup        # or: fly auth login
cd backend
fly launch --no-deploy        # accept the existing fly.toml; pick a unique app
                              # name if "swarm-backend" is taken
fly secrets set GROQ_API_KEY=gsk_your_key_here     # see README → Get a Groq key
fly deploy
fly open /health              # should return {"status":"ok","groq":true,...}
```

Notes:
- `fly.toml` is preconfigured for an always-on 256MB shared VM with a `/health`
  check (no spin-down → no cold starts in the demo).
- If you change the app name, update the frontend's backend URL in step 3.

---

## 3. Point the frontend at the backend

The frontend defaults to `https://swarm-backend.fly.dev`. If your Fly app has a
different name, set it at build time so the deployed site targets the right URL.

Edit `.github/workflows/deploy.yml` — in the **Build** step add the env var:

```yaml
      - name: Build
        run: npm run build
        env:
          VITE_API_BASE: https://YOUR-APP-NAME.fly.dev
```

(Or just rename your Fly app to `swarm-backend` and skip this.)

---

## 4. Enable GitHub Pages

1. Push to `main` (step 1 already did, or push again after edits).
2. On GitHub: **Settings → Pages → Build and deployment → Source = GitHub Actions.**
3. The `Deploy frontend to GitHub Pages` workflow runs automatically and
   publishes:
   - SPA → `https://ray98872.github.io/swarm/`
   - Write-up → `https://ray98872.github.io/swarm/writeup/`

The Vite `base` is already set to `/swarm/`, and the workflow copies
`writeup/index.html` into the build output.

---

## 5. CORS

The backend already allows `https://ray98872.github.io` plus localhost. If you
host the frontend somewhere else, set the origin on the backend:

```bash
fly secrets set ALLOWED_ORIGINS="https://ray98872.github.io,https://your-other-host"
```

---

## 6. Smoke test (do this before calling it done)

With the backend live and a Groq key set, run at least three different queries
through the **live demo** and confirm:

- all five agent cards animate waiting → searching → done (or a clean failed
  card on timeout);
- the report renders with verdict, summary, pros/cons/risks and numbered
  citations;
- the timing note shows parallel vs. sequential;
- a deliberately obscure query still returns a report (degradation), never a
  hung spinner.

Suggested queries: *“Should I migrate from Redis to Valkey?”*, *“Postgres vs
MongoDB for a new analytics product?”*, *“Is Bun production-ready as a Node.js
replacement?”*

---

## 7. Portfolio card (after mounting `ray98872.github.io`)

See [`portfolio-integration/README.md`](./portfolio-integration/README.md) for
the `SwarmFanout` graphic component and the exact Bento card props.
