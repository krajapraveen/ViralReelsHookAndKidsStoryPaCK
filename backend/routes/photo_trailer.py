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
import time
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
# Two-lane queueing:
#   _STANDARD_GATE → fair queue for FREE + PAID jobs (default 2 slots)
#   _PRIORITY_GATE → dedicated lane for PREMIUM jobs (default 1 extra slot)
# PREMIUM jobs FIRST try the priority lane (instant claim if available); if
# both are busy they wait on whichever frees first. This gives Premium an
# honest "skip the queue" claim WITHOUT starving standard tier — the
# standard semaphore is unaffected.
_STANDARD_GATE = asyncio.Semaphore(MAX_ACTIVE_PIPELINES)
PRIORITY_SLOTS = int(os.environ.get("PHOTO_TRAILER_PRIORITY_SLOTS", "1"))
_PRIORITY_GATE = asyncio.Semaphore(PRIORITY_SLOTS)
# Back-compat alias (some old call-sites + tests reference it)
_PIPELINE_GATE = _STANDARD_GATE

MAX_PHOTOS = 10
MAX_PHOTO_BYTES = 10 * 1024 * 1024
ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ACTIVE_JOB_LIMIT = {"FREE": 1, "PAID": 2, "PREMIUM": 3, "ADMIN": 10}
# ─── Pricing & plan tiers ────────────────────────────────────────────────────
# Tier system (computed live from existing fields — no schema migration):
#   PREMIUM = active subscription with monthly/quarterly/yearly plan.
#             Unlocks 90s trailers + priority queue (future) + premium templates (future).
#   PAID    = active weekly subscription, OR a non-zero credit balance large
#             enough to afford a 60s trailer. Unlocks 60s.
#   FREE    = no active subscription AND can't afford 60s.
#             Limited to 15s preview, capped at FREE_MONTHLY_QUOTA per month.
#
# Credits unchanged structure. 15s is now zero-cost (free preview); 60s and 90s
# remain credit-charged so even Premium subscribers consume their bucket.
DURATION_BUCKETS = [(15, 0), (20, 0), (45, 25), (60, 35), (90, 60)]  # (max_sec, credits)
PREMIUM_PLAN_IDS = {"monthly", "quarterly", "yearly"}
WEEKLY_PLAN_IDS  = {"weekly"}
FREE_MONTHLY_QUOTA = int(os.environ.get("PHOTO_TRAILER_FREE_QUOTA", "3"))
PREMIUM_MIN_DURATION = 90  # 90s+ requires PREMIUM
PAID_MIN_DURATION    = 60  # 60s+ requires PAID or PREMIUM

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
    duration_target_seconds: int = Field(45, ge=15, le=90)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _now(): return datetime.now(timezone.utc).isoformat()
def _credits_for(seconds: int) -> int:
    for sec, c in DURATION_BUCKETS:
        if seconds <= sec: return c
    return DURATION_BUCKETS[-1][1]

async def _user_plan(user: dict) -> str:
    """Compute the user's plan tier live. Returns FREE | PAID | PREMIUM.
    ADMIN role short-circuits to PREMIUM so internal QA isn't paywalled."""
    if (user.get("role") or "").upper() == "ADMIN":
        return "PREMIUM"
    # Check live subscription doc — there can only be one active sub per user.
    sub = await db.subscriptions.find_one(
        {"userId": user["id"], "status": "active"},
        sort=[("createdAt", -1)],
    )
    if sub:
        plan_id = (sub.get("planId") or "").lower()
        if plan_id in PREMIUM_PLAN_IDS: return "PREMIUM"
        if plan_id in WEEKLY_PLAN_IDS:  return "PAID"
    # No active sub → fall back to credit balance check.
    if (user.get("credits") or 0) >= 35:  # enough to afford a 60s trailer
        return "PAID"
    return "FREE"

async def _free_quota_used_this_month(user_id: str) -> int:
    """Count of trailer jobs the user CREATED in the current calendar month.
    Used to enforce FREE_MONTHLY_QUOTA on the FREE tier 15s preview."""
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    return await db.photo_trailer_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": start_of_month},
        # Only count jobs that actually consumed a slot (not pre-validation rejects).
        "status": {"$in": ["QUEUED", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"]},
    })

def _required_plan_for_duration(seconds: int) -> str:
    """The minimum plan tier required to render `seconds`-long trailer."""
    if seconds >= PREMIUM_MIN_DURATION: return "PREMIUM"
    if seconds >= PAID_MIN_DURATION:    return "PAID"
    return "FREE"

def _plan_rank(p: str) -> int:
    return {"FREE": 0, "PAID": 1, "PREMIUM": 2}.get((p or "FREE").upper(), 0)

def _user_role(u: dict) -> str: return (u.get("role") or "FREE").upper()

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
async def credit_estimate(duration: int = Query(45, ge=15, le=90), user: dict = Depends(get_current_user)):
    """Returns the credits cost AND the entitlement state for `duration`.
    Frontend uses this to render the lock icon on premium-only durations
    and to pre-fill the upgrade modal's CTA without waiting for a 402."""
    plan = await _user_plan(user)
    required = _required_plan_for_duration(duration)
    can_afford = (user.get("credits") or 0) >= _credits_for(duration)
    has_plan = _plan_rank(plan) >= _plan_rank(required)
    free_used = await _free_quota_used_this_month(user["id"]) if plan == "FREE" else 0
    return {
        "duration_seconds": duration,
        "credits": _credits_for(duration),
        "user_credits": user.get("credits", 0),
        "user_plan": plan,
        "required_plan": required,
        "has_required_plan": has_plan,
        "can_afford": can_afford,
        "free_quota": {
            "limit": FREE_MONTHLY_QUOTA, "used": free_used,
            "remaining": max(0, FREE_MONTHLY_QUOTA - free_used),
        } if plan == "FREE" else None,
    }

@router.get("/me/plan")
async def my_plan(user: dict = Depends(get_current_user)):
    """Lightweight plan probe — used by the frontend to render badges &
    duration-selector lock icons without computing on every keystroke."""
    plan = await _user_plan(user)
    return {
        "plan": plan,
        "credits": user.get("credits", 0),
        "free_quota_used": await _free_quota_used_this_month(user["id"]) if plan == "FREE" else None,
        "free_quota_limit": FREE_MONTHLY_QUOTA if plan == "FREE" else None,
        "max_duration_seconds": 90 if plan == "PREMIUM" else (60 if plan == "PAID" else 20),
        "premium_features": {
            "duration_90s": plan == "PREMIUM",
            "priority_queue": plan == "PREMIUM",
        },
    }

# ─── Trust & Legal: prompt sanitizer ──────────────────────────────────────────
# Hard-block list of phrases we will not generate. Three categories:
#   1. Real public figures & celebrities (likeness rights + defamation risk)
#   2. Copyrighted franchises / characters (IP infringement)
#   3. Explicit / minors-unsafe / hate / violence-glorification content
# We REJECT loudly at job creation time so credits are never charged. Frontend
# shows the reason verbatim; the user can reword and retry.
_BLOCK_PATTERNS = [
    # Politicians / heads of state / activists (small public list — not exhaustive,
    # serves as a deterrent + audit trail; full coverage requires an LLM-side filter).
    r"\b(donald\s*trump|joe\s*biden|narendra\s*modi|vladimir\s*putin|xi\s*jinping|kamala\s*harris|barack\s*obama|elon\s*musk|kim\s*jong[\-\s]*un|emmanuel\s*macron|rishi\s*sunak|mark\s*zuckerberg|jeff\s*bezos)\b",
    # Top-tier celebrities / actors / athletes (likeness)
    r"\b(taylor\s*swift|beyonc[eé]|rihanna|drake|kanye\s*west|ariana\s*grande|justin\s*bieber|selena\s*gomez|lady\s*gaga|tom\s*cruise|tom\s*holland|robert\s*downey|leonardo\s*dicaprio|brad\s*pitt|angelina\s*jolie|johnny\s*depp|will\s*smith|dwayne\s*johnson|the\s*rock|chris\s*hemsworth|chris\s*evans|scarlett\s*johansson|gal\s*gadot|jennifer\s*lawrence|emma\s*watson|harry\s*styles|virat\s*kohli|lionel\s*messi|cristiano\s*ronaldo|ms\s*dhoni|shahrukh\s*khan|salman\s*khan|deepika\s*padukone|priyanka\s*chopra)\b",
    # Copyrighted franchises / characters
    r"\b(marvel|avengers|iron\s*man|spider[\-\s]*man|spiderman|captain\s*america|thor|hulk|black\s*widow|hawkeye|black\s*panther|wakanda|loki|thanos|wanda|doctor\s*strange|deadpool|wolverine|x[\-\s]*men)\b",
    r"\b(dc\s+comics|batman|superman|wonder\s*woman|the\s*joker|aquaman|the\s*flash|green\s*lantern|harley\s*quinn|justice\s*league)\b",
    r"\b(disney|pixar|mickey\s*mouse|donald\s*duck|elsa|anna|frozen|moana|ariel|cinderella|simba|nemo|woody|buzz\s*lightyear|toy\s*story)\b",
    r"\b(star\s*wars|jedi|sith|darth\s*vader|luke\s*skywalker|yoda|baby\s*yoda|grogu|mandalorian|kylo\s*ren)\b",
    r"\b(harry\s*potter|hogwarts|voldemort|hermione|dumbledore|gryffindor|slytherin)\b",
    r"\b(pokemon|pokémon|pikachu|charizard|nintendo|mario|luigi|princess\s*peach|zelda|sonic\s*the\s*hedgehog)\b",
    r"\b(naruto|goku|dragon\s*ball|one\s*piece|luffy|sasuke|kakashi|attack\s*on\s*titan|demon\s*slayer|jujutsu\s*kaisen)\b",
    r"\b(james\s*bond|007|mission\s*impossible|john\s*wick|fast\s*&?\s*furious|the\s*matrix|neo|john\s*rambo|rocky\s*balboa|terminator|t-800|t-1000)\b",
    r"\b(game\s*of\s*thrones|jon\s*snow|daenerys|stark|lannister|targaryen|breaking\s*bad|walter\s*white|stranger\s*things|eleven|squid\s*game)\b",
    # Explicit / NSFW / minors-unsafe / illegal / hate
    r"\b(nude|naked|nsfw|porn|sex\s*scene|erotic|fetish|onlyfans)\b",
    r"\b(child\s*(soldier|abuse|porn)|minor\s*(naked|nude|sexual)|underage\s*(sex|nude)|loli|shota)\b",
    r"\b(kill\s+(real|all)\s+\w+|behead|terrorist\s+attack|isis|al[\-\s]*qaeda|nazi\s+(victory|propaganda)|hitler\s+(portrait|hero|biography)|genocide|mass\s+shooting)\b",
    r"\b(deepfake|deep[\-\s]*fake|face[\-\s]*swap\s+(porn|nude|celeb))\b",
]
_BLOCK_REGEX = re.compile("|".join(_BLOCK_PATTERNS), re.IGNORECASE)

