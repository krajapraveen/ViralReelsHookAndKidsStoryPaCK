"""
Story Engine API Routes — THE SINGLE SOURCE OF TRUTH for Story-to-Video.
All frontend calls go through /api/story-engine/*.
Replaces the old /api/pipeline/* routes.
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared import db, get_current_user, get_optional_user

from services.story_engine.schemas import CreateStoryRequest, JobState, ErrorCode, TERMINAL_STATES, PER_STAGE_FAILURE_STATES
from services.story_engine.pipeline import create_job, run_pipeline, get_job_status, execute_pipeline, process_next_stage, apply_reuse_checkpoints
from services.entitlement import get_media_access as _entitlement_get_media_access


def _get_media_access_for_user(user):
    """Compute media entitlement for the current user (or guest)."""
    if not user:
        return {"can_preview": True, "can_download": False, "watermark_required": True,
                "preview_only": True, "upgrade_required": True, "plan_type": "free"}
    return _entitlement_get_media_access(user)
from services.story_engine.cost_guard import pre_flight_check
from services.story_engine.safety import check_content_safety, rewrite_content_safely
from services.story_engine.state_machine import get_progress, get_label, FAILURE_TO_RETRY
from services.rewrite_engine import safe_rewrite

logger = logging.getLogger("story_engine.routes")
router = APIRouter(prefix="/story-engine", tags=["Story Engine"])

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — Shared options for frontend dropdowns
# ═══════════════════════════════════════════════════════════════

ANIMATION_STYLES = {
    "cartoon_2d": {"name": "2D Cartoon", "style_prompt": "2D cartoon animation style, vibrant colors, smooth lines, family-friendly"},
    "anime_style": {"name": "Anime", "style_prompt": "anime art style, expressive characters, detailed backgrounds, Studio Ghibli inspired but original"},
    "3d_pixar": {"name": "3D Animation", "style_prompt": "3D rendered animation, smooth textures, warm lighting, Pixar-quality but original"},
    "watercolor": {"name": "Watercolor", "style_prompt": "watercolor illustration, soft edges, pastel colors, children's book style"},
    "comic_book": {"name": "Comic Book", "style_prompt": "comic book art style, bold outlines, dynamic poses, vibrant colors"},
    "claymation": {"name": "Claymation", "style_prompt": "claymation style, textured surfaces, warm colors"},
}

AGE_GROUPS = {
    "toddler": {"name": "Toddlers (2-4)", "max_scenes": 4},
    "kids_5_8": {"name": "Kids (5-8)", "max_scenes": 6},
    "kids_9_12": {"name": "Tweens (9-12)", "max_scenes": 8},
    "teen": {"name": "Teens (13+)", "max_scenes": 10},
    "all_ages": {"name": "All Ages", "max_scenes": 8},
}

VOICE_PRESETS = {
    "narrator_warm": {"voice": "fable", "speed": 0.95, "name": "Warm Narrator"},
    "narrator_energetic": {"voice": "nova", "speed": 1.05, "name": "Energetic"},
    "narrator_calm": {"voice": "alloy", "speed": 0.9, "name": "Calm"},
    "narrator_dramatic": {"voice": "onyx", "speed": 1.0, "name": "Dramatic"},
    "narrator_friendly": {"voice": "shimmer", "speed": 1.0, "name": "Friendly"},
}

CREDIT_COSTS = {"small": 10, "medium": 15, "large": 20}
PLAN_SCENE_LIMITS = {"free": 3, "starter": 4, "weekly": 4, "monthly": 4, "creator": 4, "quarterly": 5, "yearly": 5, "pro": 6, "premium": 6, "enterprise": 6, "admin": 6, "demo": 6}

# Rate limits
MAX_VIDEOS_PER_HOUR = 5
MAX_CONCURRENT_JOBS = 1
RATE_LIMIT_EXEMPT_EMAILS = {"admin@creatorstudio.ai", "test@visionary-suite.com", "demo@visionary-suite.com"}

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_admin(user: dict = Depends(get_current_user)):
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _map_state_to_legacy_status(state: str) -> str:
    """Map new engine states to old pipeline status names for frontend compatibility."""
    if state == "INIT":
        return "QUEUED"
    elif state in ("PLANNING", "BUILDING_CHARACTER_CONTEXT", "PLANNING_SCENE_MOTION",
                   "GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS",
                   "GENERATING_AUDIO", "ASSEMBLING_VIDEO", "VALIDATING"):
        return "PROCESSING"
    elif state == "READY":
        return "COMPLETED"
    elif state == "PARTIAL_READY":
        return "PARTIAL"
    elif state in ("FAILED", "FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER"):
        return "FAILED"
    return "PROCESSING"


# ═══ ACTION RESOLVER — Single source of truth for UI buttons ═══
RESUMABLE_STATES = {JobState.FAILED.value, JobState.PARTIAL_READY.value,
                    "FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER"}
RECOVERING_STATES = {"ASSEMBLY_RETRYING", "FALLBACK_RENDERING"}


def _resolve_allowed_actions(job: dict) -> dict:
    """
    Determine exactly what actions the UI can show for this job.
    The frontend must ONLY render buttons from allowed_actions.
    """
    state = job.get("state", "")
    recovery = job.get("recovery_state", "NONE")

    # COMPLETED or READY — no recovery actions needed
    if state in (JobState.READY.value, "COMPLETED"):
        return {
            "allowed_actions": ["watch", "download", "share", "remix", "continue"],
            "resume_supported": False,
            "recovery_state": "NONE",
            "next_best_action": "watch",
            "fallback_in_use": False,
        }

    # PARTIAL_READY — has some output
    if state == JobState.PARTIAL_READY.value:
        has_output = bool(job.get("output_url"))
        actions = []
        if has_output:
            actions.extend(["watch", "download"])
        actions.extend(["retry", "start_over"])
        return {
            "allowed_actions": actions,
            "resume_supported": True,
            "recovery_state": "WAITING_FOR_USER",
            "next_best_action": "watch" if has_output else "retry",
            "fallback_in_use": job.get("fallback_in_use", False),
        }

    # AUTO-RECOVERING — system is trying to fix itself
    if recovery == "AUTO_RECOVERING":
        return {
            "allowed_actions": ["notify", "leave_safely"],
            "resume_supported": False,
            "recovery_state": "AUTO_RECOVERING",
            "next_best_action": "notify",
            "fallback_in_use": job.get("fallback_in_use", False),
        }

    # FAILED states — check if resume is valid
    if state in RESUMABLE_STATES:
        has_checkpoints = bool(job.get("keyframe_urls") or job.get("scene_motion_plans"))
        actions = []
        if has_checkpoints and state != "FAILED_RENDER":
            actions.append("retry")
        actions.append("start_over")
        return {
            "allowed_actions": actions,
            "resume_supported": has_checkpoints and state != "FAILED_RENDER",
            "recovery_state": "WAITING_FOR_USER",
            "next_best_action": "retry" if has_checkpoints else "start_over",
            "fallback_in_use": False,
        }

    # ASSEMBLING_VIDEO or other active states — job is still running
    if state in (JobState.ASSEMBLING_VIDEO.value, *RECOVERING_STATES):
        return {
            "allowed_actions": ["notify", "leave_safely", "cancel"],
            "resume_supported": False,
            "recovery_state": "AUTO_RECOVERING" if state in RECOVERING_STATES else "NONE",
            "next_best_action": "notify",
            "fallback_in_use": state in RECOVERING_STATES,
        }

    # Active processing states — still working
    if state in (JobState.PLANNING.value, JobState.BUILDING_CHARACTER_CONTEXT.value,
                 JobState.PLANNING_SCENE_MOTION.value, JobState.GENERATING_KEYFRAMES.value,
                 JobState.GENERATING_SCENE_CLIPS.value, JobState.GENERATING_AUDIO.value,
                 JobState.VALIDATING.value):
        return {
            "allowed_actions": ["notify", "leave_safely", "cancel"],
            "resume_supported": False,
            "recovery_state": "NONE",
            "next_best_action": "notify",
            "fallback_in_use": False,
        }

    # INIT or unknown — minimal
    return {
        "allowed_actions": ["cancel"],
        "resume_supported": False,
        "recovery_state": "NONE",
        "next_best_action": "cancel",
        "fallback_in_use": False,
    }



def _map_state_to_legacy_stage(state: str) -> str:
    """Map new engine states to old pipeline stage names for frontend progress display."""
    mapping = {
        "INIT": "scenes",
        "PLANNING": "scenes",
        "BUILDING_CHARACTER_CONTEXT": "scenes",
        "PLANNING_SCENE_MOTION": "scenes",
        "GENERATING_KEYFRAMES": "images",
        "GENERATING_SCENE_CLIPS": "images",
        "GENERATING_AUDIO": "voices",
        "ASSEMBLING_VIDEO": "render",
        "VALIDATING": "render",
        "READY": "render",
        "PARTIAL_READY": "render",
        "FAILED": "render",
        "FAILED_PLANNING": "scenes",
        "FAILED_IMAGES": "images",
        "FAILED_TTS": "voices",
        "FAILED_RENDER": "render",
    }
    return mapping.get(state, "scenes")


def _state_to_progress(state: str) -> int:
    """Convert engine state to 0-100 progress for frontend."""
    return get_progress(JobState(state)) if state in JobState.__members__ else 0


def _make_presigned_url(stored_url: str) -> str:
    """Convert a stored R2 public URL to a presigned URL for direct access."""
    if not stored_url:
        return None
    try:
        from utils.r2_presign import presign_url
        return presign_url(stored_url)
    except Exception:
        return stored_url


def _legacy_status_response(job: dict) -> dict:
    """Build a status response from a legacy pipeline_jobs document."""
    scene_images = job.get("scene_images", {})
    scene_voices = job.get("scene_voices", {})
    scenes = job.get("scenes", [])
    scene_progress = []
    for scene in scenes:
        sn = str(scene.get("scene_number", 0))
        image_url = scene_images.get(sn, {}).get("url")
        if image_url:
            image_url = _make_presigned_url(image_url)
        scene_progress.append({
            "scene_number": int(sn),
            "title": scene.get("title", f"Scene {sn}"),
            "has_image": sn in scene_images,
            "image_url": image_url,
            "has_voice": sn in scene_voices,
            "voice_duration": scene_voices.get(sn, {}).get("duration"),
        })
    stages_summary = {}
    for stage_name, stage_data in job.get("stages", {}).items():
        stages_summary[stage_name] = {
            "status": stage_data.get("status", "PENDING"),
            "duration_ms": stage_data.get("duration_ms"),
            "retry_count": stage_data.get("retry_count", 0),
            "error": stage_data.get("error"),
        }
    fallback = job.get("fallback_outputs", {})
    fallback_data = None
    if fallback:
        fallback_data = {"status": job.get("fallback_status", "none")}
        if fallback.get("fallback_mp4", {}).get("url"):
            fallback_data["fallback_video_url"] = _make_presigned_url(fallback["fallback_mp4"]["url"])
        if fallback.get("story_pack_zip", {}).get("url"):
            fallback_data["story_pack_url"] = _make_presigned_url(fallback["story_pack_zip"]["url"])
    return {
        "success": True,
        "job": {
            "job_id": job.get("job_id"),
            "title": job.get("title"),
            "status": job.get("status"),
            "progress": job.get("progress", 0),
            "current_stage": job.get("current_stage"),
            "current_step": job.get("current_step"),
            "output_url": _make_presigned_url(job.get("output_url")),
            "thumbnail_url": _make_presigned_url(job.get("thumbnail_url")),
            "error": job.get("error"),
            "stages": stages_summary,
            "scene_progress": scene_progress,
            "timing": job.get("timing", {}),
            "credits_charged": job.get("credits_charged"),
            "animation_style": job.get("animation_style", "cartoon_2d"),
            "age_group": job.get("age_group"),
            "voice_preset": job.get("voice_preset"),
            "story_text": job.get("story_text", ""),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
            "fallback": fallback_data,
            "has_recoverable_assets": bool(fallback_data) or len(scene_images) > 0,
            "slug": job.get("slug"),
            "source": "legacy_pipeline",
        },
    }


def _legacy_validate_response(job: dict) -> dict:
    """Build a validate-asset response from a legacy pipeline_jobs document."""
    status = job.get("status", "")
    output_url = _make_presigned_url(job.get("output_url"))
    thumbnail_url = _make_presigned_url(job.get("thumbnail_url"))
    fallback = job.get("fallback_outputs", {})
    fallback_mp4_url = _make_presigned_url(fallback.get("fallback_mp4", {}).get("url"))
    story_pack_url = _make_presigned_url(fallback.get("story_pack_zip", {}).get("url"))

    poster_url = thumbnail_url
    if not poster_url:
        for sn in sorted((job.get("scene_images") or {}).keys(), key=lambda x: int(x) if x.isdigit() else 0):
            url = (job.get("scene_images") or {}).get(sn, {}).get("url")
            if url:
                poster_url = _make_presigned_url(url)
                break

    best_download = output_url or fallback_mp4_url or story_pack_url
    download_ready = bool(best_download)
    preview_ready = bool(poster_url)
    share_ready = bool(output_url)

    if status == "FAILED" and not download_ready:
        ui_state, stage_detail = "FAILED", job.get("error", "Generation failed")
    elif download_ready and preview_ready:
        ui_state, stage_detail = "READY", "Video ready"
    elif download_ready:
        ui_state, stage_detail = "PARTIAL_READY", "Download available, preview limited"
    elif status == "COMPLETED":
        ui_state, stage_detail = "FAILED", "No downloadable asset found"
    else:
        ui_state, stage_detail = "FAILED", job.get("error", "Unknown status")

    return {
        "preview_ready": preview_ready, "download_ready": download_ready,
        "share_ready": share_ready, "poster_url": poster_url,
        "download_url": best_download, "share_url": output_url,
        "story_pack_url": story_pack_url, "ui_state": ui_state,
        "stage_detail": stage_detail, "title": job.get("title", ""),
    }


async def _check_rate_limit(user_id: str):
    """Enforce rate limits using both story_engine_jobs and pipeline_jobs collections."""
    user_doc = await db.users.find_one({"id": user_id}, {"email": 1, "role": 1, "_id": 0})
    if user_doc:
        if user_doc.get("email") in RATE_LIMIT_EXEMPT_EMAILS or user_doc.get("role") in ("admin", "ADMIN"):
            return

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    one_hour_ago_iso = one_hour_ago.isoformat()

    # Check new engine jobs
    engine_recent = await db.story_engine_jobs.count_documents({
        "user_id": user_id, "created_at": {"$gte": one_hour_ago_iso},
    })

    # Check legacy pipeline jobs
    legacy_recent = await db.pipeline_jobs.count_documents({
        "user_id": user_id, "created_at": {"$gte": one_hour_ago},
    })

    total_recent = engine_recent + legacy_recent
    if total_recent >= MAX_VIDEOS_PER_HOUR:
        raise HTTPException(status_code=429, detail=f"You've created {total_recent} videos this hour. Please wait a bit before starting another one.")

    active_states = [s.value for s in JobState if s not in TERMINAL_STATES]
    engine_concurrent = await db.story_engine_jobs.count_documents({
        "user_id": user_id, "state": {"$in": active_states},
    })
    legacy_concurrent = await db.pipeline_jobs.count_documents({
        "user_id": user_id, "status": {"$in": ["QUEUED", "PROCESSING"]},
    })
    total_concurrent = engine_concurrent + legacy_concurrent
    if total_concurrent >= MAX_CONCURRENT_JOBS:
        raise HTTPException(status_code=429, detail="All rendering slots are busy. Your earlier video is still processing — wait for it to finish or cancel it to start a new one.")


# ═══════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS — Frontend-facing
# ═══════════════════════════════════════════════════════════════

@router.get("/options")
async def get_engine_options():
    """Return all available options for the studio UI."""
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
        "plan_scene_limits": PLAN_SCENE_LIMITS,
    }


@router.get("/rate-limit-status")
async def get_rate_limit_status(current_user: dict = Depends(get_current_user)):
    """Check if the user can create a new video."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    user_email = current_user.get("email", "")
    user_role = current_user.get("role", "")
    is_exempt = user_email in RATE_LIMIT_EXEMPT_EMAILS or user_role in ("admin", "ADMIN")

    if is_exempt:
        return {
            "can_create": True, "recent_count": 0, "max_per_hour": 999,
            "concurrent": 0, "max_concurrent": 10, "reason": None, "exempt": True,
        }

    active_states = [s.value for s in JobState if s not in (JobState.READY, JobState.PARTIAL_READY, JobState.FAILED)]

    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    recent_count = await db.story_engine_jobs.count_documents({
        "user_id": user_id, "created_at": {"$gte": one_hour_ago},
    })
    concurrent = await db.story_engine_jobs.count_documents({
        "user_id": user_id, "state": {"$in": active_states},
    })

    can_create = recent_count < MAX_VIDEOS_PER_HOUR and concurrent < MAX_CONCURRENT_JOBS
    reason = None
    if concurrent >= MAX_CONCURRENT_JOBS:
        reason = f"All rendering slots are busy ({concurrent}/{MAX_CONCURRENT_JOBS}). Your earlier video is still processing — wait for it to finish or cancel it to start a new one."
    elif recent_count >= MAX_VIDEOS_PER_HOUR:
        reason = f"You've created {recent_count} videos this hour (limit: {MAX_VIDEOS_PER_HOUR}). Please wait a bit before starting another."

    # Fetch active jobs for the user so frontend can show them
    active_jobs_list = []
    if concurrent > 0:
        active_docs = await db.story_engine_jobs.find(
            {"user_id": user_id, "state": {"$in": active_states}},
            {"_id": 0, "job_id": 1, "title": 1, "state": 1, "created_at": 1},
        ).sort("created_at", -1).to_list(5)
        active_jobs_list = [
            {"job_id": j.get("job_id"), "title": j.get("title", "Untitled"), "state": j.get("state"), "created_at": j.get("created_at")}
            for j in active_docs
        ]

    return {
        "can_create": can_create, "recent_count": recent_count,
        "max_per_hour": MAX_VIDEOS_PER_HOUR, "concurrent": concurrent,
        "max_concurrent": MAX_CONCURRENT_JOBS, "reason": reason,
        "active_jobs": active_jobs_list,
    }


class CreateEngineRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    story_text: str = Field(..., min_length=50, max_length=10000)
    animation_style: str = Field(default="cartoon_2d")
    age_group: str = Field(default="kids_5_8")
    voice_preset: str = Field(default="narrator_warm")
    parent_video_id: Optional[str] = Field(default=None)
    quality_mode: str = Field(default="balanced")  # fast, balanced, high_quality
    series_id: Optional[str] = Field(default=None)  # Story Series context
    episode_number: Optional[int] = Field(default=None)  # Episode number within the series


# ═══ QUALITY MODE STRATEGY ═══
QUALITY_MODES = {
    "fast": {
        "label": "Fast",
        "description": "Quick generation with optimized settings",
        "max_scenes": 3,
        "image_quality": "standard",
        "use_sora": False,
        "eta_multiplier": 0.6,
        "estimated_time_range": "1–2 minutes",
    },
    "balanced": {
        "label": "Balanced",
        "description": "Good quality with reasonable speed",
        "max_scenes": 5,
        "image_quality": "standard",
        "use_sora": True,
        "eta_multiplier": 1.0,
        "estimated_time_range": "2–4 minutes",
    },
    "high_quality": {
        "label": "High Quality",
        "description": "Best visuals and narration, takes longer",
        "max_scenes": 7,
        "image_quality": "hd",
        "use_sora": True,
        "eta_multiplier": 1.5,
        "estimated_time_range": "4–8 minutes",
    },
}


