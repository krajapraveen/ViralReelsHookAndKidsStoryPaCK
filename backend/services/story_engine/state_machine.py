"""
Story Engine — Job State Machine with strict transitions, heartbeat, and per-stage failure states.
"""
import logging
from typing import Optional, Dict
from datetime import datetime, timezone
from .schemas import JobState, ErrorCode, TERMINAL_STATES, ACTIVE_STATES, PER_STAGE_FAILURE_STATES

logger = logging.getLogger("story_engine.state_machine")

# ═══════════════════════════════════════════════════════════════
# VALID STATE TRANSITIONS — Enforced strictly
# ═══════════════════════════════════════════════════════════════

VALID_TRANSITIONS: Dict[JobState, list] = {
    # INIT can jump to any active state (for checkpoint reuse — skip already-done stages)
    JobState.INIT: [
        JobState.PLANNING, JobState.BUILDING_CHARACTER_CONTEXT,
        JobState.PLANNING_SCENE_MOTION, JobState.GENERATING_KEYFRAMES,
        JobState.GENERATING_SCENE_CLIPS, JobState.GENERATING_AUDIO,
        JobState.ASSEMBLING_VIDEO, JobState.FAILED,
    ],
    JobState.PLANNING: [JobState.BUILDING_CHARACTER_CONTEXT, JobState.FAILED_PLANNING, JobState.FAILED],
    JobState.BUILDING_CHARACTER_CONTEXT: [JobState.PLANNING_SCENE_MOTION, JobState.FAILED_PLANNING, JobState.FAILED],
    JobState.PLANNING_SCENE_MOTION: [JobState.GENERATING_KEYFRAMES, JobState.FAILED_PLANNING, JobState.FAILED],
    JobState.GENERATING_KEYFRAMES: [JobState.GENERATING_SCENE_CLIPS, JobState.FAILED_IMAGES, JobState.FAILED],
    JobState.GENERATING_SCENE_CLIPS: [JobState.GENERATING_AUDIO, JobState.FAILED_IMAGES, JobState.FAILED],
    JobState.GENERATING_AUDIO: [JobState.ASSEMBLING_VIDEO, JobState.FAILED_TTS, JobState.FAILED],
    JobState.ASSEMBLING_VIDEO: [JobState.VALIDATING, JobState.FAILED_RENDER, JobState.FAILED],
    JobState.VALIDATING: [JobState.READY, JobState.PARTIAL_READY, JobState.FAILED_RENDER, JobState.FAILED],
    JobState.READY: [],
    JobState.PARTIAL_READY: [JobState.GENERATING_SCENE_CLIPS, JobState.FAILED],
    # Per-stage failure → retry same stage group or go terminal
    JobState.FAILED_PLANNING: [JobState.PLANNING, JobState.FAILED],
    JobState.FAILED_IMAGES: [JobState.GENERATING_KEYFRAMES, JobState.FAILED],
    JobState.FAILED_TTS: [JobState.GENERATING_AUDIO, JobState.FAILED],
    JobState.FAILED_RENDER: [JobState.ASSEMBLING_VIDEO, JobState.FAILED],
    JobState.FAILED: [JobState.INIT],
}

# ═══════════════════════════════════════════════════════════════
# STAGE ORDERING — Defines the pipeline sequence
# ═══════════════════════════════════════════════════════════════

STAGE_ORDER = [
    JobState.PLANNING,
    JobState.BUILDING_CHARACTER_CONTEXT,
    JobState.PLANNING_SCENE_MOTION,
    JobState.GENERATING_KEYFRAMES,
    JobState.GENERATING_SCENE_CLIPS,
    JobState.GENERATING_AUDIO,
    JobState.ASSEMBLING_VIDEO,
    JobState.VALIDATING,
]

# Map active state → its per-stage failure state
STAGE_TO_FAILURE: Dict[JobState, JobState] = {
    JobState.PLANNING: JobState.FAILED_PLANNING,
    JobState.BUILDING_CHARACTER_CONTEXT: JobState.FAILED_PLANNING,
    JobState.PLANNING_SCENE_MOTION: JobState.FAILED_PLANNING,
    JobState.GENERATING_KEYFRAMES: JobState.FAILED_IMAGES,
    JobState.GENERATING_SCENE_CLIPS: JobState.FAILED_IMAGES,
    JobState.GENERATING_AUDIO: JobState.FAILED_TTS,
    JobState.ASSEMBLING_VIDEO: JobState.FAILED_RENDER,
    JobState.VALIDATING: JobState.FAILED_RENDER,
}

# Map per-stage failure → which stage to retry from
FAILURE_TO_RETRY: Dict[JobState, JobState] = {
    JobState.FAILED_PLANNING: JobState.PLANNING,
    JobState.FAILED_IMAGES: JobState.GENERATING_KEYFRAMES,
    JobState.FAILED_TTS: JobState.GENERATING_AUDIO,
    JobState.FAILED_RENDER: JobState.ASSEMBLING_VIDEO,
}

# Max retries per stage before terminal failure
STAGE_MAX_RETRIES: Dict[JobState, int] = {
    JobState.PLANNING: 4,
    JobState.BUILDING_CHARACTER_CONTEXT: 2,
    JobState.PLANNING_SCENE_MOTION: 2,
    JobState.GENERATING_KEYFRAMES: 2,
    JobState.GENERATING_SCENE_CLIPS: 2,
    JobState.GENERATING_AUDIO: 2,
    JobState.ASSEMBLING_VIDEO: 2,
    JobState.VALIDATING: 1,
}

