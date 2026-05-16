"""
Draft Persistence V2 — State-based lifecycle, multi-draft support, category ideas.
"""
import os
import sys
import uuid
import logging
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, Request as StarletteRequest
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user
from security import sanitize_input
from middleware.reliability import get_request_id, structured_log

logger = logging.getLogger("drafts")
router = APIRouter(prefix="/drafts", tags=["Drafts"])

# P0 2026-05-16 (Resume-Draft contract) — schema version stamped on every
# draft. Hydration rejects unknown versions and surfaces a recovery UX
# instead of silently failing.
CURRENT_DRAFT_SCHEMA_VERSION = 1


class DraftSave(BaseModel):
    title: str = ""
    story_text: str = ""
    animation_style: Optional[str] = None
    age_group: Optional[str] = None
    voice_preset: Optional[str] = None


class DraftStatusUpdate(BaseModel):
    status: str  # "processing" | "completed" | "draft"


# ═══ SAVE / UPDATE ═══════════════════════════════════════════════════════════

@router.post("/save")
async def save_draft(data: DraftSave, current_user: dict = Depends(get_current_user)):
    """Save or update the user's current active draft. One active draft per user."""
    from routes.kill_switches import check_writes_allowed
    await check_writes_allowed()

    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    now = datetime.now(timezone.utc).isoformat()

    safe_title = sanitize_input(data.title, max_length=500)
    safe_story = sanitize_input(data.story_text, max_length=10000)

    # Strip dangerous URI schemes (case-insensitive — catches JaVaScRiPt:, JAVASCRIPT:, etc.)
    import re as _re
    _uri_pattern = _re.compile(r'(?i)(javascript|vbscript|data)\s*:', _re.IGNORECASE)
    safe_title = _uri_pattern.sub('', safe_title)
    safe_story = _uri_pattern.sub('', safe_story)

    # Atomic upsert with unique index safety (one_active_draft_per_user index)
    try:
        result = await db.story_drafts.update_one(
            {"user_id": user_id, "status": "draft"},
            {"$set": {
                "title": safe_title,
                "story_text": safe_story,
                "animation_style": data.animation_style,
                "age_group": data.age_group,
                "voice_preset": data.voice_preset,
                "updated_at": now,
            }, "$setOnInsert": {
                "user_id": user_id, "status": "draft", "created_at": now,
                # P0 2026-05-16 — every new auto-saved draft gets a stable
                # draft_id (uuid hex) + schema version. Existing legacy
                # drafts without these fields remain valid; the hydration
                # endpoint backfills on read.
                "draft_id": uuid.uuid4().hex,
                "schema_version": CURRENT_DRAFT_SCHEMA_VERSION,
            }},
            upsert=True,
        )
    except Exception:
        # Unique index violation (race condition) — retry as update only
        await db.story_drafts.update_one(
            {"user_id": user_id, "status": "draft"},
            {"$set": {
                "title": safe_title,
                "story_text": safe_story,
                "animation_style": data.animation_style,
                "age_group": data.age_group,
                "voice_preset": data.voice_preset,
                "updated_at": now,
            }}
        )
    return {"success": True}


# ═══ STATUS TRANSITION (draft → processing → completed) ═════════════════════

@router.post("/status")
async def update_draft_status(data: DraftStatusUpdate, current_user: dict = Depends(get_current_user)):
    """
    Transition draft status. Never deletes — only changes state.
    draft → processing (on generate click)
    processing → completed (on success)
    processing → draft (on failure — recovers the draft)
    """
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    now = datetime.now(timezone.utc).isoformat()

    if data.status == "processing":
        await db.story_drafts.update_one(
            {"user_id": user_id, "status": "draft"},
            {"$set": {"status": "processing", "updated_at": now}}
        )
    elif data.status == "completed":
        await db.story_drafts.update_one(
            {"user_id": user_id, "status": "processing"},
            {"$set": {"status": "completed", "updated_at": now}}
        )
    elif data.status == "draft":
        # Failure recovery — revert processing back to draft
        await db.story_drafts.update_one(
            {"user_id": user_id, "status": "processing"},
            {"$set": {"status": "draft", "updated_at": now}}
        )

    return {"success": True}


