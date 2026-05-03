"""AI Personal Avatar Studio — vertical-slice backend.

P0 scope: consent-based personal avatars. NO real AI generation in this
session — every renderer/voice/training path is a mock that simulates
progression. The structure mirrors `photo_trailer.py` so we can plug fal.ai
(face), ElevenLabs (voice), and a real liveness vendor in next session
without refactoring data contracts.

Hard rules baked in:
  - Self-clones only OR third-party with a recorded consent video + phrase
  - Every export carries a visible "AI-generated avatar" disclosure
  - Every export carries forensic_watermark_id metadata
  - Admin can disable a clone and revoke consent
  - Script safety check refuses banking/medical/legal/political/sexual/
    impersonation prompts
  - Banned: celebrity/public figure names (heuristic blocklist)
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, UploadFile)
from pydantic import BaseModel, Field

from shared import db, get_admin_user, get_current_user

log = logging.getLogger("avatar_studio")
router = APIRouter(prefix="/avatar", tags=["avatar"])

# ─── Constants ────────────────────────────────────────────────────────────
DISCLOSURE_TEXT = "This video uses an AI-generated avatar with verified consent."
VISIBLE_LABEL = "AI-generated avatar"
REQUIRED_CONSENT_PHRASE = (
    "I consent to creating an AI avatar of myself and my content. "
    "I understand all output will be labeled AI-generated."
)


def _normalize_consent_phrase(s: str) -> str:
    """Safe-only normalization: trim ends, collapse internal whitespace,
    case-fold. NO word reordering, NO partial matches, NO punctuation
    stripping."""
    return re.sub(r"\s+", " ", (s or "")).strip().lower()
MIN_CONSENT_SECONDS = 5
MAX_SCRIPT_CHARS = 1200
MOCK_TRAIN_SECONDS = 8       # simulated training duration
MOCK_RENDER_SECONDS = 6      # simulated render duration

# Heuristic safety lists — production must replace with proper moderation.
BANNED_SUBSTRINGS = [
    # Politicians / persuasion
    "modi", "biden", "trump", "putin", "xi jinping", "rahul gandhi",
    "vote for", "election", "political party",
    # Celebrities (small starter list — must expand or use a service)
    "shahrukh khan", "salman khan", "amitabh bachchan", "tom cruise",
    "elon musk", "taylor swift", "messi", "ronaldo", "deepika padukone",
    # Fraud / impersonation
    "otp", "one time password", "bank account", "kyc verification",
    "send me money", "wire transfer", "credit card number",
    # Medical / legal impersonation
    "i am a doctor", "i am a lawyer", "medical advice", "legal advice",
    "diagnose", "prescribe",
    # Deception
    "this is real", "not ai", "really me on a call", "pretend to be",
    # Sexual / NSFW
    "nude", "naked", "porn", "sexual", "fetish",
]
ALLOWED_CLONE_TYPES = {"self", "authorized_person"}
ALLOWED_PLATFORMS = {"generic", "youtube", "instagram", "whatsapp", "linkedin"}

# Pricing (display-only this session — no Cashfree calls)
AVATAR_PLANS = [
    {"id": "free",    "name": "Free Trial",  "price_inr": 0,    "credits": 3,    "features": [
        "1 demo avatar", "3 short generations", "Watermarked", "No commercial export"]},
    {"id": "creator", "name": "Creator",     "price_inr": 699,  "credits": 60,   "features": [
        "1 personal clone", "60 avatar credits/month", "720p export",
        "Avatar chat", "YouTube disclosure template"]},
    {"id": "pro",     "name": "Pro",         "price_inr": 1999, "credits": 250,  "features": [
        "3 clones", "250 credits/month", "1080p export",
        "Faster queue", "Brand scripts", "Priority rendering"]},
    {"id": "studio",  "name": "Studio",      "price_inr": 7999, "credits": 1200, "features": [
        "10 clones", "1200 credits/month", "Team access",
        "API access", "Commercial usage", "Manual review SLA"]},
]
AVATAR_TOPUPS = [
    {"id": "topup_25",  "price_inr": 199,   "credits": 25},
    {"id": "topup_75",  "price_inr": 499,   "credits": 75},
    {"id": "topup_180", "price_inr": 999,   "credits": 180},
    {"id": "topup_650", "price_inr": 2999,  "credits": 650},
]


# ─── Helpers ──────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_id(doc: Optional[dict]) -> Optional[dict]:
    """Remove Mongo ObjectId artifacts (we use string _id)."""
    if not doc:
        return doc
    # Map _id → id for the API surface; keep both for now.
    if "_id" in doc and "id" not in doc:
        doc["id"] = doc["_id"]
    return doc


async def _run_script_safety_check(script: str) -> dict:
    """Lightweight blocklist + length guard. Production must call a real
    moderation API (OpenAI moderation, Anthropic safety, etc.)."""
    s = script.lower().strip()
    if not s:
        return {"allowed": False, "reason": "Script cannot be empty.", "code": "EMPTY"}
    if len(script) > MAX_SCRIPT_CHARS:
        return {"allowed": False, "reason": f"Script too long (max {MAX_SCRIPT_CHARS} chars).", "code": "TOO_LONG"}
    for term in BANNED_SUBSTRINGS:
        if term in s:
            return {
                "allowed": False,
                "reason": "Script contains content we cannot generate (impersonation, "
                          "political persuasion, fraud, medical/legal, or sexual material).",
                "code": "DISALLOWED_CONTENT",
                "matched": term,
            }
    return {"allowed": True}


# ─── Models ───────────────────────────────────────────────────────────────
class CreateCloneRequest(BaseModel):
    clone_name: str = Field(..., min_length=2, max_length=60)
    clone_type: str = "self"


class GenerateVideoRequest(BaseModel):
    clone_id: str
    script: str
    platform: str = "generic"


class ChatRequest(BaseModel):
    clone_id: str
    message: str = Field(..., min_length=1, max_length=600)


class AbuseReportIn(BaseModel):
    clone_id: Optional[str] = None
    export_id: Optional[str] = None
    reason: str = Field(..., min_length=8, max_length=1000)


class AdminCloneActionIn(BaseModel):
    action: str  # "approve_consent" | "reject_consent" | "disable_clone" | "enable_clone"
    notes: Optional[str] = None


class AdminAbuseActionIn(BaseModel):
    status: str  # "reviewing" | "actioned" | "rejected"
    notes: Optional[str] = None


# ─── Public: clones CRUD ──────────────────────────────────────────────────
@router.post("/clones")
async def create_clone(body: CreateCloneRequest, user: dict = Depends(get_current_user)):
    if body.clone_type not in ALLOWED_CLONE_TYPES:
        raise HTTPException(400, "Invalid clone type")
    clone = {
        "_id": str(uuid.uuid4()),
        "user_id": user["id"],
        "clone_name": body.clone_name.strip(),
        "clone_type": body.clone_type,
        "status": "consent_pending",
        "face_model_ref": None,
        "voice_model_ref": None,
        "risk_score": 0,
        "disabled_reason": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.avatar_clones.insert_one(clone)
    return _strip_id({**clone})


@router.get("/clones")
async def list_clones(user: dict = Depends(get_current_user)):
    out = []
    async for c in db.avatar_clones.find({"user_id": user["id"]}, {"_id": 1, "clone_name": 1,
                                                                    "clone_type": 1, "status": 1,
                                                                    "face_model_ref": 1, "voice_model_ref": 1,
                                                                    "created_at": 1, "updated_at": 1,
                                                                    "disabled_reason": 1}).sort("created_at", -1):
        out.append(_strip_id(c))
    return {"clones": out}


@router.get("/clones/{clone_id}")
async def get_clone(clone_id: str, user: dict = Depends(get_current_user)):
    c = await db.avatar_clones.find_one({"_id": clone_id, "user_id": user["id"]}, {"_id": 1, "user_id": 1,
                                                                                    "clone_name": 1, "clone_type": 1,
                                                                                    "status": 1, "face_model_ref": 1,
                                                                                    "voice_model_ref": 1, "risk_score": 1,
                                                                                    "disabled_reason": 1,
                                                                                    "created_at": 1, "updated_at": 1})
    if not c:
        raise HTTPException(404, "Clone not found")
    return _strip_id(c)


# ─── Consent capture (P0: procedural — record video, read phrase) ─────────
@router.post("/clones/{clone_id}/consent")
async def submit_consent(
    clone_id: str,
    consent_phrase: str = Form(...),
    duration_seconds: float = Form(...),
    user_agent: str = Form(""),
    selfie_video: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Stores the consent video (procedural liveness placeholder) + phrase
    + UA + IP and queues admin approval. NO biometric vendor wired this
    session; admin moderation is the gate."""
    clone = await db.avatar_clones.find_one({"_id": clone_id, "user_id": user["id"]})
    if not clone:
        raise HTTPException(404, "Clone not found")
    if clone["status"] not in {"consent_pending", "consent_rejected"}:
        raise HTTPException(409, "Consent already submitted")

    if duration_seconds < MIN_CONSENT_SECONDS:
        raise HTTPException(400, f"Consent video must be at least {MIN_CONSENT_SECONDS}s")
    # Exact-match after safe normalization. 80%-overlap was too lenient
    # (let "Kichi Kichi kavaakika"-style noise through).
    if _normalize_consent_phrase(consent_phrase) != _normalize_consent_phrase(REQUIRED_CONSENT_PHRASE):
        raise HTTPException(
            400,
            "Typed phrase must exactly match the required consent phrase."
        )

    # Mock storage: we record file size + first-100-bytes hash as proof-of-upload.
    # Production must persist to R2 and store storage_url.
    raw = await selfie_video.read()
    if len(raw) < 5_000:  # 5KB min — sanity
        raise HTTPException(400, "Consent video too small. Please re-record.")
    fake_storage_url = f"mock://avatar_consent/{clone_id}/{uuid.uuid4()}.webm"

    consent = {
        "_id": str(uuid.uuid4()),
        "clone_id": clone_id,
        "user_id": user["id"],
        "consent_type": "self" if clone["clone_type"] == "self" else "third_party_authorized",
        "consent_phrase_text": consent_phrase,
        "selfie_video_url": fake_storage_url,
        "selfie_video_size_bytes": len(raw),
        "voice_consent_url": fake_storage_url,  # same artifact this session
        "liveness_score": None,                  # next session
        "id_check_status": "not_required",
        "consent_status": "pending",             # admin must approve
        "user_agent": user_agent[:500],
        "ip_address": None,                      # set by middleware in prod
        "created_at": _now(),
        "revoked_at": None,
    }
    await db.clone_consents.insert_one(consent)
    await db.avatar_clones.update_one(
        {"_id": clone_id},
        {"$set": {"status": "consent_review", "updated_at": _now()}},
    )
    await _emit_funnel("avatar_consent_submitted", user_id=user["id"],
                       meta={"clone_id": clone_id, "consent_type": consent["consent_type"]})
    return {"consent_id": consent["_id"], "status": "pending"}