@router.post("/create")
async def create_engine_job(
    request: CreateEngineRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    current_user: dict = Depends(get_optional_user),
):
    """
    Create a new Story Engine job. Returns instantly with job_id for polling.
    Supports guest mode: first-time anonymous users get ONE free generation per IP.
    """
    # Determine auth mode
    is_guest = current_user is None
    user_id = None
    guest_ip = None

    if is_guest:
        # Guest mode — IP-based free trial
        guest_ip = req.client.host if req else "unknown"
        # Check if this IP already used their free trial
        existing = await db.free_trial_generations.find_one({"ip": guest_ip, "used": True})
        if existing:
            raise HTTPException(status_code=401, detail="Free trial used. Sign up to continue creating!")
        user_id = f"guest_{guest_ip}"
    else:
        user_id = current_user.get("id") or str(current_user.get("_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        await _check_rate_limit(user_id)

    # Map animation_style to style_id
    style_id = request.animation_style if request.animation_style in ANIMATION_STYLES else "cartoon_2d"

    # Safe rewrite — sanitize risky terms in story text and title before job creation
    story_rewrite = safe_rewrite(request.story_text)
    title_rewrite = safe_rewrite(request.title)
    safe_story = story_rewrite.rewritten_text
    safe_title = title_rewrite.rewritten_text

    if story_rewrite.was_rewritten or title_rewrite.was_rewritten:
        logger.info(f"[REWRITE] story-engine/create user={user_id}: story_changes={len(story_rewrite.changes)}, title_changes={len(title_rewrite.changes)}")

    result = await create_job(
        user_id=user_id,
        story_text=safe_story,
        title=safe_title,
        style_id=style_id,
        language="en",
        age_group=request.age_group,
        parent_job_id=request.parent_video_id,
        skip_credits=is_guest,  # Don't deduct credits for guests
    )

    if not result.get("success"):
        error = result.get("error", "Job creation failed")
        if error == "insufficient_credits" and not is_guest:
            cc = result.get("credit_check", {})
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: {cc.get('required', 0)}, Available: {cc.get('current', 0)}"
            )
        # Safety module rate-limit errors — convert to proper 429 with friendly message
        if error.startswith("SLOTS_BUSY:"):
            friendly_msg = error[len("SLOTS_BUSY:"):]
            raise HTTPException(status_code=429, detail=friendly_msg)
        raise HTTPException(status_code=400, detail=error)

    job_id = result["job_id"]

    # Mark free trial as used
    if is_guest:
        await db.free_trial_generations.update_one(
            {"ip": guest_ip},
            {"$set": {"ip": guest_ip, "used": True, "job_id": job_id, "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"is_guest": True, "guest_ip": guest_ip}}
        )

    # Store voice preset, animation style, and quality mode on the job for pipeline and UI
    quality_config = QUALITY_MODES.get(request.quality_mode, QUALITY_MODES["balanced"])
    update_fields = {
        "animation_style": request.animation_style,
        "voice_preset": request.voice_preset,
        "quality_mode": request.quality_mode,
        "quality_config": quality_config,
    }
    # Link to series if this is a series-driven creation
    if request.series_id:
        update_fields["series_id"] = request.series_id
    if request.episode_number is not None:
        update_fields["episode_number"] = request.episode_number
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": update_fields}
    )

    # ═══ CHECKPOINT REUSE — Skip already-done stages for Continue/Remix ═══
    reuse_analysis = None
    if request.parent_video_id:
        try:
            reuse_analysis = await apply_reuse_checkpoints(
                job_id=job_id,
                parent_job_id=request.parent_video_id,
                new_params={
                    "story_text": request.story_text,
                    "style_id": style_id,
                    "voice_preset": request.voice_preset,
                    "age_group": request.age_group,
                },
            )
            if reuse_analysis.get("reusable_stages"):
                logger.info(
                    f"[REUSE] Job {job_id[:8]}: Reusing {len(reuse_analysis['reusable_stages'])} stages, "
                    f"mode={reuse_analysis['reuse_mode']}, starting from {reuse_analysis['start_from']}"
                )
        except Exception as e:
            logger.warning(f"[REUSE] Failed to apply reuse for {job_id[:8]}: {e} — falling back to full pipeline")
            reuse_analysis = None

    # Run pipeline in background
    background_tasks.add_task(run_pipeline, job_id)

    # Track analytics
    try:
        await db.analytics_events.insert_one({
            "event": "video_generation_started",
            "user_id": user_id,
            "data": {
                "job_id": job_id,
                "credits": result.get("credits_deducted", 0),
                "style": style_id,
                "is_guest": is_guest,
                "reuse_mode": reuse_analysis.get("reuse_mode") if reuse_analysis else "fresh",
                "stages_reused": len(reuse_analysis.get("reusable_stages", [])) if reuse_analysis else 0,
            },
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception:
        pass

    response = {
        "success": True,
        "job_id": job_id,
        "credits_charged": result.get("credits_deducted", 0),
        "estimated_scenes": 5,
        "is_guest": is_guest,
        "reuse_mode": reuse_analysis.get("reuse_mode") if reuse_analysis else "fresh",
        "stages_reused": reuse_analysis.get("reusable_stages", []) if reuse_analysis else [],
        "stages_to_generate": reuse_analysis.get("invalidated_stages", []) if reuse_analysis else [],
        "message": "Video generation started. Poll /status for progress.",
    }

    # Include rewrite note if terms were sanitized
    if story_rewrite.was_rewritten or title_rewrite.was_rewritten:
        response["rewrite_note"] = story_rewrite.user_note or title_rewrite.user_note

    return response


@router.get("/status/{job_id}")
async def get_status(job_id: str, current_user: dict = Depends(get_optional_user)):
    """Poll job progress. Returns frontend-compatible response shape.
    Falls back to legacy pipeline_jobs if not found in story_engine_jobs."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        # Try legacy pipeline_jobs
        legacy = await db.pipeline_jobs.find_one({"job_id": job_id}, {"_id": 0, "story_text": 0})
        if legacy:
            return _legacy_status_response(legacy)
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership (or admin)
    if job["user_id"] != current_user.get("id") and current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Not your job")

    state = job["state"]
    legacy_status = _map_state_to_legacy_status(state)
    legacy_stage = _map_state_to_legacy_stage(state)
    progress = _state_to_progress(state)

    # Build stage summary from stage_results
    stages_summary = {}
    for sr in job.get("stage_results", []):
        stages_summary[sr.get("stage", "")] = {
            "status": sr.get("status", "PENDING").upper(),
            "duration_ms": int(sr.get("duration_seconds", 0) * 1000) if sr.get("duration_seconds") else None,
            "error": sr.get("error"),
        }

    # Build scene_progress from keyframe_urls
    scene_progress = []
    plans = job.get("scene_motion_plans") or []
    keyframes = job.get("keyframe_urls") or []
    for i, plan in enumerate(plans):
        kf_url = keyframes[i] if i < len(keyframes) else None
        if kf_url:
            kf_url = _make_presigned_url(kf_url)
        scene_progress.append({
            "scene_number": plan.get("scene_number", i + 1),
            "title": f"Scene {plan.get('scene_number', i + 1)}",
            "has_image": bool(kf_url),
            "image_url": kf_url,
            "has_voice": False,
            "voice_duration": None,
        })

    # Output URLs
    output_url = _make_presigned_url(job.get("output_url"))
    thumbnail_url = _make_presigned_url(job.get("thumbnail_url"))
    preview_url = _make_presigned_url(job.get("preview_url"))

    # ETA and elapsed time calculation
    elapsed_seconds = 0
    eta_seconds = None
    started_at_str = job.get("created_at")
    if started_at_str:
        try:
            started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            elapsed_seconds = int((datetime.now(timezone.utc) - started_at).total_seconds())
            if progress > 0 and progress < 100 and elapsed_seconds > 0:
                rate = progress / elapsed_seconds
                eta_seconds = int((100 - progress) / rate) if rate > 0 else None
        except (ValueError, AttributeError):
            pass

    # Compute media access for this user
    media_access = _get_media_access_for_user(current_user)
    can_dl = media_access.get("can_download", False)

    return {
        "success": True,
        "job": {
            "job_id": job["job_id"],
            "title": job.get("title", "Untitled"),
            "status": legacy_status,
            "progress": progress,
            "current_stage": legacy_stage,
            "current_step": get_label(JobState(state)),
            "output_url": output_url if can_dl else None,
            "thumbnail_url": thumbnail_url,
            "preview_url": preview_url,
            "error": job.get("error_message"),
            "error_code": job.get("last_error_code"),
            "stages": stages_summary,
            "scene_progress": scene_progress,
            "timing": {
                "elapsed_seconds": elapsed_seconds,
                "eta_seconds": eta_seconds,
            },
            "credits_charged": job.get("cost_estimate", {}).get("total_credits_required", 0),
            "credits_refunded": job.get("credits_refunded", 0),
            "notification_opt_in": job.get("notification_opt_in", False),
            "animation_style": job.get("animation_style", job.get("style_id", "cartoon_2d")),
            "age_group": job.get("age_group", "kids_5_8"),
            "voice_preset": job.get("voice_preset", "narrator_warm"),
            "story_text": job.get("story_text", ""),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
            "fallback": None,
            "has_recoverable_assets": bool(job.get("keyframe_urls")),
            "slug": job.get("slug"),
            "story_chain_id": job.get("story_chain_id"),
            "episode_number": job.get("episode_number"),
            "series_id": job.get("series_id"),
            # Engine-specific fields
            "engine_state": state,
            "used_ken_burns_fallback": job.get("used_ken_burns_fallback", False),
            "sora_clips_count": job.get("sora_clips_count", 0),
            "fallback_clips_count": job.get("fallback_clips_count", 0),
            # Honest retry/recovery info for UI
            "retry_info": {
                "current_attempt": job.get("current_attempt", 0),
                "max_attempts": job.get("max_stage_attempts", 0),
                "total_retries": job.get("retry_count", 0),
                "heartbeat_detail": job.get("heartbeat_detail", ""),
                "can_retry": state in [s.value for s in PER_STAGE_FAILURE_STATES],
                "last_error_stage": job.get("last_error_stage"),
            },
            # Quality mode
            "quality_mode": job.get("quality_mode", "balanced"),
            "quality_config": job.get("quality_config"),
            # Character-driven share data
            "characters": [
                {"name": c.get("name"), "role": c.get("role"), "personality": c.get("personality_core", "")}
                for c in (job.get("character_continuity") or {}).get("characters", [])
            ],
            "cliffhanger": (job.get("episode_plan") or {}).get("cliffhanger"),
            "trigger_text": (job.get("episode_plan") or {}).get("trigger_text"),
            "tension_peak": (job.get("episode_plan") or {}).get("tension_peak"),
            "cut_mood": (job.get("episode_plan") or {}).get("cut_mood"),
            # Reuse info — tells UI which stages were reused vs regenerated
            "reuse_info": job.get("reuse_info"),
            # Action control — single source of truth for UI buttons
            **_resolve_allowed_actions(job),
            # Media entitlement — controls download/preview UI
            "media_access": media_access,
        },
    }


@router.get("/analyze-reuse")
async def analyze_reuse_preview(
    parent_job_id: str = Query(...),
    animation_style: str = Query(default=None),
    voice_preset: str = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """
    Preview what stages can be reused from a parent job.
    Called BEFORE generation to show the user what will be fast-tracked.
    """
    from services.story_engine.pipeline import analyze_reuse

    parent = await db.story_engine_jobs.find_one({"job_id": parent_job_id}, {"_id": 0})
    if not parent:
        # Try legacy pipeline_jobs
        parent = await db.pipeline_jobs.find_one({"job_id": parent_job_id}, {"_id": 0})
    if not parent:
        raise HTTPException(status_code=404, detail="Parent job not found")
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    if parent.get("user_id") != user_id and current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Not your job")

    new_params = {}
    if animation_style:
        new_params["style_id"] = animation_style
    if voice_preset:
        new_params["voice_preset"] = voice_preset
    # Story text always changes for Continue, so it'll show full rerun for those

    analysis = analyze_reuse(parent, new_params)

    # Human-readable stage names for UI
    stage_labels = {
        "PLANNING": "Scene Planning",
        "BUILDING_CHARACTER_CONTEXT": "Character Design",
        "PLANNING_SCENE_MOTION": "Motion Planning",
        "GENERATING_KEYFRAMES": "Keyframe Images",
        "GENERATING_SCENE_CLIPS": "Video Clips",
        "GENERATING_AUDIO": "Narration Audio",
        "ASSEMBLING_VIDEO": "Final Assembly",
    }

    return {
        "success": True,
        "reuse_mode": analysis["reuse_mode"],
        "reusable_stages": [{"id": s, "label": stage_labels.get(s, s)} for s in analysis["reusable_stages"]],
        "invalidated_stages": [{"id": s, "label": stage_labels.get(s, s)} for s in analysis["invalidated_stages"]],
        "estimated_time_saved_percent": len(analysis["reusable_stages"]) / 7 * 100 if analysis["reusable_stages"] else 0,
    }


@router.get("/quality-modes")
async def get_quality_modes():
    """Return available quality modes with their descriptions and estimated times."""
    return {
        "success": True,
        "modes": QUALITY_MODES,
        "default": "balanced",
    }




@router.get("/validate-asset/{job_id}")
async def validate_video_asset(job_id: str, current_user: dict = Depends(get_current_user)):
    """
    Validate Story Video assets. Returns frontend-compatible validation state.
    Download URLs are scrubbed for free users — backend is source of truth.
    """
    media_access = _get_media_access_for_user(current_user)

    job = await db.story_engine_jobs.find_one(
        {"job_id": job_id},
        {"_id": 0, "state": 1, "output_url": 1, "preview_url": 1, "thumbnail_url": 1,
         "keyframe_urls": 1, "error_message": 1, "title": 1}
    )
    if not job:
        # Try legacy pipeline_jobs — delegate to old validation logic
        legacy = await db.pipeline_jobs.find_one(
            {"job_id": job_id},
            {"_id": 0, "status": 1, "output_url": 1, "scene_images": 1,
             "fallback_outputs": 1, "thumbnail_url": 1, "error": 1, "title": 1}
        )
        if not legacy:
            raise HTTPException(status_code=404, detail="Job not found")
        return _legacy_validate_response(legacy)

    state = job.get("state", "")
    legacy_status = _map_state_to_legacy_status(state)

    # If still processing
    if legacy_status in ("QUEUED", "PROCESSING"):
        return {
            "preview_ready": False, "download_ready": False, "share_ready": False,
            "poster_url": None, "download_url": None, "share_url": None, "story_pack_url": None,
            "ui_state": "PROCESSING", "stage_detail": f"Still generating ({get_label(JobState(state))})",
        }

    output_url = _make_presigned_url(job.get("output_url"))
    thumbnail_url = _make_presigned_url(job.get("thumbnail_url"))

    # Best poster: thumbnail > first keyframe
    poster_url = thumbnail_url
    if not poster_url:
        for kf in (job.get("keyframe_urls") or []):
            if kf:
                poster_url = _make_presigned_url(kf)
                break

    download_ready = bool(output_url)
    preview_ready = bool(poster_url)
    share_ready = bool(output_url)

    if state == "FAILED" and not download_ready:
        ui_state = "FAILED"
        stage_detail = job.get("error_message", "Generation failed")
    elif state in ("FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER") and not download_ready:
        ui_state = "FAILED"
        stage_detail = job.get("error_message", f"Failed at {state}")
    elif download_ready and preview_ready:
        ui_state = "READY"
        stage_detail = "Video ready — preview and download verified"
    elif download_ready and not preview_ready:
        ui_state = "PARTIAL_READY"
        stage_detail = "Video saved — download available, preview limited"
    elif state == "READY" and not download_ready:
        ui_state = "FAILED"
        stage_detail = "Generation completed but no downloadable asset found"
    elif state == "PARTIAL_READY":
        ui_state = "PARTIAL_READY"
        stage_detail = "Story assets available — full video may not be ready"
    elif state == "FAILED" and download_ready:
        ui_state = "PARTIAL_READY"
        stage_detail = "Generation had issues but some assets were saved"
    else:
        ui_state = "FAILED"
        stage_detail = job.get("error_message", "Unknown status")

    # Scrub download URLs for free users — backend is source of truth
    can_dl = media_access.get("can_download", False)

    return {
        "preview_ready": preview_ready,
        "download_ready": download_ready and can_dl,
        "share_ready": share_ready,
        "poster_url": poster_url,
        "download_url": output_url if can_dl else None,
        "share_url": None,  # Share uses slug-based public URLs, not raw asset URLs
        "story_pack_url": None,
        "ui_state": ui_state,
        "stage_detail": stage_detail,
        "job_status": legacy_status,
        "title": job.get("title", ""),
        "media_access": media_access,
    }



@router.post("/retry/{job_id}")
async def retry_failed_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retry a failed job from its last failed stage.
    Only works for per-stage failure states (FAILED_PLANNING, FAILED_IMAGES, etc.).
    """
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["user_id"] != current_user.get("id") and current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Not your job")

    state = job["state"]
    try:
        job_state = JobState(state)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown state: {state}")

    if job_state not in PER_STAGE_FAILURE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Job is in state '{state}' — can only retry jobs in a per-stage failure state"
        )

    # Get the retry target stage
    retry_target = FAILURE_TO_RETRY.get(job_state)
    if not retry_target:
        raise HTTPException(status_code=400, detail="No retry target for this failure state")

    # Transition back to the retry stage
    now = datetime.now(timezone.utc).isoformat()
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "state": retry_target.value,
            "last_heartbeat_at": now,
            "updated_at": now,
            "error_message": None,
            "heartbeat_detail": f"Manual retry — resuming from {retry_target.value}",
        }},
    )

    # Run pipeline in background
    background_tasks = BackgroundTasks()
    background_tasks.add_task(execute_pipeline, job_id)

    logger.info(f"[RETRY] Job {job_id[:8]} retrying from {retry_target.value}")
    return JSONResponse(
        content={
            "success": True,
            "job_id": job_id,
            "retrying_from": retry_target.value,
            "message": f"Retrying from {get_label(retry_target)}",
        },
        background=background_tasks,
    )


