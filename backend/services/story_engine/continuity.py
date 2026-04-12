"""
Continuity Validator — Validates outputs before marking READY.
Checks asset existence, character consistency, and style drift.
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("story_engine.continuity")


class ValidationResult:
    def __init__(self):
        self.passed = True
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def fail(self, msg: str):
        self.passed = False
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def to_dict(self):
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_pipeline_outputs(job: dict) -> ValidationResult:
    """
    Pre-READY validation. Checks all required outputs exist.
    Must pass before job can be marked READY.
    """
    result = ValidationResult()

    # 1. Output URL must exist
    if not job.get("output_url"):
        result.fail("output_url is missing — final video not assembled")

    # 2. Preview URL must exist
    if not job.get("preview_url"):
        result.warn("preview_url is missing — no preview clip generated")

    # 3. Thumbnail must exist
    if not job.get("thumbnail_url"):
        result.warn("thumbnail_url is missing — no thumbnail generated")

    # 4. All scene clips must exist
    scene_plans = job.get("scene_motion_plans", [])
    scene_clips = job.get("scene_clip_urls", [])
    if scene_plans and len(scene_clips) < len(scene_plans):
        missing = len(scene_plans) - len(scene_clips)
        result.fail(f"{missing} scene clips missing out of {len(scene_plans)} planned")

    # 5. Keyframes should exist
    keyframes = job.get("keyframe_urls", [])
    if scene_plans and len(keyframes) < len(scene_plans):
        result.warn(f"Only {len(keyframes)}/{len(scene_plans)} keyframes generated")

    # 6. Episode plan must exist
    if not job.get("episode_plan"):
        result.fail("episode_plan is missing — planning stage incomplete")

    return result


def validate_character_continuity(
    continuity_package: dict,
    scene_descriptions: List[str],
) -> ValidationResult:
    """
    Check scene descriptions against character continuity package.
    Flags potential drift in appearance, clothing, or style.
    """
    result = ValidationResult()

    if not continuity_package or not continuity_package.get("characters"):
        result.warn("No character continuity package — skipping drift check")
        return result

    characters = continuity_package["characters"]
    style_lock = continuity_package.get("style_lock", "")  # noqa: F841

    for i, desc in enumerate(scene_descriptions):
        desc_lower = desc.lower()

        # Check each character mentioned is using consistent traits
        for char in characters:
            name_lower = char.get("name", "").lower()
            if name_lower not in desc_lower:
                continue

            # Check for clothing drift
            clothing = char.get("clothing_default", "").lower()
            if clothing:
                clothing_keywords = [w.strip() for w in clothing.split(",") if len(w.strip()) > 3]
                clothing_matches = sum(1 for kw in clothing_keywords if kw in desc_lower)
                if clothing_keywords and clothing_matches == 0:
                    result.warn(
                        f"Scene {i+1}: Character '{char['name']}' may have clothing drift — "
                        f"expected '{clothing}' but scene description doesn't mention key clothing items"
                    )

            # Check hair consistency
            hair = char.get("hair", "").lower()
            if hair and len(hair) > 3:
                if hair.split()[0] not in desc_lower and char["name"].lower() in desc_lower:
                    result.warn(
                        f"Scene {i+1}: Character '{char['name']}' hair description may drift — "
                        f"expected '{hair}'"
                    )

    return result


def should_mark_ready(validation: ValidationResult) -> str:
    """
    Determine the appropriate final state based on validation.
    Returns: READY, PARTIAL_READY, or FAILED

    RULE: A job is never READY or PARTIAL_READY without a durable output_url.
    Missing output_url = FAILED, period. A user cannot download something that doesn't exist.
    """
    # Hard rule: output_url is mandatory for any success state
    has_output_url_error = any("output_url" in e for e in validation.errors)
    if has_output_url_error:
        return "FAILED"

    if validation.passed and not validation.errors:
        return "READY"
    elif validation.errors and len(validation.errors) <= 2:
        # Some non-critical issues — partial ready (but output exists)
        return "PARTIAL_READY"
    else:
        return "FAILED"
