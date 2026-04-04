"""
Text Fast Worker — processes hooks, script, captions tasks.
Each task runs independently with its own fallback ladder.
After completion, checks if Phase 1 is done → dispatches audio + video.
"""
import logging
from shared import db
from services.viral import viral_job_service as jobs
from services.viral.text_generation_service import generate_hooks, generate_script, generate_captions
from services.viral.task_dispatch import dispatch_task, Q_AUDIO_FAST, Q_VIDEO_FAST

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
            await db.viral_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"_best_hook": result["hooks"][0] if result["hooks"] else idea}}
            )

        elif task_type == "script":
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

    # Check if Phase 1 is done → dispatch Phase 2 (audio + video)
    await _check_phase1_and_dispatch_phase2(job_id, idea, niche)


async def _check_phase1_and_dispatch_phase2(job_id: str, idea: str, niche: str):
    if await jobs.all_phase1_done(db, job_id):
        # Atomic claim to prevent double Phase 2 dispatch
        claimed = await db.viral_jobs.find_one_and_update(
            {"job_id": job_id, "_phase2_dispatched": {"$ne": True}},
            {"$set": {"_phase2_dispatched": True}},
        )
        if claimed:
            logger.info(f"[TEXT_WORKER] Phase 1 done for job {job_id}, dispatching audio + video")
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
