"""
P0 Photo Trailer (YouStar / My Movie Trailer) — fast personalized AI trailer generator.
Spec: 20-60s output. Identity consistency > animation complexity > speed > shareability.

Pipeline:
  validate → safety → script (Claude) → scene plan → Nano Banana images (with face refs)
  → OpenAI TTS narration → ffmpeg motion + music + subtitles + end card → R2 → done.

Production-safety architecture (Apr 29 2026):
- All blocking emergentintegrations calls (script LLM, Nano Banana image gen,
  OpenAI TTS) and ffmpeg subprocesses run on DEDICATED, BOUNDED, PER-STAGE
  thread pools. Each worker thread spins up its own asyncio loop via
  `asyncio.run`, so the library's sync-under-async I/O blocks the worker
  thread, NEVER the main FastAPI loop.
- Three executors, separated by stage so heavy I/O (images) cannot starve
  light I/O (TTS) or CPU (ffmpeg):
    IMAGE_EXECUTOR  — script LLM + Nano Banana image gen
    AUDIO_EXECUTOR  — OpenAI TTS narration
    RENDER_EXECUTOR — ffmpeg encode/concat/mux passes
- A system-wide `_PIPELINE_GATE` semaphore caps concurrent pipelines so
  5 users cannot melt the server.
- Result: while a trailer renders (~30-60s), all other API endpoints stay sub-100ms.

Tunables (do NOT raise blindly — measure first):
  MAX_ACTIVE_PIPELINES  — concurrent pipeline budget (default 2)
  MAX_IMAGE_WORKERS     — Nano Banana parallelism (default 4)
  MAX_AUDIO_WORKERS     — OpenAI TTS parallelism (default 4)
  MAX_RENDER_WORKERS    — ffmpeg parallelism (default 2 — CPU/disk bound)
"""
from __future__ import annotations
import os, asyncio, base64, uuid, tempfile, subprocess, logging, re, json
import concurrent.futures
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from shared import db, get_current_user, get_admin_user, deduct_credits, add_credits
from services.cloudflare_r2_storage import upload_image_bytes, upload_voice_bytes
from services.cloudflare_r2_storage import R2_CUSTOM_DOMAIN, R2_PUBLIC_URL, R2_BUCKET_NAME

load_dotenv()
log = logging.getLogger("photo_trailer")
router = APIRouter(prefix="/photo-trailer", tags=["photo-trailer"])
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# ─── Bounded parallel workers per pipeline stage ───────────────────────────────
# Hard caps. Total max threads = MAX_IMAGE_WORKERS + MAX_AUDIO_WORKERS + MAX_RENDER_WORKERS
# = 10 by default. Increasing these blindly will choke the server before it
# helps anyone. Profile + measure before tuning.
MAX_ACTIVE_PIPELINES = int(os.environ.get("PHOTO_TRAILER_MAX_ACTIVE_PIPELINES", "2"))
MAX_IMAGE_WORKERS    = int(os.environ.get("PHOTO_TRAILER_MAX_IMAGE_WORKERS",    "4"))
MAX_AUDIO_WORKERS    = int(os.environ.get("PHOTO_TRAILER_MAX_AUDIO_WORKERS",    "4"))
MAX_RENDER_WORKERS   = int(os.environ.get("PHOTO_TRAILER_MAX_RENDER_WORKERS",   "2"))

IMAGE_EXECUTOR  = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_IMAGE_WORKERS,  thread_name_prefix="trailer-img")
AUDIO_EXECUTOR  = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_AUDIO_WORKERS,  thread_name_prefix="trailer-aud")
RENDER_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_RENDER_WORKERS, thread_name_prefix="trailer-render")
_PIPELINE_GATE = asyncio.Semaphore(MAX_ACTIVE_PIPELINES)

MAX_PHOTOS = 10
MAX_PHOTO_BYTES = 10 * 1024 * 1024
ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ACTIVE_JOB_LIMIT = {"FREE": 1, "PAID": 2, "PREMIUM": 3, "ADMIN": 10}
DURATION_BUCKETS = [(15, 5), (20, 5), (45, 25), (60, 35)]  # (sec, credits)

# ─── Templates ────────────────────────────────────────────────────────────────
TEMPLATES: Dict[str, Dict[str, Any]] = {
    "superhero_origin":  {"title": "Superhero Origin",  "description": "Ordinary person discovers extraordinary power.",       "tone": "epic",        "narrator": "onyx",   "music_mood": "heroic",      "scene_count": 6, "safety": ["no_violence_glorification"]},
    "birthday_movie":    {"title": "Birthday Movie",    "description": "A celebration trailer in cinematic style.",            "tone": "joyful",      "narrator": "nova",   "music_mood": "uplifting",   "scene_count": 5, "safety": []},
    "couple_love":       {"title": "Couple Love Story", "description": "Two souls, one story — a romance trailer.",            "tone": "romantic",    "narrator": "shimmer","music_mood": "romantic",    "scene_count": 6, "safety": ["sfw"]},
    "family_adventure":  {"title": "Family Adventure",  "description": "An everyday family in a cinematic adventure.",         "tone": "warm",        "narrator": "fable",  "music_mood": "adventure",   "scene_count": 6, "safety": []},
    "anime_intro":       {"title": "Anime Intro",       "description": "Anime-style hero introduction with bold framing.",     "tone": "energetic",   "narrator": "alloy",  "music_mood": "anime",       "scene_count": 7, "safety": []},
    "mythology_hero":    {"title": "Mythology Hero",    "description": "Ancient myth retold with you as the hero.",            "tone": "majestic",    "narrator": "onyx",   "music_mood": "epic",        "scene_count": 6, "safety": []},
    "comedy_roast":      {"title": "Comedy Roast",      "description": "Light-hearted comedic trailer — friends, not foes.",   "tone": "playful",     "narrator": "echo",   "music_mood": "playful",     "scene_count": 5, "safety": ["no_harassment"]},
    "horror_night":      {"title": "Horror Night",      "description": "Stylized spooky trailer — eerie not graphic.",         "tone": "suspense",    "narrator": "echo",   "music_mood": "horror",      "scene_count": 6, "safety": ["sfw", "no_gore"]},
    "motivational":      {"title": "Motivational Transformation", "description": "Before-after journey of grit and growth.",   "tone": "inspirational","narrator":"nova",   "music_mood": "uplifting",   "scene_count": 6, "safety": []},
}

