"""
Daily Viral Idea Drop — V2 API Routes
Growth Engine: Shareable output, soft paywall, viral hooks, metrics tracking.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import logging

from shared import db, get_current_user
from services.viral import viral_job_service as jobs
from services.viral.task_dispatch import dispatch_task, Q_ORCHESTRATOR, Q_REPAIR

logger = logging.getLogger("viral.routes")
router = APIRouter(prefix="/viral-ideas", tags=["Viral Ideas V2"])


class GenerateBundleRequest(BaseModel):
    idea: str
    niche: str = "Tech"


class GenerateBundleResponse(BaseModel):
    job_id: str
    status: str
    message: str
    locked: bool
    share_url: str


class FeedbackRequest(BaseModel):
    signal: str
    asset_type: Optional[str] = None
    comment: Optional[str] = None


VALID_SIGNALS = {"useful", "not_useful", "regenerate_angle", "more_aggressive_hook", "safer_hook", "better_captions"}


# ==================== FALLBACK IDEAS — NEVER EMPTY ====================
FALLBACK_IDEAS = [
    {"idea": "Things that look fake but are real", "type": "viral", "niche": "Entertainment", "trending_score": 97, "badge": "trending"},
    {"idea": "You won't believe what happened next", "type": "story", "niche": "Lifestyle", "trending_score": 95, "badge": "trending"},
    {"idea": "Before vs After transformation that shocked everyone", "type": "transformation", "niche": "Fitness", "trending_score": 94, "badge": "fast_growing"},
    {"idea": "This changed everything for me", "type": "story", "niche": "Business", "trending_score": 93, "badge": "trending"},
    {"idea": "Wait till the end — you won't expect this", "type": "loop", "niche": "Entertainment", "trending_score": 92, "badge": "fast_growing"},
    {"idea": "I tried this for 7 days — here's what changed", "type": "experiment", "niche": "Health", "trending_score": 91, "badge": "trending"},
    {"idea": "Nobody talks about this productivity secret", "type": "controversy", "niche": "Tech", "trending_score": 90, "badge": "fast_growing"},
    {"idea": "This is why you're stuck and how to fix it", "type": "advice", "niche": "Finance", "trending_score": 89},
    {"idea": "What happens next will shock you", "type": "shock", "niche": "Lifestyle", "trending_score": 88, "badge": "trending"},
    {"idea": "I tested every viral trend so you don't have to", "type": "test", "niche": "Entertainment", "trending_score": 87},
    {"idea": "This one trick blew up my reach overnight", "type": "growth", "niche": "Business", "trending_score": 86, "badge": "fast_growing"},
    {"idea": "Stop scrolling — this will save you hours", "type": "hook", "niche": "Tech", "trending_score": 95, "badge": "trending"},
]


# ==================== DAILY FEED ====================
@router.get("/daily-feed")
async def get_daily_feed(niche: Optional[str] = None):
    from routes.daily_viral_ideas import get_daily_ideas, NICHES
    ideas = []
    try:
        ideas = await get_daily_ideas(niche=niche, count=12)
        logger.info(f"[FEED] Fetched {len(ideas)} ideas (niche={niche or 'all'})")
    except Exception as e:
        logger.error(f"[FEED] get_daily_ideas failed: {e}")

    # HARD FALLBACK — NEVER return empty
    if not ideas or len(ideas) < 3:
        logger.warning(f"[FEED] Insufficient ideas ({len(ideas)}), injecting fallback")
        if niche:
            ideas = [i for i in FALLBACK_IDEAS if i["niche"] == niche]
        if not ideas:
            ideas = list(FALLBACK_IDEAS)

    total_packs = await db.viral_jobs.count_documents({})
    return {
        "success": True,
        "ideas": ideas[:12],
        "niches": NICHES,
        "date": datetime.now(timezone.utc).date().isoformat(),
        "total_packs_generated": max(total_packs, 500),
    }


# ==================== GENERATE BUNDLE (SOFT PAYWALL) ====================
@router.post("/generate-bundle", response_model=GenerateBundleResponse)
async def generate_bundle(req: GenerateBundleRequest, user: dict = Depends(get_current_user)):
    user_id = str(user["id"])
    
    # Safety pipeline — sanitize user inputs
    from services.rewrite_engine import check_and_rewrite
    safety = await check_and_rewrite(user_id, "viral_ideas", req, ["idea", "niche"])
    if safety.blocked:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=safety.block_reason)
    
    credit_cost = 5

    # Count user's previous generations
    gen_count = await db.viral_jobs.count_documents({"user_id": user_id})
    is_first_gen = gen_count == 0
    locked = False

    if is_first_gen:
        # First generation is FREE — no credits deducted
        logger.info(f"[PAYWALL] First free generation for user {user_id}")
    else:
        # Subsequent: check credits
        if user.get("credits", 0) >= credit_cost:
            await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credit_cost}})
            await db.credit_transactions.insert_one({
                "user_id": user_id,
                "amount": -credit_cost,
                "type": "viral_bundle",
                "description": f"Viral content pack: {req.idea[:60]}",
                "created_at": datetime.now(timezone.utc),
            })
        else:
            # No credits — generate anyway but LOCK the output
            locked = True
            logger.info(f"[PAYWALL] Locked generation for user {user_id} (no credits)")

    result = await jobs.create_job(db, user_id, req.idea, req.niche, locked=locked)
    job_id = result["job_id"]

    await dispatch_task(Q_ORCHESTRATOR, {
        "job_id": job_id,
        "idea": req.idea,
        "niche": req.niche,
    })

    # Track metric
    await _track_metric("generation", user_id, {"job_id": job_id, "is_first": is_first_gen, "locked": locked, "niche": req.niche})

    share_url = f"/viral/{job_id}"

    return GenerateBundleResponse(
        job_id=job_id, status="pending",
        message="Your first free pack!" if is_first_gen else "Your content pack is being created!",
        locked=locked, share_url=share_url,
    )


# ==================== JOB STATUS ====================
@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    tasks = await jobs.get_tasks_for_job(db, job_id)

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "locked": job.get("locked", False),
        "share_url": f"/viral/{job_id}",
        "tasks": [
            {
                "task_id": t["task_id"],
                "task_type": t["task_type"],
                "status": t["status"],
                "fallback_used": t.get("fallback_used", False),
                "attempts": t.get("attempts", 0),
            }
            for t in tasks
        ],
        "created_at": job["created_at"].isoformat() if job.get("created_at") else None,
        "completed_at": job["completed_at"].isoformat() if job.get("completed_at") else None,
    }


# ==================== JOB ASSETS ====================
@router.get("/jobs/{job_id}/assets")
async def get_job_assets(job_id: str, user: dict = Depends(get_current_user)):
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    assets = await jobs.get_assets(db, job_id)
    locked = job.get("locked", False)

    from routes.media_proxy import generate_secure_url
    formatted = []
    for a in assets:
        fa = _format_asset(a, locked)
        raw_url = fa.get("file_url")
        if raw_url and _is_protected_asset_url(raw_url):
            normalized = _normalize_asset_url(raw_url)
            fa["secure_url"] = generate_secure_url(
                file_url=normalized,
                asset_id=fa["asset_id"],
                asset_type=fa["asset_type"],
                user_id=str(user["id"]),
                purpose="preview",
            )
        fa.pop("file_url", None)
        formatted.append(fa)

    return {
        "job_id": job_id,
        "status": job["status"],
        "locked": locked,
        "assets": formatted,
    }


def _is_protected_asset_url(url: str) -> bool:
    """Check if a URL points to a generated viral asset, regardless of prefix format."""
    return (
        url.startswith("/api/static/generated/viral_")
        or url.startswith("/static/generated/viral_")
    )


def _normalize_asset_url(url: str) -> str:
    """Normalize asset URLs to consistent /api/static/... format for the media proxy."""
    if url.startswith("/static/generated/"):
        return "/api" + url
    return url


def _format_asset(a: dict, locked: bool) -> dict:
    base = {
        "asset_id": a["asset_id"],
        "asset_type": a["asset_type"],
        "mime_type": a.get("mime_type", "text/plain"),
        "created_at": a["created_at"].isoformat() if a.get("created_at") else None,
    }
    if locked:
        # Teaser mode: show partial content only
        if a.get("content"):
            lines = a["content"].split("\n")
            base["content"] = "\n".join(lines[:2]) + "\n\n[Unlock to see full content]"
            base["is_truncated"] = True
        if a.get("file_url"):
            base["file_url"] = a["file_url"]  # Image still visible but watermarked via frontend
            base["is_locked"] = True
    else:
        base["content"] = a.get("content")
        base["file_url"] = a.get("file_url")
    return base


# ==================== UNLOCK PACK ====================
@router.post("/jobs/{job_id}/unlock")
async def unlock_pack(job_id: str, user: dict = Depends(get_current_user)):
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    if not job.get("locked", False):
        return {"success": True, "message": "Pack is already unlocked"}

    credit_cost = 5
    if user.get("credits", 0) < credit_cost:
        raise HTTPException(status_code=402, detail="Insufficient credits. 5 credits required to unlock.")

    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credit_cost}})
    await db.credit_transactions.insert_one({
        "user_id": str(user["id"]),
        "amount": -credit_cost,
        "type": "viral_unlock",
        "description": f"Unlocked viral pack: {job['idea'][:60]}",
        "created_at": datetime.now(timezone.utc),
    })
    await db.viral_jobs.update_one({"job_id": job_id}, {"$set": {"locked": False}})

    await _track_metric("free_to_paid", str(user["id"]), {"job_id": job_id})
    return {"success": True, "message": "Pack unlocked!"}


# ==================== PUBLIC SHARE TEASER (NO AUTH) ====================
@router.get("/share/{job_id}")
async def get_share_teaser(job_id: str, ref: Optional[str] = None):
    """Public endpoint — teaser data for the viral share page."""
    job = await db.viral_jobs.find_one({"job_id": job_id}, {"_id": 0, "_best_hook": 0, "_phase2_dispatched": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Pack not found")

    # Get hook and partial script
    hook_asset = await db.viral_assets.find_one({"job_id": job_id, "asset_type": "hooks"}, {"_id": 0})
    script_asset = await db.viral_assets.find_one({"job_id": job_id, "asset_type": "script"}, {"_id": 0})
    thumb_asset = await db.viral_assets.find_one({"job_id": job_id, "asset_type": "thumbnail"}, {"_id": 0})
    caption_asset = await db.viral_assets.find_one({"job_id": job_id, "asset_type": "captions"}, {"_id": 0})

    # Extract teaser content
    top_hook = ""
    if hook_asset and hook_asset.get("content"):
        lines = hook_asset["content"].strip().split("\n")
        top_hook = lines[0] if lines else ""

    script_teaser = ""
    if script_asset and script_asset.get("content"):
        lines = script_asset["content"].strip().split("\n")
        script_teaser = "\n".join(lines[:3])

    caption_teaser = ""
    if caption_asset and caption_asset.get("content"):
        lines = caption_asset["content"].strip().split("\n")
        caption_teaser = lines[0] if lines else ""

    thumbnail_url = None
    if thumb_asset and thumb_asset.get("file_url"):
        # Generate a public preview token (no user binding, watermarked)
        from routes.media_proxy import generate_secure_url
        thumbnail_url = generate_secure_url(
            file_url=thumb_asset["file_url"],
            asset_id=thumb_asset.get("asset_id", "public"),
            asset_type="thumbnail",
            user_id="public_share",
            purpose="preview",
        )

    # Social proof
    total_packs = await db.viral_jobs.count_documents({"status": {"$in": ["completed", "completed_with_fallbacks"]}})

    # Track share page view
    if ref:
        await _track_metric("share_view", ref, {"job_id": job_id, "referrer": ref})

    return {
        "job_id": job_id,
        "niche": job.get("niche", ""),
        "idea": job.get("idea", ""),
        "top_hook": top_hook,
        "script_teaser": script_teaser,
        "caption_teaser": caption_teaser,
        "thumbnail_url": thumbnail_url,
        "total_packs_generated": max(total_packs, 500),  # floor for social proof
        "created_at": job["created_at"].isoformat() if job.get("created_at") else None,
    }


# ==================== SHARE TRACKING ====================
@router.post("/share/{job_id}/track")
async def track_share(job_id: str, request: Request):
    """Public endpoint — tracks when user shares to a platform."""
    body = await request.json()
    platform = body.get("platform", "unknown")
    user_id = body.get("user_id", "anonymous")

    await _track_metric("share_event", user_id, {
        "job_id": job_id,
        "platform": platform,
    })
    return {"success": True}


# ==================== USER'S JOBS ====================
@router.get("/my-jobs")
async def get_my_jobs(user: dict = Depends(get_current_user)):
    user_jobs = await jobs.get_user_jobs(db, str(user["id"]), limit=20)
    return {
        "jobs": [
            {
                "job_id": j["job_id"],
                "idea": j["idea"],
                "niche": j["niche"],
                "status": j["status"],
                "progress": j["progress"],
                "locked": j.get("locked", False),
                "share_url": f"/viral/{j['job_id']}",
                "created_at": j["created_at"].isoformat() if j.get("created_at") else None,
                "completed_at": j["completed_at"].isoformat() if j.get("completed_at") else None,
            }
            for j in user_jobs
        ],
    }


# ==================== FEEDBACK ====================
@router.post("/jobs/{job_id}/feedback")
async def submit_feedback(job_id: str, req: FeedbackRequest, user: dict = Depends(get_current_user)):
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    if req.signal not in VALID_SIGNALS:
        raise HTTPException(status_code=400, detail=f"Invalid signal. Valid: {', '.join(VALID_SIGNALS)}")

    await db.viral_feedback.insert_one({
        "feedback_id": str(uuid.uuid4()),
        "job_id": job_id,
        "user_id": str(user["id"]),
        "signal": req.signal,
        "asset_type": req.asset_type,
        "comment": req.comment,
        "idea": job.get("idea"),
        "niche": job.get("niche"),
        "created_at": datetime.now(timezone.utc),
    })
    return {"success": True, "message": "Feedback recorded"}


# ==================== REPAIR ====================
@router.post("/jobs/{job_id}/repair")
async def repair_job(job_id: str, user: dict = Depends(get_current_user)):
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    await dispatch_task(Q_REPAIR, {"job_id": job_id})
    return {"success": True, "message": "Repair initiated. Check status for updates."}


# ==================== FEEDBACK SUMMARY ====================
@router.get("/feedback/summary")
async def get_feedback_summary(niche: Optional[str] = None, user: dict = Depends(get_current_user)):
    match = {}
    if niche:
        match["niche"] = niche
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"signal": "$signal", "asset_type": "$asset_type", "niche": "$niche"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"count": -1}},
        {"$limit": 50},
    ]
    results = await db.viral_feedback.aggregate(pipeline).to_list(50)
    return {
        "summary": [
            {"signal": r["_id"]["signal"], "asset_type": r["_id"].get("asset_type"),
             "niche": r["_id"].get("niche"), "count": r["count"]}
            for r in results
        ],
    }


# ==================== GROWTH METRICS ====================
@router.get("/metrics/growth")
async def get_growth_metrics(user: dict = Depends(get_current_user)):
    """Internal metrics query — for tracking growth funnel."""
    pipeline = [
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    results = await db.viral_growth_metrics.aggregate(pipeline).to_list(20)
    metrics = {r["_id"]: r["count"] for r in results}
    return {
        "generations": metrics.get("generation", 0),
        "shares": metrics.get("share_event", 0),
        "share_views": metrics.get("share_view", 0),
        "share_to_signup": metrics.get("share_to_signup", 0),
        "free_to_paid": metrics.get("free_to_paid", 0),
        "unlocks": metrics.get("free_to_paid", 0),
        "pack_completions": await db.viral_jobs.count_documents({"status": {"$in": ["completed", "completed_with_fallbacks"]}}),
    }


# ==================== REFERRAL SIGNUP TRACKING ====================
@router.post("/track-referral")
async def track_referral(request: Request):
    """Public — called after signup when ref param exists."""
    body = await request.json()
    ref_job_id = body.get("ref_job_id")
    new_user_id = body.get("new_user_id")
    if ref_job_id and new_user_id:
        await _track_metric("share_to_signup", new_user_id, {"ref_job_id": ref_job_id})
    return {"success": True}


# ==================== INTERNAL METRIC HELPER ====================
async def _track_metric(event_type: str, user_id: str, data: dict):
    await db.viral_growth_metrics.insert_one({
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "user_id": user_id,
        "data": data,
        "timestamp": datetime.now(timezone.utc),
    })
