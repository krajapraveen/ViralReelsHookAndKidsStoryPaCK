"""
Story Multiplayer Engine — Core Routes for the Story Graph.

Handles: Episode continuation, Branch creation, Story Battle ranking,
         Chain lineage queries, and competitive scoring.

Collections: story_engine_jobs (extended with graph fields)
New fields on story_engine_jobs:
  - root_story_id: str (the original story that started the chain)
  - chain_depth: int (0 for originals, increments per generation)
  - continuation_type: str ("original" | "episode" | "branch")
  - total_children: int (count of direct children)
  - total_views: int (view counter)
  - total_shares: int (share counter)
  - battle_score: float (computed ranking score)
"""
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user, get_optional_user

logger = logging.getLogger("story_multiplayer")
router = APIRouter(prefix="/stories", tags=["Story Multiplayer"])


# ═══════════════════════════════════════════════════════════════
# RANKING FORMULA — Weighted composite score
# ═══════════════════════════════════════════════════════════════

def compute_battle_score(
    total_children: int = 0,
    total_shares: int = 0,
    total_views: int = 0,
    chain_depth: int = 0,
    created_at_iso: str = None,
    streak_boost: float = 0.0,
    is_first_win_eligible: bool = False,
) -> float:
    """
    Weighted composite ranking score.
    - continues * 5 + shares * 3 + views * 1
    - depth multiplier: 1 + (chain_depth * 0.2)
    - recency boost: 1 / (1 + hours_since_creation * 0.05)
    - anti-gaming: if continues/views < 0.02 → score * 0.5
    - streak: soft influence only — 90% performance + 10% streak bonus
      A bad story with streak must NEVER beat a great story without streak.
    - first-win boost: invisible 15% lift for new users (0-1 prior entries)
      Ensures early success is possible without gaming the system.
    """
    base_score = (total_children * 5.0) + (total_shares * 3.0) + (total_views * 1.0)

    depth_multiplier = 1.0 + (chain_depth * 0.2)

    hours_since = 0
    if created_at_iso:
        try:
            created = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            hours_since = max(0, (datetime.now(timezone.utc) - created).total_seconds() / 3600)
        except (ValueError, AttributeError):
            pass

    recency_boost = 1.0 / (1.0 + hours_since * 0.05)

    performance_score = base_score * depth_multiplier * recency_boost

    # Anti-gaming: low engagement ratio penalty
    if total_views > 0 and total_children / max(total_views, 1) < 0.02:
        if total_views > 50:
            performance_score *= 0.5

    # First-Win Boost: invisible 15% lift for new users
    # Makes early success possible so new users don't bounce
    if is_first_win_eligible:
        performance_score *= 1.15

    # Streak influence: soft (max 10% of performance score)
    # 90% pure performance + 10% streak-weighted performance
    streak_influence = min(streak_boost, 0.10)  # Cap at 10%
    final_score = (performance_score * 0.9) + (performance_score * streak_influence * 0.1)

    return round(final_score, 4)


# ═══════════════════════════════════════════════════════════════
# GRAPH HELPERS
# ═══════════════════════════════════════════════════════════════

async def ensure_multiplayer_fields(job_id: str, parent_job_id: str = None, continuation_type: str = "original"):
    """
    Assign story graph fields to a job document.
    - original: root_story_id = job_id, chain_depth = 0
    - episode/branch: inherit root from parent, depth = parent + 1
    """
    if parent_job_id:
        parent = await db.story_engine_jobs.find_one(
            {"job_id": parent_job_id},
            {"_id": 0, "root_story_id": 1, "story_chain_id": 1, "chain_depth": 1, "job_id": 1}
        )
        if parent:
            root_id = parent.get("root_story_id") or parent.get("story_chain_id") or parent.get("job_id")
            depth = (parent.get("chain_depth") or 0) + 1
        else:
            root_id = job_id
            depth = 0
    else:
        root_id = job_id
        depth = 0

    now = datetime.now(timezone.utc).isoformat()
    update = {
        "root_story_id": root_id,
        "chain_depth": depth,
        "continuation_type": continuation_type,
        "total_children": 0,
        "total_views": 0,
        "total_shares": 0,
        "battle_score": 0.0,
        "multiplayer_updated_at": now,
    }

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": update}
    )

    # Increment parent's total_children counter
    if parent_job_id:
        await db.story_engine_jobs.update_one(
            {"job_id": parent_job_id},
            {"$inc": {"total_children": 1}}
        )

    return {"root_story_id": root_id, "chain_depth": depth, "continuation_type": continuation_type}


async def refresh_battle_score(job_id: str):
    """Recompute and persist battle_score for a single job, including streak boost and first-win."""
    job = await db.story_engine_jobs.find_one(
        {"job_id": job_id},
        {"_id": 0, "total_children": 1, "total_shares": 1, "total_views": 1,
         "chain_depth": 1, "created_at": 1, "user_id": 1}
    )
    if not job:
        return None

    # Fetch user's streak boost
    streak_boost = 0.0
    is_first_win_eligible = False
    if job.get("user_id"):
        streak = await db.user_streaks.find_one(
            {"user_id": job["user_id"]},
            {"_id": 0, "streak_boost": 1}
        )
        if streak:
            streak_boost = streak.get("streak_boost", 0.0)

        # First-Win Boost: check if user has very few entries (0-1 completed)
        prior_count = await db.story_engine_jobs.count_documents({
            "user_id": job["user_id"],
            "job_id": {"$ne": job_id},
            "continuation_type": "branch",
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        })
        is_first_win_eligible = prior_count <= 1

    score = compute_battle_score(
        total_children=job.get("total_children", 0),
        total_shares=job.get("total_shares", 0),
        total_views=job.get("total_views", 0),
        chain_depth=job.get("chain_depth", 0),
        created_at_iso=job.get("created_at"),
        streak_boost=streak_boost,
        is_first_win_eligible=is_first_win_eligible,
    )

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"battle_score": score, "multiplayer_updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return score


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class ContinueEpisodeRequest(BaseModel):
    parent_job_id: str = Field(..., description="Job ID of the parent story to continue linearly")
    title: str = Field(..., min_length=3, max_length=100)
    story_text: str = Field(..., min_length=50, max_length=10000)
    animation_style: str = Field(default="cartoon_2d")
    age_group: str = Field(default="kids_5_8")
    voice_preset: str = Field(default="narrator_warm")
    quality_mode: str = Field(default="balanced")


class ContinueBranchRequest(BaseModel):
    parent_job_id: str = Field(..., description="Job ID of the story to branch from (compete)")
    title: str = Field(..., min_length=3, max_length=100)
    story_text: str = Field(..., min_length=50, max_length=10000)
    animation_style: str = Field(default="cartoon_2d")
    age_group: str = Field(default="kids_5_8")
    voice_preset: str = Field(default="narrator_warm")
    quality_mode: str = Field(default="balanced")


class IncrementMetricRequest(BaseModel):
    job_id: str
    metric: str = Field(..., pattern="^(views|shares)$")


class InstantRerunRequest(BaseModel):
    source_job_id: str = Field(..., description="Job to create a variation from")
    mode: str = Field(default="try_again", pattern="^(try_again|beat_top)$")


