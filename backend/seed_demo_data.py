"""
One-off seeding script for the demo.

What it does:
  1. Creates 5 Story rows (one per golden passage) via POST /stories/
  2. Reads golden_narrative_units.json and calls POST /scenes/generate
     for each one, in order
  3. Prints the result of each step so you can see what succeeded/failed

Run this AFTER your backend is already running (uvicorn app.main:app --reload)
and your .env has a working LLM_REMOTE_URL + FAL_KEY, since this calls the
real pipeline (LLM -> safety -> image) for each scene.

Usage (from the backend/ folder, with venv activated):
    python seed_demo_data.py
"""
import json
import httpx

API_BASE = "http://127.0.0.1:8000"

# Maps story_id (as used in golden_narrative_units.json) to a title/passage,
# pulled from your golden_passages_selected.json. These MUST be created
# first so the foreign key in Scene.story_id has something to point to.
STORIES = [
    {
        "id_placeholder": 1,
        "title": "A Transfer of Care",
        "source_passage": "Abd al-Muttalib entrusts young Muhammad to the care of Abu Talib before his death.",
    },
    {
        "id_placeholder": 2,
        "title": "The First Muslim Man",
        "source_passage": "Zayd ibn Harithah chooses to remain with Muhammad rather than return to his birth family.",
    },
    {
        "id_placeholder": 3,
        "title": "Abu Bakr's Noble Heart (Part 1)",
        "source_passage": "Abu Bakr purchases Zunayrah's freedom from a cruel master.",
    },
    {
        "id_placeholder": 4,
        "title": "Abu Bakr's Noble Heart (Part 2)",
        "source_passage": "Abu Bakr's father questions his choice to free only weak slaves.",
    },
    {
        "id_placeholder": 5,
        "title": "Compassion",
        "source_passage": "The Prophet teaches Bilal mercy, even toward fallen enemies, after the Battle of Khaybar.",
    },
]


def create_stories() -> dict:
    """Creates each story and returns a mapping from the placeholder id
    used in golden_narrative_units.json to the REAL database id."""
    id_map = {}
    with httpx.Client(base_url=API_BASE, timeout=30.0) as client:
        for story in STORIES:
            payload = {
                "title": story["title"],
                "source_passage": story["source_passage"],
            }
            response = client.post("/stories/", json=payload)
            response.raise_for_status()
            real_id = response.json()["id"]
            id_map[story["id_placeholder"]] = real_id
            print(f"Created story '{story['title']}' -> id {real_id}")
    return id_map


def generate_scenes(id_map: dict):
    """Reads golden_narrative_units.json, remaps story_id to the real
    database ids, and POSTs each one to /scenes/generate."""
    with open("golden_narrative_units.json", "r", encoding="utf-8") as f:
        narrative_units = json.load(f)

    with httpx.Client(base_url=API_BASE, timeout=180.0) as client:
        for unit in narrative_units:
            placeholder_id = unit["story_id"]
            unit["story_id"] = id_map[placeholder_id]

            print(f"\nGenerating scene for story_id={unit['story_id']} "
                  f"({unit['scene_summary'][:60]}...)")
            try:
                response = client.post("/scenes/generate", json=unit)
                response.raise_for_status()
                result = response.json()
                print(f"  -> status: {result['status']}")
                if result.get("image_url"):
                    print(f"  -> image: {result['image_url']}")
                if result.get("safety_notes"):
                    print(f"  -> notes: {result['safety_notes']}")
            except httpx.HTTPStatusError as exc:
                print(f"  -> FAILED: {exc.response.status_code} {exc.response.text}")
            except Exception as exc:
                print(f"  -> FAILED: {exc}")


if __name__ == "__main__":
    print("== Step 1: creating stories ==")
    id_map = create_stories()

    print("\n== Step 2: generating scenes ==")
    generate_scenes(id_map)

    print("\nDone. Check results at http://127.0.0.1:8000/docs "
          "(GET /scenes/story/{story_id}) or in your DB browser.")