@router.get("/clones/{clone_id}/consent")
async def get_latest_consent(clone_id: str, user: dict = Depends(get_current_user)):
    clone = await db.avatar_clones.find_one({"_id": clone_id, "user_id": user["id"]}, {"_id": 1})
    if not clone:
        raise HTTPException(404, "Clone not found")
    c = await db.clone_consents.find_one(
        {"clone_id": clone_id}, sort=[("created_at", -1)],
        projection={"_id": 1, "clone_id": 1, "consent_status": 1, "created_at": 1,
                    "consent_phrase_text": 1, "selfie_video_url": 1, "consent_type": 1})
    return _strip_id(c) or {"consent_status": "none"}


# ─── Voice profile (mock) ─────────────────────────────────────────────────
def _train_err(code: str, message: str, http: int = 400):
    """Structured train/voice error. Detail is a dict so the frontend can
    map to friendly UX without parsing free-form strings (which is what let
    Safari's 'Body is disturbed or locked' leak in)."""
    return HTTPException(status_code=http, detail={"code": code, "message": message})


async def _audit_train(user_id: str, clone_id: str, consent_status: Optional[str],
                       training_state: Optional[str], error_code: Optional[str],
                       extra: Optional[dict] = None):
    log.info("avatar_train_attempt user=%s clone=%s consent=%s state=%s code=%s extra=%s ts=%s",
             user_id, clone_id, consent_status, training_state, error_code, extra or {}, _now())


@router.post("/clones/{clone_id}/voice-profile")
async def create_voice_profile(clone_id: str, user: dict = Depends(get_current_user)):
    clone = await db.avatar_clones.find_one({"_id": clone_id, "user_id": user["id"]})
    if not clone:
        await _audit_train(user["id"], clone_id, None, None, "AVATAR_SESSION_MISSING",
                           {"endpoint": "voice-profile"})
        raise _train_err("AVATAR_SESSION_MISSING",
                         "Avatar session not initialized. Please refresh and try again.", 404)
    if clone.get("status") == "disabled":
        await _audit_train(user["id"], clone_id, None, clone.get("status"),
                           "AVATAR_LOCKED", {"endpoint": "voice-profile"})
        raise _train_err("AVATAR_LOCKED",
                         "Avatar training is temporarily unavailable. Please retry in a few minutes.", 423)
    consent = await db.clone_consents.find_one({"clone_id": clone_id, "consent_status": "approved"})
    if not consent:
        latest = await db.clone_consents.find_one({"clone_id": clone_id},
                                                  sort=[("created_at", -1)],
                                                  projection={"consent_status": 1})
        cs = (latest or {}).get("consent_status") or "none"
        await _audit_train(user["id"], clone_id, cs, clone.get("status"),
                           "CONSENT_NOT_APPROVED", {"endpoint": "voice-profile"})
        raise _train_err("CONSENT_NOT_APPROVED",
                         "Your consent is still under review. Training unlocks once an admin approves.", 403)
    voice_ref = f"mock_voice::{clone_id}::{uuid.uuid4().hex[:8]}"
    await db.avatar_clones.update_one(
        {"_id": clone_id},
        {"$set": {"voice_model_ref": voice_ref, "updated_at": _now()}},
    )
    return {"voice_model_ref": voice_ref, "provider": "mock"}


