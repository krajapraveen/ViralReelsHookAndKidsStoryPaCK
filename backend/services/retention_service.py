"""
Retention Service — Notification triggers, throttling, real email via Resend, daily challenges.
Provider-agnostic email abstraction with per-user caps and unsubscribe metadata.
"""
import os
import uuid
import asyncio
import logging
import resend
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ─── RESEND CONFIG ───────────────────────────────────────────────────────────
resend.api_key = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("FROM_EMAIL") or os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

# ─── THROTTLE RULES ─────────────────────────────────────────────────────────
THROTTLE_RULES = {
    "story_remixed": {"window_minutes": 30, "aggregate": True},
    "story_trending": {"window_minutes": 720, "aggregate": False},
    "daily_challenge_live": {"window_minutes": 1440, "aggregate": False},
}

# ─── PER-USER EMAIL CAPS ────────────────────────────────────────────────────
# max emails per user per day by type
EMAIL_CAPS = {
    "story_remixed": {"max_per_day": 2, "cooldown_hours": 6},
    "story_trending": {"max_per_day": 1, "cooldown_hours": 12},
    "daily_challenge_live": {"max_per_day": 1, "cooldown_hours": 24},
    "ownership_milestone": {"max_per_day": 1, "cooldown_hours": 24},
}

# ─── EMAIL TEMPLATES ─────────────────────────────────────────────────────────

