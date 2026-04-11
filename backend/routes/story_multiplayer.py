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
from datetime import datetime, timezone
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
) -> float:
    """
    Weighted composite ranking score.
    - continues * 5 + shares * 3 + views * 1
    - depth multiplier: 1 + (chain_depth * 0.2)
    - recency boost: 1 / (1 + hours_since_creation * 0.05)
    - anti-gaming: if continues/views < 0.02 → score * 0.5
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

    final_score = base_score * depth_multiplier * recency_boost

    # Anti-gaming: low engagement ratio penalty
    if total_views > 0 and total_children / max(total_views, 1) < 0.02:
        if total_views > 50:  # Only apply after meaningful sample
            final_score *= 0.5

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
    """Recompute and persist battle_score for a single job."""
    job = await db.story_engine_jobs.find_one(
        {"job_id": job_id},
        {"_id": 0, "total_children": 1, "total_shares": 1, "total_views": 1,
         "chain_depth": 1, "created_at": 1}
    )
    if not job:
        return None

    score = compute_battle_score(
        total_children=job.get("total_children", 0),
        total_shares=job.get("total_shares", 0),
        total_views=job.get("total_views", 0),
        chain_depth=job.get("chain_depth", 0),
        created_at_iso=job.get("created_at"),
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
         "animation_style": 1, "episode_number": 1}
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent story not found")

    if parent.get("state") not in ("READY", "PARTIAL_READY", "COMPLETED"):
        raise HTTPException(status_code=400, detail="Parent story must be completed before continuing")

    # Import create_job and run the pipeline
    from services.story_engine.pipeline import create_job, run_pipeline
    from fastapi import BackgroundTasks

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

    # Store additional metadata
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "animation_style": request.animation_style,
            "voice_preset": request.voice_preset,
            "quality_mode": request.quality_mode,
        }}
    )

    # Run pipeline in background
    import asyncio
    asyncio.create_task(run_pipeline(job_id))

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
         "chain_depth": 1, "title": 1, "user_id": 1, "state": 1}
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent story not found")

    if parent.get("state") not in ("READY", "PARTIAL_READY", "COMPLETED"):
        raise HTTPException(status_code=400, detail="Parent story must be completed before branching")

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
        }}
    )

    # Run pipeline in background
    import asyncio
    asyncio.create_task(run_pipeline(job_id))

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

    return {"success": True, "job_id": request.job_id, "metric": request.metric, "battle_score": new_score}


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
        await collection.create_index([("root_story_id", 1), ("continuation_type", 1)])
        await collection.create_index([("parent_job_id", 1), ("continuation_type", 1), ("battle_score", -1)])
        logger.info("[MULTIPLAYER] Indexes created successfully")
    except Exception as e:
        logger.warning(f"[MULTIPLAYER] Index creation failed: {e}")