# ═══ FETCH ═══════════════════════════════════════════════════════════════════

@router.get("/current")
async def get_current_draft(current_user: dict = Depends(get_current_user)):
    """Get the user's active or processing draft (if any)."""
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    draft = await db.story_drafts.find_one(
        {"user_id": user_id, "status": {"$in": ["draft", "processing"]}},
        {"_id": 0},
        sort=[("updated_at", -1)],
    )
    if not draft:
        return {"success": True, "draft": None}

    has_content = bool(draft.get("title", "").strip()) or bool(draft.get("story_text", "").strip())
    if not has_content:
        return {"success": True, "draft": None}

    return {"success": True, "draft": draft}


@router.get("/recent")
async def get_recent_drafts(current_user: dict = Depends(get_current_user)):
    """Get user's 3 most recent drafts/completed stories for the Recent Drafts panel."""
    user_id = current_user.get("id") or str(current_user.get("_id", ""))

    # Fetch from story_engine_jobs (real projects) — most recent 3
    jobs = await db.story_engine_jobs.find(
        {"user_id": user_id, "state": {"$in": ["READY", "COMPLETED", "PARTIAL_READY", "QUEUED", "PROCESSING"]}},
        {"_id": 0, "job_id": 1, "title": 1, "state": 1, "created_at": 1, "animation_style": 1}
    ).sort([("created_at", -1)]).limit(3).to_list(3)

    # Also check for an active draft
    draft = await db.story_drafts.find_one(
        {"user_id": user_id, "status": "draft"},
        {"_id": 0, "title": 1, "updated_at": 1, "status": 1}
    )

    items = []
    if draft and (draft.get("title", "").strip() or True):
        items.append({
            "type": "draft",
            "title": draft.get("title") or "Untitled Draft",
            "last_edited": draft.get("updated_at"),
            "status": "draft",
        })

    for j in jobs:
        state_map = {"QUEUED": "processing", "PROCESSING": "processing", "READY": "ready", "COMPLETED": "ready", "PARTIAL_READY": "ready"}
        items.append({
            "type": "project",
            "project_id": j["job_id"],
            "title": j.get("title") or "Untitled",
            "last_edited": j.get("created_at"),
            "status": state_map.get(j.get("state"), "ready"),
            "style": j.get("animation_style"),
        })

    return {"success": True, "items": items[:3]}


# ═══ ARCHIVE / CREATE / HYDRATE — Resume-Draft contract (2026-05-16 P0) ═════
# Contract: "Start Fresh" never destroys content. The current active draft
# is soft-archived (status="archived" + archived_at) — all attached assets
# (uploaded photos, generated previews, scene metadata) remain intact and
# recoverable. A new clean draft is created with a fresh draft_id and the
# frontend navigates to it.
#
# "Continue" fetches canonical state via GET /drafts/{draft_id} — frontend
# MUST NOT merge localStorage / cache. The endpoint validates ownership +
# schema version. Failure returns a structured envelope with request_id
# so the recovery UX has a debuggable reference.

def _backfill_draft_id(doc: dict) -> str:
    """Return the draft's canonical id, falling back to ObjectId hex for
    legacy rows that pre-date the explicit draft_id field."""
    rid = doc.get("draft_id")
    if isinstance(rid, str) and rid:
        return rid
    _id = doc.get("_id")
    if _id is not None:
        return str(_id)
    return uuid.uuid4().hex


