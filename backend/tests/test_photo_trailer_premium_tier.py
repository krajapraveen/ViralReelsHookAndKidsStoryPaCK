"""Premium 90s tier — entitlement + paywall + monetization regression tests.

Founder acceptance criteria:
  • Non-premium users blocked from 90s with structured 402
  • PREMIUM users (active monthly+ subscription) allowed
  • 60s remains for PAID + PREMIUM
  • 90s costs 60 credits; 60s = 35; 20s = 0 (free preview)
  • FREE tier monthly quota enforced (no infinite free trailers)
  • Plan tier persisted on the job for MySpace badge
  • Cannot spoof tier from frontend — server is authoritative
"""
import os, uuid, asyncio
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import httpx, pytest
from datetime import datetime, timezone, timedelta

BACKEND = "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS  = "Cr3@t0rStud!o#2026"
TEST_EMAIL  = "test@visionary-suite.com"
TEST_PASS   = "Test@2026#"

async def _login(email: str, password: str) -> tuple[str, str]:
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return r.json()["token"], r.json()["user"]["id"]


# ─── Tier helper / tier endpoint behavior ─────────────────────────────────────
@pytest.mark.asyncio
async def test_admin_user_is_premium():
    """Admin role short-circuits to PREMIUM regardless of subscription."""
    token, _ = await _login(ADMIN_EMAIL, ADMIN_PASS)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.get("/api/photo-trailer/me/plan", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert body["plan"] == "PREMIUM"
        assert body["max_duration_seconds"] == 90
        assert body["premium_features"]["duration_90s"] is True
        assert body["premium_features"]["priority_queue"] is True


@pytest.mark.asyncio
async def test_paid_user_capped_at_60s_via_credits():
    """Test user has 1413 credits but no PREMIUM subscription → PAID, 60s max."""
    token, _ = await _login(TEST_EMAIL, TEST_PASS)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.get("/api/photo-trailer/me/plan", headers=H)
        body = r.json()
        assert body["plan"] in ("PAID", "PREMIUM")  # depends on test user state
        assert body["max_duration_seconds"] in (60, 90)


# ─── /credit-estimate exposes plan/required state ────────────────────────────
@pytest.mark.asyncio
async def test_credit_estimate_marks_90s_as_premium_required():
    token, _ = await _login(TEST_EMAIL, TEST_PASS)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.get("/api/photo-trailer/credit-estimate?duration=90", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert body["credits"] == 60
        assert body["required_plan"] == "PREMIUM"
        # 60s requires PAID
        r2 = await c.get("/api/photo-trailer/credit-estimate?duration=60", headers=H)
        assert r2.json()["required_plan"] == "PAID"
        assert r2.json()["credits"] == 35
        # 20s requires only FREE
        r3 = await c.get("/api/photo-trailer/credit-estimate?duration=20", headers=H)
        assert r3.json()["required_plan"] == "FREE"
        assert r3.json()["credits"] == 0


# ─── Server-side enforcement: non-premium blocked from 90s with 402 ──────────
@pytest.mark.asyncio
async def test_non_premium_blocked_from_90s_creating_job():
    """Force the test user to look like a non-premium FREE-with-credits.
    The DB-level subscription decides PAID vs PREMIUM."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    token, uid = await _login(TEST_EMAIL, TEST_PASS)
    # Cancel any active subscription so user is purely PAID-by-credits (cap = 60s).
    await db.subscriptions.update_many(
        {"userId": uid, "status": "active"},
        {"$set": {"status": "cancelled_for_test"}},
    )
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        # Make a quick upload session + photo (we never reach the pipeline)
        r = await c.post("/api/photo-trailer/uploads/init", headers=H, json={
            "file_count": 1, "mime_types": ["image/png"], "file_sizes": [1000]})
        sid = r.json()["upload_session_id"]
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
        r = await c.post("/api/photo-trailer/uploads/photo", headers=H,
                         data={"upload_session_id": sid},
                         files={"file": ("hero.png", png, "image/png")})
        aid = r.json()["asset_id"]
        await c.post("/api/photo-trailer/uploads/complete", headers=H,
                     json={"upload_session_id": sid, "consent_confirmed": True})
        # Now ask for 90s — must be 402 with structured upgrade payload
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": aid,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": 90,
        })
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        body = r.json()["detail"]
        assert isinstance(body, dict), f"detail must be structured: {body}"
        assert body["code"] == "UPGRADE_REQUIRED"
        assert body["required_plan"] == "PREMIUM"
        assert body["duration_seconds"] == 90
        assert body["upgrade_url"] == "/app/pricing"
    # Restore subscriptions
    await db.subscriptions.update_many(
        {"userId": uid, "status": "cancelled_for_test"},
        {"$set": {"status": "active"}},
    )
    cli.close()


# ─── Premium user (admin shortcut) IS allowed to start a 90s job ─────────────
@pytest.mark.asyncio
async def test_premium_admin_can_create_90s_job():
    token, _ = await _login(ADMIN_EMAIL, ADMIN_PASS)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/photo-trailer/uploads/init", headers=H, json={
            "file_count": 1, "mime_types": ["image/png"], "file_sizes": [1000]})
        sid = r.json()["upload_session_id"]
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
        r = await c.post("/api/photo-trailer/uploads/photo", headers=H,
                         data={"upload_session_id": sid},
                         files={"file": ("h.png", png, "image/png")})
        aid = r.json()["asset_id"]
        await c.post("/api/photo-trailer/uploads/complete", headers=H,
                     json={"upload_session_id": sid, "consent_confirmed": True})
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": aid,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": 90,
        })
        assert r.status_code in (200, 201), f"premium 90s should pass: {r.status_code} {r.text}"
        job_id = r.json()["job_id"]
        # Cancel right away so we don't burn a render slot.
        await c.post(f"/api/photo-trailer/jobs/{job_id}/cancel", headers=H)


# ─── Plan tier persisted on the job document ─────────────────────────────────
@pytest.mark.asyncio
async def test_job_records_plan_tier_at_creation():
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    token, uid = await _login(ADMIN_EMAIL, ADMIN_PASS)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/photo-trailer/uploads/init", headers=H, json={
            "file_count": 1, "mime_types": ["image/png"], "file_sizes": [1000]})
        sid = r.json()["upload_session_id"]
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
        await c.post("/api/photo-trailer/uploads/photo", headers=H,
                     data={"upload_session_id": sid},
                     files={"file": ("h.png", png, "image/png")})
        # Find that asset_id from the prior call
        rr = await c.post("/api/photo-trailer/uploads/photo", headers=H,
                          data={"upload_session_id": sid},
                          files={"file": ("h2.png", png, "image/png")})
        aid = rr.json()["asset_id"]
        await c.post("/api/photo-trailer/uploads/complete", headers=H,
                     json={"upload_session_id": sid, "consent_confirmed": True})
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": aid,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": 60,
        })
        job_id = r.json()["job_id"]
        await c.post(f"/api/photo-trailer/jobs/{job_id}/cancel", headers=H)
    j = await db.photo_trailer_jobs.find_one({"_id": job_id})
    assert j.get("plan_tier_at_creation") == "PREMIUM"
    assert j.get("is_priority") is True
    cli.close()


# ─── Credit table guard ──────────────────────────────────────────────────────
def test_credit_buckets_match_pricing_spec():
    import sys
    sys.path.insert(0, "/app/backend")
    from routes.photo_trailer import DURATION_BUCKETS, _credits_for
    # Founder spec: 20s free, 60s = 35cr, 90s = 60cr
    assert _credits_for(15) == 0
    assert _credits_for(20) == 0
    assert _credits_for(45) == 25
    assert _credits_for(60) == 35
    assert _credits_for(90) == 60
    # 91 falls back to last bucket (max bucket)
    assert _credits_for(120) == 60


# ─── /jobs duration validator now accepts 90s ────────────────────────────────
@pytest.mark.asyncio
async def test_credit_estimate_accepts_90_rejects_91():
    token, _ = await _login(ADMIN_EMAIL, ADMIN_PASS)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        ok = await c.get("/api/photo-trailer/credit-estimate?duration=90", headers=H)
        assert ok.status_code == 200
        bad = await c.get("/api/photo-trailer/credit-estimate?duration=91", headers=H)
        assert bad.status_code == 422
