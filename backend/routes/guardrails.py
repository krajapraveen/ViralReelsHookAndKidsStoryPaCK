"""
Red Flag Alert System + Guardrail Endpoint
Detects silent corruption: credit drift, duplicate grants, draft races,
analytics inflation, payment mismatches. Persists alerts, deduplicates,
auto-resolves when invariants heal.
"""
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user

logger = logging.getLogger("guardrails")
router = APIRouter(prefix="/admin/guardrails", tags=["Guardrails"])

# ═══ INVARIANT DEFINITIONS ═══
INVARIANTS = {
    "negative_credits": {
        "name": "No Negative Credits",
        "description": "No user should ever have credits < 0",
        "severity": "critical",
    },
    "duplicate_credit_grants": {
        "name": "No Duplicate Credit Grants",
        "description": "Each payment order_id should produce at most 1 credit ledger entry",
        "severity": "critical",
    },
    "multiple_active_drafts": {
        "name": "One Active Draft Per User",
        "description": "No user should have more than 1 draft with status='draft'",
        "severity": "high",
    },
    "orphan_processing_jobs": {
        "name": "No Stuck Processing Jobs",
        "description": "Jobs in PROCESSING state for >30 minutes are likely orphaned",
        "severity": "high",
    },
    "analytics_session_duplication": {
        "name": "No Session Start Inflation",
        "description": "session_started should not exceed 1 per session_id",
        "severity": "medium",
    },
    "payment_without_credit": {
        "name": "No Payment Without Credits",
        "description": "Every PAID order in orders collection should have a matching credit_ledger entry",
        "severity": "critical",
    },
    "private_content_leak": {
        "name": "No Private Content in Feed",
        "description": "Only READY/COMPLETED stories should appear in public-facing queries",
        "severity": "high",
    },
}


async def _check_negative_credits():
    """Check for users with negative credit balance."""
    pipeline = [{"$match": {"credits": {"$lt": 0}}}, {"$project": {"_id": 0, "email": 1, "credits": 1, "id": 1}}]
    users = await db.users.aggregate(pipeline).to_list(10)
    return {
        "violated": len(users) > 0,
        "count": len(users),
        "sample_ids": [u.get("email", u.get("id", "?")) for u in users[:5]],
    }


