"""
Brand Kit Generator — upgraded from Brand Story Builder.
Parallel AI generation, progressive results, PDF/ZIP packaging.
Pricing: Fast=10, Pro=25, Premium=50 (reserved)
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import time
import os
import logging
from datetime import datetime, timezone

from shared import db, get_current_user, get_admin_user
from services.brand_kit.orchestrator import BrandKitOrchestrator
from services.brand_kit.prompts import MODE_ARTIFACTS

logger = logging.getLogger("creatorstudio.brand_kit")

router = APIRouter(prefix="/brand-story-builder", tags=["Brand Kit Generator"])

# ==================== COPYRIGHT PROTECTION ====================
BLOCKED_KEYWORDS = [
    "marvel", "disney", "pixar", "harry potter", "pokemon", "naruto", "spiderman",
    "batman", "superman", "avengers", "frozen", "mickey", "star wars", "lord of the rings",
    "netflix", "amazon", "google", "apple", "microsoft", "facebook", "instagram",
    "tiktok", "youtube", "twitter", "coca cola", "pepsi", "mcdonalds", "nike", "adidas",
    "gucci", "louis vuitton", "rolex", "ferrari", "lamborghini", "tesla", "elon musk",
    "jeff bezos", "mark zuckerberg", "bill gates", "taylor swift", "beyonce", "drake"
]

INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Education", "E-commerce",
    "Real Estate", "Food & Beverage", "Fashion", "Consulting", "Marketing",
    "Fitness", "Travel", "Entertainment", "Manufacturing", "Non-profit",
    "SaaS", "AI/ML", "Retail", "Media", "Automotive", "Agriculture",
    "Legal", "Architecture", "Gaming", "Sustainability"
]

TONES = ["professional", "bold", "luxury", "friendly", "emotional", "gen-z", "startup", "premium"]

PERSONALITIES = ["innovative", "trustworthy", "playful", "sophisticated", "disruptive", "warm", "authoritative", "minimalist"]

CREDIT_COSTS = {"fast": 10, "pro": 25, "premium": 50}


def check_copyright(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in BLOCKED_KEYWORDS)


# ==================== MODELS ====================
class BrandKitRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=100)
    mission: str = Field(default="", max_length=500)
    founder_story: str = Field(default="", max_length=500)
    industry: str = Field(default="Technology")
    tone: str = Field(default="professional")
    audience: str = Field(default="", max_length=300)
    personality: str = Field(default="", max_length=200)
    competitors: str = Field(default="", max_length=300)
    market: str = Field(default="Global", max_length=100)
    problem_solved: str = Field(default="", max_length=300)
    mode: str = Field(default="pro")


# ==================== ENDPOINTS ====================
@router.get("/config")
async def get_config():
    return {
        "industries": INDUSTRIES,
        "tones": TONES,
        "personalities": PERSONALITIES,
        "modes": {
            "fast": {"credits": 10, "artifacts": MODE_ARTIFACTS["fast"], "label": "Fast", "desc": "Text essentials in ~5 seconds"},
            "pro": {"credits": 25, "artifacts": MODE_ARTIFACTS["pro"], "label": "Pro", "desc": "Full brand kit with visuals"},
        },
        "credit_costs": CREDIT_COSTS,
    }


@router.post("/generate")
async def generate_brand_kit(request: BrandKitRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    # Fix 3: Request logging (MANDATORY)
    logger.info(f"[BRAND_KIT] Generate request from user={user.get('id')} role={user.get('role')} payload={request.dict()}")

    # Copyright check
    all_text = f"{request.business_name} {request.mission} {request.founder_story} {request.competitors}"
    if check_copyright(all_text):
        logger.warning(f"[BRAND_KIT] Copyright blocked for user={user.get('id')} text={all_text[:100]}")
        raise HTTPException(status_code=400, detail="Input contains blocked content. Please avoid copyrighted or trademarked terms.")

    # Fix 2: Mode normalization (CRITICAL)
    mode = request.mode.lower().strip() if request.mode else "pro"
    if mode not in ("fast", "pro"):
        logger.warning(f"[BRAND_KIT] Invalid mode '{request.mode}' from user={user.get('id')}, defaulting to 'pro'")
        mode = "pro"

    cost = CREDIT_COSTS.get(mode, 25)

    # Fix 7: Credits guard — admin bypass
    is_admin = user.get("role", "").upper() in ("ADMIN", "SUPERADMIN")
    if not is_admin and user.get("credits", 0) < cost:
        logger.warning(f"[BRAND_KIT] Insufficient credits: user={user.get('id')} has={user.get('credits')} needs={cost}")
        raise HTTPException(status_code=402, detail=f"Insufficient credits. You have {user.get('credits', 0)} credits but need {cost} for {mode} mode.")

    # Deduct credits (skip for admin with unlimited)
    if not is_admin:
        await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -cost}})

    brief = {
        "business_name": request.business_name,
        "mission": request.mission or "",
        "founder_story": request.founder_story or "",
        "industry": request.industry or "Technology",
        "tone": request.tone or "professional",
        "audience": request.audience or "",
        "personality": request.personality or "",
        "competitors": request.competitors or "",
        "market": request.market or "Global",
        "problem_solved": request.problem_solved or "",
    }

    llm_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not llm_key:
        logger.error("[BRAND_KIT] EMERGENT_LLM_KEY not set!")

    orchestrator = BrandKitOrchestrator(db, llm_key)

    try:
        job_id = await orchestrator.create_job(user["id"], brief, mode)
        logger.info(f"[BRAND_KIT] Job created: {job_id} mode={mode} user={user.get('id')}")
    except Exception as e:
        logger.error(f"[BRAND_KIT] Job creation failed: {e}", exc_info=True)
        # Refund credits if not admin
        if not is_admin:
            await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": cost}})
        # Fix 4: Return REAL error (not generic)
        raise HTTPException(status_code=500, detail=f"Job creation failed: {str(e)}")

    # Run generation in background
    background_tasks.add_task(orchestrator.run_generation, job_id)

    return {
        "success": True,
        "jobId": job_id,
        "mode": mode,
        "credits_charged": cost if not is_admin else 0,
        "message": f"Building your brand kit ({mode} mode)...",
    }


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    job = await db.brand_kit_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Build artifact summary (without full data for polling)
    artifact_summary = {}
    for art_type, art in job.get("artifacts", {}).items():
        artifact_summary[art_type] = {
            "status": art.get("status", "QUEUED"),
            "latency_ms": art.get("latency_ms"),
        }

    return {
        "jobId": job["id"],
        "status": job.get("status", "CREATED"),
        "mode": job.get("mode"),
        "progress": job.get("progress", 0),
        "current_stage": job.get("current_stage", "CREATED"),
        "total_artifacts": job.get("total_artifacts", 0),
        "completed_artifacts": job.get("completed_artifacts", 0),
        "artifacts": artifact_summary,
        "brief": job.get("brief", {}),
    }


@router.get("/job/{job_id}/result")
async def get_job_result(job_id: str, user: dict = Depends(get_current_user)):
    job = await db.brand_kit_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Return full artifact data
    outputs = {}
    for art_type, art in job.get("artifacts", {}).items():
        outputs[art_type] = {
            "status": art.get("status", "QUEUED"),
            "data": art.get("data"),
            "latency_ms": art.get("latency_ms"),
        }

    return {
        "jobId": job["id"],
        "status": job.get("status"),
        "mode": job.get("mode"),
        "brief": job.get("brief", {}),
        "outputs": outputs,
        "completed_at": job.get("completed_at"),
    }


@router.get("/job/{job_id}/pdf")
async def download_pdf(job_id: str, user: dict = Depends(get_current_user)):
    from services.brand_kit.packaging import generate_brand_kit_pdf
    from fastapi.responses import Response

    job = await db.brand_kit_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") not in ("READY", "PARTIAL_READY"):
        raise HTTPException(status_code=400, detail="Brand kit not ready for download")

    try:
        pdf_bytes = generate_brand_kit_pdf(job)
        biz = job.get("brief", {}).get("business_name", "brand").replace(" ", "_")
        # Track download event
        await db.production_events.insert_one({
            "event": "download", "feature": "brand_kit", "format": "pdf",
            "job_id": job_id, "user_id": user["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{biz}_brand_kit.pdf"'}
        )
    except Exception as e:
        logger.error(f"[BRAND_KIT] PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")


@router.get("/job/{job_id}/zip")
async def download_zip(job_id: str, user: dict = Depends(get_current_user)):
    from services.brand_kit.packaging import generate_brand_kit_zip
    from fastapi.responses import Response

    job = await db.brand_kit_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") not in ("READY", "PARTIAL_READY"):
        raise HTTPException(status_code=400, detail="Brand kit not ready for download")

    try:
        zip_bytes = generate_brand_kit_zip(job)
        biz = job.get("brief", {}).get("business_name", "brand").replace(" ", "_")
        # Track download event
        await db.production_events.insert_one({
            "event": "download", "feature": "brand_kit", "format": "zip",
            "job_id": job_id, "user_id": user["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{biz}_brand_kit.zip"'}
        )
    except Exception as e:
        logger.error(f"[BRAND_KIT] ZIP generation failed: {e}")
        raise HTTPException(status_code=500, detail="ZIP generation failed")


# ==================== ADMIN ENDPOINTS ====================
@router.get("/admin/analytics")
async def get_brand_kit_analytics(admin: dict = Depends(get_admin_user)):
    total_jobs = await db.brand_kit_jobs.count_documents({})
    completed = await db.brand_kit_jobs.count_documents({"status": {"$in": ["READY", "PARTIAL_READY"]}})
    failed = await db.brand_kit_jobs.count_documents({"status": "FAILED"})

    return {
        "total_jobs": total_jobs,
        "completed": completed,
        "failed": failed,
        "success_rate": round(completed / max(total_jobs, 1) * 100, 1),
    }
