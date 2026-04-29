"""Share funnel analytics + Premium priority queue regression tests.

A — share funnel:
  • All 12 founder-spec events are in FUNNEL_STEPS allow-list
  • /api/funnel/track accepts unauthenticated share_page_view + video_play_clicked
  • /api/funnel/youstar/kpis returns the 5 ratios + 5 segmentation buckets
  • share/:slug payload now includes `creator_plan`

B — priority queue:
  • _PRIORITY_GATE + _STANDARD_GATE exist with correct slot counts
  • _run_pipeline picks priority lane for is_priority=True jobs
  • queue_wait_seconds + queue_lane recorded on the job
  • /admin/queue-stats returns aggregated metrics
"""
import os, asyncio, uuid
import httpx, pytest
from datetime import datetime, timezone, timedelta

BACKEND = "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS  = "Cr3@t0rStud!o#2026"


async def _admin_token() -> str:
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        return r.json()["token"]


# ─── A. Share funnel allow-list ───────────────────────────────────────────────
def test_funnel_allow_list_contains_share_page_events():
    """All 12 events the founder asked for must be in the allow-list,
    otherwise /track will 400-reject them at runtime."""
    import sys
    sys.path.insert(0, "/app/backend")
    from routes.funnel_tracking import FUNNEL_STEPS
    required = [
        "share_page_view", "video_play_clicked",
        "watch_25", "watch_50", "watch_75", "completed_watch",
        "make_your_own_clicked",
        "whatsapp_share_clicked", "native_share_clicked",
        "signup_started", "signup_success", "first_trailer_created",
    ]
    missing = [s for s in required if s not in FUNNEL_STEPS]
    assert not missing, f"missing share-funnel steps: {missing}"


# ─── A. /track accepts unauth share_page_view ─────────────────────────────────
@pytest.mark.asyncio
async def test_track_accepts_unauth_share_page_view():
    async with httpx.AsyncClient(base_url=BACKEND, timeout=10.0) as c:
        r = await c.post("/api/funnel/track", json={
            "step": "share_page_view",
            "session_id": str(uuid.uuid4()),
            "device_type": "mobile",
            "utm_medium": "whatsapp",
            "traffic_source": "whatsapp",
            "meta": {"slug": "abc1234567", "creator_plan": "PREMIUM",
                     "format": "vertical", "duration": 60},
        })
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"


# ─── A. KPI endpoint: shape + ratios always present ───────────────────────────
@pytest.mark.asyncio
async def test_youstar_kpi_pack_returns_expected_shape():
    token = await _admin_token()
    H = {"Authorization": f"Bearer {token}"}
    # First fire enough events so the ratios resolve
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        sid = str(uuid.uuid4())
        await c.post("/api/funnel/track", json={
            "step": "share_page_view", "session_id": sid,
            "device_type": "mobile", "utm_medium": "whatsapp",
            "meta": {"slug": "test_kpi_slug", "creator_plan": "PREMIUM",
                     "format": "vertical", "duration": 60}})
        await c.post("/api/funnel/track", json={
            "step": "video_play_clicked", "session_id": sid,
            "device_type": "mobile", "meta": {"slug": "test_kpi_slug",
                     "creator_plan": "PREMIUM", "format": "vertical"}})
        await c.post("/api/funnel/track", json={
            "step": "whatsapp_share_clicked", "session_id": sid,
            "device_type": "mobile", "meta": {"slug": "test_kpi_slug",
                     "creator_plan": "PREMIUM", "format": "vertical"}})
        # Now fetch
        r = await c.get("/api/funnel/youstar/kpis?days=7", headers=H)
        assert r.status_code == 200, r.text
        body = r.json()
        # Top-level shape
        assert "ratios" in body and "volumes" in body and "segments" in body
        # 5 founder-required ratios
        for k in ("view_to_play_pct", "play_to_signup_pct",
                  "signup_to_first_trailer_pct", "view_to_share_pct",
                  "premium_share_rate_pct", "free_share_rate_pct"):
            assert k in body["ratios"], f"ratio {k} missing"
        # 5 segmentation buckets
        for k in ("device", "format", "source", "creator_plan", "duration"):
            assert k in body["segments"], f"segment {k} missing"
        # Volume keys we just incremented
        assert body["volumes"]["share_page_view"] >= 1
        assert body["volumes"]["video_play_clicked"] >= 1
        assert body["volumes"]["whatsapp_share_clicked"] >= 1


