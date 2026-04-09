"""
Retention Service — Notification triggers, throttling, mock email, daily challenges.
Provider-agnostic email abstraction. All emails are simulated (logged, not sent).
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# ─── THROTTLE RULES ─────────────────────────────────────────────────────────
# story_remixed: group within 30 min (aggregate N remixes into 1 notification)
# story_trending: max 1 every 12 hours
# daily_challenge_live: max 1 per day
THROTTLE_RULES = {
    "story_remixed": {"window_minutes": 30, "aggregate": True},
    "story_trending": {"window_minutes": 720, "aggregate": False},
    "daily_challenge_live": {"window_minutes": 1440, "aggregate": False},
}


class RetentionService:
    def __init__(self, db):
        self.db = db

    # ─── NOTIFICATIONS ────────────────────────────────────────────────────

    async def _should_throttle(self, user_id: str, ntype: str) -> bool:
        """Check if a notification of this type was already sent within the throttle window."""
        rule = THROTTLE_RULES.get(ntype)
        if not rule:
            return False
        window = datetime.now(timezone.utc) - timedelta(minutes=rule["window_minutes"])
        recent = await self.db.notifications.find_one({
            "user_id": user_id,
            "type": ntype,
            "created_at": {"$gte": window.isoformat()},
        })
        return recent is not None

    async def _aggregate_remix_notification(self, user_id: str, job_title: str, job_id: str):
        """Aggregate multiple remixes into a single notification within the throttle window."""
        window = datetime.now(timezone.utc) - timedelta(minutes=30)
        existing = await self.db.notifications.find_one({
            "user_id": user_id,
            "type": "story_remixed",
            "created_at": {"$gte": window.isoformat()},
        })
        if existing:
            count = existing.get("meta", {}).get("remix_count", 1) + 1
            await self.db.notifications.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "title": f"{count} people remixed your story",
                    "body": f'Your story "{job_title}" is being remixed!',
                    "meta.remix_count": count,
                    "read": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }}
            )
            return True
        return False

    async def notify_story_remixed(self, original_user_id: str, original_job_id: str, original_title: str, remixer_user_id: str):
        """Notify the original author that someone remixed their story. Aggregated within 30min."""
        if original_user_id == remixer_user_id:
            return  # Don't notify yourself
        # Try aggregate first
        aggregated = await self._aggregate_remix_notification(original_user_id, original_title, original_job_id)
        if aggregated:
            logger.info(f"[RETENTION] Aggregated remix notification for user {original_user_id[:8]}")
            return
        # Create new notification
        await self.db.notifications.insert_one({
            "user_id": original_user_id,
            "type": "story_remixed",
            "title": "Someone remixed your story!",
            "body": f'Your story "{original_title}" was remixed. See what they created!',
            "link": "/app/my-space",
            "meta": {"job_id": original_job_id, "remix_count": 1},
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        # Also create mock email event
        await self._log_email_event(original_user_id, "story_remixed", {
            "subject": f"Someone remixed your story \"{original_title}\"",
            "job_id": original_job_id,
            "original_title": original_title,
        })
        logger.info(f"[RETENTION] Remix notification sent to {original_user_id[:8]}")

    async def notify_story_trending(self, user_id: str, job_id: str, title: str, view_count: int):
        """Notify the author that their story is trending. Max 1 per 12h."""
        if await self._should_throttle(user_id, "story_trending"):
            return
        await self.db.notifications.insert_one({
            "user_id": user_id,
            "type": "story_trending",
            "title": "Your story is trending!",
            "body": f'"{title}" is getting attention — {view_count} views and counting!',
            "link": "/app/my-space",
            "meta": {"job_id": job_id, "view_count": view_count},
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await self._log_email_event(user_id, "story_trending", {
            "subject": f"Your story \"{title}\" is trending!",
            "job_id": job_id,
            "view_count": view_count,
        })
        logger.info(f"[RETENTION] Trending notification sent to {user_id[:8]}")

    async def notify_daily_challenge(self, user_id: str, challenge_title: str, challenge_id: str):
        """Notify a user about a new daily challenge. Max 1 per day."""
        if await self._should_throttle(user_id, "daily_challenge_live"):
            return
        await self.db.notifications.insert_one({
            "user_id": user_id,
            "type": "daily_challenge_live",
            "title": "New daily challenge is live!",
            "body": f"Today's challenge: {challenge_title}",
            "link": f"/app/story-video-studio?challenge={challenge_id}",
            "meta": {"challenge_id": challenge_id},
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await self._log_email_event(user_id, "daily_challenge_live", {
            "subject": f"Today's challenge: {challenge_title}",
            "challenge_id": challenge_id,
        })

    async def notify_ownership_milestone(self, user_id: str, job_id: str, title: str, remix_count: int):
        """Notify the author when their story hits a remix milestone."""
        milestones = [5, 10, 25, 50, 100]
        if remix_count not in milestones:
            return
        await self.db.notifications.insert_one({
            "user_id": user_id,
            "type": "ownership_milestone",
            "title": f"Your story hit {remix_count} remixes!",
            "body": f'"{title}" — people love your idea!',
            "link": "/app/my-space",
            "meta": {"job_id": job_id, "remix_count": remix_count},
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await self._log_email_event(user_id, "ownership_milestone", {
            "subject": f"Your story \"{title}\" hit {remix_count} remixes!",
            "job_id": job_id,
            "remix_count": remix_count,
        })

    # ─── MOCK EMAIL SERVICE ───────────────────────────────────────────────
    # Provider-agnostic: send_email(template_type, user_id, payload)
    # All emails are SIMULATED — logged to email_events collection

    async def send_email(self, template_type: str, user_id: str, payload: dict):
        """Provider-agnostic email abstraction. Currently simulated."""
        return await self._log_email_event(user_id, template_type, payload)

    async def _log_email_event(self, user_id: str, template_type: str, payload: dict):
        """Log a simulated email event to the email_events collection."""
        event = {
            "event_id": f"email_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "template": template_type,
            "subject": payload.get("subject", f"[{template_type}] Notification"),
            "payload": payload,
            "status": "simulated",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self.db.email_events.insert_one(event)
        except Exception as e:
            logger.warning(f"[EMAIL] Failed to log email event: {e}")
        return event

    # ─── DAILY CHALLENGES ─────────────────────────────────────────────────

    async def get_todays_challenge(self) -> Optional[Dict]:
        """Get today's active challenge."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        challenge = await self.db.daily_challenges.find_one(
            {"active_date": today}, {"_id": 0}
        )
        if challenge:
            # Add participation count
            count = await self.db.story_engine_jobs.count_documents(
                {"challenge_id": challenge.get("challenge_id")}
            )
            challenge["participants"] = count
        return challenge

    async def create_challenge(self, title: str, prompt_seed: str, active_date: str, category: str = "general") -> Dict:
        """Create a new daily challenge (admin only)."""
        challenge_id = f"ch_{uuid.uuid4().hex[:12]}"
        challenge = {
            "challenge_id": challenge_id,
            "title": title,
            "prompt_seed": prompt_seed,
            "active_date": active_date,
            "category": category,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.daily_challenges.insert_one(challenge)
        return {k: v for k, v in challenge.items() if k != "_id"}

    async def get_challenge_entries(self, challenge_id: str, limit: int = 20) -> list:
        """Get entries for a specific challenge."""
        entries = await self.db.story_engine_jobs.find(
            {"challenge_id": challenge_id, "state": {"$in": ["READY", "PARTIAL_READY"]}},
            {"_id": 0, "job_id": 1, "title": 1, "user_id": 1, "created_at": 1, "animation_style": 1}
        ).sort("created_at", -1).limit(limit).to_list(length=limit)
        return entries

    # ─── OWNERSHIP STATS ──────────────────────────────────────────────────

    async def get_job_remix_stats(self, job_ids: list) -> Dict[str, int]:
        """Get remix counts for a list of job IDs."""
        if not job_ids:
            return {}
        pipeline = [
            {"$match": {"reuse_info.parent_job_id": {"$in": job_ids}}},
            {"$group": {"_id": "$reuse_info.parent_job_id", "count": {"$sum": 1}}},
        ]
        result = {}
        async for doc in self.db.story_engine_jobs.aggregate(pipeline):
            result[doc["_id"]] = doc["count"]
        return result

    # ─── LEADERBOARD ──────────────────────────────────────────────────────

    async def get_top_stories_today(self, limit: int = 10) -> list:
        """Get top stories by view count, created in the last 7 days."""
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        stories = await self.db.story_engine_jobs.find(
            {
                "state": {"$in": ["READY", "PARTIAL_READY"]},
                "created_at": {"$gte": week_ago},
                "gallery_opt_in": True,
            },
            {"_id": 0, "job_id": 1, "title": 1, "animation_style": 1,
             "thumbnail_url": 1, "views": 1, "user_id": 1, "created_at": 1}
        ).sort("views", -1).limit(limit).to_list(length=limit)
        return stories


def get_retention_service(db):
    return RetentionService(db)
