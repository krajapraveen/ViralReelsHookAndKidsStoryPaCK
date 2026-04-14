"""
Draft Persistence V2 — State-based lifecycle, multi-draft support, category ideas.
"""
import os
import sys
import logging
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user

logger = logging.getLogger("drafts")
router = APIRouter(prefix="/drafts", tags=["Drafts"])


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
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    now = datetime.now(timezone.utc).isoformat()

    await db.story_drafts.update_one(
        {"user_id": user_id, "status": "draft"},
        {"$set": {
            "user_id": user_id,
            "status": "draft",
            "title": data.title,
            "story_text": data.story_text,
            "animation_style": data.animation_style,
            "age_group": data.age_group,
            "voice_preset": data.voice_preset,
            "updated_at": now,
        }, "$setOnInsert": {"created_at": now}},
        upsert=True,
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


# ═══ DISCARD ═════════════════════════════════════════════════════════════════

@router.delete("/discard")
async def discard_draft(current_user: dict = Depends(get_current_user)):
    """Discard the user's active draft (only drafts, not processing/completed)."""
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    await db.story_drafts.delete_many({"user_id": user_id, "status": "draft"})
    return {"success": True}


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
