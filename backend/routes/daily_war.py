"""
Daily Story War Engine — Bounded 24h competitive story creation.

Collection: daily_wars
States: scheduled → active → ended → winner_declared

War entries are BRANCH-ONLY continuations from the daily root story.
Scoring is WAR-LOCAL: only metrics earned during the active war window count.

Tie-break: war_score > continues > shares > earlier entered_at
Winner eligibility: min 20 views AND (1+ shares OR 1+ continues)
"""
import os
import sys
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user, get_optional_user, get_admin_user

logger = logging.getLogger("daily_war")
router = APIRouter(prefix="/war", tags=["Daily Story War"])


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

WAR_DURATION_HOURS = 24
WAR_STATES = ("scheduled", "active", "ended", "winner_declared")
MIN_VIEWS_FOR_WINNER = 20
MIN_ENGAGEMENT_FOR_WINNER = 1  # shares + continues >= 1


# ═══════════════════════════════════════════════════════════════
# WAR SCORING — Isolated to war window
# ═══════════════════════════════════════════════════════════════

def compute_war_score(war_views: int, war_shares: int, war_continues: int) -> float:
    """War-local ranking score. Same weights as battle but NO depth/recency modifiers."""
    return (war_continues * 5.0) + (war_shares * 3.0) + (war_views * 1.0)


def is_winner_eligible(war_views: int, war_shares: int, war_continues: int) -> bool:
    """Minimum quality threshold for winner eligibility."""
    return war_views >= MIN_VIEWS_FOR_WINNER and (war_shares + war_continues) >= MIN_ENGAGEMENT_FOR_WINNER


def deterministic_rank_key(entry: dict) -> tuple:
    """Sort key for deterministic tie-breaking.
    Higher score first, then more continues, more shares, earlier entry.
    Returns negative values so sorted() gives descending order for scores.
    """
    return (
        -(entry.get("war_score", 0)),
        -(entry.get("war_continues", 0)),
        -(entry.get("war_shares", 0)),
        entry.get("war_entered_at", "9999"),  # earlier = better
    )


# ═══════════════════════════════════════════════════════════════
# STATE MACHINE
# ═══════════════════════════════════════════════════════════════

VALID_TRANSITIONS = {
    "scheduled": ["active"],
    "active": ["ended"],
    "ended": ["winner_declared"],
    "winner_declared": [],
}


