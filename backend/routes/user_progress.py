"""
User Journey Progress API — tracks step completion, feature usage, and guide state.
Source of truth for the product guidance system.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from shared import db
from routes.auth import get_current_user

router = APIRouter(prefix="/user/progress", tags=["user-progress"])

JOURNEY_STEPS = ["create", "customize", "generate", "result", "share"]

class ProgressUpdate(BaseModel):
    step: str
    action: Optional[str] = None
    feature: Optional[str] = None
    meta: Optional[dict] = None

@router.get("")
async def get_progress(user: dict = Depends(get_current_user)):
    user_id = user["id"]
    doc = await db.user_progress.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        doc = {
            "user_id": user_id,
            "current_step": "create",
            "completed_steps": [],
            "features_used": [],
            "guide_dismissed": False,
            "journey_started_at": datetime.now(timezone.utc).isoformat(),
            "last_action_at": datetime.now(timezone.utc).isoformat(),
            "total_generations": 0,
            "total_shares": 0,
        }
        await db.user_progress.insert_one(doc)
        doc.pop("_id", None)
    return {"success": True, "data": doc}


@router.post("/update")
async def update_progress(body: ProgressUpdate, user: dict = Depends(get_current_user)):
    user_id = user["id"]
    now = datetime.now(timezone.utc).isoformat()

    doc = await db.user_progress.find_one({"user_id": user_id})
    if not doc:
        doc = {
            "user_id": user_id,
            "current_step": "create",
            "completed_steps": [],
            "features_used": [],
            "guide_dismissed": False,
            "journey_started_at": now,
            "last_action_at": now,
            "total_generations": 0,
            "total_shares": 0,
        }
        await db.user_progress.insert_one(doc)

    update = {"$set": {"last_action_at": now}}

    if body.step in JOURNEY_STEPS:
        update["$set"]["current_step"] = body.step
        update["$addToSet"] = {"completed_steps": body.step}

    if body.feature:
        update.setdefault("$addToSet", {})["features_used"] = body.feature

    if body.action == "generation_complete":
        update["$inc"] = {"total_generations": 1}
    elif body.action == "share_complete":
        update["$inc"] = {"total_shares": 1}

    if body.meta:
        for k, v in body.meta.items():
            update["$set"][f"meta.{k}"] = v

    await db.user_progress.update_one({"user_id": user_id}, update)

    updated = await db.user_progress.find_one({"user_id": user_id}, {"_id": 0})
    return {"success": True, "data": updated}


@router.post("/dismiss-guide")
async def dismiss_guide(user: dict = Depends(get_current_user)):
    await db.user_progress.update_one(
        {"user_id": user["id"]},
        {"$set": {"guide_dismissed": True, "last_action_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"success": True}
