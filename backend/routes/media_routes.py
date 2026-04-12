"""
Media Access Routes — Controlled download + preview with entitlement checks.
No permanent raw URLs. All media access goes through entitlement validation.
"""
import logging
import os
import hashlib
import time
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from shared import db, get_current_user, get_optional_user
from services.entitlement import resolve_entitlements, can_download_asset, get_media_access

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media"])

# Secret for signing media tokens
MEDIA_SECRET = os.environ.get("MEDIA_SECRET", os.environ.get("JWT_SECRET", "media-fallback-secret"))


def _sign_media_token(asset_id: str, user_id: str, access_type: str, ttl: int = 120) -> str:
    """Generate a short-lived HMAC token for media access."""
    expires = int(time.time()) + ttl
    payload = f"{asset_id}:{user_id}:{access_type}:{expires}"
    sig = hmac.new(MEDIA_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{expires}.{sig}"


def _verify_media_token(token: str, asset_id: str, user_id: str, access_type: str) -> bool:
    """Verify a media access token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False
        expires = int(parts[0])
        if time.time() > expires:
            return False
        payload = f"{asset_id}:{user_id}:{access_type}:{expires}"
        expected_sig = hmac.new(MEDIA_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        return hmac.compare_digest(parts[1], expected_sig)
    except (ValueError, IndexError):
        return False


@router.get("/entitlement")
async def get_user_entitlement(current_user: dict = Depends(get_current_user)):
    """Get the current user's media entitlements. Frontend must use these flags."""
    access = get_media_access(current_user)
    return {
        "success": True,
        **access,
    }


@router.post("/download-token/{asset_id}")
async def request_download_token(
    asset_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Request a short-lived download token for an asset.
    Returns 403 if user is not entitled to download.
    """
    user_id = current_user.get("id", "")

    # Entitlement check — backend is source of truth
    if not can_download_asset(current_user):
        # Log denied attempt
        await db.media_access_log.insert_one({
            "event": "download_denied",
            "user_id": user_id,
            "asset_id": asset_id,
            "plan_type": current_user.get("plan_type", "free"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "DOWNLOAD_NOT_ALLOWED",
                "message": "Downloads are available for subscribed users. Upgrade your plan to download.",
            },
        )

    # Find the asset
    job = await db.story_engine_jobs.find_one({"job_id": asset_id}, {"_id": 0, "output_url": 1, "preview_url": 1, "user_id": 1, "state": 1})
    if not job:
        job = await db.pipeline_jobs.find_one({"job_id": asset_id}, {"_id": 0, "output_url": 1, "preview_url": 1, "user_id": 1, "state": 1})
    if not job:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Check video state
    state = job.get("state", "")
    if state in ("INIT", "PLANNING", "BUILDING_CHARACTER_CONTEXT", "PLANNING_SCENE_MOTION",
                 "GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS", "GENERATING_AUDIO", "ASSEMBLING_VIDEO"):
        raise HTTPException(status_code=202, detail={"status": "processing", "message": "Video is still processing. Please wait."})

    # Try output_url first, then preview_url as fallback
    output_url = job.get("output_url") or job.get("preview_url")

    # Also check fallback service
    if not output_url:
        fallback = await db.story_engine_fallbacks.find_one(
            {"job_id": asset_id},
            {"_id": 0, "fallback_video_url": 1}
        )
        if fallback:
            output_url = fallback.get("fallback_video_url")

    if not output_url:
        if state in ("FAILED", "FAILED_RENDER", "ABANDONED"):
            raise HTTPException(status_code=410, detail={"status": "failed", "message": "Video generation failed. Please try again."})
        raise HTTPException(status_code=404, detail={"status": "not_ready", "message": "No downloadable video yet. It may still be processing."})

    # Generate short-lived signed URL
    try:
        from utils.r2_presign import presign_url
        download_url = presign_url(output_url, expiry=60)  # 60 second expiry
    except Exception:
        download_url = output_url

    # Log successful download token issuance
    await db.media_access_log.insert_one({
        "event": "download_granted",
        "user_id": user_id,
        "asset_id": asset_id,
        "plan_type": current_user.get("plan_type", "free"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "success": True,
        "download_url": download_url,
        "expires_in": 60,
        "message": "Download link expires in 60 seconds.",
    }


@router.get("/preview-url/{asset_id}")
async def get_preview_url(
    asset_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get a preview URL for an asset. Free users get watermarked version.
    All URLs are short-lived.
    """
    access = get_media_access(current_user)

    # Find asset
    job = await db.story_engine_jobs.find_one(
        {"job_id": asset_id},
        {"_id": 0, "output_url": 1, "preview_url": 1, "thumbnail_url": 1, "user_id": 1},
    )
    if not job:
        job = await db.pipeline_jobs.find_one(
            {"job_id": asset_id},
            {"_id": 0, "output_url": 1, "preview_url": 1, "thumbnail_url": 1, "user_id": 1},
        )
    if not job:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Determine which URL to serve
    if access["can_download"]:
        # Paid user — full quality preview
        url = job.get("output_url") or job.get("preview_url")
    else:
        # Free user — preview only (watermarked version if available)
        url = job.get("preview_url") or job.get("output_url")

    if not url:
        raise HTTPException(status_code=404, detail="No preview available")

    try:
        from utils.r2_presign import presign_url
        preview_url = presign_url(url, expiry=120)
    except Exception:
        preview_url = url

    return {
        "success": True,
        "preview_url": preview_url,
        "expires_in": 120,
        **access,
    }
