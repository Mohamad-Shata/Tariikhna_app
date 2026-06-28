"""
Import the corrected storybooks into the Tariikhna database.

Source data (the graduation "Finalization" examples):

    Finalization/Examples/Corrected/        (--source)
        output_base/stories/*.json     <- narrative + base illustration set
        output_base/images/*.png
        output_v1/stories/*_1.json      <- same narrative, richer illustration set
        output_v1/images/*.png

    Finalization/Audio/                      (--audio)
        output_base/stories/*.json     <- same stories + per-panel audio_file +
                                           story_context.introduction/conclusion_audio
        output_base/audio/*.mp3
        output_v1/...

What this script does:
  1. Copies every panel illustration into backend/media/stories/{base,v1}/ and
     every narration clip into backend/media/audio/{base,v1}/, so the backend is
     self-contained and can serve them under /media.
  2. Rebuilds the Story + Scene tables (the old rows are throwaway pipeline test
     data) and inserts the 4 corrected stories, each with its ordered panels and
     BOTH illustration + narration variants.

Story JSONs are read from the Audio folder when present (they carry both the
image and audio references); otherwise it falls back to the Corrected folder
(illustrations only, no narration).

Run it from the backend/ folder (so paths + the SQLite file resolve correctly):

    python import_storybook.py
    python import_storybook.py --source "C:/path/to/Corrected" --audio "C:/path/to/Audio"

It is idempotent: re-running wipes and re-imports cleanly.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from sqlmodel import SQLModel, Session

from app.config import settings
from app.database import engine
from app.models.db_models import Story, Scene

HERE = Path(__file__).resolve().parent                      # .../tariikhna/backend
REPO_ROOT = HERE.parent.parent                              # .../Graduation-Project
DEFAULT_SOURCE = REPO_ROOT / "Finalization" / "Examples" / "Corrected"
DEFAULT_AUDIO = REPO_ROOT / "Finalization" / "Audio"


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _copy_media(src_dir: Path, filename: str, dest_dir: Path, prefix: str) -> str | None:
    """Copy one media file into the media tree and return its relative media path
    (e.g. 'stories/base/foo.png' or 'audio/v1/foo.mp3'), or None if missing."""
    if not filename:
        return None
    src = src_dir / filename
    if not src.exists():
        print(f"    ! missing {prefix}: {src}")
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / filename)
    return f"{prefix}/{dest_dir.name}/{filename}"


def import_storybooks(source: Path, audio: Path) -> None:
    # Story JSONs: prefer the Audio folder (has both image + audio refs).
    def stories_dir(variant: str) -> Path:
        a = audio / f"output_{variant}" / "stories"
        return a if a.exists() else source / f"output_{variant}" / "stories"

    base_stories_dir = stories_dir("base")
    v1_stories_dir = stories_dir("v1")
    base_images_dir = source / "output_base" / "images"
    v1_images_dir = source / "output_v1" / "images"
    base_audio_dir = audio / "output_base" / "audio"
    v1_audio_dir = audio / "output_v1" / "audio"

    if not base_stories_dir.exists():
        sys.exit(f"Source not found: {base_stories_dir}\n"
                 f"Pass the correct folders with --source / --audio.")

    media_root = Path(settings.media_dir)
    img_base_dest = media_root / "stories" / "base"
    img_v1_dest = media_root / "stories" / "v1"
    aud_base_dest = media_root / "audio" / "base"
    aud_v1_dest = media_root / "audio" / "v1"

    def copy_image(src_dir, filename, dest_dir):
        return _copy_media(src_dir, filename, dest_dir, "stories")

    def copy_audio(src_dir, filename, dest_dir):
        return _copy_media(src_dir, filename, dest_dir, "audio")

    def variant_dict(base_val, v1_val):
        d = {}
        if base_val:
            d["base"] = base_val
        if v1_val:
            d["v1"] = v1_val
        return d

    base_files = sorted(base_stories_dir.glob("*.json"))
    if not base_files:
        sys.exit(f"No story JSON files found in {base_stories_dir}")

    # Fresh schema so the new columns exist, then wipe + reimport.
    print("Rebuilding Story + Scene tables...")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for base_path in base_files:
            stem = base_path.stem                      # e.g. abu_bakr_..._corrected
            base_json = _load_json(base_path)

            v1_path = v1_stories_dir / f"{stem}_1.json"
            v1_json = _load_json(v1_path) if v1_path.exists() else None
            v1_panels = {p["panel_number"]: p for p in (v1_json or {}).get("panels", [])}

            ctx = base_json.get("story_context", {})
            v1ctx = (v1_json or {}).get("story_context", {})

            intro_audio = variant_dict(
                copy_audio(base_audio_dir, ctx.get("introduction_audio"), aud_base_dest),
                copy_audio(v1_audio_dir, v1ctx.get("introduction_audio"), aud_v1_dest),
            )
            concl_audio = variant_dict(
                copy_audio(base_audio_dir, ctx.get("conclusion_audio"), aud_base_dest),
                copy_audio(v1_audio_dir, v1ctx.get("conclusion_audio"), aud_v1_dest),
            )

            story = Story(
                title=base_json.get("display_title") or ctx.get("story_title") or stem,
                source_passage=base_json.get("source", ""),
                slug=base_json.get("passage_id") or stem,
                introduction=ctx.get("introduction"),
                conclusion=ctx.get("conclusion"),
                moral_lesson=ctx.get("moral_lesson"),
                reading_age=ctx.get("reading_age"),
                key_figures=ctx.get("key_figures", []),
                introduction_audio=intro_audio,
                conclusion_audio=concl_audio,
            )
            session.add(story)
            session.commit()
            session.refresh(story)

            print(f"\n{story.title}  (slug={story.slug})")

            cover_rel = None
            for panel in base_json.get("panels", []):
                n = panel["panel_number"]
                v1_panel = v1_panels.get(n)

                img_variants = variant_dict(
                    copy_image(base_images_dir, panel.get("image_file"), img_base_dest),
                    copy_image(v1_images_dir, (v1_panel or {}).get("image_file"), img_v1_dest),
                )
                aud_variants = variant_dict(
                    copy_audio(base_audio_dir, panel.get("audio_file"), aud_base_dest),
                    copy_audio(v1_audio_dir, (v1_panel or {}).get("audio_file"), aud_v1_dest),
                )

                default_image = img_variants.get("base") or img_variants.get("v1")
                default_audio = aud_variants.get("base") or aud_variants.get("v1")
                if cover_rel is None:
                    cover_rel = default_image

                scene = Scene(
                    story_id=story.id,
                    scene_number=n,
                    title=panel.get("unit_title"),
                    narrative_text=panel.get("narrative_text"),
                    moral_lesson=panel.get("moral_lesson"),
                    schema_json=panel,
                    status="published",
                    image_url=default_image,
                    image_variants=img_variants,
                    audio_url=default_audio,
                    audio_variants=aud_variants,
                )
                session.add(scene)
                print(f"  panel {n}: {panel.get('unit_title')}  "
                      f"img[{', '.join(img_variants) or '-'}] "
                      f"audio[{', '.join(aud_variants) or '-'}]")

            story.cover_image = cover_rel
            session.add(story)
            session.commit()

    print("\nDone. Stories imported into", settings.database_url)
    print("Media copied under:", media_root.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import corrected storybooks into the DB.")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Path to the 'Corrected' folder, for images (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--audio",
        type=Path,
        default=DEFAULT_AUDIO,
        help=f"Path to the 'Audio' folder, for narration (default: {DEFAULT_AUDIO})",
    )
    args = parser.parse_args()
    import_storybooks(args.source, args.audio)
