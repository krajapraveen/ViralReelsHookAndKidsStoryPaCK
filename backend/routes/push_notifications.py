"""
Push Notification Engine — Loss-aversion competitive triggers via Web Push.

ONLY sends high-intent triggers:
  - rank_drop: "You just lost #1"
  - war_overtake: "You dropped in today's war"
  - near_win: "You're one move from #1"
  - war_winner: "You WON today's war"

Rate limits: max 3/day, 2h cooldown between pushes.
Deep-links to Story Battle / War screen.
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user

logger = logging.getLogger("push_notifications")
router = APIRouter(prefix="/push", tags=["Push Notifications"])

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "").replace("\\n", "\n")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS = {"sub": os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:admin@creatorstudio.ai")}

MAX_PUSHES_PER_DAY = 3
COOLDOWN_HOURS = 2

ALLOWED_TRIGGERS = {"rank_drop", "war_overtake", "near_win", "war_winner"}


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict  # { p256dh, auth }


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


@router.get("/vapid-key")
async def get_vapid_key():
    """Return the VAPID public key for the frontend to subscribe."""
    return {"success": True, "vapid_public_key": VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe_push(request: PushSubscriptionRequest, current_user: dict = Depends(get_current_user)):
    """Save a push subscription for the current user."""
    user_id = current_user.get("id") or str(current_user.get("_id"))

    await db.push_subscriptions.update_one(
        {"user_id": user_id, "endpoint": request.endpoint},
        {"$set": {
            "user_id": user_id,
            "endpoint": request.endpoint,
            "keys": request.keys,
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
            "active": True,
        }},
        upsert=True,
    )

    return {"success": True}


@router.post("/unsubscribe")
async def unsubscribe_push(request: PushUnsubscribeRequest, current_user: dict = Depends(get_current_user)):
    """Remove a push subscription."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    await db.push_subscriptions.update_one(
        {"user_id": user_id, "endpoint": request.endpoint},
        {"$set": {"active": False}}
    )
    return {"success": True}


async def send_push_to_user(user_id: str, trigger: str, title: str, body: str, deep_link: str, data: dict = None):
    """
    Send a push notification to a user. Enforces rate limits and cooldown.
    Only sends for ALLOWED_TRIGGERS.
    """
    if trigger not in ALLOWED_TRIGGERS:
        return False

    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        return False

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Rate limit: max 3/day
    daily_count = await db.push_log.count_documents({
        "user_id": user_id,
        "sent_at": {"$gte": today_start},
    })
    if daily_count >= MAX_PUSHES_PER_DAY:
        return False

    # Cooldown: 2h between pushes
    cooldown_cutoff = (now - timedelta(hours=COOLDOWN_HOURS)).isoformat()
    recent = await db.push_log.find_one({
        "user_id": user_id,
        "sent_at": {"$gte": cooldown_cutoff},
    })
    if recent:
        return False

    # Get active subscriptions
    subs = await db.push_subscriptions.find(
        {"user_id": user_id, "active": True},
        {"_id": 0}
    ).to_list(5)

    if not subs:
        return False

    payload = json.dumps({
        "title": title,
        "body": body,
        "data": {"deep_link": deep_link, "trigger": trigger, **(data or {})},
        "tag": trigger,
    })

    sent = 0
    try:
        from pywebpush import webpush, WebPushException
        for sub in subs:
            try:
                webpush(
                    subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS,
                )
                sent += 1
            except WebPushException as e:
                if "410" in str(e) or "404" in str(e):
                    await db.push_subscriptions.update_one(
                        {"endpoint": sub["endpoint"]}, {"$set": {"active": False}}
                    )
            except Exception:
                pass
    except ImportError:
        return False

    if sent > 0:
        await db.push_log.insert_one({
            "user_id": user_id, "trigger": trigger, "title": title, "body": body,
            "deep_link": deep_link, "sent_at": now.isoformat(), "subscriptions_sent": sent,
        })

    return sent > 0


async def trigger_rank_drop_push(user_id: str, story_title: str, battle_parent_id: str, new_rank: int):
    rank_text = f"#{new_rank}" if new_rank > 0 else "your spot"
    await send_push_to_user(user_id, "rank_drop",
        f"You dropped to {rank_text}",
        f"Someone just beat your entry on \"{story_title}\". Come back now and take your spot.",
        f"/app/story-battle/{battle_parent_id}")


async def trigger_war_overtake_push(user_id: str, new_rank: int, time_left_str: str):
    await send_push_to_user(user_id, "war_overtake",
        f"You dropped to #{new_rank} in today's Story War",
        f"Someone just overtook you.{' ' + time_left_str if time_left_str else ''} Fight back now.",
        "/app/war")


async def trigger_near_win_push(user_id: str, story_title: str, battle_parent_id: str, gap: int):
    await send_push_to_user(user_id, "near_win",
        "You're one move away from #1",
        f"Only {gap} continue{'s' if gap != 1 else ''} behind on \"{story_title}\". Don't lose this moment.",
        f"/app/story-battle/{battle_parent_id}")


async def trigger_war_winner_push(user_id: str, war_title: str):
    await send_push_to_user(user_id, "war_winner",
        "You WON today's Story War!",
        f"Your version of \"{war_title}\" claimed #1. You'll be featured on the homepage.",
        "/app/war")


async def create_push_indexes():
    try:
        await db.push_subscriptions.create_index([("user_id", 1), ("active", 1)])
        await db.push_subscriptions.create_index([("user_id", 1), ("endpoint", 1)], unique=True)
        await db.push_log.create_index([("user_id", 1), ("sent_at", -1)])
        await db.battle_rank_snapshot.create_index([("parent_job_id", 1)], unique=True)
    except Exception as e:
        logger.warning(f"[PUSH] Index creation failed: {e}")
