"""
Orchestrates the full per-scene pipeline:

  narrative unit -> LLM generates schema (incl. image_prompt)
                 -> safety check on image_prompt
                 -> if passed: fal.ai generates image
                 -> persist everything to the database

This is the only place that calls all three services together, so the
routers stay thin and this logic can be tested or reused (e.g. from a
batch script) without going through HTTP at all.
"""
from sqlmodel import Session
from app.models.db_models import Scene
from app.services import llm_service, safety_service, image_service


def run_scene_pipeline(narrative_unit: dict, session: Session) -> Scene:
    """
    narrative_unit: dict matching NarrativeUnitInput (must include story_id,
                     scene_number, and the Layer 1c fields)
    session: an open DB session (from the get_session dependency)

    returns: the saved Scene row, with status reflecting how far it got:
             "safety_rejected" | "image_failed" | "image_generated"
    """
    # 1. Generate the schema (this is your fine-tuned model's job)
    schema = llm_service.generate_scene_schema(narrative_unit)

    scene = Scene(
        story_id=narrative_unit["story_id"],
        scene_number=narrative_unit["scene_number"],
        schema_json=schema,
        status="draft",
    )
    session.add(scene)
    session.commit()
    session.refresh(scene)

    # 2. Safety check the image_prompt BEFORE spending money/time on fal.ai
    image_prompt = schema.get("image_prompt", "")
    characters = schema.get("characters_present", [])
    safety_result = safety_service.check_image_prompt(image_prompt, characters)

    if not safety_result.passed:
        scene.status = "safety_rejected"
        scene.safety_notes = safety_result.notes
        session.add(scene)
        session.commit()
        session.refresh(scene)
        return scene

    # 3. Generate the image
    try:
        image_url = image_service.generate_image(image_prompt)
        scene.image_url = image_url
        scene.status = "image_generated"
    except Exception as exc:
        scene.status = "image_failed"
        scene.safety_notes = f"Image generation error: {exc}"

    session.add(scene)
    session.commit()
    session.refresh(scene)
    return scene