# ─── Avatar training (mock job) ───────────────────────────────────────────
@router.post("/clones/{clone_id}/train")
async def train_clone(clone_id: str, bg: BackgroundTasks, user: dict = Depends(get_current_user)):
    clone = await db.avatar_clones.find_one({"_id": clone_id, "user_id": user["id"]})
    if not clone:
        await _audit_train(user["id"], clone_id, None, None, "AVATAR_SESSION_MISSING")
        raise _train_err("AVATAR_SESSION_MISSING",
                         "Avatar session not initialized. Please refresh and try again.", 404)
    if clone.get("status") == "disabled":
        await _audit_train(user["id"], clone_id, None, clone.get("status"), "AVATAR_LOCKED")
        raise _train_err("AVATAR_LOCKED",
                         "Avatar training is temporarily unavailable. Please retry in a few minutes.", 423)
    consent = await db.clone_consents.find_one({"clone_id": clone_id, "consent_status": "approved"})
    if not consent:
        latest = await db.clone_consents.find_one({"clone_id": clone_id},
                                                  sort=[("created_at", -1)],
                                                  projection={"consent_status": 1})
        cs = (latest or {}).get("consent_status") or "none"
        await _audit_train(user["id"], clone_id, cs, clone.get("status"), "CONSENT_NOT_APPROVED")
        raise _train_err("CONSENT_NOT_APPROVED",
                         "Your consent is still under review. Training unlocks once an admin approves.", 403)
    if clone["status"] == "ready":
        await _audit_train(user["id"], clone_id, "approved", "ready", None,
                           {"already_ready": True})
        return {"job_id": None, "status": "already_ready"}
    if clone["status"] not in {"consent_approved", "training", "consent_review"}:
        await _audit_train(user["id"], clone_id, "approved", clone.get("status"),
                           "AVATAR_STATE_INVALID")
        raise _train_err("AVATAR_STATE_INVALID",
                         "Something went wrong while preparing your avatar. Please retry.", 409)
    try:
        job = {
            "_id": str(uuid.uuid4()),
            "user_id": user["id"],
            "clone_id": clone_id,
            "job_type": "train_avatar",
            "status": "queued",
            "progress": 0,
            "worker_name": "mock_avatar_training_worker",
            "input": {},
            "output_url": None,
            "error_code": None,
            "started_at": None,
            "completed_at": None,
            "created_at": _now(),
        }
        await db.avatar_jobs.insert_one(job)
        await db.avatar_clones.update_one({"_id": clone_id},
                                          {"$set": {"status": "training", "updated_at": _now()}})
        bg.add_task(_mock_training_worker, job["_id"])
        await _audit_train(user["id"], clone_id, "approved", "training", None,
                           {"job_id": job["_id"]})
        return {"job_id": job["_id"], "status": "queued"}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("train init failed user=%s clone=%s: %s", user["id"], clone_id, e)
        await _audit_train(user["id"], clone_id, "approved", clone.get("status"),
                           "TRAINING_INIT_FAILED", {"exception": str(e)[:300]})
        raise _train_err("TRAINING_INIT_FAILED",
                         "Could not start training. Please retry.", 500)


async def _mock_training_worker(job_id: str):
    """Simulate training progression. Replace with real fal.ai call next session."""
    try:
        await db.avatar_jobs.update_one({"_id": job_id}, {
            "$set": {"status": "running", "progress": 5, "started_at": _now()}})
        for pct in (20, 45, 70, 90):
            await asyncio.sleep(MOCK_TRAIN_SECONDS / 4)
            await db.avatar_jobs.update_one({"_id": job_id}, {"$set": {"progress": pct}})
        job = await db.avatar_jobs.find_one({"_id": job_id})
        if not job:
            return
        face_ref = f"mock_face::{job['clone_id']}::{uuid.uuid4().hex[:8]}"
        await db.avatar_clones.update_one(
            {"_id": job["clone_id"]},
            {"$set": {"face_model_ref": face_ref, "status": "ready", "updated_at": _now()}},
        )
        await db.avatar_jobs.update_one({"_id": job_id}, {
            "$set": {"status": "completed", "progress": 100,
                     "completed_at": _now(), "output_url": face_ref}})
    except Exception as e:
        log.exception(f"mock train worker failed: {e}")
        await db.avatar_jobs.update_one({"_id": job_id}, {
            "$set": {"status": "failed", "error_code": "MOCK_TRAIN_FAIL"}})


# ─── Job polling ──────────────────────────────────────────────────────────
@router.get("/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    j = await db.avatar_jobs.find_one(
        {"_id": job_id, "user_id": user["id"]},
        {"_id": 1, "clone_id": 1, "job_type": 1, "status": 1, "progress": 1,
         "output_url": 1, "error_code": 1, "started_at": 1, "completed_at": 1, "created_at": 1,
         "stage_label": 1, "eta_seconds": 1, "is_demo_output": 1, "demo_label": 1,
         "output_export_id": 1, "input": 1})
    if not j:
        raise HTTPException(404, "Job not found")
    # Self-heal zombie jobs killed by a hot-reload (Phase 1 mock only).
    if j.get("job_type") == "studio_mock_generate":
        j = await _reconcile_stuck_job_if_needed(j) or j
    return _strip_id(j)


# ─── Script-to-video (mock renderer) ──────────────────────────────────────
@router.post("/generate-video")
async def generate_video(body: GenerateVideoRequest, bg: BackgroundTasks,
                         user: dict = Depends(get_current_user)):
    if body.platform not in ALLOWED_PLATFORMS:
        raise HTTPException(400, "Unsupported platform")
    clone = await db.avatar_clones.find_one({"_id": body.clone_id, "user_id": user["id"]})
    if not clone:
        raise HTTPException(404, "Clone not found")
    if clone["status"] != "ready":
        raise HTTPException(409, "Clone is not ready yet")
    safety = await _run_script_safety_check(body.script)
    if not safety["allowed"]:
        raise HTTPException(400, safety)
    job = {
        "_id": str(uuid.uuid4()),
        "user_id": user["id"],
        "clone_id": body.clone_id,
        "job_type": "generate_video",
        "status": "queued",
        "progress": 0,
        "worker_name": "mock_render_worker",
        "input": {
            "script": body.script,
            "platform": body.platform,
            "disclosure_text": DISCLOSURE_TEXT,
        },
        "output_url": None,
        "error_code": None,
        "started_at": None,
        "completed_at": None,
        "created_at": _now(),
    }
    await db.avatar_jobs.insert_one(job)
    bg.add_task(_mock_render_worker, job["_id"])
    return {"job_id": job["_id"], "status": "queued"}