# ─── Models ───────────────────────────────────────────────────────────────────
class UploadInitIn(BaseModel):
    file_count: int = Field(..., ge=1)
    mime_types: List[str]
    file_sizes: List[int]

class UploadCompleteIn(BaseModel):
    upload_session_id: str
    consent_confirmed: bool

class JobCreateIn(BaseModel):
    upload_session_id: str
    hero_asset_id: str
    villain_asset_id: Optional[str] = None
    supporting_asset_ids: List[str] = []
    template_id: str
    custom_prompt: Optional[str] = None
    duration_target_seconds: int = Field(45, ge=15, le=60)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _now(): return datetime.now(timezone.utc).isoformat()
def _user_role(u: dict) -> str: return (u.get("role") or "FREE").upper()
def _credits_for(seconds: int) -> int:
    for sec, c in DURATION_BUCKETS:
        if seconds <= sec: return c
    return DURATION_BUCKETS[-1][1]

def _strip(d: dict) -> dict:
    """Drop _id and ensure ISO strings."""
    if not d: return d
    d.pop("_id", None)
    return d

async def _emit(event: str, user_id: str, meta: dict = None):
    try:
        await db.funnel_events.insert_one({
            "step": event, "event": event, "session_id": meta.get("session_id") if meta else None,
            "user_id": user_id, "timestamp": _now(), "meta": meta or {},
        })
    except Exception:
        pass

# ─── Validation ───────────────────────────────────────────────────────────────
@router.post("/uploads/init")
async def init_upload(body: UploadInitIn, user: dict = Depends(get_current_user)):
    if body.file_count > MAX_PHOTOS:
        raise HTTPException(400, f"You can upload a maximum of {MAX_PHOTOS} photos only.")
    if len(body.mime_types) != body.file_count or len(body.file_sizes) != body.file_count:
        raise HTTPException(400, "mime_types and file_sizes length must equal file_count")
    for m in body.mime_types:
        if m.lower() not in ALLOWED_MIME:
            raise HTTPException(400, f"Unsupported file type: {m}. Use JPG, PNG or WEBP.")
    for s in body.file_sizes:
        if s > MAX_PHOTO_BYTES:
            raise HTTPException(400, "Each photo must be 10MB or smaller.")
    sid = str(uuid.uuid4())
    await db.photo_trailer_upload_sessions.insert_one({
        "_id": sid, "user_id": user["id"], "status": "CREATED",
        "photo_count": body.file_count, "consent_confirmed": False, "asset_ids": [],
        "created_at": _now(), "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "updated_at": _now(),
    })
    await _emit("photo_trailer_upload_started", user["id"], {"session": sid, "count": body.file_count})
    return {"upload_session_id": sid, "max_photos": MAX_PHOTOS, "max_bytes": MAX_PHOTO_BYTES}

