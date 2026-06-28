"""
Read-only endpoints that power the storybook reader (Streamlit frontend).

These return display-ready, nested payloads so the frontend can render a page
with a single call:

  GET /library/stories                 -> list of story cards (summaries)
  GET /library/stories/{story_id}      -> one story + its ordered panels
  GET /library/stories/by-slug/{slug}  -> same, looked up by slug (passage_id)

Illustration paths are stored relative (e.g. "stories/base/foo.png") and turned
into absolute URLs here, based on the incoming request, so they work no matter
what host/port the backend runs on.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from app.database import get_session
from app.models.db_models import Story, Scene

router = APIRouter(prefix="/library", tags=["library"])


def _media_url(request: Request, path: Optional[str]) -> Optional[str]:
    """Turn a stored media path into an absolute URL the browser can load.

    Absolute URLs (http...) are passed through unchanged so externally hosted
    images (e.g. fal.ai output) still work."""
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = str(request.base_url).rstrip("/")
    return f"{base}/media/{path.lstrip('/')}"


def _variants_to_urls(request: Request, variants: dict) -> dict:
    return {k: _media_url(request, v) for k, v in (variants or {}).items()}


def _story_summary(request: Request, story: Story, panel_count: int) -> dict:
    return {
        "id": story.id,
        "slug": story.slug,
        "title": story.title,
        "source": story.source_passage,
        "introduction": story.introduction,
        "conclusion": story.conclusion,
        "moral_lesson": story.moral_lesson,
        "reading_age": story.reading_age,
        "key_figures": story.key_figures or [],
        "cover_image": _media_url(request, story.cover_image),
        "introduction_audio": _variants_to_urls(request, story.introduction_audio),
        "conclusion_audio": _variants_to_urls(request, story.conclusion_audio),
        "panel_count": panel_count,
    }


def _panel_payload(request: Request, scene: Scene) -> dict:
    return {
        "id": scene.id,
        "panel_number": scene.scene_number,
        "title": scene.title,
        "narrative_text": scene.narrative_text,
        "moral_lesson": scene.moral_lesson,
        "image_url": _media_url(request, scene.image_url),
        "image_variants": _variants_to_urls(request, scene.image_variants),
        "audio_url": _media_url(request, scene.audio_url),
        "audio_variants": _variants_to_urls(request, scene.audio_variants),
        "characters": scene.schema_json.get("characters", []),
        "era": scene.schema_json.get("era"),
        "region": scene.schema_json.get("region"),
    }


@router.get("/stories")
def list_library_stories(request: Request, session: Session = Depends(get_session)):
    """All stories as lightweight cards for the library grid."""
    stories = session.exec(select(Story).order_by(Story.id)).all()
    out = []
    for story in stories:
        panel_count = len(
            session.exec(select(Scene).where(Scene.story_id == story.id)).all()
        )
        out.append(_story_summary(request, story, panel_count))
    return out


def _full_story(request: Request, story: Story, session: Session) -> dict:
    panels = session.exec(
        select(Scene)
        .where(Scene.story_id == story.id)
        .order_by(Scene.scene_number)
    ).all()
    payload = _story_summary(request, story, len(panels))
    payload["panels"] = [_panel_payload(request, p) for p in panels]
    return payload


@router.get("/stories/{story_id}")
def get_library_story(
    story_id: int, request: Request, session: Session = Depends(get_session)
):
    """One story plus its ordered panels — everything the detail page needs."""
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return _full_story(request, story, session)


@router.get("/stories/by-slug/{slug}")
def get_library_story_by_slug(
    slug: str, request: Request, session: Session = Depends(get_session)
):
    story = session.exec(select(Story).where(Story.slug == slug)).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return _full_story(request, story, session)
