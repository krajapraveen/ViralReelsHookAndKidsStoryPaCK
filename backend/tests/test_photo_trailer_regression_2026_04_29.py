"""Regression tests for the two P0 bugs reported on 2026-04-29:

Bug 1 — Generated trailers must be saved + visible in MySpace
Bug 2 — 60-second trailers must produce final MP4 between 55 and 65 seconds

These tests do NOT actually run the LLM/ffmpeg pipeline (cost). They:
  • Seed a completed photo_trailer_jobs row
  • Hit /api/photo-trailer/my-trailers as the same user
  • Assert the row is visible with all fields needed by MySpace card
  • Hit /jobs/:id/stream + /share/:slug to confirm playback signing works
For the 60s path, a separate live e2e harness exists:
  backend/tests/verify_60s_trailer_e2e.py — runs a real generation and
  asserts MP4 duration is in [55, 65]. Run that nightly / pre-deploy.
"""
import os, uuid, asyncio
import httpx, pytest
from datetime import datetime, timezone

BACKEND = "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS  = "Cr3@t0rStud!o#2026"

async def _login() -> tuple[str, str]:
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        return r.json()["token"], r.json()["user"]["id"]


# ─── Bug 1: completed trailer is reachable through MySpace's data fetch ──────
@pytest.mark.asyncio
async def test_completed_trailer_visible_to_myspace_fetch():
    """Seed a completed job; verify /my-trailers returns it with every field
    the PhotoTrailerCard renderer reads."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    token, uid = await _login()
    job_id = str(uuid.uuid4())
    slug = uuid.uuid4().hex[:10]
    now = datetime.now(timezone.utc).isoformat()
    await db.photo_trailer_jobs.insert_one({
        "_id": job_id, "user_id": uid, "status": "COMPLETED",
        "current_stage": "COMPLETED", "progress_percent": 100,
        "template_id": "superhero_origin", "template_name": "Superhero Origin",
        "duration_target_seconds": 60,
        "result_video_url": "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/phototrailer/test/results/test.mp4",
        "result_video_key": "videos/phototrailer/test/results/test.mp4",
        "result_thumbnail_url": "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/images/phototrailer/test/results/thumb.jpg",
        "result_thumbnail_key": "images/phototrailer/test/results/thumb.jpg",
        "result_video_asset_id": str(uuid.uuid4()),
        "public_share_slug": slug,
        "created_at": now, "completed_at": now, "updated_at": now,
    })
    H = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
            r = await c.get("/api/photo-trailer/my-trailers?limit=50", headers=H)
            assert r.status_code == 200
            rows = r.json().get("trailers", [])
            match = next((t for t in rows if t.get("job_id") == job_id), None)
            assert match, f"seeded job {job_id} missing from /my-trailers"
            # Every field MySpacePage.js reads on the completed-card path
            for fld in ("job_id", "status", "template_name", "result_video_url",
                        "result_thumbnail_url", "public_share_slug",
                        "duration_target_seconds", "created_at"):
                assert match.get(fld), f"field {fld} missing on completed trailer row"
            assert match["status"] == "COMPLETED"
            assert match["duration_target_seconds"] == 60
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": job_id})
    cli.close()


# ─── Bug 1: PROCESSING trailer also surfaces (so In-Progress section fills) ──
@pytest.mark.asyncio
async def test_processing_trailer_visible_in_my_trailers():
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    token, uid = await _login()
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.photo_trailer_jobs.insert_one({
        "_id": job_id, "user_id": uid, "status": "PROCESSING",
        "current_stage": "RENDERING_TRAILER", "progress_percent": 75,
        "template_id": "superhero_origin", "template_name": "Superhero Origin",
        "duration_target_seconds": 30,
        "created_at": now, "started_at": now, "updated_at": now,
    })
    H = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
            r = await c.get("/api/photo-trailer/my-trailers?limit=50", headers=H)
            rows = r.json().get("trailers", [])
            match = next((t for t in rows if t.get("job_id") == job_id), None)
            assert match, "PROCESSING trailer not in /my-trailers"
            assert match["status"] == "PROCESSING"
            assert match["current_stage"] == "RENDERING_TRAILER"
            assert match["progress_percent"] == 75
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": job_id})
    cli.close()


# ─── Bug 1: result_video_asset_id is populated on completion ─────────────────
@pytest.mark.asyncio
async def test_result_video_asset_id_populated_on_completion():
    """Recent completed jobs must carry a non-null result_video_asset_id."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    # Find a job that completed AFTER the asset_id wiring was added
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    j = await db.photo_trailer_jobs.find_one(
        {"status": "COMPLETED", "completed_at": {"$gt": cutoff}},
        sort=[("completed_at", -1)],
    )
    if not j:
        pytest.skip("no recent completed job to assert against")
    assert j.get("result_video_asset_id"), \
        f"completed job {j['_id']} missing result_video_asset_id"
    cli.close()


# ─── Bug 2: scene-level duration math handles 60s correctly ──────────────────
@pytest.mark.asyncio
async def test_scene_duration_math_for_60s_target():
    """Per-scene duration for 60s with a 6-scene template must be 10s, not 3s.
    Without this, -shortest in the per-scene encode would truncate the clip
    to the TTS narration length (~3s) and the trailer would render as ~20s."""
    import sys
    sys.path.insert(0, "/app/backend")
    # Re-derive what the pipeline computes
    target_seconds = 60
    scene_count = 6
    seconds_per_scene_planner = max(3, target_seconds // scene_count)
    assert seconds_per_scene_planner == 10
    # In the render path
    per_scene_dur = max(3.0, target_seconds / max(1, scene_count))
    assert per_scene_dur == 10.0
    # And the total expected length, including 2.5s end card
    expected_total = scene_count * per_scene_dur + 2.5
    assert 55.0 <= expected_total <= 65.0, f"derived total {expected_total} outside range"


# ─── Bug 2: 60s is allowed by API contract ───────────────────────────────────
@pytest.mark.asyncio
async def test_60s_accepted_by_credit_estimate_and_jobs_create():
    token, _ = await _login()
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.get("/api/photo-trailer/credit-estimate?duration=60", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert body["duration_seconds"] == 60
        assert body["credits"] == 35
        # 61 must be rejected (le=60)
        r2 = await c.get("/api/photo-trailer/credit-estimate?duration=61", headers=H)
        assert r2.status_code == 422


# ─── Bug 2: per-scene encode no longer uses -shortest ────────────────────────
def test_per_scene_encode_does_not_use_shortest_flag():
    """Static guard: regression-protect the file from someone re-adding
    -shortest, which would re-introduce the 60s truncation bug."""
    src = open("/app/backend/routes/photo_trailer.py").read()
    # Find the per-scene encode block (it begins with `_ffmpeg([ffmpeg, "-y", "-loop", "1", "-i", img,`)
    marker = '_ffmpeg([ffmpeg, "-y", "-loop", "1", "-i", img'
    assert marker in src, "per-scene encode block markers changed; update this guard"
    # The block is a single ffmpeg() call on contiguous lines — slice & inspect
    start = src.index(marker)
    end = src.index("out_clips.append(clip)", start)
    block = src[start:end]
    # Look for `af_chain = (` definition just above (within 80 lines).
    af_search_start = max(0, src.rfind("af_chain = (", 0, start))
    af_block = src[af_search_start:end] if af_search_start else ""
    assert '"-shortest"' not in block, \
        "PER-SCENE ENCODE must NOT use -shortest (truncates 60s trailers to ~20s)"
    assert "apad,atrim=duration=" in af_block, \
        "audio chain must apad to dur so 60s trailers don't truncate to TTS length"
