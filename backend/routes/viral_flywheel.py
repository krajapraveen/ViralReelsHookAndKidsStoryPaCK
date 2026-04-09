"""
Viral Flywheel Engine v1 — Core Routes
Handles: attribution tracking, remix lineage, creator rewards, viral leaderboard.
Collections: viral_referrals, remix_lineage, creator_rewards
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, logger, get_current_user

router = APIRouter(prefix="/viral", tags=["Viral Flywheel"])


# ─── Models ──────────────────────────────────────────────────────────────────

class TrackShareClick(BaseModel):
    share_slug: str
    referrer_user_id: Optional[str] = None
    session_id: str = ""
    traffic_source: str = "direct"

class TrackShareConversion(BaseModel):
    share_slug: str
    session_id: str = ""
    conversion_type: str = "remix"  # remix | signup
    new_job_id: Optional[str] = None
    new_user_id: Optional[str] = None

class RecordLineage(BaseModel):
    child_job_id: str
    parent_job_id: str
    parent_share_slug: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SHARE ATTRIBUTION TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/track-click")
async def track_share_click(data: TrackShareClick):
    """Track when a shared link is clicked by a visitor.
    Creates a viral_referral record linking source creator to visitor."""
    # Look up the share to find the source creator
    share = await db.shares.find_one(
        {"id": data.share_slug},
        {"_id": 0, "userId": 1, "generationId": 1, "title": 1}
    )
    if not share:
        # Also try slug-based lookup via public creations
        creation = await db.story_engine_jobs.find_one(
            {"slug": data.share_slug},
            {"_id": 0, "user_id": 1, "job_id": 1, "title": 1}
        )
        if not creation:
            return {"ok": True, "tracked": False}
        source_user_id = creation.get("user_id", "")
        generation_id = creation.get("job_id", "")
        title = creation.get("title", "")
    else:
        source_user_id = share.get("userId", "")
        generation_id = share.get("generationId", "")
        title = share.get("title", "")

    # Calculate attribution depth
    depth = 1
    if share and share.get("parentShareId"):
        # This share is already a fork — increment depth
        parent = await db.shares.find_one(
            {"id": share["parentShareId"]},
            {"_id": 0, "userId": 1}
        )
        if parent:
            # Check if parent also has a parent
            existing_ref = await db.viral_referrals.find_one(
                {"share_slug": share["parentShareId"]},
                {"_id": 0, "attribution_depth": 1}
            )
            depth = (existing_ref.get("attribution_depth", 1) if existing_ref else 1) + 1

    referral = {
        "share_slug": data.share_slug,
        "share_source_user": source_user_id,
        "generation_id": generation_id,
        "title": title,
        "click_session_id": data.session_id,
        "traffic_source": data.traffic_source,
        "attribution_depth": depth,
        "clicked_at": datetime.now(timezone.utc).isoformat(),
        "converted": False,
        "conversion_type": None,
        "converted_at": None,
        "share_conversion_user": None,
    }

    await db.viral_referrals.insert_one(referral)

    # Track analytics event
    await db.analytics_events.insert_one({
        "event": "shared_link_clicked",
        "data": {
            "share_slug": data.share_slug,
            "source_user": source_user_id,
            "traffic_source": data.traffic_source,
            "attribution_depth": depth,
        },
        "timestamp": datetime.now(timezone.utc),
    })

    return {"ok": True, "tracked": True, "attribution_depth": depth}


@router.post("/track-conversion")
async def track_share_conversion(data: TrackShareConversion):
    """Track when a share click converts to a remix or signup.
    Updates the referral record and creates lineage entry."""
    # Find the most recent unresolved referral for this slug+session
    referral = await db.viral_referrals.find_one(
        {"share_slug": data.share_slug, "click_session_id": data.session_id, "converted": False},
        {"_id": 1, "share_source_user": 1, "generation_id": 1, "attribution_depth": 1}
    )

    source_user = ""
    depth = 1
    if referral:
        source_user = referral.get("share_source_user", "")
        depth = referral.get("attribution_depth", 1)
        # Mark as converted
        await db.viral_referrals.update_one(
            {"_id": referral["_id"]},
            {"$set": {
                "converted": True,
                "conversion_type": data.conversion_type,
                "converted_at": datetime.now(timezone.utc).isoformat(),
                "share_conversion_user": data.new_user_id or "",
                "new_job_id": data.new_job_id,
            }}
        )

    # Track analytics
    event_name = "shared_story_remixed" if data.conversion_type == "remix" else "viral_referral_signup"
    await db.analytics_events.insert_one({
        "event": event_name,
        "data": {
            "share_slug": data.share_slug,
            "source_user": source_user,
            "new_user": data.new_user_id,
            "new_job_id": data.new_job_id,
            "attribution_depth": depth,
        },
        "timestamp": datetime.now(timezone.utc),
    })

    return {"ok": True, "converted": True, "source_user": source_user}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. REMIX LINEAGE TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/lineage")
async def record_lineage(data: RecordLineage, user: dict = Depends(get_current_user)):
    """Record parent→child remix relationship for visible attribution chain."""
    user_id = user.get("id") or str(user.get("_id"))

    # Get parent info
    parent_job = await db.story_engine_jobs.find_one(
        {"job_id": data.parent_job_id},
        {"_id": 0, "user_id": 1, "title": 1, "slug": 1}
    )

    lineage = {
        "child_job_id": data.child_job_id,
        "child_user_id": user_id,
        "parent_job_id": data.parent_job_id,
        "parent_user_id": parent_job.get("user_id", "") if parent_job else "",
        "parent_title": parent_job.get("title", "") if parent_job else "",
        "parent_slug": parent_job.get("slug", "") if parent_job else "",
        "parent_share_slug": data.parent_share_slug,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Upsert to avoid duplicates
    await db.remix_lineage.update_one(
        {"child_job_id": data.child_job_id},
        {"$set": lineage},
        upsert=True,
    )

    # Track chain creation
    await db.analytics_events.insert_one({
        "event": "viral_chain_created",
        "data": {
            "child_job_id": data.child_job_id,
            "parent_job_id": data.parent_job_id,
            "parent_user": lineage["parent_user_id"],
            "child_user": user_id,
        },
        "timestamp": datetime.now(timezone.utc),
    })

    # Notify original creator (grouped)
    if parent_job and parent_job.get("user_id") and parent_job["user_id"] != user_id:
        await _notify_creator_remix(parent_job["user_id"], parent_job.get("title", ""), user_id)

    return {"ok": True, "lineage_recorded": True, "parent_title": lineage["parent_title"]}


@router.get("/lineage/{job_id}")
async def get_lineage(job_id: str):
    """Get the 'Inspired by' attribution chain for a job."""
    lineage = await db.remix_lineage.find_one(
        {"child_job_id": job_id},
        {"_id": 0}
    )
    if not lineage:
        return {"found": False, "lineage": None}

    return {
        "found": True,
        "lineage": {
            "parent_title": lineage.get("parent_title", ""),
            "parent_slug": lineage.get("parent_slug", ""),
            "parent_user_id": lineage.get("parent_user_id", ""),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CREATOR REWARDS (Share-to-Remix)
# ═══════════════════════════════════════════════════════════════════════════════

REWARD_PER_5_REMIXES = 1  # 1 credit per 5 remix conversions
MAX_DAILY_REWARD = 5      # Cap at 5 bonus credits/day

@router.get("/rewards/status")
async def get_reward_status(user: dict = Depends(get_current_user)):
    """Get current viral reward status for the logged-in creator."""
    user_id = user.get("id") or str(user.get("_id"))

    # Count total remix conversions from shares by this user
    total_conversions = await db.viral_referrals.count_documents({
        "share_source_user": user_id,
        "converted": True,
        "conversion_type": "remix",
    })

    # Count today's rewards
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_rewards = await db.creator_rewards.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start.isoformat()},
    })

    # Count total rewards earned
    total_rewards = await db.creator_rewards.count_documents({"user_id": user_id})

    return {
        "total_remix_conversions": total_conversions,
        "total_credits_earned": total_rewards * REWARD_PER_5_REMIXES,
        "today_credits_earned": today_rewards * REWARD_PER_5_REMIXES,
        "daily_cap": MAX_DAILY_REWARD,
        "conversions_until_next_reward": 5 - (total_conversions % 5) if total_conversions % 5 != 0 else 0,
    }


@router.post("/rewards/check-and-grant")
async def check_and_grant_rewards(user: dict = Depends(get_current_user)):
    """Check if creator is eligible for reward credits and grant them."""
    user_id = user.get("id") or str(user.get("_id"))

    total_conversions = await db.viral_referrals.count_documents({
        "share_source_user": user_id,
        "converted": True,
        "conversion_type": "remix",
    })

    # How many rewards should have been granted total
    expected_rewards = total_conversions // 5

    # How many already granted
    existing_rewards = await db.creator_rewards.count_documents({"user_id": user_id})

    # Check daily cap
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_rewards = await db.creator_rewards.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start.isoformat()},
    })

    granted = 0
    while existing_rewards + granted < expected_rewards and today_rewards + granted < MAX_DAILY_REWARD:
        await db.creator_rewards.insert_one({
            "user_id": user_id,
            "credits": REWARD_PER_5_REMIXES,
            "reason": "viral_remix_conversion",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        # Add credits to user
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": REWARD_PER_5_REMIXES}},
        )
        await db.analytics_events.insert_one({
            "event": "reward_granted",
            "data": {"user_id": user_id, "credits": REWARD_PER_5_REMIXES, "reason": "viral_remix"},
            "timestamp": datetime.now(timezone.utc),
        })
        granted += 1

    return {"ok": True, "credits_granted": granted * REWARD_PER_5_REMIXES}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. VIRAL LEADERBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/leaderboard")
async def viral_leaderboard(limit: int = Query(10, le=25)):
    """Top viral creators ranked by weighted viral score.
    Score = (referred_remixes * 0.5) + (downstream_chain_depth * 0.3) + (viral_signups * 0.2)"""

    # Aggregate remix conversions per source user
    pipeline = [
        {"$match": {"converted": True}},
        {"$group": {
            "_id": "$share_source_user",
            "referred_remixes": {"$sum": {"$cond": [{"$eq": ["$conversion_type", "remix"]}, 1, 0]}},
            "viral_signups": {"$sum": {"$cond": [{"$eq": ["$conversion_type", "signup"]}, 1, 0]}},
            "max_depth": {"$max": "$attribution_depth"},
        }},
        {"$match": {"_id": {"$ne": ""}}},
    ]

    leaders = {}
    async for doc in db.viral_referrals.aggregate(pipeline):
        uid = doc["_id"]
        remixes = doc.get("referred_remixes", 0)
        signups = doc.get("viral_signups", 0)
        depth = doc.get("max_depth", 1)
        score = round(remixes * 0.5 + depth * 0.3 + signups * 0.2, 2)
        leaders[uid] = {
            "user_id": uid,
            "referred_remixes": remixes,
            "viral_signups": signups,
            "max_chain_depth": depth,
            "viral_score": score,
        }

    # Sort by viral_score, get top N
    ranked = sorted(leaders.values(), key=lambda x: x["viral_score"], reverse=True)[:limit]

    # Enrich with user names
    for entry in ranked:
        user = await db.users.find_one(
            {"id": entry["user_id"]},
            {"_id": 0, "name": 1, "picture": 1},
        )
        entry["name"] = user.get("name", "Creator") if user else "Creator"
        entry["picture"] = user.get("picture") if user else None

    return {"success": True, "leaderboard": ranked}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. VIRAL METRICS (for admin dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/metrics")
async def viral_metrics():
    """Core viral loop metrics for admin dashboard."""
    total_shares = await db.viral_referrals.count_documents({})
    total_clicks = total_shares  # Each referral = 1 click
    total_conversions = await db.viral_referrals.count_documents({"converted": True})
    total_remixes = await db.viral_referrals.count_documents({"converted": True, "conversion_type": "remix"})
    total_signups = await db.viral_referrals.count_documents({"converted": True, "conversion_type": "signup"})

    # Average attribution depth for converted referrals
    depth_pipeline = [
        {"$match": {"converted": True}},
        {"$group": {"_id": None, "avg_depth": {"$avg": "$attribution_depth"}}},
    ]
    avg_depth = 1.0
    async for doc in db.viral_referrals.aggregate(depth_pipeline):
        avg_depth = round(doc.get("avg_depth", 1.0), 2)

    # Click → remix conversion rate
    click_to_remix = round(total_remixes / total_clicks * 100, 2) if total_clicks > 0 else 0
    # Click → signup conversion rate
    click_to_signup = round(total_signups / total_clicks * 100, 2) if total_clicks > 0 else 0

    # Viral coefficient estimate: avg remixes per creator who shares
    unique_sharers = len(await db.viral_referrals.distinct("share_source_user"))
    viral_coefficient = round(total_remixes / unique_sharers, 2) if unique_sharers > 0 else 0

    return {
        "success": True,
        "metrics": {
            "total_share_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_remixes": total_remixes,
            "total_signups": total_signups,
            "click_to_remix_rate": click_to_remix,
            "click_to_signup_rate": click_to_signup,
            "avg_attribution_depth": avg_depth,
            "viral_coefficient": viral_coefficient,
            "unique_sharers": unique_sharers,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 6. VIRAL CHAIN STATS (per-user top story chain + momentum)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/chain-stats")
async def viral_chain_stats(user: dict = Depends(get_current_user)):
    """Get the user's top viral story chain with momentum signals.
    Returns the single strongest chain for focused display."""
    user_id = user.get("id") or str(user.get("_id"))

    # Find stories by this user that have been remixed (they appear as parent in lineage)
    pipeline = [
        {"$match": {"parent_user_id": user_id}},
        {"$group": {
            "_id": "$parent_job_id",
            "parent_title": {"$first": "$parent_title"},
            "parent_slug": {"$first": "$parent_slug"},
            "remix_count": {"$sum": 1},
            "unique_remixers": {"$addToSet": "$child_user_id"},
            "latest_remix": {"$max": "$created_at"},
        }},
        {"$sort": {"remix_count": -1}},
        {"$limit": 1},
    ]

    top_story = None
    async for doc in db.remix_lineage.aggregate(pipeline):
        # Calculate chain depth: how deep does this story's influence go
        max_depth = 1
        child_ids = [doc["_id"]]
        checked = set()
        for level in range(5):  # Max 5 levels deep
            next_children = []
            for cid in child_ids:
                if cid in checked:
                    continue
                checked.add(cid)
                async for child in db.remix_lineage.find(
                    {"parent_job_id": cid},
                    {"_id": 0, "child_job_id": 1}
                ):
                    next_children.append(child["child_job_id"])
            if not next_children:
                break
            child_ids = next_children
            max_depth = level + 2

        # Momentum: count remixes in last 7 days
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent_remixes = await db.remix_lineage.count_documents({
            "parent_job_id": doc["_id"],
            "created_at": {"$gte": week_ago},
        })

        # Today's remixes
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
        today_remixes = await db.remix_lineage.count_documents({
            "parent_job_id": doc["_id"],
            "created_at": {"$gte": today_start},
        })

        top_story = {
            "job_id": doc["_id"],
            "title": doc.get("parent_title", "Your Story"),
            "slug": doc.get("parent_slug", ""),
            "total_remixes": doc["remix_count"],
            "unique_creators_inspired": len(doc.get("unique_remixers", [])),
            "chain_depth": max_depth,
            "latest_remix_at": doc.get("latest_remix"),
            "remixes_this_week": recent_remixes,
            "remixes_today": today_remixes,
        }

    if not top_story:
        return {"success": True, "has_chain": False, "top_story": None}

    return {"success": True, "has_chain": True, "top_story": top_story}


# ═══════════════════════════════════════════════════════════════════════════════
# 7. VIRAL MILESTONES
# ═══════════════════════════════════════════════════════════════════════════════

MILESTONE_DEFS = [
    {"id": "first_viral_remix", "label": "First Viral Remix", "icon": "sparkles", "threshold_field": "total_remixes", "threshold": 1},
    {"id": "inspired_5", "label": "Inspired 5 Creators", "icon": "users", "threshold_field": "unique_creators", "threshold": 5},
    {"id": "inspired_10", "label": "Inspired 10 Creators", "icon": "users", "threshold_field": "unique_creators", "threshold": 10},
    {"id": "depth_3", "label": "Spread Across 3 Levels", "icon": "layers", "threshold_field": "max_depth", "threshold": 3},
    {"id": "depth_5", "label": "Spread Across 5 Levels", "icon": "layers", "threshold_field": "max_depth", "threshold": 5},
    {"id": "viral_25", "label": "25 Viral Remixes", "icon": "flame", "threshold_field": "total_remixes", "threshold": 25},
]

@router.get("/milestones")
async def viral_milestones(user: dict = Depends(get_current_user)):
    """Get viral milestone badges for the user."""
    user_id = user.get("id") or str(user.get("_id"))

    # Aggregate user's viral stats
    total_remixes = await db.remix_lineage.count_documents({"parent_user_id": user_id})
    unique_creators = len(await db.remix_lineage.distinct("child_user_id", {"parent_user_id": user_id}))

    # Calculate max depth across all stories
    max_depth = 1
    parent_jobs = await db.remix_lineage.distinct("parent_job_id", {"parent_user_id": user_id})
    for pj in parent_jobs[:10]:  # Cap at 10 stories to avoid perf issues
        depth = 1
        children = [pj]
        for level in range(5):
            next_c = []
            async for c in db.remix_lineage.find({"parent_job_id": {"$in": children}}, {"_id": 0, "child_job_id": 1}):
                next_c.append(c["child_job_id"])
            if not next_c:
                break
            children = next_c
            depth = level + 2
        max_depth = max(max_depth, depth)

    stats = {
        "total_remixes": total_remixes,
        "unique_creators": unique_creators,
        "max_depth": max_depth,
    }

    earned = []
    upcoming = []
    for m in MILESTONE_DEFS:
        current_val = stats.get(m["threshold_field"], 0)
        if current_val >= m["threshold"]:
            earned.append({**m, "current": current_val})
        else:
            upcoming.append({**m, "current": current_val, "remaining": m["threshold"] - current_val})

    # Award new milestones (track in DB)
    for ms in earned:
        existing = await db.viral_milestones.find_one(
            {"user_id": user_id, "milestone_id": ms["id"]},
            {"_id": 1}
        )
        if not existing:
            await db.viral_milestones.insert_one({
                "user_id": user_id,
                "milestone_id": ms["id"],
                "label": ms["label"],
                "earned_at": datetime.now(timezone.utc).isoformat(),
            })
            await db.analytics_events.insert_one({
                "event": "viral_milestone_awarded",
                "data": {"user_id": user_id, "milestone": ms["id"]},
                "timestamp": datetime.now(timezone.utc),
            })

    return {
        "success": True,
        "earned": earned,
        "upcoming": upcoming[:2],  # Show next 2 milestones only
        "stats": stats,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _notify_creator_remix(creator_user_id: str, story_title: str, remixer_user_id: str):
    """Create a grouped notification with emotional, momentum-driven copy."""
    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y-%m-%d")

    # Count total remixes this week for momentum language
    week_ago = (now - timedelta(days=7)).isoformat()
    week_remixes = await db.remix_lineage.count_documents({
        "parent_user_id": creator_user_id,
        "created_at": {"$gte": week_ago},
    })

    # Check for existing grouped notification today
    existing = await db.notifications.find_one(
        {"user_id": creator_user_id, "type": "viral_remix", "group_key": today_key},
        {"_id": 1, "count": 1},
    )

    if existing:
        count = existing.get("count", 1) + 1
        # Emotional, momentum-driven title
        if count >= 5:
            title = f"Your stories inspired {count} creators today — you're on fire!"
        elif count >= 2:
            title = f"Your story inspired {count} creators this week — you're gaining momentum"
        else:
            title = f"Your story \"{story_title[:30]}\" just inspired another creator"

        await db.notifications.update_one(
            {"_id": existing["_id"]},
            {
                "$inc": {"count": 1},
                "$set": {
                    "title": title,
                    "message": f"Your shared stories are spreading! {week_remixes} remixes this week.",
                    "updated_at": now.isoformat(),
                    "read": False,
                },
                "$push": {"remixer_ids": {"$each": [remixer_user_id], "$slice": -10}},
            },
        )
    else:
        # First remix today — emotionally warm
        title = f"Your story \"{story_title[:30]}\" just inspired a new creator"
        message = "Every share spreads your creation to new audiences!"
        if week_remixes > 1:
            message = f"{week_remixes} creators inspired this week — keep sharing!"

        await db.notifications.insert_one({
            "user_id": creator_user_id,
            "type": "viral_remix",
            "group_key": today_key,
            "title": title,
            "message": message,
            "count": 1,
            "remixer_ids": [remixer_user_id],
            "read": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "link": "/app/my-space",
        })