@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel an active or failed job. Refunds credits if applicable."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["user_id"] != current_user.get("id") and current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Not your job")

    state = job["state"]
    if state in ("READY", "PARTIAL_READY"):
        raise HTTPException(status_code=400, detail="Cannot cancel a completed job")

    now = datetime.now(timezone.utc).isoformat()
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "state": "FAILED",
            "error_message": "Cancelled by user",
            "last_error_code": "CANCELLED",
            "updated_at": now,
        }},
    )

    # Refund credits
    from services.story_engine.pipeline import _refund_credits
    await _refund_credits(job_id)

    logger.info(f"[CANCEL] Job {job_id[:8]} cancelled by user {current_user.get('id', '')[:12]}")
    return {
        "success": True,
        "job_id": job_id,
        "message": "Job cancelled. Credits will be refunded.",
    }



@router.get("/credit-check")
async def credit_check(user: dict = Depends(get_current_user)):
    """Pre-flight credit check."""
    user_doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "credits": 1})
    credits = user_doc.get("credits", 0) if user_doc else 0
    estimate = pre_flight_check(credits)
    return {
        "success": True,
        "sufficient": estimate.sufficient,
        "required": estimate.total_credits_required,
        "current": credits,
        "shortfall": estimate.shortfall,
        "breakdown": estimate.breakdown,
    }