class QuickShotRequest(BaseModel):
    root_story_id: str = Field(..., description="Root story of the battle to enter")


# ═══════════════════════════════════════════════════════════════
# VARIATION SUFFIXES for instant reruns (keeps content fresh)
# ═══════════════════════════════════════════════════════════════

_VARIATION_SUFFIXES = [
    "Rewrite this story with a surprising twist at the climax that changes everything.",
    "Rewrite with sharper dialogue and more vivid action scenes.",
    "Rewrite with deeper emotional stakes and character development.",
    "Rewrite with faster pacing and higher tension throughout.",
    "Rewrite with a completely different opening that hooks the reader immediately.",
    "Rewrite with an unexpected perspective shift that reveals hidden motives.",
    "Rewrite making the conflict more intense and the resolution more satisfying.",
    "Rewrite with richer world-building and sensory details.",
]


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS — Episode & Branch Creation
# ═══════════════════════════════════════════════════════════════

@router.post("/continue-episode")
async def continue_episode(
    request: ContinueEpisodeRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Continue Next Episode — Linear continuation of the same storyline.
    The new story inherits the same root and increments chain_depth.
    """
    user_id = current_user.get("id") or str(current_user.get("_id"))

    # Verify parent exists
    parent = await db.story_engine_jobs.find_one(
        {"job_id": request.parent_job_id},
        {"_id": 0, "job_id": 1, "root_story_id": 1, "story_chain_id": 1,
         "chain_depth": 1, "title": 1, "user_id": 1, "state": 1,
         "animation_style": 1, "episode_number": 1, "visibility": 1}
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent story not found")

    if parent.get("state") not in ("READY", "PARTIAL_READY", "COMPLETED"):
        raise HTTPException(status_code=400, detail="Parent story must be completed before continuing")

    # Cross-user visibility: allow if public or if user owns it
    parent_vis = parent.get("visibility", "public")
    if parent_vis == "private" and parent.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="This story is private and cannot be continued")

    # Import create_job and run the pipeline
    from services.story_engine.pipeline import create_job, run_pipeline

    result = await create_job(
        user_id=user_id,
        story_text=request.story_text,
        title=request.title,
        style_id=request.animation_style,
        language="en",
        age_group=request.age_group,
        parent_job_id=request.parent_job_id,
        story_chain_id=parent.get("root_story_id") or parent.get("story_chain_id") or parent.get("job_id"),
    )

    if not result.get("success"):
        error = result.get("error", "Job creation failed")
        if error == "insufficient_credits":
            cc = result.get("credit_check", {})
            raise HTTPException(status_code=402, detail=f"Insufficient credits. Required: {cc.get('required', 0)}, Available: {cc.get('current', 0)}")
        raise HTTPException(status_code=400, detail=error)

    job_id = result["job_id"]

    # Set multiplayer graph fields — EPISODE type
    graph_info = await ensure_multiplayer_fields(job_id, request.parent_job_id, "episode")

    # Store additional metadata + attribution
    parent_creator_name = "Anonymous"
    if parent.get("user_id"):
        pu = await db.users.find_one({"id": parent["user_id"]}, {"_id": 0, "name": 1, "email": 1})
        if pu:
            parent_creator_name = pu.get("name") or pu.get("email", "").split("@")[0]

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "animation_style": request.animation_style,
            "voice_preset": request.voice_preset,
            "quality_mode": request.quality_mode,
            "derivative_label": "continued_from",
            "source_story_id": request.parent_job_id,
            "source_story_title": parent.get("title"),
            "source_creator_id": parent.get("user_id"),
            "source_creator_name": parent_creator_name,
            "visibility": "public",
        }}
    )

    # Run pipeline in background (skip if queued)
    import asyncio
    if not result.get("queued"):
        asyncio.create_task(run_pipeline(job_id))

    # Record streak participation
    try:
        from routes.streaks import record_participation
        await record_participation(user_id, "episode", job_id)
    except Exception:
        pass

    return {
        "success": True,
        "job_id": job_id,
        "continuation_type": "episode",
        "parent_job_id": request.parent_job_id,
        "root_story_id": graph_info["root_story_id"],
        "chain_depth": graph_info["chain_depth"],
        "credits_charged": result.get("credits_deducted", 0),
        "message": "Episode generation started. Poll /api/story-engine/status/{job_id} for progress.",
    }


@router.post("/continue-branch")
async def continue_branch(
    request: ContinueBranchRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Fork / Branch — Competing alternate version of the story.
    Creates a rival branch that competes for #1 ranking against siblings.
    """
    user_id = current_user.get("id") or str(current_user.get("_id"))

    # Verify parent exists
    parent = await db.story_engine_jobs.find_one(
        {"job_id": request.parent_job_id},
        {"_id": 0, "job_id": 1, "root_story_id": 1, "story_chain_id": 1,
         "chain_depth": 1, "title": 1, "user_id": 1, "state": 1, "visibility": 1}
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent story not found")

    if parent.get("state") not in ("READY", "PARTIAL_READY", "COMPLETED"):
        raise HTTPException(status_code=400, detail="Parent story must be completed before branching")

    # Cross-user visibility: allow if public or if user owns it
    parent_vis = parent.get("visibility", "public")
    if parent_vis == "private" and parent.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="This story is private and cannot be branched")

    from services.story_engine.pipeline import create_job, run_pipeline

    result = await create_job(
        user_id=user_id,
        story_text=request.story_text,
        title=request.title,
        style_id=request.animation_style,
        language="en",
        age_group=request.age_group,
        parent_job_id=request.parent_job_id,
        story_chain_id=parent.get("root_story_id") or parent.get("story_chain_id") or parent.get("job_id"),
    )

    if not result.get("success"):
        error = result.get("error", "Job creation failed")
        if error == "insufficient_credits":
            cc = result.get("credit_check", {})
            raise HTTPException(status_code=402, detail=f"Insufficient credits. Required: {cc.get('required', 0)}, Available: {cc.get('current', 0)}")
        raise HTTPException(status_code=400, detail=error)

    job_id = result["job_id"]

    # Set multiplayer graph fields — BRANCH type
    graph_info = await ensure_multiplayer_fields(job_id, request.parent_job_id, "branch")

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "animation_style": request.animation_style,
            "voice_preset": request.voice_preset,
            "quality_mode": request.quality_mode,
            "derivative_label": "remixed_from",
            "source_story_id": request.parent_job_id,
            "source_story_title": parent.get("title"),
            "source_creator_id": parent.get("user_id"),
            "source_creator_name": None,  # populated below
            "visibility": "public",
        }}
    )

    # Populate source creator name
    if parent.get("user_id"):
        pu = await db.users.find_one({"id": parent["user_id"]}, {"_id": 0, "name": 1, "email": 1})
        if pu:
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"source_creator_name": pu.get("name") or pu.get("email", "").split("@")[0]}}
            )

    # Run pipeline in background (skip if queued)
    import asyncio
    is_queued = result.get("queued", False)
    if not is_queued:
        asyncio.create_task(run_pipeline(job_id))

    # Record streak participation
    try:
        from routes.streaks import record_participation
        await record_participation(user_id, "branch", job_id)
    except Exception:
        pass

    # Notify original author that someone branched their story
    try:
        parent_author = parent.get("user_id")
        if parent_author and parent_author != user_id:
            await db.notifications.insert_one({
                "user_id": parent_author,
                "type": "story_branched",
                "title": "Someone forked your story!",
                "message": f"A competing version of \"{parent.get('title', 'your story')}\" was just created. Will it beat yours?",
                "data": {
                    "parent_job_id": request.parent_job_id,
                    "branch_job_id": job_id,
                    "brancher_user_id": user_id,
                },
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        logger.warning(f"Failed to send branch notification: {e}")

    return {
        "success": True,
        "job_id": job_id,
        "continuation_type": "branch",
        "parent_job_id": request.parent_job_id,
        "root_story_id": graph_info["root_story_id"],
        "chain_depth": graph_info["chain_depth"],
        "credits_charged": result.get("credits_deducted", 0),
        "message": "Branch generation started. This version will compete for #1. Poll /api/story-engine/status/{job_id} for progress.",
    }


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS — Chain & Battle Queries
# ═══════════════════════════════════════════════════════════════

@router.get("/{story_id}/chain")
async def get_story_chain(story_id: str, current_user: dict = Depends(get_optional_user)):
    """
    Get the full lineage chain for a story.
    Returns timeline (episodes) and branches at each node.
    """
    # Find the story to get its root
    story = await db.story_engine_jobs.find_one(
        {"job_id": story_id},
        {"_id": 0, "root_story_id": 1, "story_chain_id": 1, "job_id": 1}
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    root_id = story.get("root_story_id") or story.get("story_chain_id") or story.get("job_id")

    # Fetch all jobs in this chain
    chain_filter = {
        "$or": [
            {"root_story_id": root_id},
            {"story_chain_id": root_id},
            {"job_id": root_id},
        ],
        "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED", "INIT", "PLANNING",
                          "BUILDING_CHARACTER_CONTEXT", "PLANNING_SCENE_MOTION",
                          "GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS",
                          "GENERATING_AUDIO", "ASSEMBLING_VIDEO", "VALIDATING"]},
    }

    projection = {
        "_id": 0,
        "job_id": 1, "title": 1, "user_id": 1, "state": 1,
        "parent_job_id": 1, "root_story_id": 1, "chain_depth": 1,
        "continuation_type": 1, "episode_number": 1,
        "total_children": 1, "total_views": 1, "total_shares": 1,
        "battle_score": 1, "thumbnail_url": 1, "created_at": 1,
        "animation_style": 1,
    }

    all_jobs = await db.story_engine_jobs.find(chain_filter, projection).sort("created_at", 1).to_list(200)

    if not all_jobs:
        raise HTTPException(status_code=404, detail="No chain data found")

    # Build timeline (episodes = linear path from root)
    episodes = [j for j in all_jobs if j.get("continuation_type") in ("original", "episode", None)]
    episodes.sort(key=lambda x: x.get("chain_depth", 0))

    # Build branch map: parent_job_id → [branches]
    branch_map = {}
    for j in all_jobs:
        if j.get("continuation_type") == "branch":
            pid = j.get("parent_job_id", "")
            if pid not in branch_map:
                branch_map[pid] = []
            branch_map[pid].append(j)

    # Sort branches by battle_score (descending)
    for pid in branch_map:
        branch_map[pid].sort(key=lambda x: x.get("battle_score", 0), reverse=True)

    # Chain stats
    total_nodes = len(all_jobs)
    max_depth = max((j.get("chain_depth", 0) for j in all_jobs), default=0)
    total_branches = sum(1 for j in all_jobs if j.get("continuation_type") == "branch")
    total_episodes = sum(1 for j in all_jobs if j.get("continuation_type") in ("original", "episode", None))

    return {
        "success": True,
        "root_story_id": root_id,
        "chain_stats": {
            "total_nodes": total_nodes,
            "max_depth": max_depth,
            "total_episodes": total_episodes,
            "total_branches": total_branches,
        },
        "episodes": episodes,
        "branch_map": branch_map,
        "all_nodes": all_jobs,
    }


@router.get("/{story_id}/branches")
async def get_story_branches(story_id: str, current_user: dict = Depends(get_optional_user)):
    """
    Get all competing branches of a specific story node.
    Returns siblings sorted by battle_score (highest first).
    """
    # Find all branches that share this parent
    branches = await db.story_engine_jobs.find(
        {
            "parent_job_id": story_id,
            "continuation_type": "branch",
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        },
        {
            "_id": 0,
            "job_id": 1, "title": 1, "user_id": 1, "state": 1,
            "chain_depth": 1, "total_children": 1, "total_views": 1,
            "total_shares": 1, "battle_score": 1, "thumbnail_url": 1,
            "created_at": 1, "animation_style": 1,
        }
    ).sort("battle_score", -1).to_list(50)

    # Also include the parent itself for comparison
    parent = await db.story_engine_jobs.find_one(
        {"job_id": story_id},
        {
            "_id": 0,
            "job_id": 1, "title": 1, "user_id": 1, "state": 1,
            "chain_depth": 1, "total_children": 1, "total_views": 1,
            "total_shares": 1, "battle_score": 1, "thumbnail_url": 1,
            "created_at": 1, "animation_style": 1, "continuation_type": 1,
        }
    )

    # Include episodes that share same parent (siblings)
    episodes = await db.story_engine_jobs.find(
        {
            "parent_job_id": story_id,
            "continuation_type": "episode",
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        },
        {
            "_id": 0,
            "job_id": 1, "title": 1, "user_id": 1, "state": 1,
            "chain_depth": 1, "total_children": 1, "total_views": 1,
            "total_shares": 1, "battle_score": 1, "thumbnail_url": 1,
            "created_at": 1, "animation_style": 1,
        }
    ).sort("created_at", 1).to_list(50)

    return {
        "success": True,
        "parent": parent,
        "branches": branches,
        "episodes": episodes,
        "total_branches": len(branches),
        "total_episodes": len(episodes),
    }


# ═══════════════════════════════════════════════════════════════
# STORY BATTLE — Side-by-side comparison with ranking
# ═══════════════════════════════════════════════════════════════

@router.get("/battle/{story_id}")
async def get_story_battle(story_id: str, current_user: dict = Depends(get_optional_user)):
    """
    Story Battle Screen data — shows the parent story and all competing branches
    ranked by battle_score. This is the deep-link target for notifications.
    """
    # Find the story
    story = await db.story_engine_jobs.find_one(
        {"job_id": story_id},
        {"_id": 0, "job_id": 1, "title": 1, "user_id": 1, "state": 1,
         "parent_job_id": 1, "root_story_id": 1, "chain_depth": 1,
         "continuation_type": 1, "total_children": 1, "total_views": 1,
         "total_shares": 1, "battle_score": 1, "thumbnail_url": 1,
         "output_url": 1, "created_at": 1, "animation_style": 1,
         "story_text": 1, "episode_plan": 1}
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Determine the battle context: look at the parent to find all siblings
    parent_id = story.get("parent_job_id")
    if not parent_id:
        # This IS the root — get all its direct children (branches)
        battle_parent_id = story_id
    else:
        battle_parent_id = parent_id

    # Get all competing versions (branches from the same parent)
    competitors = await db.story_engine_jobs.find(
        {
            "parent_job_id": battle_parent_id,
            "continuation_type": "branch",
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        },
        {
            "_id": 0,
            "job_id": 1, "title": 1, "user_id": 1, "state": 1,
            "chain_depth": 1, "total_children": 1, "total_views": 1,
            "total_shares": 1, "battle_score": 1, "thumbnail_url": 1,
            "output_url": 1, "created_at": 1, "animation_style": 1,
            "story_text": 1,
        }
    ).sort("battle_score", -1).to_list(50)

    # Get the battle parent too
    battle_parent = await db.story_engine_jobs.find_one(
        {"job_id": battle_parent_id},
        {
            "_id": 0,
            "job_id": 1, "title": 1, "user_id": 1,
            "total_children": 1, "total_views": 1, "total_shares": 1,
            "battle_score": 1, "thumbnail_url": 1, "output_url": 1,
            "created_at": 1, "story_text": 1,
        }
    )

    # Assign ranks
    all_contenders = []
    if battle_parent:
        all_contenders.append({**battle_parent, "is_original": True})
    for c in competitors:
        all_contenders.append({**c, "is_original": False})

    # Sort by battle_score
    all_contenders.sort(key=lambda x: x.get("battle_score", 0), reverse=True)
    for i, c in enumerate(all_contenders):
        c["rank"] = i + 1

    # Enrich with creator names
    user_ids = list({c.get("user_id") for c in all_contenders if c.get("user_id")})
    user_map = {}
    if user_ids:
        users = await db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "name": 1, "email": 1}
        ).to_list(100)
        user_map = {u["id"]: u.get("name") or u.get("email", "").split("@")[0] for u in users}

    for c in all_contenders:
        c["creator_name"] = user_map.get(c.get("user_id"), "Anonymous")

    # Find current user's rank if they have a contender
    user_id = None
    user_rank = None
    if current_user:
        user_id = current_user.get("id") or str(current_user.get("_id"))
        for c in all_contenders:
            if c.get("user_id") == user_id:
                user_rank = c.get("rank")
                break

    return {
        "success": True,
        "battle_parent_id": battle_parent_id,
        "current_story": story,
        "contenders": all_contenders,
        "total_contenders": len(all_contenders),
        "user_rank": user_rank,
        "user_id": user_id,
    }


