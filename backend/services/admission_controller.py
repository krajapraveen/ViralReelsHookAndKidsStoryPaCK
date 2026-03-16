"""
Admission Controller — Pre-job gate for pipeline protection.

Checks before any job enters the pipeline:
  1. User concurrency (active jobs per user)
  2. System capacity (queue depth + active workers)
  3. Plan-based admission policy

Decision matrix:
  - Free user + at concurrency limit  → REJECT (clear message)
  - Free user + system overloaded     → REJECT (try again later)
  - Paid user + at concurrency limit   → REJECT (wait for jobs)
  - Paid user + system overloaded      → QUEUE with ETA
  - Premium user                       → ADMIT immediately when possible
"""

import logging
import time
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

# Max queued jobs before system is considered "overloaded"
QUEUE_OVERLOAD_THRESHOLD = 20

# Max active processing jobs before system is stressed
ACTIVE_JOBS_STRESS_THRESHOLD = 10

# Premium plans that get priority admission even under load
PREMIUM_PLANS = frozenset(["pro", "premium", "enterprise", "admin", "demo"])

PAID_PLANS = frozenset([
    "weekly", "monthly", "quarterly", "yearly",
    "starter", "creator", "pro", "premium", "enterprise",
    "admin", "demo"
])


class AdmissionResult:
    """Result of an admission check."""
    __slots__ = ("admitted", "reason", "retry_after_sec", "queue_position", "eta_sec")

    def __init__(self, admitted: bool, reason: str = "", retry_after_sec: int = 0,
                 queue_position: int = 0, eta_sec: int = 0):
        self.admitted = admitted
        self.reason = reason
        self.retry_after_sec = retry_after_sec
        self.queue_position = queue_position
        self.eta_sec = eta_sec

    def to_dict(self):
        d = {"admitted": self.admitted, "reason": self.reason}
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
    Pre-job admission check. Must be called BEFORE credit reservation.

    Returns AdmissionResult with admitted=True/False and reason.
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

    # ── Check 2: System capacity ──────────────────────────────────────────
    queued_jobs = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
    processing_jobs = await db.pipeline_jobs.count_documents({"status": "PROCESSING"})

    system_overloaded = queued_jobs >= QUEUE_OVERLOAD_THRESHOLD
    system_stressed = processing_jobs >= ACTIVE_JOBS_STRESS_THRESHOLD

    if system_overloaded or system_stressed:
        # Premium users: always admit
        if is_premium:
            logger.info(f"[ADMISSION] Premium user {user_id[:8]} admitted despite load (queued={queued_jobs}, active={processing_jobs})")
            return AdmissionResult(admitted=True)

        # Paid users: queue with ETA
        if is_paid:
            est_wait = queued_jobs * 70  # ~70s per job estimate
            logger.info(f"[ADMISSION] Paid user {user_id[:8]} queued with ETA (queued={queued_jobs}, active={processing_jobs})")
            return AdmissionResult(
                admitted=True,  # Admitted but with queue warning
                reason=f"System is busy. Your job is queued. Estimated wait: ~{est_wait // 60} minutes.",
                queue_position=queued_jobs + 1,
                eta_sec=est_wait,
            )

        # Free users: REJECT with clear message
        retry_min = max(2, queued_jobs // 5)
        logger.info(f"[ADMISSION] Free user {user_id[:8]} REJECTED — system overloaded (queued={queued_jobs}, active={processing_jobs})")
        return AdmissionResult(
            admitted=False,
            reason=f"Our servers are busy right now. Please try again in {retry_min} minutes, or upgrade to skip the queue.",
            retry_after_sec=retry_min * 60,
        )

    # ── Admitted ──────────────────────────────────────────────────────────
    logger.info(f"[ADMISSION] User {user_id[:8]} admitted (plan={plan}, active={active_jobs}/{max_concurrent}, queue={queued_jobs})")
    return AdmissionResult(admitted=True)


async def get_system_status() -> dict:
    """Return current system capacity metrics for monitoring."""
    queued = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
    processing = await db.pipeline_jobs.count_documents({"status": "PROCESSING"})
    failed_recent = await db.pipeline_jobs.count_documents({
        "status": "FAILED",
        "completed_at": {"$gte": __import__("datetime").datetime.now(__import__("datetime").timezone.utc) - __import__("datetime").timedelta(hours=1)},
    })

    return {
        "queued_jobs": queued,
        "processing_jobs": processing,
        "failed_last_hour": failed_recent,
        "system_overloaded": queued >= QUEUE_OVERLOAD_THRESHOLD,
        "system_stressed": processing >= ACTIVE_JOBS_STRESS_THRESHOLD,
        "capacity": {
            "queue_threshold": QUEUE_OVERLOAD_THRESHOLD,
            "active_threshold": ACTIVE_JOBS_STRESS_THRESHOLD,
        },
    }
