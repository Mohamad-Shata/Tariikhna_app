# Deploying Tariikhna for free

Tariikhna is two services, so it needs two free deployments that talk over HTTPS:

| Part | Host | Why |
|------|------|-----|
| **Backend** (FastAPI + SQLite + images) | **Render** (free Web Service) | runs `uvicorn`; serves data + `/media` images |
| **Frontend** (Streamlit) | **Streamlit Community Cloud** | free, purpose-built for Streamlit |

The story data (`backend/tariikhna.db`) and illustrations (`backend/media/`) are
committed to git, so **no database or file storage is needed on the host** — the
content ships with the repo. The HF/fal.ai keys are **not** required for the
storybook to run, so the backend needs no secrets.

> ⚠️ Free tiers **sleep when idle**. The first request after a nap cold-starts the
> backend (~30–50s); the frontend retries automatically, so the first page load
> just takes a few extra seconds.

---

## Step 0 — Get the code on GitHub

**Recommended: a standalone `tariikhna` repo.** Streamlit Cloud and Render clone
the *entire* repo on every deploy. Your `graduation-project` repo also contains
`Finalization/`, `Phase_1/`, etc. (large, image-heavy) — cloning all of that on
each deploy is slow and may hit size limits. `tariikhna/` is self-contained, so:

```bash
cd tariikhna
git init
# stop tracking the committed secret file (keeps it on disk, removes from git):
git rm --cached backend/.env 2>/dev/null || true
git add .
git commit -m "Tariikhna storybook app"
# create an empty repo named e.g. "tariikhna" on GitHub, then:
git remote add origin https://github.com/<you>/tariikhna.git
git push -u origin main
```

In a standalone repo the paths are `backend/` and `frontend/`.

<details>
<summary>Alternative: deploy from the existing <code>graduation-project</code> monorepo (no split)</summary>

You don't have to split. Just prefix the paths in the steps below with
`tariikhna/` (e.g. Render Root Directory = `tariikhna/backend`, Streamlit main
file = `tariikhna/frontend/streamlit_app.py`). The only downside is the slower
full-repo clone described above.
</details>

---

## Step 1 — Backend on Render

1. Push the repo to GitHub (Step 0). Make sure `backend/tariikhna.db` and
   `backend/media/` are committed (they are not gitignored).
2. On [render.com](https://render.com) → **New → Web Service** → connect the repo.
3. Settings:
   - **Root Directory:** `backend`  *(monorepo: `tariikhna/backend`)*
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** *(leave blank — the `Procfile` is used)* or set:
     `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*`
   - **Instance Type:** Free
4. Create the service. When it's live, note the URL, e.g.
   `https://tariikhna-api.onrender.com`.
5. Verify: open `https://<your-backend>/library/stories` — you should see JSON.

The `--proxy-headers` flags matter: they make the backend emit **`https://`**
image URLs behind Render's TLS proxy. Without them, images would be `http://` and
the browser would block them as mixed content on the HTTPS frontend.

---

## Step 2 — Frontend on Streamlit Community Cloud

1. On [share.streamlit.io](https://share.streamlit.io) → **New app** → pick the repo.
2. Settings:
   - **Main file path:** `frontend/streamlit_app.py`
     *(monorepo: `tariikhna/frontend/streamlit_app.py`)*
   - **Branch:** `main`
3. Open **Advanced settings → Secrets** and paste (using your Render URL):
   ```toml
   TARIIKHNA_API_URL = "https://tariikhna-api.onrender.com"
   ```
4. Deploy. The app installs `frontend/requirements.txt` automatically.

That's it — the Streamlit app reads `TARIIKHNA_API_URL` from secrets and pulls
stories + images from your Render backend.

---

## Updating after a deploy

- Change code/data → `git push` → both hosts auto-redeploy from `main`.
- Re-imported stories? Commit the updated `backend/tariikhna.db` and
  `backend/media/` too — that's the content the backend serves.

## Notes & gotchas

- **Cold starts:** expected on free tiers; the frontend retries for ~90s.
- **Keep the backend awake (optional):** a free uptime pinger (e.g. UptimeRobot)
  hitting `https://<backend>/` every ~10 min avoids most cold starts.
- **Rotate the keys** in `backend/.env` — they were committed earlier in history.