# ═══════════════════════════════════════════════════════════════
# METRICS — Increment views/shares and refresh score
# ═══════════════════════════════════════════════════════════════

@router.post("/increment-metric")
async def increment_metric(request: IncrementMetricRequest):
    """Increment a story's view or share count and refresh its battle score."""
    field_map = {"views": "total_views", "shares": "total_shares"}
    field = field_map.get(request.metric)
    if not field:
        raise HTTPException(status_code=400, detail="Invalid metric")

    result = await db.story_engine_jobs.update_one(
        {"job_id": request.job_id},
        {"$inc": {field: 1}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Story not found")

    # Refresh battle score
    new_score = await refresh_battle_score(request.job_id)

    # Check for rank changes and send notifications
    try:
        job = await db.story_engine_jobs.find_one(
            {"job_id": request.job_id},
            {"_id": 0, "parent_job_id": 1}
        )
        if job and job.get("parent_job_id"):
            await check_and_send_rank_notifications(request.job_id, job["parent_job_id"])
    except Exception as e:
        logger.warning(f"[BATTLE-NOTIFY] Failed to check rank notifications: {e}")

    return {"success": True, "job_id": request.job_id, "metric": request.metric, "battle_score": new_score}


# ═══════════════════════════════════════════════════════════════
# INSTANT RE-RUN — Zero-friction one-tap regeneration
# ═══════════════════════════════════════════════════════════════

@router.post("/instant-rerun")
async def instant_rerun(
    request: InstantRerunRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Instant Re-run — one tap, no modal, no input.
    Reuses source job's story_text with a slight variation.
    Mode: try_again (self-variation) or beat_top (competitive against #1).
    """
    import random
    user_id = current_user.get("id") or str(current_user.get("_id"))

    source = await db.story_engine_jobs.find_one(
        {"job_id": request.source_job_id},
        {"_id": 0, "job_id": 1, "title": 1, "story_text": 1, "animation_style": 1,
         "root_story_id": 1, "story_chain_id": 1, "parent_job_id": 1,
         "chain_depth": 1, "user_id": 1, "state": 1, "visibility": 1}
    )
    if not source:
        raise HTTPException(status_code=404, detail="Source story not found")

    # Track rerun count for this user in this session (anti-spam quality gate)
    rerun_key = f"rerun_{user_id}_{source.get('root_story_id', request.source_job_id)}"
    rerun_count = 0
    rerun_doc = await db.rerun_tracker.find_one(
        {"key": rerun_key, "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}},
        {"_id": 0, "count": 1}
    )
    if rerun_doc:
        rerun_count = rerun_doc.get("count", 0)

    # Quality gate: after 3 reruns, suggest trying a different approach
    quality_warning = None
    if rerun_count >= 3:
        quality_warning = "Same pattern detected. Try a stronger twist to beat #1."

    # Build variation text
    base_text = source.get("story_text", "")
    variation_suffix = random.choice(_VARIATION_SUFFIXES)

    if request.mode == "beat_top":
        # Get #1 version for competitive context
        root_id = source.get("root_story_id") or source.get("story_chain_id") or request.source_job_id
        top = await db.story_engine_jobs.find_one(
            {
                "root_story_id": root_id,
                "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
                "battle_score": {"$gt": 0},
            },
            {"_id": 0, "title": 1, "story_text": 1, "battle_score": 1},
            sort=[("battle_score", -1)],
        )
        if top and top.get("story_text"):
            variation_text = f"{base_text}\n\n[COMPETITIVE REWRITE: The current #1 version focuses on: \"{top['story_text'][:200]}...\". Create a dramatically better version that outperforms it. {variation_suffix}]"
        else:
            variation_text = f"{base_text}\n\n[REWRITE INSTRUCTION: {variation_suffix}]"
        title_prefix = "Beat"
    else:
        variation_text = f"{base_text}\n\n[REWRITE INSTRUCTION: {variation_suffix}]"
        title_prefix = "v" + str(rerun_count + 2)

    new_title = f"{source.get('title', 'Story')} — {title_prefix}"

    # Determine parent for the branch
    parent_id = source.get("parent_job_id") or request.source_job_id

    from services.story_engine.pipeline import create_job, run_pipeline

    result = await create_job(
        user_id=user_id,
        story_text=variation_text,
        title=new_title,
        style_id=source.get("animation_style", "cartoon_2d"),
        language="en",
        age_group="all_ages",
        parent_job_id=parent_id,
        story_chain_id=source.get("root_story_id") or source.get("story_chain_id"),
    )

    if not result.get("success"):
        error = result.get("error", "Generation failed")
        if error == "insufficient_credits":
            cc = result.get("credit_check", {})
            raise HTTPException(status_code=402, detail=f"Insufficient credits. Required: {cc.get('required', 0)}")
        raise HTTPException(status_code=400, detail=error)

    job_id = result["job_id"]

    # Set multiplayer fields — always a branch (competing version)
    graph_info = await ensure_multiplayer_fields(job_id, parent_id, "branch")

    # Attribution
    source_creator_name = "Anonymous"
    if source.get("user_id"):
        pu = await db.users.find_one({"id": source["user_id"]}, {"_id": 0, "name": 1, "email": 1})
        if pu:
            source_creator_name = pu.get("name") or pu.get("email", "").split("@")[0]

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "derivative_label": "remixed_from",
            "source_story_id": request.source_job_id,
            "source_story_title": source.get("title"),
            "source_creator_id": source.get("user_id"),
            "source_creator_name": source_creator_name,
            "visibility": "public",
            "rerun_mode": request.mode,
            "rerun_number": rerun_count + 1,
        }}
    )

    # Track rerun count
    await db.rerun_tracker.update_one(
        {"key": rerun_key},
        {"$set": {"key": rerun_key, "created_at": datetime.now(timezone.utc).isoformat()},
         "$inc": {"count": 1}},
        upsert=True,
    )

    # Run pipeline (skip if queued)
    import asyncio
    is_queued = result.get("queued", False)
    if not is_queued:
        asyncio.create_task(run_pipeline(job_id))

    # Track analytics
    try:
        await db.analytics_events.insert_one({
            "event": f"instant_rerun_{request.mode}",
            "user_id": user_id,
            "data": {"source_job_id": request.source_job_id, "new_job_id": job_id, "rerun_number": rerun_count + 1},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    # Record streak participation
    try:
        from routes.streaks import record_participation
        await record_participation(user_id, f"rerun_{request.mode}", job_id)
    except Exception:
        pass

    return {
        "success": True,
        "job_id": job_id,
        "mode": request.mode,
        "rerun_number": rerun_count + 1,
        "quality_warning": quality_warning,
        "root_story_id": graph_info["root_story_id"],
        "chain_depth": graph_info["chain_depth"],
        "credits_charged": result.get("credits_deducted", 0),
        "message": "Instant rerun started. New version generating...",
    }


# ═══════════════════════════════════════════════════════════════
# QUICK SHOT — 1-tap zero-input entry for lazy spectators
# ═══════════════════════════════════════════════════════════════

_QUICK_SHOT_TWISTS = [
    "Rewrite this story with a completely unexpected villain reveal.",
    "Rewrite this story but set it 100 years in the future.",
    "Rewrite this with a darkly comedic tone and witty dialogue.",
    "Rewrite making the protagonist morally ambiguous with hidden motives.",
    "Rewrite with a mind-bending twist ending nobody sees coming.",
    "Rewrite this story from the antagonist's sympathetic perspective.",
    "Rewrite with an urgent countdown that ratchets tension every scene.",
    "Rewrite this story with a shocking betrayal by the closest ally.",
]


@router.post("/quick-shot")
async def quick_shot(
    request: QuickShotRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Quick Shot — 1-tap entry into a battle. Zero thinking, zero input.
    Auto-generates a competitive branch from the root story with a random twist.
    Converts passive spectators into active players.
    """
    import random
    user_id = current_user.get("id") or str(current_user.get("_id"))

    # Find the root story
    root = await db.story_engine_jobs.find_one(
        {"job_id": request.root_story_id},
        {"_id": 0, "job_id": 1, "title": 1, "story_text": 1, "animation_style": 1,
         "root_story_id": 1, "user_id": 1, "state": 1}
    )
    if not root:
        raise HTTPException(status_code=404, detail="Battle root not found")

    base_text = root.get("story_text", "")
    if not base_text or len(base_text) < 20:
        raise HTTPException(status_code=400, detail="Root story has no text to remix")

    # Pick a random twist
    twist = random.choice(_QUICK_SHOT_TWISTS)
    variation_text = f"{base_text}\n\n[QUICK SHOT REWRITE: {twist}]"
    new_title = f"{root.get('title', 'Story')} — Quick Shot"

    from services.story_engine.pipeline import create_job, run_pipeline

    result = await create_job(
        user_id=user_id,
        story_text=variation_text,
        title=new_title,
        style_id=root.get("animation_style", "cartoon_2d"),
        language="en",
        age_group="all_ages",
        parent_job_id=request.root_story_id,
        story_chain_id=request.root_story_id,
    )

    if not result.get("success"):
        error = result.get("error", "Generation failed")
        if error == "insufficient_credits":
            cc = result.get("credit_check", {})
            raise HTTPException(status_code=402, detail=f"Insufficient credits. Required: {cc.get('required', 0)}")
        raise HTTPException(status_code=400, detail=error)

    job_id = result["job_id"]

    # Set multiplayer fields — always a branch
    graph_info = await ensure_multiplayer_fields(job_id, request.root_story_id, "branch")

    # Attribution
    root_creator_name = "Anonymous"
    if root.get("user_id"):
        pu = await db.users.find_one({"id": root["user_id"]}, {"_id": 0, "name": 1, "email": 1})
        if pu:
            root_creator_name = pu.get("name") or pu.get("email", "").split("@")[0]

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "derivative_label": "quick_shot_from",
            "source_story_id": request.root_story_id,
            "source_story_title": root.get("title"),
            "source_creator_id": root.get("user_id"),
            "source_creator_name": root_creator_name,
            "visibility": "public",
            "quick_shot": True,
        }}
    )

    # Run pipeline (skip if queued)
    import asyncio
    is_queued = result.get("queued", False)
    if not is_queued:
        asyncio.create_task(run_pipeline(job_id))

    # Track conversion analytics
    now = datetime.now(timezone.utc).isoformat()
    try:
        await db.analytics_events.insert_one({
            "event": "quick_shot_entry",
            "user_id": user_id,
            "data": {
                "root_story_id": request.root_story_id,
                "new_job_id": job_id,
                "source": "spectator_conversion",
            },
            "created_at": now,
        })
    except Exception:
        pass

    # Record streak participation — this triggers the "Streak Started" hook
    streak_result = None
    try:
        from routes.streaks import record_participation
        streak_result = await record_participation(user_id, "quick_shot", job_id)
    except Exception:
        pass

    return {
        "success": True,
        "job_id": job_id,
        "root_story_id": graph_info["root_story_id"],
        "chain_depth": graph_info["chain_depth"],
        "credits_charged": result.get("credits_deducted", 0),
        "queued": is_queued,
        "streak_started": streak_result.get("current_streak", 0) == 1 if streak_result else False,
        "current_streak": streak_result.get("current_streak", 0) if streak_result else 0,
        "message": "Quick Shot queued! We'll start rendering as soon as a slot opens." if is_queued else "Quick Shot fired! Your version is generating...",
    }


# ═══════════════════════════════════════════════════════════════
# STORY VIEWER — Public read access for consumption
# ═══════════════════════════════════════════════════════════════

@router.get("/viewer/{story_id}")
async def get_story_for_viewer(story_id: str, current_user: dict = Depends(get_optional_user)):
    """
    Public story viewer data — returns story content for consumption.
    No ownership check. Used by the Story Viewer Page.
    Checks both story_engine_jobs and pipeline_jobs (legacy content).
    """
    job = await db.story_engine_jobs.find_one(
        {"job_id": story_id},
        {"_id": 0}
    )

    # Fallback: check pipeline_jobs for legacy content
    source_collection = "story_engine_jobs"
    if not job:
        job = await db.pipeline_jobs.find_one(
            {"job_id": story_id},
            {"_id": 0}
        )
        source_collection = "pipeline_jobs"

    if not job:
        raise HTTPException(status_code=404, detail="Story not found")

    # State check — different field names per collection
    if source_collection == "story_engine_jobs":
        if job.get("state") not in ("READY", "PARTIAL_READY", "COMPLETED"):
            raise HTTPException(status_code=400, detail="Story is not ready for viewing")
    else:
        # pipeline_jobs uses "status" not "state"
        if job.get("status") not in ("COMPLETED",):
            raise HTTPException(status_code=400, detail="Story is not ready for viewing")

    # Visibility check: private stories only visible to owner
    visibility = job.get("visibility", "public")
    user_id = None
    if current_user:
        user_id = current_user.get("id") or str(current_user.get("_id"))

    if visibility == "private" and job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="This story is private")

    # Track view in user's watch history (for cross-user "Continue Watching")
    if user_id:
        await db.watch_history.update_one(
            {"user_id": user_id, "job_id": story_id},
            {"$set": {
                "user_id": user_id,
                "job_id": story_id,
                "title": job.get("title"),
                "last_viewed_at": datetime.now(timezone.utc).isoformat(),
                "creator_id": job.get("user_id"),
            }},
            upsert=True,
        )

    # Build scene progress
    scene_progress = []
    for sr in job.get("stage_results", []):
        if sr.get("stage") == "keyframes" and sr.get("output"):
            for scene in sr["output"].get("scenes", []):
                if scene.get("url"):
                    scene_progress.append({
                        "title": scene.get("title", ""),
                        "image_url": scene["url"],
                    })

    # Get creator name
    creator_name = "Anonymous"
    if job.get("user_id"):
        user = await db.users.find_one(
            {"id": job["user_id"]},
            {"_id": 0, "name": 1, "email": 1}
        )
        if user:
            creator_name = user.get("name") or user.get("email", "").split("@")[0]

    return {
        "success": True,
        "job": {
            "job_id": job.get("job_id"),
            "title": job.get("title"),
            "story_text": job.get("story_text", ""),
            "state": job.get("state"),
            "output_url": job.get("output_url"),
            "thumbnail_url": job.get("thumbnail_url"),
            "animation_style": job.get("animation_style"),
            "episode_number": job.get("episode_number"),
            "scene_progress": scene_progress,
            # Multiplayer fields
            "root_story_id": job.get("root_story_id"),
            "story_chain_id": job.get("story_chain_id"),
            "parent_job_id": job.get("parent_job_id"),
            "chain_depth": job.get("chain_depth", 0),
            "continuation_type": job.get("continuation_type", "original"),
            "total_children": job.get("total_children", 0),
            "total_views": job.get("total_views", 0),
            "total_shares": job.get("total_shares", 0),
            "battle_score": job.get("battle_score", 0.0),
            "creator_name": creator_name,
            "created_at": job.get("created_at"),
            "visibility": job.get("visibility", "public"),
            # Attribution
            "derivative_label": job.get("derivative_label"),
            "source_story_id": job.get("source_story_id"),
            "source_story_title": job.get("source_story_title"),
            "source_creator_id": job.get("source_creator_id"),
            "source_creator_name": job.get("source_creator_name"),
        },
    }


