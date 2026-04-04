"""
Orchestrator Worker — processes master job dispatch
"""
import logging
from shared import db
from services.viral.orchestration_service import orchestrate_job

logger = logging.getLogger("viral.worker.orchestrator")


async def handle_orchestrator(payload: dict):
    job_id = payload["job_id"]
    idea = payload["idea"]
    niche = payload["niche"]
    logger.info(f"[ORCH_WORKER] Starting orchestration for job {job_id}")
    try:
        await orchestrate_job(db, job_id, idea, niche)
    except Exception as e:
        logger.error(f"[ORCH_WORKER] Orchestration failed for job {job_id}: {e}", exc_info=True)
        from services.viral.viral_job_service import mark_job_failed
        await mark_job_failed(db, job_id)
