# Tariikhna (تاريخنا — "Our History")

Authentic Islamic historical narratives, retold as gentle, historically-corrected
**illustrated storybooks for children**. A Streamlit app presents them as a
readable storybook.

The story data and images are committed to the repo, so the Streamlit app reads
them **directly** by default (no server required) — that's what makes the free
single-service deploy possible. A FastAPI backend is also included for those who
want a separate API; the app uses it automatically when `TARIIKHNA_API_URL` is
set. See [DEPLOY.md](DEPLOY.md).

---

## What's inside

```
(repo root)
├── backend/                     FastAPI + SQLModel + SQLite (optional API)
│   ├── app/
│   │   ├── main.py              app + CORS + /media static mount
│   │   ├── models/db_models.py  Story + Scene (panel) tables
│   │   ├── routers/library.py   read-only storybook API
│   │   ├── routers/stories.py   generation-pipeline endpoints (unchanged)
│   │   └── routers/scenes.py    generation-pipeline endpoints (unchanged)
│   ├── import_storybook.py      ⭐ loads the corrected stories into the DB
│   ├── media/stories/{base,v1}/ illustrations (committed)
│   └── tariikhna.db             SQLite database (the imported content, committed)
└── frontend/                    Streamlit multipage app
    ├── streamlit_app.py         Home page
    ├── pages/1_📚_Stories.py     Library (grid of story cards)
    ├── pages/2_📖_Read_Story.py  Reader (scene image beside narrative text)
    ├── local_store.py           reads the bundled DB + images (default, no server)
    └── storybook_api.py         data access: auto-selects local vs API mode
```

## The data

The content comes from `Finalization/Examples/Corrected/` (illustrations) and
`Finalization/Audio/` (narration):

- **4 stories**, each a sequence of panels (scenes) with a `narrative_text`,
  `unit_title`, and per-scene `moral_lesson`.
- Each scene has **two illustration variants**: `base` (`output_base/images`) and
  `v1` (`output_v1/images`, richer prompts). The narrative is identical between
  them — only the artwork differs — so the Reader offers a **Storybook / Detailed**
  toggle to switch sets.
- Each scene, plus the intro and conclusion, also has **narration audio** (MP3,
  `base` + `v1`). The Reader shows a 🔊 player so children can listen to the text;
  the narration follows the same Storybook / Detailed toggle.

| Story | Slug | Scenes | Ages |
|-------|------|--------|------|
| Abu Bakr's Noble Heart | `abu_bakr_frees_the_slaves` | 6 | 7–11 |
| Compassion | `mercy_even_to_enemies` | 5 | 8–12 |
| A Transfer of Care | `the_orphan_taken_in` | 6 | 6–10 |
| The First Muslim Man | `zayd_the_first_muslim_man` | 6 | 8–12 |

The importer copies the illustrations and audio into `backend/media/`, so the app
is **self-contained** and does not depend on the `Finalization/` folder at runtime.

---

## Setup & run (local)

From the repo root:

```bash
# one-time: create a virtualenv and install deps
py -V:3.10 -m venv .venv
.venv/Scripts/python -m pip install -r frontend/requirements.txt

# run the app — that's all you need (reads the bundled DB + images directly)
cd frontend
../.venv/Scripts/python -m streamlit run streamlit_app.py
#   App: http://localhost:8501
```

**Optional — run the FastAPI backend too** (only if you want the API instead of
direct DB reads):

```bash
.venv/Scripts/python -m pip install -r backend/requirements.txt

# terminal 1: the backend
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload   # :8000/docs

# terminal 2: point the frontend at it
cd frontend
TARIIKHNA_API_URL=http://127.0.0.1:8000 ../.venv/Scripts/python -m streamlit run streamlit_app.py
```

**Re-import the stories** (only if the source JSON changes — the data is already
committed in `backend/tariikhna.db` + `backend/media/`):

```bash
cd backend
../.venv/Scripts/python import_storybook.py \
    --source "../../Graduation-Project/Finalization/Examples/Corrected" \
    --audio  "../../Graduation-Project/Finalization/Audio"
```

The data source is chosen automatically: `TARIIKHNA_API_URL` set → API mode;
otherwise the bundled database → local mode.

---

## Storybook API (read-only)

| Method & path | Returns |
|---|---|
| `GET /library/stories` | all stories as summary cards (title, intro, age, key figures, cover image, scene count) |
| `GET /library/stories/{id}` | one story + its ordered panels (narrative, title, moral, both image variants) |
| `GET /library/stories/by-slug/{slug}` | same, looked up by slug |
| `GET /media/...` | the illustration PNGs |

Image paths are stored relative in the DB and returned as **absolute URLs** built
from the request host, so they work on any host/port.

> The existing `POST /stories`, `POST /scenes/generate`, etc. (the LLM + image
> generation pipeline) are untouched and still work.

---

## ⚠️ Security note

`backend/.env` currently contains **real-looking Hugging Face and fal.ai
credentials** committed to the repo. Rotate those keys and move them out of
version control (e.g. an untracked `.env`) before sharing this repository.