async def _mock_render_worker(job_id: str):
    """Simulate render + watermark. Provider-adapter shape so a real
    fal.ai/HeyGen call can drop in next session."""
    try:
        await db.avatar_jobs.update_one({"_id": job_id}, {
            "$set": {"status": "running", "progress": 10, "started_at": _now()}})
        # Phase: voice synth (mocked)
        await asyncio.sleep(MOCK_RENDER_SECONDS / 3)
        await db.avatar_jobs.update_one({"_id": job_id}, {"$set": {"progress": 40}})
        # Phase: face render (mocked)
        await asyncio.sleep(MOCK_RENDER_SECONDS / 3)
        await db.avatar_jobs.update_one({"_id": job_id}, {"$set": {"progress": 75}})
        # Phase: watermark + disclosure burn-in (mocked)
        await asyncio.sleep(MOCK_RENDER_SECONDS / 3)
        job = await db.avatar_jobs.find_one({"_id": job_id})
        if not job:
            return
        clone_id = job["clone_id"]
        # Mock output: a public sample MP4. Production will be R2 watermarked URL.
        mock_video_url = (
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/"
            "BigBuckBunny.mp4"
        )
        forensic_id = f"WM-{uuid.uuid4().hex[:16]}"
        export = {
            "_id": str(uuid.uuid4()),
            "user_id": job["user_id"],
            "clone_id": clone_id,
            "job_id": job_id,
            "export_type": "video",
            "file_url": mock_video_url,
            "visible_label_applied": True,
            "visible_label_text": VISIBLE_LABEL,
            "forensic_watermark_id": forensic_id,
            "disclosure_text": DISCLOSURE_TEXT,
            "platform": job["input"]["platform"],
            "metadata": {
                "ai_generated": True,
                "ai_provider": "mock",
                "clone_id": clone_id,
                "watermark_id": forensic_id,
                "visible_label": VISIBLE_LABEL,
                "disclosure": DISCLOSURE_TEXT,
                "youtube_synthetic_disclosure_required": True,
                "eu_ai_act_marking_required": True,
            },
            "script": job["input"]["script"][:1000],
            "created_at": _now(),
        }
        await db.avatar_exports.insert_one(export)
        # Funnel emit: first vs repeat export per user.
        prior = await db.avatar_exports.count_documents({"user_id": job["user_id"]})
        step = "avatar_first_export" if prior <= 1 else "avatar_repeat_export"
        await _emit_funnel(step, user_id=job["user_id"],
                           meta={"clone_id": clone_id, "export_id": export["_id"],
                                 "platform": job["input"]["platform"]})
        await db.avatar_jobs.update_one({"_id": job_id}, {
            "$set": {"status": "completed", "progress": 100,
                     "completed_at": _now(), "output_url": mock_video_url,
                     "output_export_id": export["_id"]}})
    except Exception as e:
        log.exception(f"mock render worker failed: {e}")
        await db.avatar_jobs.update_one({"_id": job_id}, {
            "$set": {"status": "failed", "error_code": "MOCK_RENDER_FAIL"}})


# ─── Avatar chat (mock — echoes script through safety check) ──────────────
@router.post("/clones/{clone_id}/chat")
async def avatar_chat(clone_id: str, body: ChatRequest,
                      user: dict = Depends(get_current_user)):
    clone = await db.avatar_clones.find_one({"_id": clone_id, "user_id": user["id"]})
    if not clone or clone["status"] != "ready":
        raise HTTPException(404, "Ready clone not found")
    safety = await _run_script_safety_check(body.message)
    if not safety["allowed"]:
        raise HTTPException(400, safety)
    # Mock response — production wires to LLM with persona context.
    reply = f"[{VISIBLE_LABEL}] {clone['clone_name']}: I hear you say '{body.message}'. " \
            "(Mock reply — real avatar chat lands next session with disclosure.)"
    return {"reply": reply, "visible_label": VISIBLE_LABEL,
            "disclosure": DISCLOSURE_TEXT}


# ─── Exports listing + abuse reports ──────────────────────────────────────
@router.get("/clones/{clone_id}/exports")
async def list_exports(clone_id: str, user: dict = Depends(get_current_user)):
    out = []
    async for e in db.avatar_exports.find(
        {"user_id": user["id"], "clone_id": clone_id},
        {"_id": 1, "clone_id": 1, "export_type": 1, "file_url": 1,
         "visible_label_applied": 1, "visible_label_text": 1,
         "forensic_watermark_id": 1, "disclosure_text": 1, "platform": 1,
         "created_at": 1, "metadata": 1, "script": 1},
    ).sort("created_at", -1):
        out.append(_strip_id(e))
    return {"exports": out}


@router.post("/abuse-report")
async def submit_abuse_report(body: AbuseReportIn, user: dict = Depends(get_current_user)):
    if not body.clone_id and not body.export_id:
        raise HTTPException(400, "clone_id or export_id required")
    rep = {
        "_id": str(uuid.uuid4()),
        "reporter_user_id": user["id"],
        "clone_id": body.clone_id,
        "export_id": body.export_id,
        "reason": body.reason,
        "status": "open",
        "admin_notes": None,
        "created_at": _now(),
    }
    await db.clone_abuse_reports.insert_one(rep)
    return {"report_id": rep["_id"]}


# ─── Billing surface (display-only this session) ──────────────────────────
@router.get("/billing/plans")
async def list_plans():
    return {"plans": AVATAR_PLANS, "topups": AVATAR_TOPUPS, "currency": "INR"}


# ─── Admin: moderation ────────────────────────────────────────────────────
@router.get("/admin/clones")
async def admin_list_clones(status: Optional[str] = None,
                            user: dict = Depends(get_admin_user)):
    q: dict = {}
    if status:
        q["status"] = status
    out = []
    async for c in db.avatar_clones.find(q, {"_id": 1, "user_id": 1, "clone_name": 1,
                                              "clone_type": 1, "status": 1,
                                              "face_model_ref": 1, "voice_model_ref": 1,
                                              "risk_score": 1, "disabled_reason": 1,
                                              "created_at": 1, "updated_at": 1}).sort("created_at", -1).limit(200):
        out.append(_strip_id(c))
    return {"clones": out}


@router.get("/admin/consents/pending")
async def admin_list_pending_consents(user: dict = Depends(get_admin_user)):
    out = []
    async for c in db.clone_consents.find(
        {"consent_status": "pending"},
        {"_id": 1, "clone_id": 1, "user_id": 1, "consent_type": 1,
         "consent_phrase_text": 1, "selfie_video_url": 1, "selfie_video_size_bytes": 1,
         "created_at": 1, "user_agent": 1},
    ).sort("created_at", -1).limit(100):
        out.append(_strip_id(c))
    return {"consents": out}


@router.post("/admin/clones/{clone_id}/action")
async def admin_clone_action(clone_id: str, body: AdminCloneActionIn,
                             user: dict = Depends(get_admin_user)):
    clone = await db.avatar_clones.find_one({"_id": clone_id})
    if not clone:
        raise HTTPException(404, "Clone not found")
    action = body.action
    if action == "approve_consent":
        consent = await db.clone_consents.find_one(
            {"clone_id": clone_id, "consent_status": "pending"},
            sort=[("created_at", -1)])
        if not consent:
            raise HTTPException(409, "No pending consent")
        await db.clone_consents.update_one(
            {"_id": consent["_id"]},
            {"$set": {"consent_status": "approved",
                      "admin_notes": body.notes, "approved_at": _now(),
                      "approved_by": user["id"]}})
        await db.avatar_clones.update_one(
            {"_id": clone_id},
            {"$set": {"status": "consent_approved", "updated_at": _now()}})
    elif action == "reject_consent":
        consent = await db.clone_consents.find_one(
            {"clone_id": clone_id, "consent_status": "pending"},
            sort=[("created_at", -1)])
        if not consent:
            raise HTTPException(409, "No pending consent")
        await db.clone_consents.update_one(
            {"_id": consent["_id"]},
            {"$set": {"consent_status": "rejected",
                      "admin_notes": body.notes, "rejected_at": _now(),
                      "rejected_by": user["id"]}})
        await db.avatar_clones.update_one(
            {"_id": clone_id},
            {"$set": {"status": "consent_rejected", "updated_at": _now()}})
    elif action == "disable_clone":
        await db.avatar_clones.update_one(
            {"_id": clone_id},
            {"$set": {"status": "disabled",
                      "disabled_reason": body.notes or "Admin disabled",
                      "updated_at": _now()}})
        # Revoke active consents too
        await db.clone_consents.update_many(
            {"clone_id": clone_id, "consent_status": "approved"},
            {"$set": {"consent_status": "revoked", "revoked_at": _now()}})
    elif action == "enable_clone":
        await db.avatar_clones.update_one(
            {"_id": clone_id},
            {"$set": {"status": "ready" if clone.get("face_model_ref") else "consent_approved",
                      "disabled_reason": None,
                      "updated_at": _now()}})
    else:
        raise HTTPException(400, f"Unknown action: {action}")
    return {"ok": True}


