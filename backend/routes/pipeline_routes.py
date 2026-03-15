"""
Pipeline API Routes
Story → Video durable pipeline endpoints.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
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

# Rate limits - Production values
MAX_VIDEOS_PER_HOUR = 5
MAX_CONCURRENT_JOBS = 1

# Users exempt from rate limiting (admin, demo, UAT)
RATE_LIMIT_EXEMPT_EMAILS = {"admin@creatorstudio.ai", "test@visionary-suite.com", "demo@visionary-suite.com"}


from typing import Optional

class CreatePipelineRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    story_text: str = Field(..., min_length=50, max_length=10000)
    animation_style: str = Field(default="cartoon_2d")
    age_group: str = Field(default="kids_5_8")
    voice_preset: str = Field(default="narrator_warm")
    include_watermark: bool = Field(default=True)
    parent_video_id: Optional[str] = Field(default=None, description="ID of remixed video")


async def _track_event(event: str, user_id: str = None, data: dict = None):
    """Track an analytics event for funnel analysis."""
    await db.analytics_events.insert_one({
        "event": event,
        "user_id": user_id,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc),
    })


async def _check_rate_limit(user_id: str):
    """Enforce rate limits: MAX_VIDEOS_PER_HOUR and MAX_CONCURRENT_JOBS."""
    # Check if user is exempt from rate limiting
    user_doc = await db.users.find_one({"id": user_id}, {"email": 1, "role": 1, "_id": 0})
    if user_doc:
        if user_doc.get("email") in RATE_LIMIT_EXEMPT_EMAILS or user_doc.get("role") in ("admin", "ADMIN"):
            return  # Skip rate limit for exempt users

    # Auto-timeout stale jobs older than 15 minutes
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    await db.pipeline_jobs.update_many(
        {"user_id": user_id, "status": {"$in": ["QUEUED", "PROCESSING"]}, "created_at": {"$lt": stale_cutoff}},
        {"$set": {"status": "FAILED", "error": "Job timed out after 15 minutes", "completed_at": datetime.now(timezone.utc)}}
    )

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_count = await db.pipeline_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": one_hour_ago},
    })
    if recent_count >= MAX_VIDEOS_PER_HOUR:
        raise HTTPException(status_code=429, detail=f"Rate limit: max {MAX_VIDEOS_PER_HOUR} videos per hour. Please wait.")

    concurrent = await db.pipeline_jobs.count_documents({
        "user_id": user_id,
        "status": {"$in": ["QUEUED", "PROCESSING"]},
    })
    if concurrent >= MAX_CONCURRENT_JOBS:
        raise HTTPException(status_code=429, detail="You already have a video generating. Please wait for it to finish.")


@router.get("/rate-limit-status")
async def get_rate_limit_status(current_user: dict = Depends(get_current_user)):
    """Check if the user can create a new video (pre-check)."""
    user_id = current_user.get("id") or str(current_user.get("_id"))

    # Check if user is exempt from rate limiting
    user_email = current_user.get("email", "")
    user_role = current_user.get("role", "")
    is_exempt = user_email in RATE_LIMIT_EXEMPT_EMAILS or user_role in ("admin", "ADMIN")

    if is_exempt:
        return {
            "can_create": True,
            "recent_count": 0,
            "max_per_hour": 999,
            "concurrent": 0,
            "max_concurrent": 10,
            "reason": None,
            "exempt": True,
        }

    # Auto-timeout stale jobs
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    await db.pipeline_jobs.update_many(
        {"user_id": user_id, "status": {"$in": ["QUEUED", "PROCESSING"]}, "created_at": {"$lt": stale_cutoff}},
        {"$set": {"status": "FAILED", "error": "Job timed out after 15 minutes", "completed_at": datetime.now(timezone.utc)}}
    )

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_count = await db.pipeline_jobs.count_documents({
        "user_id": user_id, "created_at": {"$gte": one_hour_ago},
    })
    concurrent = await db.pipeline_jobs.count_documents({
        "user_id": user_id, "status": {"$in": ["QUEUED", "PROCESSING"]},
    })

    can_create = recent_count < MAX_VIDEOS_PER_HOUR and concurrent < MAX_CONCURRENT_JOBS
    reason = None
    if concurrent >= MAX_CONCURRENT_JOBS:
        reason = "You have a video currently generating. Please wait for it to finish."
    elif recent_count >= MAX_VIDEOS_PER_HOUR:
        reason = f"You've reached the limit of {MAX_VIDEOS_PER_HOUR} videos per hour. Please wait."

    return {
        "can_create": can_create,
        "recent_count": recent_count,
        "max_per_hour": MAX_VIDEOS_PER_HOUR,
        "concurrent": concurrent,
        "max_concurrent": MAX_CONCURRENT_JOBS,
        "reason": reason,
    }



def _make_presigned_url(stored_url: str) -> str:
    """Convert a stored R2 public URL to a presigned URL for direct access."""
    from utils.r2_presign import presign_url
    return presign_url(stored_url)


@router.get("/gallery")
async def public_gallery(category: str = None, sort: str = "newest", featured: bool = False):
    """Public endpoint: return completed videos and showcase items for the gallery."""
    query = {
        "status": "COMPLETED",
        "$or": [
            {"output_url": {"$exists": True, "$ne": None}},
            {"is_showcase": True},
        ]
    }
    if category and category != "all":
        query["animation_style"] = category
    if featured:
        query["remix_count"] = {"$gte": 1}

    sort_field = "completed_at"
    sort_dir = -1
    if sort == "most_remixed":
        sort_field = "remix_count"

    jobs = await db.pipeline_jobs.find(
        query,
        {"title": 1, "output_url": 1, "thumbnail_url": 1, "animation_style": 1, "timing": 1,
         "completed_at": 1, "job_id": 1, "story_text": 1, "remix_count": 1,
         "age_group": 1, "voice_preset": 1, "is_showcase": 1, "_id": 0}
    ).sort(sort_field, sort_dir).to_list(length=48)

    for job in jobs:
        if job.get("output_url"):
            job["output_url"] = _make_presigned_url(job["output_url"])
        if job.get("thumbnail_url") and not job.get("thumbnail_url", "").startswith("https://static.prod-images"):
            job["thumbnail_url"] = _make_presigned_url(job["thumbnail_url"])

    return {"videos": jobs}


@router.get("/gallery/leaderboard")
async def gallery_leaderboard():
    """Public endpoint: return most remixed videos/showcases for the leaderboard."""
    query = {
        "status": "COMPLETED",
        "remix_count": {"$gte": 1},
        "$or": [
            {"output_url": {"$exists": True, "$ne": None}},
            {"is_showcase": True},
        ]
    }
    projection = {"title": 1, "output_url": 1, "thumbnail_url": 1, "animation_style": 1, "job_id": 1,
                  "remix_count": 1, "completed_at": 1, "story_text": 1, "age_group": 1,
                  "voice_preset": 1, "is_showcase": 1, "_id": 0}

    jobs = await db.pipeline_jobs.find(query, projection).sort("remix_count", -1).to_list(length=10)

    if not jobs:
        query.pop("remix_count")
        jobs = await db.pipeline_jobs.find(query, projection).sort("completed_at", -1).to_list(length=5)

    for j in jobs:
        if j.get("output_url"):
            j["output_url"] = _make_presigned_url(j["output_url"])
        if j.get("thumbnail_url") and not j.get("thumbnail_url", "").startswith("https://static.prod-images"):
            j["thumbnail_url"] = _make_presigned_url(j["thumbnail_url"])

    return {"leaderboard": jobs}


@router.get("/gallery/categories")
async def gallery_categories():
    """Public endpoint: return available categories with counts."""
    pipe = [
        {"$match": {"status": "COMPLETED", "$or": [
            {"output_url": {"$exists": True, "$ne": None}},
            {"is_showcase": True},
        ]}},
        {"$group": {"_id": "$animation_style", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = await db.pipeline_jobs.aggregate(pipe).to_list(length=20)
    categories = [{"id": r["_id"], "name": ANIMATION_STYLES.get(r["_id"], {}).get("name", r["_id"]), "count": r["count"]} for r in rows if r["_id"]]
    total = sum(r["count"] for r in rows)
    return {"categories": [{"id": "all", "name": "All", "count": total}] + categories}


@router.get("/performance")
async def get_performance_stats(current_user: dict = Depends(get_current_user)):
    """Admin endpoint: get performance monitoring stats."""
    if current_user.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required")

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    # Queue depth
    queued = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
    processing = await db.pipeline_jobs.count_documents({"status": "PROCESSING"})

    # Recent render times
    render_pipe = [
        {"$match": {"status": "COMPLETED", "completed_at": {"$gte": one_hour_ago}}},
        {"$group": {
            "_id": None,
            "avg_total_ms": {"$avg": "$timing.total_ms"},
            "avg_render_ms": {"$avg": "$timing.render_ms"},
            "max_total_ms": {"$max": "$timing.total_ms"},
            "count": {"$sum": 1},
        }},
    ]
    render_rows = await db.pipeline_jobs.aggregate(render_pipe).to_list(length=1)
    render_stats = render_rows[0] if render_rows else {"avg_total_ms": 0, "avg_render_ms": 0, "max_total_ms": 0, "count": 0}
    render_stats.pop("_id", None)

    # Failure rate (last hour)
    failed = await db.pipeline_jobs.count_documents({"status": "FAILED", "created_at": {"$gte": one_hour_ago}})
    total_recent = await db.pipeline_jobs.count_documents({"created_at": {"$gte": one_hour_ago}})
    failure_rate = round((failed / total_recent * 100), 1) if total_recent > 0 else 0

    # Worker stats
    workers = get_worker_stats()

    return {
        "success": True,
        "queue": {"queued": queued, "processing": processing},
        "render_stats": render_stats,
        "failure_rate": failure_rate,
        "failed_last_hour": failed,
        "total_last_hour": total_recent,
        "workers": workers,
        "timestamp": now.isoformat(),
    }


@router.get("/gallery/{job_id}")
async def get_gallery_video(job_id: str):
    """Public endpoint: get a single video for remix."""
    job = await db.pipeline_jobs.find_one(
        {"job_id": job_id, "status": "COMPLETED"},
        {"title": 1, "story_text": 1, "animation_style": 1, "age_group": 1,
         "voice_preset": 1, "output_url": 1, "job_id": 1, "remix_count": 1, "_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Video not found")
    if job.get("output_url"):
        job["output_url"] = _make_presigned_url(job["output_url"])
    return {"video": job}


@router.get("/gallery/{job_id}/og")
async def get_gallery_video_og(job_id: str):
    """Public endpoint: return OG meta HTML for social sharing."""
    from fastapi.responses import HTMLResponse
    job = await db.pipeline_jobs.find_one(
        {"job_id": job_id, "status": "COMPLETED"},
        {"title": 1, "output_url": 1, "animation_style": 1, "story_text": 1, "_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Video not found")

    base_url = os.environ.get("REACT_APP_BACKEND_URL", "")
    title = job.get("title", "AI Story Video")
    desc = (job.get("story_text", "") or "")[:200]
    video_url = job.get("output_url", "")
    page_url = f"{base_url}/gallery?video={job_id}"

    html = f"""<!DOCTYPE html>