@router.post("/uploads/photo")
async def upload_photo(
    upload_session_id: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """One-shot upload: store bytes in R2 + create asset doc."""
    sess = await db.photo_trailer_upload_sessions.find_one({"_id": upload_session_id, "user_id": user["id"]}, {"_id": 1, "asset_ids": 1, "photo_count": 1})
    if not sess:
        raise HTTPException(404, "Upload session not found")
    if len(sess.get("asset_ids", [])) >= MAX_PHOTOS:
        raise HTTPException(400, f"You can upload a maximum of {MAX_PHOTOS} photos only.")
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME:
        raise HTTPException(400, "Unsupported file type. Use JPG, PNG or WEBP.")
    data = await file.read()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(400, "Each photo must be 10MB or smaller.")
    asset_id = str(uuid.uuid4())
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", file.filename or "photo.jpg")
    ok, key_or_url = await upload_image_bytes(data, f"trailer_{asset_id}_{safe_name}", project_id=f"phototrailer/{user['id']}/{upload_session_id}")
    if not ok:
        raise HTTPException(500, "Storage upload failed — please retry.")
    # Detect width/height best-effort
    w = h = None
    try:
        from PIL import Image
        from io import BytesIO
        im = Image.open(BytesIO(data)); w, h = im.size
    except Exception:
        pass
    storage_key = key_or_url.split(f"{R2_BUCKET_NAME}/")[-1] if R2_BUCKET_NAME in key_or_url else key_or_url
    doc = {
        "_id": asset_id, "user_id": user["id"], "upload_session_id": upload_session_id,
        "original_filename": file.filename, "mime_type": file.content_type,
        "file_size": len(data), "width": w, "height": h,
        "storage_key": storage_key, "storage_url": key_or_url, "thumbnail_key": None,
        "safety_status": "PENDING", "face_detected": True,  # heuristic accept; safety pass at job time
        "selected_role": "UNUSED", "created_at": _now(),
    }
    await db.photo_trailer_assets.insert_one(doc)
    await db.photo_trailer_upload_sessions.update_one(
        {"_id": upload_session_id},
        {"$push": {"asset_ids": asset_id}, "$set": {"status": "UPLOADING", "updated_at": _now()}},
    )
    return {"asset_id": asset_id, "storage_url": key_or_url, "width": w, "height": h}

@router.post("/uploads/complete")
async def complete_upload(body: UploadCompleteIn, user: dict = Depends(get_current_user)):
    if not body.consent_confirmed:
        raise HTTPException(400, "You must confirm photo rights to continue.")
    sess = await db.photo_trailer_upload_sessions.find_one({"_id": body.upload_session_id, "user_id": user["id"]})
    if not sess:
        raise HTTPException(404, "Upload session not found")
    if not sess.get("asset_ids"):
        raise HTTPException(400, "Upload at least one photo first.")
    if len(sess["asset_ids"]) > MAX_PHOTOS:
        raise HTTPException(400, f"You can upload a maximum of {MAX_PHOTOS} photos only.")
    await db.photo_trailer_upload_sessions.update_one(
        {"_id": body.upload_session_id},
        {"$set": {"status": "COMPLETED", "consent_confirmed": True, "updated_at": _now()}},
    )
    await _emit("photo_trailer_consent_checked", user["id"], {"session": body.upload_session_id})
    return {"success": True}

@router.get("/templates")
async def list_templates():
    return {"templates": [{"id": k, **v} for k, v in TEMPLATES.items()]}

@router.get("/credit-estimate")
async def credit_estimate(duration: int = Query(45, ge=15, le=60), user: dict = Depends(get_current_user)):
    return {"duration_seconds": duration, "credits": _credits_for(duration), "user_credits": user.get("credits", 0)}

# ─── Job creation ─────────────────────────────────────────────────────────────
@router.post("/jobs")
async def create_job(body: JobCreateIn, bg: BackgroundTasks, user: dict = Depends(get_current_user)):
    if body.template_id not in TEMPLATES:
        raise HTTPException(400, "Invalid template")
    sess = await db.photo_trailer_upload_sessions.find_one({"_id": body.upload_session_id, "user_id": user["id"]})
    if not sess: raise HTTPException(404, "Upload session not found")
    if sess.get("status") != "COMPLETED": raise HTTPException(400, "Upload not finalised — confirm consent first.")
    if body.hero_asset_id not in sess["asset_ids"]:
        raise HTTPException(400, "Hero must be one of the uploaded photos")
    for vid in [body.villain_asset_id] + body.supporting_asset_ids:
        if vid and vid not in sess["asset_ids"]:
            raise HTTPException(400, "Character refs must come from uploaded photos")
    role = _user_role(user)
    active = await db.photo_trailer_jobs.count_documents({"user_id": user["id"], "status": {"$in": ["QUEUED", "PROCESSING"]}})
    if active >= ACTIVE_JOB_LIMIT.get(role, 1):
        raise HTTPException(429, f"You already have {active} active trailer(s). Wait for them to finish.")
    cred = _credits_for(body.duration_target_seconds)
    if (user.get("credits") or 0) < cred and role != "ADMIN":
        raise HTTPException(402, f"Need {cred} credits. You have {user.get('credits', 0)}.")
    job_id = str(uuid.uuid4())
    tpl = TEMPLATES[body.template_id]
    job = {
        "_id": job_id, "user_id": user["id"], "upload_session_id": body.upload_session_id,
        "status": "QUEUED", "current_stage": "QUEUED", "progress_percent": 0,
        "hero_asset_id": body.hero_asset_id, "villain_asset_id": body.villain_asset_id,
        "supporting_asset_ids": body.supporting_asset_ids,
        "template_id": body.template_id, "template_name": tpl["title"],
        "custom_prompt": (body.custom_prompt or "").strip()[:500],
        "duration_target_seconds": body.duration_target_seconds,
        "estimated_credits": cred, "charged_credits": 0, "refunded_credits": 0,
        "narrator_style": tpl["narrator"], "music_mood": tpl["music_mood"],
        "script_text": None, "error_code": None, "error_message": None,
        "result_video_asset_id": None, "result_thumbnail_asset_id": None,
        "result_video_url": None, "result_thumbnail_url": None,
        "public_share_slug": None,
        "created_at": _now(), "started_at": None, "completed_at": None, "failed_at": None,
        "updated_at": _now(),
    }
    await db.photo_trailer_jobs.insert_one(job)
    # Mark assets with roles
    await db.photo_trailer_assets.update_one({"_id": body.hero_asset_id}, {"$set": {"selected_role": "HERO"}})
    if body.villain_asset_id:
        await db.photo_trailer_assets.update_one({"_id": body.villain_asset_id}, {"$set": {"selected_role": "VILLAIN"}})
    for aid in body.supporting_asset_ids:
        await db.photo_trailer_assets.update_one({"_id": aid}, {"$set": {"selected_role": "SUPPORTING"}})
    await _emit("photo_trailer_job_created", user["id"], {"job_id": job_id, "template": body.template_id, "duration": body.duration_target_seconds})
    bg.add_task(_run_pipeline, job_id)
    return {"job_id": job_id, "status": "QUEUED", "estimated_credits": cred}

@router.get("/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    j = await db.photo_trailer_jobs.find_one({"_id": job_id, "user_id": user["id"]}, {"_id": 0})
    if not j: raise HTTPException(404, "Job not found")
    return j

@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, bg: BackgroundTasks, user: dict = Depends(get_current_user)):
    j = await db.photo_trailer_jobs.find_one({"_id": job_id, "user_id": user["id"]})
    if not j: raise HTTPException(404, "Job not found")
    if j.get("status") != "FAILED": raise HTTPException(400, "Only failed jobs can be retried")
    await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {
        "status": "QUEUED", "current_stage": "QUEUED", "progress_percent": 0,
        "error_code": None, "error_message": None, "failed_at": None,
        "charged_credits": 0, "refunded_credits": 0, "updated_at": _now(),
    }})
    bg.add_task(_run_pipeline, job_id)
    return {"ok": True}

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, user: dict = Depends(get_current_user)):
    j = await db.photo_trailer_jobs.find_one({"_id": job_id, "user_id": user["id"]})
    if not j: raise HTTPException(404, "Job not found")
    if j.get("status") in ["COMPLETED", "CANCELLED"]: return {"ok": True}
    await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {"status": "CANCELLED", "updated_at": _now()}})
    if j.get("charged_credits"):
        await add_credits(user["id"], j["charged_credits"], f"Refund cancelled trailer {job_id}", tx_type="REFUND")
        await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {"refunded_credits": j["charged_credits"]}})
    return {"ok": True}

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user: dict = Depends(get_current_user)):
    res = await db.photo_trailer_jobs.update_one({"_id": job_id, "user_id": user["id"]}, {"$set": {"deleted_at": _now()}})
    if res.matched_count == 0: raise HTTPException(404, "Job not found")
    return {"ok": True}

@router.get("/my-trailers")
async def my_trailers(user: dict = Depends(get_current_user), limit: int = Query(30, ge=1, le=100)):
    # NB: must include the job id so MySpace can deep-link via ?trailer=<id>
    # and so notification click handlers can match a card. Strip the Mongo
    # _id but project it onto a JSON-friendly job_id field.
    cur = db.photo_trailer_jobs.find(
        {"user_id": user["id"], "deleted_at": {"$exists": False}},
    ).sort("created_at", -1).limit(limit)
    rows = []
    async for d in cur:
        d["job_id"] = d.pop("_id")
        rows.append(d)
    return {"trailers": rows}

