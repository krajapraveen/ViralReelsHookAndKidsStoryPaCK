"""
Pipeline API Routes
Story → Video durable pipeline endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from shared import db, get_current_user
from services.pipeline_engine import (
    create_pipeline_job, resume_pipeline, get_job,
    ANIMATION_STYLES, AGE_GROUPS, VOICE_PRESETS, CREDIT_COSTS,
)
from services.pipeline_worker import enqueue_job, get_worker_stats

logger = logging.getLogger("pipeline_routes")

router = APIRouter(prefix="/pipeline", tags=["Story Video Pipeline"])


class CreatePipelineRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    story_text: str = Field(..., min_length=50, max_length=10000)
    animation_style: str = Field(default="cartoon_2d")
    age_group: str = Field(default="kids_5_8")
    voice_preset: str = Field(default="narrator_warm")
    include_watermark: bool = Field(default=True)


@router.get("/options")
async def get_pipeline_options():
    """Return all available options for the pipeline."""
    return {
        "success": True,
        "animation_styles": [
            {"id": k, "name": v["name"], "style_prompt": v["style_prompt"]}
            for k, v in ANIMATION_STYLES.items()
        ],
        "age_groups": [
            {"id": k, "name": v["name"], "max_scenes": v["max_scenes"]}
            for k, v in AGE_GROUPS.items()
        ],
        "voice_presets": [
            {"id": k, "name": v["name"], "voice": v["voice"]}
            for k, v in VOICE_PRESETS.items()
        ],
        "credit_costs": CREDIT_COSTS,
    }


@router.post("/create")
async def create_pipeline(
    request: CreatePipelineRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new pipeline job. Returns instantly with job_id."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await create_pipeline_job(
            user_id=user_id,
            title=request.title,
            story_text=request.story_text,
            animation_style=request.animation_style,
            age_group=request.age_group,
            voice_preset=request.voice_preset,
            include_watermark=request.include_watermark,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Enqueue for worker processing
    await enqueue_job(result["job_id"])

    return {
        "success": True,
        "job_id": result["job_id"],
        "credits_charged": result["credits_charged"],
        "estimated_scenes": result["estimated_scenes"],
        "message": "Video generation queued. Poll /status for progress.",
    }


@router.get("/status/{job_id}")
async def get_pipeline_status(job_id: str, current_user: dict = Depends(get_current_user)):
    """Poll pipeline job progress. Returns full stage info."""
    job = await db.pipeline_jobs.find_one({"job_id": job_id}, {"_id": 0, "story_text": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Build scene thumbnails from checkpointed images
    scene_images = job.get("scene_images", {})
    scene_voices = job.get("scene_voices", {})
    scenes = job.get("scenes", [])

    scene_progress = []
    for scene in scenes:
        sn = str(scene.get("scene_number", 0))
        sp = {
            "scene_number": int(sn),
            "title": scene.get("title", f"Scene {sn}"),
            "has_image": sn in scene_images,
            "image_url": scene_images.get(sn, {}).get("url"),
            "has_voice": sn in scene_voices,
            "voice_duration": scene_voices.get(sn, {}).get("duration"),
        }
        scene_progress.append(sp)

    # Build stage summary
    stages_summary = {}
    for stage_name, stage_data in job.get("stages", {}).items():
        stages_summary[stage_name] = {
            "status": stage_data.get("status", "PENDING"),
            "duration_ms": stage_data.get("duration_ms"),
            "retry_count": stage_data.get("retry_count", 0),
            "error": stage_data.get("error"),
        }

    return {
        "success": True,
        "job": {
            "job_id": job.get("job_id"),
            "title": job.get("title"),
            "status": job.get("status"),
            "progress": job.get("progress", 0),
            "current_stage": job.get("current_stage"),
            "current_step": job.get("current_step"),
            "output_url": job.get("output_url"),
            "error": job.get("error"),
            "stages": stages_summary,
            "scene_progress": scene_progress,
            "timing": job.get("timing", {}),
            "credits_charged": job.get("credits_charged"),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
        },
    }


@router.post("/resume/{job_id}")
async def resume_pipeline_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Resume a failed pipeline from last checkpoint."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    job = await db.pipeline_jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your job")
    if job.get("status") == "COMPLETED":
        raise HTTPException(status_code=400, detail="Job already completed")

    try:
        await resume_pipeline(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await enqueue_job(job_id)

    return {"success": True, "message": "Pipeline resumed from last checkpoint."}


@router.get("/user-jobs")
async def get_user_pipeline_jobs(current_user: dict = Depends(get_current_user)):
    """Get all pipeline jobs for the current user."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    jobs = await db.pipeline_jobs.find(
        {"user_id": user_id},
        {"_id": 0, "story_text": 0, "scenes": 0, "scene_images": 0, "scene_voices": 0},
    ).sort("created_at", -1).to_list(length=50)

    return {"success": True, "jobs": jobs}


@router.get("/workers/status")
async def pipeline_worker_status(current_user: dict = Depends(get_current_user)):
    """Get worker pool status (admin diagnostic)."""
    stats = get_worker_stats()
    return {"success": True, "workers": stats}
