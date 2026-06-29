"""
Import the corrected storybooks into the Tariikhna database.

Single illustration set (the "base" set) — one image + one narration clip per
scene, plus intro/conclusion narration. Source data lives in the separate
Graduation-Project repo:

    Graduation-Project/output_base/images/*.png          (--images)
    Graduation-Project/Finalization/Audio/output_base/
        stories/*.json   <- narrative + per-scene image_file/audio_file +        (--stories)
                            story_context.introduction_audio/conclusion_audio
        audio/*.mp3                                                               (--audio)

What this script does:
  1. Copies each panel illustration into backend/media/stories/ and each
     narration clip into backend/media/audio/, so the app is self-contained and
     can serve them under /media.
  2. Rebuilds the Story + Scene tables (old rows are throwaway pipeline test
     data) and inserts the corrected stories with their ordered panels.

Run it from the backend/ folder (so paths + the SQLite file resolve correctly).
With the default layout on disk, no args are needed:

    python import_storybook.py
    python import_storybook.py --images "C:/.../output_base/images" \
                               --stories "C:/.../Audio/output_base/stories" \
                               --audio   "C:/.../Audio/output_base/audio"

It is idempotent: re-running wipes media + tables and re-imports cleanly.
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

HERE = Path(__file__).resolve().parent                      # .../Tariikhna_app/backend
GP_ROOT = HERE.parent.parent / "Graduation-Project"         # sibling source repo
DEFAULT_IMAGES = GP_ROOT / "output_base" / "images"
DEFAULT_STORIES = GP_ROOT / "Finalization" / "Audio" / "output_base" / "stories"
DEFAULT_AUDIO = GP_ROOT / "Finalization" / "Audio" / "output_base" / "audio"


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _copy_media(src_dir: Path, filename: str, dest_dir: Path, prefix: str) -> str | None:
    """Copy one media file into the media tree and return its relative media path
    (e.g. 'stories/foo.png' or 'audio/foo.mp3'), or None if missing."""
    if not filename:
        return None
    src = src_dir / filename
    if not src.exists():
        print(f"    ! missing {prefix}: {src}")
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / filename)
    return f"{prefix}/{filename}"


def import_storybooks(images: Path, stories: Path, audio: Path) -> None:
    if not stories.exists():
        sys.exit(f"Stories folder not found: {stories}\n"
                 f"Pass the correct folders with --images / --stories / --audio.")

    story_files = sorted(stories.glob("*.json"))
    if not story_files:
        sys.exit(f"No story JSON files found in {stories}")

    media_root = Path(settings.media_dir)
    img_dest = media_root / "stories"
    aud_dest = media_root / "audio"

    # Wipe the media dirs this script manages so nothing stale is left behind
    # (e.g. the old base/v1 subfolders), then rebuild the tables.
    print("Clearing media + rebuilding Story + Scene tables...")
    shutil.rmtree(img_dest, ignore_errors=True)
    shutil.rmtree(aud_dest, ignore_errors=True)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    def copy_image(filename):
        return _copy_media(images, filename, img_dest, "stories")

    def copy_audio(filename):
        return _copy_media(audio, filename, aud_dest, "audio")

    with Session(engine) as session:
        for story_path in story_files:
            stem = story_path.stem
            data = _load_json(story_path)
            ctx = data.get("story_context", {})

            story = Story(
                title=data.get("display_title") or ctx.get("story_title") or stem,
                source_passage=data.get("source", ""),
                slug=data.get("passage_id") or stem,
                introduction=ctx.get("introduction"),
                conclusion=ctx.get("conclusion"),
                moral_lesson=ctx.get("moral_lesson"),
                reading_age=ctx.get("reading_age"),
                key_figures=ctx.get("key_figures", []),
                introduction_audio=copy_audio(ctx.get("introduction_audio")),
                conclusion_audio=copy_audio(ctx.get("conclusion_audio")),
            )
            session.add(story)
            session.commit()
            session.refresh(story)

            print(f"\n{story.title}  (slug={story.slug})")

            cover_rel = None
            for panel in data.get("panels", []):
                n = panel["panel_number"]
                image_rel = copy_image(panel.get("image_file"))
                audio_rel = copy_audio(panel.get("audio_file"))
                if cover_rel is None:
                    cover_rel = image_rel

                scene = Scene(
                    story_id=story.id,
                    scene_number=n,
                    title=panel.get("unit_title"),
                    narrative_text=panel.get("narrative_text"),
                    moral_lesson=panel.get("moral_lesson"),
                    schema_json=panel,
                    status="published",
                    image_url=image_rel,
                    audio_url=audio_rel,
                )
                session.add(scene)
                print(f"  panel {n}: {panel.get('unit_title')}  "
                      f"[img: {'yes' if image_rel else 'NO'}, "
                      f"audio: {'yes' if audio_rel else 'NO'}]")

            story.cover_image = cover_rel
            session.add(story)
            session.commit()

    print("\nDone. Stories imported into", settings.database_url)
    print("Media copied under:", media_root.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import the storybooks into the DB.")
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES,
                        help=f"Folder of panel PNGs (default: {DEFAULT_IMAGES})")
    parser.add_argument("--stories", type=Path, default=DEFAULT_STORIES,
                        help=f"Folder of story JSONs (default: {DEFAULT_STORIES})")
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO,
                        help=f"Folder of narration MP3s (default: {DEFAULT_AUDIO})")
    args = parser.parse_args()
    import_storybooks(args.images, args.stories, args.audio)