<html><head>
<meta property="og:type" content="video.other" />
<meta property="og:title" content="{title} | Visionary Suite" />
<meta property="og:description" content="{desc}" />
<meta property="og:video" content="{video_url}" />
<meta property="og:video:type" content="video/mp4" />
<meta property="og:url" content="{page_url}" />
<meta property="og:site_name" content="Visionary Suite" />
<meta name="twitter:card" content="player" />
<meta name="twitter:title" content="{title} | Visionary Suite" />
<meta name="twitter:description" content="{desc}" />
<meta name="twitter:player" content="{video_url}" />
<meta http-equiv="refresh" content="0;url={page_url}" />
</head><body>Redirecting...</body></html>"""
    return HTMLResponse(content=html)


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

    # Enforce rate limits
    await _check_rate_limit(user_id)

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

    # Store remix link if present
    if request.parent_video_id:
        await db.pipeline_jobs.update_one(
            {"job_id": result["job_id"]},
            {"$set": {"parent_video_id": request.parent_video_id}}
        )
        await db.pipeline_jobs.update_one(
            {"job_id": request.parent_video_id},
            {"$inc": {"remix_count": 1}}
        )

    # Track analytics
    await _track_event("video_generation_started", user_id, {
        "job_id": result["job_id"],
        "credits": result["credits_charged"],
        "style": request.animation_style,
        "is_remix": bool(request.parent_video_id),
    })

    # Enqueue for worker processing with priority based on user plan
    user_plan = current_user.get("plan", "free")
    await enqueue_job(result["job_id"], user_id=user_id, user_plan=user_plan)

    return {
        "success": True,
        "job_id": result["job_id"],
        "credits_charged": result["credits_charged"],
        "estimated_scenes": result["estimated_scenes"],
        "queue_priority": "priority" if user_plan in ("admin", "demo", "weekly", "monthly", "quarterly", "yearly", "starter", "creator", "pro", "premium", "enterprise") else "standard",
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
        image_url = scene_images.get(sn, {}).get("url")
        if image_url:
            image_url = _make_presigned_url(image_url)
        sp = {
            "scene_number": int(sn),
            "title": scene.get("title", f"Scene {sn}"),
            "has_image": sn in scene_images,
            "image_url": image_url,
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

    # Include fallback outputs if available
    fallback = job.get("fallback_outputs", {})
    fallback_data = None
    if fallback:
        fallback_data = {
            "status": job.get("fallback_status", "none"),
        }
        if fallback.get("fallback_mp4", {}).get("url"):
            fallback_data["fallback_video_url"] = _make_presigned_url(fallback["fallback_mp4"]["url"])
            fallback_data["fallback_video_size_mb"] = fallback["fallback_mp4"].get("file_size_mb")
            fallback_data["fallback_video_type"] = "slideshow"
        if fallback.get("story_pack_zip", {}).get("url"):
            fallback_data["story_pack_url"] = _make_presigned_url(fallback["story_pack_zip"]["url"])
            fallback_data["story_pack_size_mb"] = fallback["story_pack_zip"].get("file_size_mb")
        if fallback.get("preview"):
            fallback_data["has_preview"] = True
            fallback_data["preview_scenes"] = fallback["preview"].get("total_scenes", 0)

    return {
        "success": True,
        "job": {
            "job_id": job.get("job_id"),
            "title": job.get("title"),
            "status": job.get("status"),
            "progress": job.get("progress", 0),
            "current_stage": job.get("current_stage"),
            "current_step": job.get("current_step"),
            "output_url": _make_presigned_url(job.get("output_url")) if job.get("output_url") else None,
            "error": job.get("error"),
            "stages": stages_summary,
            "scene_progress": scene_progress,
            "timing": job.get("timing", {}),
            "credits_charged": job.get("credits_charged"),
            "queue_priority": job.get("queue_tier", "FREE"),
            "queue_wait_ms": job.get("queue_wait_ms"),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
            "fallback": fallback_data,
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

    # Preserve original priority on retry/resume
    user_plan = current_user.get("plan", "free")
    await enqueue_job(job_id, user_id=user_id, user_plan=user_plan)

    return {"success": True, "message": "Pipeline resumed from last checkpoint."}


@router.get("/user-jobs")
async def get_user_pipeline_jobs(current_user: dict = Depends(get_current_user)):
    """Get all pipeline jobs for the current user."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    jobs = await db.pipeline_jobs.find(
        {"user_id": user_id},
        {"_id": 0, "story_text": 0, "scenes": 0, "scene_images": 0, "scene_voices": 0},
    ).sort("created_at", -1).to_list(length=50)

    for j in jobs:
        if j.get("output_url"):
            j["output_url"] = _make_presigned_url(j["output_url"])
        if j.get("thumbnail_url"):
            j["thumbnail_url"] = _make_presigned_url(j["thumbnail_url"])

    return {"success": True, "jobs": jobs}


