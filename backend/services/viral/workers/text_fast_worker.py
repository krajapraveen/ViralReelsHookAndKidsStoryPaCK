"""
Text Fast Worker — processes hooks, script, captions tasks
Each task runs independently with its own fallback ladder.
After completion, checks if all pre-packaging tasks are done.
"""
import logging
from shared import db
from services.viral import viral_job_service as jobs
from services.viral.text_generation_service import generate_hooks, generate_script, generate_captions
from services.viral.task_dispatch import dispatch_task, Q_PACKAGING

logger = logging.getLogger("viral.worker.text_fast")


async def handle_text_task(payload: dict):
    task_id = payload["task_id"]
    job_id = payload["job_id"]
    task_type = payload["task_type"]
    idea = payload["idea"]
    niche = payload["niche"]

    logger.info(f"[TEXT_WORKER] Processing {task_type} task={task_id} job={job_id}")

    phase_map = {"hooks": "generating_hooks", "script": "generating_script", "captions": "generating_captions"}
    await jobs.update_job_phase(db, job_id, phase_map.get(task_type, "processing"))

    try:
        if task_type == "hooks":
            result = await generate_hooks(idea, niche, count=3)
            hooks_text = "\n".join(result["hooks"])
            await jobs.save_asset(db, job_id, task_id, "hooks", content=hooks_text, mime_type="text/plain")
            await jobs.update_task(db, task_id, "completed", fallback_used=result["fallback_used"])

            # Store first hook in job for downstream use
            await db.viral_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"_best_hook": result["hooks"][0] if result["hooks"] else idea}}
            )

        elif task_type == "script":
            # Wait briefly for hooks to be ready, then use the best hook
            import asyncio
            hook = idea
            for _ in range(5):
                job_data = await db.viral_jobs.find_one({"job_id": job_id}, {"_best_hook": 1})
                if job_data and job_data.get("_best_hook"):
                    hook = job_data["_best_hook"]
                    break
                await asyncio.sleep(0.5)

            result = await generate_script(idea, niche, hook)
            await jobs.save_asset(db, job_id, task_id, "script", content=result["script"], mime_type="text/markdown")
            await jobs.update_task(db, task_id, "completed", fallback_used=result["fallback_used"])

        elif task_type == "captions":
            import asyncio
            hook = idea
            for _ in range(5):
                job_data = await db.viral_jobs.find_one({"job_id": job_id}, {"_best_hook": 1})
                if job_data and job_data.get("_best_hook"):
                    hook = job_data["_best_hook"]
                    break
                await asyncio.sleep(0.5)

            result = await generate_captions(idea, niche, hook)
            captions_text = "\n\n".join(f"=== {p.upper()} ===\n{c}" for p, c in result["captions"].items())
            await jobs.save_asset(db, job_id, task_id, "captions", content=captions_text, mime_type="text/plain")
            await jobs.update_task(db, task_id, "completed", fallback_used=result["fallback_used"])

    except Exception as e:
        logger.error(f"[TEXT_WORKER] Task {task_type} failed completely: {e}", exc_info=True)
        # Even on total failure, save deterministic fallback
        from services.viral.fallback_service import generate_fallback_hooks, generate_fallback_script, generate_fallback_captions
        if task_type == "hooks":
            hooks = generate_fallback_hooks(idea, niche, 3)
            await jobs.save_asset(db, job_id, task_id, "hooks", content="\n".join(hooks))
        elif task_type == "script":
            script = generate_fallback_script(idea, niche)
            await jobs.save_asset(db, job_id, task_id, "script", content=script)
        elif task_type == "captions":
            captions = generate_fallback_captions(idea, niche)
            text = "\n\n".join(f"=== {p.upper()} ===\n{c}" for p, c in captions.items())
            await jobs.save_asset(db, job_id, task_id, "captions", content=text)
        await jobs.update_task(db, task_id, "completed", fallback_used=True)

    # Check if all pre-packaging tasks are done
    await _check_and_dispatch_packaging(job_id)


async def _check_and_dispatch_packaging(job_id: str):
    if await jobs.all_pretasks_done(db, job_id):
        # Atomic claim: only the first worker to set status=processing wins
        pkg_task = await db.viral_job_tasks.find_one_and_update(
            {"job_id": job_id, "task_type": "packaging", "status": "pending"},
            {"$set": {"status": "processing"}},
            projection={"task_id": 1, "_id": 0},
        )
        if pkg_task:
            logger.info(f"[TEXT_WORKER] Claimed packaging for job {job_id}")
            await dispatch_task(Q_PACKAGING, {
                "task_id": pkg_task["task_id"],
                "job_id": job_id,
            })
