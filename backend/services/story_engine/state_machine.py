"""
Story Engine — Job State Machine with strict transitions.
No fake completion states. Truth-based progression only.
"""
import logging
from typing import Optional, Dict
from datetime import datetime, timezone
from .schemas import JobState

logger = logging.getLogger("story_engine.state_machine")

# Valid state transitions — enforced strictly
VALID_TRANSITIONS: Dict[JobState, list] = {
    JobState.INIT: [JobState.PLANNING, JobState.FAILED],
    JobState.PLANNING: [JobState.BUILDING_CHARACTER_CONTEXT, JobState.FAILED],
    JobState.BUILDING_CHARACTER_CONTEXT: [JobState.PLANNING_SCENE_MOTION, JobState.FAILED],
    JobState.PLANNING_SCENE_MOTION: [JobState.GENERATING_KEYFRAMES, JobState.FAILED],
    JobState.GENERATING_KEYFRAMES: [JobState.GENERATING_SCENE_CLIPS, JobState.FAILED],
    JobState.GENERATING_SCENE_CLIPS: [JobState.GENERATING_AUDIO, JobState.FAILED],
    JobState.GENERATING_AUDIO: [JobState.ASSEMBLING_VIDEO, JobState.FAILED],
    JobState.ASSEMBLING_VIDEO: [JobState.VALIDATING, JobState.FAILED],
    JobState.VALIDATING: [JobState.READY, JobState.PARTIAL_READY, JobState.FAILED],
    JobState.READY: [],  # Terminal
    JobState.PARTIAL_READY: [JobState.GENERATING_SCENE_CLIPS, JobState.FAILED],  # Can retry missing clips
    JobState.FAILED: [JobState.INIT],  # Can retry from start
}

# Progress percentage per state
STATE_PROGRESS: Dict[JobState, int] = {
    JobState.INIT: 0,
    JobState.PLANNING: 8,
    JobState.BUILDING_CHARACTER_CONTEXT: 15,
    JobState.PLANNING_SCENE_MOTION: 22,
    JobState.GENERATING_KEYFRAMES: 35,
    JobState.GENERATING_SCENE_CLIPS: 60,
    JobState.GENERATING_AUDIO: 75,
    JobState.ASSEMBLING_VIDEO: 85,
    JobState.VALIDATING: 95,
    JobState.READY: 100,
    JobState.PARTIAL_READY: 90,
    JobState.FAILED: 0,
}

# Human-readable stage labels
STATE_LABELS: Dict[JobState, str] = {
    JobState.INIT: "Initializing",
    JobState.PLANNING: "Planning episode structure",
    JobState.BUILDING_CHARACTER_CONTEXT: "Building character continuity",
    JobState.PLANNING_SCENE_MOTION: "Planning scene motion",
    JobState.GENERATING_KEYFRAMES: "Generating keyframes",
    JobState.GENERATING_SCENE_CLIPS: "Generating moving scene clips",
    JobState.GENERATING_AUDIO: "Generating narration audio",
    JobState.ASSEMBLING_VIDEO: "Assembling final video",
    JobState.VALIDATING: "Validating outputs",
    JobState.READY: "Ready",
    JobState.PARTIAL_READY: "Partially ready — some scenes incomplete",
    JobState.FAILED: "Failed",
}


def can_transition(current: JobState, target: JobState) -> bool:
    """Check if a state transition is valid."""
    return target in VALID_TRANSITIONS.get(current, [])


def validate_transition(current: JobState, target: JobState) -> None:
    """Raise if transition is invalid."""
    if not can_transition(current, target):
        allowed = VALID_TRANSITIONS.get(current, [])
        raise ValueError(
            f"Invalid state transition: {current.value} → {target.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )


def get_progress(state: JobState) -> int:
    """Get progress percentage for a state."""
    return STATE_PROGRESS.get(state, 0)


def get_label(state: JobState) -> str:
    """Get human-readable label for a state."""
    return STATE_LABELS.get(state, state.value)


async def transition_job(db, job_id: str, target_state: JobState, error: Optional[str] = None) -> dict:
    """
    Atomically transition a job to a new state.
    Returns the updated job document.
    """
    now = datetime.now(timezone.utc).isoformat()

    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise ValueError(f"Job {job_id} not found")

    current = JobState(job["state"])
    validate_transition(current, target_state)

    update = {
        "$set": {
            "state": target_state.value,
            "updated_at": now,
        }
    }

    if error:
        update["$set"]["error_message"] = error

    if target_state == JobState.READY:
        update["$set"]["completed_at"] = now
    elif target_state == JobState.FAILED:
        update["$set"]["error_message"] = error or "Unknown failure"

    result = await db.story_engine_jobs.find_one_and_update(
        {"job_id": job_id, "state": current.value},  # Optimistic lock
        update,
        return_document=True,
    )

    if not result:
        raise ValueError(f"Concurrent modification on job {job_id} — state changed")

    logger.info(f"[STATE] Job {job_id[:8]}: {current.value} → {target_state.value}")
    return {k: v for k, v in result.items() if k != "_id"}
