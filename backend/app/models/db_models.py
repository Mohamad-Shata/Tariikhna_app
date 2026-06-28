"""
Database table definitions.

Two tables:
- Story: a published storybook (one adapted Sira passage / event). Holds the
  story-level context shown on the library + detail pages (title, intro,
  conclusion, moral, reading age, key figures, cover image).
- Scene: one comic panel inside a story — the narrative text shown beside the
  illustration, plus the illustration(s) themselves and the full schema JSON
  emitted by the pipeline.

Each Scene keeps BOTH illustration variants produced by the image pipeline:
  - image_url       -> the default illustration shown (base set)
  - image_variants  -> {"base": "<url>", "v1": "<url>"} so the reader can switch
                       between the two generated illustration sets.

The pipeline-oriented fields (schema_json, status, safety_notes) are kept so the
generation pipeline (routers/scenes.py) keeps working unchanged; the storybook
display only needs the explicit columns (title, narrative_text, ...).
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON


class Story(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    title: str                              # display_title shown to readers
    source_passage: str                     # source citation / raw passage

    # --- Storybook context (Layer-1 story_context) ----------------------------
    slug: Optional[str] = Field(default=None, index=True)  # passage_id, URL-safe
    introduction: Optional[str] = None
    conclusion: Optional[str] = None
    moral_lesson: Optional[str] = None
    reading_age: Optional[str] = None
    key_figures: list = Field(default=[], sa_column=Column(JSON))
    cover_image: Optional[str] = None       # relative media path of cover panel

    # Narration for the intro/conclusion text, per illustration variant:
    # {"base": "<path>", "v1": "<path>"}
    introduction_audio: dict = Field(default={}, sa_column=Column(JSON))
    conclusion_audio: dict = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Scene(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    story_id: int = Field(foreign_key="story.id")
    scene_number: int                       # panel_number, 1-based ordering

    # --- Storybook display fields (shown beside the illustration) -------------
    title: Optional[str] = None             # unit_title of the panel
    narrative_text: Optional[str] = None    # the text read beside the image
    moral_lesson: Optional[str] = None      # per-panel moral / takeaway

    # The full schema JSON produced by the pipeline (characters, image_prompt,
    # era, region, compliance, ...). Stored as JSON so nothing is lost.
    schema_json: dict = Field(default={}, sa_column=Column(JSON))

    # Pipeline status: draft -> safety_checked -> image_generated -> published
    status: str = Field(default="draft")

    # Default illustration (relative media path or absolute URL) + all variants.
    image_url: Optional[str] = None
    image_variants: dict = Field(default={}, sa_column=Column(JSON))

    # Narration of this panel's text, per illustration variant.
    audio_url: Optional[str] = None
    audio_variants: dict = Field(default={}, sa_column=Column(JSON))

    safety_notes: Optional[str] = None      # why something was flagged, if it was

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
