"""
Phase 4 — Retention Engine
Handles: Streaks, Nudges, Episode Milestones, Content Seeding, Return Experience
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from shared import db
from routes.auth import get_current_user
from shared import get_admin_user

logger = logging.getLogger("creatorstudio.retention")
router = APIRouter(prefix="/retention", tags=["retention"])


def _now():
    return datetime.now(timezone.utc)


def _today_str():
    return _now().strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════════════
# STREAKS — Track daily engagement, award milestone credits
# ═══════════════════════════════════════════════════════════════════════════════

STREAK_MILESTONES = {
    3: 10,   # Day 3 → +10 credits
    7: 25,   # Day 7 → +25 credits
}


@router.get("/streak")
async def get_streak(user: dict = Depends(get_current_user)):
    """Get current user's streak info."""
    streak = await db.streaks.find_one(
        {"user_id": user["id"]}, {"_id": 0}
    )
    if not streak:
        return {
            "success": True,
            "current_streak": 0,
            "longest_streak": 0,
            "last_active_date": None,
            "milestones_claimed": [],
            "next_milestone": 3,
            "next_reward": 10,
        }

    current = streak.get("current_streak", 0)
    milestones_claimed = streak.get("milestones_claimed", [])

    # Find next unclaimed milestone
    next_ms = None
    next_reward = None
    for day, credits in sorted(STREAK_MILESTONES.items()):
        if day not in milestones_claimed:
            next_ms = day
            next_reward = credits
            break

    return {
        "success": True,
        "current_streak": current,
        "longest_streak": streak.get("longest_streak", 0),
        "last_active_date": streak.get("last_active_date"),
        "milestones_claimed": milestones_claimed,
        "next_milestone": next_ms,
        "next_reward": next_reward,
    }


async def record_daily_activity(user_id: str):
    """Called when user generates/continues a story. Updates streak."""
    today = _today_str()
    yesterday = (_now() - timedelta(days=1)).strftime("%Y-%m-%d")

    streak = await db.streaks.find_one(
        {"user_id": user_id}, {"_id": 0}
    )

    if not streak:
        # First activity ever
        await db.streaks.insert_one({
            "user_id": user_id,
            "current_streak": 1,
            "longest_streak": 1,
            "last_active_date": today,
            "milestones_claimed": [],
            "created_at": _now().isoformat(),
        })
        return {"streak": 1, "milestone_reached": None}

    last_active = streak.get("last_active_date", "")

    if last_active == today:
        # Already counted today
        return {"streak": streak.get("current_streak", 1), "milestone_reached": None}

    if last_active == yesterday:
        # Consecutive day
        new_streak = streak.get("current_streak", 0) + 1
    else:
        # Streak broken — reset to 1
        new_streak = 1

    longest = max(new_streak, streak.get("longest_streak", 0))

    await db.streaks.update_one(
        {"user_id": user_id},
        {"$set": {
            "current_streak": new_streak,
            "longest_streak": longest,
            "last_active_date": today,
        }}
    )

    # Check milestone rewards
    milestone_reached = None
    milestones_claimed = streak.get("milestones_claimed", [])
    for day, credits in sorted(STREAK_MILESTONES.items()):
        if new_streak >= day and day not in milestones_claimed:
            # Award credits
            await db.users.update_one(
                {"id": user_id},
                {"$inc": {"credits": credits}}
            )
            await db.credit_transactions.insert_one({
                "user_id": user_id,
                "amount": credits,
                "type": "streak_reward",
                "description": f"{day}-day streak reward",
                "created_at": _now().isoformat(),
            })
            await db.streaks.update_one(
                {"user_id": user_id},
                {"$push": {"milestones_claimed": day}}
            )
            milestone_reached = {"day": day, "credits": credits}
            logger.info(f"[STREAK] User {user_id[:8]} hit {day}-day streak → +{credits} credits")

    return {"streak": new_streak, "milestone_reached": milestone_reached}


# ═══════════════════════════════════════════════════════════════════════════════
# EPISODE MILESTONE REWARDS — Every 5 episodes = +5 credits
# ═══════════════════════════════════════════════════════════════════════════════

