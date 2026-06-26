"""
Endpoints for generating and retrieving scenes.

POST /scenes/generate  is the main one: takes a narrative unit, runs the
full pipeline (LLM -> safety -> image), and returns the saved scene.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.db_models import Scene
from app.schemas.scene_schema import NarrativeUnitInput
from app.services.pipeline_service import run_scene_pipeline

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.post("/generate", response_model=Scene)
def generate_scene(
    narrative_unit: NarrativeUnitInput,
    session: Session = Depends(get_session),
):
    """Runs the full pipeline for one scene: LLM schema generation,
    safety check, image generation, and persistence."""
    scene = run_scene_pipeline(narrative_unit.model_dump(), session)
    return scene


@router.get("/story/{story_id}", response_model=list[Scene])
def list_scenes_for_story(story_id: int, session: Session = Depends(get_session)):
    """Returns all scenes for a story, in order — this is what the
    Streamlit comic reader view will call."""
    statement = (
        select(Scene)
        .where(Scene.story_id == story_id)
        .order_by(Scene.scene_number)
    )
    return session.exec(statement).all()


@router.get("/{scene_id}", response_model=Scene)
def get_scene(scene_id: int, session: Session = Depends(get_session)):
    scene = session.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.post("/{scene_id}/regenerate-image", response_model=Scene)
def regenerate_image(scene_id: int, session: Session = Depends(get_session)):
    """Re-runs only the image generation step for an existing scene —
    useful when the schema/prompt is fine but the image itself didn't
    turn out well."""
    from app.services import image_service, safety_service

    scene = session.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    image_prompt = scene.schema_json.get("image_prompt", "")
    characters = scene.schema_json.get("characters_present", [])
    safety_result = safety_service.check_image_prompt(image_prompt, characters)

    if not safety_result.passed:
        scene.status = "safety_rejected"
        scene.safety_notes = safety_result.notes
    else:
        try:
            scene.image_url = image_service.generate_image(image_prompt)
            scene.status = "image_generated"
            scene.safety_notes = None
        except Exception as exc:
            scene.status = "image_failed"
            scene.safety_notes = f"Image generation error: {exc}"

    session.add(scene)
    session.commit()
    session.refresh(scene)
    return scene