@router.get("/admin/abuse-reports")
async def admin_list_abuse_reports(status: Optional[str] = None,
                                   user: dict = Depends(get_admin_user)):
    q: dict = {}
    if status:
        q["status"] = status
    out = []
    async for r in db.clone_abuse_reports.find(q, {"_id": 1, "reporter_user_id": 1,
                                                    "clone_id": 1, "export_id": 1,
                                                    "reason": 1, "status": 1,
                                                    "admin_notes": 1, "created_at": 1}
                                               ).sort("created_at", -1).limit(200):
        out.append(_strip_id(r))
    return {"reports": out}


@router.post("/admin/abuse-reports/{report_id}/action")
async def admin_abuse_action(report_id: str, body: AdminAbuseActionIn,
                              user: dict = Depends(get_admin_user)):
    if body.status not in {"reviewing", "actioned", "rejected"}:
        raise HTTPException(400, "Invalid status")
    r = await db.clone_abuse_reports.find_one({"_id": report_id})
    if not r:
        raise HTTPException(404, "Report not found")
    await db.clone_abuse_reports.update_one(
        {"_id": report_id},
        {"$set": {"status": body.status, "admin_notes": body.notes,
                  "updated_at": _now(), "updated_by": user["id"]}})
    return {"ok": True}


# ─── Health probe ─────────────────────────────────────────────────────────
@router.get("/health")
async def health():
    return {"ok": True, "service": "avatar_studio", "mode": "vertical_slice_mock"}


# ═════════════════════════════════════════════════════════════════════════
#  ANONYMOUS DEMO WIZARD (2026-05-03 — P0 try-before-signup flow)
#  Founder directive: /avatar-demo lands directly in the wizard. No login
#  before Generate. Login gate ONLY at Save / Download / Create / Export.
#  Session-scoped abuse guard: max 2 generations per session per rolling 24h.
# ═════════════════════════════════════════════════════════════════════════

ANON_SESSION_LIMIT = 2            # per session id per 24h
ANON_SESSION_WINDOW_HOURS = 24


class AnonStudioGenerateRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=80)
    avatar_type: str
    motion_style: str = "talking_head"
    duration_seconds: int = Field(15, ge=5, le=90)
    script: Optional[str] = Field(None, max_length=MAX_SCRIPT_CHARS)
    clone_name: Optional[str] = None
    safety_confirmed: bool = True
    assets: Optional[dict] = None


async def _count_recent_anon_jobs(session_id: str) -> int:
    cutoff = (datetime.now(timezone.utc).timestamp()
              - ANON_SESSION_WINDOW_HOURS * 3600)
    from datetime import datetime as _dt, timezone as _tz
    cutoff_iso = _dt.fromtimestamp(cutoff, tz=_tz.utc).isoformat()
    return await db.avatar_jobs.count_documents({
        "anonymous_session_id": session_id,
        "created_at": {"$gte": cutoff_iso},
    })


@router.post("/studio/anon-mock-generate")
async def studio_anon_mock_generate(body: AnonStudioGenerateRequest, bg: BackgroundTasks):
    """NO auth. Creates an anonymous mock avatar job bound to a client
    session_id so we can rate-limit abuse without accounts. Every job
    returned is_demo_output=true + anonymous=true.

    Login gate is applied ONLY client-side when the user tries to Save /
    Download / Create a real avatar / Export — that's intentional per the
    founder's directive (demo first, signup second)."""
    if body.avatar_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(400, {"code": "INVALID_AVATAR_TYPE",
                                  "message": "Unknown avatar type."})
    if body.motion_style not in ALLOWED_MOTION_STYLES:
        raise HTTPException(400, {"code": "INVALID_MOTION_STYLE",
                                  "message": "Unknown motion style."})
    if not body.safety_confirmed:
        raise HTTPException(400, {"code": "SAFETY_NOT_CONFIRMED",
                                  "message": "Please confirm the safety checklist before generating."})
    if body.script:
        safety = await _run_script_safety_check(body.script)
        if not safety["allowed"]:
            raise HTTPException(400, {"code": safety.get("code", "DISALLOWED_CONTENT"),
                                      "message": safety["reason"]})

    recent = await _count_recent_anon_jobs(body.session_id)
    if recent >= ANON_SESSION_LIMIT:
        raise HTTPException(429, {
            "code": "ANON_LIMIT_REACHED",
            "message": "You've hit the free demo limit. Sign up to keep generating.",
            "limit": ANON_SESSION_LIMIT,
            "window_hours": ANON_SESSION_WINDOW_HOURS,
        })

    total_progress_seconds = _mock_progress_for_duration(body.duration_seconds)
    job = {
        "_id": str(uuid.uuid4()),
        "user_id": None,
        "anonymous_session_id": body.session_id,
        "clone_id": None,
        "job_type": "studio_anon_mock_generate",
        "status": "queued",
        "progress": 0,
        "worker_name": "mock_studio_illusion_worker",
        "input": {
            "avatar_type": body.avatar_type,
            "motion_style": body.motion_style,
            "duration_seconds": body.duration_seconds,
            "clone_name": (body.clone_name or "").strip()[:60] or None,
            "script": (body.script or "").strip()[:MAX_SCRIPT_CHARS] or None,
            "assets": body.assets or {},
            "disclosure_text": DISCLOSURE_TEXT,
        },
        "is_demo_output": True,
        "anonymous": True,
        "demo_label": DEMO_SIMULATED_LABEL,
        "eta_seconds": total_progress_seconds,
        "output_url": None,
        "error_code": None,
        "started_at": None,
        "completed_at": None,
        "created_at": _now(),
    }
    await db.avatar_jobs.insert_one(job)
    bg.add_task(_mock_studio_illusion_worker, job["_id"], total_progress_seconds,
                body.motion_style, body.avatar_type)
    # Funnel: client also emits demo_generate_clicked, but we stamp it server-side
    # so session_id attribution is guaranteed.
    await _emit_funnel("demo_generate_clicked", session_id=body.session_id,
                       meta={"avatar_type": body.avatar_type,
                             "motion_style": body.motion_style,
                             "duration_seconds": body.duration_seconds})
    return {"job_id": job["_id"], "status": "queued",
            "eta_seconds": total_progress_seconds,
            "demo_label": DEMO_SIMULATED_LABEL,
            "is_demo_output": True,
            "anonymous": True,
            "remaining_in_window": max(0, ANON_SESSION_LIMIT - recent - 1)}


@router.get("/studio/anon-jobs/{job_id}")
async def studio_anon_job(job_id: str, session_id: str):
    """Anonymous job polling. Session-scoped — no cross-session leaks.
    Self-heals zombie jobs (e.g. when a hot-reload killed the worker).
    Returns the same shape as the authenticated /jobs/{id}."""
    proj = {"_id": 1, "job_type": 1, "status": 1, "progress": 1,
            "output_url": 1, "error_code": 1, "started_at": 1, "completed_at": 1,
            "created_at": 1, "stage_label": 1, "eta_seconds": 1, "is_demo_output": 1,
            "demo_label": 1, "output_export_id": 1, "input": 1, "anonymous": 1}
    j = await db.avatar_jobs.find_one(
        {"_id": job_id, "anonymous_session_id": session_id}, proj)
    if not j:
        raise HTTPException(404, "Job not found")
    # Self-heal: if the mock worker died mid-flight, finalize now.
    j = await _reconcile_stuck_job_if_needed(j) or j
    # Server-side emit of demo_completed on first observation of terminal state.
    if j.get("status") == "completed":
        already = await db.funnel_events.find_one(
            {"step": "demo_completed", "meta.job_id": job_id})
        if not already:
            await _emit_funnel("demo_completed", session_id=session_id,
                               meta={"job_id": job_id,
                                     "avatar_type": (j.get("input") or {}).get("avatar_type")})
    return _strip_id(j)