async def transition_war(war_id: str, from_state: str, to_state: str) -> bool:
    """Atomic state transition with guard."""
    if to_state not in VALID_TRANSITIONS.get(from_state, []):
        logger.warning(f"[WAR] Invalid transition: {from_state} → {to_state} for war {war_id}")
        return False

    result = await db.daily_wars.update_one(
        {"war_id": war_id, "state": from_state},
        {"$set": {"state": to_state, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 1:
        logger.info(f"[WAR] Transitioned {war_id}: {from_state} → {to_state}")
        return True
    return False


# ═══════════════════════════════════════════════════════════════
# LEADERBOARD COMPUTATION
# ═══════════════════════════════════════════════════════════════

async def compute_war_leaderboard(war_id: str, current_user_id: str = None):
    """Build the full leaderboard for a war with deterministic ranking."""
    entries = await db.story_engine_jobs.find(
        {"war_id": war_id, "war_entry": True},
        {
            "_id": 0, "job_id": 1, "title": 1, "user_id": 1, "state": 1,
            "war_score": 1, "war_views": 1, "war_shares": 1, "war_continues": 1,
            "war_entered_at": 1, "thumbnail_url": 1, "animation_style": 1,
        }
    ).to_list(200)

    # Sort with deterministic tie-breaking
    entries.sort(key=deterministic_rank_key)

    # Assign ranks
    for i, e in enumerate(entries):
        e["war_rank"] = i + 1
        e["eligible"] = is_winner_eligible(
            e.get("war_views", 0), e.get("war_shares", 0), e.get("war_continues", 0)
        )

    # Enrich with creator names
    user_ids = list({e.get("user_id") for e in entries if e.get("user_id")})
    user_map = {}
    if user_ids:
        users = await db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "name": 1, "email": 1}
        ).to_list(100)
        user_map = {u["id"]: u.get("name") or u.get("email", "").split("@")[0] for u in users}

    for e in entries:
        e["creator_name"] = user_map.get(e.get("user_id"), "Anonymous")

    # Compute gap-to-#1
    top_score = entries[0]["war_score"] if entries else 0
    top_continues = entries[0].get("war_continues", 0) if entries else 0
    for e in entries:
        e["gap_score"] = round(top_score - e.get("war_score", 0), 1)
        e["gap_continues"] = top_continues - e.get("war_continues", 0)

    # Find current user's entry
    user_rank = None
    user_entry = None
    if current_user_id:
        for e in entries:
            if e.get("user_id") == current_user_id:
                user_rank = e["war_rank"]
                user_entry = e
                break

    return {
        "entries": entries,
        "total_entries": len(entries),
        "user_rank": user_rank,
        "user_entry": user_entry,
    }


# ═══════════════════════════════════════════════════════════════
# WINNER DECLARATION
# ═══════════════════════════════════════════════════════════════

async def declare_winner(war_id: str):
    """Compute and declare the winner of a war. Only called when state = ended."""
    war = await db.daily_wars.find_one({"war_id": war_id}, {"_id": 0})
    if not war or war.get("state") != "ended":
        return None

    lb = await compute_war_leaderboard(war_id)
    entries = lb["entries"]

    # Find first eligible entry
    winner = None
    for e in entries:
        if e.get("eligible"):
            winner = e
            break

    now = datetime.now(timezone.utc).isoformat()

    if winner:
        update = {
            "winner_job_id": winner["job_id"],
            "winner_user_id": winner["user_id"],
            "winner_title": winner.get("title", "Untitled"),
            "winner_rank": 1,
            "winner_score": winner.get("war_score", 0),
            "winner_creator_name": winner.get("creator_name", "Anonymous"),
            "total_entries": lb["total_entries"],
            "declared_at": now,
        }
    else:
        # No eligible winner
        update = {
            "winner_job_id": None,
            "winner_user_id": None,
            "winner_title": None,
            "winner_rank": None,
            "winner_score": 0,
            "total_entries": lb["total_entries"],
            "no_eligible_winner": True,
            "declared_at": now,
        }

    await db.daily_wars.update_one({"war_id": war_id}, {"$set": update})
    success = await transition_war(war_id, "ended", "winner_declared")

    if success and winner:
        # Notify winner
        await db.notifications.insert_one({
            "user_id": winner["user_id"],
            "type": "war_won",
            "title": "You WON today's Story War!",
            "message": f"Your version \"{winner.get('title', '')}\" claimed #1. You'll be featured on the homepage.",
            "data": {
                "war_id": war_id,
                "deep_link": f"/app/story-battle/{war.get('root_story_id', '')}",
            },
            "read": False,
            "created_at": now,
        })
        logger.info(f"[WAR] Winner declared for {war_id}: {winner['job_id']}")

        # Notify all other participants
        for e in entries:
            if e["user_id"] != winner["user_id"]:
                await db.notifications.insert_one({
                    "user_id": e["user_id"],
                    "type": "war_ended",
                    "title": f"Today's Story War ended. You placed #{e['war_rank']}",
                    "message": f"\"{winner.get('title', '')}\" by {winner.get('creator_name', '')} took #1. Try again tomorrow.",
                    "data": {
                        "war_id": war_id,
                        "your_rank": e["war_rank"],
                        "deep_link": f"/app/story-battle/{war.get('root_story_id', '')}",
                    },
                    "read": False,
                    "created_at": now,
                })

    return winner


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE — Auto-transition scheduled → active, active → ended
# ═══════════════════════════════════════════════════════════════

async def check_war_lifecycle():
    """Called periodically to advance war states based on time."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # scheduled → active
    scheduled = await db.daily_wars.find(
        {"state": "scheduled", "start_time": {"$lte": now_iso}},
        {"_id": 0, "war_id": 1}
    ).to_list(10)
    for w in scheduled:
        await transition_war(w["war_id"], "scheduled", "active")

    # active → ended
    active = await db.daily_wars.find(
        {"state": "active", "end_time": {"$lte": now_iso}},
        {"_id": 0, "war_id": 1}
    ).to_list(10)
    for w in active:
        success = await transition_war(w["war_id"], "active", "ended")
        if success:
            await declare_winner(w["war_id"])


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class SeedWarRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    story_text: str = Field(..., min_length=50, max_length=5000)
    animation_style: str = Field(default="cartoon_2d")
    start_delay_minutes: int = Field(default=0, ge=0, le=1440)


class EnterWarRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    story_text: str = Field(..., min_length=50, max_length=10000)
    animation_style: str = Field(default="cartoon_2d")
    voice_preset: str = Field(default="narrator_warm")
    quality_mode: str = Field(default="balanced")


class WarMetricRequest(BaseModel):
    job_id: str
    metric: str = Field(..., pattern="^(views|shares|continues)$")


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/current")
async def get_current_war(current_user: dict = Depends(get_optional_user)):
    """Get the active (or most recent) war with full leaderboard."""
    # Check lifecycle first
    await check_war_lifecycle()

    # Find active war
    war = await db.daily_wars.find_one(
        {"state": "active"},
        {"_id": 0}
    )

    if not war:
        # Try most recent ended/winner_declared
        war = await db.daily_wars.find_one(
            {"state": {"$in": ["ended", "winner_declared"]}},
            {"_id": 0},
            sort=[("end_time", -1)]
        )

    if not war:
        # Try scheduled
        war = await db.daily_wars.find_one(
            {"state": "scheduled"},
            {"_id": 0},
            sort=[("start_time", 1)]
        )

    if not war:
        return {"success": True, "war": None, "leaderboard": None}

    # Compute time left
    time_left_seconds = 0
    if war.get("state") == "active" and war.get("end_time"):
        try:
            end = datetime.fromisoformat(war["end_time"].replace("Z", "+00:00"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            time_left_seconds = max(0, int((end - datetime.now(timezone.utc)).total_seconds()))
        except (ValueError, AttributeError):
            pass

    # Build leaderboard
    user_id = None
    if current_user:
        user_id = current_user.get("id") or str(current_user.get("_id"))

    leaderboard = await compute_war_leaderboard(war["war_id"], user_id)

    # Yesterday's rank for re-entry messaging
    yesterday_rank = None
    if user_id:
        yesterday_war = await db.daily_wars.find_one(
            {
                "state": "winner_declared",
                "war_id": {"$ne": war["war_id"]},
            },
            {"_id": 0, "war_id": 1},
            sort=[("end_time", -1)]
        )
        if yesterday_war:
            yesterday_entry = await db.story_engine_jobs.find_one(
                {"war_id": yesterday_war["war_id"], "war_entry": True, "user_id": user_id},
                {"_id": 0, "war_rank": 1}
            )
            if yesterday_entry:
                yesterday_rank = yesterday_entry.get("war_rank")

    return {
        "success": True,
        "war": {
            "war_id": war["war_id"],
            "state": war["state"],
            "root_story_id": war.get("root_story_id"),
            "root_title": war.get("root_title"),
            "root_story_text": war.get("root_story_text", "")[:300],
            "start_time": war.get("start_time"),
            "end_time": war.get("end_time"),
            "time_left_seconds": time_left_seconds,
            "total_entries": leaderboard["total_entries"],
            "winner_job_id": war.get("winner_job_id"),
            "winner_title": war.get("winner_title"),
            "winner_creator_name": war.get("winner_creator_name"),
            "winner_score": war.get("winner_score"),
            "no_eligible_winner": war.get("no_eligible_winner", False),
        },
        "leaderboard": leaderboard,
        "yesterday_rank": yesterday_rank,
    }


@router.post("/enter")
async def enter_war(
    request: EnterWarRequest,
    current_user: dict = Depends(get_current_user),
):
    """Enter the active Daily Story War. BRANCH-ONLY from the war root."""
    user_id = current_user.get("id") or str(current_user.get("_id"))

    # Check lifecycle
    await check_war_lifecycle()

    # Find active war
    war = await db.daily_wars.find_one({"state": "active"}, {"_id": 0})
    if not war:
        raise HTTPException(status_code=400, detail="No active Story War right now. Check back soon.")

    war_id = war["war_id"]
    root_id = war["root_story_id"]

    # Check if user already entered this war
    existing = await db.story_engine_jobs.find_one(
        {"war_id": war_id, "war_entry": True, "user_id": user_id},
        {"_id": 0, "job_id": 1}
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"You already entered this war. Your entry: {existing['job_id']}"
        )

    # Create BRANCH from war root (hard-enforced)
    from services.story_engine.pipeline import create_job, run_pipeline

    result = await create_job(
        user_id=user_id,
        story_text=request.story_text,
        title=request.title,
        style_id=request.animation_style,
        language="en",
        age_group="all_ages",
        parent_job_id=root_id,
        story_chain_id=root_id,
    )

    if not result.get("success"):
        error = result.get("error", "Job creation failed")
        if error == "insufficient_credits":
            cc = result.get("credit_check", {})
            raise HTTPException(status_code=402, detail=f"Insufficient credits. Required: {cc.get('required', 0)}")
        raise HTTPException(status_code=400, detail=error)

    job_id = result["job_id"]
    now = datetime.now(timezone.utc).isoformat()

    # Set multiplayer graph fields — BRANCH type
    from routes.story_multiplayer import ensure_multiplayer_fields
    await ensure_multiplayer_fields(job_id, root_id, "branch")

    # Set war-specific fields
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "war_id": war_id,
            "war_entry": True,
            "war_score": 0.0,
            "war_views": 0,
            "war_shares": 0,
            "war_continues": 0,
            "war_rank": 0,
            "war_entered_at": now,
            "animation_style": request.animation_style,
            "voice_preset": request.voice_preset,
            "quality_mode": request.quality_mode,
        }}
    )

    # Increment war entry count
    await db.daily_wars.update_one(
        {"war_id": war_id},
        {"$inc": {"total_entries": 1}}
    )

    # Run pipeline
    asyncio.create_task(run_pipeline(job_id))

    return {
        "success": True,
        "job_id": job_id,
        "war_id": war_id,
        "continuation_type": "branch",
        "message": "War entry created! Your version is being generated. Check the leaderboard for your rank.",
    }


@router.post("/increment-metric")
async def war_increment_metric(request: WarMetricRequest):
    """Increment a war entry's war-local metric and refresh war_score."""
    # Verify this is a war entry
    entry = await db.story_engine_jobs.find_one(
        {"job_id": request.job_id, "war_entry": True},
        {"_id": 0, "war_id": 1, "war_views": 1, "war_shares": 1, "war_continues": 1, "user_id": 1}
    )
    if not entry:
        raise HTTPException(status_code=404, detail="War entry not found")

    # Check war is still active
    war = await db.daily_wars.find_one(
        {"war_id": entry["war_id"]},
        {"_id": 0, "state": 1}
    )
    if not war or war.get("state") != "active":
        raise HTTPException(status_code=400, detail="This war has ended. Metrics are frozen.")

    field_map = {"views": "war_views", "shares": "war_shares", "continues": "war_continues"}
    field = field_map.get(request.metric)
    if not field:
        raise HTTPException(status_code=400, detail="Invalid metric")

    # Atomic increment
    await db.story_engine_jobs.update_one(
        {"job_id": request.job_id},
        {"$inc": {field: 1}}
    )

    # Refresh war_score
    updated = await db.story_engine_jobs.find_one(
        {"job_id": request.job_id},
        {"_id": 0, "war_views": 1, "war_shares": 1, "war_continues": 1}
    )
    new_score = compute_war_score(
        updated.get("war_views", 0),
        updated.get("war_shares", 0),
        updated.get("war_continues", 0),
    )
    await db.story_engine_jobs.update_one(
        {"job_id": request.job_id},
        {"$set": {"war_score": new_score}}
    )

    # Check for overtake and send war-specific notifications
    await check_war_overtake(entry["war_id"], request.job_id, entry.get("user_id"))

    # Also increment the global metric for the story
    global_field = {"views": "total_views", "shares": "total_shares", "continues": "total_children"}
    await db.story_engine_jobs.update_one(
        {"job_id": request.job_id},
        {"$inc": {global_field.get(request.metric, "total_views"): 1}}
    )

    return {"success": True, "job_id": request.job_id, "metric": request.metric, "war_score": new_score}


@router.get("/history")
async def get_war_history(
    limit: int = Query(default=10, le=30),
    current_user: dict = Depends(get_optional_user),
):
    """Past war results with winners."""
    wars = await db.daily_wars.find(
        {"state": "winner_declared"},
        {"_id": 0, "war_id": 1, "root_title": 1, "start_time": 1, "end_time": 1,
         "winner_title": 1, "winner_creator_name": 1, "winner_score": 1,
         "total_entries": 1, "no_eligible_winner": 1}
    ).sort("end_time", -1).limit(limit).to_list(limit)

    # If user is logged in, find their ranks in past wars
    user_id = None
    if current_user:
        user_id = current_user.get("id") or str(current_user.get("_id"))

    if user_id:
        for w in wars:
            lb = await compute_war_leaderboard(w["war_id"], user_id)
            w["your_rank"] = lb.get("user_rank")

    return {"success": True, "wars": wars, "total": len(wars)}


@router.get("/yesterday")
async def get_yesterday_results(current_user: dict = Depends(get_current_user)):
    """Get the user's rank from the most recently completed war."""
    user_id = current_user.get("id") or str(current_user.get("_id"))

    war = await db.daily_wars.find_one(
        {"state": "winner_declared"},
        {"_id": 0},
        sort=[("end_time", -1)]
    )
    if not war:
        return {"success": True, "yesterday_war": None}

    # Compute leaderboard to get accurate rank
    lb = await compute_war_leaderboard(war["war_id"], user_id)

    return {
        "success": True,
        "yesterday_war": {
            "war_id": war["war_id"],
            "root_title": war.get("root_title"),
            "winner_title": war.get("winner_title"),
            "winner_creator_name": war.get("winner_creator_name"),
            "total_entries": lb["total_entries"],
            "your_rank": lb.get("user_rank"),
            "your_score": lb["user_entry"].get("war_score") if lb.get("user_entry") else None,
            "your_title": lb["user_entry"].get("title") if lb.get("user_entry") else None,
            "you_participated": lb.get("user_entry") is not None,
        },
    }


# ═══════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/admin/seed")
async def admin_seed_war(request: SeedWarRequest, current_user: dict = Depends(get_admin_user)):
    """Admin: Create a new Daily Story War with a root story."""
    # Check no active war exists
    active = await db.daily_wars.find_one({"state": {"$in": ["scheduled", "active"]}})
    if active:
        raise HTTPException(status_code=409, detail=f"A war is already {active['state']}. End it first.")

    war_id = f"war-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    start_time = now + timedelta(minutes=request.start_delay_minutes)
    end_time = start_time + timedelta(hours=WAR_DURATION_HOURS)

    # Create the war root story as a READY job (it's the seed, not a generated video)
    root_job_id = f"war-root-{uuid.uuid4().hex[:8]}"
    admin_id = current_user.get("id") or str(current_user.get("_id"))

    await db.story_engine_jobs.insert_one({
        "job_id": root_job_id,
        "user_id": admin_id,
        "state": "READY",
        "title": request.title,
        "story_text": request.story_text,
        "animation_style": request.animation_style,
        "created_at": now.isoformat(),
        "story_chain_id": root_job_id,
        "parent_job_id": None,
        "root_story_id": root_job_id,
        "chain_depth": 0,
        "continuation_type": "original",
        "total_children": 0,
        "total_views": 0,
        "total_shares": 0,
        "battle_score": 0.0,
        "is_war_root": True,
        "war_id": war_id,
    })

    # Create war document
    state = "active" if request.start_delay_minutes == 0 else "scheduled"
    await db.daily_wars.insert_one({
        "war_id": war_id,
        "root_story_id": root_job_id,
        "root_title": request.title,
        "root_story_text": request.story_text,
        "state": state,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_entries": 0,
        "winner_job_id": None,
        "winner_user_id": None,
        "winner_title": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    })

    logger.info(f"[WAR] Seeded war {war_id} ({state}), root={root_job_id}")

    return {
        "success": True,
        "war_id": war_id,
        "root_story_id": root_job_id,
        "state": state,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }


@router.post("/admin/end")
async def admin_end_war(current_user: dict = Depends(get_admin_user)):
    """Admin: Force-end the current active war and declare winner."""
    war = await db.daily_wars.find_one({"state": "active"}, {"_id": 0})
    if not war:
        raise HTTPException(status_code=404, detail="No active war to end")

    success = await transition_war(war["war_id"], "active", "ended")
    if not success:
        raise HTTPException(status_code=400, detail="Failed to end war")

    winner = await declare_winner(war["war_id"])

    return {
        "success": True,
        "war_id": war["war_id"],
        "winner": {
            "job_id": winner["job_id"],
            "title": winner.get("title"),
            "creator_name": winner.get("creator_name"),
            "war_score": winner.get("war_score"),
        } if winner else None,
    }


# ═══════════════════════════════════════════════════════════════
# WAR OVERTAKE NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

async def check_war_overtake(war_id: str, triggering_job_id: str, triggering_user_id: str):
    """Send aggressive overtake notifications during an active war."""
    entries = await db.story_engine_jobs.find(
        {"war_id": war_id, "war_entry": True},
        {"_id": 0, "job_id": 1, "user_id": 1, "war_score": 1, "war_continues": 1,
         "war_shares": 1, "war_entered_at": 1, "title": 1}
    ).to_list(200)

    entries.sort(key=deterministic_rank_key)

    if len(entries) < 2:
        return

    # Get war for time-left context
    war = await db.daily_wars.find_one({"war_id": war_id}, {"_id": 0, "end_time": 1})
    time_left_str = ""
    if war and war.get("end_time"):
        try:
            end = datetime.fromisoformat(war["end_time"].replace("Z", "+00:00"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            hours_left = max(0, (end - datetime.now(timezone.utc)).total_seconds() / 3600)
            if hours_left < 1:
                time_left_str = f" Only {int(hours_left * 60)} minutes left!"
            else:
                time_left_str = f" {int(hours_left)}h left in the war."
        except (ValueError, AttributeError):
            pass

    # Assign ranks
    for i, e in enumerate(entries):
        e["rank"] = i + 1

    now = datetime.now(timezone.utc).isoformat()

    # Check who got overtaken
    for e in entries:
        if e["user_id"] == triggering_user_id:
            continue

        # Throttle: 1 war overtake per user per 30 min
        recent = await db.notifications.find_one({
            "user_id": e["user_id"],
            "type": "war_overtake",
            "data.war_id": war_id,
            "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()},
        })
        if recent:
            continue

        rank = e["rank"]
        if rank > 1:
            triggering_entry = next((x for x in entries if x["job_id"] == triggering_job_id), None)
            triggering_rank = triggering_entry["rank"] if triggering_entry else "?"

            if isinstance(triggering_rank, int) and triggering_rank < rank:
                await db.notifications.insert_one({
                    "user_id": e["user_id"],
                    "type": "war_overtake",
                    "title": f"You dropped to #{rank} in today's Story War",
                    "message": f"Someone just overtook you.{time_left_str} Fight back now.",
                    "data": {
                        "war_id": war_id,
                        "your_rank": rank,
                        "deep_link": "/app/war",
                    },
                    "read": False,
                    "created_at": now,
                })


# ═══════════════════════════════════════════════════════════════
# INDEXES
# ═══════════════════════════════════════════════════════════════

async def create_war_indexes():
    """Create indexes for daily war queries."""
    try:
        await db.daily_wars.create_index("war_id", unique=True)
        await db.daily_wars.create_index("state")
        await db.daily_wars.create_index([("state", 1), ("end_time", -1)])
        await db.story_engine_jobs.create_index([("war_id", 1), ("war_entry", 1)])
        await db.story_engine_jobs.create_index([("war_id", 1), ("war_score", -1)])
        logger.info("[WAR] Indexes created successfully")
    except Exception as e:
        logger.warning(f"[WAR] Index creation failed: {e}")