@router.get("/user-jobs")
async def list_user_jobs(current_user: dict = Depends(get_current_user)):
    """Get ALL jobs for the current user — merges story_engine_jobs and legacy pipeline_jobs."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    media_access = _get_media_access_for_user(current_user)
    can_dl = media_access.get("can_download", False)
    jobs = []

    # 1. Story Engine jobs (new engine)
    cursor = db.story_engine_jobs.find(
        {"user_id": user_id},
        {"_id": 0, "story_text": 0, "episode_plan": 0, "character_continuity": 0,
         "scene_motion_plans": 0, "stage_results": 0},
    ).sort("created_at", -1).limit(50)

    async for doc in cursor:
        state = doc.get("state", "INIT")
        jobs.append({
            "job_id": doc["job_id"],
            "title": doc.get("title", "Untitled"),
            "status": _map_state_to_legacy_status(state),
            "progress": _state_to_progress(state),
            "current_stage": _map_state_to_legacy_stage(state),
            "output_url": _make_presigned_url(doc.get("output_url")) if can_dl else None,
            "thumbnail_url": _make_presigned_url(doc.get("thumbnail_url")),
            "thumbnail_small_url": _make_presigned_url(doc.get("thumbnail_url")),
            "animation_style": doc.get("animation_style", doc.get("style_id", "cartoon_2d")),
            "age_group": doc.get("age_group"),
            "voice_preset": doc.get("voice_preset"),
            "credits_charged": doc.get("cost_estimate", {}).get("total_credits_required", 0),
            "created_at": doc.get("created_at"),
            "completed_at": doc.get("completed_at"),
            "error": doc.get("error_message"),
            "has_recoverable_assets": bool(doc.get("keyframe_urls")),
            "engine_state": state,
            "source": "story_engine",
        })

    # 2. Legacy pipeline jobs
    legacy_cursor = db.pipeline_jobs.find(
        {"user_id": user_id, "status": {"$nin": ["ORPHANED"]}},
        {"_id": 0, "story_text": 0, "scenes": 0, "scene_images": 0, "scene_voices": 0},
    ).sort("created_at", -1).limit(50)

    async for doc in legacy_cursor:
        # Normalize datetime fields to ISO string for JSON serialization
        ca = doc.get("created_at")
        if hasattr(ca, 'isoformat'):
            ca = ca.isoformat()
        coa = doc.get("completed_at")
        if hasattr(coa, 'isoformat'):
            coa = coa.isoformat()

        jobs.append({
            "job_id": doc.get("job_id"),
            "title": doc.get("title", "Untitled"),
            "status": doc.get("status", "FAILED"),
            "progress": doc.get("progress", 0),
            "current_stage": doc.get("current_stage"),
            "output_url": _make_presigned_url(doc.get("output_url")) if can_dl else None,
            "thumbnail_url": _make_presigned_url(doc.get("thumbnail_url")),
            "animation_style": doc.get("animation_style", "cartoon_2d"),
            "age_group": doc.get("age_group"),
            "voice_preset": doc.get("voice_preset"),
            "credits_charged": doc.get("credits_charged", 0),
            "created_at": ca,
            "completed_at": coa,
            "error": doc.get("error"),
            "has_recoverable_assets": bool(doc.get("fallback_outputs")) or doc.get("fallback_status") not in (None, "none"),
            "source": "legacy_pipeline",
        })

    # Sort merged list by created_at descending (handle mixed datetime/str types)
    def _sort_key(j):
        ca = j.get("created_at") or ""
        if isinstance(ca, str):
            return ca
        return ca.isoformat() if hasattr(ca, 'isoformat') else str(ca)
    jobs.sort(key=_sort_key, reverse=True)
    return {"success": True, "jobs": jobs[:50]}


# Alias for frontend compatibility
@router.get("/my-jobs")
async def list_my_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    """Alias for /user-jobs with pagination."""
    return await list_user_jobs(user)


@router.post("/resume/{job_id}")
async def resume_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Resume a failed job. Handles both engine and legacy jobs."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})

    if job:
        # Story Engine job
        if job.get("user_id") != user_id and current_user.get("role", "").upper() != "ADMIN":
            raise HTTPException(status_code=403, detail="Not your job")

        state = job.get("state", "")
        actions = _resolve_allowed_actions(job)

        if state == JobState.READY.value:
            raise HTTPException(status_code=400, detail="Job already completed")

        # Only allow retry/resume if the action resolver says so
        if "retry" not in actions["allowed_actions"] and "start_over" not in actions["allowed_actions"]:
            raise HTTPException(
                status_code=400,
                detail=f"Job is currently {state.replace('_', ' ').lower()}. Cannot resume right now."
            )

        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"state": JobState.INIT.value, "error_message": None, "recovery_state": "NONE"}, "$inc": {"retry_count": 1}},
        )
        background_tasks.add_task(run_pipeline, job_id)
        return {"success": True, "message": "Pipeline resumed from beginning."}
    else:
        # Try legacy pipeline_jobs
        legacy = await db.pipeline_jobs.find_one({"job_id": job_id})
        if not legacy:
            raise HTTPException(status_code=404, detail="Job not found")
        if legacy.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not your job")
        if legacy.get("status") == "COMPLETED":
            raise HTTPException(status_code=400, detail="Job already completed")
        try:
            from services.pipeline_engine import resume_pipeline
            await resume_pipeline(job_id)
            from services.pipeline_worker import enqueue_job
            await enqueue_job(job_id, user_id=user_id, user_plan=current_user.get("plan", "free"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"success": True, "message": "Legacy pipeline resumed from last checkpoint."}


@router.get("/preview/{job_id}")
async def get_preview(job_id: str):
    """Preview data for a job — scene images and narration. Handles both engine and legacy jobs."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if job:
        scenes = []
        plans = job.get("scene_motion_plans") or []
        keyframes = job.get("keyframe_urls") or []
        ep_scenes = (job.get("episode_plan") or {}).get("scene_breakdown") or []
        for i, plan in enumerate(plans):
            kf_url = keyframes[i] if i < len(keyframes) else None
            ep_scene = ep_scenes[i] if i < len(ep_scenes) else {}
            scenes.append({
                "scene_number": plan.get("scene_number", i + 1),
                "title": f"Scene {plan.get('scene_number', i + 1)}",
                "image_url": _make_presigned_url(kf_url) if kf_url else None,
                "narration_text": ep_scene.get("action_summary", plan.get("action", "")),
                "duration": plan.get("clip_duration_seconds", 5.0),
            })
        episode_plan = job.get("episode_plan") or {}
        return {
            "success": True,
            "preview": {
                "title": job.get("title", "Untitled"),
                "total_scenes": len(scenes),
                "scenes": scenes,
                "final_video_url": _make_presigned_url(job.get("output_url")),
                "story_text": job.get("story_text", ""),
                "cliffhanger": episode_plan.get("cliffhanger"),
                "trigger_text": episode_plan.get("trigger_text"),
                "tension_peak": episode_plan.get("tension_peak"),
                "cut_mood": episode_plan.get("cut_mood"),
            },
        }
    else:
        # Legacy pipeline job
        legacy = await db.pipeline_jobs.find_one({"job_id": job_id})
        if not legacy:
            raise HTTPException(status_code=404, detail="Job not found")
        try:
            from services.fallback_pipeline import get_preview_data
            preview = await get_preview_data(legacy)
        except Exception:
            preview = {"title": legacy.get("title", ""), "total_scenes": 0, "scenes": []}
        fallback = legacy.get("fallback_outputs", {})
        preview["final_video_url"] = _make_presigned_url(legacy.get("output_url"))
        preview["fallback_video_url"] = _make_presigned_url(fallback.get("fallback_mp4", {}).get("url"))
        preview["story_pack_url"] = _make_presigned_url(fallback.get("story_pack_zip", {}).get("url"))
        return {"success": True, "preview": preview}


