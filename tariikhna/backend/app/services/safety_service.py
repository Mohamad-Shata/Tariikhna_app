"""
Mirrors your pipeline's Layer 3 (safety filter), but applied as a *gate*
inside the API rather than a notebook step — every image_prompt must pass
this before it's sent to fal.ai.

Start with a deterministic keyword/pattern check (fast, free, no extra API
call) for the clearest violations of your Islamic depiction rules, and use
this as the place to plug in a model-based check later if you want one.
"""
import re
from app.schemas.scene_schema import SafetyCheckResult

# Words/phrases that should never appear in an image_prompt per your
# depiction rules. Extend this list as you find more violations during testing.
BANNED_PATTERNS = [
    r"\bprophet'?s face\b",
    r"\bshowing (his|the) face\b.*\bprophet\b",
    r"\bnude\b",
    r"\bbare (skin|chest|arms|legs)\b",
    r"\bblood\b",
    r"\bgraphic violence\b",
    r"\bweapon.*\bswinging\b",
]

REQUIRED_HINTS_FOR_PROPHET_SCENES = [
    "seen from behind",
    "back to camera",
    "obscured",
    "behind",
]


def check_image_prompt(image_prompt: str, characters_present: list[dict]) -> SafetyCheckResult:
    """
    image_prompt: the prompt string about to be sent to fal.ai
    characters_present: the schema's characters_present list, so we can check
                         that any prophet-role character is depicted correctly
    """
    lowered = image_prompt.lower()

    for pattern in BANNED_PATTERNS:
        if re.search(pattern, lowered):
            return SafetyCheckResult(
                passed=False,
                notes=f"Flagged banned pattern: '{pattern}'",
            )

    # If any character has a prophet-style depiction rule, make sure the
    # prompt actually reflects "shown from behind" / face-obscured language.
    has_prophet_role = any(
        "prophet" in str(c.get("role", "")).lower()
        or "never show face" in str(c.get("depiction_rule", "")).lower()
        for c in characters_present
    )
    if has_prophet_role:
        if not any(hint in lowered for hint in REQUIRED_HINTS_FOR_PROPHET_SCENES):
            return SafetyCheckResult(
                passed=False,
                notes="Scene includes a prophet-role character but the prompt "
                      "doesn't clearly specify a from-behind/obscured depiction.",
            )

    return SafetyCheckResult(passed=True, notes=None)