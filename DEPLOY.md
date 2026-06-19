# Deploying Swarm (all free tiers)

Three pieces ship independently: the **GitHub repo**, the **Hugging Face Spaces
backend** (free, no credit card), and the **GitHub Pages frontend**. Do them in
this order.

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

## 2. Deploy the backend to Hugging Face Spaces (free, no card)

Fly.io is no longer £0 (it now requires a credit card and bills ~$1.94/mo for
an always-on VM), so the backend deploys to a free **Hugging Face Space** using
the Docker SDK on **CPU Basic** hardware. No credit card. The container runs
persistently, so the SSE stream and in-memory sessions work unchanged. (A free
Space sleeps after ~48h of inactivity and cold-starts on the next request.)

1. Sign in / sign up at https://huggingface.co (free, no card).
2. Create the Space: **New → Space** → owner `ray98872`, name `swarm-backend`,
   **SDK = Docker**, hardware **CPU Basic (free)**, visibility Public.
3. Add the Groq key as a secret: in the Space, **Settings → Variables and
   secrets → New secret** → name `GROQ_API_KEY`, value `gsk_...`
   (see README → *Get a Groq key*).
4. Push the **`backend/` folder contents** to the Space's git repo. From the
   project root:

   ```bash
   cd backend
   git init
   git add -A
   git commit -m "Swarm backend"
   git remote add space https://huggingface.co/spaces/ray98872/swarm-backend
   git push space main --force      # HF will prompt for a write token as the password
   ```

   (Create a write token at https://huggingface.co/settings/tokens if asked.)
5. The Space builds the Dockerfile automatically. When it's running, check:
   `https://ray98872-swarm-backend.hf.space/health` → `{"status":"ok","groq":true,...}`

Notes:
- `backend/README.md` carries the HF Space config (`sdk: docker`,
  `app_port: 7860`); the Dockerfile listens on 7860 to match.
- If you name the Space something other than `swarm-backend`, update the URL in
  step 3 of section 3 below (and `frontend/src/config.js`).

---

## 3. Point the frontend at the backend

The frontend defaults to `https://ray98872-swarm-backend.hf.space` (the HF Space
URL pattern is `https://<owner>-<space-name>.hf.space`). If your Space has a
different name, set the URL at build time so the deployed site targets it.

Edit `.github/workflows/deploy.yml` — in the **Build** step add the env var:

```yaml
      - name: Build
        run: npm run build
        env:
          VITE_API_BASE: https://YOUR-OWNER-YOUR-SPACE.hf.space
```

(Or just name the Space `swarm-backend` under owner `ray98872` and skip this.)

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
host the frontend somewhere else, add an `ALLOWED_ORIGINS` secret on the Space
(Settings → Variables and secrets), comma-separated:

```
ALLOWED_ORIGINS = https://ray98872.github.io,https://your-other-host
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
