"""P0 2026-06 — Per-attempt refund + admin credit-grant + retry-orphan repair.

Behavioural pins for the bug class krajapraveen@gmail.com hit on
visionary-suite.com (job 2282a6aa-2bf7-43b8-8739-9c9158fb8f32):

  1. Retry-orphan detection — when a job has 2 deducts + 1 refund, the
     guardrail counts SUMS and flags it. The repair endpoint refunds the
     missing 60 credits.
  2. Per-attempt refund reference_id — refund(attempt 0) does NOT block
     refund(attempt 1). Concurrent paths can both refund their own attempt
     without colliding.
  3. Admin credit grant — safe, audited, idempotent. Re-posting same
     reference_id is a no-op.

Suite uses the live backend (Motor cross-event-loop safety) like the
other 2026-06 trailer suites.
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio
import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")


def _api_base() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


@pytest_asyncio.fixture
async def seeded_user_with_retry_orphan():
    """Seed a synthetic user + ONE failed trailer job with 2 deducts and
    1 refund (krajapraveen production scenario). All cleaned up at exit."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]

    uid = f"orphan-{uuid.uuid4().hex[:8]}"
    email = f"orphan-{uuid.uuid4().hex[:6]}@example.com"
    job_id = f"jid-{uuid.uuid4().hex[:8]}"
    starting_credits = 100

    await db.users.insert_one({
        "_id": uid, "id": uid, "email": email,
        "name": "Retry Orphan Test", "role": "USER",
        "credits": starting_credits,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # FAILED trailer doc whose denorm cache says "refunded" but is actually
    # missing 60 credits in the ledger (mirrors job 2282a6aa).
    failed_at = (datetime.now(timezone.utc).replace(microsecond=0).timestamp())
    from datetime import timedelta as _td
    failed_iso = (datetime.now(timezone.utc) - _td(minutes=30)).isoformat()
    await db.photo_trailer_jobs.insert_one({
        "_id": job_id, "user_id": uid,
        "status": "FAILED", "current_stage": "FAILED",
        "duration_target_seconds": 90, "template_id": "anime_intro",
        "estimated_credits": 60, "charged_credits": 60, "refunded_credits": 60,
        "error_code": "RENDER_INVALID",
        "error_message": "Trailer failed — credits refunded. Please try again.",
        "created_at": (datetime.now(timezone.utc)).isoformat(),
        # Older than 5min grace, within 7-day horizon so guardrail catches it.
        "failed_at": failed_iso,
        "updated_at": failed_iso,
    })
    # Ledger: 2 deducts, 1 refund — net -60 credits the user is owed.
    base_ts = failed_iso
    await db.credit_ledger.insert_many([
        {"_id": f"led-{uuid.uuid4().hex[:8]}",
         "user_id": uid, "type": "deduct", "amount": 60,
         "reason": f"Photo trailer {job_id}", "reference_id": None,
         "created_at": base_ts},
        {"_id": f"led-{uuid.uuid4().hex[:8]}",
         "user_id": uid, "type": "refund", "amount": 60,
         "reason": f"Refund failed trailer {job_id}",
         "reference_id": f"trailer_refund:{job_id}",  # legacy single-attempt
         "created_at": base_ts},
        {"_id": f"led-{uuid.uuid4().hex[:8]}",
         "user_id": uid, "type": "deduct", "amount": 60,
         "reason": f"Photo trailer {job_id}", "reference_id": None,
         "created_at": base_ts},
    ])

    token = create_token(uid, "USER")
    yield {"user_id": uid, "email": email, "job_id": job_id,
           "token": token, "starting_credits": starting_credits, "db": db}

    await db.users.delete_one({"id": uid})
    await db.photo_trailer_jobs.delete_one({"_id": job_id})
    await db.credit_ledger.delete_many({"user_id": uid})
    cli.close()


@pytest_asyncio.fixture
async def admin_session():
    """Synthetic admin user. Cleaned up at exit."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    aid = f"adm-{uuid.uuid4().hex[:8]}"
    await db.users.insert_one({
        "_id": aid, "id": aid, "email": f"{aid}@example.com",
        "name": "P0 Admin", "role": "ADMIN", "credits": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    yield {"id": aid, "token": create_token(aid, "ADMIN"), "db": db}
    await db.users.delete_one({"id": aid})
    await db.admin_credit_grants_audit.delete_many({"actor_user_id": aid})
    cli.close()


# ─── 1. Repair endpoint catches retry orphan ─────────────────────────────────


@pytest.mark.asyncio
async def test_repair_refunds_detects_retry_orphan(seeded_user_with_retry_orphan, admin_session):
    """Old sweep skipped jobs with refunded_credits > 0. New sweep walks the
    ledger directly and detects deducts > refunds. Krajapraveen's job had
    refunded_credits=60 but two 60cr deducts → orphan."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=20.0) as cli:
        # Dry run — must spot the orphan.
        r = await cli.post(
            "/api/photo-trailer/admin/repair-refunds",
            headers={"Authorization": f"Bearer {admin_session['token']}"},
            json={
                "user_email": seeded_user_with_retry_orphan["email"],
                "dry_run": True, "limit": 50,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["dry_run"] is True
        assert body["candidates"] >= 1
        # Find the result row for our seeded job.
        ours = [x for x in body["results"]
                if x["job_id"] == seeded_user_with_retry_orphan["job_id"]]
        assert ours, f"Repair sweep missed seeded orphan job. Results: {body['results']}"
        row = ours[0]
        assert row["deducts_total"] == 120
        assert row["refunds_total"] == 60
        assert row["delta"] == 60
        assert row["action"] == "would_refund"
        assert row["would_restore_credits"] == 60


@pytest.mark.asyncio
async def test_repair_refunds_live_restores_orphan(seeded_user_with_retry_orphan, admin_session):
    """Live run actually credits the user back the missing 60 and the
    second run is a no-op (idempotency)."""
    base = _api_base()
    db = seeded_user_with_retry_orphan["db"]
    starting = seeded_user_with_retry_orphan["starting_credits"]

    async with httpx.AsyncClient(base_url=base, timeout=20.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/admin/repair-refunds",
            headers={"Authorization": f"Bearer {admin_session['token']}"},
            json={
                "user_email": seeded_user_with_retry_orphan["email"],
                "dry_run": False, "limit": 50,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_restored_credits"] == 60

        # Balance check
        u = await db.users.find_one(
            {"id": seeded_user_with_retry_orphan["user_id"]},
            {"_id": 0, "credits": 1},
        )
        assert int(u["credits"]) == starting + 60, (
            f"Expected balance to grow by 60 (orphan restored), "
            f"started {starting}, now {u['credits']}"
        )

        # New canonical refund row exists with per-attempt reference_id.
        refund_row = await db.credit_ledger.find_one({
            "user_id": seeded_user_with_retry_orphan["user_id"],
            "reference_id": {
                "$regex": f"^trailer_refund:{seeded_user_with_retry_orphan['job_id']}:attempt:"
            },
        })
        assert refund_row is not None, "Per-attempt refund row must be written."

        # Second live run is a no-op.
        r2 = await cli.post(
            "/api/photo-trailer/admin/repair-refunds",
            headers={"Authorization": f"Bearer {admin_session['token']}"},
            json={
                "user_email": seeded_user_with_retry_orphan["email"],
                "dry_run": False, "limit": 50,
            },
        )
        assert r2.status_code == 200
        assert r2.json()["total_restored_credits"] == 0, (
            "Repair sweep must be idempotent — second run restores 0."
        )
        u2 = await db.users.find_one(
            {"id": seeded_user_with_retry_orphan["user_id"]},
            {"_id": 0, "credits": 1},
        )
        assert int(u2["credits"]) == starting + 60, (
            "Second repair must not double-credit."
        )


# ─── 2. Guardrail detects retry orphan ───────────────────────────────────────


@pytest.mark.asyncio
async def test_guardrail_detects_retry_orphan_via_sum(seeded_user_with_retry_orphan, admin_session):
    """Tightened guardrail counts deduct/refund SUMS. The seeded job has
    deducts=120, refunds=60 → must flag."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.get(
            "/api/admin/guardrails",
            headers={"Authorization": f"Bearer {admin_session['token']}"},
        )
        assert r.status_code == 200, r.text
        invariants = r.json().get("invariants", {})
        guard = invariants.get("trailer_failed_without_refund")
        assert guard is not None, f"Guardrail not registered: {list(invariants.keys())}"
        assert guard["status"] == "FAIL", (
            f"Guardrail must fail for retry-orphan. Got: {guard}"
        )
        # Sample must encode the delta so ops can read it at a glance.
        joined = " ".join(guard.get("sample_ids", []))
        assert "delta=" in joined, f"Sample must show delta. Got: {joined}"


# ─── 3. Admin credit-grant endpoint ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_credit_grant_is_idempotent(admin_session):
    """Re-posting same reference_id must NOT double-credit."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    db = admin_session["db"]
    uid = f"grant-target-{uuid.uuid4().hex[:6]}"
    email = f"grant-target-{uuid.uuid4().hex[:6]}@example.com"
    await db.users.insert_one({
        "_id": uid, "id": uid, "email": email,
        "name": "Grant Target", "role": "USER", "credits": 50,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    base = _api_base()
    ref_id = f"test_grant_{uuid.uuid4().hex[:8]}"

    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        payload = {
            "user_email": email, "amount": 60,
            "reason": "P0 manual repair test for orphan deduct",
            "reference_id": ref_id,
        }
        r1 = await cli.post(
            "/api/photo-trailer/admin/credits/grant",
            headers={"Authorization": f"Bearer {admin_session['token']}"},
            json=payload,
        )
        assert r1.status_code == 200, r1.text
        b1 = r1.json()
        assert b1["already_granted"] is False
        assert b1["balance_before"] == 50
        assert b1["balance_after"] == 110
        assert b1["amount"] == 60
        assert b1["audit_id"]

        # Second call with same reference_id — no-op.
        r2 = await cli.post(
            "/api/photo-trailer/admin/credits/grant",
            headers={"Authorization": f"Bearer {admin_session['token']}"},
            json=payload,
        )
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["already_granted"] is True
        assert b2["amount"] == 0
        assert b2["balance_before"] == 110
        assert b2["balance_after"] == 110

        # Balance unchanged.
        u = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1})
        assert int(u["credits"]) == 110, (
            f"Idempotency failed: balance is {u['credits']}, expected 110."
        )

        # Audit row exists.
        audit = await db.admin_credit_grants_audit.find_one({"reference_id": ref_id})
        assert audit is not None
        assert audit["target_user_id"] == uid
        assert audit["amount"] == 60
        assert audit["balance_before"] == 50
        assert audit["balance_after"] == 110

    # Cleanup
    await db.users.delete_one({"id": uid})
    await db.credit_ledger.delete_many({"user_id": uid})
    await db.admin_credit_grants_audit.delete_many({"target_user_id": uid})


@pytest.mark.asyncio
async def test_admin_credit_grant_rejects_short_reason_and_amount(admin_session):
    """Cannot grant 0 credits, cannot use a 3-char reason. These are the
    smell tests that stop "test", "fix", "x" reasons from cluttering audit."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=10.0) as cli:
        # Empty reason
        r = await cli.post(
            "/api/photo-trailer/admin/credits/grant",
            headers={"Authorization": f"Bearer {admin_session['token']}"},
            json={"user_email": "x@x.com", "amount": 10, "reason": "x", "reference_id": "ref_xxxxx"},
        )
        assert r.status_code == 422  # Pydantic validation error
        # Zero amount
        r2 = await cli.post(
            "/api/photo-trailer/admin/credits/grant",
            headers={"Authorization": f"Bearer {admin_session['token']}"},
            json={"user_email": "x@x.com", "amount": 0,
                  "reason": "valid reason here", "reference_id": "ref_xxxxx"},
        )
        assert r2.status_code == 422


@pytest.mark.asyncio
async def test_admin_credit_grant_requires_admin_auth():
    """Non-admin token must be rejected."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    uid = f"nonadmin-{uuid.uuid4().hex[:6]}"
    await db.users.insert_one({
        "_id": uid, "id": uid, "email": f"{uid}@example.com",
        "name": "Non Admin", "role": "USER", "credits": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    token = create_token(uid, "USER")

    base = _api_base()
    try:
        async with httpx.AsyncClient(base_url=base, timeout=10.0) as c:
            r = await c.post(
                "/api/photo-trailer/admin/credits/grant",
                headers={"Authorization": f"Bearer {token}"},
                json={"user_email": "x@x.com", "amount": 10,
                      "reason": "valid reason here", "reference_id": "ref_xxxxx"},
            )
            assert r.status_code in (401, 403), (
                f"Non-admin must be rejected, got {r.status_code}: {r.text}"
            )
    finally:
        await db.users.delete_one({"id": uid})
        cli.close()
