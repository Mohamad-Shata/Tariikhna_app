"""
Import the corrected storybooks into the Tariikhna database.

Source data (the graduation "Finalization" examples):

    Finalization/Examples/Corrected/
        output_base/stories/*.json     <- narrative + base illustration set
        output_base/images/*.png
        output_v1/stories/*_1.json      <- same narrative, richer illustration set
        output_v1/images/*.png

What this script does:
  1. Copies every panel illustration into backend/media/stories/{base,v1}/ so
     the backend is self-contained and can serve them under /media.
  2. Rebuilds the Story + Scene tables (the old rows are throwaway pipeline test
     data) and inserts the 4 corrected stories, each with its ordered panels and
     BOTH illustration variants.

Run it from the backend/ folder (so paths + the SQLite file resolve correctly):

    python import_storybook.py
    python import_storybook.py --source "C:/path/to/Corrected"   # custom source

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


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _copy_image(src_dir: Path, filename: str, dest_dir: Path) -> str | None:
    """Copy one illustration into the media tree and return its relative
    media path (e.g. 'stories/base/foo.png'), or None if the source is missing."""
    if not filename:
        return None
    src = src_dir / filename
    if not src.exists():
        print(f"    ! missing image: {src}")
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / filename)
    # media path relative to the media root: stories/<variant>/<file>
    return f"stories/{dest_dir.name}/{filename}"


def import_storybooks(source: Path) -> None:
    base_stories_dir = source / "output_base" / "stories"
    base_images_dir = source / "output_base" / "images"
    v1_stories_dir = source / "output_v1" / "stories"
    v1_images_dir = source / "output_v1" / "images"

    if not base_stories_dir.exists():
        sys.exit(f"Source not found: {base_stories_dir}\n"
                 f"Pass the correct folder with --source.")

    media_root = Path(settings.media_dir)
    base_dest = media_root / "stories" / "base"
    v1_dest = media_root / "stories" / "v1"

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
            story = Story(
                title=base_json.get("display_title") or ctx.get("story_title") or stem,
                source_passage=base_json.get("source", ""),
                slug=base_json.get("passage_id") or stem,
                introduction=ctx.get("introduction"),
                conclusion=ctx.get("conclusion"),
                moral_lesson=ctx.get("moral_lesson"),
                reading_age=ctx.get("reading_age"),
                key_figures=ctx.get("key_figures", []),
            )
            session.add(story)
            session.commit()
            session.refresh(story)

            print(f"\n{story.title}  (slug={story.slug})")

            cover_rel = None
            for panel in base_json.get("panels", []):
                n = panel["panel_number"]

                base_rel = _copy_image(base_images_dir, panel.get("image_file"), base_dest)

                v1_panel = v1_panels.get(n)
                v1_rel = None
                if v1_panel:
                    v1_rel = _copy_image(v1_images_dir, v1_panel.get("image_file"), v1_dest)

                variants = {}
                if base_rel:
                    variants["base"] = base_rel
                if v1_rel:
                    variants["v1"] = v1_rel

                default_image = base_rel or v1_rel
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
                    image_variants=variants,
                )
                session.add(scene)
                print(f"  panel {n}: {panel.get('unit_title')}  "
                      f"[{', '.join(variants.keys()) or 'no image'}]")

            story.cover_image = cover_rel
            session.add(story)
            session.commit()

    print("\nDone. Stories imported into", settings.database_url)
    print("Illustrations copied under:", media_root.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import corrected storybooks into the DB.")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Path to the 'Corrected' folder (default: {DEFAULT_SOURCE})",
    )
    args = parser.parse_args()
    import_storybooks(args.source)