@router.get("/analytics/funnel")
async def get_analytics_funnel(days: int = 30, current_user: dict = Depends(get_current_user)):
    """Admin endpoint: get growth funnel analytics."""
    if current_user.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipe = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {"_id": "$event", "count": {"$sum": 1}}},
    ]
    rows = await db.analytics_events.aggregate(pipe).to_list(length=100)
    event_counts = {r["_id"]: r["count"] for r in rows}

    # Daily breakdown for chart
    daily_pipe = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "event": "$event",
            },
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.date": 1}},
    ]
    daily_rows = await db.analytics_events.aggregate(daily_pipe).to_list(length=5000)
    daily = {}
    for r in daily_rows:
        d = r["_id"]["date"]
        if d not in daily:
            daily[d] = {}
        daily[d][r["_id"]["event"]] = r["count"]

    # Cost analytics: total credits consumed
    cost_pipe = [
        {"$match": {"timestamp": {"$gte": since}, "event": "video_generation_started"}},
        {"$group": {"_id": None, "total_credits": {"$sum": "$data.credits"}}},
    ]
    cost_rows = await db.analytics_events.aggregate(cost_pipe).to_list(length=1)
    total_credits = cost_rows[0]["total_credits"] if cost_rows else 0

    # Remix stats
    remix_count = await db.pipeline_jobs.count_documents({
        "parent_video_id": {"$exists": True, "$ne": None},
        "created_at": {"$gte": since},
    })

    # Total videos
    total_videos = await db.pipeline_jobs.count_documents({"created_at": {"$gte": since}})
    completed_videos = await db.pipeline_jobs.count_documents({"status": "COMPLETED", "created_at": {"$gte": since}})

    return {
        "success": True,
        "funnel": event_counts,
        "daily": daily,
        "totals": {
            "total_videos": total_videos,
            "completed_videos": completed_videos,
            "remix_count": remix_count,
            "total_credits_consumed": total_credits,
        },
    }