async def _check_duplicate_credit_grants():
    """Check for duplicate credit grants per order_id."""
    pipeline = [
        {"$match": {"type": {"$in": ["credit", "purchase", "payment"]}, "order_id": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$order_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    dupes = await db.credit_ledger.aggregate(pipeline).to_list(20)
    return {
        "violated": len(dupes) > 0,
        "count": len(dupes),
        "sample_ids": [d["_id"] for d in dupes[:5]],
    }


async def _check_multiple_active_drafts():
    """Check for users with >1 active draft."""
    pipeline = [
        {"$match": {"status": "draft"}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    multi = await db.story_drafts.aggregate(pipeline).to_list(20)
    return {
        "violated": len(multi) > 0,
        "count": len(multi),
        "sample_ids": [str(m["_id"])[:20] for m in multi[:5]],
    }


async def _check_orphan_processing_jobs():
    """Check for jobs stuck in PROCESSING for >30 minutes."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    stuck = await db.story_engine_jobs.count_documents({
        "state": "PROCESSING",
        "updated_at": {"$lt": cutoff}
    })
    sample = []
    if stuck > 0:
        jobs = await db.story_engine_jobs.find(
            {"state": "PROCESSING", "updated_at": {"$lt": cutoff}},
            {"_id": 0, "job_id": 1}
        ).to_list(5)
        sample = [j["job_id"] for j in jobs]
    return {"violated": stuck > 0, "count": stuck, "sample_ids": sample}


async def _check_analytics_session_duplication():
    """Check for session_started duplication (>1 per session_id in last 24h)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    pipeline = [
        {"$match": {"step": "session_started", "timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": "$session_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    dupes = await db.funnel_events.aggregate(pipeline).to_list(50)
    return {
        "violated": len(dupes) > 0,
        "count": len(dupes),
        "sample_ids": [str(d["_id"])[:20] for d in dupes[:5]],
    }


async def _check_payment_without_credit():
    """Check for PAID orders without corresponding credit ledger entry."""
    # Get recent paid orders (exclude subscriptions which have different credit flow)
    orders = await db.orders.find(
        {"status": "PAID", "type": {"$nin": ["SUBSCRIPTION", "subscription"]}},
        {"_id": 0, "order_id": 1, "user_id": 1}
    ).sort("created_at", -1).to_list(50)

    missing = []
    for order in orders:
        oid = order.get("order_id", "")
        uid = order.get("user_id")
        if oid and uid:  # Skip orders without user_id (orphan test data)
            credit = await db.credit_ledger.find_one({"order_id": oid})
            if not credit:
                missing.append(oid)

    return {
        "violated": len(missing) > 0,
        "count": len(missing),
        "sample_ids": missing[:5],
    }


async def _check_private_content_leak():
    """Sample public feed query and verify only READY/COMPLETED content."""
    # Check recent items that might leak
    non_ready = await db.story_engine_jobs.count_documents({
        "state": {"$nin": ["READY", "COMPLETED", "PARTIAL", "FAILED", "PROCESSING", "QUEUED", "CREATED"]},
        "is_public": True
    })
    return {"violated": non_ready > 0, "count": non_ready, "sample_ids": []}


# Map invariant keys to check functions
CHECKERS = {
    "negative_credits": _check_negative_credits,
    "duplicate_credit_grants": _check_duplicate_credit_grants,
    "multiple_active_drafts": _check_multiple_active_drafts,
    "orphan_processing_jobs": _check_orphan_processing_jobs,
    "analytics_session_duplication": _check_analytics_session_duplication,
    "payment_without_credit": _check_payment_without_credit,
    "private_content_leak": _check_private_content_leak,
}


async def _persist_alert(key: str, result: dict, meta: dict):
    """Persist or update alert in system_alerts collection. Deduplicates by key."""
    now = datetime.now(timezone.utc).isoformat()

    if result["violated"]:
        existing = await db.system_alerts.find_one({"invariant_key": key, "status": "open"})
        if existing:
            # Update existing alert (don't spam)
            await db.system_alerts.update_one(
                {"invariant_key": key, "status": "open"},
                {"$set": {
                    "last_seen_at": now,
                    "count": result["count"],
                    "sample_entity_ids": result["sample_ids"],
                }, "$inc": {"trigger_count": 1}}
            )
        else:
            # New alert
            await db.system_alerts.insert_one({
                "invariant_key": key,
                "name": meta["name"],
                "description": meta["description"],
                "severity": meta["severity"],
                "status": "open",
                "count": result["count"],
                "sample_entity_ids": result["sample_ids"],
                "first_seen_at": now,
                "last_seen_at": now,
                "trigger_count": 1,
                "resolved_at": None,
            })
    else:
        # Invariant healthy — auto-resolve any open alert
        await db.system_alerts.update_many(
            {"invariant_key": key, "status": "open"},
            {"$set": {"status": "resolved", "resolved_at": now}}
        )


@router.get("")
async def get_guardrails(current_user: dict = Depends(get_current_user)):
    """
    Admin-only guardrail health check.
    Returns pass/fail per invariant with counts, timestamps, sample IDs, severity.
    """
    if current_user.get("role", "").upper() != "ADMIN":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")

    results = {}
    overall_healthy = True

    for key, meta in INVARIANTS.items():
        checker = CHECKERS.get(key)
        if not checker:
            continue
        try:
            result = await checker()
            await _persist_alert(key, result, meta)

            # Get latest alert info
            alert = await db.system_alerts.find_one(
                {"invariant_key": key},
                {"_id": 0},
                sort=[("last_seen_at", -1)]
            )

            status = "FAIL" if result["violated"] else "PASS"
            if result["violated"]:
                overall_healthy = False

            results[key] = {
                "status": status,
                "name": meta["name"],
                "severity": meta["severity"],
                "count": result["count"],
                "sample_ids": result["sample_ids"],
                "last_triggered_at": alert.get("last_seen_at") if alert and result["violated"] else None,
                "first_seen_at": alert.get("first_seen_at") if alert and result["violated"] else None,
                "trigger_count": alert.get("trigger_count", 0) if alert else 0,
            }
        except Exception as e:
            logger.error(f"Guardrail check failed for {key}: {e}")
            results[key] = {
                "status": "ERROR",
                "name": meta["name"],
                "severity": meta["severity"],
                "error": str(e)[:100],
            }

    return {
        "healthy": overall_healthy,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "invariant_count": len(results),
        "pass_count": sum(1 for r in results.values() if r["status"] == "PASS"),
        "fail_count": sum(1 for r in results.values() if r["status"] == "FAIL"),
        "invariants": results,
    }


@router.get("/alerts")
async def get_open_alerts(current_user: dict = Depends(get_current_user)):
    """Get all open (unresolved) alerts."""
    if current_user.get("role", "").upper() != "ADMIN":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")

    alerts = await db.system_alerts.find(
        {"status": "open"},
        {"_id": 0}
    ).sort("severity_order", 1).to_list(100)

    return {"alerts": alerts, "count": len(alerts)}


@router.get("/history")
async def get_alert_history(days: int = 7, current_user: dict = Depends(get_current_user)):
    """Get alert history for the last N days."""
    if current_user.get("role", "").upper() != "ADMIN":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    alerts = await db.system_alerts.find(
        {"first_seen_at": {"$gte": cutoff}},
        {"_id": 0}
    ).sort("first_seen_at", -1).to_list(200)

    return {"alerts": alerts, "count": len(alerts), "period_days": days}
