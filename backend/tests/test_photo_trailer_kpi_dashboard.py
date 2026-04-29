"""Tests for /api/photo-trailer/admin/dashboard — the founder KPI readout.

These hit the LIVE running backend (REACT_APP_BACKEND_URL) instead of spinning
up a fresh ASGI transport, because the global Motor client used by
routes.photo_trailer is bound to its event loop and clashes with pytest-asyncio
fresh loops if we re-instantiate the app inside a test.
"""
import os
import uuid
import json
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Backend .env powers MONGO_URL/DB_NAME for direct seeding
load_dotenv("/app/backend/.env")


def _api_base() -> str:
    """Resolve the live backend URL from frontend/.env (production-like)."""
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:8001"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


@pytest_asyncio.fixture
async def admin_token():
    """Login as admin and yield bearer token."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.post(
            "/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
        )
        assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
        body = r.json()
        tok = body.get("access_token") or body.get("token")
        assert tok, body
        yield tok


@pytest.mark.asyncio
async def test_dashboard_requires_admin_auth():
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.get("/api/photo-trailer/admin/dashboard")
    assert r.status_code in (401, 403), r.status_code


@pytest.mark.asyncio
async def test_dashboard_rejects_invalid_range(admin_token):
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=15.0) as cli:
        r = await cli.get(
            "/api/photo-trailer/admin/dashboard?range=12h",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_dashboard_shape_and_math(admin_token):
    """Seed funnel events + a completed PREMIUM 90s job, hit endpoint, assert
    every section + KPI is present and computed correctly."""
    base = _api_base()
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]

    sid_a = str(uuid.uuid4())
    sid_b = str(uuid.uuid4())
    slug = f"kpi-test-{uuid.uuid4().hex[:8]}"
    job_id = f"kpi-job-{uuid.uuid4().hex[:8]}"

    try:
        await db.funnel_events.insert_many([
            {"step": "share_page_view", "session_id": sid_a, "timestamp": _now_iso(),
             "traffic_source": "whatsapp", "meta": {"slug": slug, "format": "wide"}},
            {"step": "share_page_view", "session_id": sid_b, "timestamp": _now_iso(),
             "traffic_source": "direct", "meta": {"slug": slug, "format": "wide"}},
            {"step": "video_play_clicked", "session_id": sid_a, "timestamp": _now_iso(),
             "meta": {"slug": slug, "format": "wide"}},
            {"step": "watch_25", "session_id": sid_a, "timestamp": _now_iso(),
             "meta": {"slug": slug}},
            {"step": "completed_watch", "session_id": sid_a, "timestamp": _now_iso(),
             "meta": {"slug": slug, "format": "wide"}},
            {"step": "whatsapp_share_clicked", "session_id": sid_a, "timestamp": _now_iso(),
             "meta": {"slug": slug}},
            {"step": "make_your_own_clicked", "session_id": sid_b, "timestamp": _now_iso(),
             "meta": {"slug": slug}},
        ])
        now = datetime.now(timezone.utc)
        await db.photo_trailer_jobs.insert_one({
            "_id": job_id, "user_id": "kpi-test-user", "status": "COMPLETED",
            "template_id": "superhero_origin",
            "duration_target_seconds": 90, "plan_tier_at_creation": "PREMIUM",
            "queue_lane": "priority", "queue_wait_seconds": 4.5,
            "charged_credits": 50, "public_share_slug": slug,
            "created_at":   now.isoformat(),
            "started_at":   now.isoformat(),
            "completed_at": (now + timedelta(seconds=180)).isoformat(),
        })

        async with httpx.AsyncClient(base_url=base, timeout=20.0) as c:
            r = await c.get(
                "/api/photo-trailer/admin/dashboard?range=7d",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert r.status_code == 200, r.text
        body = r.json()

        for section in ("acquisition", "engagement", "conversion",
                        "revenue", "ops", "virality"):
            assert section in body, f"missing section: {section}"

        # ACQUISITION
        acq = body["acquisition"]
        assert acq["share_page_views"] >= 2
        assert acq["unique_visitors"] >= 2
        assert acq["source_split"]["whatsapp"] >= 1
        assert acq["source_split"]["direct"]   >= 1

        # ENGAGEMENT
        eng = body["engagement"]
        assert eng["plays_unique"] >= 1
        assert eng["view_to_play_pct"] > 0
        assert eng["watch_25_pct"] > 0
        assert eng["watch_100_pct"] > 0
        assert eng["format_play_split"]["wide"] >= 1
        titles = [t["template_id"] for t in eng["top_templates_by_completion"]]
        assert "superhero_origin" in titles, json.dumps(titles)

        # CONVERSION
        conv = body["conversion"]
        assert conv["make_your_own_clicks"] >= 1
        assert conv["make_your_own_ctr_pct"] > 0
        for k in ("signup_started", "signup_completed", "first_trailer_created",
                  "view_to_signup_pct", "signup_to_first_trailer_pct"):
            assert k in conv, k

        # REVENUE
        rev = body["revenue"]
        assert rev["premium_jobs"] >= 1
        assert rev["purchases_90s"] >= 1
        assert rev["credits_charged_total"] >= 50
        for k in ("free_jobs", "paid_jobs", "premium_jobs",
                  "purchases_60s", "purchases_90s",
                  "upgrade_modal_shown", "upgrade_clicked", "upgrade_ctr_pct"):
            assert k in rev, k

        # OPS
        ops = body["ops"]
        assert ops["avg_wait_premium_seconds"] >= 4.0
        assert ops["total_jobs"] >= 1
        # 90s render time should be roughly 180s for our seeded job
        assert ops["avg_render_seconds_by_duration"]["90"] is not None
        assert ops["avg_render_seconds_by_duration"]["90"] >= 100

        # VIRALITY
        vir = body["virality"]
        assert vir["whatsapp_shares"] >= 1
        assert vir["view_to_share_pct"] > 0
        share_titles = [t["template_id"] for t in vir["top_templates_by_share_rate"]]
        assert "superhero_origin" in share_titles, json.dumps(share_titles)
    finally:
        await db.funnel_events.delete_many({"meta.slug": slug})
        await db.photo_trailer_jobs.delete_one({"_id": job_id})
        cli.close()


@pytest.mark.asyncio
async def test_dashboard_supports_all_three_ranges(admin_token):
    """24h / 7d / 30d should all return valid 6-section payloads."""
    base = _api_base()
    async with httpx.AsyncClient(base_url=base, timeout=20.0) as c:
        for rng in ("24h", "7d", "30d"):
            r = await c.get(
                f"/api/photo-trailer/admin/dashboard?range={rng}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, f"range={rng}: {r.status_code} {r.text}"
            j = r.json()
            assert j["range"] == rng
            for section in ("acquisition", "engagement", "conversion",
                            "revenue", "ops", "virality"):
                assert section in j, f"range={rng} missing {section}"