@router.get("/workers/status")
async def pipeline_worker_status(current_user: dict = Depends(get_current_user)):
    """Get worker pool status (admin diagnostic)."""
    stats = get_worker_stats()
    return {"success": True, "workers": stats}



# ─── FALLBACK OUTPUT ENDPOINTS ───────────────────────────────────────────────

@router.get("/preview/{job_id}")
async def get_job_preview(job_id: str):
    """Public preview page data: scene images in order, audio per scene, story text.
    Works for any job that has generated scenes (regardless of render status)."""
    job = await db.pipeline_jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from services.fallback_pipeline import get_preview_data
    preview = await get_preview_data(job)

    # Include fallback info if available
    fallback = job.get("fallback_outputs", {})
    preview["fallback_video_url"] = None
    preview["story_pack_url"] = None
    preview["final_video_url"] = None

    if job.get("output_url"):
        preview["final_video_url"] = _make_presigned_url(job["output_url"])
    if fallback.get("fallback_mp4", {}).get("url"):
        preview["fallback_video_url"] = _make_presigned_url(fallback["fallback_mp4"]["url"])
    if fallback.get("story_pack_zip", {}).get("url"):
        preview["story_pack_url"] = _make_presigned_url(fallback["story_pack_zip"]["url"])

    return {"success": True, "preview": preview}


