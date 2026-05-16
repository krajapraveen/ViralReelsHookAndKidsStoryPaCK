"""
Activation Digest — Admin Endpoints
2026-05 P0. Brutally concise operational truth for the founder's 8 AM IST inbox.

Endpoints:
  GET  /api/admin/activation-digest/latest     → most recent persisted digest
  GET  /api/admin/activation-digest/history    → last N digests (default 30)
  POST /api/admin/activation-digest/run-now    → recompute + persist + email (admin trigger)
  GET  /api/admin/activation-digest/preview    → compute fresh WITHOUT persisting (debug)
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from shared import db, get_admin_user
from services.activation_digest_service import (
    get_activation_digest_service,
    MAX_DIGESTS_RETAINED,
    COLLECTION_NAME,
    _format_digest_text,
)

router = APIRouter(prefix="/admin/activation-digest", tags=["Activation Digest"])


@router.get("/latest")
async def latest_digest(user: dict = Depends(get_admin_user)):
    doc = await db[COLLECTION_NAME].find_one(
        {}, {"_id": 0}, sort=[("generated_at", -1)],
    )
    if not doc:
        return {"success": True, "digest": None, "text": None,
                "note": "No digest persisted yet. Call /run-now or wait for 08:00 IST scheduler."}
    return {"success": True, "digest": doc, "text": _format_digest_text(doc)}


@router.get("/history")
async def digest_history(
    user: dict = Depends(get_admin_user),
    limit: int = Query(MAX_DIGESTS_RETAINED, ge=1, le=MAX_DIGESTS_RETAINED),
):
    cursor = db[COLLECTION_NAME].find({}, {"_id": 0}).sort("generated_at", -1).limit(limit)
    docs = [d async for d in cursor]
    return {"success": True, "count": len(docs), "retained_max": MAX_DIGESTS_RETAINED, "digests": docs}


@router.post("/run-now")
async def run_digest_now(
    user: dict = Depends(get_admin_user),
    skip_email: bool = Query(False),
):
    svc = get_activation_digest_service(db)
    result = await svc.run_once(also_email=not skip_email)
    return {"success": True, **result}


@router.get("/preview")
async def preview_digest(user: dict = Depends(get_admin_user)):
    """Compute the digest fresh WITHOUT persisting — useful for debugging."""
    svc = get_activation_digest_service(db)
    digest = await svc.compute()
    return {"success": True, "digest": digest, "text": _format_digest_text(digest)}