# Heartbeat thresholds per stage (seconds) — beyond this, job is considered stale
HEARTBEAT_THRESHOLDS: Dict[str, int] = {
    "INIT": 60,
    "PLANNING": 180,
    "BUILDING_CHARACTER_CONTEXT": 120,
    "PLANNING_SCENE_MOTION": 120,
    "GENERATING_KEYFRAMES": 300,
    "GENERATING_SCENE_CLIPS": 600,
    "GENERATING_AUDIO": 240,
    "ASSEMBLING_VIDEO": 480,
    "VALIDATING": 60,
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
    JobState.FAILED_PLANNING: 0,
    JobState.FAILED_IMAGES: 0,
    JobState.FAILED_TTS: 0,
    JobState.FAILED_RENDER: 0,
}

# Human-readable stage labels — honest, not generic
STATE_LABELS: Dict[JobState, str] = {
    JobState.INIT: "Initializing",
    JobState.PLANNING: "Generating scenes",
    JobState.BUILDING_CHARACTER_CONTEXT: "Building character continuity",
    JobState.PLANNING_SCENE_MOTION: "Planning scene motion",
    JobState.GENERATING_KEYFRAMES: "Generating keyframes",
    JobState.GENERATING_SCENE_CLIPS: "Generating video clips",
    JobState.GENERATING_AUDIO: "Generating narration audio",
    JobState.ASSEMBLING_VIDEO: "Rendering final video",
    JobState.VALIDATING: "Validating outputs",
    JobState.READY: "Ready",
    JobState.PARTIAL_READY: "Partially complete — some scenes incomplete",
    JobState.FAILED: "Failed",
    JobState.FAILED_PLANNING: "Failed at scene generation",
    JobState.FAILED_IMAGES: "Failed at image/video generation",
    JobState.FAILED_TTS: "Failed at audio generation",
    JobState.FAILED_RENDER: "Failed at video rendering",
}


# ═══════════════════════════════════════════════════════════════
# CORE STATE MACHINE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def can_transition(current: JobState, target: JobState) -> bool:
    return target in VALID_TRANSITIONS.get(current, [])


def validate_transition(current: JobState, target: JobState) -> None:
    if not can_transition(current, target):
        allowed = VALID_TRANSITIONS.get(current, [])
        raise ValueError(
            f"Invalid state transition: {current.value} -> {target.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )


def get_progress(state: JobState) -> int:
    return STATE_PROGRESS.get(state, 0)


def get_label(state: JobState) -> str:
    return STATE_LABELS.get(state, state.value)


def get_next_stage(current: JobState) -> Optional[JobState]:
    """Get the next stage in the pipeline sequence."""
    try:
        idx = STAGE_ORDER.index(current)
        if idx < len(STAGE_ORDER) - 1:
            return STAGE_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def get_failure_state(stage: JobState) -> JobState:
    """Get the per-stage failure state for a given active stage."""
    return STAGE_TO_FAILURE.get(stage, JobState.FAILED)


async def transition_job(db, job_id: str, target_state: JobState, error: Optional[str] = None, error_code: Optional[str] = None) -> dict:
    """Atomically transition a job to a new state with optimistic locking."""
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
            "last_heartbeat_at": now,
        }
    }

    if error:
        update["$set"]["error_message"] = error
        update["$set"]["last_error_message"] = error
        update["$set"]["last_error_stage"] = current.value

    if error_code:
        update["$set"]["last_error_code"] = error_code

    if target_state == JobState.READY:
        update["$set"]["completed_at"] = now
    elif target_state in TERMINAL_STATES and target_state not in {JobState.READY, JobState.PARTIAL_READY}:
        update["$set"]["error_message"] = error or "Unknown failure"

    result = await db.story_engine_jobs.find_one_and_update(
        {"job_id": job_id, "state": current.value},
        update,
        return_document=True,
    )

    if not result:
        raise ValueError(f"Concurrent modification on job {job_id} - state changed")

    logger.info(f"[STATE] Job {job_id[:8]}: {current.value} -> {target_state.value}")
    return {k: v for k, v in result.items() if k != "_id"}


async def update_heartbeat(db, job_id: str, detail: Optional[str] = None) -> None:
    """Update job heartbeat timestamp. Called during active stage processing."""
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {"last_heartbeat_at": now, "updated_at": now}
    if detail:
        update_fields["heartbeat_detail"] = detail
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": update_fields},
    )


async def increment_stage_retry(db, job_id: str, stage: str) -> int:
    """Increment retry count for a specific stage. Returns new count."""
    result = await db.story_engine_jobs.find_one_and_update(
        {"job_id": job_id},
        {
            "$inc": {f"stage_retry_counts.{stage}": 1, "retry_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
        return_document=True,
    )
    if result:
        return result.get("stage_retry_counts", {}).get(stage, 1)
    return 0


def get_stage_retry_count(job: dict, stage: str) -> int:
    """Get current retry count for a stage from job document."""
    return job.get("stage_retry_counts", {}).get(stage, 0)
