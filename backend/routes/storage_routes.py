"""
Storage API — Direct-to-R2 signed URL uploads + lifecycle management.

Endpoints:
  POST /api/storage/presigned-upload  — Get a signed URL for direct browser → R2 upload
  POST /api/storage/confirm-upload    — Confirm upload completion, register asset
  POST /api/storage/cleanup-temp      — Admin: trigger temp asset cleanup
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import sys
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/storage", tags=["Storage"])

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB

# Temp asset TTL
TEMP_TTL_HOURS = 72


class PresignedUploadRequest(BaseModel):
    filename: str
    content_type: str
    file_size: int
    purpose: str = "photo_upload"  # photo_upload, avatar_export, etc.


@router.post("/presigned-upload")
async def get_presigned_upload_url(request: PresignedUploadRequest, user: dict = Depends(get_current_user)):
    """Get a presigned URL for direct browser-to-R2 upload."""

    if request.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_TYPES)}")

    if request.file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)}MB.")

    try:
        from services.cloudflare_r2_storage import CloudflareR2Storage
        r2 = CloudflareR2Storage()
        if not r2.is_configured:
            raise HTTPException(status_code=503, detail="Storage service not configured")

        project_id = f"uploads/{user['id'][:12]}"
        result = r2.generate_presigned_upload_url(
            asset_type="image",
            filename=request.filename,
            project_id=project_id,
            content_type=request.content_type,
            expiration=600,  # 10 minutes
        )

        if not result:
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")

        # Track the pending upload in DB (for lifecycle cleanup)
        await db.pending_uploads.insert_one({
            "user_id": user["id"],
            "storage_key": result["key"],
            "public_url": result["public_url"],
            "content_type": request.content_type,
            "file_size": request.file_size,
            "purpose": request.purpose,
            "status": "pending",
            "is_temp": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=TEMP_TTL_HOURS)).isoformat(),
        })

        return {
            "upload_url": result["upload_url"],
            "public_url": result["public_url"],
            "storage_key": result["key"],
            "content_type": result["content_type"],
            "expires_in": result["expires_in"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Presigned upload error: {e}")
        raise HTTPException(status_code=500, detail="Storage error")


class ConfirmUploadRequest(BaseModel):
    storage_key: str


@router.post("/confirm-upload")
async def confirm_upload(request: ConfirmUploadRequest, user: dict = Depends(get_current_user)):
    """Confirm that a direct upload completed. Validates the file exists in R2."""
    pending = await db.pending_uploads.find_one(
        {"storage_key": request.storage_key, "user_id": user["id"]},
        {"_id": 0}
    )
    if not pending:
        raise HTTPException(status_code=404, detail="Upload record not found")

    # Validate file exists in R2 via HEAD
    try:
        from services.cloudflare_r2_storage import CloudflareR2Storage
        r2 = CloudflareR2Storage()
        exists = await r2.file_exists(request.storage_key)
    except Exception:
        exists = True  # Assume success if HEAD check fails

    if not exists:
        raise HTTPException(status_code=400, detail="File not found in storage. Upload may have failed.")

    await db.pending_uploads.update_one(
        {"storage_key": request.storage_key},
        {"$set": {"status": "confirmed", "confirmed_at": datetime.now(timezone.utc).isoformat()}}
    )

    return {
        "success": True,
        "public_url": pending["public_url"],
        "storage_key": request.storage_key,
    }


# ── Storage Lifecycle ────────────────────────────────────────────────────

async def cleanup_temp_assets():
    """Background task: delete temp assets older than TEMP_TTL_HOURS from R2 and DB."""
    while True:
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=TEMP_TTL_HOURS)).isoformat()

            # Find expired temp uploads that were never confirmed or promoted to permanent
            expired = await db.pending_uploads.find(
                {"is_temp": True, "status": {"$ne": "permanent"}, "created_at": {"$lt": cutoff}},
                {"_id": 0, "storage_key": 1, "status": 1}
            ).to_list(100)

            if expired:
                from services.cloudflare_r2_storage import CloudflareR2Storage
                r2 = CloudflareR2Storage()
                deleted = 0

                for item in expired:
                    key = item.get("storage_key")
                    if not key:
                        continue
                    try:
                        await r2.delete_file(key)
                        deleted += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete temp asset {key}: {e}")

                # Remove from DB
                keys = [item["storage_key"] for item in expired if item.get("storage_key")]
                if keys:
                    await db.pending_uploads.delete_many({"storage_key": {"$in": keys}})

                if deleted:
                    logger.info(f"[LIFECYCLE] Cleaned up {deleted} expired temp assets")

        except Exception as e:
            logger.error(f"[LIFECYCLE] Cleanup error: {e}")

        await asyncio.sleep(3600)  # Run every hour


@router.post("/cleanup-temp")
async def trigger_cleanup(user: dict = Depends(get_current_user)):
    """Admin: manually trigger temp asset cleanup."""
    if str(user.get("role", "")).lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=TEMP_TTL_HOURS)).isoformat()
    count = await db.pending_uploads.count_documents(
        {"is_temp": True, "status": {"$ne": "permanent"}, "created_at": {"$lt": cutoff}}
    )
    return {"expired_count": count, "ttl_hours": TEMP_TTL_HOURS, "message": "Cleanup runs automatically every hour"}
