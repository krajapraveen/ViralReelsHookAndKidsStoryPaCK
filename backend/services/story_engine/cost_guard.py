"""
Cost Guard — Pre-flight cost estimation and stage-level budget checks.
Never allow generation without sufficient credits.
"""
import logging
from typing import Dict
from .schemas import CostEstimate

logger = logging.getLogger("story_engine.cost_guard")

# Credit costs per stage
STAGE_COSTS = {
    "planning": 1,
    "character_context": 1,
    "scene_motion_planning": 1,
    "keyframes": 5,        # ~1 credit per keyframe, typical 5 scenes
    "scene_clips": 10,     # most expensive — GPU video generation
    "audio": 2,            # TTS generation
    "assembly": 1,         # FFmpeg assembly
    "validation": 0,
}

# Total default cost for a standard Story-to-Video job
DEFAULT_TOTAL_COST = sum(STAGE_COSTS.values())  # 21 credits


def estimate_cost(scene_count: int = 5, has_narration: bool = True) -> Dict[str, int]:
    """
    Estimate credits required based on scene count and options.
    Returns breakdown dict.
    """
    breakdown = {
        "planning": STAGE_COSTS["planning"],
        "character_context": STAGE_COSTS["character_context"],
        "scene_motion_planning": STAGE_COSTS["scene_motion_planning"],
        "keyframes": max(1, scene_count),  # 1 credit per keyframe
        "scene_clips": max(2, scene_count * 2),  # 2 credits per clip
        "audio": STAGE_COSTS["audio"] if has_narration else 0,
        "assembly": STAGE_COSTS["assembly"],
    }
    return breakdown


def pre_flight_check(user_credits: int, scene_count: int = 5, has_narration: bool = True) -> CostEstimate:
    """
    Pre-flight cost estimation. Called before any generation starts.
    Returns whether user has sufficient credits and exact shortfall.
    """
    breakdown = estimate_cost(scene_count, has_narration)
    total_required = sum(breakdown.values())
    sufficient = user_credits >= total_required
    shortfall = max(0, total_required - user_credits)

    estimate = CostEstimate(
        total_credits_required=total_required,
        breakdown=breakdown,
        user_current_credits=user_credits,
        sufficient=sufficient,
        shortfall=shortfall,
    )

    if not sufficient:
        logger.warning(
            f"[COST_GUARD] Insufficient credits: need {total_required}, have {user_credits}, shortfall {shortfall}"
        )

    return estimate


def check_stage_budget(job_credits_consumed: int, job_cost_estimate: int, stage: str) -> bool:
    """
    Stage-level budget check. Prevents runaway costs.
    Returns True if the stage can proceed within budget.
    """
    stage_cost = STAGE_COSTS.get(stage, 0)
    projected_total = job_credits_consumed + stage_cost

    # Allow 20% over-budget tolerance for retries
    budget_limit = int(job_cost_estimate * 1.2)

    if projected_total > budget_limit:
        logger.warning(
            f"[COST_GUARD] Stage '{stage}' would exceed budget: "
            f"consumed={job_credits_consumed}, stage_cost={stage_cost}, limit={budget_limit}"
        )
        return False

    return True