def _render_email_html(template_type: str, payload: dict) -> str:
    """Render clean, simple email HTML with CTA button."""
    title = payload.get("subject", "Notification")
    body = payload.get("body", "")
    cta_text = payload.get("cta_text", "Open App")
    cta_url = payload.get("cta_url", "https://trust-engine-5.preview.emergentagent.com/app")

    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px; background: #0d0d18; color: #e4e4e7;">
      <div style="margin-bottom: 24px;">
        <span style="font-size: 12px; font-weight: 700; color: #a78bfa; letter-spacing: 1px; text-transform: uppercase;">Visionary Suite</span>
      </div>
      <h2 style="font-size: 20px; font-weight: 700; color: #ffffff; margin: 0 0 12px 0; line-height: 1.3;">{title}</h2>
      <p style="font-size: 14px; color: #a1a1aa; line-height: 1.6; margin: 0 0 24px 0;">{body}</p>
      <a href="{cta_url}" style="display: inline-block; padding: 12px 28px; background: linear-gradient(135deg, #7c3aed, #6366f1); color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 10px;">{cta_text}</a>
      <div style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #27272a;">
        <p style="font-size: 11px; color: #52525b; margin: 0;">You're receiving this because you created content on Visionary Suite.</p>
      </div>
    </div>
    """

TEMPLATE_BUILDERS = {
    "story_remixed": lambda p: {
        "subject": p.get("subject", "Someone remixed your story!"),
        "body": f'Your story "{p.get("original_title", "Untitled")}" was remixed! See what they created and remix it back.',
        "cta_text": "See Remixes",
        "cta_url": "https://trust-engine-5.preview.emergentagent.com/app/my-space",
    },
    "story_trending": lambda p: {
        "subject": p.get("subject", "Your story is trending!"),
        "body": f'"{p.get("original_title", p.get("title", "Your story"))}" is getting attention — {p.get("view_count", "many")} views and counting!',
        "cta_text": "View Your Story",
        "cta_url": "https://trust-engine-5.preview.emergentagent.com/app/my-space",
    },
    "daily_challenge_live": lambda p: {
        "subject": p.get("subject", "New daily challenge is live!"),
        "body": f'Today\'s challenge: "{p.get("challenge_title", "Create something amazing")}". Join now and see what others are creating!',
        "cta_text": "Join Challenge",
        "cta_url": f'https://trust-engine-5.preview.emergentagent.com/app/story-video-studio?challenge={p.get("challenge_id", "")}',
    },
    "ownership_milestone": lambda p: {
        "subject": p.get("subject", "Your story hit a milestone!"),
        "body": f'"{p.get("original_title", p.get("title", "Your story"))}" just hit {p.get("remix_count", "?")} remixes. People love your idea!',
        "cta_text": "See Your Impact",
        "cta_url": "https://trust-engine-5.preview.emergentagent.com/app/my-space",
    },
}

# ─── CREATOR DIGEST EMAIL TEMPLATE ──────────────────────────────────────────

def _render_digest_html(digest: dict) -> str:
    """Render Creator Digest email — 20-second read max."""
    top = digest.get("top_story", {})
    momentum = digest.get("momentum_text", "")
    percentile = digest.get("percentile_text", "")
    rising = digest.get("rising_fast", False)
    cta = digest.get("cta", {})

    stats_html = ""
    views = digest.get("total_views", 0)
    remixes = digest.get("new_remixes", 0)
    if views > 0:
        stats_html += f'<div style="display:inline-block;margin-right:24px;"><span style="font-size:28px;font-weight:800;color:#ffffff;">{views}</span><br/><span style="font-size:11px;color:#71717a;">views this week</span></div>'
    if remixes > 0:
        stats_html += f'<div style="display:inline-block;margin-right:24px;"><span style="font-size:28px;font-weight:800;color:#a78bfa;">{remixes}</span><br/><span style="font-size:11px;color:#71717a;">new remixes</span></div>'

    top_story_html = ""
    if top.get("title"):
        top_story_html = f"""
        <div style="margin:20px 0;padding:16px;border-radius:12px;border:1px solid #27272a;background:#18181b;">
          <p style="font-size:10px;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:1px;margin:0 0 6px 0;">Most Celebrated Story</p>
          <p style="font-size:16px;font-weight:700;color:#ffffff;margin:0 0 4px 0;">{top["title"]}</p>
          <p style="font-size:12px;color:#71717a;margin:0;">{top.get("views", 0)} views &bull; {top.get("remix_count", 0)} remixes</p>
        </div>
        """

    badge_html = ""
    if rising:
        badge_html = '<div style="display:inline-block;padding:4px 12px;border-radius:20px;background:#7c3aed20;border:1px solid #7c3aed40;font-size:11px;font-weight:700;color:#a78bfa;margin-bottom:16px;">Rising Fast This Week</div><br/>'

    momentum_html = ""
    if momentum:
        momentum_html = f'<p style="font-size:13px;color:#d4d4d8;margin:0 0 4px 0;">{momentum}</p>'

    percentile_html = ""
    if percentile:
        percentile_html = f'<p style="font-size:12px;color:#71717a;margin:0 0 16px 0;">{percentile}</p>'

    cta_text = cta.get("text", "See your dashboard")
    cta_url = cta.get("url", "https://trust-engine-5.preview.emergentagent.com/app/my-space")

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#0d0d18;color:#e4e4e7;">
      <div style="margin-bottom:20px;">
        <span style="font-size:12px;font-weight:700;color:#a78bfa;letter-spacing:1px;text-transform:uppercase;">Visionary Suite</span>
        <span style="font-size:11px;color:#52525b;float:right;">Weekly Digest</span>
      </div>
      <h2 style="font-size:20px;font-weight:800;color:#ffffff;margin:0 0 6px 0;line-height:1.3;">Your story world is growing</h2>
      <p style="font-size:13px;color:#a1a1aa;margin:0 0 20px 0;">Here's what happened this week.</p>
      {badge_html}
      <div style="margin-bottom:20px;">{stats_html}</div>
      {momentum_html}
      {percentile_html}
      {top_story_html}
      <a href="{cta_url}" style="display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#7c3aed,#6366f1);color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;border-radius:10px;margin-top:8px;">{cta_text}</a>
      <div style="margin-top:32px;padding-top:16px;border-top:1px solid #27272a;">
        <p style="font-size:11px;color:#52525b;margin:0;">Sent weekly to active creators on Visionary Suite.</p>
      </div>
    </div>
    """


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

    # ─── EMAIL SERVICE (Resend) ─────────────────────────────────────────────
    # Provider-agnostic: send_email(template_type, user_id, payload)
    # Real delivery via Resend. Logged to email_events. Per-user caps enforced.

    async def _check_email_cap(self, user_id: str, template_type: str) -> bool:
        """Check if user has exceeded email cap for this type today."""
        cap = EMAIL_CAPS.get(template_type, {"max_per_day": 2, "cooldown_hours": 24})
        day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        count = await self.db.email_events.count_documents({
            "user_id": user_id,
            "template": template_type,
            "status": {"$in": ["sent", "simulated"]},
            "created_at": {"$gte": day_start.isoformat()},
        })
        if count >= cap["max_per_day"]:
            return False
        # Also check cooldown
        cooldown_start = datetime.now(timezone.utc) - timedelta(hours=cap["cooldown_hours"])
        recent = await self.db.email_events.find_one({
            "user_id": user_id,
            "template": template_type,
            "status": {"$in": ["sent", "simulated"]},
            "created_at": {"$gte": cooldown_start.isoformat()},
        })
        return recent is None

    async def send_email(self, template_type: str, user_id: str, payload: dict):
        """Send email via Resend with per-user caps and logging."""
        # Check caps
        if not await self._check_email_cap(user_id, template_type):
            logger.info(f"[EMAIL] Cap reached for {user_id[:8]} / {template_type}, skipping")
            return None

        # Get user email
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
        if not user or not user.get("email"):
            # Fallback: try user_id field, then ObjectId
            user = await self.db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1})
        if not user or not user.get("email"):
            from bson import ObjectId
            try:
                user = await self.db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 0, "email": 1})
            except Exception:
                pass
        if not user or not user.get("email"):
            logger.warning(f"[EMAIL] No email found for user {user_id[:8]}")
            return None

        recipient = user["email"]

        # Build template
        builder = TEMPLATE_BUILDERS.get(template_type)
        if builder:
            tpl = builder(payload)
        else:
            tpl = {"subject": payload.get("subject", "Notification"), "body": "", "cta_text": "Open App", "cta_url": ""}

        html = _render_email_html(template_type, tpl)

        # Log event first
        event = {
            "event_id": f"email_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "recipient": recipient,
            "template": template_type,
            "subject": tpl["subject"],
            "payload": payload,
            "status": "pending",
            "email_type": template_type,
            "user_preferences_key": f"{template_type}_notifications",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.db.email_events.insert_one(event)
        except Exception:
            pass

        # Send via Resend (non-blocking)
        if resend.api_key:
            try:
                params = {
                    "from": SENDER_EMAIL,
                    "to": [recipient],
                    "subject": tpl["subject"],
                    "html": html,
                }
                result = await asyncio.to_thread(resend.Emails.send, params)
                email_id = result.get("id") if isinstance(result, dict) else str(result)
                # Update event status
                await self.db.email_events.update_one(
                    {"event_id": event["event_id"]},
                    {"$set": {"status": "sent", "resend_id": email_id}}
                )
                logger.info(f"[EMAIL] Sent {template_type} to {recipient} (id: {email_id})")
                return event
            except Exception as e:
                logger.warning(f"[EMAIL] Resend failed for {recipient}: {e}")
                await self.db.email_events.update_one(
                    {"event_id": event["event_id"]},
                    {"$set": {"status": "failed", "error": str(e)}}
                )
                return event
        else:
            # No API key — simulate
            await self.db.email_events.update_one(
                {"event_id": event["event_id"]},
                {"$set": {"status": "simulated"}}
            )
            logger.info(f"[EMAIL] Simulated {template_type} to {recipient} (no API key)")
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
        """Get top stories by weighted score (remix_count * 0.6 + views * 0.4), last 7 days."""
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        pipeline = [
            {"$match": {
                "state": {"$in": ["READY", "PARTIAL_READY"]},
                "created_at": {"$gte": week_ago},
                "gallery_opt_in": True,
            }},
            {"$lookup": {
                "from": "story_engine_jobs",
                "localField": "job_id",
                "foreignField": "reuse_info.parent_job_id",
                "as": "remixes",
            }},
            {"$addFields": {
                "remix_count": {"$size": "$remixes"},
                "view_count": {"$ifNull": ["$views", 0]},
                "score": {"$add": [
                    {"$multiply": [{"$size": "$remixes"}, 0.6]},
                    {"$multiply": [{"$ifNull": ["$views", 0]}, 0.4]},
                ]},
            }},
            {"$sort": {"score": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0, "job_id": 1, "title": 1, "animation_style": 1,
                "thumbnail_url": 1, "views": "$view_count", "remix_count": 1,
                "score": 1, "user_id": 1, "created_at": 1,
            }},
        ]
        stories = []
        async for doc in self.db.story_engine_jobs.aggregate(pipeline):
            stories.append(doc)
        return stories

    # ─── CREATOR DIGEST ───────────────────────────────────────────────────

    async def compute_digest(self, user_id: str) -> Optional[Dict]:
        """Compute weekly digest stats for a single user. Returns None if no activity."""
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        two_weeks_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

        # Get user's completed jobs
        user_jobs = await self.db.story_engine_jobs.find(
            {"user_id": user_id, "state": {"$in": ["READY", "PARTIAL_READY"]}},
            {"_id": 0, "job_id": 1, "title": 1, "views": 1, "created_at": 1, "animation_style": 1}
        ).to_list(length=500)

        if not user_jobs:
            return None

        job_ids = [j["job_id"] for j in user_jobs]

        # This week's remix count
        this_week_remixes = await self.db.story_engine_jobs.count_documents({
            "reuse_info.parent_job_id": {"$in": job_ids},
            "created_at": {"$gte": week_ago},
        })

        # Last week's remix count (for momentum)
        last_week_remixes = await self.db.story_engine_jobs.count_documents({
            "reuse_info.parent_job_id": {"$in": job_ids},
            "created_at": {"$gte": two_weeks_ago, "$lt": week_ago},
        })

        # Total views this week (approximate — sum views field)
        total_views = sum(j.get("views", 0) for j in user_jobs)

        # Skip if zero meaningful activity
        if this_week_remixes == 0 and total_views == 0:
            return None

        # Find top story (most views + remixes)
        remix_stats = await self.get_job_remix_stats(job_ids)
        top_story = None
        top_score = -1
        for j in user_jobs:
            rc = remix_stats.get(j["job_id"], 0)
            sc = (j.get("views", 0) * 0.4) + (rc * 0.6)
            if sc > top_score:
                top_score = sc
                top_story = {"title": j["title"], "views": j.get("views", 0), "remix_count": rc, "job_id": j["job_id"]}

        # Momentum signal
        momentum_text = ""
        if this_week_remixes > last_week_remixes and last_week_remixes > 0:
            growth = this_week_remixes - last_week_remixes
            momentum_text = f"Your remixes grew by {growth} this week"
        elif this_week_remixes > 0:
            momentum_text = f"You gained {this_week_remixes} new remix{'es' if this_week_remixes > 1 else ''} this week"

        # Percentile (compare against all creators)
        total_creators = await self.db.story_engine_jobs.distinct("user_id", {"state": {"$in": ["READY", "PARTIAL_READY"]}})
        total_creator_count = len(total_creators)
        percentile_text = ""
        if total_creator_count > 5:
            # Count how many creators have fewer total remixes
            all_user_remixes = {}
            async for doc in self.db.story_engine_jobs.aggregate([
                {"$match": {"reuse_info.parent_job_id": {"$exists": True}, "created_at": {"$gte": week_ago}}},
                {"$lookup": {"from": "story_engine_jobs", "localField": "reuse_info.parent_job_id", "foreignField": "job_id", "as": "parent"}},
                {"$unwind": {"path": "$parent", "preserveNullAndEmptyArrays": True}},
                {"$group": {"_id": "$parent.user_id", "count": {"$sum": 1}}},
            ]):
                if doc["_id"]:
                    all_user_remixes[doc["_id"]] = doc["count"]
            my_remixes = all_user_remixes.get(user_id, 0)
            below_count = sum(1 for v in all_user_remixes.values() if v < my_remixes)
            if len(all_user_remixes) > 0 and my_remixes > 0:
                pct = int((below_count / len(all_user_remixes)) * 100)
                if pct >= 50:
                    percentile_text = f"You outperformed {pct}% of creators this week"

        # Rising Fast badge
        rising_fast = this_week_remixes >= 5 and this_week_remixes > last_week_remixes * 1.5

        # Personalized CTA
        cta = {"text": "See your dashboard", "url": "https://trust-engine-5.preview.emergentagent.com/app/my-space"}
        if this_week_remixes >= 3:
            cta = {"text": "See who remixed your story", "url": "https://trust-engine-5.preview.emergentagent.com/app/my-space"}
        elif total_views >= 50:
            cta = {"text": "See why your story is trending", "url": "https://trust-engine-5.preview.emergentagent.com/app/my-space"}

        return {
            "user_id": user_id,
            "total_views": total_views,
            "new_remixes": this_week_remixes,
            "last_week_remixes": last_week_remixes,
            "top_story": top_story,
            "momentum_text": momentum_text,
            "percentile_text": percentile_text,
            "rising_fast": rising_fast,
            "cta": cta,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def send_digest(self, user_id: str, digest: dict) -> Optional[Dict]:
        """Send the Creator Digest email. Max 1/week."""
        # Check weekly cap (1 digest per 7 days)
        week_ago = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
        recent = await self.db.email_events.find_one({
            "user_id": user_id,
            "template": "creator_digest",
            "status": {"$in": ["sent", "simulated"]},
            "created_at": {"$gte": week_ago},
        })
        if recent:
            logger.info(f"[DIGEST] Already sent this week to {user_id[:8]}, skipping")
            return None

        # Get user email
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
        if not user or not user.get("email"):
            user = await self.db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1})
        if not user or not user.get("email"):
            from bson import ObjectId
            try:
                user = await self.db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 0, "email": 1})
            except Exception:
                pass
        if not user or not user.get("email"):
            return None

        recipient = user["email"]
        subject = "Your story world is growing this week"
        if digest.get("rising_fast"):
            subject = "You're rising fast this week"
        elif digest.get("new_remixes", 0) >= 5:
            subject = f"{digest['new_remixes']} new remixes on your stories this week"

        html = _render_digest_html(digest)

        event = {
            "event_id": f"email_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "recipient": recipient,
            "template": "creator_digest",
            "subject": subject,
            "payload": digest,
            "status": "pending",
            "email_type": "creator_digest",
            "user_preferences_key": "weekly_digest",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.db.email_events.insert_one(event)
        except Exception:
            pass

        if resend.api_key:
            try:
                params = {"from": SENDER_EMAIL, "to": [recipient], "subject": subject, "html": html}
                result = await asyncio.to_thread(resend.Emails.send, params)
                email_id = result.get("id") if isinstance(result, dict) else str(result)
                await self.db.email_events.update_one(
                    {"event_id": event["event_id"]},
                    {"$set": {"status": "sent", "resend_id": email_id}}
                )
                logger.info(f"[DIGEST] Sent to {recipient}")
                return event
            except Exception as e:
                logger.warning(f"[DIGEST] Resend failed for {recipient}: {e}")
                await self.db.email_events.update_one(
                    {"event_id": event["event_id"]},
                    {"$set": {"status": "failed", "error": str(e)}}
                )
                return event
        else:
            await self.db.email_events.update_one(
                {"event_id": event["event_id"]},
                {"$set": {"status": "simulated"}}
            )
            return event

    async def run_weekly_digest(self) -> Dict:
        """Run digest for all active creators. Returns summary of sent/skipped counts."""
        # Find all creators with completed jobs in last 30 days
        month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        active_users = await self.db.story_engine_jobs.distinct(
            "user_id",
            {"state": {"$in": ["READY", "PARTIAL_READY"]}, "created_at": {"$gte": month_ago}}
        )

        sent = 0
        skipped = 0
        for uid in active_users:
            if not uid:
                continue
            try:
                digest = await self.compute_digest(uid)
                if digest:
                    result = await self.send_digest(uid, digest)
                    if result:
                        sent += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.warning(f"[DIGEST] Error for {uid[:8]}: {e}")
                skipped += 1

        logger.info(f"[DIGEST] Weekly run complete: {sent} sent, {skipped} skipped")
        return {"sent": sent, "skipped": skipped, "total_creators": len(active_users)}


def get_retention_service(db):
    return RetentionService(db)
