"""
Comic Storybook canonical transition log + stuck-job janitor.

Phase 3c-minimal (transition log):
  Every terminal status change on a `comic_storybook_v2_jobs` row gets
  audited into `comic_storybook_v2_transitions` with the source, the
  previous status, the new status, an optional reason, and the
  request_id of the request that caused the transition (or
  "janitor:stuck-job" when the janitor fired). This gives ops a clean
  forensic trail for the next split-brain.

Phase 4a (stuck-job janitor):
  The Comic Storybook idempotency lock-trap fix recovered orphan
  PENDING idempotency rows, but a job whose worker died AFTER the job
  row was inserted (mid-`stage_image_generation`, OOM, supervisor
  restart) can still leave the job document stuck in PROCESSING /
  STORY_OUTLINE / etc. forever. The janitor finds rows with
  status NOT IN {COMPLETED, FAILED, CANCELLED, REFUNDED} whose
  `updated_at` is older than STUCK_THRESHOLD_MINUTES and transitions
  them to FAILED_STUCK with refund.

The janitor is opt-in via env var `COMIC_STORYBOOK_JANITOR_ENABLED=1`
to make rollback trivial.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("creatorstudio.storybook.janitor")

TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "REFUNDED", "FAILED_STUCK"}
STUCK_THRESHOLD_MINUTES = int(os.environ.get("COMIC_STORYBOOK_STUCK_MINUTES", "30"))
JANITOR_INTERVAL_SECONDS = int(os.environ.get("COMIC_STORYBOOK_JANITOR_INTERVAL", "300"))


async def record_transition(
    db,
    *,
    job_id: str,
    user_id: str | None,
    from_status: str | None,
    to_status: str,
    source: str,
    reason: str | None = None,
    request_id: str | None = None,
    extra: dict | None = None,
) -> None:
    """Append a single transition audit row.

    Designed to be FORGIVING — any exception is swallowed so the
    audit never breaks the actual generation flow.
    """
    try:
        await db.comic_storybook_v2_transitions.insert_one({
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "user_id": user_id,
            "from_status": from_status,
            "to_status": to_status,
            "source": source,
            "reason": (reason or "")[:500],
            "request_id": request_id,
            "extra": extra or {},
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(
            "[transition-log] failed to audit transition job=%s "
            "%s→%s source=%s err=%s",
            job_id[:8], from_status, to_status, source, e,
        )


async def recover_stuck_comic_jobs(db) -> dict:
    """Single janitor pass.

    Finds jobs whose status is non-terminal AND whose `updatedAt` is
    older than `STUCK_THRESHOLD_MINUTES` minutes. Marks each one as
    `FAILED_STUCK`, refunds the cost, releases any idempotency lock,
    and writes an audit row.

    Returns a summary dict of what was done so callers (admin
    endpoint / cron) can surface it.
    """
    threshold = datetime.now(timezone.utc) - timedelta(minutes=STUCK_THRESHOLD_MINUTES)
    threshold_iso = threshold.isoformat()

    stuck = await db.comic_storybook_v2_jobs.find(
        {
            "status": {"$nin": list(TERMINAL_STATUSES)},
            # `updatedAt` is the heartbeat field stamped by update_stage.
            # Some legacy rows used `createdAt` instead; the $or covers both.
            "$or": [
                {"updatedAt": {"$lt": threshold_iso}},
                {"updatedAt": {"$exists": False}, "createdAt": {"$lt": threshold_iso}},
            ],
        },
        {"_id": 0, "id": 1, "userId": 1, "status": 1, "cost": 1,
         "idempotency_key": 1, "createdAt": 1},
    ).to_list(100)

    recovered = []
    for row in stuck:
        job_id = row["id"]
        prev = row.get("status")
        user_id = row.get("userId")
        cost = int(row.get("cost", 0) or 0)
        idem_key = row.get("idempotency_key")

        try:
            # Mark the job FAILED_STUCK.
            await db.comic_storybook_v2_jobs.update_one(
                {"id": job_id, "status": prev},  # CAS — don't clobber a
                                                  # racing real completion.
                {"$set": {
                    "status": "FAILED_STUCK",
                    "progressMessage": "Auto-recovered by janitor: worker stopped responding.",
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                    "stuck_recovered_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            # Refund credits if any were debited.
            if cost > 0 and user_id:
                try:
                    await db.users.update_one(
                        {"id": user_id},
                        {"$inc": {"credits": cost}},
                    )
                except Exception as e:
                    logger.warning(
                        "[janitor] refund failed user=%s cost=%s err=%s",
                        user_id, cost, e,
                    )
            # Release idempotency lock so the user can retry.
            if idem_key:
                try:
                    await db.idempotency_keys.delete_one({"key": idem_key})
                except Exception:
                    pass
            # Audit.
            await record_transition(
                db,
                job_id=job_id,
                user_id=user_id,
                from_status=prev,
                to_status="FAILED_STUCK",
                source="janitor:stuck-job",
                reason=f"updatedAt older than {STUCK_THRESHOLD_MINUTES}m",
                extra={"refunded_credits": cost},
            )
            recovered.append({
                "job_id": job_id,
                "user_id": user_id,
                "prev_status": prev,
                "refunded": cost,
            })
            logger.warning(
                "[janitor] recovered stuck job id=%s user=%s prev=%s refund=%s",
                job_id[:8], (user_id or "?")[:8], prev, cost,
            )
        except Exception as e:
            logger.error(
                "[janitor] failed to recover job id=%s err=%s",
                job_id[:8], e,
            )

    return {
        "checked": len(stuck),
        "recovered_count": len(recovered),
        "threshold_minutes": STUCK_THRESHOLD_MINUTES,
        "recovered": recovered,
    }


async def run_janitor_forever(db) -> None:
    """Background loop. Started on app boot when the env flag is set."""
    logger.info(
        "[janitor] started. interval=%ss stuck_threshold=%sm",
        JANITOR_INTERVAL_SECONDS, STUCK_THRESHOLD_MINUTES,
    )
    while True:
        try:
            await recover_stuck_comic_jobs(db)
        except Exception as e:
            logger.error("[janitor] unhandled error in pass: %s", e)
        await asyncio.sleep(JANITOR_INTERVAL_SECONDS)