# ═════════════════════════════════════════════════════════════════════════
#  AI CLONING STUDIO — Phase 1 MOCKED WIZARD (2026-05-04)
#  Strict: frontend demand-validation illusion. No real AI providers.
#  Auto-completes in 20-60s based on duration. Always returns demo output.
# ═════════════════════════════════════════════════════════════════════════

ALLOWED_AVATAR_TYPES = {"quick_avatar", "voice_matched", "motion", "template"}
ALLOWED_MOTION_STYLES = {"talking_head", "gesture", "full_body", "static"}

# Demo sample outputs — self-hosted on our R2 bucket. Generated by
# /app/backend/scripts/generate_avatar_demo_previews.py — each variant is a
# clearly-labeled "SIMULATED PREVIEW" video (abstract accent-colored
# silhouette + rotating subtitle text: "your face speaking in your voice").
# No external CDN. No random flower or nature footage. Keeps the user's
# mental model: "this is what YOUR avatar will look like in Phase 2".
#
# The ?v=2 cache-buster forces every browser/CDN to re-fetch and invalidates
# any previously-cached <video> blob from the v1 era.
_DEMO_VERSION = "v2"
DEMO_OUTPUT_URLS = {
    "talking_head": f"https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/avatar_demo_v2/talking_head.mp4?v={_DEMO_VERSION}",
    "gesture":      f"https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/avatar_demo_v2/gesture.mp4?v={_DEMO_VERSION}",
    "full_body":    f"https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/avatar_demo_v2/full_body.mp4?v={_DEMO_VERSION}",
    "static":       f"https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/avatar_demo_v2/static.mp4?v={_DEMO_VERSION}",
}

# Hard assertion at import time — boots the process with a visible error if
# anyone ever sneaks an off-theme URL back in. Prevents silent regressions.
for _mk, _mu in DEMO_OUTPUT_URLS.items():
    if "avatar_demo_v2" not in _mu:
        raise RuntimeError(
            f"DEMO_OUTPUT_URLS[{_mk!r}] must point to avatar_demo_v2/*.mp4 "
            f"(got {_mu!r}). Off-theme content = broken trust = dead funnel."
        )

DEMO_SIMULATED_LABEL = "Demo / simulated output"

STUDIO_TEMPLATES = [
    {"id": "intro_reel",     "name": "Intro Reel",         "duration_seconds": 15, "motion_style": "talking_head",
     "description": "Short hook with your face + script. Perfect for YouTube Shorts or Reels."},
    {"id": "course_welcome", "name": "Course Welcome",     "duration_seconds": 30, "motion_style": "talking_head",
     "description": "Warm welcome video for your students. Re-use for every cohort."},
    {"id": "product_demo",   "name": "Product Demo",       "duration_seconds": 45, "motion_style": "gesture",
     "description": "Show off a feature with gestures and energy."},
    {"id": "founder_update", "name": "Founder Update",     "duration_seconds": 60, "motion_style": "talking_head",
     "description": "Weekly update format. Changelog, wins, asks."},
    {"id": "testimonial",    "name": "Testimonial",        "duration_seconds": 20, "motion_style": "talking_head",
     "description": "Customer quote delivered by your avatar with disclosure."},
    {"id": "wellness_tip",   "name": "Daily Wellness Tip", "duration_seconds": 15, "motion_style": "gesture",
     "description": "Bite-sized lifestyle content in your voice."},
]


class StudioGenerateRequest(BaseModel):
    avatar_type: str = Field(..., description="quick_avatar|voice_matched|motion|template")
    motion_style: str = Field("talking_head")
    duration_seconds: int = Field(15, ge=5, le=90)
    script: Optional[str] = Field(None, max_length=MAX_SCRIPT_CHARS)
    template_id: Optional[str] = None
    clone_name: Optional[str] = None
    safety_confirmed: bool = True
    assets: Optional[dict] = None  # { photo_name, voice_sample_name, etc. } — names only, fully mocked


@router.get("/studio/templates")
async def studio_templates():
    """Public read of template catalog for the wizard."""
    return {"templates": STUDIO_TEMPLATES, "motion_styles": sorted(ALLOWED_MOTION_STYLES),
            "avatar_types": sorted(ALLOWED_AVATAR_TYPES)}


def _mock_progress_for_duration(duration: int) -> int:
    """Total seconds of fake progress based on output length.
    Short clips (<20s) → 20s total, Medium (20-45s) → 35s, Long (>45s) → 55s."""
    if duration <= 20:
        return 20
    if duration <= 45:
        return 35
    return 55


@router.post("/studio/mock-generate")
async def studio_mock_generate(body: StudioGenerateRequest, bg: BackgroundTasks,
                                user: dict = Depends(get_current_user)):
    """PHASE 1 MOCK: accepts any valid wizard input, creates a job that
    auto-completes in 20-60s with a demo output URL. No real generation.

    Every output is stamped `is_demo_output: true` and labeled
    `Demo / simulated output` on both the job record and the export row.
    Frontend must surface this label prominently.
    """
    if body.avatar_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(400, {"code": "INVALID_AVATAR_TYPE",
                                  "message": "Unknown avatar type. Pick one of the 4 options."})
    if body.motion_style not in ALLOWED_MOTION_STYLES:
        raise HTTPException(400, {"code": "INVALID_MOTION_STYLE",
                                  "message": "Unknown motion style."})
    if not body.safety_confirmed:
        raise HTTPException(400, {"code": "SAFETY_NOT_CONFIRMED",
                                  "message": "Please confirm the safety checklist before generating."})
    if body.script:
        safety = await _run_script_safety_check(body.script)
        if not safety["allowed"]:
            raise HTTPException(400, {"code": safety.get("code", "DISALLOWED_CONTENT"),
                                      "message": safety["reason"]})

    total_progress_seconds = _mock_progress_for_duration(body.duration_seconds)

    job = {
        "_id": str(uuid.uuid4()),
        "user_id": user["id"],
        "clone_id": None,
        "job_type": "studio_mock_generate",
        "status": "queued",
        "progress": 0,
        "worker_name": "mock_studio_illusion_worker",
        "input": {
            "avatar_type": body.avatar_type,
            "motion_style": body.motion_style,
            "duration_seconds": body.duration_seconds,
            "template_id": body.template_id,
            "clone_name": (body.clone_name or "").strip()[:60] or None,
            "script": (body.script or "").strip()[:MAX_SCRIPT_CHARS] or None,
            "assets": body.assets or {},
            "disclosure_text": DISCLOSURE_TEXT,
        },
        "is_demo_output": True,
        "demo_label": DEMO_SIMULATED_LABEL,
        "eta_seconds": total_progress_seconds,
        "output_url": None,
        "error_code": None,
        "started_at": None,
        "completed_at": None,
        "created_at": _now(),
    }
    await db.avatar_jobs.insert_one(job)
    bg.add_task(_mock_studio_illusion_worker, job["_id"], total_progress_seconds,
                body.motion_style, body.avatar_type)
    return {"job_id": job["_id"], "status": "queued",
            "eta_seconds": total_progress_seconds,
            "demo_label": DEMO_SIMULATED_LABEL,
            "is_demo_output": True}


