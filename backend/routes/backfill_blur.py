"""
Backfill Blurhash — Generates thumb_blur for existing stories that lack it.
Runs in batches, non-blocking. Admin-only endpoint.
"""
import os
import io
import base64
import logging
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, BackgroundTasks

from shared import db, get_current_user
from PIL import Image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/backfill", tags=["admin-backfill"])

CDN_BASE = os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", "")


def _extract_r2_key(url: str) -> str | None:
    """Extract R2 object key from any stored URL format."""
    if not url:
        return None
    try:
        base = url.split("?")[0]
        if ".r2.dev/" in base:
            return base.split(".r2.dev/", 1)[1]
        if ".r2.cloudflarestorage.com/" in base:
            parts = base.split(".r2.cloudflarestorage.com/", 1)
            if len(parts) > 1:
                bk = parts[1].split("/", 1)
                return bk[1] if len(bk) > 1 else None
        if url.startswith("/api/media/r2/"):
            return url[len("/api/media/r2/"):]
        if not url.startswith("http") and not url.startswith("/"):
            return url
    except Exception:
        pass
    return None


def _generate_blur_from_bytes(image_bytes: bytes) -> dict | None:
    """Generate a tiny base64 JPEG blur placeholder from raw image bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((32, 32), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=20, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return {"type": "inline_base64", "value": f"data:image/jpeg;base64,{b64}"}
    except Exception as e:
        logger.error(f"[BACKFILL] blur generation failed: {e}")
        return None


async def _backfill_batch(batch_size: int = 50):
    """Process a batch of stories missing thumb_blur."""
    if not CDN_BASE:
        logger.error("[BACKFILL] CLOUDFLARE_R2_PUBLIC_URL not set, cannot backfill")
        return {"processed": 0, "success": 0, "error": "CDN_BASE not configured"}

    # Find stories with media but no thumb_blur
    query = {
        "$and": [
            {"$or": [
                {"media.thumbnail_small.url": {"$exists": True, "$ne": None}},
                {"thumbnail_url": {"$exists": True, "$ne": None}},
                {"thumbnail_small_url": {"$exists": True, "$ne": None}},
            ]},
            {"$or": [
                {"media.thumb_blur": {"$exists": False}},
                {"media.thumb_blur": None},
            ]},
        ]
    }

    proj = {
        "_id": 0, "job_id": 1,
        "media": 1, "thumbnail_url": 1, "thumbnail_small_url": 1,
        "scene_images": 1,
    }

    # Check both collections
    se_jobs = await db.story_engine_jobs.find(query, proj).limit(batch_size).to_list(batch_size)
    pj_jobs = await db.pipeline_jobs.find(query, proj).limit(batch_size).to_list(batch_size)

    all_jobs = [(j, "story_engine_jobs") for j in se_jobs] + [(j, "pipeline_jobs") for j in pj_jobs]

    processed = 0
    success = 0
    errors = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for job, collection in all_jobs:
            job_id = job.get("job_id", "unknown")
            processed += 1

            # Resolve best available image URL
            media = job.get("media") or {}
            thumb_raw = (media.get("thumbnail_small") or {}).get("url")
            if not thumb_raw:
                thumb_raw = job.get("thumbnail_small_url") or job.get("thumbnail_url")
            if not thumb_raw:
                si = job.get("scene_images") or {}
                if si:
                    fk = sorted(si.keys(), key=lambda k: int(k) if k.isdigit() else 999)
                    if fk and isinstance(si.get(fk[0]), dict):
                        thumb_raw = si[fk[0]].get("url")

            key = _extract_r2_key(thumb_raw)
            if not key:
                errors.append(f"{job_id[:8]}: no resolvable image key")
                continue

            # Download from CDN
            cdn_url = f"{CDN_BASE}/{key}"
            try:
                resp = await client.get(cdn_url)
                if resp.status_code != 200:
                    errors.append(f"{job_id[:8]}: CDN {resp.status_code}")
                    continue

                blur = _generate_blur_from_bytes(resp.content)
                if not blur:
                    errors.append(f"{job_id[:8]}: blur gen failed")
                    continue

                # Update DB
                coll = db[collection]
                await coll.update_one(
                    {"job_id": job_id},
                    {"$set": {"media.thumb_blur": blur}},
                )
                success += 1

            except Exception as e:
                errors.append(f"{job_id[:8]}: {str(e)[:60]}")

    logger.info(f"[BACKFILL] Batch complete: {success}/{processed} succeeded")
    return {"processed": processed, "success": success, "errors": errors[:10]}


@router.post("/thumb-blur")
async def trigger_backfill(
    background_tasks: BackgroundTasks,
    batch_size: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """Trigger a background backfill of thumb_blur for existing stories.
    Admin-only. Non-blocking — runs in background."""
    role = current_user.get("role", "").upper()
    if role not in ("ADMIN", "SUPERADMIN"):
        return {"error": "Admin access required"}

    background_tasks.add_task(_backfill_batch, batch_size)
    return {"status": "started", "batch_size": batch_size}


@router.get("/thumb-blur/status")
async def backfill_status(current_user: dict = Depends(get_current_user)):
    """Check how many stories still need thumb_blur."""
    role = current_user.get("role", "").upper()
    if role not in ("ADMIN", "SUPERADMIN"):
        return {"error": "Admin access required"}

    query_missing = {"$or": [
        {"media.thumb_blur": {"$exists": False}},
        {"media.thumb_blur": None},
    ]}
    query_has = {"media.thumb_blur": {"$exists": True, "$ne": None}}

    se_missing = await db.story_engine_jobs.count_documents(query_missing)
    pj_missing = await db.pipeline_jobs.count_documents(query_missing)
    se_done = await db.story_engine_jobs.count_documents(query_has)
    pj_done = await db.pipeline_jobs.count_documents(query_has)

    return {
        "missing": {"story_engine": se_missing, "pipeline": pj_missing, "total": se_missing + pj_missing},
        "done": {"story_engine": se_done, "pipeline": pj_done, "total": se_done + pj_done},
    }


@router.post("/thumb-blur/sync")
async def sync_backfill(
    batch_size: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """Run backfill synchronously (blocking). Use for testing or small batches."""
    role = current_user.get("role", "").upper()
    if role not in ("ADMIN", "SUPERADMIN"):
        return {"error": "Admin access required"}

    result = await _backfill_batch(batch_size)
    return result