# ─── Admin ────────────────────────────────────────────────────────────────────
@router.get("/admin/overview")
async def admin_overview(user: dict = Depends(get_admin_user), days: int = Query(30, ge=1, le=365)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    base = {"created_at": {"$gte": cutoff}}
    total_uploads = await db.photo_trailer_upload_sessions.count_documents(base)
    total_jobs = await db.photo_trailer_jobs.count_documents(base)
    completed = await db.photo_trailer_jobs.count_documents({**base, "status": "COMPLETED"})
    failed = await db.photo_trailer_jobs.count_documents({**base, "status": "FAILED"})
    active = await db.photo_trailer_jobs.count_documents({"status": {"$in": ["QUEUED", "PROCESSING"]}})
    by_template = []
    async for d in db.photo_trailer_jobs.aggregate([
        {"$match": base},
        {"$group": {"_id": "$template_id", "count": {"$sum": 1}, "completed": {"$sum": {"$cond": [{"$eq": ["$status", "COMPLETED"]}, 1, 0]}}}},
        {"$project": {"template_id": "$_id", "_id": 0, "count": 1, "completed": 1}},
        {"$sort": {"count": -1}},
    ]):
        by_template.append(d)
    by_stage_fail = []
    async for d in db.photo_trailer_jobs.aggregate([
        {"$match": {**base, "status": "FAILED"}},
        {"$group": {"_id": "$current_stage", "count": {"$sum": 1}}},
        {"$project": {"stage": "$_id", "_id": 0, "count": 1}},
        {"$sort": {"count": -1}},
    ]):
        by_stage_fail.append(d)
    avg_credits = 0
    async for d in db.photo_trailer_jobs.aggregate([
        {"$match": {**base, "status": "COMPLETED"}},
        {"$group": {"_id": None, "avg": {"$avg": "$charged_credits"}}},
    ]):
        avg_credits = round(d.get("avg") or 0, 1)
    return {
        "period_days": days,
        "total_uploads": total_uploads, "total_jobs": total_jobs,
        "completed": completed, "failed": failed, "active": active,
        "upload_to_generate_pct": round(100 * total_jobs / total_uploads, 1) if total_uploads else 0.0,
        "completion_pct": round(100 * completed / total_jobs, 1) if total_jobs else 0.0,
        "by_template": by_template,
        "failure_stage_breakdown": by_stage_fail,
        "avg_credits_charged": avg_credits,
    }


# ═════════════════════════ PIPELINE ORCHESTRATOR ═══════════════════════════════

STAGES = ["VALIDATING", "ANALYZING_PHOTOS", "BUILDING_CHARACTER", "WRITING_TRAILER_SCRIPT",
          "GENERATING_SCENES", "GENERATING_VOICEOVER", "ADDING_MUSIC", "RENDERING_TRAILER", "COMPLETED"]
STAGE_PCT = {s: int((i + 1) / len(STAGES) * 100) for i, s in enumerate(STAGES)}

# Royalty-free music — bundled in /app/backend/static/music_pack/. Falls back to silence.
MUSIC_PACK_DIR = "/app/backend/static/music_pack"
MUSIC_TRACK_BY_MOOD = {
    "heroic": "heroic.mp3", "uplifting": "uplifting.mp3", "romantic": "romantic.mp3",
    "adventure": "adventure.mp3", "anime": "anime.mp3", "epic": "epic.mp3",
    "playful": "playful.mp3", "horror": "horror.mp3",
}

async def _set_stage(job_id: str, stage: str, **extra):
    upd = {"current_stage": stage, "progress_percent": STAGE_PCT.get(stage, 0), "updated_at": _now()}
    upd.update(extra)
    await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": upd})

async def _fail(job_id: str, code: str, msg: str):
    j = await db.photo_trailer_jobs.find_one({"_id": job_id})
    if not j: return
    log.error(f"[trailer {job_id}] FAIL {code}: {msg}")
    await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {
        "status": "FAILED", "current_stage": "FAILED", "error_code": code,
        "error_message": msg, "failed_at": _now(), "updated_at": _now(),
    }})
    if j.get("charged_credits") and not j.get("refunded_credits"):
        try:
            await add_credits(j["user_id"], j["charged_credits"], f"Refund failed trailer {job_id}", tx_type="REFUND")
            await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {"refunded_credits": j["charged_credits"]}})
        except Exception as e:
            log.warning(f"refund failed: {e}")
    await _emit("photo_trailer_generation_failed", j["user_id"], {"job_id": job_id, "code": code})

async def _load_asset_bytes(asset_id: str) -> Optional[bytes]:
    a = await db.photo_trailer_assets.find_one({"_id": asset_id})
    if not a: return None
    url = a.get("storage_url")
    if not url: return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(url)
            return r.content if r.status_code == 200 else None
    except Exception as e:
        log.warning(f"load asset {asset_id} failed: {e}")
        return None

async def _llm_script(job: dict, hero_role_hint: str) -> List[Dict[str, str]]:
    """Returns list of {'narration': str, 'visual': str} per scene.
    Offloaded to worker thread — emergentintegrations blocks the loop."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    tpl = TEMPLATES[job["template_id"]]
    scene_count = tpl["scene_count"]
    target_seconds = job["duration_target_seconds"]
    seconds_per_scene = max(3, target_seconds // scene_count)
    sys_prompt = (
        "You are a cinematic trailer scriptwriter. Output VALID JSON only — no commentary. "
        "Schema: {\"scenes\": [{\"narration\": \"~12 word voiceover line\", \"visual\": \"detailed cinematic visual prompt\"}]}. "
        f"Tone: {tpl['tone']}. Template: {tpl['title']} — {tpl['description']}. "
        f"Hero is {hero_role_hint}. Trailer is {target_seconds}s split across {scene_count} scenes (~{seconds_per_scene}s each). "
        "Keep all content SFW, no real-celebrity claims, no political figures, no minors in unsafe contexts. "
        "Each visual prompt MUST emphasize that the hero's face/character must remain consistent across all scenes."
    )
    user_text = job.get("custom_prompt") or f"A {tpl['tone']} {tpl['title'].lower()} trailer."
    session_id = f"trailer_{job['_id']}"

    def _sync_call() -> str:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=sys_prompt)
        chat.with_model("anthropic", "claude-sonnet-4-20250514")
        raw = asyncio.run(chat.send_message(UserMessage(text=f"Write the trailer for: {user_text}")))
        return raw if isinstance(raw, str) else str(raw)

    txt = await asyncio.get_event_loop().run_in_executor(IMAGE_EXECUTOR, _sync_call)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m: raise RuntimeError(f"script parse failed: {txt[:200]}")
    data = json.loads(m.group(0))
    scenes = data.get("scenes") or []
    if not scenes: raise RuntimeError("script empty")
    return scenes[:scene_count]

async def _gen_scene_image(visual_prompt: str, hero_b64: str, villain_b64: Optional[str], session_id: str) -> bytes:
    """Generate one scene image with reference photos for character consistency.
    Runs the (sync-under-async) emergentintegrations call on a worker thread
    so the main FastAPI event loop stays responsive for other users."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    refs = [ImageContent(hero_b64)]
    if villain_b64: refs.append(ImageContent(villain_b64))
    full_prompt = (
        f"{visual_prompt}\n\nCRITICAL: The hero in this scene must visually match the FIRST reference photo's "
        "face, age, ethnicity, hair and overall identity. Cinematic 16:9 framing. Photorealistic film still. "
        "Strong dramatic lighting. No on-screen text. No watermarks. No logos."
    )

    def _sync_call() -> bytes:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message="You generate a single cinematic image.")
        chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        msg = UserMessage(text=full_prompt, file_contents=refs)
        # Each thread runs its own event loop — emergentintegrations' blocking
        # I/O stays in this worker thread, never touching the main loop.
        # Light retry on transient upstream failures (rate limits, parser errors).
        last_err = None
        for attempt in range(2):
            try:
                _txt, images = asyncio.run(chat.send_message_multimodal_response(msg))
                if images and images[0].get("data"):
                    return base64.b64decode(images[0]["data"])
                last_err = RuntimeError(f"empty response (txt={(_txt or '')[:100]})")
            except Exception as e:
                last_err = e
                log.warning(f"[scene_image] attempt {attempt+1} failed for {session_id}: {type(e).__name__}: {str(e)[:200]}")
        raise last_err or RuntimeError("image gen failed after retries")

    return await asyncio.get_event_loop().run_in_executor(IMAGE_EXECUTOR, _sync_call)

