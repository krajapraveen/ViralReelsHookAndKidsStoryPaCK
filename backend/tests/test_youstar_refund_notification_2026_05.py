"""
YouStar refund notification — 2026-05-16 P0 (support-load reduction)

Locks in the user mandate:
  "Wire RENDER_INVALID into notification copy.
   'Trailer failed — credits refunded. Please try again.'
   Only for confirmed refunded jobs.
   Include clear status in MySpace/job detail."

Coverage:
  • _fail("RENDER_INVALID", ...) — when refund_issued=True a
    `generation_failed` notification with the founder copy lands in
    db.notifications.
  • _fail() does NOT fire a notification when there's no refund to issue
    (charged_credits == 0).
  • Janitor reap-with-refund path also fires the notification.
  • error_message for RENDER_INVALID is normalized to the user-facing copy
    (the techy ffprobe detail no longer leaks into MySpace UI).
"""
import os
import uuid
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")


def _iso_minutes_ago(m: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=m)).isoformat()


@pytest_asyncio.fixture
async def mongo():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    yield db
    cli.close()


@pytest.mark.asyncio
async def test_fail_paths_notification_matrix(mongo):
    """One consolidated test (single asyncio loop → avoids Motor's
    cross-loop binding) covering three _fail() scenarios:

      A. RENDER_INVALID + refund → notification with EXACT founder copy
         + user-facing error_message normalized (no ffprobe leakage).
      B. CREDIT_DEDUCT_FAIL with no charged credits → NO notification
         (would be misleading to claim a refund).
      C. IMAGE_GEN_FAIL + refund → notification with generic refund copy
         (founder copy reserved for RENDER_INVALID).
    """
    from routes.photo_trailer import _fail

    # ── Scenario A: RENDER_INVALID + refund ─────────────────────────────
    user_a = f"refund-notif-A-{uuid.uuid4().hex[:8]}"
    jid_a = f"trailer-A-{uuid.uuid4().hex[:8]}"
    # ── Scenario B: no-refund failure ───────────────────────────────────
    user_b = f"refund-notif-B-{uuid.uuid4().hex[:8]}"
    jid_b = f"trailer-B-{uuid.uuid4().hex[:8]}"
    # ── Scenario C: generic refund copy ─────────────────────────────────
    user_c = f"refund-notif-C-{uuid.uuid4().hex[:8]}"
    jid_c = f"trailer-C-{uuid.uuid4().hex[:8]}"

    try:
        await mongo.users.insert_many([
            {"_id": user_a, "id": user_a, "email": f"{user_a}@t.l", "credits_balance": 0},
            {"_id": user_b, "id": user_b, "email": f"{user_b}@t.l", "credits_balance": 0},
            {"_id": user_c, "id": user_c, "email": f"{user_c}@t.l", "credits_balance": 0},
        ])
        await mongo.photo_trailer_jobs.insert_many([
            {"_id": jid_a, "user_id": user_a, "status": "PROCESSING",
             "current_stage": "RENDERING_TRAILER", "duration_target_seconds": 60,
             "charged_credits": 25, "refunded_credits": 0,
             "created_at": _iso_minutes_ago(2)},
            {"_id": jid_b, "user_id": user_b, "status": "PROCESSING",
             "current_stage": "VALIDATING", "duration_target_seconds": 60,
             "charged_credits": 0, "refunded_credits": 0,
             "created_at": _iso_minutes_ago(1)},
            {"_id": jid_c, "user_id": user_c, "status": "PROCESSING",
             "current_stage": "GENERATING_SCENES", "duration_target_seconds": 60,
             "charged_credits": 25, "refunded_credits": 0,
             "created_at": _iso_minutes_ago(3)},
        ])

        await _fail(jid_a, "RENDER_INVALID",
                    "Final video failed quality check: no audio stream in final MP4.")
        await _fail(jid_b, "CREDIT_DEDUCT_FAIL", "Insufficient credits")
        await _fail(jid_c, "IMAGE_GEN_FAIL", "Scene 4 image-gen failed after 3 retries")

        # ── A: RENDER_INVALID assertions ────────────────────────────────
        doc_a = await mongo.photo_trailer_jobs.find_one({"_id": jid_a})
        assert doc_a["status"] == "FAILED"
        assert doc_a["error_code"] == "RENDER_INVALID"
        assert doc_a["refunded_credits"] == 25
        assert doc_a["error_message"] == \
            "Trailer failed — credits refunded. Please try again."
        notif_a = await mongo.notifications.find_one({"user_id": user_a, "job_id": jid_a})
        assert notif_a is not None, "RENDER_INVALID refund must create a notification"
        assert notif_a["type"] == "generation_failed"
        assert notif_a["title"] == "Trailer failed — credits refunded"
        assert notif_a["message"] == \
            "Trailer failed — credits refunded. Please try again."
        assert notif_a["feature"] == "photo_trailer"
        assert notif_a["action_url"] == f"/app/my-space?trailer={jid_a}"
        assert notif_a["metadata"]["refund_issued"] is True
        assert notif_a["metadata"]["error_code"] == "RENDER_INVALID"
        assert notif_a["metadata"]["refunded_credits"] == 25

        # ── B: no refund → no notification ──────────────────────────────
        notif_b = await mongo.notifications.find_one({"user_id": user_b, "job_id": jid_b})
        assert notif_b is None, \
            "_fail must not create a refund notification when no refund was issued"

        # ── C: generic refund copy ──────────────────────────────────────
        notif_c = await mongo.notifications.find_one({"user_id": user_c, "job_id": jid_c})
        assert notif_c is not None
        assert notif_c["title"] == "Trailer failed — credits refunded"
        assert "credits have been refunded" in notif_c["message"].lower()
        assert notif_c["metadata"]["error_code"] == "IMAGE_GEN_FAIL"
    finally:
        for jid in (jid_a, jid_b, jid_c):
            await mongo.notifications.delete_many({"job_id": jid})
            await mongo.photo_trailer_jobs.delete_one({"_id": jid})
        for uid in (user_a, user_b, user_c):
            await mongo.users.delete_one({"_id": uid})


