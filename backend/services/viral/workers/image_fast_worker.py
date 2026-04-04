"""
Image Fast Worker — processes thumbnail generation tasks.
After completion, checks if Phase 1 is done → dispatches audio + video.
"""
import os
import logging
from shared import db
from services.viral import viral_job_service as jobs
from services.viral.image_generation_service import generate_thumbnail
from services.viral.task_dispatch import dispatch_task, Q_AUDIO_FAST, Q_VIDEO_FAST

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

    # Check if Phase 1 is done → dispatch Phase 2
    await _check_phase1_and_dispatch_phase2(job_id, idea, niche)


async def _check_phase1_and_dispatch_phase2(job_id: str, idea: str, niche: str):
    if await jobs.all_phase1_done(db, job_id):
        claimed = await db.viral_jobs.find_one_and_update(
            {"job_id": job_id, "_phase2_dispatched": {"$ne": True}},
            {"$set": {"_phase2_dispatched": True}},
        )
        if claimed:
            logger.info(f"[IMG_WORKER] Phase 1 done for job {job_id}, dispatching audio + video")
            audio_task = await db.viral_job_tasks.find_one(
                {"job_id": job_id, "task_type": "audio"}, {"task_id": 1}
            )
            video_task = await db.viral_job_tasks.find_one(
                {"job_id": job_id, "task_type": "video"}, {"task_id": 1}
            )
            if audio_task:
                await dispatch_task(Q_AUDIO_FAST, {
                    "task_id": audio_task["task_id"], "job_id": job_id,
                    "task_type": "audio", "idea": idea, "niche": niche,
                })
            if video_task:
                await dispatch_task(Q_VIDEO_FAST, {
                    "task_id": video_task["task_id"], "job_id": job_id,
                    "task_type": "video", "idea": idea, "niche": niche,
                })
