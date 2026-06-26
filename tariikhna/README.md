# Tariikhna (تاريخنا — "Our History")

Authentic Islamic historical narratives, retold as gentle, historically-corrected
**illustrated storybooks for children**. A FastAPI backend serves the story data
and illustrations; a Streamlit frontend presents them as a readable storybook.

---

## What's inside

```
tariikhna/
├── backend/                     FastAPI + SQLModel + SQLite
│   ├── app/
│   │   ├── main.py              app + CORS + /media static mount
│   │   ├── models/db_models.py  Story + Scene (panel) tables
│   │   ├── routers/library.py   read-only storybook API (used by the frontend)
│   │   ├── routers/stories.py   generation-pipeline endpoints (unchanged)
│   │   └── routers/scenes.py    generation-pipeline endpoints (unchanged)
│   ├── import_storybook.py      ⭐ loads the corrected stories into the DB
│   ├── media/stories/{base,v1}/ illustrations served at /media/...
│   └── tariikhna.db             SQLite database (the imported content)
└── frontend/                    Streamlit multipage app
    ├── streamlit_app.py         Home page
    ├── pages/1_📚_Stories.py     Library (grid of story cards)
    ├── pages/2_📖_Read_Story.py  Reader (scene image beside narrative text)
    └── storybook_api.py         shared API client + styling
```

## The data

The content comes from `Finalization/Examples/Corrected/`:

- **4 stories**, each a sequence of panels (scenes) with a `narrative_text`,
  `unit_title`, and per-scene `moral_lesson`.
- Each scene has **two illustration variants**: `base` (`output_base/images`) and
  `v1` (`output_v1/images`, richer prompts). The narrative is identical between
  them — only the artwork differs — so the Reader offers a **Storybook / Detailed**
  toggle to switch illustration sets.

| Story | Slug | Scenes | Ages |
|-------|------|--------|------|
| Abu Bakr's Noble Heart | `abu_bakr_frees_the_slaves` | 6 | 7–11 |
| Compassion | `mercy_even_to_enemies` | 5 | 8–12 |
| A Transfer of Care | `the_orphan_taken_in` | 6 | 6–10 |
| The First Muslim Man | `zayd_the_first_muslim_man` | 6 | 8–12 |

The importer copies the illustrations into `backend/media/`, so the backend is
**self-contained** and does not depend on the `Finalization/` folder at runtime.

---

## Setup & run (local)

From the `tariikhna/` folder:

```bash
# 1. one-time: create a virtualenv and install deps
py -V:3.10 -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt -r frontend/requirements.txt

# 2. one-time: import the corrected stories into the database
cd backend
../.venv/Scripts/python import_storybook.py
#   (custom source: ../.venv/Scripts/python import_storybook.py --source "C:/path/to/Corrected")

# 3. run the backend  (terminal 1, from backend/)
../.venv/Scripts/python -m uvicorn app.main:app --reload
#   API docs:   http://127.0.0.1:8000/docs

# 4. run the frontend (terminal 2, from frontend/)
../.venv/Scripts/python -m streamlit run streamlit_app.py
#   App:        http://localhost:8501
```

The frontend reads `TARIIKHNA_API_URL` (default `http://127.0.0.1:8000`) to find
the backend, so you can point it at a deployed API without code changes.

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