@router.get("/assets/{job_id}")
async def get_job_assets(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get downloadable URLs for all individual assets of a job."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    job = await db.pipeline_jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Allow owner or admin
    is_admin = current_user.get("role") in ("admin", "ADMIN")
    if job.get("user_id") != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not your job")

    from services.fallback_pipeline import get_asset_links
    assets = await get_asset_links(job)
    return {"success": True, "assets": assets}


@router.post("/notify-when-ready/{job_id}")
async def subscribe_notify_when_ready(job_id: str, current_user: dict = Depends(get_current_user)):
    """Subscribe to be notified when a long-running job completes.
    Stores a flag so the system sends a notification on completion."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    job = await db.pipeline_jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your job")

    # If already completed, return immediately
    if job.get("status") in ("COMPLETED", "PARTIAL"):
        return {"success": True, "message": "Job already completed", "already_done": True}

    await db.pipeline_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"notify_on_complete": True, "notify_email": current_user.get("email", "")}}
    )

    return {"success": True, "message": "You'll be notified when your video is ready"}


@router.post("/generate-fallback/{job_id}")
async def manually_generate_fallback(job_id: str, current_user: dict = Depends(get_current_user)):
    """Manually trigger fallback generation for a failed job.
    Useful if user wants to get assets from an old failed job."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    job = await db.pipeline_jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your job")

    # Check if fallback already exists
    if job.get("fallback_outputs"):
        return {"success": True, "message": "Fallback already generated", "fallback": job["fallback_outputs"]}

    # Check if job has assets to work with
    if not job.get("scenes") or not job.get("scene_images"):
        raise HTTPException(status_code=400, detail="No scene assets available for this job")

    from services.fallback_pipeline import run_fallback_pipeline
    await run_fallback_pipeline(job_id, job.get("current_stage", "render"))

    # Re-fetch updated job
    updated = await db.pipeline_jobs.find_one({"job_id": job_id}, {"_id": 0, "fallback_outputs": 1, "fallback_status": 1})
    return {"success": True, "message": "Fallback generated", "fallback_status": updated.get("fallback_status")}