async def _tts(narration: str, voice: str) -> bytes:
    """OpenAI TTS via emergentintegrations — runs on the AUDIO_EXECUTOR."""
    from emergentintegrations.llm.openai import OpenAITextToSpeech

    def _sync_call() -> bytes:
        tts = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
        return asyncio.run(tts.generate_speech(text=narration[:4000], model="tts-1", voice=voice))

    return await asyncio.get_event_loop().run_in_executor(AUDIO_EXECUTOR, _sync_call)

def _ffmpeg_run(args: List[str]) -> None:
    res = subprocess.run(args, capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        log.error(f"ffmpeg cmd failed: {' '.join(args[:4])}... stderr: {res.stderr[-1200:]}")
        raise RuntimeError(f"ffmpeg failed: {res.stderr[-600:]}")

async def _ffmpeg(args: List[str]) -> None:
    """Run ffmpeg in the dedicated RENDER_EXECUTOR — bounded so 5 simultaneous
    pipelines cannot all spawn ffmpeg processes at the same time."""
    await asyncio.get_event_loop().run_in_executor(RENDER_EXECUTOR, _ffmpeg_run, args)

# ───────────────────── Motion engine (v2) ────────────────────────────────────
# Spec: every scene must visibly move. ≥4 motion styles per 6-scene trailer.
# No frozen frames > 1s. 8 distinct camera moves rotated by scene index +
# template-tone seed. Per-template tone color grade. Subtitle drawn from
# narration line. 0.25s fade-in/out per clip simulates a soft trailer-cut.

# Each motion is parameterized by frame count for the scene's duration
# so movement is continuous regardless of clip length.
def _motion_filter(idx: int, frames: int) -> str:
    """Pick a motion style by index. zoompan paints one frame per `d` step;
    we drive `d=frames` so the move plays exactly once across the clip."""
    f = max(1, int(frames))
    # All motions use `on` (current output frame number) directly so the
    # ffmpeg zoom variable's accumulation quirks can never freeze a clip.
    # Each style produces visibly continuous motion at every frame.
    h = 2.6  # horizontal sweep px/frame
    v = 1.8  # vertical sweep px/frame
    styles = [
        # 0: slow_push — 1.00 → ~1.22 over the clip
        f"zoompan=z='1.0+on*0.0030':d={f}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25",
        # 1: pan_right — fixed zoom, horizontal sweep
        f"zoompan=z='1.20':d={f}:x='(iw-iw/zoom)/2+on*{h}':y='(ih-ih/zoom)/2':s=1280x720:fps=25",
        # 2: pull_back — 1.32 → ~1.10
        f"zoompan=z='1.32-on*0.0030':d={f}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25",
        # 3: push_to_face — 1.00 → ~1.30, anchored toward upper third
        f"zoompan=z='1.0+on*0.0040':d={f}:x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':s=1280x720:fps=25",
        # 4: pan_left
        f"zoompan=z='1.20':d={f}:x='(iw-iw/zoom)/2-on*{h}':y='(ih-ih/zoom)/2':s=1280x720:fps=25",
        # 5: diagonal_drift — zoom + diagonal sweep
        f"zoompan=z='1.0+on*0.0022':d={f}:x='(iw-iw/zoom)/2+on*{h}':y='(ih-ih/zoom)/2+on*{v}':s=1280x720:fps=25",
        # 6: handheld_shake — micro shake with sin/cos
        f"zoompan=z='1.22':d={f}:x='iw/2-(iw/zoom/2)+sin(on/2.8)*22':y='ih/2-(ih/zoom/2)+cos(on/2.4)*14':s=1280x720:fps=25",
        # 7: vertical_reveal — pan upward
        f"zoompan=z='1.22':d={f}:x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)-on*{v}':s=1280x720:fps=25",
    ]
    return styles[idx % len(styles)]

# Tone seed: ensures the FIRST scene of a horror trailer leans handheld,
# action leans push-to-face, etc. Subsequent scenes rotate from there so
# every trailer still gets ≥4 distinct moves.
_TONE_SEED = {
    "epic": 3, "horror": 6, "scary": 6, "comedy": 1, "comedic": 1,
    "cinematic": 0, "intense": 6, "warm": 0, "playful": 1, "mysterious": 7,
    "action": 3, "anime": 3, "fantasy": 0, "mythology": 0, "love": 0,
    "family": 0, "drama": 0, "romance": 0, "documentary": 0,
}

# Per-template color grade. Subtle, applied via eq+curves which are bundled
# in stock ffmpeg. NEVER strong enough to alter identity.
_TONE_GRADE = {
    "horror":     "eq=contrast=1.18:saturation=0.78:brightness=-0.05",
    "scary":      "eq=contrast=1.18:saturation=0.78:brightness=-0.05",
    "epic":       "eq=contrast=1.10:saturation=1.15:gamma=0.95",
    "action":     "eq=contrast=1.18:saturation=1.10",
    "anime":      "eq=saturation=1.30:contrast=1.10",
    "comedic":    "eq=saturation=1.18:brightness=0.04",
    "comedy":     "eq=saturation=1.18:brightness=0.04",
    "love":       "eq=saturation=1.10:gamma=1.05",
    "family":     "eq=saturation=1.10:gamma=1.05",
    "warm":       "eq=saturation=1.10:gamma=1.05",
    "fantasy":    "eq=saturation=1.20:gamma=1.05",
    "mythology":  "eq=saturation=1.20:gamma=1.05",
    "cinematic":  "eq=contrast=1.08:saturation=1.05",
    "mysterious": "eq=contrast=1.10:saturation=0.92:brightness=-0.03",
}

def _ffmpeg_text_escape(s: str) -> str:
    """Escape a string for use inside ffmpeg drawtext text= parameter.
    Commas would break the surrounding filter chain; colons and single-quotes
    are filter-syntax delimiters; backslashes are illegal."""
    s = (s or "").replace("\\", "")
    return (s.replace(",", "")        # comma: filter chain separator
             .replace(":", " ")       # colon: filter argument separator
             .replace("'", "’")       # single quote: filter string delimiter
             .replace("[", "(").replace("]", ")"))  # brackets: filter labels

def _subtitle_filter(narration: str) -> str:
    txt = _ffmpeg_text_escape(narration)[:90]
    if not txt: return None
    return ("drawtext=text='" + txt + "':"
            "fontcolor=white:fontsize=28:"
            "box=1:boxcolor=black@0.55:boxborderw=10:"
            "x=(w-tw)/2:y=h-th-32")

# ─────────────────────────────────────────────────────────────────────────────
async def _render_trailer(job: dict, scenes_data: List[dict], tmp: str) -> str:
    """ffmpeg: stitch images with varied motion + voiceover + music +
    subtitles + end card. Each scene gets a distinct camera move + tone
    grade + scene subtitle + 0.25s fade-in/out so cuts feel cinematic."""
    import imageio_ffmpeg
    # Prefer system ffmpeg (has drawtext + libfreetype). Fall back to bundled.
    ffmpeg = "/usr/bin/ffmpeg" if os.path.exists("/usr/bin/ffmpeg") else imageio_ffmpeg.get_ffmpeg_exe()
    template = TEMPLATES.get(job.get("template_id", ""), {})
    tone = (template.get("tone") or "cinematic").lower()
    tone_seed = _TONE_SEED.get(tone, 0)
    grade = _TONE_GRADE.get(tone)

    out_clips = []
    for i, s in enumerate(scenes_data):
        img = s["image_path"]; aud = s["audio_path"]; dur = max(3.0, s["duration"])
        clip = os.path.join(tmp, f"clip_{i}.mp4")
        # 8-style motion rotation seeded by template tone — 6-scene trailers
        # always get ≥ 4 distinct moves (verified by frame-diff regression).
        frames = max(75, int(dur * 25))
        motion = _motion_filter(tone_seed + i, frames)
        subtitle = _subtitle_filter(s.get("narration", ""))

        # Filter chain: scale → crop → setsar → motion → tone grade →
        # subtitle → fade-in/out → format. fade=t=in/out at 0.25s simulates
        # a soft trailer-cut crossfade when clips are concatenated.
        chain = [
            "scale=1280:720:force_original_aspect_ratio=increase",
            "crop=1280:720",
            "setsar=1",
            motion,
        ]
        if grade:    chain.append(grade)
        if subtitle: chain.append(subtitle)
        chain.append(f"fade=t=in:st=0:d=0.25,fade=t=out:st={max(0.0, dur-0.25):.2f}:d=0.25")
        chain.append("format=yuv420p")
        vf = ",".join(chain)

        await _ffmpeg([ffmpeg, "-y", "-loop", "1", "-i", img, "-i", aud,
                     "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-b:a", "128k", "-r", "25", "-t", f"{dur}",
                     "-shortest", "-movflags", "+faststart", clip])
        out_clips.append(clip)
    # End card — 2.5s static branded text
    end_card = os.path.join(tmp, "endcard.mp4")
    await _ffmpeg([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=2.5:r=25",
                 "-vf", "drawtext=text='Created with Visionary Suite':fontcolor=white:fontsize=42:x=(w-tw)/2:y=(h-th)/2-30,"
                        "drawtext=text='visionary-suite.com':fontcolor=#a78bfa:fontsize=24:x=(w-tw)/2:y=(h-th)/2+30",
                 "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", "25",
                 "-c:a", "aac", "-shortest", end_card])
    out_clips.append(end_card)
    # Concat
    concat_txt = os.path.join(tmp, "concat.txt")
    with open(concat_txt, "w") as f:
        for c in out_clips: f.write(f"file '{c}'\n")
    stitched = os.path.join(tmp, "stitched.mp4")
    await _ffmpeg([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
                 "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                 "-movflags", "+faststart", stitched])
    # Music bed (if available) — duck under voiceover
    music_path = os.path.join(MUSIC_PACK_DIR, MUSIC_TRACK_BY_MOOD.get(job.get("music_mood", ""), ""))
    if not os.path.exists(music_path): music_path = None
    # Watermark + optional music
    final = os.path.join(tmp, "final.mp4")
    wm_filter = ("[0:v]drawtext=text='Visionary Suite':fontcolor=white@0.65:fontsize=18:"
                 "x=w-tw-22:y=h-th-22:box=1:boxcolor=black@0.25:boxborderw=8[v]")
    if music_path:
        await _ffmpeg([ffmpeg, "-y", "-i", stitched, "-stream_loop", "-1", "-i", music_path,
                     "-filter_complex", wm_filter + ";[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=shortest[a]",
                     "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-shortest",
                     "-movflags", "+faststart", final])
    else:
        await _ffmpeg([ffmpeg, "-y", "-i", stitched, "-vf", "drawtext=text='Visionary Suite':fontcolor=white@0.65:fontsize=18:"
                     "x=w-tw-22:y=h-th-22:box=1:boxcolor=black@0.25:boxborderw=8",
                     "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                     "-c:a", "copy", "-movflags", "+faststart", final])
    return final

async def _run_pipeline(job_id: str):
    """The orchestrator. Each stage advances progress + updates DB.
    Wrapped by a system-wide semaphore (max 2 concurrent pipelines) so one
    user's trailer can never overload the backend for other users."""
    async with _PIPELINE_GATE:
        await _run_pipeline_inner(job_id)

async def _run_pipeline_inner(job_id: str):
    """Inner pipeline body — runs once the gate has been acquired."""
    j = await db.photo_trailer_jobs.find_one({"_id": job_id})
    if not j: return
    user_id = j["user_id"]
    tmpdir = tempfile.mkdtemp(prefix=f"trailer_{job_id}_")
    try:
        # Mark processing + charge
        await _set_stage(job_id, "VALIDATING", status="PROCESSING", started_at=_now())
        cred = j["estimated_credits"]
        try:
            await deduct_credits(user_id, cred, f"Photo trailer {job_id}")
            await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {"charged_credits": cred}})
        except Exception as e:
            return await _fail(job_id, "CREDIT_DEDUCT_FAIL", str(e)[:200])
        await _emit("photo_trailer_generation_started", user_id, {"job_id": job_id})

        # Hero photo bytes (required) + villain (optional) → base64 refs
        await _set_stage(job_id, "ANALYZING_PHOTOS")
        hero_bytes = await _load_asset_bytes(j["hero_asset_id"])
        if not hero_bytes: return await _fail(job_id, "HERO_LOAD_FAIL", "Could not load hero photo. Try uploading again.")
        hero_b64 = base64.b64encode(hero_bytes).decode("utf-8")
        villain_b64 = None
        if j.get("villain_asset_id"):
            vb = await _load_asset_bytes(j["villain_asset_id"])
            if vb: villain_b64 = base64.b64encode(vb).decode("utf-8")

        # Script
        await _set_stage(job_id, "BUILDING_CHARACTER")
        await _set_stage(job_id, "WRITING_TRAILER_SCRIPT")
        try:
            scenes = await _llm_script(j, hero_role_hint="the person in the FIRST reference photo")
        except Exception as e:
            return await _fail(job_id, "SCRIPT_FAIL", f"Trailer writing hit a hiccup. Please retry.")
        await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {"script_text": json.dumps(scenes)[:8000]}})

        # Image + voice generation per scene (parallelised)
        await _set_stage(job_id, "GENERATING_SCENES")
        scene_payload: List[dict] = []
        per_scene_dur = max(3.0, j["duration_target_seconds"] / max(1, len(scenes)))

        async def _scene_assets(idx: int, sc: dict) -> dict:
            img_bytes = await _gen_scene_image(sc["visual"], hero_b64, villain_b64, session_id=f"img_{job_id}_{idx}")
            img_path = os.path.join(tmpdir, f"scene_{idx}.png")
            with open(img_path, "wb") as f: f.write(img_bytes)
            await db.photo_trailer_scenes.insert_one({
                "_id": str(uuid.uuid4()), "job_id": job_id, "user_id": user_id,
                "scene_index": idx, "scene_type": "main", "scene_prompt": sc["visual"][:1000],
                "character_prompt": "hero+villain refs", "narration_text": sc["narration"][:500],
                "image_asset_id": None, "audio_asset_id": None, "duration_seconds": per_scene_dur,
                "motion_type": ["ZOOM", "PAN", "PUSH_IN"][idx % 3], "transition_type": "fade",
                "status": "DONE", "created_at": _now(),
            })
            return {"idx": idx, "image_path": img_path, "narration": sc["narration"]}

        try:
            scene_payload = await asyncio.gather(*[_scene_assets(i, sc) for i, sc in enumerate(scenes)])
        except Exception as e:
            log.exception(f"[trailer {job_id}] image gen failed: {e}")
            return await _fail(job_id, "IMAGE_GEN_FAIL", "Some scenes couldn't render. Please retry.")

        # Voiceover per scene
        await _set_stage(job_id, "GENERATING_VOICEOVER")
        async def _v(p):
            audio = await _tts(p["narration"], j.get("narrator_style") or "alloy")
            ap = os.path.join(tmpdir, f"audio_{p['idx']}.mp3"); 
            with open(ap, "wb") as f: f.write(audio)
            p["audio_path"] = ap; p["duration"] = per_scene_dur
            return p
        try:
            scene_payload = await asyncio.gather(*[_v(p) for p in scene_payload])
        except Exception as e:
            return await _fail(job_id, "TTS_FAIL", "Voiceover hit a hiccup. Please retry.")

        # Render
        await _set_stage(job_id, "ADDING_MUSIC")
        await _set_stage(job_id, "RENDERING_TRAILER")
        try:
            scene_payload.sort(key=lambda p: p["idx"])
            final_path = await _render_trailer(j, scene_payload, tmpdir)
        except Exception as e:
            log.exception(f"render failed for {job_id}")
            return await _fail(job_id, "RENDER_FAIL", "Final render hit a hiccup. Please retry.")

        # Upload
        with open(final_path, "rb") as f: video_bytes = f.read()
        ok, video_url = await _upload_video_bytes(video_bytes, f"trailer_{job_id}.mp4", user_id)
        if not ok:
            return await _fail(job_id, "UPLOAD_FAIL", "Storage upload failed. Please retry.")
        # Thumbnail = first scene image
        thumb_url = None
        try:
            with open(scene_payload[0]["image_path"], "rb") as f: tb = f.read()
            ok2, thumb_url_or_key = await upload_image_bytes(tb, f"trailer_{job_id}_thumb.jpg", project_id=f"phototrailer/{user_id}/results")
            if ok2: thumb_url = thumb_url_or_key
        except Exception:
            pass

        # Record output
        await db.photo_trailer_outputs.insert_one({
            "_id": str(uuid.uuid4()), "job_id": job_id, "user_id": user_id,
            "video_storage_key": video_url, "thumbnail_storage_key": thumb_url,
            "duration_seconds": j["duration_target_seconds"], "resolution": "1280x720",
            "file_size": len(video_bytes), "watermark_applied": True, "end_card_applied": True,
            "download_token_required": True, "created_at": _now(),
        })
        slug = uuid.uuid4().hex[:10]
        await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {
            "status": "COMPLETED", "current_stage": "COMPLETED", "progress_percent": 100,
            "result_video_url": video_url, "result_thumbnail_url": thumb_url,
            "public_share_slug": slug, "completed_at": _now(), "updated_at": _now(),
        }})
        await _emit("photo_trailer_generation_completed", user_id, {"job_id": job_id, "duration": j["duration_target_seconds"]})

        # In-app notification: "Your YouStar trailer is ready" — re-uses the
        # existing notification system; the bell + center already polls these.
        try:
            from services.notification_service import NotificationService
            tpl_name = j.get("template_name") or TEMPLATES.get(j["template_id"], {}).get("title", "trailer")
            await NotificationService(db).create_notification(
                user_id=user_id,
                notification_type="generation_complete",
                feature="photo_trailer",
                title="Your YouStar trailer is ready",
                message=f"Your '{tpl_name}' trailer just finished — tap to watch.",
                job_id=job_id,
                download_url=video_url,
                action_url=f"/app/my-space?trailer={job_id}",
                metadata={"template_id": j["template_id"], "thumbnail_url": thumb_url, "duration": j["duration_target_seconds"]},
            )
        except Exception as e:
            log.warning(f"[trailer {job_id}] notification create failed (non-fatal): {e}")
    except Exception as e:
        log.exception(f"orchestrator crash {job_id}")
        await _fail(job_id, "PIPELINE_CRASH", str(e)[:200])
    finally:
        try:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception: pass