# Friendly rewrites — when the prompt LOOKS like an unsafe ask but we can
# soften it. Currently used for "deepfake" → "AI cinematic portrait".
_REWRITE_MAP = {
    r"\bdeep[\-\s]*fake\b": "AI cinematic portrait",
    r"\bface[\-\s]*swap\b": "AI character likeness",
}

def _sanitize_prompt(text: str) -> tuple[str, Optional[str]]:
    """Returns (cleaned_prompt, reject_reason). If reject_reason is non-None
    the caller MUST refuse the job. Otherwise the cleaned prompt is safe to
    forward downstream."""
    if not text: return ("", None)
    # 1. Light-touch rewrites first
    cleaned = text
    for pat, repl in _REWRITE_MAP.items():
        cleaned = re.sub(pat, repl, cleaned, flags=re.IGNORECASE)
    # 2. Hard-block check on the rewritten text
    m = _BLOCK_REGEX.search(cleaned)
    if m:
        bad = m.group(0)
        return (cleaned, f"Your prompt mentions \"{bad}\". To protect copyrights and likeness rights, "
                         "please reword without celebrities, public figures, or copyrighted characters.")
    return (cleaned, None)


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

    # ── Plan / entitlement enforcement (server-side; cannot be spoofed) ───
    plan = await _user_plan(user)
    required = _required_plan_for_duration(body.duration_target_seconds)
    if _plan_rank(plan) < _plan_rank(required):
        # 402 = Payment Required. Body conveys what to upgrade to.
        await _emit("photo_trailer_plan_blocked", user["id"], {
            "duration": body.duration_target_seconds,
            "current_plan": plan, "required_plan": required,
        })
        raise HTTPException(status_code=402, detail={
            "code": "UPGRADE_REQUIRED",
            "message": (
                f"{body.duration_target_seconds}-second trailers require the "
                f"{required} plan. Upgrade to unlock."
            ),
            "current_plan": plan,
            "required_plan": required,
            "duration_seconds": body.duration_target_seconds,
            "upgrade_url": "/app/pricing",
        })

    # FREE-tier monthly quota for the 15-20s preview path
    if plan == "FREE":
        used = await _free_quota_used_this_month(user["id"])
        if used >= FREE_MONTHLY_QUOTA:
            await _emit("photo_trailer_quota_exhausted", user["id"], {
                "used": used, "limit": FREE_MONTHLY_QUOTA,
            })
            raise HTTPException(status_code=429, detail={
                "code": "FREE_QUOTA_EXCEEDED",
                "message": (
                    f"You've used your {FREE_MONTHLY_QUOTA} free trailers this month. "
                    "Upgrade for unlimited 60s trailers."
                ),
                "used": used, "limit": FREE_MONTHLY_QUOTA,
                "upgrade_url": "/app/pricing",
            })

    cred = _credits_for(body.duration_target_seconds)
    have = int(user.get("credits") or 0)
    if have < cred and role != "ADMIN":
        # Suggest a shorter duration the user CAN afford right now — surfaces
        # the founder-mandated "downgrade to fit" UX without a round-trip.
        from typing import List as _List
        suggested: _List[int] = []
        for d in (15, 20, 45, 60, 90):
            if d < body.duration_target_seconds and _credits_for(d) <= have:
                suggested.append(d)
        await _emit("photo_trailer_low_credit_seen", user["id"], {
            "required_credits": cred, "current_credits": have,
            "missing_credits": cred - have,
            "duration_seconds": body.duration_target_seconds,
            "current_plan": plan,
        })
        raise HTTPException(402, detail={
            "code": "INSUFFICIENT_CREDITS",
            "message": "Your credits are too low to generate this trailer.",
            "required_credits": cred,
            "current_credits": have,
            "missing_credits": cred - have,
            "duration_seconds": body.duration_target_seconds,
            "current_plan": plan,
            "suggested_durations": suggested,  # e.g. [15, 20] for an affordable downgrade
            "upgrade_url": "/app/pricing",
            "topup_url": "/app/billing",
        })

    # ── Trust & Legal: prompt sanitizer (blocks before credits are charged) ──
    raw_prompt = (body.custom_prompt or "").strip()
    cleaned_prompt, reject_reason = _sanitize_prompt(raw_prompt)
    if reject_reason:
        # Audit trail for review without blowing up the user's credits.
        try:
            await db.photo_trailer_safety_blocks.insert_one({
                "_id": str(uuid.uuid4()), "user_id": user["id"],
                "raw_prompt": raw_prompt[:1000], "reason": reject_reason,
                "template_id": body.template_id, "blocked_at": _now(),
            })
        except Exception: pass
        await _emit("photo_trailer_prompt_blocked", user["id"], {"reason": reject_reason[:200]})
        raise HTTPException(400, reject_reason)
    job_id = str(uuid.uuid4())
    tpl = TEMPLATES[body.template_id]
    job = {
        "_id": job_id, "user_id": user["id"], "upload_session_id": body.upload_session_id,
        "status": "QUEUED", "current_stage": "QUEUED", "progress_percent": 0,
        "hero_asset_id": body.hero_asset_id, "villain_asset_id": body.villain_asset_id,
        "supporting_asset_ids": body.supporting_asset_ids,
        "template_id": body.template_id, "template_name": tpl["title"],
        "custom_prompt": cleaned_prompt[:500],
        "duration_target_seconds": body.duration_target_seconds,
        "estimated_credits": cred, "charged_credits": 0, "refunded_credits": 0,
        "narrator_style": tpl["narrator"], "music_mood": tpl["music_mood"],
        # Plan tier the user was on at job creation. Frozen here so the
        # MySpace card badge stays accurate even if they upgrade/downgrade later.
        "plan_tier_at_creation": plan,
        "is_priority": plan == "PREMIUM",
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

# ─── Signed-URL gateway (private playback) ────────────────────────────────────
# Public bucket exposure was a P0 risk: completed video URLs were permanent
# and unsigned, enabling scraping/hotlinking/uncontrolled distribution.
# All playback now flows through these endpoints which mint short-lived
# (10-min default) presigned URLs against the same R2 bucket. The owner-only
# `/stream` requires auth + ownership; the public `/share/{slug}` endpoint
# is rate-limit-safe (slug is 10-char random hex) and serves the share page.
SIGNED_URL_TTL_SECONDS = int(os.environ.get("PHOTO_TRAILER_SIGNED_URL_TTL", "600"))

def _strip_public_prefix(url: str) -> Optional[str]:
    """Convert a public R2 URL back to its bucket key. Used for migration
    of jobs that were created before we started storing the key explicitly."""
    if not url: return None
    if not url.startswith("http"): return url
    for prefix in (
        f"https://{R2_CUSTOM_DOMAIN}/" if R2_CUSTOM_DOMAIN else None,
        f"{R2_PUBLIC_URL.rstrip('/')}/" if R2_PUBLIC_URL else None,
    ):
        if prefix and url.startswith(prefix):
            return url[len(prefix):].split("?", 1)[0]
    for marker in ("/videos/", "/images/", "/voices/"):
        if marker in url:
            return marker.strip("/") + "/" + url.split(marker, 1)[1].split("?", 1)[0]
    return None

async def _sign_or_passthrough(key_or_url: str, *, ttl: int = SIGNED_URL_TTL_SECONDS,
                               filename: Optional[str] = None) -> Optional[str]:
    """Mint a presigned URL. Falls back to the original URL when R2 is not
    configured (local dev) or signing fails — so dev never breaks."""
    if not key_or_url: return None
    from services.cloudflare_r2_storage import get_r2_storage
    if key_or_url.startswith("/static/") or key_or_url.startswith("local/"):
        return key_or_url
    r2 = get_r2_storage()
    key = key_or_url if not key_or_url.startswith("http") else _strip_public_prefix(key_or_url)
    if r2 and key:
        try:
            signed = r2.generate_presigned_download_url(key=key, expiration=ttl, filename=filename)
            if signed: return signed
        except Exception as e:
            log.warning(f"presign failed for {key}: {e}")
    return key_or_url if key_or_url.startswith("http") else None

@router.get("/jobs/{job_id}/stream")
async def stream_video(job_id: str, user: dict = Depends(get_current_user),
                        download: bool = Query(False),
                        format: str = Query("wide", pattern="^(wide|vertical)$")):
    """Owner-only signed playback. `format=vertical` returns the 9:16 cut
    (Reels / Shorts / TikTok / WhatsApp Status). Falls back to widescreen
    when no vertical asset was rendered for this job."""
    j = await db.photo_trailer_jobs.find_one({"_id": job_id, "user_id": user["id"]})
    if not j: raise HTTPException(404, "Job not found")
    if j.get("status") != "COMPLETED":
        raise HTTPException(400, "Trailer is not ready yet.")
    use_vert = (format == "vertical") and bool(
        j.get("result_vertical_video_key") or j.get("result_vertical_video_url"))
    if use_vert:
        key = j.get("result_vertical_video_key") or _strip_public_prefix(j.get("result_vertical_video_url") or "")
    else:
        key = j.get("result_video_key")
        if not key:
            key = _strip_public_prefix(j.get("result_video_url") or "")
            if key:
                await db.photo_trailer_jobs.update_one(
                    {"_id": job_id}, {"$set": {"result_video_key": key}})
    if not key: raise HTTPException(404, "Video unavailable.")
    suffix = "_vertical" if use_vert else ""
    fname = f"trailer_{job_id[:8]}{suffix}.mp4" if download else None
    url = await _sign_or_passthrough(key, filename=fname)
    if not url: raise HTTPException(500, "Could not mint signed URL")
    thumb_key = j.get("result_thumbnail_key") or _strip_public_prefix(j.get("result_thumbnail_url") or "")
    return {
        "url": url, "expires_in": SIGNED_URL_TTL_SECONDS,
        "format": "vertical" if use_vert else "wide",
        "thumbnail_url": await _sign_or_passthrough(thumb_key) if thumb_key else None,
        "has_vertical": bool(j.get("result_vertical_video_key") or j.get("result_vertical_video_url")),
    }

@router.get("/share/{slug}")
async def share_page(slug: str):
    """Public share-page payload. Slug is 10 random hex chars set at job
    completion — unguessable enough that it acts as the access token.
    Returns BOTH widescreen and vertical signed URLs when available; the
    public /trailer/:slug page picks based on viewport (mobile→vertical)."""
    j = await db.photo_trailer_jobs.find_one(
        {"public_share_slug": slug, "status": "COMPLETED",
         "deleted_at": {"$exists": False}})
    if not j: raise HTTPException(404, "Trailer not found")
    key = j.get("result_video_key") or _strip_public_prefix(j.get("result_video_url") or "")
    if not key: raise HTTPException(404, "Video unavailable")
    if not j.get("result_video_key") and key:
        await db.photo_trailer_jobs.update_one({"_id": j["_id"]},
                                                {"$set": {"result_video_key": key}})
    vert_key = j.get("result_vertical_video_key") or _strip_public_prefix(j.get("result_vertical_video_url") or "")
    thumb_key = j.get("result_thumbnail_key") or _strip_public_prefix(j.get("result_thumbnail_url") or "")
    video_url = await _sign_or_passthrough(key)
    vertical_url = await _sign_or_passthrough(vert_key) if vert_key else None
    thumb_url = await _sign_or_passthrough(thumb_key) if thumb_key else None
    creator_name = "A Visionary Suite creator"
    try:
        u = await db.users.find_one({"id": j.get("user_id")}, {"name": 1, "_id": 0})
        if u and u.get("name"): creator_name = u["name"].split()[0]
    except Exception: pass
    try:
        await db.photo_trailer_jobs.update_one({"_id": j["_id"]},
            {"$inc": {"share_view_count": 1}})
    except Exception: pass
    tpl = TEMPLATES.get(j.get("template_id") or "", {})
    return {
        "slug": slug, "video_url": video_url, "vertical_video_url": vertical_url,
        "thumbnail_url": thumb_url,
        "title": tpl.get("title") or j.get("template_name") or "AI Movie Trailer",
        "duration_seconds": j.get("duration_target_seconds"),
        "creator_first_name": creator_name,
        "creator_plan": j.get("plan_tier_at_creation") or "FREE",
        "expires_in": SIGNED_URL_TTL_SECONDS,
    }

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
    """Move the job to a new stage AND update the progress heartbeat. The
    `last_progress_at` + `last_stage_change_at` fields tell the janitor this
    job is alive; without them, slow scene-gens were getting reaped at 5min."""
    upd = {
        "current_stage": stage,
        "progress_percent": STAGE_PCT.get(stage, 0),
        "updated_at": _now(),
        "last_progress_at": _now(),
        "last_stage_change_at": _now(),
        # Clear any previous transient progress message — the new stage starts fresh
        "progress_message": None,
    }
    upd.update(extra)
    await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": upd})

async def _heartbeat(job_id: str, message: Optional[str] = None):
    """Mid-stage liveness ping — call from inside long-running stages so the
    janitor's heartbeat protection knows the job is making progress.
    Optional `message` populates `progress_message` (e.g. "Retrying scene 4/6")
    which the frontend renders next to the stage name."""
    upd = {"last_progress_at": _now(), "updated_at": _now()}
    if message is not None:
        upd["progress_message"] = message
    try:
        await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": upd})
    except Exception:
        pass  # heartbeat MUST never break the pipeline

async def _fail(job_id: str, code: str, msg: str):
    j = await db.photo_trailer_jobs.find_one({"_id": job_id})
    if not j: return
    log.error(f"[trailer {job_id}] FAIL {code}: {msg}")
    # Preserve the stage we were ON when failure happened — without this, the
    # admin dashboard cannot tell GENERATING_SCENES failures from RENDERING ones.
    failure_stage = j.get("current_stage") or "UNKNOWN"
    if failure_stage == "FAILED":  # double-fail edge case
        failure_stage = j.get("failure_stage") or "UNKNOWN"
    await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {
        "status": "FAILED", "current_stage": "FAILED",
        "failure_stage": failure_stage,
        "error_code": code,
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
    so the main FastAPI event loop stays responsive for other users.

    RELIABILITY SPRINT: 3 attempts with 2s/5s/10s backoff (was 2 attempts with
    no backoff). This is the inner retry — the outer per-scene retry in the
    pipeline orchestrator wraps this to give a true "retry only the failed
    scene, not the whole trailer" behavior."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    refs = [ImageContent(hero_b64)]
    if villain_b64: refs.append(ImageContent(villain_b64))
    full_prompt = (
        f"{visual_prompt}\n\nCRITICAL: The hero in this scene must visually match the FIRST reference photo's "
        "face, age, ethnicity, hair and overall identity. Cinematic 16:9 framing. Photorealistic film still. "
        "Strong dramatic lighting. No on-screen text. No watermarks. No logos."
    )
    BACKOFF_SECONDS = [2, 5, 10]

    def _sync_call() -> bytes:
        last_err = None
        import time as _t
        for attempt in range(3):
            try:
                chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message="You generate a single cinematic image.")
                chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
                msg = UserMessage(text=full_prompt, file_contents=refs)
                _txt, images = asyncio.run(chat.send_message_multimodal_response(msg))
                if images and images[0].get("data"):
                    return base64.b64decode(images[0]["data"])
                last_err = RuntimeError(f"empty response (txt={(_txt or '')[:100]})")
            except Exception as e:
                last_err = e
                log.warning(f"[scene_image] attempt {attempt+1}/3 failed for {session_id}: {type(e).__name__}: {str(e)[:200]}")
            if attempt < 2:
                _t.sleep(BACKOFF_SECONDS[attempt])
        raise last_err or RuntimeError("image gen failed after 3 retries")

    return await asyncio.get_event_loop().run_in_executor(IMAGE_EXECUTOR, _sync_call)

async def _tts(narration: str, voice: str) -> bytes:
    """OpenAI TTS via emergentintegrations — runs on the AUDIO_EXECUTOR.
    Light retry on transient upstream issues (rate limit, network reset)."""
    from emergentintegrations.llm.openai import OpenAITextToSpeech

    def _sync_call() -> bytes:
        last = None
        for attempt in range(3):
            try:
                tts = OpenAITextToSpeech(api_key=EMERGENT_LLM_KEY)
                return asyncio.run(tts.generate_speech(
                    text=narration[:4000], model="tts-1", voice=voice))
            except Exception as e:
                last = e
                # Bounded backoff so 6 parallel TTS calls don't all hammer at once
                import time as _t
                _t.sleep(0.6 * (attempt + 1))
        raise last  # type: ignore[misc]

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
    we drive `d=frames` so the move plays exactly once across the clip.

    All motion rates are normalized against `last` (= f-1) so the camera
    traverses its FULL valid range over the clip duration — never running
    out of pan room and clamping mid-clip (the bug that caused the second
    half of pan styles to freeze in v2)."""
    f = max(2, int(frames))
    last = f - 1  # final output frame index — denominator for normalised pans
    # Zoom ramps: total delta over the clip (e.g. 0.22 = 1.00→1.22).
    z_in   = f"1.0+on*{0.22/last:.6f}"   # slow_push: 1.00 → 1.22
    z_in_h = f"1.0+on*{0.30/last:.6f}"   # push_to_face: 1.00 → 1.30
    z_out  = f"1.32-on*{0.22/last:.6f}"  # pull_back: 1.32 → 1.10
    z_drift= f"1.0+on*{0.20/last:.6f}"   # diagonal_drift: 1.00 → 1.20
    # Pan factors stay in [0, 1] of the available range (iw-iw/zoom).
    px_full   = f"on/{last}"                # 0 → 1
    px_invert = f"(1-on/{last})"            # 1 → 0
    px_drift  = f"(0.20+on*{0.55/last:.6f})" # 0.20 → 0.75 — gentle off-axis
    py_drift  = f"(0.30+on*{0.40/last:.6f})" # 0.30 → 0.70
    styles = [
        # 0: slow_push — center-anchored zoom-in
        f"zoompan=z='{z_in}':d={f}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25",
        # 1: pan_right — fixed zoom, full left→right traversal
        f"zoompan=z='1.20':d={f}:x='{px_full}*(iw-iw/zoom)':y='(ih-ih/zoom)/2':s=1280x720:fps=25",
        # 2: pull_back — center-anchored zoom-out from 1.32 to 1.10
        f"zoompan=z='{z_out}':d={f}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25",
        # 3: push_to_face — zoom-in anchored on upper third (face area)
        f"zoompan=z='{z_in_h}':d={f}:x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':s=1280x720:fps=25",
        # 4: pan_left — fixed zoom, full right→left traversal
        f"zoompan=z='1.20':d={f}:x='{px_invert}*(iw-iw/zoom)':y='(ih-ih/zoom)/2':s=1280x720:fps=25",
        # 5: diagonal_drift — gentle zoom + bounded diagonal sweep
        f"zoompan=z='{z_drift}':d={f}:x='{px_drift}*(iw-iw/zoom)':y='{py_drift}*(ih-ih/zoom)':s=1280x720:fps=25",
        # 6: handheld_shake — fixed zoom + sub-pixel sin/cos shake
        f"zoompan=z='1.22':d={f}:x='iw/2-(iw/zoom/2)+sin(on/2.8)*22':y='ih/2-(ih/zoom/2)+cos(on/2.4)*14':s=1280x720:fps=25",
        # 7: vertical_reveal — fixed zoom, full bottom→top reveal
        f"zoompan=z='1.22':d={f}:x='iw/2-(iw/zoom/2)':y='{px_invert}*(ih-ih/zoom)':s=1280x720:fps=25",
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

        # Audio chain: pad TTS with silence so the audio matches `dur`.
        # Without this, `-shortest` would truncate the per-scene clip to the
        # narration length (~3s), so a 60s trailer (6×10s scenes) would
        # render as ~20s. apad makes the audio stream infinite, atrim caps
        # it at dur. Final clip length is governed by `-t {dur}` only.
        af_chain = (
            f"apad,atrim=duration={dur},"
            f"afade=t=in:st=0:d=0.20,"
            f"afade=t=out:st={max(0.0, dur-0.30):.2f}:d=0.30"
        )

        await _ffmpeg([ffmpeg, "-y", "-loop", "1", "-i", img, "-i", aud,
                     "-vf", vf, "-af", af_chain,
                     "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-b:a", "128k", "-r", "25", "-t", f"{dur}",
                     "-movflags", "+faststart", clip])
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
    # Watermark + optional music + provenance metadata embedded in MP4 container
    final = os.path.join(tmp, "final.mp4")
    wm_filter = ("[0:v]drawtext=text='Visionary Suite':fontcolor=white@0.65:fontsize=18:"
                 "x=w-tw-22:y=h-th-22:box=1:boxcolor=black@0.25:boxborderw=8[v]")
    # Provenance metadata — forensic + brand tag baked into the container.
    # Lets reviewers / takedown bots identify origin even if the file is
    # re-uploaded / renamed without re-encoding.
    job_id_short = str(job.get("_id", ""))[:8]
    meta_args = [
        "-metadata", "title=Created with Visionary Suite AI",
        "-metadata", "artist=Visionary Suite",
        "-metadata", "comment=AI-generated personalized trailer",
        "-metadata", "copyright=© Visionary Suite — visionary-suite.com",
        "-metadata", "encoded_by=visionary-suite/photo-trailer-v2",
        "-metadata", f"description=Photo Trailer Job {job_id_short} | {job.get('template_id', 'custom')}",
    ]
    if music_path:
        await _ffmpeg([ffmpeg, "-y", "-i", stitched, "-stream_loop", "-1", "-i", music_path,
                     "-filter_complex", wm_filter + ";[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=shortest[a]",
                     "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-shortest",
                     *meta_args, "-movflags", "+faststart", final])
    else:
        await _ffmpeg([ffmpeg, "-y", "-i", stitched, "-vf", "drawtext=text='Visionary Suite':fontcolor=white@0.65:fontsize=18:"
                     "x=w-tw-22:y=h-th-22:box=1:boxcolor=black@0.25:boxborderw=8",
                     "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                     "-c:a", "copy", *meta_args, "-movflags", "+faststart", final])
    return final


# ─── 9:16 vertical auto-cut ──────────────────────────────────────────────────
# Distribution > polish. Reels / Shorts / TikTok / WhatsApp Status all
# require 9:16. We post-process the finished 16:9 master into a 1080x1920
# vertical asset with the typical "blurred-bg + centered hero" treatment so
# faces are NEVER stretched. Subtitles ride in the safe band (250-1570 px).
async def _render_vertical_from_widescreen(source_mp4: str, out_mp4: str) -> None:
    """Bounded re-encode pass: 1080x1920, blurred BG + scaled FG overlay,
    fall-back to 720x1280 if the encoder rejects the higher res."""
    # Use /usr/bin/ffmpeg — it ships with drawtext (libfreetype). The
    # /usr/local/bin/ffmpeg build does not include drawtext so the watermark
    # filter graph would fail there.
    ffmpeg = "/usr/bin/ffmpeg" if os.path.exists("/usr/bin/ffmpeg") else "ffmpeg"
    fc = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=24:1,eq=brightness=-0.10:saturation=0.90[bg];"
        "[0:v]scale=1080:-2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
            "drawtext=text='Visionary Suite':fontcolor=white@0.65:fontsize=28:"
            "x=(w-tw)/2:y=h-110:box=1:boxcolor=black@0.30:boxborderw=10[v]"
    )
    args = [
        ffmpeg, "-y", "-i", source_mp4,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-metadata", "title=Created with Visionary Suite AI",
        "-metadata", "comment=AI-generated personalized trailer · 9:16 vertical",
        "-metadata", "copyright=© Visionary Suite — visionary-suite.com",
        "-movflags", "+faststart",
        out_mp4,
    ]
    try:
        await _ffmpeg(args)
    except Exception:
        log.warning("vertical 1080x1920 encode failed; retrying at 720x1280")
        fc_lo = fc.replace("1080:1920", "720:1280").replace("1080:-2", "720:-2")
        args[args.index("-filter_complex") + 1] = fc_lo
        await _ffmpeg(args)


async def _run_pipeline(job_id: str):
    """Two-lane pipeline orchestrator.

    PREMIUM jobs: try _PRIORITY_GATE first (instant if available, no fight
    against standard-tier traffic). Fall through to _STANDARD_GATE if the
    priority lane is full — better to share a slot than to wait forever.
    Every job records `queue_wait_seconds` so we can prove Premium waits
    are actually shorter."""
    job = await db.photo_trailer_jobs.find_one({"_id": job_id}, {"is_priority": 1, "user_id": 1})
    is_priority = bool(job and job.get("is_priority"))
    enqueue_ts = time.time()
    gate_lane = "standard"
    # Premium → race priority + standard; whichever frees first wins.
    if is_priority:
        # asyncio.wait on two semaphore acquires: take the first that succeeds.
        prio_task = asyncio.create_task(_PRIORITY_GATE.acquire())
        std_task  = asyncio.create_task(_STANDARD_GATE.acquire())
        done, pending = await asyncio.wait(
            [prio_task, std_task], return_when=asyncio.FIRST_COMPLETED)
        # Cancel the loser; if it has already acquired we must release.
        for t in pending:
            t.cancel()
            try: await t
            except (asyncio.CancelledError, Exception): pass
            else:
                # Rare race: it acquired between FIRST_COMPLETED and cancel —
                # release immediately so we don't leak a slot.
                if t is prio_task: _PRIORITY_GATE.release()
                else: _STANDARD_GATE.release()
        if prio_task in done and not prio_task.cancelled():
            gate_lane = "priority"
            try:
                wait_secs = round(time.time() - enqueue_ts, 2)
                await db.photo_trailer_jobs.update_one(
                    {"_id": job_id},
                    {"$set": {"queue_wait_seconds": wait_secs, "queue_lane": gate_lane}},
                )
                await _run_pipeline_inner(job_id)
            finally:
                _PRIORITY_GATE.release()
            return
        # else: standard gate fell through
        gate_lane = "standard"
        try:
            wait_secs = round(time.time() - enqueue_ts, 2)
            await db.photo_trailer_jobs.update_one(
                {"_id": job_id},
                {"$set": {"queue_wait_seconds": wait_secs, "queue_lane": gate_lane}},
            )
            await _run_pipeline_inner(job_id)
        finally:
            _STANDARD_GATE.release()
        return

    # Standard (FREE / PAID) — fair queue, no priority access.
    async with _STANDARD_GATE:
        wait_secs = round(time.time() - enqueue_ts, 2)
        await db.photo_trailer_jobs.update_one(
            {"_id": job_id},
            {"$set": {"queue_wait_seconds": wait_secs, "queue_lane": "standard"}},
        )
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

        # Image + voice generation per scene (parallelised, with per-scene retry)
        await _set_stage(job_id, "GENERATING_SCENES")
        scene_payload: List[dict] = []
        per_scene_dur = max(3.0, j["duration_target_seconds"] / max(1, len(scenes)))
        total_scenes = len(scenes)

        async def _scene_assets(idx: int, sc: dict) -> dict:
            """Image step. Inner _gen_scene_image already retries 3x with
            backoff; outer retry here handles provider-level rate limits."""
            await _heartbeat(job_id, f"Generating scene {idx+1}/{total_scenes}")
            try:
                img_bytes = await _gen_scene_image(
                    sc["visual"], hero_b64, villain_b64,
                    session_id=f"img_{job_id}_{idx}",
                )
            except Exception as first_err:
                # Outer per-scene retry: provider-level errors that survived
                # 3 inner retries get ONE more shot here, with a fresh session
                # id so any rate-limit cool-down has a chance to clear.
                log.warning(f"[trailer {job_id}] scene {idx+1} provider error → outer retry: {first_err}")
                await _heartbeat(job_id, f"Retrying scene {idx+1}/{total_scenes}")
                await asyncio.sleep(3)
                img_bytes = await _gen_scene_image(
                    sc["visual"], hero_b64, villain_b64,
                    session_id=f"img_retry_{job_id}_{idx}",
                )
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
            # SPEED: kick off voiceover for THIS scene immediately. The TTS
            # call runs concurrently with sibling image-gens still in flight,
            # cutting wall-clock by ~25-40% on a 6-scene trailer (we no
            # longer wait for the whole image batch before any voice work).
            await _heartbeat(job_id, f"Recording voiceover {idx+1}/{total_scenes}")
            audio = await _tts(sc["narration"], j.get("narrator_style") or "alloy")
            audio_path = os.path.join(tmpdir, f"audio_{idx}.mp3")
            with open(audio_path, "wb") as f: f.write(audio)
            return {
                "idx": idx,
                "image_path": img_path,
                "narration": sc["narration"],
                "audio_path": audio_path,
                "duration": per_scene_dur,
            }

        try:
            # gather with return_exceptions so one failed scene doesn't cancel
            # the others — we tally what failed and report which scene index
            # to the user instead of dropping the whole trailer.
            results = await asyncio.gather(
                *[_scene_assets(i, sc) for i, sc in enumerate(scenes)],
                return_exceptions=True,
            )
            failed_idx = [i for i, r in enumerate(results) if isinstance(r, Exception)]
            if failed_idx:
                # Log each failure precisely — diagnostics will show which
                # scenes are pathological.
                for i in failed_idx:
                    log.error(f"[trailer {job_id}] scene {i+1} FAILED after retries: "
                              f"{type(results[i]).__name__}: {str(results[i])[:300]}")
                return await _fail(
                    job_id, "IMAGE_GEN_FAIL",
                    f"Couldn't render scene {failed_idx[0]+1}/{total_scenes} after retries. Please retry.",
                )
            scene_payload = list(results)
        except Exception:
            log.exception(f"[trailer {job_id}] image gen gather crashed")
            return await _fail(job_id, "IMAGE_GEN_FAIL", "Some scenes couldn't render. Please retry.")

        # SPEED: voiceover already happened inline per scene above (image+TTS
        # pipeline). We still flip through the GENERATING_VOICEOVER stage so
        # the UI progress bar progresses linearly and the dashboard's stage
        # accounting stays consistent — but the actual TTS work is done.
        await _set_stage(job_id, "GENERATING_VOICEOVER")

        # Render
        await _set_stage(job_id, "ADDING_MUSIC")
        await _set_stage(job_id, "RENDERING_TRAILER")
        await _heartbeat(job_id, "Final render — stitching scenes, adding music, watermark")
        try:
            scene_payload.sort(key=lambda p: p["idx"])
            final_path = await _render_trailer(j, scene_payload, tmpdir)
        except Exception as e:
            log.exception(f"render failed for {job_id}")
            return await _fail(job_id, "RENDER_FAIL", "Final render hit a hiccup. Please retry.")

        # Upload widescreen master
        with open(final_path, "rb") as f: video_bytes = f.read()
        ok, video_url, video_key = await _upload_video_bytes(video_bytes, f"trailer_{job_id}.mp4", user_id)
        if not ok:
            return await _fail(job_id, "UPLOAD_FAIL", "Storage upload failed. Please retry.")

        # 9:16 vertical companion (Reels / Shorts / TikTok / WhatsApp Status).
        # Bounded second pass — runs on the same RENDER_EXECUTOR. If the
        # encode fails we DO NOT fail the whole job; the widescreen master
        # is the contract. The card will simply hide the vertical button.
        vertical_url = None; vertical_key = None
        try:
            vert_path = os.path.join(tmpdir, "vertical.mp4")
            t_v = time.time()
            await _render_vertical_from_widescreen(final_path, vert_path)
            log.info(f"[trailer {job_id}] vertical render took {time.time()-t_v:.1f}s")
            with open(vert_path, "rb") as f: vert_bytes = f.read()
            okv, v_url, v_key = await _upload_video_bytes(vert_bytes, f"trailer_{job_id}_vertical.mp4", user_id)
            if okv:
                vertical_url, vertical_key = v_url, v_key
        except Exception as e:
            log.warning(f"[trailer {job_id}] vertical cut failed (widescreen still saved): {e}")

        # Thumbnail = first scene image
        thumb_url = None; thumb_key = None
        try:
            with open(scene_payload[0]["image_path"], "rb") as f: tb = f.read()
            ok2, thumb_url_or_key = await upload_image_bytes(tb, f"trailer_{job_id}_thumb.jpg", project_id=f"phototrailer/{user_id}/results")
            if ok2:
                thumb_url = thumb_url_or_key
                thumb_key = _strip_public_prefix(thumb_url_or_key)
        except Exception:
            pass

        # Record output
        output_doc_id = str(uuid.uuid4())
        await db.photo_trailer_outputs.insert_one({
            "_id": output_doc_id, "job_id": job_id, "user_id": user_id,
            "video_storage_key": video_key, "video_storage_url": video_url,
            "vertical_video_storage_key": vertical_key, "vertical_video_storage_url": vertical_url,
            "thumbnail_storage_key": thumb_key, "thumbnail_storage_url": thumb_url,
            "duration_seconds": j["duration_target_seconds"], "resolution": "1280x720",
            "vertical_resolution": "1080x1920" if vertical_url else None,
            "file_size": len(video_bytes), "watermark_applied": True, "end_card_applied": True,
            "download_token_required": True, "created_at": _now(),
        })
        slug = uuid.uuid4().hex[:10]
        await db.photo_trailer_jobs.update_one({"_id": job_id}, {"$set": {
            "status": "COMPLETED", "current_stage": "COMPLETED", "progress_percent": 100,
            "result_video_asset_id": output_doc_id,
            "result_thumbnail_asset_id": output_doc_id if thumb_key else None,
            "result_video_url": video_url, "result_video_key": video_key,
            "result_vertical_video_url": vertical_url, "result_vertical_video_key": vertical_key,
            "result_thumbnail_url": thumb_url, "result_thumbnail_key": thumb_key,
            "public_share_slug": slug, "completed_at": _now(), "updated_at": _now(),
        }})

        # Fire `first_trailer_created` exactly once per user — the count of
        # OTHER completed jobs for this user must be 0 before this insert.
        # Cheap check; runs once per pipeline so no hot path concern.
        try:
            other_completed = await db.photo_trailer_jobs.count_documents({
                "user_id": user_id, "status": "COMPLETED", "_id": {"$ne": job_id},
            })
            if other_completed == 0:
                await _emit("first_trailer_created", user_id, {
                    "job_id": job_id, "template": j.get("template_id"),
                    "duration": j.get("duration_target_seconds"),
                    "creator_plan": j.get("plan_tier_at_creation"),
                })
        except Exception: pass
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


async def _upload_video_bytes(data: bytes, name: str, user_id: str) -> tuple:
    """Upload an in-memory MP4 to R2 (or local fallback).
    Returns (ok, public_url, storage_key) — the storage_key is used to
    mint short-lived presigned playback URLs (signed_stream endpoint)."""
    from services.cloudflare_r2_storage import get_r2_storage
    service = get_r2_storage()
    if not service or not getattr(service, "_client", None):
        try:
            os.makedirs("/app/backend/static/trailer_outputs", exist_ok=True)
            local = f"/app/backend/static/trailer_outputs/{name}"
            with open(local, "wb") as f: f.write(data)
            return True, f"/static/trailer_outputs/{name}", f"local/{name}"
        except Exception as e:
            return False, str(e), ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as t:
            t.write(data); local_path = t.name
        ok, url, key = await service.upload_file(local_path, asset_type="video",
                                                 project_id=f"phototrailer/{user_id}/results",
                                                 custom_filename=name)
        try: os.unlink(local_path)
        except Exception: pass
        return ok, (url or key), key
    except Exception as e:
        return False, str(e), ""



# ═════════════════════════ STALE-JOB JANITOR ════════════════════════════════════
# Reaps Photo Trailer jobs stuck in PROCESSING > duration-tier-aware threshold.
# Hardens against backend restart drops + orphaned pipelines (e.g. a worker
# crash mid-render). Marks them FAILED with STALE_PIPELINE and refunds the
# user's credits exactly once. Idempotent — re-running is safe.
#
# RELIABILITY SPRINT (2026-04-29 founder directive):
#   1. Dynamic stale thresholds per duration tier (was hard-coded 5min for all
#      tiers — that's why 50% of fails were JANITOR_STALE on 60/90s renders
#      that legitimately take 4+ minutes).
#   2. Heartbeat protection — if last_progress_at < HEARTBEAT_LIVE_SECONDS,
#      the job is alive and the janitor MUST NOT reap it.
#   3. Auto-recovery — first STALE_PIPELINE auto-requeues exactly once,
#      preserving credits. Only the second stale → real refund + fail.

# Per-duration stale thresholds (founder directive):
#   20s trailer  = 10 min
#   45-60s       = 20 min
#   90s          = 35 min
STALE_MIN_BY_DURATION = {
    20: 10,
    45: 20,
    60: 20,
    90: 35,
}
STALE_THRESHOLD_DEFAULT_MIN = 15  # used when duration_target_seconds is missing
HEARTBEAT_LIVE_SECONDS = 180  # 3 min — if progress newer than this, job is alive
JANITOR_INTERVAL_SECONDS = 120
MAX_AUTO_REQUEUES = 1  # stale-recovery: each job gets ONE free auto-retry
STALE_THRESHOLD_MINUTES = STALE_THRESHOLD_DEFAULT_MIN  # back-compat for older tests

def _stale_threshold_for(duration_seconds: Optional[int]) -> int:
    """Pick the right stale-cutoff for this job's duration tier."""
    if duration_seconds is None:
        return STALE_THRESHOLD_DEFAULT_MIN
    return STALE_MIN_BY_DURATION.get(int(duration_seconds), STALE_THRESHOLD_DEFAULT_MIN)

async def _reap_stale_pipelines() -> Dict[str, Any]:
    """Single sweep — find + reap PROCESSING jobs older than their duration-tier
    threshold AND with no recent progress heartbeat. First-time stale jobs are
    auto-requeued (credits preserved). Second-time stale → refund + FAIL.

    Returns metrics dict for logging/testing. Atomic + idempotent: status/retry
    transitions are gated on prior values, so concurrent janitor sweeps cannot
    double-refund or double-requeue."""
    now_dt = datetime.now(timezone.utc)
    reaped, refunded_total, refund_failures, skipped_already_terminal = 0, 0, 0, 0
    auto_requeued, skipped_alive_heartbeat = 0, 0

    # Pull anything PROCESSING old enough to MAYBE be stale. The smallest
    # possible threshold is the smallest tier (10min for 20s tier), so we
    # use that as a cheap DB-side prefilter — anything younger than that
    # cannot possibly be stale regardless of duration tier.
    min_threshold_min = min(STALE_MIN_BY_DURATION.values())
    db_prefilter_cutoff = (now_dt - timedelta(minutes=min_threshold_min)).isoformat()
    # Cap per-sweep work so a backlog of stuck jobs (e.g. after a backend
    # restart) cannot thunder the orchestrator with simultaneous requeues.
    SWEEP_LIMIT = 50
    cursor = db.photo_trailer_jobs.find({
        "status": "PROCESSING",
        "started_at": {"$lt": db_prefilter_cutoff, "$ne": None},
    }).limit(SWEEP_LIMIT)
    async for j in cursor:
        jid = j["_id"]
        # 1. Per-duration threshold check
        threshold_min = _stale_threshold_for(j.get("duration_target_seconds"))
        started_iso = j.get("started_at")
        if not started_iso:
            continue
        try:
            started_dt = datetime.fromisoformat(started_iso)
        except Exception:
            continue
        age_min = (now_dt - started_dt).total_seconds() / 60.0
        if age_min < threshold_min:
            continue  # not old enough for its tier yet

        # 2. Heartbeat protection — alive jobs must not be reaped.
        last_prog = j.get("last_progress_at") or j.get("updated_at")
        if last_prog:
            try:
                last_prog_dt = datetime.fromisoformat(last_prog)
                if (now_dt - last_prog_dt).total_seconds() < HEARTBEAT_LIVE_SECONDS:
                    skipped_alive_heartbeat += 1
                    continue
            except Exception:
                pass

        # 3. Auto-recovery: first stale gets a free requeue.
        retry_count = int(j.get("retry_count") or 0)
        if retry_count < MAX_AUTO_REQUEUES:
            # Atomic transition: PROCESSING + retry_count==N → QUEUED + retry_count==N+1
            upd = await db.photo_trailer_jobs.update_one(
                {"_id": jid, "status": "PROCESSING", "retry_count": {"$in": [None, retry_count]}},
                {"$set": {
                    "status": "QUEUED",
                    "current_stage": "VALIDATING",
                    "progress_percent": 0,
                    "progress_message": "Recovering stalled job — auto-retrying",
                    "started_at": None,  # reset so the next sweep computes a fresh age
                    "last_progress_at": _now(),
                    "last_stage_change_at": _now(),
                    "updated_at": _now(),
                    "retry_count": retry_count + 1,
                    "auto_requeued_at": _now(),
                }},
            )
            if upd.modified_count == 0:
                skipped_already_terminal += 1
                continue
            # Fire and forget — orchestrator will re-run the pipeline.
            asyncio.create_task(_run_pipeline(jid))
            try:
                await _emit("photo_trailer_auto_requeued", j["user_id"],
                            {"job_id": jid, "retry_count": retry_count + 1, "age_min": round(age_min, 1)})
            except Exception:
                pass
            log.warning(
                f"[trailer-janitor] AUTO-REQUEUED stale job {jid} user={j['user_id']} "
                f"template={j.get('template_id')} age={round(age_min,1)}min retry={retry_count+1}"
            )
            auto_requeued += 1
            continue

        # 4. Already retried → real failure with refund (atomic transition guards refund).
        upd = await db.photo_trailer_jobs.update_one(
            {"_id": jid, "status": "PROCESSING"},
            {"$set": {
                "status": "FAILED", "current_stage": "FAILED",
                "failure_stage": "JANITOR_STALE",
                "error_code": "STALE_PIPELINE",
                "error_message": "Trailer didn't complete in time. Credits refunded — please retry.",
                "failed_at": _now(), "updated_at": _now(),
            }},
        )
        if upd.modified_count == 0:
            skipped_already_terminal += 1
            continue
        charged = j.get("charged_credits") or 0
        prior_refund = j.get("refunded_credits") or 0
        if charged > 0 and prior_refund == 0:
            try:
                await add_credits(j["user_id"], charged, f"Refund stale trailer {jid}", tx_type="REFUND")
                await db.photo_trailer_jobs.update_one(
                    {"_id": jid, "refunded_credits": 0},
                    {"$set": {"refunded_credits": charged}},
                )
                refunded_total += charged
                log.warning(
                    f"[trailer-janitor] Reaped stale job {jid} user={j['user_id']} "
                    f"template={j.get('template_id')} age={round(age_min,1)}min "
                    f"retry={retry_count} refunded={charged}cr"
                )
            except Exception as e:
                refund_failures += 1
                log.error(f"[trailer-janitor] Refund failed for {jid}: {e}")
        else:
            log.warning(
                f"[trailer-janitor] Reaped stale job {jid} user={j['user_id']} "
                f"template={j.get('template_id')} age={round(age_min,1)}min retry={retry_count} (no refund needed)"
            )
        try:
            await _emit("photo_trailer_generation_failed", j["user_id"],
                        {"job_id": jid, "code": "STALE_PIPELINE", "via": "janitor"})
        except Exception:
            pass
        reaped += 1

    return {
        "reaped": reaped,
        "auto_requeued": auto_requeued,
        "refunded_credits_total": refunded_total,
        "refund_failures": refund_failures,
        "skipped_alive_heartbeat": skipped_alive_heartbeat,
        "skipped_already_terminal": skipped_already_terminal,
        "swept_at": now_dt.isoformat(),
    }


async def stale_pipeline_janitor_loop():
    """Forever loop wired up at server startup. Runs `_reap_stale_pipelines`
    every JANITOR_INTERVAL_SECONDS seconds. Survives individual sweep errors.
    Also runs the source-photo retention sweep on the same cadence (it's
    cheap when there's nothing to purge)."""
    log.info(f"[trailer-janitor] starting (every {JANITOR_INTERVAL_SECONDS}s, "
             f"thresholds={STALE_MIN_BY_DURATION}min, heartbeat={HEARTBEAT_LIVE_SECONDS}s)")
    await asyncio.sleep(15)
    while True:
        try:
            result = await _reap_stale_pipelines()
            if result["reaped"] > 0:
                log.info(f"[trailer-janitor] sweep result: {result}")
        except Exception as e:
            log.exception(f"[trailer-janitor] sweep crashed: {e}")
        try:
            purged = await _purge_old_source_photos()
            if purged.get("purged", 0) > 0:
                log.info(f"[trailer-retention] purged {purged}")
        except Exception as e:
            log.exception(f"[trailer-retention] sweep crashed: {e}")
        await asyncio.sleep(JANITOR_INTERVAL_SECONDS)


# ─── Trust & Legal: source photo retention sweep ─────────────────────────────
PHOTO_RETENTION_DAYS = int(os.environ.get("PHOTO_TRAILER_PHOTO_RETENTION_DAYS", "7"))

async def _purge_old_source_photos() -> Dict[str, Any]:
    """Find jobs that finished > PHOTO_RETENTION_DAYS days ago and purge
    their source photo assets from R2. Bounded sweep — at most 200 assets
    per pass so a backlog can't stall the loop."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=PHOTO_RETENTION_DAYS)).isoformat()
    purged = 0
    failed = 0
    skipped = 0
    asset_ids: List[str] = []
    sessions_seen: set = set()
    cursor = db.photo_trailer_jobs.find(
        {"status": {"$in": ["COMPLETED", "FAILED", "CANCELLED"]},
         "$or": [
             {"completed_at": {"$lt": cutoff, "$ne": None}},
             {"failed_at":    {"$lt": cutoff, "$ne": None}},
             {"updated_at":   {"$lt": cutoff}, "status": "CANCELLED"},
         ]},
        {"upload_session_id": 1, "_id": 1},
    ).limit(50)
    async for j in cursor:
        sid = j.get("upload_session_id")
        if sid: sessions_seen.add(sid)

    if not sessions_seen:
        return {"purged": 0, "failed": 0, "skipped": 0, "sessions_swept": 0}

    assets_cursor = db.photo_trailer_assets.find(
        {"upload_session_id": {"$in": list(sessions_seen)},
         "deleted_at": {"$exists": False}},
    ).limit(200)
    from services.cloudflare_r2_storage import get_r2_storage
    r2 = get_r2_storage()
    async for a in assets_cursor:
        aid = a["_id"]
        key = a.get("storage_key")
        if not key:
            skipped += 1; continue
        ok = False
        if r2:
            try:
                ok = await r2.delete_file(key)
            except Exception as e:
                log.warning(f"[trailer-retention] r2 delete {key} failed: {e}")
        await db.photo_trailer_assets.update_one(
            {"_id": aid, "deleted_at": {"$exists": False}},
            {"$set": {"deleted_at": _now(), "r2_purge_ok": bool(ok)}},
        )
        if ok: purged += 1
        else: failed += 1
        asset_ids.append(aid)

    return {
        "purged": purged, "failed": failed, "skipped": skipped,
        "sessions_swept": len(sessions_seen), "asset_ids_processed": len(asset_ids),
        "retention_days": PHOTO_RETENTION_DAYS, "cutoff": cutoff,
    }


@router.post("/admin/janitor/run-now")
async def admin_run_janitor(user: dict = Depends(get_admin_user)):
    """Admin manual trigger — used by tests + ops."""
    return await _reap_stale_pipelines()


@router.post("/admin/retention/run-now")
async def admin_run_retention(user: dict = Depends(get_admin_user)):
    """Admin manual trigger for the photo retention sweep."""
    return await _purge_old_source_photos()


@router.get("/admin/queue-stats")
async def admin_queue_stats(user: dict = Depends(get_admin_user), days: int = Query(7, ge=1, le=90)):
    """Premium priority queue metrics — proves the lane separation is honest.
    Returns avg/p50/p95 wait time per plan tier over the last `days`.
    Founder acceptance: Premium waits MATERIALLY lower than free."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipe = [
        {"$match": {
            "queue_wait_seconds": {"$exists": True},
            "created_at": {"$gte": cutoff},
        }},
        {"$group": {
            "_id": {"plan": "$plan_tier_at_creation", "lane": "$queue_lane"},
            "n": {"$sum": 1},
            "avg_wait_s": {"$avg": "$queue_wait_seconds"},
            "max_wait_s": {"$max": "$queue_wait_seconds"},
            "min_wait_s": {"$min": "$queue_wait_seconds"},
        }},
    ]
    rows = []
    async for d in db.photo_trailer_jobs.aggregate(pipe):
        rows.append({
            "plan": (d["_id"] or {}).get("plan") or "UNKNOWN",
            "lane": (d["_id"] or {}).get("lane") or "standard",
            "samples": d["n"],
            "avg_wait_seconds": round(d["avg_wait_s"] or 0, 2),
            "max_wait_seconds": round(d["max_wait_s"] or 0, 2),
            "min_wait_seconds": round(d["min_wait_s"] or 0, 2),
        })
    # Aggregate per plan
    by_plan = {}
    for r in rows:
        p = r["plan"]
        b = by_plan.setdefault(p, {"plan": p, "samples": 0, "avg_wait_seconds": 0.0})
        b["samples"] += r["samples"]
        b["avg_wait_seconds"] = (
            (b["avg_wait_seconds"] * (b["samples"] - r["samples"])
             + r["avg_wait_seconds"] * r["samples"]) / max(1, b["samples"])
        )
    return {
        "period_days": days,
        "by_plan_and_lane": rows,
        "by_plan": [{"plan": p, "samples": v["samples"], "avg_wait_seconds": round(v["avg_wait_seconds"], 2)}
                    for p, v in by_plan.items()],
        "config": {
            "standard_slots": MAX_ACTIVE_PIPELINES,
            "priority_slots": PRIORITY_SLOTS,
        },
    }