# ═══════════════════════════════════════════════════════════════
# BACKFILL — Migrate existing jobs to have multiplayer fields
# ═══════════════════════════════════════════════════════════════

@router.post("/backfill-multiplayer")
async def backfill_multiplayer_fields(current_user: dict = Depends(get_current_user)):
    """Admin/dev endpoint: backfill multiplayer fields on existing jobs that lack them."""
    if current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    # Find jobs without the multiplayer fields
    jobs_without = await db.story_engine_jobs.find(
        {"root_story_id": {"$exists": False}},
        {"_id": 0, "job_id": 1, "parent_job_id": 1, "story_chain_id": 1}
    ).to_list(1000)

    updated = 0
    for job in jobs_without:
        parent_id = job.get("parent_job_id")
        if parent_id:
            # Has parent → could be episode or branch. Default to episode for legacy.
            await ensure_multiplayer_fields(job["job_id"], parent_id, "episode")
        else:
            # No parent → original
            await ensure_multiplayer_fields(job["job_id"], None, "original")
        updated += 1

    return {"success": True, "updated": updated, "total_found": len(jobs_without)}


class SetVisibilityRequest(BaseModel):
    job_id: str
    visibility: str = Field(..., pattern="^(public|unlisted|private)$")


@router.post("/set-visibility")
async def set_story_visibility(request: SetVisibilityRequest, current_user: dict = Depends(get_current_user)):
    """Set visibility for a story. Only the owner can change visibility."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    job = await db.story_engine_jobs.find_one(
        {"job_id": request.job_id},
        {"_id": 0, "user_id": 1}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Story not found")
    if job.get("user_id") != user_id and current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Only the owner can change visibility")

    await db.story_engine_jobs.update_one(
        {"job_id": request.job_id},
        {"$set": {"visibility": request.visibility}}
    )
    return {"success": True, "job_id": request.job_id, "visibility": request.visibility}


@router.post("/backfill-visibility")
async def backfill_visibility(current_user: dict = Depends(get_current_user)):
    """Admin: Set all completed stories without visibility to public."""
    if current_user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.story_engine_jobs.update_many(
        {
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
            "visibility": {"$exists": False},
        },
        {"$set": {"visibility": "public"}}
    )

    return {"success": True, "updated": result.modified_count}


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION ENGINE — High-Stakes Ego-Driven Triggers
# ═══════════════════════════════════════════════════════════════

async def check_and_send_rank_notifications(job_id: str, parent_job_id: str):
    """
    After a score refresh, check if any rank changes occurred and notify affected users.
    Triggers: rank_drop (you lost #1), version_outperformed (competitor passed you).
    Deep-links to Story Battle screen.
    """
    if not parent_job_id:
        return

    # Get all branches from this parent, sorted by score
    contenders = await db.story_engine_jobs.find(
        {
            "parent_job_id": parent_job_id,
            "continuation_type": "branch",
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        },
        {"_id": 0, "job_id": 1, "user_id": 1, "title": 1, "battle_score": 1}
    ).sort("battle_score", -1).to_list(50)

    # Also include parent
    parent = await db.story_engine_jobs.find_one(
        {"job_id": parent_job_id},
        {"_id": 0, "job_id": 1, "user_id": 1, "title": 1, "battle_score": 1}
    )
    if parent:
        all_contenders = [parent] + contenders
    else:
        all_contenders = contenders

    all_contenders.sort(key=lambda x: x.get("battle_score", 0), reverse=True)

    if len(all_contenders) < 2:
        return

    # The new #1
    current_leader = all_contenders[0]
    current_leader_id = current_leader.get("user_id")

    # Check previous leader (stored in a simple cache on the parent)
    prev_leader_id = None
    if parent:
        prev_leader_id = parent.get("_prev_battle_leader")

    # If leader changed, notify the old leader
    if prev_leader_id and prev_leader_id != current_leader_id:
        now = datetime.now(timezone.utc).isoformat()
        new_leader_title = current_leader.get("title", "A competing version")

        # Throttle: max 1 rank_drop notification per user per 6 hours
        recent = await db.notifications.find_one({
            "user_id": prev_leader_id,
            "type": "rank_drop",
            "data.parent_job_id": parent_job_id,
            "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()},
        })
        if not recent:
            await db.notifications.insert_one({
                "user_id": prev_leader_id,
                "type": "rank_drop",
                "title": "You just lost #1 spot on your story",
                "message": f"\"{new_leader_title}\" overtook you. Take it back now.",
                "data": {
                    "parent_job_id": parent_job_id,
                    "new_leader_job_id": current_leader.get("job_id"),
                    "deep_link": f"/app/story-battle/{parent_job_id}",
                },
                "read": False,
                "created_at": now,
            })
            logger.info(f"[BATTLE-NOTIFY] rank_drop sent to {prev_leader_id[:12]} for battle {parent_job_id[:12]}")

            # Fire push notification
            try:
                from routes.push_notifications import trigger_rank_drop_push
                parent_title = parent.get("title", "your story") if parent else "your story"
                await trigger_rank_drop_push(prev_leader_id, parent_title, parent_job_id, 0)
            except Exception as push_err:
                logger.warning(f"[PUSH] rank_drop push failed: {push_err}")

    # Update stored leader
    if parent:
        await db.story_engine_jobs.update_one(
            {"job_id": parent_job_id},
            {"$set": {"_prev_battle_leader": current_leader_id}}
        )

    # Notify all non-leaders that a new version outperformed them (once per branch)
    triggering_job = await db.story_engine_jobs.find_one(
        {"job_id": job_id},
        {"_id": 0, "user_id": 1, "title": 1}
    )
    if triggering_job:
        triggering_user = triggering_job.get("user_id")
        for c in all_contenders[1:]:  # Skip #1
            cuid = c.get("user_id")
            if cuid and cuid != triggering_user:
                # Check recent notification to prevent spam
                recent_outperform = await db.notifications.find_one({
                    "user_id": cuid,
                    "type": "version_outperformed",
                    "data.parent_job_id": parent_job_id,
                    "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()},
                })
                if not recent_outperform:
                    now = datetime.now(timezone.utc).isoformat()
                    await db.notifications.insert_one({
                        "user_id": cuid,
                        "type": "version_outperformed",
                        "title": "Your story version is falling behind",
                        "message": "Other versions are gaining more traction. Create a better version to compete.",
                        "data": {
                            "parent_job_id": parent_job_id,
                            "deep_link": f"/app/story-battle/{parent_job_id}",
                        },
                        "read": False,
                        "created_at": now,
                    })

    # Near-win push: check if #2 contender is within gap ≤ 2 continues of #1
    if len(all_contenders) >= 2:
        top = all_contenders[0]
        runner_up = all_contenders[1]
        top_continues = top.get("total_children", 0)
        runner_continues = runner_up.get("total_children", 0)
        gap = top_continues - runner_continues
        if 0 < gap <= 2:
            try:
                from routes.push_notifications import trigger_near_win_push
                parent_title = parent.get("title", "") if parent else ""
                await trigger_near_win_push(
                    runner_up.get("user_id"), parent_title, parent_job_id, gap
                )
            except Exception:
                pass


@router.get("/hottest-battle")
async def get_hottest_battle(current_user: dict = Depends(get_optional_user)):
    """
    Find the hottest active battle — the story root with the most branches + highest total activity.
    Used for the Spectator Mode on the homepage.
    """
    # Find story roots with the most branches (most competitive)
    pipeline_agg = [
        {"$match": {
            "continuation_type": "branch",
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
            "visibility": {"$in": ["public", None]},
        }},
        {"$group": {
            "_id": "$root_story_id",
            "branch_count": {"$sum": 1},
            "total_score": {"$sum": "$battle_score"},
            "total_views": {"$sum": "$total_views"},
            "latest_created": {"$max": "$created_at"},
        }},
        {"$sort": {"branch_count": -1, "total_score": -1}},
        {"$limit": 1},
    ]

    results = await db.story_engine_jobs.aggregate(pipeline_agg).to_list(1)
    if not results:
        return {"success": True, "battle": None}

    hottest = results[0]
    root_id = hottest["_id"]

    # Get the root story
    root = await db.story_engine_jobs.find_one(
        {"job_id": root_id},
        {"_id": 0, "job_id": 1, "title": 1, "user_id": 1, "thumbnail_url": 1, "story_text": 1}
    )
    if not root:
        return {"success": True, "battle": None}

    # Get top 3 contenders
    contenders = await db.story_engine_jobs.find(
        {
            "$or": [
                {"job_id": root_id},
                {"root_story_id": root_id, "continuation_type": "branch",
                 "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]}},
            ],
        },
        {
            "_id": 0, "job_id": 1, "title": 1, "user_id": 1,
            "battle_score": 1, "total_children": 1, "total_views": 1, "total_shares": 1,
        }
    ).sort("battle_score", -1).limit(5).to_list(5)

    # Enrich with names
    user_ids = list({c.get("user_id") for c in contenders if c.get("user_id")})
    user_map = {}
    if user_ids:
        users = await db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "name": 1, "email": 1}
        ).to_list(50)
        user_map = {u["id"]: u.get("name") or u.get("email", "").split("@")[0] for u in users}

    for i, c in enumerate(contenders):
        c["creator_name"] = user_map.get(c.get("user_id"), "Anonymous")
        c["rank"] = i + 1

    # Check near-win (gap between #1 and #2)
    near_win = False
    gap_to_first = 0
    gap_continues_to_first = 0
    if len(contenders) >= 2:
        top_score = contenders[0].get("battle_score", 0)
        second_score = contenders[1].get("battle_score", 0)
        gap_to_first = round(top_score - second_score)
        top_continues = contenders[0].get("total_children", 0)
        second_continues = contenders[1].get("total_children", 0)
        gap_continues_to_first = top_continues - second_continues
        near_win = gap_to_first <= 5  # Close race

    # Root creator
    root_creator = user_map.get(root.get("user_id"), "Anonymous")

    # Personalized conversion data for logged-in users
    user_entry_count = 0
    user_is_new = True
    user_already_in_battle = False
    if current_user:
        uid = current_user.get("id") or str(current_user.get("_id"))
        # How many total branches has this user made? (for first-win messaging)
        user_entry_count = await db.story_engine_jobs.count_documents({
            "user_id": uid,
            "continuation_type": "branch",
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        })
        user_is_new = user_entry_count <= 1
        # Is user already in THIS battle?
        user_already_in_battle = await db.story_engine_jobs.count_documents({
            "user_id": uid,
            "root_story_id": root_id,
            "continuation_type": "branch",
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        }) > 0

    return {
        "success": True,
        "battle": {
            "root_story_id": root_id,
            "root_title": root.get("title"),
            "root_creator": root_creator,
            "root_thumbnail": root.get("thumbnail_url"),
            "branch_count": hottest["branch_count"],
            "total_views": hottest["total_views"],
            "contenders": contenders[:3],
            "near_win": near_win,
            "gap_to_first": gap_to_first,
            "gap_continues_to_first": gap_continues_to_first,
            # Conversion personalization
            "user_entry_count": user_entry_count,
            "user_is_new": user_is_new,
            "user_already_in_battle": user_already_in_battle,
        },
    }


@router.get("/notifications/battle")
async def get_battle_notifications(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=20, le=50),
):
    """Get battle-related notifications for the current user."""
    user_id = current_user.get("id") or str(current_user.get("_id"))

    notifications = await db.notifications.find(
        {
            "user_id": user_id,
            "type": {"$in": ["rank_drop", "version_outperformed", "story_branched", "new_branch_created"]},
        },
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    unread = sum(1 for n in notifications if not n.get("read"))

    return {
        "success": True,
        "notifications": notifications,
        "total": len(notifications),
        "unread": unread,
    }


# ═══════════════════════════════════════════════════════════════
# FEED PRIORITIZATION — Chain depth + continuation rate
# ═══════════════════════════════════════════════════════════════

@router.get("/feed/trending")
async def get_trending_stories(
    limit: int = Query(default=20, le=50),
    current_user: dict = Depends(get_optional_user),
):
    """
    Trending stories feed — public stories from ALL users, ranked by battle_score.
    """
    stories = await db.story_engine_jobs.find(
        {
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
            "battle_score": {"$gt": 0},
            "visibility": {"$in": ["public", None]},  # Include legacy stories without visibility field
        },
        {
            "_id": 0,
            "job_id": 1, "title": 1, "user_id": 1, "state": 1,
            "continuation_type": 1, "chain_depth": 1,
            "total_children": 1, "total_views": 1, "total_shares": 1,
            "battle_score": 1, "thumbnail_url": 1, "created_at": 1,
            "animation_style": 1, "root_story_id": 1,
            "derivative_label": 1, "source_story_title": 1, "source_creator_name": 1,
        }
    ).sort("battle_score", -1).limit(limit).to_list(limit)

    # Enrich with creator names
    user_ids = list({s.get("user_id") for s in stories if s.get("user_id")})
    user_map = {}
    if user_ids:
        users = await db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "name": 1, "email": 1}
        ).to_list(100)
        user_map = {u["id"]: u.get("name") or u.get("email", "").split("@")[0] for u in users}

    for s in stories:
        s["creator_name"] = user_map.get(s.get("user_id"), "Anonymous")

    return {
        "success": True,
        "stories": stories,
        "total": len(stories),
    }


@router.get("/feed/discover")
async def discover_stories(
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="latest", pattern="^(latest|trending|most_continued)$"),
    current_user: dict = Depends(get_optional_user),
):
    """
    Public discovery feed — ALL public stories from ALL users.
    Paginated, filterable. This is the core cross-user discovery endpoint.
    """
    sort_key = {
        "latest": [("created_at", -1)],
        "trending": [("battle_score", -1)],
        "most_continued": [("total_children", -1)],
    }.get(sort_by, [("created_at", -1)])

    stories = await db.story_engine_jobs.find(
        {
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
            "visibility": {"$in": ["public", None]},
            "is_seed_content": {"$ne": True},
        },
        {
            "_id": 0,
            "job_id": 1, "title": 1, "user_id": 1, "state": 1,
            "continuation_type": 1, "chain_depth": 1,
            "total_children": 1, "total_views": 1, "total_shares": 1,
            "battle_score": 1, "thumbnail_url": 1, "output_url": 1,
            "created_at": 1, "animation_style": 1, "root_story_id": 1,
            "derivative_label": 1, "source_story_title": 1, "source_creator_name": 1,
            "story_text": 1,
        }
    ).sort(sort_key).skip(offset).limit(limit).to_list(limit)

    user_ids = list({s.get("user_id") for s in stories if s.get("user_id")})
    user_map = {}
    if user_ids:
        users = await db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "name": 1, "email": 1}
        ).to_list(100)
        user_map = {u["id"]: u.get("name") or u.get("email", "").split("@")[0] for u in users}

    for s in stories:
        s["creator_name"] = user_map.get(s.get("user_id"), "Anonymous")
        # Trim story_text for feed display
        if s.get("story_text") and len(s["story_text"]) > 200:
            s["story_text"] = s["story_text"][:200] + "..."

    total = await db.story_engine_jobs.count_documents({
        "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        "visibility": {"$in": ["public", None]},
        "is_seed_content": {"$ne": True},
    })

    return {
        "success": True,
        "stories": stories,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total,
    }


@router.get("/feed/continue-watching")
async def continue_watching_feed(
    limit: int = Query(default=20, le=50),
    current_user: dict = Depends(get_current_user),
):
    """
    Continue Watching — stories this user has previously viewed (own + others' public).
    Based on watch_history collection.
    """
    user_id = current_user.get("id") or str(current_user.get("_id"))

    # Get recent watch history
    history = await db.watch_history.find(
        {"user_id": user_id},
        {"_id": 0, "job_id": 1}
    ).sort("last_viewed_at", -1).limit(limit).to_list(limit)

    if not history:
        return {"success": True, "stories": [], "total": 0}

    job_ids = [h["job_id"] for h in history]

    stories = await db.story_engine_jobs.find(
        {
            "job_id": {"$in": job_ids},
            "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]},
        },
        {
            "_id": 0,
            "job_id": 1, "title": 1, "user_id": 1, "state": 1,
            "total_views": 1, "thumbnail_url": 1, "output_url": 1,
            "created_at": 1, "animation_style": 1, "root_story_id": 1,
            "continuation_type": 1, "chain_depth": 1,
            "derivative_label": 1, "source_story_title": 1,
        }
    ).to_list(limit)

    # Preserve watch history order
    story_map = {s["job_id"]: s for s in stories}
    ordered = [story_map[jid] for jid in job_ids if jid in story_map]

    user_ids = list({s.get("user_id") for s in ordered if s.get("user_id")})
    user_map = {}
    if user_ids:
        users = await db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "name": 1, "email": 1}
        ).to_list(100)
        user_map = {u["id"]: u.get("name") or u.get("email", "").split("@")[0] for u in users}

    for s in ordered:
        s["creator_name"] = user_map.get(s.get("user_id"), "Anonymous")

    return {
        "success": True,
        "stories": ordered,
        "total": len(ordered),
    }


# ═══════════════════════════════════════════════════════════════
# INDEXES — Create DB indexes for performance
# ═══════════════════════════════════════════════════════════════

async def create_multiplayer_indexes():
    """Create indexes for story multiplayer queries."""
    try:
        collection = db.story_engine_jobs
        await collection.create_index("root_story_id")
        await collection.create_index("parent_job_id")
        await collection.create_index("continuation_type")
        await collection.create_index("battle_score")
        await collection.create_index("visibility")
        await collection.create_index([("root_story_id", 1), ("continuation_type", 1)])
        await collection.create_index([("parent_job_id", 1), ("continuation_type", 1), ("battle_score", -1)])
        await collection.create_index([("visibility", 1), ("state", 1), ("created_at", -1)])
        await collection.create_index([("visibility", 1), ("state", 1), ("battle_score", -1)])
        await db.watch_history.create_index([("user_id", 1), ("last_viewed_at", -1)])
        await db.watch_history.create_index([("user_id", 1), ("job_id", 1)], unique=True)
        logger.info("[MULTIPLAYER] Indexes created successfully")
    except Exception as e:
        logger.warning(f"[MULTIPLAYER] Index creation failed: {e}")
