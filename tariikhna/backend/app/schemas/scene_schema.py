"""
Request/response shapes for the API. Kept separate from the DB models
(app/models/db_models.py) so the API contract can evolve independently
of the storage layer.
"""
from typing import Optional
from pydantic import BaseModel


class NarrativeUnitInput(BaseModel):
    """Input to the scene-generation endpoint: one narrative unit from your
    Layer 1c output, ready to be converted into a schema + image_prompt."""
    story_id: int
    scene_number: int
    scene_summary: str
    key_visual_action: str
    characters_present: list[str]
    setting: str
    emotional_tone: str
    time_of_day: Optional[str] = None


class SceneSchemaOutput(BaseModel):
    """What the fine-tuned LLM returns — mirrors your training schema.
    Kept loose (dict-friendly) since your schema has nested objects
    (characters_present, setting, color_palette, etc.)."""
    scene_number: int
    scene_summary: str
    key_visual_action: str
    image_prompt: str
    characters_present: list[dict]
    setting: dict
    emotional_tone: str
    time_of_day: Optional[str] = None
    color_palette: Optional[dict] = None
    composition: Optional[dict] = None


class SafetyCheckResult(BaseModel):
    passed: bool
    notes: Optional[str] = None


class SceneResponse(BaseModel):
    id: int
    story_id: int
    scene_number: int
    schema_json: dict
    status: str
    image_url: Optional[str] = None
    safety_notes: Optional[str] = None