async def _finalize_mock_job(job_id: str, motion_style: str, avatar_type: str,
                              reason: str = "worker") -> bool:
    """Idempotent finalizer. Safe to call from the worker OR from a
    reconciliation path. Picks up an already-completed job and exits fast.
    Returns True if this call performed the finalize, False if already done
    or job missing."""
    job = await db.avatar_jobs.find_one({"_id": job_id})
    if not job:
        log.warning("[mock_finalize] job %s missing (reason=%s)", job_id, reason)
        return False
    if job.get("status") == "completed":
        return False  # idempotent — someone else already finalized

    demo_url = DEMO_OUTPUT_URLS.get(motion_style, DEMO_OUTPUT_URLS["talking_head"])
    if "avatar_demo_v2" not in demo_url:
        log.error("[mock_finalize] BLOCKED off-theme demo_url=%r for job=%s — "
                  "forcing safe fallback.", demo_url, job_id)
        demo_url = DEMO_OUTPUT_URLS["talking_head"]
    forensic_id = f"DEMO-WM-{uuid.uuid4().hex[:14]}"
    export = {
        "_id": str(uuid.uuid4()),
        "user_id": job.get("user_id"),
        "clone_id": None,
        "job_id": job_id,
        "export_type": "video",
        "file_url": demo_url,
        "visible_label_applied": True,
        "visible_label_text": VISIBLE_LABEL,
        "demo_label": DEMO_SIMULATED_LABEL,
        "is_demo_output": True,
        "forensic_watermark_id": forensic_id,
        "disclosure_text": DISCLOSURE_TEXT,
        "platform": "generic",
        "metadata": {
            "ai_generated": True,
            "ai_provider": "mock_studio_illusion",
            "avatar_type": avatar_type,
            "motion_style": motion_style,
            "watermark_id": forensic_id,
            "visible_label": VISIBLE_LABEL,
            "demo_label": DEMO_SIMULATED_LABEL,
            "is_demo_output": True,
            "disclosure": DISCLOSURE_TEXT,
            "finalize_reason": reason,
        },
        "created_at": _now(),
    }
    await db.avatar_exports.insert_one(export)
    if job.get("user_id"):
        prior = await db.avatar_exports.count_documents({"user_id": job["user_id"]})
        step = "avatar_first_export" if prior <= 1 else "avatar_repeat_export"
        await _emit_funnel(step, user_id=job["user_id"],
                           meta={"export_id": export["_id"], "is_demo_output": True,
                                 "avatar_type": avatar_type,
                                 "finalize_reason": reason})
    await db.avatar_jobs.update_one({"_id": job_id}, {
        "$set": {"status": "completed", "progress": 100,
                 "stage_label": "Ready",
                 "completed_at": _now(), "output_url": demo_url,
                 "output_export_id": export["_id"]}})
    log.info("[mock_finalize] job=%s reason=%s url=%s", job_id, reason, demo_url)
    return True


async def _reconcile_stuck_job_if_needed(j: dict) -> dict:
    """Self-healing reconciliation for Phase-1 mocked demo jobs.

    FastAPI BackgroundTasks are fragile — a backend hot-reload mid-job
    (common in dev) kills in-flight tasks and leaves the job stuck at its
    last progress tick. On every poll we check: is this job running past
    its eta + grace period? If yes, we either auto-complete it (demo output)
    or mark it failed.

    Returns the possibly-updated job dict (always re-fetched on mutation)."""
    if not j:
        return j
    if j.get("status") != "running":
        return j
    started = j.get("started_at")
    if not started:
        return j
    # parse ISO timestamp (stored as isoformat string in _now())
    try:
        if isinstance(started, str):
            from datetime import datetime as _dt
            started_dt = _dt.fromisoformat(started.replace("Z", "+00:00"))
        else:
            started_dt = started
        elapsed = (datetime.now(timezone.utc) - started_dt).total_seconds()
    except Exception:
        return j
    eta = j.get("eta_seconds") or 30
    # Grace: let real jobs finish within eta+5s. Beyond that, reconcile.
    if elapsed < eta + 5:
        return j
    # Hard cap: never let a mock job linger past 65s
    hard_cap = 65
    job_id = j["_id"]
    input_dict = j.get("input") or {}
    motion_style = input_dict.get("motion_style", "talking_head")
    avatar_type = input_dict.get("avatar_type", "quick_avatar")
    reason = "reconcile_overdue" if elapsed < hard_cap else "reconcile_hard_cap"
    log.warning("[reconcile] job=%s elapsed=%.1fs eta=%ds progress=%s — forcing finalize (%s)",
                job_id, elapsed, eta, j.get("progress"), reason)
    finalized = await _finalize_mock_job(job_id, motion_style, avatar_type, reason=reason)
    if finalized:
        return await db.avatar_jobs.find_one({"_id": job_id}) or j
    return j


async def _mock_studio_illusion_worker(job_id: str, total_seconds: int,
                                        motion_style: str, avatar_type: str):
    """Fake the full pipeline: 5 named stages, progress ticks, final demo URL.
    If the worker dies mid-flight (e.g. hot-reload), the reconciliation path
    in the polling endpoints will auto-finalize on the next GET."""
    stages = [
        ("Analyzing your input",       10),
        ("Preparing avatar model",     30),
        ("Synthesizing voice",         55),
        ("Rendering motion + scene",   80),
        ("Applying disclosure label",  95),
    ]
    try:
        await db.avatar_jobs.update_one({"_id": job_id}, {
            "$set": {"status": "running", "progress": 3, "started_at": _now(),
                     "stage_label": stages[0][0]}})
        tick = total_seconds / (len(stages) + 1)
        for label, pct in stages:
            await asyncio.sleep(tick)
            await db.avatar_jobs.update_one({"_id": job_id}, {
                "$set": {"progress": pct, "stage_label": label}})
        await asyncio.sleep(tick)
        await _finalize_mock_job(job_id, motion_style, avatar_type, reason="worker")
    except Exception as e:
        log.exception("mock studio worker failed: %s", e)
        await db.avatar_jobs.update_one({"_id": job_id}, {
            "$set": {"status": "failed", "error_code": "MOCK_STUDIO_FAIL",
                     "stage_label": "Failed — please retry"}})


# ═════════════════════════════════════════════════════════════════════════
#  DEMAND VALIDATION SCAFFOLDING (2026-05-03) — funnel, referral, demo cfg.
#  Founder directive: track only, no AI spend, no Phase 2 dependencies.
#  All emits go to db.funnel_events (shared collection, namespaced step
#  names: avatar_*). Photo Trailer untouched.
# ═════════════════════════════════════════════════════════════════════════

ALLOWED_FUNNEL_STEPS = {
    "avatar_landing_view",
    "avatar_demo_played",
    "avatar_signup_from_avatar",
    "avatar_consent_submitted",
    "avatar_first_export",
    "avatar_repeat_export",
    "avatar_share_click",
    # Anonymous try-before-signup wizard (2026-05-03)
    "demo_generate_clicked",
    "demo_completed",
    "signup_after_demo",
    "retry_after_demo",
    "share_after_demo",
}


