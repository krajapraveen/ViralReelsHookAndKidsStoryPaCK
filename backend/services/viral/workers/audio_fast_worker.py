"""
Audio Fast Worker — generates TTS voiceover for hook/script.
Dispatches after Phase 1 (text + image) completes.
If TTS fails, task is marked as completed with fallback (skipped) — does NOT block pack.
"""
import os
import logging
from shared import db
from services.viral import viral_job_service as jobs
from services.viral.audio_generation_service import generate_voiceover
from services.viral.task_dispatch import dispatch_task, Q_PACKAGING

logger = logging.getLogger("viral.worker.audio_fast")

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "static", "generated", "viral_audio")


async def handle_audio_task(payload: dict):
    task_id = payload["task_id"]
    job_id = payload["job_id"]
    idea = payload.get("idea", "")

    logger.info(f"[AUDIO_WORKER] Processing audio task={task_id} job={job_id}")
    await jobs.update_job_phase(db, job_id, "generating_audio")

    try:
        # Get hook text from completed assets
        hook_asset = await db.viral_assets.find_one(
            {"job_id": job_id, "asset_type": "hooks"}, {"content": 1}
        )
        voiceover_text = ""
        if hook_asset and hook_asset.get("content"):
            lines = hook_asset["content"].strip().split("\n")
            voiceover_text = lines[0] if lines else idea
        else:
            voiceover_text = idea

        # Generate with energetic tone (default for viral content)
        result = await generate_voiceover(voiceover_text, tone="energetic")

        if result.get("skipped") or not result.get("audio_bytes"):
            logger.info(f"[AUDIO_WORKER] TTS skipped for job {job_id}")
            await jobs.update_task(db, task_id, "completed", fallback_used=True)
        else:
            audio_bytes = result["audio_bytes"]
            os.makedirs(AUDIO_DIR, exist_ok=True)
            filename = f"vo_{job_id[:8]}_{task_id[:8]}.mp3"
            filepath = os.path.join(AUDIO_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(audio_bytes)

            file_url = f"/api/static/generated/viral_audio/{filename}"
            await jobs.save_asset(db, job_id, task_id, "voiceover",
                                  file_url=file_url, file_path=filepath, mime_type="audio/mpeg")
            await jobs.update_task(db, task_id, "completed", fallback_used=False)
            logger.info(f"[AUDIO_WORKER] Voiceover saved: {filepath}")

    except Exception as e:
        logger.error(f"[AUDIO_WORKER] Audio failed: {e}", exc_info=True)
        await jobs.update_task(db, task_id, "completed", fallback_used=True)

    # Check if all pre-packaging tasks are done
    await _check_and_dispatch_packaging(job_id)


async def _check_and_dispatch_packaging(job_id: str):
    if await jobs.all_pretasks_done(db, job_id):
        pkg_task = await db.viral_job_tasks.find_one_and_update(
            {"job_id": job_id, "task_type": "packaging", "status": "pending"},
            {"$set": {"status": "processing"}},
            projection={"task_id": 1, "_id": 0},
        )
        if pkg_task:
            logger.info(f"[AUDIO_WORKER] Claimed packaging for job {job_id}")
            await dispatch_task(Q_PACKAGING, {
                "task_id": pkg_task["task_id"],
                "job_id": job_id,
            })