@router.post("/notify-when-ready/{job_id}")
async def subscribe_notify(job_id: str, current_user: dict = Depends(get_current_user)):
    """Subscribe to completion notification."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0, "user_id": 1, "state": 1})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your job")

    if job["state"] in (JobState.READY.value, JobState.PARTIAL_READY.value):
        return {"success": True, "message": "Job already completed", "already_done": True}

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"notify_on_complete": True, "notify_email": current_user.get("email", "")}}
    )
    return {"success": True, "message": "You'll be notified when your video is ready"}


# ═══════════════════════════════════════════════════════════════
# CHAIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/chain/{chain_id}")
async def get_story_chain(chain_id: str, user: dict = Depends(get_current_user)):
    """Get all episodes in a story chain."""
    cursor = db.story_engine_jobs.find(
        {"story_chain_id": chain_id},
        {"_id": 0, "job_id": 1, "title": 1, "state": 1, "episode_number": 1,
         "output_url": 1, "thumbnail_url": 1, "created_at": 1},
    ).sort("episode_number", 1)
    episodes = await cursor.to_list(length=100)
    return {"success": True, "chain_id": chain_id, "episodes": episodes, "total": len(episodes)}


@router.get("/asset-proxy")
async def proxy_asset_for_export(url: str):
    """Proxy R2 assets to bypass CORS for client-side video export."""
    import httpx
    from urllib.parse import urlparse
    from fastapi.responses import Response

    allowed_domains = ["r2.cloudflarestorage.com", "r2.dev"]
    parsed = urlparse(url)
    if not any(domain in parsed.netloc for domain in allowed_domains):
        raise HTTPException(status_code=403, detail="Only R2 bucket assets can be proxied")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch asset")
            return Response(
                content=resp.content,
                media_type=resp.headers.get("content-type", "application/octet-stream"),
                headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=3600"},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Asset download timed out")
    except Exception as e:
        logger.error(f"Asset proxy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to proxy asset")


@router.post("/generate-fallback/{job_id}")
async def generate_fallback(job_id: str, current_user: dict = Depends(get_current_user)):
    """Generate fallback assets for a failed job. Works for both engine and legacy jobs."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    # Try legacy pipeline_jobs first (most likely for fallback requests)
    job = await db.pipeline_jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your job")
    if job.get("fallback_outputs"):
        return {"success": True, "message": "Fallback already generated", "fallback": job["fallback_outputs"]}
    if not job.get("scenes") or not job.get("scene_images"):
        raise HTTPException(status_code=400, detail="No scene assets available")
    from services.fallback_pipeline import run_fallback_pipeline
    await run_fallback_pipeline(job_id, job.get("current_stage", "render"))
    updated = await db.pipeline_jobs.find_one({"job_id": job_id}, {"_id": 0, "fallback_outputs": 1, "fallback_status": 1})
    return {"success": True, "message": "Fallback generated", "fallback_status": updated.get("fallback_status")}