async def check_episode_milestone(user_id: str, series_id: str):
    """Called after a new episode is generated. Awards credits every 5 episodes."""
    episode_count = await db.pipeline_jobs.count_documents({
        "user_id": user_id,
        "series_id": series_id,
        "status": "COMPLETED",
    })

    if episode_count > 0 and episode_count % 5 == 0:
        reward = 5
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": reward}}
        )
        await db.credit_transactions.insert_one({
            "user_id": user_id,
            "amount": reward,
            "type": "episode_milestone",
            "description": f"Episode milestone: {episode_count} episodes in series",
            "meta": {"series_id": series_id, "episode_count": episode_count},
            "created_at": _now().isoformat(),
        })
        logger.info(f"[MILESTONE] User {user_id[:8]} hit {episode_count} episodes in series {series_id[:8]} → +{reward} credits")
        return {"rewarded": True, "credits": reward, "episodes": episode_count}

    return {"rewarded": False, "episodes": episode_count}


# ═══════════════════════════════════════════════════════════════════════════════
# RETURN EXPERIENCE — "Continue your story" data for dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/return-banner")
async def get_return_banner(user: dict = Depends(get_current_user)):
    """Get the most relevant 'continue your story' data for the return experience."""
    user_id = user["id"]

    # Find user's most recent completed story
    latest_story = await db.pipeline_jobs.find_one(
        {
            "user_id": user_id,
            "status": "COMPLETED",
            "thumbnail_url": {"$exists": True, "$nin": [None, ""]},
        },
        {
            "_id": 0, "job_id": 1, "title": 1, "thumbnail_url": 1,
            "slug": 1, "story_text": 1, "animation_style": 1,
            "completed_at": 1, "series_id": 1,
        },
        sort=[("completed_at", -1)],
    )

    if not latest_story:
        return {"success": True, "has_story": False}

    # Extract cliffhanger from story text
    story_text = latest_story.get("story_text", "")
    cliffhanger = ""
    if story_text:
        sentences = [s.strip() for s in story_text.replace("...", ".").split(".") if s.strip()]
        if len(sentences) >= 2:
            cliffhanger = sentences[-2] + "..."
        elif sentences:
            cliffhanger = sentences[-1] + "..."

    # Get character name if available
    char_name = None
    chars = await db.pipeline_jobs.find_one(
        {"job_id": latest_story["job_id"]},
        {"_id": 0, "extracted_characters": 1}
    )
    if chars and chars.get("extracted_characters"):
        char_name = chars["extracted_characters"][0].get("name")

    # Check series context
    series_info = None
    if latest_story.get("series_id"):
        series = await db.story_series.find_one(
            {"series_id": latest_story["series_id"]},
            {"_id": 0, "title": 1, "series_id": 1}
        )
        ep_count = await db.pipeline_jobs.count_documents({
            "series_id": latest_story["series_id"],
            "status": "COMPLETED",
        })
        if series:
            series_info = {
                "series_id": series["series_id"],
                "title": series["title"],
                "episode_number": ep_count + 1,
            }

    latest_story.pop("story_text", None)

    return {
        "success": True,
        "has_story": True,
        "story": latest_story,
        "cliffhanger": cliffhanger,
        "character_name": char_name,
        "series_info": series_info,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NUDGE SYSTEM — "Continue your story" notifications for inactive users
# ═══════════════════════════════════════════════════════════════════════════════

async def run_nudge_check():
    """Background task: find users with stories who haven't been active in 6+ hours.
    Create in-app notifications with character name + cliffhanger + deep link."""
    six_hours_ago = (_now() - timedelta(hours=6)).isoformat()
    twenty_four_hours_ago = (_now() - timedelta(hours=24)).isoformat()

    # Find users who generated recently (within 24h) but not in last 6h
    recent_jobs = await db.pipeline_jobs.find(
        {
            "status": "COMPLETED",
            "completed_at": {"$gte": twenty_four_hours_ago, "$lte": six_hours_ago},
            "thumbnail_url": {"$exists": True, "$nin": [None, ""]},
        },
        {"_id": 0, "user_id": 1, "job_id": 1, "title": 1, "slug": 1, "story_text": 1, "extracted_characters": 1}
    ).sort("completed_at", -1).to_list(200)

    # Group by user, take most recent per user
    user_jobs = {}
    for job in recent_jobs:
        uid = job.get("user_id")
        if uid and uid not in user_jobs:
            user_jobs[uid] = job

    nudge_count = 0
    for user_id, job in user_jobs.items():
        # Check if we already nudged this user in the last 6 hours
        existing_nudge = await db.notifications.find_one({
            "user_id": user_id,
            "type": "nudge",
            "created_at": {"$gte": six_hours_ago},
        }, {"_id": 1})
        if existing_nudge:
            continue

        # Build notification with character name + cliffhanger
        title_text = job.get("title", "Your Story")
        char_name = None
        chars = job.get("extracted_characters", [])
        if chars:
            char_name = chars[0].get("name")

        story_text = job.get("story_text", "")
        cliffhanger = "What happens next might surprise you..."
        if story_text:
            sentences = [s.strip() for s in story_text.replace("...", ".").split(".") if s.strip()]
            if len(sentences) >= 2:
                cliffhanger = sentences[-1] + "..."

        # Build notification
        if char_name:
            notif_title = f"{char_name}'s story isn't finished..."
        else:
            notif_title = f'"{title_text}" isn\'t finished...'

        slug = job.get("slug")
        link = f"/v/{slug}" if slug else f"/app/story-video-studio?job={job['job_id']}"

        await db.notifications.insert_one({
            "user_id": user_id,
            "type": "nudge",
            "title": notif_title,
            "body": cliffhanger,
            "link": link,
            "meta": {"job_id": job["job_id"], "character_name": char_name},
            "read": False,
            "created_at": _now().isoformat(),
        })
        nudge_count += 1

    if nudge_count > 0:
        logger.info(f"[NUDGE] Sent {nudge_count} 'continue your story' nudges")

    return nudge_count


async def run_email_nudges():
    """Generate email nudge content for users with inactive stories.
    Formats emails with character name + cliffhanger + deep link.
    NOTE: Requires email service integration (SendGrid/Resend) to actually send.
    Currently logs prepared emails for when service is connected."""
    six_hours_ago = (_now() - timedelta(hours=6)).isoformat()
    twenty_four_hours_ago = (_now() - timedelta(hours=24)).isoformat()

    recent_jobs = await db.pipeline_jobs.find(
        {
            "status": "COMPLETED",
            "completed_at": {"$gte": twenty_four_hours_ago, "$lte": six_hours_ago},
            "thumbnail_url": {"$exists": True, "$nin": [None, ""]},
        },
        {"_id": 0, "user_id": 1, "job_id": 1, "title": 1, "slug": 1, "story_text": 1, "extracted_characters": 1}
    ).sort("completed_at", -1).to_list(100)

    user_jobs = {}
    for job in recent_jobs:
        uid = job.get("user_id")
        if uid and uid not in user_jobs:
            user_jobs[uid] = job

    emails_queued = 0
    for user_id, job in user_jobs.items():
        # Check if already sent email nudge in last 24 hours
        existing = await db.email_nudges.find_one({
            "user_id": user_id,
            "created_at": {"$gte": twenty_four_hours_ago},
        }, {"_id": 1})
        if existing:
            continue

        user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "name": 1})
        if not user or not user.get("email"):
            continue

        chars = job.get("extracted_characters", [])
        char_name = chars[0].get("name") if chars else None
        story_text = job.get("story_text", "")
        cliffhanger = "What happens next will shock you"
        if story_text:
            sentences = [s.strip() for s in story_text.replace("...", ".").split(".") if s.strip()]
            if sentences:
                cliffhanger = sentences[-1]

        slug = job.get("slug")
        link = f"/v/{slug}" if slug else f"/app/story-video-studio?job={job['job_id']}"

        subject = f"{char_name}'s story isn't finished..." if char_name else f'"{job.get("title", "Your story")}" isn\'t finished...'
        body_text = f'"{cliffhanger}"\n\nContinue now: {link}'

        # Store email nudge record
        await db.email_nudges.insert_one({
            "user_id": user_id,
            "email": user["email"],
            "subject": subject,
            "body": body_text,
            "cliffhanger": cliffhanger,
            "character_name": char_name,
            "link": link,
            "job_id": job["job_id"],
            "sent": False,
            "created_at": _now().isoformat(),
        })
        emails_queued += 1

        # TODO: When email service is integrated, send here:
        # await send_email(to=user["email"], subject=subject, body=body_text)

    if emails_queued > 0:
        logger.info(f"[EMAIL NUDGE] Queued {emails_queued} email nudges (pending email service integration)")

    return emails_queued