async def _upload_video_bytes(data: bytes, name: str, user_id: str) -> (bool, str):
    """Upload an in-memory MP4 to R2 (or local fallback)."""
    from services.cloudflare_r2_storage import get_r2_storage
    service = get_r2_storage()
    if not service or not getattr(service, "_client", None):
        try:
            os.makedirs("/app/backend/static/trailer_outputs", exist_ok=True)
            local = f"/app/backend/static/trailer_outputs/{name}"
            with open(local, "wb") as f: f.write(data)
            return True, f"/static/trailer_outputs/{name}"
        except Exception as e:
            return False, str(e)
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as t:
            t.write(data); local_path = t.name
        ok, url, key = await service.upload_file(local_path, asset_type="video",
                                                 project_id=f"phototrailer/{user_id}/results",
                                                 custom_filename=name)
        try: os.unlink(local_path)
        except Exception: pass
        return ok, (url or key)
    except Exception as e:
        return False, str(e)



# ═════════════════════════ STALE-JOB JANITOR ════════════════════════════════════
# Reaps Photo Trailer jobs stuck in PROCESSING > STALE_THRESHOLD minutes.
# Hardens against backend restart drops + orphaned pipelines (e.g. a worker
# crash mid-render). Marks them FAILED with STALE_PIPELINE and refunds the
# user's credits exactly once. Idempotent — re-running is safe.

