"""
Packaging Worker — assembles ZIP bundle from completed assets
ZIP failure does NOT block individual asset access.
"""
import logging
from shared import db
from services.viral import viral_job_service as jobs
from services.viral.packaging_service import create_bundle

logger = logging.getLogger("viral.worker.packaging")


async def handle_packaging_task(payload: dict):
    task_id = payload["task_id"]
    job_id = payload["job_id"]

    logger.info(f"[PKG_WORKER] Packaging job {job_id}")
    await jobs.update_job_phase(db, job_id, "packaging")

    try:
        result = await create_bundle(db, job_id)
        if result["success"]:
            await jobs.save_asset(db, job_id, task_id, "zip_bundle",
                                  file_url=result["zip_url"],
                                  file_path=result["zip_path"],
                                  mime_type="application/zip")
            await jobs.update_task(db, task_id, "completed")
        else:
            # ZIP failed but assets are still individually accessible
            logger.warning(f"[PKG_WORKER] ZIP failed for job {job_id}, assets still available individually")
            await jobs.update_task(db, task_id, "completed", fallback_used=True)

    except Exception as e:
        logger.error(f"[PKG_WORKER] Packaging failed: {e}", exc_info=True)
        await jobs.update_task(db, task_id, "completed", fallback_used=True)

    # Mark job as ready regardless of ZIP success
    await jobs.update_job_phase(db, job_id, "ready")
    logger.info(f"[PKG_WORKER] Job {job_id} marked ready")