@router.get("/admin/email-nudges")
async def get_email_nudge_queue(admin: dict = Depends(get_admin_user)):
    """Admin view of pending email nudges."""
    pending = await db.email_nudges.find(
        {"sent": False},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)

    total_pending = await db.email_nudges.count_documents({"sent": False})
    total_sent = await db.email_nudges.count_documents({"sent": True})

    return {
        "success": True,
        "pending_count": total_pending,
        "sent_count": total_sent,
        "recent_pending": pending,
        "note": "Email sending requires service integration (SendGrid/Resend). Nudges are queued and ready.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT SEEDING — Admin tool to batch-generate showcase content
# ═══════════════════════════════════════════════════════════════════════════════

class SeedRequest(BaseModel):
    count: int = 10
    themes: Optional[list] = None


@router.post("/admin/seed-content")
async def seed_content(req: SeedRequest, admin: dict = Depends(get_admin_user)):
    """Admin endpoint to queue batch story generation for seeding trending/gallery feeds."""
    import uuid

    themes = req.themes or [
        # Emotional hooks
        "A mother receives a letter from her child 30 years in the future, and the last line makes her cry",
        "An old man sits on a park bench every day waiting for someone who never comes, until today",
        # Mystery / suspense
        "She opened the door to her childhood home, but everything inside belonged to someone else",
        "The detective finds a photo of a crime scene — taken three days before the crime happened",
        # Kids / family
        "A brave little fox named Finn discovers a magical door under a waterfall that leads to a sky kingdom",
        "A dragon who is afraid of fire tries to hide it from the other dragons at school",
        # Viral hooks
        "A street musician plays one note that makes everyone in the city stop walking — then they all start crying",
        "She found her own diary in a thrift shop, but the handwriting wasn't hers",
        # Fantasy
        "A lighthouse keeper discovers the light attracts not ships, but creatures from another dimension",
        "Twin sisters discover they share the same dream every night — until one sister disappears from it",
    ]

    jobs_created = []
    count = min(req.count, 50)  # Cap at 50

    for i in range(count):
        theme = themes[i % len(themes)]
        job_id = str(uuid.uuid4())

        job = {
            "job_id": job_id,
            "user_id": admin["id"],
            "title": theme.split(" ")[-3:] if len(theme.split()) > 3 else theme,
            "story_text": theme,
            "animation_style": ["cartoon_2d", "anime", "watercolor", "realistic"][i % 4],
            "pipeline_type": "story_video",
            "status": "QUEUED",
            "is_seed_content": True,
            "public": True,
            "created_at": _now().isoformat(),
        }

        await db.pipeline_jobs.insert_one({k: v for k, v in job.items() if k != "_id"})
        jobs_created.append(job_id)

    logger.info(f"[SEED] Admin {admin['id'][:8]} queued {len(jobs_created)} seed stories")

    return {
        "success": True,
        "message": f"Queued {len(jobs_created)} stories for generation",
        "job_ids": jobs_created,
        "note": "Stories will be generated by pipeline workers and appear in gallery/trending once complete.",
    }


@router.get("/admin/seed-status")
async def get_seed_status(admin: dict = Depends(get_admin_user)):
    """Check status of seeded content."""
    total = await db.pipeline_jobs.count_documents({"is_seed_content": True})
    completed = await db.pipeline_jobs.count_documents({"is_seed_content": True, "status": "COMPLETED"})
    failed = await db.pipeline_jobs.count_documents({"is_seed_content": True, "status": "FAILED"})
    queued = await db.pipeline_jobs.count_documents({"is_seed_content": True, "status": {"$in": ["QUEUED", "PROCESSING"]}})

    return {
        "success": True,
        "total": total,
        "completed": completed,
        "failed": failed,
        "queued": queued,
    }
