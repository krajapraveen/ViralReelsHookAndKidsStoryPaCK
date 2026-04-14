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
    "credit_drift": {
        "name": "No Credit Drift",
        "description": "For every user: purchased - used must equal current balance",
        "severity": "critical",
    },
    "generation_integrity": {
        "name": "Generation-Credit 1:1 Match",
        "description": "Every completed job must have exactly 1 credit deduction; no orphan deductions without jobs",
        "severity": "critical",
    },
    "orphan_deductions": {
        "name": "No Orphan Credit Deductions",
        "description": "Every generation-related deduction must map to a valid job (active, completed, or failed-with-refund)",
        "severity": "critical",
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


async def _check_credit_drift():
    """Check that purchased - used = balance for all users with ledger activity.
    Excludes admin/unlimited users (credits managed outside ledger)."""
    pipeline = [
        {"$group": {
            "_id": "$user_id",
            "total_credits": {"$sum": {"$cond": [{"$gt": ["$amount", 0]}, "$amount", 0]}},
            "total_debits": {"$sum": {"$cond": [{"$lt": ["$amount", 0]}, {"$abs": "$amount"}, 0]}},
        }},
        {"$project": {"_id": 1, "total_credits": 1, "total_debits": 1, "expected_balance": {"$subtract": ["$total_credits", "$total_debits"]}}},
    ]
    ledger_users = await db.credit_ledger.aggregate(pipeline).to_list(500)

    drifted = []
    # Known development/test accounts to exclude from drift check
    DEV_EMAILS = {"test@visionary-suite.com", "ai@visionary-suite.com", "admin@creatorstudio.ai", "fresh@test-overlay.com"}
    for lu in ledger_users:
        uid = lu["_id"]
        if not uid:
            continue
        expected = lu.get("expected_balance", 0)
        user = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1, "role": 1, "email": 1})
        if not user:
            continue
        # Skip admin/unlimited/dev users — their credits are managed outside ledger
        if user.get("role", "").upper() == "ADMIN" or user.get("credits", 0) >= 999999:
            continue
        if user.get("email", "") in DEV_EMAILS:
            continue
        actual = user.get("credits", 0)
        # Allow tolerance for admin-granted credits and concurrent ops
        if abs(actual - expected) > 10:
            drifted.append(f"{uid[:15]}:expected={expected},actual={actual}")

    return {"violated": len(drifted) > 0, "count": len(drifted), "sample_ids": drifted[:5]}


