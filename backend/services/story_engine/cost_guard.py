"""
Cost Guard — Pre-flight cost estimation AND runtime budget enforcement.
Called before EVERY external call. Not dead code.
"""
import logging
from typing import Dict
from .schemas import CostEstimate, ErrorCode

logger = logging.getLogger("story_engine.cost_guard")

# Credit costs per stage
STAGE_COSTS = {
    "planning": 1,
    "character_context": 1,
    "scene_motion_planning": 1,
    "keyframes": 5,
    "scene_clips": 10,
    "audio": 2,
    "assembly": 1,
    "validation": 0,
}

DEFAULT_TOTAL_COST = sum(STAGE_COSTS.values())

# Map JobState values to stage cost keys
STATE_TO_COST_KEY = {
    "PLANNING": "planning",
    "BUILDING_CHARACTER_CONTEXT": "character_context",
    "PLANNING_SCENE_MOTION": "scene_motion_planning",
    "GENERATING_KEYFRAMES": "keyframes",
    "GENERATING_SCENE_CLIPS": "scene_clips",
    "GENERATING_AUDIO": "audio",
    "ASSEMBLING_VIDEO": "assembly",
    "VALIDATING": "validation",
}


def estimate_cost(scene_count: int = 5, has_narration: bool = True) -> Dict[str, int]:
    breakdown = {
        "planning": STAGE_COSTS["planning"],
        "character_context": STAGE_COSTS["character_context"],
        "scene_motion_planning": STAGE_COSTS["scene_motion_planning"],
        "keyframes": max(1, scene_count),
        "scene_clips": max(2, scene_count * 2),
        "audio": STAGE_COSTS["audio"] if has_narration else 0,
        "assembly": STAGE_COSTS["assembly"],
    }
    return breakdown


def pre_flight_check(user_credits: int, scene_count: int = 5, has_narration: bool = True) -> CostEstimate:
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
    """Stage-level budget check. Returns True if within budget."""
    stage_cost = STAGE_COSTS.get(stage, 0)
    projected_total = job_credits_consumed + stage_cost
    budget_limit = int(job_cost_estimate * 1.2)

    if projected_total > budget_limit:
        logger.warning(
            f"[COST_GUARD] Stage '{stage}' would exceed budget: "
            f"consumed={job_credits_consumed}, stage_cost={stage_cost}, limit={budget_limit}"
        )
        return False

    return True


class BudgetExceededError(Exception):
    """Raised when runtime budget guard blocks a stage."""
    def __init__(self, stage: str, consumed: int, limit: int):
        self.stage = stage
        self.consumed = consumed
        self.limit = limit
        self.error_code = ErrorCode.BUDGET_EXCEEDED_RUNTIME
        super().__init__(f"Budget exceeded at stage '{stage}': consumed={consumed}, limit={limit}")


def enforce_runtime_budget(job: dict, stage_state: str) -> None:
    """
    Runtime budget guard. Called before every external API call.
    Raises BudgetExceededError if the job would exceed its budget.
    """
    cost_estimate = job.get("cost_estimate", {})
    max_budget = cost_estimate.get("total_credits_required", DEFAULT_TOTAL_COST)
    consumed = job.get("total_credits_consumed", 0)
    cost_key = STATE_TO_COST_KEY.get(stage_state, "")
    stage_cost = STAGE_COSTS.get(cost_key, 0)

    # Allow 30% over-budget for retries and fallbacks
    hard_limit = int(max_budget * 1.3)
    projected = consumed + stage_cost

    if projected > hard_limit:
        logger.error(
            f"[COST_GUARD] RUNTIME BUDGET EXCEEDED at {stage_state}: "
            f"consumed={consumed}, stage_cost={stage_cost}, projected={projected}, limit={hard_limit}"
        )
        raise BudgetExceededError(stage_state, consumed, hard_limit)

    logger.debug(f"[COST_GUARD] Budget OK for {stage_state}: {projected}/{hard_limit}")
