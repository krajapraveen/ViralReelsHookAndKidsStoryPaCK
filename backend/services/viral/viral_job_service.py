"""
Viral Job Service — CRUD for jobs, tasks, assets, events
"""
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger("viral.job_service")

PHASES = [
    "planning", "generating_hooks", "generating_script", "generating_captions",
    "generating_thumbnail", "generating_audio", "generating_video", "packaging", "ready",
]
FRIENDLY_MESSAGES = {
    "planning": "Setting up your content pack...",
    "generating_hooks": "Crafting viral hooks...",
    "generating_script": "Writing your script...",
    "generating_captions": "Creating social captions...",
    "generating_thumbnail": "Designing your thumbnail...",
    "generating_audio": "Recording voiceover...",
    "generating_video": "Composing your video...",
    "packaging": "Finalizing your pack...",
    "ready": "Your pack is ready!",
    "recovering": "Optimizing your output...",
    "fallback": "Preparing an alternative version...",
    "finalizing": "Finalizing your pack...",
}

PHASE1_TASK_TYPES = {"hooks", "script", "captions", "thumbnail"}


async def create_job(db, user_id: str, idea: str, niche: str, locked: bool = False) -> dict:
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "job_id": job_id,
        "user_id": user_id,
        "idea": idea,
        "niche": niche,
        "status": "pending",
        "locked": locked,
        "progress": {
            "current_phase": "planning",
            "phases_completed": [],
            "percentage": 0,
            "message": FRIENDLY_MESSAGES["planning"],
        },
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    await db.viral_jobs.insert_one(job)
    await log_event(db, job_id, "job_created", "Job created")
    return {"job_id": job_id}


async def get_job(db, job_id: str) -> dict | None:
    return await db.viral_jobs.find_one({"job_id": job_id}, {"_id": 0})


async def get_user_jobs(db, user_id: str, limit: int = 20) -> list:
    return await db.viral_jobs.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)


async def update_job_phase(db, job_id: str, phase: str, percentage: int = None):
    if percentage is None:
        idx = PHASES.index(phase) if phase in PHASES else 0
        percentage = int((idx / (len(PHASES) - 1)) * 100)
    message = FRIENDLY_MESSAGES.get(phase, "Processing...")
    update = {
        "$set": {
            "progress.current_phase": phase,
            "progress.percentage": percentage,
            "progress.message": message,
            "updated_at": datetime.now(timezone.utc),
        },
        "$addToSet": {"progress.phases_completed": phase},
    }
    if phase == "ready":
        update["$set"]["status"] = "completed"
        update["$set"]["completed_at"] = datetime.now(timezone.utc)
    elif phase not in ("planning",):
        update["$set"]["status"] = "processing"
    await db.viral_jobs.update_one({"job_id": job_id}, update)
    await log_event(db, job_id, "phase_changed", f"Phase: {phase}")


async def mark_job_failed(db, job_id: str):
    await db.viral_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "status": "completed_with_fallbacks",
            "progress.current_phase": "ready",
            "progress.percentage": 100,
            "progress.message": "Your pack is ready!",
            "updated_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc),
        }}
    )


async def create_task(db, job_id: str, task_type: str) -> str:
    task_id = str(uuid.uuid4())
    await db.viral_job_tasks.insert_one({
        "task_id": task_id,
        "job_id": job_id,
        "task_type": task_type,
        "status": "pending",
        "fallback_used": False,
        "attempts": 0,
        "failure_reason": None,
        "created_at": datetime.now(timezone.utc),
        "completed_at": None,
    })
    return task_id


async def update_task(db, task_id: str, status: str, fallback_used: bool = False, failure_reason: str = None):
    update = {
        "$set": {
            "status": status,
            "fallback_used": fallback_used,
            "completed_at": datetime.now(timezone.utc) if status in ("completed", "failed") else None,
        },
        "$inc": {"attempts": 1},
    }
    if failure_reason:
        update["$set"]["failure_reason"] = failure_reason
    await db.viral_job_tasks.update_one({"task_id": task_id}, update)


async def get_tasks_for_job(db, job_id: str) -> list:
    return await db.viral_job_tasks.find({"job_id": job_id}, {"_id": 0}).to_list(20)


async def all_phase1_done(db, job_id: str) -> bool:
    """Check if all Phase 1 tasks (hooks, script, captions, thumbnail) are done."""
    pending = await db.viral_job_tasks.count_documents({
        "job_id": job_id,
        "task_type": {"$in": list(PHASE1_TASK_TYPES)},
        "status": {"$nin": ["completed", "failed"]},
    })
    return pending == 0


async def all_pretasks_done(db, job_id: str) -> bool:
    """Check if ALL non-packaging tasks are done (Phase 1 + Phase 2)."""
    pending = await db.viral_job_tasks.count_documents({
        "job_id": job_id,
        "task_type": {"$ne": "packaging"},
        "status": {"$nin": ["completed", "failed"]},
    })
    return pending == 0


async def save_asset(db, job_id: str, task_id: str, asset_type: str,
                     content: str = None, file_url: str = None,
                     file_path: str = None, mime_type: str = "text/plain") -> str:
    asset_id = str(uuid.uuid4())
    await db.viral_assets.insert_one({
        "asset_id": asset_id,
        "job_id": job_id,
        "task_id": task_id,
        "asset_type": asset_type,
        "content": content,
        "file_url": file_url,
        "file_path": file_path,
        "mime_type": mime_type,
        "created_at": datetime.now(timezone.utc),
    })
    return asset_id


async def get_assets(db, job_id: str) -> list:
    return await db.viral_assets.find({"job_id": job_id}, {"_id": 0}).to_list(50)


async def log_event(db, job_id: str, event_type: str, message: str):
    await db.viral_job_events.insert_one({
        "event_id": str(uuid.uuid4()),
        "job_id": job_id,
        "event_type": event_type,
        "message": message,
        "timestamp": datetime.now(timezone.utc),
    })