# ═══════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/admin/jobs")
async def admin_list_jobs(
    state: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(_get_admin),
):
    """Admin: List all Story Engine jobs with filters."""
    query = {}
    if state:
        query["state"] = state
    total = await db.story_engine_jobs.count_documents(query)
    cursor = db.story_engine_jobs.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
    jobs = await cursor.to_list(length=limit)
    stats = {}
    for s in JobState:
        stats[s.value] = await db.story_engine_jobs.count_documents({"state": s.value})
    return {"success": True, "jobs": jobs, "total": total, "stats": stats, "page": page}


@router.get("/admin/job/{job_id}")
async def admin_get_job(job_id: str, admin: dict = Depends(_get_admin)):
    """Admin: Get full job details."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "job": job}


@router.post("/admin/retry/{job_id}")
async def admin_retry_job(job_id: str, background_tasks: BackgroundTasks, admin: dict = Depends(_get_admin)):
    """Admin: Retry a failed job."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["state"] not in ("FAILED", "PARTIAL_READY"):
        raise HTTPException(status_code=400, detail=f"Can only retry FAILED/PARTIAL_READY jobs, current: {job['state']}")
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"state": JobState.INIT.value, "error_message": None}, "$inc": {"retry_count": 1}},
    )
    background_tasks.add_task(run_pipeline, job_id)
    return {"success": True, "message": f"Retrying job {job_id[:8]}"}


