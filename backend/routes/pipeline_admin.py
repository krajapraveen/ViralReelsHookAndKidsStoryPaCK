"""Admin diagnostics for pipeline jobs — per-job validation health check."""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from shared import db, get_admin_user
import os
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("pipeline_admin")
router = APIRouter(prefix="/admin/pipeline", tags=["admin-pipeline"])


@router.get("/diagnostics")
async def pipeline_diagnostics(admin: dict = Depends(get_admin_user), limit: int = 50):
    """Per-job diagnostics: render_path, audio, duration, scene counts, validation failures."""
    jobs = await db.pipeline_jobs.find(
        {}, {"_id": 0, "job_id": 1, "user_id": 1, "title": 1, "status": 1,
             "estimated_scenes": 1, "scene_images": 1, "scene_voices": 1,
             "render_path": 1, "output_url": 1, "diagnostics": 1,
             "validation_failures": 1, "credits_refunded": 1, "created_at": 1,
             "completed_at": 1, "failure_reason": 1}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    rows = []
    for j in jobs:
        scenes_rendered = len(j.get("scene_images") or {})
        scenes_voiced = len(j.get("scene_voices") or {})
        expected = j.get("estimated_scenes", 0)
        diag = j.get("diagnostics") or {}
        rows.append({
            "job_id": j.get("job_id"),
            "user_id": j.get("user_id"),
            "title": (j.get("title") or "")[:60],
            "status": j.get("status"),
            "expected_scenes": expected,
            "scenes_rendered": scenes_rendered,
            "scenes_voiced": scenes_voiced,
            "render_path_present": bool(j.get("render_path")),
            "output_url_present": bool(j.get("output_url")),
            "audio_stream_present": diag.get("audio_stream_present", False) if j.get("status") == "COMPLETED" else None,
            "duration_sec": diag.get("duration_sec", 0) if j.get("status") == "COMPLETED" else None,
            "validation_failures": j.get("validation_failures") or [],
            "failure_reason": j.get("failure_reason"),
            "credits_refunded": j.get("credits_refunded", 0),
            "created_at": j.get("created_at"),
            "completed_at": j.get("completed_at"),
        })

    # Summary
    total = len(rows)
    completed = sum(1 for r in rows if r["status"] == "COMPLETED")
    false_completed = sum(1 for r in rows if r["status"] == "COMPLETED" and not r["render_path_present"] and not r["output_url_present"])
    failed = sum(1 for r in rows if r["status"] == "FAILED")
    refunded = sum(r["credits_refunded"] or 0 for r in rows)

    return {
        "success": True,
        "summary": {
            "total": total,
            "completed": completed,
            "false_completed": false_completed,
            "failed": failed,
            "credits_refunded_sum": refunded,
        },
        "rows": rows,
    }


@router.post("/cleanup-false-completed")
async def cleanup_false_completed(admin: dict = Depends(get_admin_user)):
    """Find old COMPLETED jobs with no render_path/output_url and flip them to FAILED with auto-refund."""
    bad = await db.pipeline_jobs.find(
        {"status": "COMPLETED", "render_path": None, "output_url": None},
        {"_id": 0}
    ).to_list(1000)
    fixed = 0
    refunded_total = 0
    now = datetime.now(timezone.utc)
    for j in bad:
        user_id = j.get("user_id")
        credits = int(j.get("credit_cost") or 0)
        if user_id and credits > 0:
            await db.users.update_one({"id": user_id}, {"$inc": {"credits": credits}})
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "amount": credits,
                "type": "PIPELINE_REFUND_RETROACTIVE",
                "description": f"Retroactive refund — job {j.get('job_id','?')[:8]} marked completed without render output",
                "createdAt": now.isoformat(),
            })
            refunded_total += credits
        await db.pipeline_jobs.update_one(
            {"job_id": j.get("job_id")},
            {"$set": {
                "status": "FAILED",
                "failure_reason": "RETROACTIVE_NO_RENDER",
                "validation_failures": ["NO_RENDER_PATH", "NO_OUTPUT_URL"],
                "credits_refunded": credits,
                "failed_at": now,
            }}
        )
        fixed += 1
    return {"success": True, "fixed": fixed, "credits_refunded_total": refunded_total}
