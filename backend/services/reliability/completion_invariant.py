"""
Generic completion-invariant helper — P1 2026-05-19 reliability sweep.

Single canonical gate every multi-output async pipeline must call
before persisting a terminal success state. Without this gate, partial
corruption silently becomes "success" — the exact failure mode that
produced the Photo-to-Comic 2-of-3 panel bug.

Doctrine reference: rule 2 ("every critical flow has canonical state")
and rule 3 ("every failure is observable").

Usage:

    from services.reliability.completion_invariant import (
        assert_completion_invariant, InvariantResult,
    )

    result = await assert_completion_invariant(
        expected_count=panel_count,
        actual_count=actual_ready_count,
        declared_status=job_status,
        request_id=request_id,
        job_id=job_id,
        pipeline="photo_to_comic.strip",
        db=db,
    )
    job_status = result.effective_status
    job_decision = result.decision
    if result.repaired:
        # downstream notification / refund flow

The helper is intentionally synchronous-friendly and accepts an
optional `db` handle so callers can opt into metric persistence. It
NEVER raises — invariant failure is a domain event, not a 500.

Counters emitted (daily-bucketed in `diagnostics_metrics`):
  • completion_invariant_failed_total    — gate caught a false COMPLETE
  • partial_output_repaired_total        — status downgraded gracefully
  • false_complete_prevented_total       — total "lies" we caught
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

logger = logging.getLogger("creatorstudio.completion_invariant")

# Statuses we treat as "claimed terminal success". Pipelines may use
# different names; we recognize the canonical four and any pipeline can
# add its own via the `terminal_success_states` argument.
DEFAULT_TERMINAL_SUCCESS = frozenset({
    "COMPLETED",
    "READY",
    "SUCCESS",
    "READY_WITH_WARNINGS",
})

# Statuses we downgrade to when the invariant fails. Pipelines may
# override per call.
DEFAULT_REPAIR_STATUS = "PARTIAL_READY"


@dataclass(frozen=True)
class InvariantResult:
    effective_status: str
    decision: str
    repaired: bool
    expected: int
    actual: int
    pipeline: str
    request_id: Optional[str]
    job_id: Optional[str]


async def _emit_metric(db: Any, metric: str, meta: Optional[dict] = None) -> None:
    """Increment a daily-bucketed counter. Never raises."""
    if db is None:
        return
    try:
        bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await db.diagnostics_metrics.update_one(
            {"metric": metric, "bucket": bucket},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {
                    "metric": metric,
                    "bucket": bucket,
                    "first_seen_at": datetime.now(timezone.utc).isoformat(),
                },
                "$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()},
                "$push": {
                    "recent_samples": {
                        "$each": [{
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "meta": meta or {},
                        }],
                        "$slice": -25,
                    },
                },
            },
            upsert=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to persist completion-invariant metric")


async def assert_completion_invariant(
    *,
    expected_count: int,
    actual_count: int,
    declared_status: str,
    request_id: Optional[str] = None,
    job_id: Optional[str] = None,
    pipeline: str = "unknown",
    db: Any = None,
    repair_status: str = DEFAULT_REPAIR_STATUS,
    terminal_success_states: Optional[frozenset[str]] = None,
) -> InvariantResult:
    """The canonical completion gate.

    Returns an `InvariantResult` carrying the effective status the
    caller MUST persist. NEVER raises. If the declared status claims
    terminal success but `actual_count != expected_count`, the result's
    `effective_status` is downgraded to `repair_status` and the
    appropriate counters are incremented.

    Calling this helper is the merge gate enforced by
    `test_completion_invariant_audit_*` — any new pipeline that emits
    a terminal-success status without going through this helper will
    fail CI.
    """
    success_set = terminal_success_states or DEFAULT_TERMINAL_SUCCESS
    claims_success = declared_status in success_set
    counts_match = (expected_count == actual_count)

    base_meta = {
        "pipeline": pipeline,
        "request_id": request_id,
        "job_id": job_id,
        "expected": expected_count,
        "actual": actual_count,
        "declared": declared_status,
    }

    if not claims_success:
        # Non-success terminal (FAILED, CANCELLED, etc.) — let it through
        # untouched. The invariant only fires on claimed success.
        return InvariantResult(
            effective_status=declared_status,
            decision="ACCEPT_AS_DECLARED",
            repaired=False,
            expected=expected_count,
            actual=actual_count,
            pipeline=pipeline,
            request_id=request_id,
            job_id=job_id,
        )

    if counts_match:
        return InvariantResult(
            effective_status=declared_status,
            decision="ACCEPT_FULL",
            repaired=False,
            expected=expected_count,
            actual=actual_count,
            pipeline=pipeline,
            request_id=request_id,
            job_id=job_id,
        )

    # ──── INVARIANT FAILURE — claimed success but counts disagree. ─────
    logger.error(
        "[completion_invariant] FALSE_COMPLETE_PREVENTED pipeline=%s "
        "job_id=%s request_id=%s declared=%s expected=%d actual=%d",
        pipeline, job_id, request_id, declared_status,
        expected_count, actual_count,
    )

    await _emit_metric(db, "completion_invariant_failed_total", base_meta)
    await _emit_metric(db, "false_complete_prevented_total", base_meta)
    if actual_count > 0:
        await _emit_metric(db, "partial_output_repaired_total", base_meta)

    return InvariantResult(
        effective_status=repair_status,
        decision="ACCEPT_PARTIAL_INVARIANT_REPAIRED",
        repaired=True,
        expected=expected_count,
        actual=actual_count,
        pipeline=pipeline,
        request_id=request_id,
        job_id=job_id,
    )


# Convenience export — registered pipelines opt in to the static-audit
# coverage. The audit scanner reads this list to know which modules to
# enforce. Adding a new pipeline is a one-line addition here AND the
# pipeline must call `assert_completion_invariant` before any
# terminal-success status persistence.
REGISTERED_PIPELINES: Tuple[str, ...] = (
    "routes/photo_to_comic.py",
)
