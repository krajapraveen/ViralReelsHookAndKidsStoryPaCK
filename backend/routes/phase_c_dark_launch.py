"""
Phase C Dark Launch Infrastructure — Hidden Gamification Engines
All engines compute and accumulate data silently. No public UI exposure.
Feature flag gates activation on readiness_score >= 4/5 AND viral_events >= 1000.
Collections: phase_c_leaderboard, phase_c_rank_snapshots, phase_c_rewards,
             phase_c_streaks, phase_c_achievements, phase_c_notifications
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, logger, get_current_user, get_admin_user

router = APIRouter(prefix="/phase-c", tags=["Phase C Dark Launch"])

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

RANK_TIERS = [
    {"id": "diamond", "label": "Diamond", "min_score": 50, "color": "#b9f2ff"},
    {"id": "gold", "label": "Gold", "min_score": 25, "color": "#ffd700"},
    {"id": "silver", "label": "Silver", "min_score": 10, "color": "#c0c0c0"},
    {"id": "bronze", "label": "Bronze", "min_score": 1, "color": "#cd7f32"},
]

STREAK_TIERS = [
    {"id": "streak_30", "label": "30-Day Legend", "days": 30, "reward_credits": 10},
    {"id": "streak_14", "label": "14-Day Machine", "days": 14, "reward_credits": 5},
    {"id": "streak_7", "label": "7-Day Warrior", "days": 7, "reward_credits": 3},
    {"id": "streak_3", "label": "3-Day Starter", "days": 3, "reward_credits": 1},
]

FREEZE_EARN_INTERVAL = 7  # Earn 1 freeze token every 7 streak days
REWARD_EXPIRY_DAYS = 7  # Rewards expire 7 days after Phase C activation
MIN_VIRAL_EVENTS_FOR_ACTIVATION = 1000


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FEATURE FLAG — Phase C Activation Status
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def phase_c_status():
    """Check if Phase C should be activated.
    Requires BOTH: 4/5 readiness thresholds AND 1000+ viral referral events."""

    # Import readiness logic inline to avoid circular deps
    from routes.viral_flywheel import READINESS_THRESHOLDS

    # Condition A: Check readiness thresholds (reuse existing logic)
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Repeat share rate
    recent_sharers = await db.viral_referrals.distinct(
        "share_source_user",
        {"clicked_at": {"$gte": week_ago}, "share_source_user": {"$ne": ""}}
    )
    total_sharers = len(recent_sharers)
    repeat_pipeline = [
        {"$match": {"clicked_at": {"$gte": week_ago}, "share_source_user": {"$ne": ""}}},
        {"$group": {"_id": {"user": "$share_source_user", "slug": "$share_slug"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 2}}},
        {"$group": {"_id": "$_id.user"}},
    ]
    repeat_sharers = 0
    async for _ in db.viral_referrals.aggregate(repeat_pipeline):
        repeat_sharers += 1
    repeat_share_rate = round(repeat_sharers / total_sharers * 100, 1) if total_sharers > 0 else 0

    # Chain depth rate
    total_chains = await db.viral_referrals.count_documents({"clicked_at": {"$gte": week_ago}})
    deep_chains = await db.viral_referrals.count_documents({
        "clicked_at": {"$gte": week_ago}, "attribution_depth": {"$gte": 2}
    })
    chain_depth_rate = round(deep_chains / total_chains * 100, 1) if total_chains > 0 else 0

    # Return-to-inspect rate
    chain_views = await db.analytics_events.count_documents({
        "event": "viral_chain_viewed",
        "timestamp": {"$gte": datetime.now(timezone.utc) - timedelta(hours=72)},
    })
    creators_with_chains = len(await db.remix_lineage.distinct("parent_user_id"))
    return_to_inspect = round(chain_views / creators_with_chains * 100, 1) if creators_with_chains > 0 else 0

    # Click-to-remix
    total_clicks_all = await db.viral_referrals.count_documents({})
    total_remix_conversions = await db.viral_referrals.count_documents({
        "converted": True, "conversion_type": "remix"
    })
    click_to_remix = round(total_remix_conversions / total_clicks_all * 100, 1) if total_clicks_all > 0 else 0

    # Milestone engagement
    users_with_milestones = len(await db.viral_milestones.distinct("user_id"))
    milestone_interactions = await db.analytics_events.count_documents({
        "event": {"$in": ["viral_chain_viewed", "viral_milestone_awarded"]},
    })
    milestone_engagement = round(milestone_interactions / max(users_with_milestones, 1) * 100, 1) if users_with_milestones > 0 else 0

    thresholds_passing = sum([
        repeat_share_rate >= READINESS_THRESHOLDS["repeat_share_rate"]["threshold"],
        chain_depth_rate >= READINESS_THRESHOLDS["chain_depth_rate"]["threshold"],
        return_to_inspect >= READINESS_THRESHOLDS["return_to_inspect_rate"]["threshold"],
        click_to_remix >= READINESS_THRESHOLDS["click_to_remix_rate"]["threshold"],
        milestone_engagement >= READINESS_THRESHOLDS["milestone_engagement_rate"]["threshold"],
    ])

    # Condition B: Minimum viral sample volume
    total_viral_events = await db.viral_referrals.count_documents({})

    condition_a = thresholds_passing >= 4
    condition_b = total_viral_events >= MIN_VIRAL_EVENTS_FOR_ACTIVATION

    enable_phase_c = condition_a and condition_b

    return {
        "success": True,
        "enable_phase_c": enable_phase_c,
        "thresholds_passing": thresholds_passing,
        "required_thresholds": 4,
        "total_viral_events": total_viral_events,
        "required_viral_events": MIN_VIRAL_EVENTS_FOR_ACTIVATION,
        "condition_a_met": condition_a,
        "condition_b_met": condition_b,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LEADERBOARD ENGINE — Compute rankings silently
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/engine/compute-leaderboard")
async def compute_leaderboard(admin: dict = Depends(get_admin_user)):
    """Compute competitive rankings and store as hidden leaderboard.
    Score = (remixes * 0.5) + (chain_depth * 0.3) + (signups * 0.2) + (streak_bonus * 0.1)
    Also stores a daily rank snapshot for momentum tracking."""

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

    rankings = []
    async for doc in db.viral_referrals.aggregate(pipeline):
        uid = doc["_id"]
        remixes = doc.get("referred_remixes", 0)
        signups = doc.get("viral_signups", 0)
        depth = doc.get("max_depth", 1)

        # Streak bonus from phase_c_streaks
        streak_doc = await db.phase_c_streaks.find_one(
            {"user_id": uid}, {"_id": 0, "streak_days": 1}
        )
        streak_days = streak_doc.get("streak_days", 0) if streak_doc else 0
        streak_bonus = min(streak_days, 30)  # Cap at 30

        score = round(remixes * 0.5 + depth * 0.3 + signups * 0.2 + streak_bonus * 0.1, 2)

        # Determine rank tier
        rank_tier = "unranked"
        for tier in RANK_TIERS:
            if score >= tier["min_score"]:
                rank_tier = tier["id"]
                break

        rankings.append({
            "user_id": uid,
            "viral_score": score,
            "referred_remixes": remixes,
            "viral_signups": signups,
            "max_chain_depth": depth,
            "streak_days": streak_days,
            "rank_tier": rank_tier,
        })

    # Sort by score descending
    rankings.sort(key=lambda x: x["viral_score"], reverse=True)

    # Assign rank positions
    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y-%m-%d")

    for i, entry in enumerate(rankings):
        entry["rank_position"] = i + 1
        entry["computed_at"] = now.isoformat()

        # Upsert into leaderboard
        await db.phase_c_leaderboard.update_one(
            {"user_id": entry["user_id"]},
            {"$set": entry},
            upsert=True,
        )

        # Store daily snapshot (for "You climbed X places this week")
        await db.phase_c_rank_snapshots.update_one(
            {"user_id": entry["user_id"], "snapshot_date": today_key},
            {"$set": {
                "user_id": entry["user_id"],
                "snapshot_date": today_key,
                "rank_position": entry["rank_position"],
                "viral_score": entry["viral_score"],
                "rank_tier": entry["rank_tier"],
                "recorded_at": now.isoformat(),
            }},
            upsert=True,
        )

    # Track hidden analytics
    await db.analytics_events.insert_one({
        "event": "hidden_rank_progress",
        "data": {
            "total_ranked": len(rankings),
            "tier_distribution": {
                tier["id"]: sum(1 for r in rankings if r["rank_tier"] == tier["id"])
                for tier in RANK_TIERS
            },
        },
        "timestamp": now,
    })

    return {
        "success": True,
        "total_ranked": len(rankings),
        "tier_distribution": {
            tier["id"]: sum(1 for r in rankings if r["rank_tier"] == tier["id"])
            for tier in RANK_TIERS
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. REWARD CALCULATION ENGINE — Silent accrual with expiry
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/engine/compute-rewards")
async def compute_rewards(admin: dict = Depends(get_admin_user)):
    """Silently accumulate pending rewards based on rank and streak achievements.
    Rewards include earned_at and expires_at (7 days after Phase C activation).
    Also pre-builds competition notification drafts."""

    now = datetime.now(timezone.utc)
    rewards_created = 0
    notifications_drafted = 0

    # 1. Rank-based rewards: credit bonus for each tier reached
    rank_rewards = {
        "diamond": 15,
        "gold": 10,
        "silver": 5,
        "bronze": 2,
    }

    async for entry in db.phase_c_leaderboard.find({}, {"_id": 0}):
        uid = entry.get("user_id", "")
        tier = entry.get("rank_tier", "unranked")

        if tier in rank_rewards:
            # Check if rank reward already exists for this tier
            existing = await db.phase_c_rewards.find_one({
                "user_id": uid, "reward_type": "rank_tier", "tier": tier
            })
            if not existing:
                await db.phase_c_rewards.insert_one({
                    "user_id": uid,
                    "reward_type": "rank_tier",
                    "tier": tier,
                    "credits": rank_rewards[tier],
                    "status": "pending",
                    "earned_at": now.isoformat(),
                    "expires_at": None,  # Set when Phase C activates
                    "description": f"Reached {tier.capitalize()} rank",
                })
                rewards_created += 1

    # 2. Streak-based rewards from phase_c_streaks
    async for streak in db.phase_c_streaks.find({}, {"_id": 0}):
        uid = streak.get("user_id", "")
        days = streak.get("streak_days", 0)

        for st in STREAK_TIERS:
            if days >= st["days"]:
                existing = await db.phase_c_rewards.find_one({
                    "user_id": uid, "reward_type": "streak_tier", "tier": st["id"]
                })
                if not existing:
                    await db.phase_c_rewards.insert_one({
                        "user_id": uid,
                        "reward_type": "streak_tier",
                        "tier": st["id"],
                        "credits": st["reward_credits"],
                        "status": "pending",
                        "earned_at": now.isoformat(),
                        "expires_at": None,
                        "description": f"Achieved {st['label']} streak",
                    })
                    rewards_created += 1

    # 3. Pre-build competition notification drafts
    # "Rank up" notifications for top movers
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    async for entry in db.phase_c_leaderboard.find(
        {"rank_position": {"$lte": 25}}, {"_id": 0}
    ):
        uid = entry.get("user_id", "")
        current_rank = entry.get("rank_position", 0)

        # Find rank 7 days ago
        old_snapshot = await db.phase_c_rank_snapshots.find_one(
            {"user_id": uid, "snapshot_date": {"$lte": week_ago}},
            {"_id": 0, "rank_position": 1},
            sort=[("snapshot_date", -1)],
        )
        old_rank = old_snapshot.get("rank_position", current_rank) if old_snapshot else current_rank
        rank_change = old_rank - current_rank

        if rank_change > 0:
            existing_notif = await db.phase_c_notifications.find_one({
                "user_id": uid, "type": "rank_climb", "week_key": now.strftime("%Y-W%W")
            })
            if not existing_notif:
                await db.phase_c_notifications.insert_one({
                    "user_id": uid,
                    "type": "rank_climb",
                    "week_key": now.strftime("%Y-W%W"),
                    "title": f"You climbed {rank_change} place{'s' if rank_change > 1 else ''} this week!",
                    "message": f"You're now ranked #{current_rank} among all creators.",
                    "status": "draft",
                    "created_at": now.isoformat(),
                })
                notifications_drafted += 1

    # Track hidden analytics
    await db.analytics_events.insert_one({
        "event": "hidden_reward_pending",
        "data": {"rewards_created": rewards_created, "notifications_drafted": notifications_drafted},
        "timestamp": now,
    })

    total_pending = await db.phase_c_rewards.count_documents({"status": "pending"})
    total_drafts = await db.phase_c_notifications.count_documents({"status": "draft"})

    return {
        "success": True,
        "new_rewards_created": rewards_created,
        "new_notifications_drafted": notifications_drafted,
        "total_pending_rewards": total_pending,
        "total_draft_notifications": total_drafts,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. STREAK TRACKING ENGINE — Enhanced with tiers and freeze tokens
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/engine/compute-streaks")
async def compute_streaks(admin: dict = Depends(get_admin_user)):
    """Compute and store enhanced streak data for all active users.
    Tracks streak days, tiers, freeze tokens (1 per 7 streak days), and loss events."""

    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y-%m-%d")
    streaks_updated = 0
    freezes_used = 0

    # Get all users with recent activity (last 60 days)
    sixty_days_ago = (now - timedelta(days=60)).isoformat()
    active_users = await db.jobs.distinct("user_id", {
        "created_at": {"$gte": sixty_days_ago},
        "status": {"$in": ["COMPLETED", "PARTIAL"]},
    })

    for uid in active_users:
        if not uid:
            continue

        # Calculate streak from scratch (consistent with existing streaks.py logic)
        streak_days = 0
        check_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        missed_today = False

        for i in range(60):
            day_start = check_date - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            had_gen = await db.jobs.count_documents({
                "user_id": uid,
                "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()},
                "status": {"$in": ["COMPLETED", "PARTIAL"]},
            })
            if had_gen > 0:
                streak_days += 1
            else:
                if i == 0:
                    missed_today = True
                    continue
                break

        # Get existing streak record
        existing = await db.phase_c_streaks.find_one(
            {"user_id": uid}, {"_id": 0}
        )
        prev_streak = existing.get("streak_days", 0) if existing else 0

        # Calculate freeze tokens: 1 per 7 streak days
        freeze_tokens_earned = streak_days // FREEZE_EARN_INTERVAL
        freeze_tokens_used = existing.get("freeze_tokens_used", 0) if existing else 0
        freeze_tokens_available = max(0, freeze_tokens_earned - freeze_tokens_used)

        # Check for streak break (had a streak yesterday but missed today)
        streak_broken = False
        if prev_streak > 0 and streak_days == 0 and missed_today:
            # Auto-use a freeze token if available
            if freeze_tokens_available > 0:
                streak_days = prev_streak  # Preserve streak
                freeze_tokens_used += 1
                freeze_tokens_available -= 1
                freezes_used += 1
            else:
                streak_broken = True

        # Determine current streak tier
        current_tier = None
        for st in STREAK_TIERS:
            if streak_days >= st["days"]:
                current_tier = st["id"]
                break

        # Best streak ever
        best_streak = max(streak_days, existing.get("best_streak", 0) if existing else 0)

        streak_doc = {
            "user_id": uid,
            "streak_days": streak_days,
            "best_streak": best_streak,
            "current_tier": current_tier,
            "freeze_tokens_earned": freeze_tokens_earned,
            "freeze_tokens_used": freeze_tokens_used,
            "freeze_tokens_available": freeze_tokens_available,
            "streak_broken": streak_broken,
            "last_computed": now.isoformat(),
            "last_active_date": today_key,
        }

        await db.phase_c_streaks.update_one(
            {"user_id": uid},
            {"$set": streak_doc},
            upsert=True,
        )
        streaks_updated += 1

    # Track hidden analytics
    total_active_streaks = await db.phase_c_streaks.count_documents({"streak_days": {"$gte": 1}})
    tier_counts = {}
    for st in STREAK_TIERS:
        tier_counts[st["id"]] = await db.phase_c_streaks.count_documents({"current_tier": st["id"]})

    await db.analytics_events.insert_one({
        "event": "hidden_streak_days",
        "data": {
            "streaks_updated": streaks_updated,
            "active_streaks": total_active_streaks,
            "freezes_auto_used": freezes_used,
            "tier_distribution": tier_counts,
        },
        "timestamp": now,
    })

    return {
        "success": True,
        "streaks_updated": streaks_updated,
        "active_streaks": total_active_streaks,
        "freezes_auto_used": freezes_used,
        "tier_distribution": tier_counts,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ACHIEVEMENT FRAMEWORK — Badges computed and stored, never displayed
# ═══════════════════════════════════════════════════════════════════════════════

ACHIEVEMENT_DEFS = [
    # Rank badges
    {"id": "rank_bronze", "category": "rank", "label": "Bronze Creator", "condition_field": "rank_tier", "condition_value": "bronze"},
    {"id": "rank_silver", "category": "rank", "label": "Silver Creator", "condition_field": "rank_tier", "condition_value": "silver"},
    {"id": "rank_gold", "category": "rank", "label": "Gold Creator", "condition_field": "rank_tier", "condition_value": "gold"},
    {"id": "rank_diamond", "category": "rank", "label": "Diamond Creator", "condition_field": "rank_tier", "condition_value": "diamond"},
    # Streak badges
    {"id": "streak_3", "category": "streak", "label": "3-Day Starter", "condition_field": "streak_tier", "condition_value": "streak_3"},
    {"id": "streak_7", "category": "streak", "label": "7-Day Warrior", "condition_field": "streak_tier", "condition_value": "streak_7"},
    {"id": "streak_14", "category": "streak", "label": "14-Day Machine", "condition_field": "streak_tier", "condition_value": "streak_14"},
    {"id": "streak_30", "category": "streak", "label": "30-Day Legend", "condition_field": "streak_tier", "condition_value": "streak_30"},
    # Reward milestones
    {"id": "first_reward", "category": "reward", "label": "First Hidden Reward", "condition_field": "rewards_count", "condition_value": 1},
    {"id": "rewards_5", "category": "reward", "label": "5 Rewards Earned", "condition_field": "rewards_count", "condition_value": 5},
    {"id": "rewards_10", "category": "reward", "label": "10 Rewards Earned", "condition_field": "rewards_count", "condition_value": 10},
]

@router.post("/engine/compute-achievements")
async def compute_achievements(admin: dict = Depends(get_admin_user)):
    """Compute and store achievement badges for all qualifying users."""

    now = datetime.now(timezone.utc)
    achievements_awarded = 0

    # Get all users in leaderboard or streaks
    leaderboard_users = await db.phase_c_leaderboard.distinct("user_id")
    streak_users = await db.phase_c_streaks.distinct("user_id")
    all_users = set(leaderboard_users + streak_users)

    for uid in all_users:
        if not uid:
            continue

        # Get user state
        lb_entry = await db.phase_c_leaderboard.find_one(
            {"user_id": uid}, {"_id": 0, "rank_tier": 1}
        )
        streak_entry = await db.phase_c_streaks.find_one(
            {"user_id": uid}, {"_id": 0, "current_tier": 1}
        )
        rewards_count = await db.phase_c_rewards.count_documents({"user_id": uid})

        user_state = {
            "rank_tier": lb_entry.get("rank_tier") if lb_entry else None,
            "streak_tier": streak_entry.get("current_tier") if streak_entry else None,
            "rewards_count": rewards_count,
        }

        for ach in ACHIEVEMENT_DEFS:
            field_val = user_state.get(ach["condition_field"])
            qualifies = False

            if ach["category"] == "rank":
                # Rank achievements: check if user's tier matches or exceeds
                tier_order = ["bronze", "silver", "gold", "diamond"]
                if field_val and field_val in tier_order:
                    user_tier_idx = tier_order.index(field_val)
                    required_idx = tier_order.index(ach["condition_value"])
                    qualifies = user_tier_idx >= required_idx
            elif ach["category"] == "streak":
                # Streak achievements: check if tier matches or exceeds
                tier_order = ["streak_3", "streak_7", "streak_14", "streak_30"]
                if field_val and field_val in tier_order:
                    user_tier_idx = tier_order.index(field_val)
                    required_idx = tier_order.index(ach["condition_value"])
                    qualifies = user_tier_idx >= required_idx
            elif ach["category"] == "reward":
                qualifies = (field_val or 0) >= ach["condition_value"]

            if qualifies:
                existing = await db.phase_c_achievements.find_one({
                    "user_id": uid, "achievement_id": ach["id"]
                })
                if not existing:
                    await db.phase_c_achievements.insert_one({
                        "user_id": uid,
                        "achievement_id": ach["id"],
                        "category": ach["category"],
                        "label": ach["label"],
                        "status": "hidden",
                        "earned_at": now.isoformat(),
                    })
                    achievements_awarded += 1

    # Track hidden analytics
    total_achievements = await db.phase_c_achievements.count_documents({})
    category_counts = {}
    for cat in ["rank", "streak", "reward"]:
        category_counts[cat] = await db.phase_c_achievements.count_documents({"category": cat})

    await db.analytics_events.insert_one({
        "event": "phase_c_activation_ready",
        "data": {
            "achievements_awarded": achievements_awarded,
            "total_achievements": total_achievements,
            "category_distribution": category_counts,
        },
        "timestamp": now,
    })

    return {
        "success": True,
        "new_achievements_awarded": achievements_awarded,
        "total_achievements": total_achievements,
        "category_distribution": category_counts,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 6. RUN ALL ENGINES (single admin trigger)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/engine/run-all")
async def run_all_engines(admin: dict = Depends(get_admin_user)):
    """Execute all Phase C engines in sequence: streaks → leaderboard → rewards → achievements."""
    results = {}

    streaks_result = await compute_streaks(admin)
    results["streaks"] = streaks_result

    lb_result = await compute_leaderboard(admin)
    results["leaderboard"] = lb_result

    rewards_result = await compute_rewards(admin)
    results["rewards"] = rewards_result

    achievements_result = await compute_achievements(admin)
    results["achievements"] = achievements_result

    return {"success": True, "engines": results}


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ADMIN DARK LAUNCH MONITOR — Aggregate stats + drill-down
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/monitor")
async def dark_launch_monitor(admin: dict = Depends(get_admin_user)):
    """Aggregate operational metrics for the Dark Launch dashboard."""

    # Leaderboard stats
    total_ranked = await db.phase_c_leaderboard.count_documents({})
    tier_dist = {}
    for tier in RANK_TIERS:
        tier_dist[tier["id"]] = await db.phase_c_leaderboard.count_documents({"rank_tier": tier["id"]})

    # Pending rewards
    total_pending_rewards = await db.phase_c_rewards.count_documents({"status": "pending"})
    total_reward_credits = 0
    async for r in db.phase_c_rewards.aggregate([
        {"$match": {"status": "pending"}},
        {"$group": {"_id": None, "total": {"$sum": "$credits"}}},
    ]):
        total_reward_credits = r.get("total", 0)

    # Active streaks
    total_active_streaks = await db.phase_c_streaks.count_documents({"streak_days": {"$gte": 1}})
    streak_tier_dist = {}
    for st in STREAK_TIERS:
        streak_tier_dist[st["id"]] = await db.phase_c_streaks.count_documents({"current_tier": st["id"]})

    # Achievements
    total_achievements = await db.phase_c_achievements.count_documents({})
    achievement_category_dist = {}
    for cat in ["rank", "streak", "reward"]:
        achievement_category_dist[cat] = await db.phase_c_achievements.count_documents({"category": cat})

    # Draft notifications
    total_draft_notifications = await db.phase_c_notifications.count_documents({"status": "draft"})

    # Freeze tokens stats
    total_freezes_available = 0
    async for f in db.phase_c_streaks.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$freeze_tokens_available"}}},
    ]):
        total_freezes_available = f.get("total", 0)

    # Phase C activation readiness
    status = await phase_c_status()

    # Simulated engagement score: how many users would qualify
    users_eligible_leaderboard = await db.phase_c_leaderboard.count_documents({"viral_score": {"$gte": 1}})
    users_eligible_rewards = await db.phase_c_rewards.distinct("user_id", {"status": "pending"})
    users_with_streak_badge = await db.phase_c_achievements.distinct("user_id", {"category": "streak"})
    users_with_rank_badge = await db.phase_c_achievements.distinct("user_id", {"category": "rank"})

    simulated_engagement = {
        "users_eligible_for_leaderboard_display": users_eligible_leaderboard,
        "users_eligible_for_reward_reveal": len(users_eligible_rewards),
        "users_with_streak_badges": len(users_with_streak_badge),
        "users_with_rank_badges": len(users_with_rank_badge),
    }

    # Last engine run time
    last_run = await db.analytics_events.find_one(
        {"event": "hidden_rank_progress"},
        {"_id": 0, "timestamp": 1},
        sort=[("timestamp", -1)],
    )

    return {
        "success": True,
        "activation": {
            "enable_phase_c": status["enable_phase_c"],
            "thresholds_passing": status["thresholds_passing"],
            "required_thresholds": status["required_thresholds"],
            "total_viral_events": status["total_viral_events"],
            "required_viral_events": status["required_viral_events"],
            "condition_a_met": status["condition_a_met"],
            "condition_b_met": status["condition_b_met"],
        },
        "leaderboard": {
            "total_ranked": total_ranked,
            "tier_distribution": tier_dist,
        },
        "rewards": {
            "total_pending": total_pending_rewards,
            "total_credits_pending": total_reward_credits,
        },
        "streaks": {
            "total_active": total_active_streaks,
            "tier_distribution": streak_tier_dist,
            "total_freeze_tokens": total_freezes_available,
        },
        "achievements": {
            "total": total_achievements,
            "category_distribution": achievement_category_dist,
        },
        "notifications": {
            "total_drafts": total_draft_notifications,
        },
        "simulated_engagement": simulated_engagement,
        "last_engine_run": last_run.get("timestamp").isoformat() if last_run and last_run.get("timestamp") else None,
    }


@router.get("/admin/drill-down")
async def dark_launch_drill_down(
    admin: dict = Depends(get_admin_user),
    category: str = Query("leaderboard", description="leaderboard|streaks|rewards|achievements"),
    limit: int = Query(25, le=50),
):
    """Drill-down into individual user data for the Dark Launch monitor."""

    results = []

    if category == "leaderboard":
        async for entry in db.phase_c_leaderboard.find(
            {}, {"_id": 0}
        ).sort("rank_position", 1).limit(limit):
            user = await db.users.find_one(
                {"id": entry["user_id"]}, {"_id": 0, "name": 1}
            )
            entry["name"] = user.get("name", "Creator") if user else "Creator"

            # Rank momentum from snapshots
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
            old_snap = await db.phase_c_rank_snapshots.find_one(
                {"user_id": entry["user_id"], "snapshot_date": {"$lte": week_ago}},
                {"_id": 0, "rank_position": 1},
                sort=[("snapshot_date", -1)],
            )
            if old_snap:
                entry["rank_change_7d"] = old_snap["rank_position"] - entry["rank_position"]
            else:
                entry["rank_change_7d"] = 0

            # Pending rewards count
            entry["pending_rewards"] = await db.phase_c_rewards.count_documents({
                "user_id": entry["user_id"], "status": "pending"
            })

            results.append(entry)

    elif category == "streaks":
        async for entry in db.phase_c_streaks.find(
            {"streak_days": {"$gte": 1}}, {"_id": 0}
        ).sort("streak_days", -1).limit(limit):
            user = await db.users.find_one(
                {"id": entry["user_id"]}, {"_id": 0, "name": 1}
            )
            entry["name"] = user.get("name", "Creator") if user else "Creator"
            results.append(entry)

    elif category == "rewards":
        # Group rewards by user
        pipeline = [
            {"$match": {"status": "pending"}},
            {"$group": {
                "_id": "$user_id",
                "total_credits": {"$sum": "$credits"},
                "reward_count": {"$sum": 1},
                "reward_types": {"$addToSet": "$reward_type"},
                "latest_earned": {"$max": "$earned_at"},
            }},
            {"$sort": {"total_credits": -1}},
            {"$limit": limit},
        ]
        async for doc in db.phase_c_rewards.aggregate(pipeline):
            user = await db.users.find_one(
                {"id": doc["_id"]}, {"_id": 0, "name": 1}
            )
            results.append({
                "user_id": doc["_id"],
                "name": user.get("name", "Creator") if user else "Creator",
                "total_credits_pending": doc["total_credits"],
                "reward_count": doc["reward_count"],
                "reward_types": doc["reward_types"],
                "latest_earned": doc["latest_earned"],
            })

    elif category == "achievements":
        pipeline = [
            {"$group": {
                "_id": "$user_id",
                "badges": {"$push": {"id": "$achievement_id", "label": "$label", "category": "$category"}},
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        async for doc in db.phase_c_achievements.aggregate(pipeline):
            user = await db.users.find_one(
                {"id": doc["_id"]}, {"_id": 0, "name": 1}
            )
            results.append({
                "user_id": doc["_id"],
                "name": user.get("name", "Creator") if user else "Creator",
                "badge_count": doc["count"],
                "badges": doc["badges"],
            })

    return {"success": True, "category": category, "results": results}