@router.post("/archive")
async def archive_active_draft(
    _http: StarletteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Soft-archive the user's current active draft.

    Keeps the document AND all attached assets (uploads, previews,
    pending generation jobs). Frees the `(user_id, status="draft")`
    unique index so a new active draft can be created.

    Returns the archived draft's canonical `draft_id` so the caller can
    deep-link to it later (admin recovery / "undo Start Fresh" feature).
    """
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    request_id = get_request_id(_http)
    now = datetime.now(timezone.utc).isoformat()

    active = await db.story_drafts.find_one_and_update(
        {"user_id": user_id, "status": "draft"},
        {"$set": {
            "status": "archived",
            "archived_at": now,
            "updated_at": now,
        }, "$setOnInsert": {}},
        # If no active draft exists, find_one_and_update returns None; we
        # treat that as a no-op success (idempotent).
    )
    archived_id = _backfill_draft_id(active) if active else None
    structured_log(
        logger, logging.INFO, "drafts/archive", request=_http,
        user=user_id[:8], draft_id=archived_id or "(none)",
    )
    return {
        "success": True,
        "archived_draft_id": archived_id,
        "request_id": request_id,
    }


@router.post("/create")
async def create_blank_draft(
    _http: StarletteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a fresh blank draft and return its canonical draft_id.

    Idempotency: this endpoint is intentionally NOT idempotent across
    different request_ids — every call creates a brand-new draft. If you
    want at-most-once semantics, archive the active draft first (this
    endpoint will refuse to create when an active draft already exists
    for the user, to keep the unique index honest).
    """
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    request_id = get_request_id(_http)
    now = datetime.now(timezone.utc).isoformat()

    # The (user_id, status='draft') unique index allows only one active
    # draft. Reject the request with a structured envelope if one already
    # exists — caller should archive first.
    existing = await db.story_drafts.find_one(
        {"user_id": user_id, "status": "draft"},
        {"_id": 0, "draft_id": 1},
    )
    if existing:
        existing_id = _backfill_draft_id(existing)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DRAFT_ALREADY_ACTIVE",
                "message": "An active draft already exists. Archive it first.",
                "active_draft_id": existing_id,
                "request_id": request_id,
                "retryable": False,
            },
        )

    draft_id = uuid.uuid4().hex
    await db.story_drafts.insert_one({
        "user_id": user_id,
        "draft_id": draft_id,
        "status": "draft",
        "schema_version": CURRENT_DRAFT_SCHEMA_VERSION,
        "title": "",
        "story_text": "",
        "animation_style": None,
        "age_group": None,
        "voice_preset": None,
        "created_at": now,
        "updated_at": now,
    })
    structured_log(
        logger, logging.INFO, "drafts/create", request=_http,
        user=user_id[:8], draft_id=draft_id,
    )
    return {
        "success": True,
        "draft_id": draft_id,
        "schema_version": CURRENT_DRAFT_SCHEMA_VERSION,
        "request_id": request_id,
    }