# ─── Founder KPI Dashboard ────────────────────────────────────────────────────
# Single endpoint that powers /app/admin/photo-trailers. Built to answer the
# only question that matters at this stage: is YouStar actually working?
# 27 KPIs across Acquisition / Engagement / Conversion / Revenue / Ops / Virality.
_RANGE_MAP = {"24h": 1, "7d": 7, "30d": 30}

def _range_to_cutoff_iso(rng: str) -> str:
    days = _RANGE_MAP.get(rng, 7)
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

async def _unique_sessions(step: str, cutoff: str, extra_match: dict = None) -> int:
    match = {"step": step, "timestamp": {"$gte": cutoff}}
    if extra_match: match.update(extra_match)
    pipe = [
        {"$match": match},
        {"$group": {"_id": "$session_id"}},
        {"$count": "n"},
    ]
    async for d in db.funnel_events.aggregate(pipe):
        return int(d.get("n", 0))
    return 0

async def _unique_users(step: str, cutoff: str) -> int:
    pipe = [
        {"$match": {"step": step, "timestamp": {"$gte": cutoff}, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "n"},
    ]
    async for d in db.funnel_events.aggregate(pipe):
        return int(d.get("n", 0))
    return 0

def _safe_pct(num, den) -> float:
    return round(100.0 * (num or 0) / den, 1) if den else 0.0

@router.get("/admin/dashboard")
async def admin_kpi_dashboard(
    user: dict = Depends(get_admin_user),
    range: str = Query("7d", pattern="^(24h|7d|30d)$"),
):
    """Single-shot founder KPI dashboard. Truth-first, no charts library bloat.

    Returns 27 KPIs across:
      ACQUISITION (1-3)  ENGAGEMENT (4-7)  CONVERSION (8-13)
      REVENUE (14-19)    OPS (20-24)       VIRALITY (25-27)
    """
    cutoff = _range_to_cutoff_iso(range)

    # ═══ ACQUISITION ═══════════════════════════════════════════════════════════
    # 1. Public share page views (raw event count)
    share_page_view_total = await db.funnel_events.count_documents(
        {"step": "share_page_view", "timestamp": {"$gte": cutoff}}
    )
    # 2. Unique visitors (unique session_ids)
    unique_visitors = await _unique_sessions("share_page_view", cutoff)
    # 3. Source split — bucket traffic_source values into the founder's 4 buckets
    source_split = {"whatsapp": 0, "native_share": 0, "direct": 0, "other": 0}
    pipe_src = [
        {"$match": {"step": "share_page_view", "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": {"sid": "$session_id", "src": "$traffic_source"}}},
        {"$group": {"_id": "$_id.src", "n": {"$sum": 1}}},
    ]
    async for d in db.funnel_events.aggregate(pipe_src):
        src = (d["_id"] or "direct").lower() if d["_id"] else "direct"
        n = int(d["n"])
        if src == "whatsapp": source_split["whatsapp"] += n
        elif src in {"direct", "unknown", "none", ""}: source_split["direct"] += n
        elif src in {"share", "native", "navigator", "navigator-share"}: source_split["native_share"] += n
        else: source_split["other"] += n

    # ═══ ENGAGEMENT ════════════════════════════════════════════════════════════
    plays_unique = await _unique_sessions("video_play_clicked", cutoff)
    w25 = await _unique_sessions("watch_25", cutoff)
    w50 = await _unique_sessions("watch_50", cutoff)
    w75 = await _unique_sessions("watch_75", cutoff)
    w100 = await _unique_sessions("completed_watch", cutoff)
    # Format split: count play events grouped by meta.format
    fmt_pipe = [
        {"$match": {"step": "video_play_clicked", "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$meta.format", "n": {"$sum": 1}}},
    ]
    fmt_play = {"wide": 0, "vertical": 0}
    async for d in db.funnel_events.aggregate(fmt_pipe):
        f = d["_id"] or "wide"
        if f in fmt_play: fmt_play[f] += int(d["n"])
    # Top templates by completion rate (need slug→template_id join)
    # Step A: collect (slug, views, completions) from funnel events
    slug_view_pipe = [
        {"$match": {"step": "share_page_view", "timestamp": {"$gte": cutoff},
                    "meta.slug": {"$ne": None}}},
        {"$group": {"_id": {"slug": "$meta.slug", "sid": "$session_id"}}},
        {"$group": {"_id": "$_id.slug", "views": {"$sum": 1}}},
    ]
    slug_views = {}
    async for d in db.funnel_events.aggregate(slug_view_pipe):
        if d["_id"]: slug_views[d["_id"]] = int(d["views"])
    slug_complete_pipe = [
        {"$match": {"step": "completed_watch", "timestamp": {"$gte": cutoff},
                    "meta.slug": {"$ne": None}}},
        {"$group": {"_id": {"slug": "$meta.slug", "sid": "$session_id"}}},
        {"$group": {"_id": "$_id.slug", "completes": {"$sum": 1}}},
    ]
    slug_completes = {}
    async for d in db.funnel_events.aggregate(slug_complete_pipe):
        if d["_id"]: slug_completes[d["_id"]] = int(d["completes"])
    slug_share_pipe = [
        {"$match": {"step": {"$in": ["whatsapp_share_clicked", "native_share_clicked"]},
                    "timestamp": {"$gte": cutoff}, "meta.slug": {"$ne": None}}},
        {"$group": {"_id": {"slug": "$meta.slug", "sid": "$session_id"}}},
        {"$group": {"_id": "$_id.slug", "shares": {"$sum": 1}}},
    ]
    slug_shares = {}
    async for d in db.funnel_events.aggregate(slug_share_pipe):
        if d["_id"]: slug_shares[d["_id"]] = int(d["shares"])
    # Slug → template_id mapping (pull only slugs we have data on)
    all_slugs = set(slug_views) | set(slug_completes) | set(slug_shares)
    slug_to_tpl = {}
    if all_slugs:
        async for j in db.photo_trailer_jobs.find(
            {"public_share_slug": {"$in": list(all_slugs)}},
            {"_id": 0, "public_share_slug": 1, "template_id": 1},
        ):
            slug_to_tpl[j["public_share_slug"]] = j.get("template_id") or "unknown"
    # Aggregate per template
    tpl_agg = {}  # tpl_id → {views, completes, shares}
    for slug, views in slug_views.items():
        tpl = slug_to_tpl.get(slug, "unknown")
        tpl_agg.setdefault(tpl, {"views": 0, "completes": 0, "shares": 0})["views"] += views
    for slug, c in slug_completes.items():
        tpl = slug_to_tpl.get(slug, "unknown")
        tpl_agg.setdefault(tpl, {"views": 0, "completes": 0, "shares": 0})["completes"] += c
    for slug, s in slug_shares.items():
        tpl = slug_to_tpl.get(slug, "unknown")
        tpl_agg.setdefault(tpl, {"views": 0, "completes": 0, "shares": 0})["shares"] += s
    top_templates_completion = sorted(
        [
            {
                "template_id": tpl,
                "title": (TEMPLATES.get(tpl, {}) or {}).get("title", tpl),
                "views": v["views"], "completes": v["completes"],
                "completion_pct": _safe_pct(v["completes"], v["views"]),
            }
            for tpl, v in tpl_agg.items() if v["views"] >= 1
        ],
        key=lambda x: (-x["completion_pct"], -x["views"]),
    )[:10]

    # ═══ CONVERSION ════════════════════════════════════════════════════════════
    make_your_own_clicks = await _unique_sessions("make_your_own_clicked", cutoff)
    signup_started = await _unique_sessions("signup_started", cutoff)
    signup_completed = await _unique_sessions("signup_completed", cutoff)
    first_trailer_created = await _unique_users("first_trailer_created", cutoff)

    # ═══ REVENUE ═══════════════════════════════════════════════════════════════
    job_match = {"created_at": {"$gte": cutoff}}
    plan_pipe = [
        {"$match": job_match},
        {"$group": {"_id": "$plan_tier_at_creation", "n": {"$sum": 1}}},
    ]
    plan_counts = {"FREE": 0, "PAID": 0, "PREMIUM": 0}
    async for d in db.photo_trailer_jobs.aggregate(plan_pipe):
        k = (d["_id"] or "FREE").upper()
        if k in plan_counts: plan_counts[k] += int(d["n"])
    purchases_60s = await db.photo_trailer_jobs.count_documents({
        **job_match, "duration_target_seconds": 60, "status": "COMPLETED",
    })
    purchases_90s = await db.photo_trailer_jobs.count_documents({
        **job_match, "duration_target_seconds": 90, "status": "COMPLETED",
    })
    upgrade_shown = await _unique_sessions("photo_trailer_paywall_shown", cutoff)
    upgrade_clicked = await _unique_sessions("photo_trailer_paywall_upgrade_clicked", cutoff)
    # Credits charged (revenue proxy — credits are the economic unit)
    credits_pipe = [
        {"$match": {**job_match, "status": "COMPLETED"}},
        {"$group": {"_id": None, "total": {"$sum": "$charged_credits"}}},
    ]
    total_credits = 0
    async for d in db.photo_trailer_jobs.aggregate(credits_pipe):
        total_credits = int(d.get("total") or 0)

    # ═══ OPS ═══════════════════════════════════════════════════════════════════
    queue_depth_active = await db.photo_trailer_jobs.count_documents(
        {"status": {"$in": ["QUEUED", "PROCESSING"]}}
    )
    wait_pipe = [
        {"$match": {**job_match, "queue_wait_seconds": {"$exists": True}}},
        {"$group": {"_id": "$queue_lane", "avg": {"$avg": "$queue_wait_seconds"},
                    "n": {"$sum": 1}}},
    ]
    wait_by_lane = {"priority": 0.0, "standard": 0.0}
    wait_samples = {"priority": 0, "standard": 0}
    async for d in db.photo_trailer_jobs.aggregate(wait_pipe):
        lane = d["_id"] or "standard"
        if lane in wait_by_lane:
            wait_by_lane[lane] = round(d["avg"] or 0, 1)
            wait_samples[lane] = int(d["n"])
    total_jobs_in_range = await db.photo_trailer_jobs.count_documents(job_match)
    failed_in_range = await db.photo_trailer_jobs.count_documents(
        {**job_match, "status": "FAILED"}
    )

    # ── Failure diagnostics: stage breakdown, error codes, recovery est. ────
    # error_code → canonical stage (covers historical jobs that lack
    # `failure_stage`). For new failures we also store `failure_stage` directly.
    ERROR_TO_STAGE = {
        "CREDIT_DEDUCT_FAIL":   "VALIDATING",
        "HERO_LOAD_FAIL":       "ANALYZING_PHOTOS",
        "SCRIPT_FAIL":          "WRITING_TRAILER_SCRIPT",
        "IMAGE_GEN_FAIL":       "GENERATING_SCENES",
        "TTS_FAIL":             "GENERATING_VOICEOVER",
        "RENDER_FAIL":          "RENDERING_TRAILER",
        "UPLOAD_FAIL":          "RENDERING_TRAILER",
        "STALE_PIPELINE":       "JANITOR_STALE",
        "PIPELINE_CRASH":       "PIPELINE_CRASH",
    }
    # Codes whose root cause is typically transient → retryable
    RETRYABLE_CODES = {"IMAGE_GEN_FAIL", "TTS_FAIL", "RENDER_FAIL",
                       "UPLOAD_FAIL", "SCRIPT_FAIL", "PIPELINE_CRASH",
                       "STALE_PIPELINE"}
    # Conservative empirical retry success rate for transient pipeline failures
    RETRY_SUCCESS_RATE = 0.65

    failure_stage_breakdown = []
    error_code_breakdown = []
    if failed_in_range:
        # Per-error-code aggregation, then derive stage
        ec_pipe = [
            {"$match": {**job_match, "status": "FAILED"}},
            {"$group": {"_id": "$error_code", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
        ]
        stage_counts = {}
        async for d in db.photo_trailer_jobs.aggregate(ec_pipe):
            code = d["_id"] or "UNKNOWN"
            n = int(d["n"])
            error_code_breakdown.append({
                "error_code": code, "count": n,
                "share_pct": _safe_pct(n, failed_in_range),
                "retryable": code in RETRYABLE_CODES,
            })
            stage = ERROR_TO_STAGE.get(code, "UNKNOWN")
            stage_counts[stage] = stage_counts.get(stage, 0) + n
        # If any new-style failure_stage is set, prefer it
        fs_pipe = [
            {"$match": {**job_match, "status": "FAILED",
                        "failure_stage": {"$exists": True, "$ne": None,
                                          "$nin": ["FAILED", "UNKNOWN"]}}},
            {"$group": {"_id": "$failure_stage", "n": {"$sum": 1}}},
        ]
        async for d in db.photo_trailer_jobs.aggregate(fs_pipe):
            # Override derived count for stages we have direct evidence for
            stage_counts[d["_id"]] = max(stage_counts.get(d["_id"], 0), int(d["n"]))
        failure_stage_breakdown = sorted(
            [{"stage": s, "count": n,
              "share_pct": _safe_pct(n, failed_in_range)}
             for s, n in stage_counts.items()],
            key=lambda x: -x["count"],
        )

    top_failure_stage = failure_stage_breakdown[0] if failure_stage_breakdown else None
    top_error_code = error_code_breakdown[0] if error_code_breakdown else None

    # Recovery opportunity: if top error is retryable, estimate fail-rate drop
    # if we successfully retried RETRY_SUCCESS_RATE of those failures.
    recovery_opportunity = None
    if top_error_code and top_error_code["retryable"] and failed_in_range and total_jobs_in_range:
        recoverable_fails = int(top_error_code["count"] * RETRY_SUCCESS_RATE)
        projected_fails = max(0, failed_in_range - recoverable_fails)
        current_rate = _safe_pct(failed_in_range, total_jobs_in_range)
        projected_rate = _safe_pct(projected_fails, total_jobs_in_range)
        recovery_opportunity = {
            "top_error_code": top_error_code["error_code"],
            "retryable_count": top_error_code["count"],
            "assumed_retry_success_rate": RETRY_SUCCESS_RATE,
            "current_fail_rate_pct": current_rate,
            "projected_fail_rate_pct": projected_rate,
            "estimated_drop_pct": round(current_rate - projected_rate, 1),
        }

    # Recent failed jobs sample (clickable in UI)
    recent_failures = []
    if failed_in_range:
        async for f in db.photo_trailer_jobs.find(
            {**job_match, "status": "FAILED"},
            {"_id": 1, "error_code": 1, "error_message": 1, "failed_at": 1,
             "template_id": 1, "plan_tier_at_creation": 1, "failure_stage": 1,
             "duration_target_seconds": 1},
        ).sort("failed_at", -1).limit(10):
            recent_failures.append({
                "job_id": f["_id"],
                "error_code": f.get("error_code") or "UNKNOWN",
                "error_message": (f.get("error_message") or "")[:160],
                "stage": f.get("failure_stage") or
                         ERROR_TO_STAGE.get(f.get("error_code") or "", "UNKNOWN"),
                "template_id": f.get("template_id"),
                "plan_tier": f.get("plan_tier_at_creation") or "FREE",
                "duration": f.get("duration_target_seconds"),
                "failed_at": f.get("failed_at"),
            })

    # Daily fail trend (last 14d max regardless of range, by stage stacked)
    trend_days = 1 if range == "24h" else (7 if range == "7d" else 30)
    trend_cutoff = (datetime.now(timezone.utc) - timedelta(days=trend_days)).isoformat()
    trend_pipe = [
        {"$match": {"status": "FAILED", "failed_at": {"$gte": trend_cutoff}}},
        {"$project": {
            "day": {"$substr": ["$failed_at", 0, 10]},
            "error_code": 1,
        }},
        {"$group": {"_id": {"day": "$day", "code": "$error_code"},
                    "n": {"$sum": 1}}},
        {"$sort": {"_id.day": 1}},
    ]
    trend_by_day = {}
    async for d in db.photo_trailer_jobs.aggregate(trend_pipe):
        day = (d["_id"] or {}).get("day") or "?"
        code = (d["_id"] or {}).get("code") or "UNKNOWN"
        stage = ERROR_TO_STAGE.get(code, "UNKNOWN")
        trend_by_day.setdefault(day, {})
        trend_by_day[day][stage] = trend_by_day[day].get(stage, 0) + int(d["n"])
    fail_trend = [{"day": day, "by_stage": stages, "total": sum(stages.values())}
                  for day, stages in sorted(trend_by_day.items())]


    # Avg render time by duration (started_at → completed_at)
    render_pipe = [
        {"$match": {**job_match, "status": "COMPLETED",
                    "started_at": {"$ne": None}, "completed_at": {"$ne": None}}},
        {"$project": {
            "duration_target_seconds": 1,
            "render_seconds": {
                "$divide": [
                    {"$subtract": [
                        {"$dateFromString": {"dateString": "$completed_at"}},
                        {"$dateFromString": {"dateString": "$started_at"}},
                    ]},
                    1000,
                ]},
        }},
        {"$group": {"_id": "$duration_target_seconds",
                    "avg": {"$avg": "$render_seconds"}, "n": {"$sum": 1}}},
    ]
    render_by_duration = {"20": None, "60": None, "90": None}
    render_samples = {"20": 0, "60": 0, "90": 0}
    async for d in db.photo_trailer_jobs.aggregate(render_pipe):
        k = str(int(d["_id"])) if d["_id"] is not None else None
        if k in render_by_duration:
            render_by_duration[k] = round(d["avg"] or 0, 1)
            render_samples[k] = int(d["n"])

    # ═══ VIRALITY ══════════════════════════════════════════════════════════════
    wa_shares = await _unique_sessions("whatsapp_share_clicked", cutoff)
    native_shares = await _unique_sessions("native_share_clicked", cutoff)
    total_shares = wa_shares + native_shares
    completed_jobs = await db.photo_trailer_jobs.count_documents(
        {**job_match, "status": "COMPLETED"}
    )
    top_templates_share = sorted(
        [
            {
                "template_id": tpl,
                "title": (TEMPLATES.get(tpl, {}) or {}).get("title", tpl),
                "views": v["views"], "shares": v["shares"],
                "share_rate_pct": _safe_pct(v["shares"], v["views"]),
            }
            for tpl, v in tpl_agg.items() if v["views"] >= 1
        ],
        key=lambda x: (-x["share_rate_pct"], -x["views"]),
    )[:10]

    return {
        "range": range,
        "generated_at": _now(),
        "acquisition": {
            "share_page_views": share_page_view_total,
            "unique_visitors": unique_visitors,
            "source_split": source_split,
        },
        "engagement": {
            "view_to_play_pct": _safe_pct(plays_unique, unique_visitors),
            "watch_25_pct": _safe_pct(w25, plays_unique),
            "watch_50_pct": _safe_pct(w50, plays_unique),
            "watch_75_pct": _safe_pct(w75, plays_unique),
            "watch_100_pct": _safe_pct(w100, plays_unique),
            "plays_unique": plays_unique,
            "format_play_split": fmt_play,
            "top_templates_by_completion": top_templates_completion,
        },
        "conversion": {
            "make_your_own_ctr_pct": _safe_pct(make_your_own_clicks, unique_visitors),
            "make_your_own_clicks": make_your_own_clicks,
            "signup_started": signup_started,
            "signup_completed": signup_completed,
            "first_trailer_created": first_trailer_created,
            "view_to_signup_pct": _safe_pct(signup_completed, unique_visitors),
            "signup_to_first_trailer_pct": _safe_pct(first_trailer_created, signup_completed),
        },
        "revenue": {
            "free_jobs": plan_counts["FREE"],
            "paid_jobs": plan_counts["PAID"],
            "premium_jobs": plan_counts["PREMIUM"],
            "purchases_60s": purchases_60s,
            "purchases_90s": purchases_90s,
            "upgrade_modal_shown": upgrade_shown,
            "upgrade_clicked": upgrade_clicked,
            "upgrade_ctr_pct": _safe_pct(upgrade_clicked, upgrade_shown),
            "credits_charged_total": total_credits,
        },
        "ops": {
            "queue_depth_active": queue_depth_active,
            "avg_wait_premium_seconds": wait_by_lane["priority"],
            "avg_wait_standard_seconds": wait_by_lane["standard"],
            "wait_samples": wait_samples,
            "fail_rate_pct": _safe_pct(failed_in_range, total_jobs_in_range),
            "total_jobs": total_jobs_in_range,
            "failed_jobs": failed_in_range,
            "avg_render_seconds_by_duration": render_by_duration,
            "render_samples_by_duration": render_samples,
            # ── Diagnostic block (P0 founder ask: WHY are jobs failing) ──
            "failure_stage_breakdown": failure_stage_breakdown,
            "error_code_breakdown": error_code_breakdown,
            "top_failure_stage": top_failure_stage,
            "top_error_code": top_error_code,
            "recovery_opportunity": recovery_opportunity,
            "recent_failures": recent_failures,
            "fail_trend": fail_trend,
        },
        "virality": {
            "view_to_share_pct": _safe_pct(total_shares, unique_visitors),
            "shares_total": total_shares,
            "whatsapp_shares": wa_shares,
            "native_shares": native_shares,
            "shares_per_completed_trailer": (
                round(total_shares / completed_jobs, 2) if completed_jobs else 0.0
            ),
            "top_templates_by_share_rate": top_templates_share,
        },
    }
