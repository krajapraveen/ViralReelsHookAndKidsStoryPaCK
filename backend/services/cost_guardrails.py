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
    __slots__ = (
        "allowed", "reason", "enforced_max_pages", "enforced_max_retries",
        # P0 2026-05-19 — structured envelope fields so the founder-spec
        # DAILY_LIMIT_REACHED HTTPException can render reset_at / counts /
        # plan_type without a second DB round-trip.
        "limit_type", "current_count", "max_allowed", "reset_at", "plan_type",
    )

    def __init__(
        self, allowed=True, reason="", enforced_max_pages=0, enforced_max_retries=3,
        limit_type=None, current_count=None, max_allowed=None, reset_at=None,
        plan_type=None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.enforced_max_pages = enforced_max_pages
        self.enforced_max_retries = enforced_max_retries
        self.limit_type = limit_type
        self.current_count = current_count
        self.max_allowed = max_allowed
        self.reset_at = reset_at
        self.plan_type = plan_type


async def check_guardrails(
    user_id: str,
    user_plan: str,
    requested_pages: int,
    feature: str = "comic_storybook",
    user: dict | None = None,
) -> GuardrailResult:
    """
    Hard enforcement. Returns allowed=False with clear reason if limits exceeded.

    P0 2026-05-19 — bypass for unlimited users + don't burn quota on
    failed/cancelled jobs.
    """
    plan = str(user_plan).lower().strip()
    job_limit = JOB_LIMITS.get(plan, JOB_LIMITS["free"])
    daily_limit = DAILY_LIMITS.get(plan, DAILY_LIMITS["free"])

    # ── Layer 1: Per-job limit ────────────────────────────────────────
    enforced_pages = min(requested_pages, job_limit["max_pages"])
    max_retries = job_limit["max_retries"]

    # P0 2026-05-19 — Unlimited user bypass. The previous limiter only
    # consulted `user_plan`; an admin/owner/dev/qa/test user whose plan
    # field is still "free" would hit the free cap (2 jobs/day) even
    # though `is_unlimited_user()` flags them as unlimited everywhere
    # else in the system. Production screenshot showed exactly this:
    # 159 credits, 60 cr cost, but DAILY_LIMIT_REACHED.
    from services.entitlement import is_unlimited_user
    if user is not None and is_unlimited_user(user):
        logger.info(
            "[GUARDRAIL] unlimited bypass user_id=%s plan=%s pages=%s",
            user_id[:8], plan, enforced_pages,
        )
        return GuardrailResult(
            allowed=True,
            enforced_max_pages=enforced_pages,
            enforced_max_retries=max_retries,
        )

    # ── Layer 2: Per-user daily limit ─────────────────────────────────
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    # P0 2026-05-19 — Exclude FAILED / CANCELLED / EXPIRED jobs from
    # the daily count. A user whose job crashed mid-pipeline shouldn't
    # lose their daily quota slot — credits get refunded so the daily
    # cap should match.
    countable_filter = {
        "userId": user_id,
        "createdAt": {"$gte": today_start.isoformat()},
        "status": {"$nin": ["FAILED", "CANCELLED", "EXPIRED", "REFUNDED"]},
    }
    daily_jobs = await db.comic_storybook_v2_jobs.count_documents(countable_filter)

    if daily_jobs >= daily_limit["max_jobs"]:
        logger.warning(
            "[GUARDRAIL] User %s hit daily job limit (%s/%s)",
            user_id[:8], daily_jobs, daily_limit["max_jobs"],
        )
        return GuardrailResult(
            allowed=False,
            reason=(
                f"Daily limit reached ({daily_jobs}/{daily_limit['max_jobs']} "
                f"comics today). Resets at midnight UTC."
            ),
            limit_type="per_user_daily_jobs",
            current_count=daily_jobs,
            max_allowed=daily_limit["max_jobs"],
            reset_at=tomorrow_start.isoformat(),
            plan_type=plan,
        )

    # Check daily cost — same filter (don't count failed/cancelled cost).
    cost_pipeline = [
        {"$match": countable_filter},
        {"$group": {"_id": None, "total": {"$sum": "$cost"}}},
    ]
    cost_result = await db.comic_storybook_v2_jobs.aggregate(cost_pipeline).to_list(1)
    daily_cost = cost_result[0]["total"] if cost_result else 0

    if daily_cost >= daily_limit["max_cost"]:
        logger.warning(
            "[GUARDRAIL] User %s hit daily cost limit (%s/%s)",
            user_id[:8], daily_cost, daily_limit["max_cost"],
        )
        return GuardrailResult(
            allowed=False,
            reason=(
                f"Daily credit limit reached ({daily_cost}/{daily_limit['max_cost']}). "
                f"Resets at midnight UTC."
            ),
            limit_type="per_user_daily_cost",
            current_count=daily_cost,
            max_allowed=daily_limit["max_cost"],
            reset_at=tomorrow_start.isoformat(),
            plan_type=plan,
        )

    # ── Layer 3: System-wide kill switch ──────────────────────────────
    sys_pipeline = [
        {"$match": {
            "createdAt": {"$gte": today_start.isoformat()},
            "status": {"$nin": ["FAILED", "CANCELLED", "EXPIRED", "REFUNDED"]},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$cost"}}},
    ]
    sys_result = await db.comic_storybook_v2_jobs.aggregate(sys_pipeline).to_list(1)
    system_daily_cost = sys_result[0]["total"] if sys_result else 0

    if system_daily_cost >= SYSTEM_DAILY_COST_CEILING:
        if plan not in ("pro", "premium", "admin", "demo"):
            logger.critical(
                "[GUARDRAIL] SYSTEM KILL SWITCH — blocking %s user (system cost: %s)",
                plan, system_daily_cost,
            )
            return GuardrailResult(
                allowed=False,
                reason="Platform at maximum capacity today. Premium users only. Please try again tomorrow or upgrade.",
                limit_type="system_capacity",
                current_count=system_daily_cost,
                max_allowed=SYSTEM_DAILY_COST_CEILING,
                reset_at=tomorrow_start.isoformat(),
                plan_type=plan,
            )
        # Premium users: reduce pages
        enforced_pages = min(enforced_pages, 10)
        max_retries = 1
    elif system_daily_cost >= SYSTEM_SEVERE_THRESHOLD:
        if plan == "free":
            logger.warning(
                "[GUARDRAIL] System cost high — blocking free user (cost: %s)",
                system_daily_cost,
            )
            return GuardrailResult(
                allowed=False,
                reason="High demand — free generation paused. Upgrade to continue.",
                limit_type="system_degraded",
                current_count=system_daily_cost,
                max_allowed=SYSTEM_SEVERE_THRESHOLD,
                reset_at=tomorrow_start.isoformat(),
                plan_type=plan,
            )
        # Paid: reduce pages
        enforced_pages = min(enforced_pages, 15)

    logger.info(
        "[GUARDRAIL] User %s allowed: pages=%s retries=%s daily_jobs=%s",
        user_id[:8], enforced_pages, max_retries, daily_jobs,
    )
    return GuardrailResult(
        allowed=True,
        enforced_max_pages=enforced_pages,
        enforced_max_retries=max_retries,
    )


async def get_user_quota_status(user_id: str, user_plan: str, user: dict | None = None) -> dict:
    """P0 2026-05-19 — pre-flight quota lookup for the frontend so the
    UI can render remaining-jobs + reset-at BEFORE the user clicks
    Generate. Mirrors the same exclusion rules as check_guardrails."""
    from services.entitlement import is_unlimited_user
    plan = str(user_plan).lower().strip()
    daily_limit = DAILY_LIMITS.get(plan, DAILY_LIMITS["free"])
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    if user is not None and is_unlimited_user(user):
        return {
            "is_unlimited": True,
            "plan_type": plan,
            "jobs_today": 0,
            "jobs_max": None,
            "jobs_remaining": None,
            "cost_today": 0,
            "cost_max": None,
            "reset_at": tomorrow_start.isoformat(),
        }

    countable_filter = {
        "userId": user_id,
        "createdAt": {"$gte": today_start.isoformat()},
        "status": {"$nin": ["FAILED", "CANCELLED", "EXPIRED", "REFUNDED"]},
    }
    jobs_today = await db.comic_storybook_v2_jobs.count_documents(countable_filter)
    cost_pipeline = [
        {"$match": countable_filter},
        {"$group": {"_id": None, "total": {"$sum": "$cost"}}},
    ]
    cost_result = await db.comic_storybook_v2_jobs.aggregate(cost_pipeline).to_list(1)
    cost_today = cost_result[0]["total"] if cost_result else 0
    return {
        "is_unlimited": False,
        "plan_type": plan,
        "jobs_today": jobs_today,
        "jobs_max": daily_limit["max_jobs"],
        "jobs_remaining": max(0, daily_limit["max_jobs"] - jobs_today),
        "cost_today": cost_today,
        "cost_max": daily_limit["max_cost"],
        "reset_at": tomorrow_start.isoformat(),
    }


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
