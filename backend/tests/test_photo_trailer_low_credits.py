"""Tests for the P0 LOW-CREDITS REVENUE UX (2026-04-29 founder directive).

Drives the live backend so we don't fight the cross-event-loop Motor issue.
"""
import os
import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone
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
async def low_credit_user():
    """Provision a synthetic user with zero credits + a directly-minted JWT,
    plus an upload session marked COMPLETED + a hero asset. Bypasses /register
    (which has IP-rate-limiting) by inserting directly via Mongo + JWT."""
    import sys
    sys.path.insert(0, "/app/backend")
    from shared import create_token  # noqa: WPS433

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]

    user_id = f"lowcred-{uuid.uuid4().hex[:8]}"
    email = f"lowcred-{uuid.uuid4().hex[:6]}@example.com"
    session_id = str(uuid.uuid4())
    asset_id = str(uuid.uuid4())

    sub_id = str(uuid.uuid4())
    await db.users.insert_one({
        "_id": user_id, "id": user_id, "email": email,
        "name": "Low Cred User", "role": "USER",
        # No tier field — _user_plan reads from `subscriptions`. Seed an
        # active monthly sub below so the plan-check passes for ALL durations
        # and we exercise the CREDIT check (the actual subject of these tests).
        "credits": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.subscriptions.insert_one({
        "_id": sub_id, "userId": user_id,
        "planId": "monthly",  # → PREMIUM tier in _user_plan
        "status": "active",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    await db.photo_trailer_upload_sessions.insert_one({
        "_id": session_id, "user_id": user_id,
        "status": "COMPLETED",
        "asset_ids": [asset_id],
        "photo_count": 1,
        "consent_recorded_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.photo_trailer_assets.insert_one({
        "_id": asset_id, "user_id": user_id,
        "upload_session_id": session_id,
        "stored_url": "https://example.invalid/fake.jpg",
        "storage_key": "fake/key.jpg",
        "moderation_status": "PASSED",
        "consent_recorded_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    token = create_token(user_id, "USER")
    yield {
        "token": token, "user_id": user_id, "email": email,
        "session_id": session_id, "hero_asset_id": asset_id,
    }

    # Cleanup
    await db.users.delete_one({"id": user_id})
    await db.subscriptions.delete_one({"_id": sub_id})
    await db.photo_trailer_upload_sessions.delete_one({"_id": session_id})
    await db.photo_trailer_assets.delete_one({"_id": asset_id})
    await db.photo_trailer_jobs.delete_many({"user_id": user_id})
    await db.funnel_events.delete_many({"user_id": user_id})
    cli.close()


@pytest.mark.asyncio
async def test_insufficient_credits_returns_structured_402(low_credit_user):
    """Picking a 60s trailer with 0 credits must return a 402 with the exact
    founder-spec payload: code, required, current, missing, suggested
    durations, upgrade_url, topup_url."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/jobs",
            headers={"Authorization": f"Bearer {low_credit_user['token']}"},
            json={
                "upload_session_id": low_credit_user["session_id"],
                "hero_asset_id":     low_credit_user["hero_asset_id"],
                "supporting_asset_ids": [],
                "template_id": "comedy_roast",
                "duration_target_seconds": 60,
                "narrator_style": "alloy",
            },
        )

    assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
    body = r.json()
    detail = body.get("detail")
    assert isinstance(detail, dict), f"detail must be a dict, got: {detail}"
    assert detail["code"] == "INSUFFICIENT_CREDITS"
    assert "Your credits are too low" in detail["message"]
    assert detail["required_credits"] == 35   # 60s tier
    assert detail["current_credits"] == 0
    assert detail["missing_credits"] == 35
    assert detail["duration_seconds"] == 60
    assert detail["current_plan"] == "PREMIUM"
    assert detail["upgrade_url"] == "/app/pricing"
    assert detail["topup_url"] == "/app/billing"
    # Suggested durations: 20s should be suggested (free) — that's the
    # "downgrade to fit your wallet" UX
    assert 20 in detail["suggested_durations"], detail["suggested_durations"]
    assert 60 not in detail["suggested_durations"]
    assert 90 not in detail["suggested_durations"]


@pytest.mark.asyncio
async def test_low_credit_seen_event_emitted(low_credit_user):
    """The 402 path must emit photo_trailer_low_credit_seen for the dashboard's
    revenue funnel — otherwise we can't see that we LOST conversions."""
    base = _api_base()
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    try:
        async with httpx.AsyncClient(base_url=base, timeout=15.0) as h:
            r = await h.post(
                "/api/photo-trailer/jobs",
                headers={"Authorization": f"Bearer {low_credit_user['token']}"},
                json={
                    "upload_session_id": low_credit_user["session_id"],
                    "hero_asset_id":     low_credit_user["hero_asset_id"],
                    "supporting_asset_ids": [],
                    "template_id": "comedy_roast",
                    "duration_target_seconds": 90,
                    "narrator_style": "alloy",
                },
            )
        assert r.status_code == 402

        # Wait briefly for the event insert
        import asyncio
        await asyncio.sleep(0.4)

        ev = await db.funnel_events.find_one({
            "step": "photo_trailer_low_credit_seen",
            "user_id": low_credit_user["user_id"],
        })
        assert ev is not None, "low_credit_seen event must be emitted"
        meta = ev.get("meta") or {}
        assert meta["required_credits"] == 60   # 90s tier
        assert meta["current_credits"] == 0
        assert meta["missing_credits"] == 60
        assert meta["duration_seconds"] == 90
        assert meta["current_plan"] == "PREMIUM"
    finally:
        cli.close()


@pytest.mark.asyncio
async def test_free_tier_20s_does_not_trip_402(low_credit_user):
    """A 20s preview is free (0 credits required) so even a zero-balance user
    should NOT see the low-credits modal. Returns 200/202 with a job id."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.post(
            "/api/photo-trailer/jobs",
            headers={"Authorization": f"Bearer {low_credit_user['token']}"},
            json={
                "upload_session_id": low_credit_user["session_id"],
                "hero_asset_id":     low_credit_user["hero_asset_id"],
                "supporting_asset_ids": [],
                "template_id": "comedy_roast",
                "duration_target_seconds": 20,
                "narrator_style": "alloy",
            },
        )
    # Either accepted (200/202) or quota-exceeded (429) — but NEVER 402.
    assert r.status_code != 402, f"20s free preview should not paywall, got {r.status_code}: {r.text}"


def test_funnel_track_allowlist_includes_low_credit_events():
    """The 5 new low-credit events must be in the public /api/funnel/track
    allowlist or the frontend tracker silently drops them."""
    src = open("/app/backend/routes/funnel_tracking.py").read()
    for ev in (
        "photo_trailer_low_credit_seen",
        "photo_trailer_buy_credit_clicked",
        "photo_trailer_subscribe_clicked",
        "photo_trailer_duration_downgraded",
        "photo_trailer_credit_fail_recovered",
    ):
        assert f'"{ev}"' in src, f"funnel allowlist missing event: {ev}"


def test_pipeline_image_tts_is_pipelined_per_scene():
    """SPEED: per-scene image+TTS must be pipelined (TTS kicked off inline
    after each image lands), not done in two serial gather() phases.
    The serial _v gather block must be gone."""
    src = open("/app/backend/routes/photo_trailer.py").read()
    # The merged inline kick-off is present
    assert 'audio = await _tts(sc["narration"]' in src, \
        "per-scene TTS must be inlined after image gen"
    # The old 2-phase serial gather is gone
    assert 'gather(*[_v(p) for p in scene_payload])' not in src, \
        "old serial TTS gather must be removed for the speed win"
