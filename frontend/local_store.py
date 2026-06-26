"""
Local data source — reads the bundled SQLite database and the illustrations on
disk directly, with no backend server.

This is what powers the single-service deployment (Streamlit Community Cloud):
the story data (`backend/tariikhna.db`) and images (`backend/media/`) are
committed to the repo, so the Streamlit app can read them straight from the
filesystem. The dict shapes returned here are identical to the FastAPI
`/library/...` responses, so the pages don't care which source is used — the
only difference is that image fields are local file paths instead of URLs
(st.image happily accepts either).
"""
import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "backend" / "tariikhna.db"
MEDIA_ROOT = REPO_ROOT / "backend" / "media"


def available() -> bool:
    """True if the bundled database is present (i.e. local mode is possible)."""
    return DB_PATH.exists()


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _loads(value, default):
    if not value:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _media_path(rel):
    """Absolute path to an illustration, or None if missing/blank."""
    if not rel:
        return None
    p = MEDIA_ROOT / rel
    return str(p) if p.exists() else None


def _variants_to_paths(variants: dict) -> dict:
    out = {}
    for key, rel in (variants or {}).items():
        path = _media_path(rel)
        if path:
            out[key] = path
    return out


def _story_summary(row: sqlite3.Row, panel_count: int) -> dict:
    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "source": row["source_passage"],
        "introduction": row["introduction"],
        "conclusion": row["conclusion"],
        "moral_lesson": row["moral_lesson"],
        "reading_age": row["reading_age"],
        "key_figures": _loads(row["key_figures"], []),
        "cover_image": _media_path(row["cover_image"]),
        "panel_count": panel_count,
    }


def _panel_payload(row: sqlite3.Row) -> dict:
    schema = _loads(row["schema_json"], {})
    return {
        "id": row["id"],
        "panel_number": row["scene_number"],
        "title": row["title"],
        "narrative_text": row["narrative_text"],
        "moral_lesson": row["moral_lesson"],
        "image_url": _media_path(row["image_url"]),
        "image_variants": _variants_to_paths(_loads(row["image_variants"], {})),
        "characters": schema.get("characters", []),
        "era": schema.get("era"),
        "region": schema.get("region"),
    }


def list_stories() -> list[dict]:
    with _connect() as con:
        stories = con.execute("SELECT * FROM story ORDER BY id").fetchall()
        out = []
        for s in stories:
            n = con.execute(
                "SELECT COUNT(*) AS c FROM scene WHERE story_id = ?", (s["id"],)
            ).fetchone()["c"]
            out.append(_story_summary(s, n))
        return out


def get_story(story_id: int) -> dict:
    with _connect() as con:
        s = con.execute("SELECT * FROM story WHERE id = ?", (story_id,)).fetchone()
        if not s:
            raise KeyError(f"Story {story_id} not found")
        panels = con.execute(
            "SELECT * FROM scene WHERE story_id = ? ORDER BY scene_number", (story_id,)
        ).fetchall()
        payload = _story_summary(s, len(panels))
        payload["panels"] = [_panel_payload(p) for p in panels]
        return payload