# ─── Source-level assertions (cheap, no loop concerns) ───────────────────────
def test_source_render_invalid_uses_founder_copy():
    """Belt-and-braces: confirm the source literal can't drift."""
    src = open("/app/backend/routes/photo_trailer.py").read()
    assert 'Trailer failed — credits refunded. Please try again.' in src, \
        "Founder copy literal must be present in _fail()"
    # And it must only fire after refund_issued is True
    assert "if refund_issued:" in src
    # The janitor refund path must also create a notification
    assert "[trailer-janitor] notification create failed" in src


# ─── Janitor path ────────────────────────────────────────────────────────────
import httpx


def _api_base() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


@pytest_asyncio.fixture
async def admin_token():
    async with httpx.AsyncClient(base_url=_api_base(), timeout=15.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200, r.text
        yield r.json().get("access_token") or r.json().get("token")


@pytest.mark.asyncio
async def test_janitor_reap_with_refund_fires_notification(mongo, admin_token):
    """When the janitor reaps a stale job AND issues a refund, a
    generation_failed notification with via=janitor metadata must appear."""
    user_id = f"janitor-notif-{uuid.uuid4().hex[:8]}"
    jid = f"trailer-janitor-{uuid.uuid4().hex[:8]}"
    try:
        await mongo.users.insert_one({
            "_id": user_id, "id": user_id,
            "email": f"{user_id}@test.local", "credits_balance": 0,
        })
        # Past the 10-min wall → janitor reaps + refunds
        await mongo.photo_trailer_jobs.insert_one({
            "_id": jid, "user_id": user_id, "status": "PROCESSING",
            "current_stage": "GENERATING_SCENES",
            "duration_target_seconds": 60,
            "started_at": _iso_minutes_ago(12),
            "created_at": _iso_minutes_ago(12),
            "last_progress_at": _iso_minutes_ago(8),
            "retry_count": 0,
            "charged_credits": 25, "refunded_credits": 0,
        })
        async with httpx.AsyncClient(base_url=_api_base(), timeout=30.0) as cli:
            r = await cli.post(
                "/api/photo-trailer/admin/janitor/run-now",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, r.text

        # Small wait for notification insert
        await asyncio.sleep(0.5)

        doc = await mongo.photo_trailer_jobs.find_one({"_id": jid})
        assert doc["status"] == "FAILED"
        assert doc["refunded_credits"] == 25

        notif = await mongo.notifications.find_one({"user_id": user_id, "job_id": jid})
        assert notif is not None, "janitor refund must trigger a notification"
        assert notif["type"] == "generation_failed"
        assert "refunded" in notif["title"].lower()
        assert notif["metadata"]["refund_issued"] is True
        assert notif["metadata"].get("via") == "janitor"
        assert notif["metadata"]["refunded_credits"] == 25
    finally:
        await mongo.notifications.delete_many({"job_id": jid})
        await mongo.photo_trailer_jobs.delete_one({"_id": jid})
        await mongo.users.delete_one({"_id": user_id})