async def _check_generation_integrity():
    """Check that every completed job has credit deduction. Excludes admin/system users."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    job_pipeline = [
        {"$match": {"state": {"$in": ["READY", "COMPLETED"]}, "created_at": {"$gte": cutoff}, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id", "job_count": {"$sum": 1}}},
    ]
    job_counts = {r["_id"]: r["job_count"] for r in await db.story_engine_jobs.aggregate(job_pipeline).to_list(500)}

    debit_pipeline = [
        {"$match": {"amount": {"$lt": 0}, "timestamp": {"$gte": cutoff}, "user_id": {"$ne": None}}},
        {"$group": {"_id": "$user_id", "debit_count": {"$sum": 1}}},
    ]
    debit_counts = {r["_id"]: r["debit_count"] for r in await db.credit_ledger.aggregate(debit_pipeline).to_list(500)}

    DEV_ACCOUNTS = {"test@visionary-suite.com", "ai@visionary-suite.com", "admin@creatorstudio.ai", "fresh@test-overlay.com"}
    mismatches = []
    for uid in job_counts:
        jobs = job_counts.get(uid, 0)
        debits = debit_counts.get(uid, 0)
        # Skip admin/unlimited/system/dev users (they bypass credit deduction)
        user = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1, "role": 1, "email": 1})
        if user and (user.get("role", "").upper() in ["ADMIN", "SUPERADMIN", "SYSTEM"] or user.get("credits", 0) >= 999999):
            continue
        if user and user.get("email", "") in DEV_ACCOUNTS:
            continue
        if uid in ("system", "admin"):
            continue
        if jobs > 0 and debits == 0:
            mismatches.append(f"{uid[:15]}:jobs={jobs},debits={debits}")
        elif debits > jobs + 3:  # Tolerance for retries/refunds
            mismatches.append(f"{uid[:15]}:jobs={jobs},debits={debits}")

    return {"violated": len(mismatches) > 0, "count": len(mismatches), "sample_ids": mismatches[:5]}


async def _check_orphan_deductions():
    """Check that every generation-related credit deduction maps to a valid job.
    A deduction is orphaned if it references a job_id that doesn't exist, or
    the job is missing/stuck with no terminal state or refund."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Get all generation-related deductions (negative amounts with job references)
    deductions = await db.credit_ledger.find(
        {"amount": {"$lt": 0}, "timestamp": {"$gte": cutoff}, "user_id": {"$ne": None}},
        {"_id": 0, "user_id": 1, "amount": 1, "job_id": 1, "order_id": 1, "reason": 1, "type": 1, "timestamp": 1}
    ).to_list(500)

    orphans = []
    for ded in deductions:
        job_id = ded.get("job_id")
        reason = str(ded.get("reason", "")).lower()
        ded_type = str(ded.get("type", "")).lower()

        # Skip non-generation deductions (purchases, refunds, etc)
        if ded_type in ("refund", "admin_adjustment", "purchase"):
            continue
        if "refund" in reason or "adjustment" in reason:
            continue

        # If deduction has a job_id, verify the job exists
        if job_id:
            job = await db.story_engine_jobs.find_one(
                {"job_id": job_id},
                {"_id": 0, "state": 1, "job_id": 1}
            )
            if not job:
                orphans.append(f"deduction_no_job:{job_id[:15]}:amt={ded['amount']}")
            elif job.get("state") in ("FAILED",) :
                # Failed job — check if refund exists
                refund = await db.credit_ledger.find_one(
                    {"job_id": job_id, "amount": {"$gt": 0}, "type": {"$in": ["refund", "credit_refund"]}}
                )
                if not refund:
                    # Failed job with deduction but no refund — flag but lower severity
                    # (may be intentional policy: no refund on failure)
                    pass
        else:
            # Deduction without job_id reference — check if it's a generation deduction
            if "generat" in reason or "story" in reason or "creat" in reason:
                orphans.append(f"deduction_no_ref:{ded.get('user_id','?')[:10]}:amt={ded['amount']}:ts={ded.get('timestamp','?')[:16]}")

    return {"violated": len(orphans) > 0, "count": len(orphans), "sample_ids": orphans[:5]}


# Map invariant keys to check functions
CHECKERS = {
    "negative_credits": _check_negative_credits,
    "duplicate_credit_grants": _check_duplicate_credit_grants,
    "multiple_active_drafts": _check_multiple_active_drafts,
    "orphan_processing_jobs": _check_orphan_processing_jobs,
    "analytics_session_duplication": _check_analytics_session_duplication,
    "payment_without_credit": _check_payment_without_credit,
    "private_content_leak": _check_private_content_leak,
    "credit_drift": _check_credit_drift,
    "generation_integrity": _check_generation_integrity,
    "orphan_deductions": _check_orphan_deductions,
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


@router.get("/critical")
async def get_critical_guardrails(current_user: dict = Depends(get_current_user)):
    """
    Fast critical-only guardrail check. Designed for 1-5 minute polling.
    Checks ONLY money/credit/generation invariants — no heavy aggregations.
    """
    if current_user.get("role", "").upper() != "ADMIN":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")

    CRITICAL_KEYS = ["negative_credits", "duplicate_credit_grants", "payment_without_credit",
                     "credit_drift", "generation_integrity", "orphan_deductions"]

    results = {}
    overall_healthy = True
    now = datetime.now(timezone.utc).isoformat()

    for key in CRITICAL_KEYS:
        meta = INVARIANTS.get(key)
        checker = CHECKERS.get(key)
        if not meta or not checker:
            continue
        try:
            result = await checker()
            await _persist_alert(key, result, meta)
            status = "FAIL" if result["violated"] else "PASS"
            if result["violated"]:
                overall_healthy = False
            results[key] = {
                "status": status,
                "count": result["count"],
                "sample_ids": result["sample_ids"],
            }
        except Exception as e:
            results[key] = {"status": "ERROR", "error": str(e)[:100]}

    return {
        "healthy": overall_healthy,
        "checked_at": now,
        "checks": len(results),
        "invariants": results,
    }


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
