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
    "I consent to creating an AI avatar of myself for my own content. "
    "I understand all output will be labeled AI-generated."
)
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
    expected = REQUIRED_CONSENT_PHRASE.lower().strip()
    given = consent_phrase.lower().strip()
    # Loose match: 80%+ of expected words must appear in given text
    expected_words = set(re.findall(r"\w+", expected))
    given_words = set(re.findall(r"\w+", given))
    overlap = len(expected_words & given_words) / max(len(expected_words), 1)
    if overlap < 0.8:
        raise HTTPException(400, "Consent phrase doesn't match. Please read the required text.")

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
@router.post("/clones/{clone_id}/voice-profile")
async def create_voice_profile(clone_id: str, user: dict = Depends(get_current_user)):
    clone = await db.avatar_clones.find_one({"_id": clone_id, "user_id": user["id"]})
    if not clone:
        raise HTTPException(404, "Clone not found")
    consent = await db.clone_consents.find_one({"clone_id": clone_id, "consent_status": "approved"})
    if not consent:
        raise HTTPException(403, "Approved consent required")
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
        raise HTTPException(404, "Clone not found")
    consent = await db.clone_consents.find_one({"clone_id": clone_id, "consent_status": "approved"})
    if not consent:
        raise HTTPException(403, "Verified consent required before training")
    if clone["status"] == "ready":
        return {"job_id": None, "status": "already_ready"}
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
    await db.avatar_clones.update_one({"_id": clone_id}, {"$set": {"status": "training", "updated_at": _now()}})
    bg.add_task(_mock_training_worker, job["_id"])
    return {"job_id": job["_id"], "status": "queued"}


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
         "output_url": 1, "error_code": 1, "started_at": 1, "completed_at": 1, "created_at": 1})
    if not j:
        raise HTTPException(404, "Job not found")
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
