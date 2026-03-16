"""
Admission Controller — Pre-job gate for pipeline protection + graceful degradation.

Checks before any job enters the pipeline:
  1. User concurrency (active jobs per user)
  2. System capacity (queue depth + active workers)
  3. Plan-based admission policy
  4. Graceful degradation under load

Load Levels:
  NORMAL   → Full quality for all tiers
  STRESSED → Reduce free-tier scenes (3→2), prioritize paid
  SEVERE   → Pause free generation, reduce paid scenes
  CRITICAL → Only premium/admin jobs accepted

Decision matrix:
  - Free user + at concurrency limit  → REJECT (clear message)
  - Free user + system overloaded     → REJECT (try again later)
  - Paid user + at concurrency limit   → REJECT (wait for jobs)
  - Paid user + system overloaded      → QUEUE with ETA
  - Premium user                       → ADMIT immediately when possible
"""

import logging
from datetime import datetime, timezone, timedelta
from shared import db

logger = logging.getLogger("admission_controller")

# ─── CONCURRENCY LIMITS PER PLAN ──────────────────────────────────────────

CONCURRENCY_LIMITS = {
    "free": 1,
    "starter": 3,
    "weekly": 3,
    "monthly": 3,
    "creator": 3,
    "quarterly": 3,
    "yearly": 3,
    "pro": 5,
    "premium": 5,
    "enterprise": 5,
    "admin": 10,
    "demo": 5,
}

# ─── SYSTEM CAPACITY THRESHOLDS ───────────────────────────────────────────

QUEUE_OVERLOAD_THRESHOLD = 20
ACTIVE_JOBS_STRESS_THRESHOLD = 10

# Graceful degradation thresholds
STRESSED_QUEUE_THRESHOLD = 10       # Queue >= 10 → STRESSED
SEVERE_QUEUE_THRESHOLD = 20         # Queue >= 20 → SEVERE
CRITICAL_QUEUE_THRESHOLD = 35       # Queue >= 35 → CRITICAL
STRESSED_ACTIVE_THRESHOLD = 6       # Active >= 6 → STRESSED
SEVERE_ACTIVE_THRESHOLD = 12        # Active >= 12 → SEVERE

PREMIUM_PLANS = frozenset(["pro", "premium", "enterprise", "admin", "demo"])

PAID_PLANS = frozenset([
    "weekly", "monthly", "quarterly", "yearly",
    "starter", "creator", "pro", "premium", "enterprise",
    "admin", "demo"
])

# ─── LOAD LEVELS ──────────────────────────────────────────────────────────

LOAD_NORMAL = "normal"
LOAD_STRESSED = "stressed"
LOAD_SEVERE = "severe"
LOAD_CRITICAL = "critical"

# Scene reduction under load — overrides PLAN_SCENE_LIMITS
DEGRADED_SCENE_LIMITS = {
    LOAD_NORMAL: {},  # no override
    LOAD_STRESSED: {"free": 2},  # free: 3→2
    LOAD_SEVERE: {"free": 0, "starter": 3, "weekly": 3, "monthly": 3, "creator": 3, "quarterly": 3, "yearly": 3},  # free paused, paid capped at 3
    LOAD_CRITICAL: {"free": 0, "starter": 0, "weekly": 0, "monthly": 0, "creator": 0, "quarterly": 0, "yearly": 0},  # only premium/admin
}


def _compute_load_level(queued: int, processing: int) -> str:
    """Determine current system load level from queue + active counts."""
    if queued >= CRITICAL_QUEUE_THRESHOLD:
        return LOAD_CRITICAL
    if queued >= SEVERE_QUEUE_THRESHOLD or processing >= SEVERE_ACTIVE_THRESHOLD:
        return LOAD_SEVERE
    if queued >= STRESSED_QUEUE_THRESHOLD or processing >= STRESSED_ACTIVE_THRESHOLD:
        return LOAD_STRESSED
    return LOAD_NORMAL


class AdmissionResult:
    """Result of an admission check."""
    __slots__ = ("admitted", "reason", "retry_after_sec", "queue_position", "eta_sec", "load_level", "degraded_max_scenes")

    def __init__(self, admitted: bool, reason: str = "", retry_after_sec: int = 0,
                 queue_position: int = 0, eta_sec: int = 0, load_level: str = LOAD_NORMAL,
                 degraded_max_scenes: int = 0):
        self.admitted = admitted
        self.reason = reason
        self.retry_after_sec = retry_after_sec
        self.queue_position = queue_position
        self.eta_sec = eta_sec
        self.load_level = load_level
        self.degraded_max_scenes = degraded_max_scenes

    def to_dict(self):
        d = {"admitted": self.admitted, "reason": self.reason, "load_level": self.load_level}
        if self.degraded_max_scenes:
            d["degraded_max_scenes"] = self.degraded_max_scenes
        if not self.admitted:
            if self.retry_after_sec:
                d["retry_after_sec"] = self.retry_after_sec
            if self.queue_position:
                d["queue_position"] = self.queue_position
            if self.eta_sec:
                d["eta_sec"] = self.eta_sec
        return d


