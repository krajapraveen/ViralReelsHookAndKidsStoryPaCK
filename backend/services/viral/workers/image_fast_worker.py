"""
Image Fast Worker — processes thumbnail generation tasks
After completion, checks if all pre-packaging tasks are done.
"""
import os
import logging
from shared import db
from services.viral import viral_job_service as jobs
from services.viral.image_generation_service import generate_thumbnail
from services.viral.task_dispatch import dispatch_task, Q_PACKAGING

logger = logging.getLogger("viral.worker.image_fast")

THUMB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "static", "generated", "viral_thumbs")


async def handle_image_task(payload: dict):
    task_id = payload["task_id"]
    job_id = payload["job_id"]
    idea = payload["idea"]
    niche = payload["niche"]

    logger.info(f"[IMG_WORKER] Processing thumbnail task={task_id} job={job_id}")
    await jobs.update_job_phase(db, job_id, "generating_thumbnail")

    try:
        result = await generate_thumbnail(idea, niche)
        image_bytes = result["image_bytes"]

        os.makedirs(THUMB_DIR, exist_ok=True)
        filename = f"thumb_{job_id[:8]}_{task_id[:8]}.png"
        filepath = os.path.join(THUMB_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(image_bytes)

        file_url = f"/api/static/generated/viral_thumbs/{filename}"
        await jobs.save_asset(db, job_id, task_id, "thumbnail",
                              file_url=file_url, file_path=filepath, mime_type="image/png")
        await jobs.update_task(db, task_id, "completed", fallback_used=result["fallback_used"])
        logger.info(f"[IMG_WORKER] Thumbnail saved: {filepath}")

    except Exception as e:
        logger.error(f"[IMG_WORKER] Thumbnail failed completely: {e}", exc_info=True)
        # Save minimal fallback
        from services.viral.image_generation_service import _generate_fallback_thumbnail
        fb_bytes = _generate_fallback_thumbnail(idea, niche)
        os.makedirs(THUMB_DIR, exist_ok=True)
        filename = f"thumb_{job_id[:8]}_fb.png"
        filepath = os.path.join(THUMB_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(fb_bytes)
        file_url = f"/api/static/generated/viral_thumbs/{filename}"
        await jobs.save_asset(db, job_id, task_id, "thumbnail",
                              file_url=file_url, file_path=filepath, mime_type="image/png")
        await jobs.update_task(db, task_id, "completed", fallback_used=True)

    # Check if all pre-packaging tasks are done — atomic claim
    if await jobs.all_pretasks_done(db, job_id):
        pkg_task = await db.viral_job_tasks.find_one_and_update(
            {"job_id": job_id, "task_type": "packaging", "status": "pending"},
            {"$set": {"status": "processing"}},
            projection={"task_id": 1, "_id": 0},
        )
        if pkg_task:
            logger.info(f"[IMG_WORKER] Claimed packaging for job {job_id}")
            await dispatch_task(Q_PACKAGING, {
                "task_id": pkg_task["task_id"],
                "job_id": job_id,
            })