# ─── A. /share/:slug now exposes creator_plan ────────────────────────────────
@pytest.mark.asyncio
async def test_share_endpoint_exposes_creator_plan():
    """Public share-page payload must carry creator_plan so the frontend
    can attach it to every funnel event."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    j_id = str(uuid.uuid4()); slug = uuid.uuid4().hex[:10]
    now = datetime.now(timezone.utc).isoformat()
    await db.photo_trailer_jobs.insert_one({
        "_id": j_id, "user_id": "test-user", "status": "COMPLETED",
        "template_id": "superhero_origin", "template_name": "Superhero Origin",
        "duration_target_seconds": 60,
        "result_video_url": "https://x/v.mp4", "result_video_key": "v.mp4",
        "public_share_slug": slug,
        "plan_tier_at_creation": "PREMIUM",
        "created_at": now, "completed_at": now, "updated_at": now,
    })
    try:
        async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
            r = await c.get(f"/api/photo-trailer/share/{slug}")
            assert r.status_code == 200
            assert r.json()["creator_plan"] == "PREMIUM"
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": j_id})
    cli.close()


# ─── B. Priority queue: gates configured correctly ────────────────────────────
def test_priority_and_standard_gates_separate():
    import sys
    sys.path.insert(0, "/app/backend")
    from routes.photo_trailer import (
        _PRIORITY_GATE, _STANDARD_GATE, MAX_ACTIVE_PIPELINES,
    )
    # Two distinct semaphores
    assert _PRIORITY_GATE is not _STANDARD_GATE
    # Standard slots match the existing constant; priority is independent.
    assert _STANDARD_GATE._value <= MAX_ACTIVE_PIPELINES
    assert _PRIORITY_GATE._value >= 1


# ─── B. Premium job records lane='priority' + low queue_wait ──────────────────
@pytest.mark.asyncio
async def test_premium_job_records_priority_lane_and_wait_time():
    """Premium job acquires the priority lane. Each async test gets a fresh
    event loop, so we use a fresh motor client per-test to avoid the
    "Event loop is closed" race against the imported module's cached handle."""
    import sys
    sys.path.insert(0, "/app/backend")
    from routes import photo_trailer as pt
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    # Rebind module db for this test only
    saved_db = pt.db
    pt.db = db

    j_id = str(uuid.uuid4())
    await db.photo_trailer_jobs.insert_one({
        "_id": j_id, "user_id": "queue-test-user", "status": "QUEUED",
        "is_priority": True,
        "plan_tier_at_creation": "PREMIUM",
        "estimated_credits": 60,
        "duration_target_seconds": 60,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Replace _run_pipeline_inner with a no-op
    inner_called = []
    async def fake_inner(jid):
        inner_called.append(jid)
        await asyncio.sleep(0.05)
    saved = pt._run_pipeline_inner
    pt._run_pipeline_inner = fake_inner
    try:
        await pt._run_pipeline(j_id)
    finally:
        pt._run_pipeline_inner = saved

    fresh = await db.photo_trailer_jobs.find_one({"_id": j_id})
    try:
        assert inner_called == [j_id]
        assert fresh.get("queue_lane") == "priority", \
            f"PREMIUM job should hit priority lane, got: {fresh.get('queue_lane')}"
        assert fresh.get("queue_wait_seconds") is not None
        assert fresh["queue_wait_seconds"] < 1.0, \
            f"empty priority gate → near-zero wait, got {fresh['queue_wait_seconds']}"
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": j_id})
    pt.db = saved_db
    cli.close()


# ─── B. Standard job → standard lane ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_standard_job_records_standard_lane():
    """Standard (non-premium) job lands in the standard lane."""
    import sys
    sys.path.insert(0, "/app/backend")
    from routes import photo_trailer as pt
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    saved_db = pt.db
    pt.db = db
    j_id = str(uuid.uuid4())
    await db.photo_trailer_jobs.insert_one({
        "_id": j_id, "user_id": "queue-test-user", "status": "QUEUED",
        "is_priority": False,
        "plan_tier_at_creation": "PAID",
        "estimated_credits": 35,
        "duration_target_seconds": 60,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    async def fake_inner(jid): await asyncio.sleep(0.01)
    saved = pt._run_pipeline_inner
    pt._run_pipeline_inner = fake_inner
    try:
        await pt._run_pipeline(j_id)
    finally:
        pt._run_pipeline_inner = saved

    fresh = await db.photo_trailer_jobs.find_one({"_id": j_id})
    try:
        assert fresh.get("queue_lane") == "standard"
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": j_id})
    pt.db = saved_db
    cli.close()


# ─── B. /admin/queue-stats returns aggregated shape ──────────────────────────
@pytest.mark.asyncio
async def test_admin_queue_stats_returns_expected_shape():
    token = await _admin_token()
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.get("/api/photo-trailer/admin/queue-stats?days=7",
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        for k in ("period_days", "by_plan_and_lane", "by_plan", "config"):
            assert k in body
        assert body["config"]["standard_slots"] == 2
        assert body["config"]["priority_slots"] >= 1