async def check_admission(user_id: str, user_plan: str) -> AdmissionResult:
    """
    Pre-job admission check with graceful degradation.
    Must be called BEFORE credit reservation.
    """
    plan = str(user_plan).lower().strip()
    is_paid = plan in PAID_PLANS
    is_premium = plan in PREMIUM_PLANS

    # ── Check 1: User concurrency limit ───────────────────────────────────
    max_concurrent = CONCURRENCY_LIMITS.get(plan, CONCURRENCY_LIMITS["free"])

    active_jobs = await db.pipeline_jobs.count_documents({
        "user_id": user_id,
        "status": {"$in": ["QUEUED", "PROCESSING"]},
    })

    if active_jobs >= max_concurrent:
        if is_paid:
            return AdmissionResult(
                admitted=False,
                reason=f"You have {active_jobs} active job(s). Your plan allows {max_concurrent} concurrent jobs. Please wait for a job to finish.",
                retry_after_sec=30,
            )
        else:
            return AdmissionResult(
                admitted=False,
                reason=f"You already have an active video being generated. Free accounts can run {max_concurrent} job at a time. Please wait for it to finish or upgrade your plan.",
                retry_after_sec=60,
            )

    # ── Check 2: System load level + graceful degradation ─────────────────
    queued_jobs = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
    processing_jobs = await db.pipeline_jobs.count_documents({"status": "PROCESSING"})
    load_level = _compute_load_level(queued_jobs, processing_jobs)

    # Get plan-specific degraded scene limit (0 = paused/blocked)
    degradation = DEGRADED_SCENE_LIMITS.get(load_level, {})
    degraded_scenes = degradation.get(plan)  # None = no override

    # ── CRITICAL: Only premium/admin ──────────────────────────────────────
    if load_level == LOAD_CRITICAL and not is_premium:
        logger.warning(f"[ADMISSION] CRITICAL LOAD — rejecting {plan} user {user_id[:8]} (queued={queued_jobs}, active={processing_jobs})")
        return AdmissionResult(
            admitted=False,
            reason="System is at maximum capacity. Only premium users can generate right now. Please try again in a few minutes or upgrade your plan.",
            retry_after_sec=180,
            load_level=load_level,
        )

    # ── SEVERE: Pause free, degrade paid ──────────────────────────────────
    if load_level == LOAD_SEVERE:
        if not is_paid:
            logger.info(f"[ADMISSION] SEVERE LOAD — pausing free user {user_id[:8]} (queued={queued_jobs}, active={processing_jobs})")
            return AdmissionResult(
                admitted=False,
                reason="Our servers are under heavy load. Free generation is temporarily paused. Please try again in a few minutes or upgrade to skip the queue.",
                retry_after_sec=120,
                load_level=load_level,
            )
        if is_premium:
            logger.info(f"[ADMISSION] SEVERE LOAD — premium user {user_id[:8]} admitted (queued={queued_jobs})")
            return AdmissionResult(admitted=True, load_level=load_level)

        # Paid non-premium: admit with reduced scenes
        est_wait = queued_jobs * 70
        logger.info(f"[ADMISSION] SEVERE LOAD — paid user {user_id[:8]} admitted with degradation (queued={queued_jobs})")
        return AdmissionResult(
            admitted=True,
            reason=f"System is busy. Your video will use fewer scenes for faster delivery. Estimated wait: ~{est_wait // 60} minutes.",
            queue_position=queued_jobs + 1,
            eta_sec=est_wait,
            load_level=load_level,
            degraded_max_scenes=degraded_scenes or 0,
        )

    # ── STRESSED: Reduce free, prioritize paid ────────────────────────────
    if load_level == LOAD_STRESSED:
        if not is_paid:
            # Admit but with reduced scene count
            logger.info(f"[ADMISSION] STRESSED — free user {user_id[:8]} admitted with degraded scenes (queued={queued_jobs})")
            return AdmissionResult(
                admitted=True,
                reason="Our servers are busy. Your video will be slightly shorter for faster delivery.",
                load_level=load_level,
                degraded_max_scenes=degraded_scenes or 0,
            )
        # Paid/premium: normal admission
        logger.info(f"[ADMISSION] STRESSED — paid user {user_id[:8]} admitted normally (queued={queued_jobs})")
        return AdmissionResult(admitted=True, load_level=load_level)

    # ── NORMAL: Full admission ────────────────────────────────────────────
    logger.info(f"[ADMISSION] User {user_id[:8]} admitted (plan={plan}, active={active_jobs}/{max_concurrent}, queue={queued_jobs}, load={load_level})")
    return AdmissionResult(admitted=True, load_level=load_level)


async def get_system_status() -> dict:
    """Return current system capacity metrics with load level."""
    queued = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
    processing = await db.pipeline_jobs.count_documents({"status": "PROCESSING"})
    failed_recent = await db.pipeline_jobs.count_documents({
        "status": "FAILED",
        "completed_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=1)},
    })

    load_level = _compute_load_level(queued, processing)

    return {
        "queued_jobs": queued,
        "processing_jobs": processing,
        "failed_last_hour": failed_recent,
        "load_level": load_level,
        "system_overloaded": queued >= QUEUE_OVERLOAD_THRESHOLD,
        "system_stressed": processing >= ACTIVE_JOBS_STRESS_THRESHOLD,
        "degradation_active": load_level != LOAD_NORMAL,
        "capacity": {
            "queue_threshold": QUEUE_OVERLOAD_THRESHOLD,
            "active_threshold": ACTIVE_JOBS_STRESS_THRESHOLD,
            "stressed_at": STRESSED_QUEUE_THRESHOLD,
            "severe_at": SEVERE_QUEUE_THRESHOLD,
            "critical_at": CRITICAL_QUEUE_THRESHOLD,
        },
    }
