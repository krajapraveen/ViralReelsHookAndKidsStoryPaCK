"""
Cost Guardrails — Hard enforcement of per-job, per-user, and system-wide limits.

3 layers:
  1. Per-job:   max_pages, max_panels
  2. Per-user:  max_jobs_per_day, max_cost_per_day
  3. System:    daily_cost_ceiling → degrade free, restrict paid, protect premium

HARD STOPS, not warnings.
"""
import logging
from datetime import datetime, timezone, timedelta
from shared import db

logger = logging.getLogger("cost_guardrails")

# ── PER-JOB LIMITS ────────────────────────────────────────────────────────

JOB_LIMITS = {
    "free":    {"max_pages": 10, "max_panels_per_page": 1, "max_retries": 1},
    "starter": {"max_pages": 20, "max_panels_per_page": 1, "max_retries": 2},
    "weekly":  {"max_pages": 20, "max_panels_per_page": 1, "max_retries": 2},
    "monthly": {"max_pages": 20, "max_panels_per_page": 1, "max_retries": 2},
    "creator": {"max_pages": 20, "max_panels_per_page": 1, "max_retries": 2},
    "pro":     {"max_pages": 30, "max_panels_per_page": 2, "max_retries": 3},
    "premium": {"max_pages": 30, "max_panels_per_page": 2, "max_retries": 3},
    "admin":   {"max_pages": 30, "max_panels_per_page": 2, "max_retries": 3},
    "demo":    {"max_pages": 30, "max_panels_per_page": 2, "max_retries": 3},
}

# ── PER-USER DAILY LIMITS ─────────────────────────────────────────────────

DAILY_LIMITS = {
    "free":    {"max_jobs": 2,  "max_cost": 50},
    "starter": {"max_jobs": 10, "max_cost": 200},
    "weekly":  {"max_jobs": 10, "max_cost": 200},
    "monthly": {"max_jobs": 10, "max_cost": 200},
    "creator": {"max_jobs": 15, "max_cost": 300},
    "pro":     {"max_jobs": 50, "max_cost": 1000},
    "premium": {"max_jobs": 50, "max_cost": 1000},
    "admin":   {"max_jobs": 999, "max_cost": 99999},
    "demo":    {"max_jobs": 50, "max_cost": 1000},
}

# ── SYSTEM-WIDE KILL SWITCH ───────────────────────────────────────────────

SYSTEM_DAILY_COST_CEILING = 5000  # credits/day across all users
SYSTEM_SEVERE_THRESHOLD = 3500    # trigger degradation


class GuardrailResult:
    __slots__ = ("allowed", "reason", "enforced_max_pages", "enforced_max_retries")

    def __init__(self, allowed=True, reason="", enforced_max_pages=0, enforced_max_retries=3):
        self.allowed = allowed
        self.reason = reason
        self.enforced_max_pages = enforced_max_pages
        self.enforced_max_retries = enforced_max_retries


async def check_guardrails(user_id: str, user_plan: str, requested_pages: int, feature: str = "comic_storybook") -> GuardrailResult:
    """
    Hard enforcement. Returns allowed=False with clear reason if limits exceeded.
    """
    plan = str(user_plan).lower().strip()
    job_limit = JOB_LIMITS.get(plan, JOB_LIMITS["free"])
    daily_limit = DAILY_LIMITS.get(plan, DAILY_LIMITS["free"])

    # ── Layer 1: Per-job limit ────────────────────────────────────────
    enforced_pages = min(requested_pages, job_limit["max_pages"])
    max_retries = job_limit["max_retries"]

    # ── Layer 2: Per-user daily limit ─────────────────────────────────
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    daily_jobs = await db.comic_storybook_v2_jobs.count_documents({
        "userId": user_id,
        "createdAt": {"$gte": today_start.isoformat()},
    })

    if daily_jobs >= daily_limit["max_jobs"]:
        logger.warning(f"[GUARDRAIL] User {user_id[:8]} hit daily job limit ({daily_jobs}/{daily_limit['max_jobs']})")
        return GuardrailResult(
            allowed=False,
            reason=f"Daily limit reached ({daily_jobs}/{daily_limit['max_jobs']} jobs today). Resets at midnight UTC. Upgrade for higher limits.",
        )

    # Check daily cost
    cost_pipeline = [
        {"$match": {"userId": user_id, "createdAt": {"$gte": today_start.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$cost"}}},
    ]
    cost_result = await db.comic_storybook_v2_jobs.aggregate(cost_pipeline).to_list(1)
    daily_cost = cost_result[0]["total"] if cost_result else 0

    if daily_cost >= daily_limit["max_cost"]:
        logger.warning(f"[GUARDRAIL] User {user_id[:8]} hit daily cost limit ({daily_cost}/{daily_limit['max_cost']})")
        return GuardrailResult(
            allowed=False,
            reason=f"Daily credit limit reached ({daily_cost}/{daily_limit['max_cost']}). Resets at midnight UTC.",
        )

    # ── Layer 3: System-wide kill switch ──────────────────────────────
    sys_pipeline = [
        {"$match": {"createdAt": {"$gte": today_start.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$cost"}}},
    ]
    sys_result = await db.comic_storybook_v2_jobs.aggregate(sys_pipeline).to_list(1)
    system_daily_cost = sys_result[0]["total"] if sys_result else 0

    if system_daily_cost >= SYSTEM_DAILY_COST_CEILING:
        if plan not in ("pro", "premium", "admin", "demo"):
            logger.critical(f"[GUARDRAIL] SYSTEM KILL SWITCH — blocking {plan} user (system cost: {system_daily_cost})")
            return GuardrailResult(
                allowed=False,
                reason="Platform at maximum capacity today. Premium users only. Please try again tomorrow or upgrade.",
            )
        # Premium users: reduce pages
        enforced_pages = min(enforced_pages, 10)
        max_retries = 1
    elif system_daily_cost >= SYSTEM_SEVERE_THRESHOLD:
        if plan == "free":
            logger.warning(f"[GUARDRAIL] System cost high — blocking free user (cost: {system_daily_cost})")
            return GuardrailResult(
                allowed=False,
                reason="High demand — free generation paused. Upgrade to continue.",
            )
        # Paid: reduce pages
        enforced_pages = min(enforced_pages, 15)

    logger.info(f"[GUARDRAIL] User {user_id[:8]} allowed: pages={enforced_pages}, retries={max_retries}, daily_jobs={daily_jobs}")
    return GuardrailResult(
        allowed=True,
        enforced_max_pages=enforced_pages,
        enforced_max_retries=max_retries,
    )


async def get_guardrail_status() -> dict:
    """Admin view: current guardrail state."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    sys_pipeline = [
        {"$match": {"createdAt": {"$gte": today_start.isoformat()}}},
        {"$group": {"_id": None, "total_cost": {"$sum": "$cost"}, "total_jobs": {"$sum": 1}}},
    ]
    result = await db.comic_storybook_v2_jobs.aggregate(sys_pipeline).to_list(1)
    stats = result[0] if result else {"total_cost": 0, "total_jobs": 0}

    return {
        "system_daily_cost": stats.get("total_cost", 0),
        "system_daily_jobs": stats.get("total_jobs", 0),
        "ceiling": SYSTEM_DAILY_COST_CEILING,
        "severe_threshold": SYSTEM_SEVERE_THRESHOLD,
        "kill_switch_active": stats.get("total_cost", 0) >= SYSTEM_DAILY_COST_CEILING,
        "degradation_active": stats.get("total_cost", 0) >= SYSTEM_SEVERE_THRESHOLD,
    }