@router.post("/admin/retry-assembly/{job_id}")
async def admin_retry_assembly(job_id: str, background_tasks: BackgroundTasks, admin: dict = Depends(_get_admin)):
    """Admin: Re-run only FFmpeg assembly for a job that has all assets but failed at assembly."""
    from services.story_engine.pipeline import _stage_assembly
    from services.story_engine.continuity import validate_pipeline_outputs, should_mark_ready

    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Run assembly in background
    async def _retry_assembly():
        try:
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"state": JobState.ASSEMBLING_VIDEO.value, "error_message": None}}
            )
            result = await _stage_assembly(job)
            if result.get("status") == "success" and result.get("output", {}).get("output_url"):
                await db.story_engine_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {"state": JobState.VALIDATING.value}}
                )
                # Re-validate
                updated_job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
                validation = validate_pipeline_outputs(updated_job)
                final_state = should_mark_ready(validation)
                await db.story_engine_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "state": final_state,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "validation_result": validation.to_dict(),
                    }}
                )
                logger.info(f"[RETRY-ASSEMBLY] Job {job_id[:8]} assembly completed: {final_state}")
            else:
                error_msg = result.get("error", "Assembly produced no output")
                await db.story_engine_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {"state": JobState.FAILED.value, "error_message": error_msg}}
                )
        except Exception as e:
            logger.error(f"[RETRY-ASSEMBLY] Job {job_id[:8]} failed: {e}")
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"state": JobState.FAILED.value, "error_message": str(e)[:500]}}
            )

    background_tasks.add_task(_retry_assembly)
    return {"success": True, "message": f"Retrying assembly for {job_id[:8]}"}


@router.get("/admin/pipeline-health")
async def admin_pipeline_health(admin: dict = Depends(_get_admin)):
    """Admin: Pipeline health overview."""
    total_jobs = await db.story_engine_jobs.count_documents({})
    active_states = [s.value for s in JobState if s not in (JobState.READY, JobState.PARTIAL_READY, JobState.FAILED)]
    active = await db.story_engine_jobs.count_documents({"state": {"$in": active_states}})
    ready = await db.story_engine_jobs.count_documents({"state": "READY"})
    failed = await db.story_engine_jobs.count_documents({"state": "FAILED"})
    return {
        "success": True,
        "total_jobs": total_jobs,
        "active_jobs": active,
        "ready_jobs": ready,
        "failed_jobs": failed,
        "success_rate": round(ready / max(total_jobs, 1) * 100, 1),
    }


@router.get("/admin/generation-analytics")
async def admin_generation_analytics(
    days: int = Query(default=7, ge=1, le=90),
    admin: dict = Depends(_get_admin),
):
    """
    Admin: Generation analytics — completion rate, stall rate, retry rate,
    recovery success rate, ETA accuracy, time to first status, and
    fresh vs continue vs remix completion times.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    # created_at may be stored as either datetime or ISO string — match both
    date_filter = {"$or": [
        {"created_at": {"$gte": cutoff}},
        {"created_at": {"$gte": cutoff_str}},
    ]}

    pipeline = [
        {"$match": date_filter},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "completed": {"$sum": {"$cond": [{"$eq": ["$state", "READY"]}, 1, 0]}},
            "partial": {"$sum": {"$cond": [{"$eq": ["$state", "PARTIAL_READY"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$in": ["$state", ["FAILED", "FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER"]]}, 1, 0]}},
            "total_retries": {"$sum": {"$ifNull": ["$retry_count", 0]}},
            "jobs_with_retries": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$retry_count", 0]}, 0]}, 1, 0]}},
            "reuse_jobs": {"$sum": {"$cond": [{"$ne": [{"$ifNull": ["$reuse_info.reuse_mode", "fresh"]}, "fresh"]}, 1, 0]}},
            "fresh_jobs": {"$sum": {"$cond": [{"$eq": [{"$ifNull": ["$reuse_info.reuse_mode", "fresh"]}, "fresh"]}, 1, 0]}},
            "style_remixes": {"$sum": {"$cond": [{"$eq": ["$reuse_info.reuse_mode", "style_remix"]}, 1, 0]}},
            "voice_remixes": {"$sum": {"$cond": [{"$eq": ["$reuse_info.reuse_mode", "voice_remix"]}, 1, 0]}},
            "continues": {"$sum": {"$cond": [{"$eq": ["$reuse_info.reuse_mode", "continue"]}, 1, 0]}},
            "fast_mode": {"$sum": {"$cond": [{"$eq": ["$quality_mode", "fast"]}, 1, 0]}},
            "balanced_mode": {"$sum": {"$cond": [{"$eq": [{"$ifNull": ["$quality_mode", "balanced"]}, "balanced"]}, 1, 0]}},
            "high_quality_mode": {"$sum": {"$cond": [{"$eq": ["$quality_mode", "high_quality"]}, 1, 0]}},
        }},
    ]

    results = await db.story_engine_jobs.aggregate(pipeline).to_list(1)
    stats = results[0] if results else {}

    total = stats.get("total", 0)
    completed = stats.get("completed", 0)
    failed = stats.get("failed", 0)

    # Compute timing stats from stage_results
    timing_pipeline = [
        {"$match": {"$and": [date_filter, {"state": "READY"}]}},
        {"$project": {
            "_id": 0,
            "reuse_mode": {"$ifNull": ["$reuse_info.reuse_mode", "fresh"]},
            "quality_mode": {"$ifNull": ["$quality_mode", "balanced"]},
            "timing": 1,
        }},
    ]
    timing_docs = await db.story_engine_jobs.aggregate(timing_pipeline).to_list(500)

    fresh_times = [d["timing"]["total_ms"] / 1000 for d in timing_docs if d.get("timing", {}).get("total_ms") and d.get("reuse_mode") == "fresh"]
    reuse_times = [d["timing"]["total_ms"] / 1000 for d in timing_docs if d.get("timing", {}).get("total_ms") and d.get("reuse_mode") != "fresh"]

    avg_fresh = round(sum(fresh_times) / len(fresh_times), 1) if fresh_times else None
    avg_reuse = round(sum(reuse_times) / len(reuse_times), 1) if reuse_times else None

    return {
        "success": True,
        "period_days": days,
        "totals": {
            "total_jobs": total,
            "completed": completed,
            "partial_ready": stats.get("partial", 0),
            "failed": failed,
            "completion_rate": round(completed / max(total, 1) * 100, 1),
            "failure_rate": round(failed / max(total, 1) * 100, 1),
        },
        "retries": {
            "total_retries": stats.get("total_retries", 0),
            "jobs_with_retries": stats.get("jobs_with_retries", 0),
            "retry_rate": round(stats.get("jobs_with_retries", 0) / max(total, 1) * 100, 1),
        },
        "reuse": {
            "total_reuse_jobs": stats.get("reuse_jobs", 0),
            "fresh_jobs": stats.get("fresh_jobs", 0),
            "style_remixes": stats.get("style_remixes", 0),
            "voice_remixes": stats.get("voice_remixes", 0),
            "continues": stats.get("continues", 0),
        },
        "quality_modes": {
            "fast": stats.get("fast_mode", 0),
            "balanced": stats.get("balanced_mode", 0),
            "high_quality": stats.get("high_quality_mode", 0),
        },
        "timing": {
            "avg_fresh_completion_seconds": avg_fresh,
            "avg_reuse_completion_seconds": avg_reuse,
            "speedup_percent": round((1 - avg_reuse / avg_fresh) * 100, 1) if avg_fresh and avg_reuse and avg_fresh > 0 else None,
            "sample_size_fresh": len(fresh_times),
            "sample_size_reuse": len(reuse_times),
        },
    }