async def _emit_funnel(step: str, *, user_id: Optional[str] = None,
                       session_id: Optional[str] = None, meta: Optional[dict] = None) -> None:
    """Append-only emit. Shared funnel_events collection (same one Photo
    Trailer + signup tracking use). Step names are avatar_* namespaced."""
    if step not in ALLOWED_FUNNEL_STEPS:
        return
    try:
        await db.funnel_events.insert_one({
            "_id": str(uuid.uuid4()),
            "step": step,
            "user_id": user_id,
            "session_id": session_id,
            "meta": meta or {},
            "timestamp": _now(),
        })
    except Exception as e:
        log.warning(f"funnel emit failed step={step}: {e}")


class FunnelTrackIn(BaseModel):
    step: str
    session_id: Optional[str] = None
    meta: Optional[dict] = None


@router.post("/funnel/track")
async def funnel_track(body: FunnelTrackIn):
    """Public client-side emit (used for landing/demo/share events).
    Server-side emits (consent, export) happen automatically inside the
    pipeline. Anonymous calls are allowed — session_id is the only key."""
    if body.step not in ALLOWED_FUNNEL_STEPS:
        raise HTTPException(400, "Unknown step")
    await _emit_funnel(body.step, session_id=body.session_id, meta=body.meta)
    return {"ok": True}


class ReferralAttributeIn(BaseModel):
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer_user_id: Optional[str] = None
    landing_path: Optional[str] = None
    landed_at: Optional[str] = None


@router.post("/referral/attribute")
async def referral_attribute(body: ReferralAttributeIn,
                             user: dict = Depends(get_current_user)):
    """Idempotent. First call per user attaches attribution and emits
    avatar_signup_from_avatar. Subsequent calls are no-ops. Never overwrites
    once set, so a returning user can't game attribution by re-hitting the
    demo page."""
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "avatar_attribution": 1})
    if u and u.get("avatar_attribution"):
        return {"ok": True, "attributed": False, "reason": "already_attributed"}
    attribution = {
        "utm_source": (body.utm_source or "")[:80] or None,
        "utm_campaign": (body.utm_campaign or "")[:80] or None,
        "referrer_user_id": body.referrer_user_id,
        "landing_path": (body.landing_path or "")[:200] or None,
        "landed_at": body.landed_at,
        "attributed_at": _now(),
    }
    await db.users.update_one({"id": user["id"]},
                              {"$set": {"avatar_attribution": attribution}})
    await _emit_funnel("avatar_signup_from_avatar", user_id=user["id"], meta=attribution)
    return {"ok": True, "attributed": True}


# ─── Demo videos config (admin-editable, public read) ─────────────────────
DEFAULT_DEMO_CFG = {
    "_id": "default",
    "above_fold_headline": "I didn't shoot this video. My AI avatar did.",
    "above_fold_subhead": "I made 5 reels in 8 minutes using this AI version of me. Every clip is disclosure-labeled, YouTube + EU AI Act safe.",
    "videos": [
        {
            "id": "demo_1",
            "title": "Daily reel — 60 seconds, zero recording",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "poster_url": None,
            "is_placeholder": True,
            "used_by": "Coaches",
            "time_saved": "5 reels in 8 minutes",
            "caption": "This isn't me. I made this with my AI avatar in under a minute.",
        },
        {
            "id": "demo_2",
            "title": "Course welcome — never re-record",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "poster_url": None,
            "is_placeholder": True,
            "used_by": "Course creators",
            "time_saved": "20 cohort welcomes per hour",
            "caption": "I didn't record this. The script changed yesterday — the avatar re-rendered while I slept.",
        },
        {
            "id": "demo_3",
            "title": "Founder update — daily without burnout",
            "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "poster_url": None,
            "is_placeholder": True,
            "used_by": "Founders",
            "time_saved": "Daily updates, zero studio time",
            "caption": "Watch this. My AI avatar posts every weekday. I don't.",
        },
    ],
}


@router.get("/demo-config")
async def demo_config():
    """Public read. Returns the demo videos config — DB doc if present,
    else the placeholder default. Frontend renders this verbatim."""
    cfg = await db.avatar_demo_config.find_one({"_id": "default"})
    out = cfg or DEFAULT_DEMO_CFG
    out = {k: v for k, v in out.items() if k != "_id"}
    return out


class DemoConfigIn(BaseModel):
    above_fold_headline: Optional[str] = None
    above_fold_subhead: Optional[str] = None
    videos: Optional[list] = None


@router.post("/admin/demo-config")
async def admin_set_demo_config(body: DemoConfigIn,
                                user: dict = Depends(get_admin_user)):
    """Admin-only: update demo videos. Founder uses this to swap real
    self-recorded clips in once the 3 are ready."""
    update = {k: v for k, v in body.dict().items() if v is not None}
    if not update:
        raise HTTPException(400, "Nothing to update")
    update["updated_at"] = _now()
    update["updated_by"] = user["id"]
    await db.avatar_demo_config.update_one(
        {"_id": "default"},
        {"$set": {**update, "_id": "default"}},
        upsert=True,
    )
    return {"ok": True}


# ─── Admin funnel table (one tiny row-table, no charts) ───────────────────
@router.get("/admin/funnel-table")
async def admin_funnel_table(days: int = 14, user: dict = Depends(get_admin_user)):
    """Returns the single table the founder asked for:
        day  views  demo_plays  signups  consents  first_exports  repeats  shares
    No fancy charts. Last `days` days, oldest-first."""
    days = max(1, min(days, 60))
    from datetime import timedelta as _td
    from datetime import datetime as _dt
    from datetime import timezone as _tz
    today = _dt.now(_tz.utc).date()
    rows = []
    for offset in range(days - 1, -1, -1):
        d = today - _td(days=offset)
        start = _dt(d.year, d.month, d.day, 0, 0, 0, tzinfo=_tz.utc).isoformat()
        end = _dt(d.year, d.month, d.day, 23, 59, 59, tzinfo=_tz.utc).isoformat()
        cnt = {}
        for step in ("avatar_landing_view", "avatar_demo_played",
                     "avatar_signup_from_avatar", "avatar_consent_submitted",
                     "avatar_first_export", "avatar_repeat_export",
                     "avatar_share_click"):
            cnt[step] = await db.funnel_events.count_documents({
                "step": step, "timestamp": {"$gte": start, "$lte": end},
            })
        rows.append({
            "day": d.isoformat(),
            "views": cnt["avatar_landing_view"],
            "demo_plays": cnt["avatar_demo_played"],
            "signups": cnt["avatar_signup_from_avatar"],
            "consents": cnt["avatar_consent_submitted"],
            "first_exports": cnt["avatar_first_export"],
            "repeats": cnt["avatar_repeat_export"],
            "shares": cnt["avatar_share_click"],
        })
    # Day-7 gate snapshot (uses last 7 days only)
    last7 = rows[-7:] if len(rows) >= 7 else rows
    totals = {k: sum(r[k] for r in last7) for k in
              ("views", "demo_plays", "signups", "consents",
               "first_exports", "repeats", "shares")}
    gate = {
        "users_completed_full_flow": totals["first_exports"],
        "users_repeated": totals["repeats"],
        "organic_shares": totals["shares"],
        "passes_gate": totals["first_exports"] >= 20
                        and totals["repeats"] >= 5
                        and totals["shares"] >= 1,
    }
    return {"rows": rows, "last7_totals": totals, "day7_gate": gate}
