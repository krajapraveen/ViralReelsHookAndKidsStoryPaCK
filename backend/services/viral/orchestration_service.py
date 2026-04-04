"""
Orchestration Service — creates child tasks and dispatches them in parallel
"""
import logging
from services.viral.viral_job_service import create_task, update_job_phase
from services.viral.task_dispatch import dispatch_task, Q_TEXT_FAST, Q_IMAGE_FAST

logger = logging.getLogger("viral.orchestration")


async def orchestrate_job(db, job_id: str, idea: str, niche: str):
    """
    Fan out from master job into parallel child tasks.
    Text tasks (hooks, script, captions) dispatch in parallel.
    Image task dispatches in parallel with text.
    Packaging is triggered by the last completing pre-task.
    """
    await update_job_phase(db, job_id, "planning")

    # Create child tasks
    hook_task_id = await create_task(db, job_id, "hooks")
    script_task_id = await create_task(db, job_id, "script")
    caption_task_id = await create_task(db, job_id, "captions")
    thumb_task_id = await create_task(db, job_id, "thumbnail")
    await create_task(db, job_id, "packaging")

    logger.info(f"[ORCH] Created 5 child tasks for job {job_id}")

    # Dispatch ALL in parallel — text + image simultaneously
    await dispatch_task(Q_TEXT_FAST, {
        "task_id": hook_task_id, "job_id": job_id,
        "task_type": "hooks", "idea": idea, "niche": niche,
    })
    await dispatch_task(Q_TEXT_FAST, {
        "task_id": script_task_id, "job_id": job_id,
        "task_type": "script", "idea": idea, "niche": niche,
    })
    await dispatch_task(Q_TEXT_FAST, {
        "task_id": caption_task_id, "job_id": job_id,
        "task_type": "captions", "idea": idea, "niche": niche,
    })
    await dispatch_task(Q_IMAGE_FAST, {
        "task_id": thumb_task_id, "job_id": job_id,
        "task_type": "thumbnail", "idea": idea, "niche": niche,
    })

    logger.info(f"[ORCH] All tasks dispatched for job {job_id}")