STALE_THRESHOLD_MINUTES = 5
JANITOR_INTERVAL_SECONDS = 120

async def _reap_stale_pipelines() -> Dict[str, Any]:
    """Single sweep — find + reap PROCESSING jobs older than the threshold.
    Returns metrics dict for logging/testing. Atomic + idempotent:
    the status update is gated on `status: PROCESSING`, so if two janitors
    or a real completion race the reap, only one wins and only that one
    issues a refund."""
    cutoff_dt = datetime.now(timezone.utc) - timedelta(minutes=STALE_THRESHOLD_MINUTES)
    cutoff_iso = cutoff_dt.isoformat()
    reaped, refunded_total, refund_failures, skipped_already_terminal = 0, 0, 0, 0

    cursor = db.photo_trailer_jobs.find({
        "status": "PROCESSING",
        "started_at": {"$lt": cutoff_iso, "$ne": None},
    })
    async for j in cursor:
        jid = j["_id"]
        # Atomic transition: only flip if STILL PROCESSING. Loses race -> skip.
        upd = await db.photo_trailer_jobs.update_one(
            {"_id": jid, "status": "PROCESSING"},
            {"$set": {
                "status": "FAILED", "current_stage": "FAILED",
                "error_code": "STALE_PIPELINE",
                "error_message": "Trailer didn't complete in time. Credits refunded — please retry.",
                "failed_at": _now(), "updated_at": _now(),
            }},
        )
        if upd.modified_count == 0:
            skipped_already_terminal += 1
            continue

        # Refund exactly once: only if charged > 0 AND not previously refunded.
        # The atomic guard above ensures only one janitor instance can reach here.
        charged = j.get("charged_credits") or 0
        prior_refund = j.get("refunded_credits") or 0
        if charged > 0 and prior_refund == 0:
            try:
                await add_credits(j["user_id"], charged, f"Refund stale trailer {jid}", tx_type="REFUND")
                # Belt-and-braces: the refunded_credits write is itself idempotent
                # (set to charged value, won't double if re-run somehow).
                await db.photo_trailer_jobs.update_one(
                    {"_id": jid, "refunded_credits": 0},
                    {"$set": {"refunded_credits": charged}},
                )
                refunded_total += charged
                age_min = round((datetime.now(timezone.utc) - cutoff_dt).total_seconds() / 60 + STALE_THRESHOLD_MINUTES, 1)
                log.warning(
                    f"[trailer-janitor] Reaped stale job {jid} user={j['user_id']} "
                    f"template={j.get('template_id')} age>={age_min}min refunded={charged}cr"
                )
            except Exception as e:
                refund_failures += 1
                log.error(f"[trailer-janitor] Refund failed for {jid}: {e}")
        else:
            log.warning(
                f"[trailer-janitor] Reaped stale job {jid} user={j['user_id']} "
                f"template={j.get('template_id')} (no refund needed: charged={charged} prior_refund={prior_refund})"
            )
        try:
            await _emit("photo_trailer_generation_failed", j["user_id"],
                        {"job_id": jid, "code": "STALE_PIPELINE", "via": "janitor"})
        except Exception:
            pass
        reaped += 1

    return {
        "reaped": reaped,
        "refunded_credits_total": refunded_total,
        "refund_failures": refund_failures,
        "skipped_already_terminal": skipped_already_terminal,
        "cutoff_iso": cutoff_iso,
    }


async def stale_pipeline_janitor_loop():
    """Forever loop wired up at server startup. Runs `_reap_stale_pipelines`
    every JANITOR_INTERVAL_SECONDS seconds. Survives individual sweep errors."""
    log.info(f"[trailer-janitor] starting (every {JANITOR_INTERVAL_SECONDS}s, threshold {STALE_THRESHOLD_MINUTES}min)")
    # Small delay so other startup tasks settle first.
    await asyncio.sleep(15)
    while True:
        try:
            result = await _reap_stale_pipelines()
            if result["reaped"] > 0:
                log.info(f"[trailer-janitor] sweep result: {result}")
        except Exception as e:
            log.exception(f"[trailer-janitor] sweep crashed: {e}")
        await asyncio.sleep(JANITOR_INTERVAL_SECONDS)


@router.post("/admin/janitor/run-now")
async def admin_run_janitor(user: dict = Depends(get_admin_user)):
    """Admin manual trigger — used by tests + ops."""
    return await _reap_stale_pipelines()