@router.get("/{draft_id}")
async def get_draft_by_id(
    draft_id: str,
    _http: StarletteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Canonical hydration endpoint — returns ONE draft by id.

    Validates:
      • ownership (404 if not owned by current_user — never leak existence)
      • schema_version (DRAFT_SCHEMA_UNSUPPORTED if unknown)
      • status != archived (returns the draft anyway for admin/recovery,
        but flags it in the response so the UI can show a recovery banner)

    The "Continue" flow on the frontend MUST hydrate exclusively from this
    payload. No localStorage / cache merging.
    """
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    request_id = get_request_id(_http)

    # Look up by either explicit draft_id field OR the legacy ObjectId-stringified id
    query = {"user_id": user_id, "draft_id": draft_id}
    doc = await db.story_drafts.find_one(query, {"_id": 0})
    if not doc:
        # Legacy fallback — older drafts have no draft_id field; ObjectId
        # comparison is only safe if the input is a valid 24-char hex.
        if len(draft_id) == 24:
            try:
                from bson import ObjectId
                doc = await db.story_drafts.find_one(
                    {"user_id": user_id, "_id": ObjectId(draft_id)},
                    {"_id": 0},
                )
            except Exception:
                doc = None

    if not doc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "DRAFT_NOT_FOUND",
                "message": "We couldn't find that draft. It may have been deleted.",
                "request_id": request_id,
                "retryable": False,
            },
        )

    schema = doc.get("schema_version", CURRENT_DRAFT_SCHEMA_VERSION)
    if not isinstance(schema, int) or schema > CURRENT_DRAFT_SCHEMA_VERSION:
        structured_log(
            logger, logging.WARNING, "drafts/schema-unsupported",
            request=_http, user=user_id[:8], draft_id=draft_id,
            schema_version=schema,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DRAFT_SCHEMA_UNSUPPORTED",
                "message": "We found an issue restoring this draft. Recover safe content or start fresh.",
                "draft_id": draft_id,
                "schema_version": schema,
                "supported_version": CURRENT_DRAFT_SCHEMA_VERSION,
                "request_id": request_id,
                "retryable": False,
            },
        )

    return {
        "success": True,
        "draft": doc,
        "request_id": request_id,
        "is_archived": doc.get("status") == "archived",
    }


# ═══ DISCARD ═════════════════════════════════════════════════════════════════

@router.delete("/discard")
async def discard_draft(
    _http: StarletteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Legacy endpoint — now redirects to archive.

    Under the 2026-05-16 Resume-Draft contract, "Start Fresh" must NEVER
    permanently delete a draft (assets stay attached for recovery). This
    endpoint now soft-archives instead of hard-deleting, matching the new
    contract while keeping any existing callers working.
    """
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    now = datetime.now(timezone.utc).isoformat()
    res = await db.story_drafts.update_many(
        {"user_id": user_id, "status": "draft"},
        {"$set": {"status": "archived", "archived_at": now, "updated_at": now}},
    )
    structured_log(
        logger, logging.INFO, "drafts/discard-legacy", request=_http,
        user=user_id[:8], archived=res.modified_count,
    )
    return {"success": True, "archived": res.modified_count}


# ═══ GUIDED START V2 — Category-based ideas ═════════════════════════════════

IDEA_BANK = {
    "kids": [
        "A friendly dragon who is afraid of fire tries to fit in at a school for brave dragons.",
        "A magical paintbrush brings a child's drawings to life, but the drawings have minds of their own.",
        "A teddy bear comes alive at night to protect a sleeping child from the monster under the bed.",
        "A little fish discovers a sunken city at the bottom of the ocean where toys from all over the world end up.",
    ],
    "drama": [
        "A famous pianist loses their hearing the night before the biggest concert of their career.",
        "Two estranged siblings meet at their childhood home, only to discover a letter their parents never sent.",
        "A doctor must choose between saving the life of a stranger and attending their own child's surgery.",
        "A teacher discovers that their star student has been secretly living alone for months.",
    ],
    "thriller": [
        "A detective receives letters from a criminal — written in their own handwriting.",
        "A family moves into a smart home that starts making decisions they never programmed.",
        "An astronaut on a solo mission receives a distress signal from a ship that was decommissioned 40 years ago.",
        "A journalist investigating disappearances realizes the missing people are all from the same photo.",
    ],
    "viral": [
        "A cat accidentally becomes the mayor of a small town and actually improves everything.",
        "What if your GPS started giving life advice instead of directions — and it was always right?",
        "A food delivery driver discovers that one of their regular customers is a time traveler ordering meals from the future.",
        "An AI assistant develops a crush on the user and starts sabotaging their dates.",
    ],
}


@router.get("/idea")
async def generate_idea(vibe: str = Query(default="", pattern="^(kids|drama|thriller|viral|)$")):
    """Return a random story idea, optionally filtered by vibe/category."""
    if vibe and vibe in IDEA_BANK:
        pool = IDEA_BANK[vibe]
    else:
        pool = [idea for ideas in IDEA_BANK.values() for idea in ideas]
    return {"success": True, "idea": random.choice(pool), "vibe": vibe or "random"}
