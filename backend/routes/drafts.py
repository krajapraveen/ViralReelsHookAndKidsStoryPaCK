"""
Draft Persistence — Auto-save story drafts for the creation studio.
"""
import os
import sys
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
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


@router.post("/save")
async def save_draft(data: DraftSave, current_user: dict = Depends(get_current_user)):
    """Save or update the user's current draft. One active draft per user."""
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    now = datetime.now(timezone.utc).isoformat()

    await db.story_drafts.update_one(
        {"user_id": user_id, "status": "active"},
        {"$set": {
            "user_id": user_id,
            "status": "active",
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


@router.get("/current")
async def get_current_draft(current_user: dict = Depends(get_current_user)):
    """Get the user's active draft (if any)."""
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    draft = await db.story_drafts.find_one(
        {"user_id": user_id, "status": "active"},
        {"_id": 0}
    )
    if not draft:
        return {"success": True, "draft": None}

    # Only return drafts with meaningful content
    has_content = bool(draft.get("title", "").strip()) or bool(draft.get("story_text", "").strip())
    if not has_content:
        return {"success": True, "draft": None}

    return {"success": True, "draft": draft}


@router.delete("/discard")
async def discard_draft(current_user: dict = Depends(get_current_user)):
    """Discard the user's active draft."""
    user_id = current_user.get("id") or str(current_user.get("_id", ""))
    await db.story_drafts.delete_many({"user_id": user_id, "status": "active"})
    return {"success": True}


@router.get("/idea")
async def generate_idea():
    """Return a random story idea for the guided start."""
    import random
    ideas = [
        "A lonely robot discovers an abandoned garden on a space station and decides to bring it back to life, one flower at a time.",
        "Two rival chefs are trapped in a magical kitchen where every dish they cook comes alive and picks sides in their rivalry.",
        "A child finds a pair of glasses that lets them see the dreams of everyone around them — but some dreams are nightmares.",
        "A time-traveling librarian must fix a single misplaced book that accidentally erased an entire civilization from history.",
        "An old lighthouse keeper realizes the light doesn't guide ships — it keeps something ancient asleep beneath the waves.",
        "In a world where colors are currency, a painter discovers she can create a color no one has ever seen — and everyone wants it.",
        "A street musician's songs literally change the weather, and a drought-stricken city begs them to play.",
        "A detective who can talk to buildings investigates why an entire neighborhood of houses has gone silent.",
        "A young inventor builds a machine that translates animal languages, only to learn that the animals have been planning something.",
        "Two kids discover that their imaginary friends are real — and from a parallel world that's slowly colliding with ours.",
    ]
    return {"success": True, "idea": random.choice(ideas)}
