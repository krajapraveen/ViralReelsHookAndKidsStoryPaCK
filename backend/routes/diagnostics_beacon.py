"""
Diagnostics Beacon Routes — P1 2026-05-19 reliability sweep
==============================================================

Lightweight backend counters that the frontend pings to prove that
reliability shims are doing work in production. Three metrics:

  • frontend_event_trap_blocked_total
      A React SyntheticEvent (or other non-matching arg) was caught by
      `dropEventArg()` before it could poison handler state.

  • error_toast_without_request_id_total
      A user-facing error toast fired but no backend X-Request-Id was
      available, so the toast had to mint a local Reference ID.

  • p2c_label_fallback_total
      Photo-to-Comic style normalization had to coerce a non-canonical
      label/object input into a canonical key.

The beacon endpoint accepts a batch of events to keep network noise low.
Counters are persisted in the `diagnostics_metrics` collection with
per-day buckets so the admin dashboard can plot a sparkline.

The admin metrics-read endpoint exposes the rolled-up counts. It is
behind the existing `get_admin_user` dependency.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, validator

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_admin_user  # noqa: E402

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])

# ────────────────────────────────────────────────────────────────────
# Allow-listed metric names. Any other name is silently rejected so an
# attacker cannot blow up the collection with arbitrary keys.
# ────────────────────────────────────────────────────────────────────
ALLOWED_METRICS = frozenset({
    "frontend_event_trap_blocked_total",
    "error_toast_without_request_id_total",
    "p2c_label_fallback_total",
    # P0 2026-05-22 — Reaction GIF connection-loss bug-class elimination.
    # Frontend emits these so we can observe (and alert on) transient
    # polling failures, structural recoveries, and invariant-repaired
    # completions in production.
    "reaction_gif_connection_lost_total",
    "reaction_gif_poll_recovered_total",
    "reaction_gif_completion_invariant_failed_total",
    # P0 2026-05-22 — Reaction GIF false-success bug-class elimination.
    # Backend emits asset_verify_failed; frontend emits broken_preview
    # and false_success_prevented (when its image preload probe fails
    # against a "COMPLETED" job).
    "reaction_gif_asset_verify_started_total",
    "reaction_gif_asset_verify_failed_total",
    "reaction_gif_broken_preview_total",
    "reaction_gif_false_success_prevented_total",
    "reaction_gif_download_url_missing_total",
    # P0 2026-05-22 — Stuck-job / timeout bug-class elimination.
    "reaction_gif_stage_timeout_total",
    "reaction_gif_job_timeout_total",
    "reaction_gif_stuck_job_repaired_total",
    "reaction_gif_worker_silent_death_total",
    "reaction_gif_poll_terminal_miss_total",
    "reaction_gif_refund_on_timeout_total",
})

# Hard cap on payload size — prevents abusive clients from spamming.
MAX_EVENTS_PER_BATCH = 50


class BeaconEvent(BaseModel):
    metric: str = Field(..., description="Metric name (must be in allow-list)")
    ts: Optional[int] = Field(None, description="Client timestamp ms (informational)")
    page: Optional[str] = Field(None, max_length=128)
    meta: Optional[Dict[str, Any]] = Field(None, description="Free-form metadata, capped")

    @validator("meta")
    def _cap_meta(cls, v):  # noqa: N805
        if v is None:
            return v
        # Strip oversized payloads so a bug in the frontend can't fill Mongo.
        out: Dict[str, Any] = {}
        for k, val in list(v.items())[:10]:
            if isinstance(val, str) and len(val) > 256:
                val = val[:256] + "...(truncated)"
            out[str(k)[:64]] = val
        return out


class BeaconBatch(BaseModel):
    events: List[BeaconEvent] = Field(default_factory=list)


def _today_bucket() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@router.post("/beacon")
async def post_beacon(payload: BeaconBatch, request: Request) -> Dict[str, Any]:
    """Accept a batch of metric events. Silently rejects unknown metric
    names so the frontend never fails because of a typo. Returns the
    count of accepted/rejected events so the client can log."""
    if not payload.events:
        return {"accepted": 0, "rejected": 0}

    events = payload.events[:MAX_EVENTS_PER_BATCH]
    bucket = _today_bucket()
    request_id = request.headers.get("X-Request-Id") or request.headers.get("x-request-id")
    accepted = 0
    rejected = 0

    # Aggregate counts in-memory per metric for a single bulk update.
    agg: Dict[str, int] = {}
    samples_per_metric: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        if ev.metric not in ALLOWED_METRICS:
            rejected += 1
            continue
        agg[ev.metric] = agg.get(ev.metric, 0) + 1
        # Keep a small ring of recent sample metas per metric for
        # forensics. Capped to 5 per request so we don't bloat the doc.
        samples = samples_per_metric.setdefault(ev.metric, [])
        if len(samples) < 5:
            samples.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "page": ev.page,
                "meta": ev.meta,
                "request_id": request_id,
            })
        accepted += 1

    for metric, count in agg.items():
        await db.diagnostics_metrics.update_one(
            {"metric": metric, "bucket": bucket},
            {
                "$inc": {"count": count},
                "$setOnInsert": {
                    "metric": metric,
                    "bucket": bucket,
                    "first_seen_at": datetime.now(timezone.utc).isoformat(),
                },
                "$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()},
                "$push": {
                    "recent_samples": {
                        "$each": samples_per_metric[metric],
                        "$slice": -25,  # keep newest 25 only
                    }
                },
            },
            upsert=True,
        )

    return {"accepted": accepted, "rejected": rejected}


@router.get("/metrics")
async def get_metrics(
    bucket: Optional[str] = None,
    admin=Depends(get_admin_user),
) -> Dict[str, Any]:
    """Admin-only view of the rolled-up counters. Defaults to today's
    bucket. Strips _id to satisfy the JSON-serialization mandate."""
    if admin is None:
        raise HTTPException(status_code=403, detail="Admin only")

    target_bucket = bucket or _today_bucket()
    cursor = db.diagnostics_metrics.find(
        {"bucket": target_bucket}, {"_id": 0}
    )
    docs = await cursor.to_list(length=None)

    by_metric = {name: 0 for name in ALLOWED_METRICS}
    detail = {}
    for d in docs:
        m = d.get("metric")
        if m in ALLOWED_METRICS:
            by_metric[m] = d.get("count", 0)
            detail[m] = {
                "count": d.get("count", 0),
                "first_seen_at": d.get("first_seen_at"),
                "last_seen_at": d.get("last_seen_at"),
                "recent_samples": d.get("recent_samples", [])[-5:],
            }

    return {
        "bucket": target_bucket,
        "totals": by_metric,
        "detail": detail,
        "allowed_metrics": sorted(ALLOWED_METRICS),
    }
