"""Regression tests for 9:16 vertical-cut auto-pass.

Locks in the contract so the feature can't silently regress:
  • _render_vertical_from_widescreen exists and uses /usr/bin/ffmpeg
    (the build that ships drawtext, NOT /usr/local/bin/ffmpeg)
  • Pipeline writes result_vertical_video_url + result_vertical_video_key
  • /jobs/{id}/stream supports ?format=vertical and rejects bad formats
  • /share/{slug} returns vertical_video_url when available
  • Static guard: filter graph contains the blurred-bg overlay pattern
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


# ─── Static guard: helper exists, uses safe ffmpeg, has blurred-bg + drawtext ─
def test_vertical_helper_uses_correct_ffmpeg_binary():
    src = open("/app/backend/routes/photo_trailer.py").read()
    # Helper must exist exactly once (no duplicates re-introduced)
    assert src.count("async def _render_vertical_from_widescreen(") == 1, \
        "expected exactly one definition of _render_vertical_from_widescreen"
    # Slice the function body — bounded by the next top-level `async def` /
    # `def ` / `@router` so we don't accidentally pick up dead code.
    fn_start = src.index("async def _render_vertical_from_widescreen(")
    rest = src[fn_start:]
    # Find next top-level definition AFTER ours
    candidates = []
    for marker in ("\nasync def ", "\ndef ", "\n@router"):
        idx = rest.find(marker, 1)
        if idx > 0: candidates.append(idx)
    fn_end = min(candidates) if candidates else len(rest)
    block = rest[:fn_end]
    # Strip comment lines so the helpful comment that mentions
    # /usr/local/bin/ffmpeg doesn't fail the guard.
    code_only = "\n".join(
        ln for ln in block.splitlines()
        if not ln.lstrip().startswith("#")
    )
    assert '/usr/bin/ffmpeg' in code_only, "vertical helper must call /usr/bin/ffmpeg"
    assert '/usr/local/bin/ffmpeg' not in code_only, \
        "/usr/local/bin/ffmpeg has no drawtext — vertical encode will crash"
    assert "boxblur" in block, "vertical helper must apply boxblur to BG plate"
    assert "overlay=(W-w)/2:(H-h)/2" in block, "vertical helper must center-overlay FG"
    assert "scale=1080:-2" in block or "scale=1080:1920" in block, \
        "vertical helper must target 1080-width output"
    assert "Visionary Suite" in block, "vertical helper must keep brand watermark"


# ─── Static guard: pipeline calls the vertical pass + persists URL/key ────────
def test_pipeline_invokes_vertical_render_and_persists_url():
    src = open("/app/backend/routes/photo_trailer.py").read()
    assert "_render_vertical_from_widescreen(" in src, \
        "pipeline must invoke vertical render after main upload"
    assert '"result_vertical_video_url"' in src, \
        "pipeline must persist result_vertical_video_url"
    assert '"result_vertical_video_key"' in src, \
        "pipeline must persist result_vertical_video_key"
    # Vertical asset is stored on the photo_trailer_outputs row too
    assert '"vertical_video_storage_key"' in src, \
        "outputs collection must record vertical_video_storage_key"


# ─── Endpoint contract: /jobs/{id}/stream?format=vertical ─────────────────────
@pytest.mark.asyncio
async def test_stream_endpoint_supports_format_query():
    """Seed a completed job WITH a vertical asset, hit /stream both ways."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    token, uid = await _login()
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.photo_trailer_jobs.insert_one({
        "_id": job_id, "user_id": uid, "status": "COMPLETED",
        "current_stage": "COMPLETED", "progress_percent": 100,
        "template_id": "superhero_origin", "template_name": "Superhero Origin",
        "duration_target_seconds": 30,
        "result_video_url": "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/phototrailer/test/results/test.mp4",
        "result_video_key": "videos/phototrailer/test/results/test.mp4",
        "result_vertical_video_url": "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/phototrailer/test/results/test_vertical.mp4",
        "result_vertical_video_key": "videos/phototrailer/test/results/test_vertical.mp4",
        "public_share_slug": uuid.uuid4().hex[:10],
        "created_at": now, "completed_at": now, "updated_at": now,
    })
    H = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
            # Default = wide
            r = await c.get(f"/api/photo-trailer/jobs/{job_id}/stream", headers=H)
            assert r.status_code == 200
            body = r.json()
            assert body["format"] == "wide"
            assert body["has_vertical"] is True
            # ?format=vertical → vertical key signed
            r2 = await c.get(f"/api/photo-trailer/jobs/{job_id}/stream?format=vertical", headers=H)
            assert r2.status_code == 200
            b2 = r2.json()
            assert b2["format"] == "vertical"
            assert "test_vertical" in b2["url"]
            # Bad format → 422
            r3 = await c.get(f"/api/photo-trailer/jobs/{job_id}/stream?format=square", headers=H)
            assert r3.status_code == 422
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": job_id})
    cli.close()


# ─── /share/:slug returns vertical_video_url when present ─────────────────────
@pytest.mark.asyncio
async def test_share_endpoint_returns_vertical_video_url():
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    token, uid = await _login()
    job_id = str(uuid.uuid4())
    slug = uuid.uuid4().hex[:10]
    now = datetime.now(timezone.utc).isoformat()
    await db.photo_trailer_jobs.insert_one({
        "_id": job_id, "user_id": uid, "status": "COMPLETED",
        "template_id": "superhero_origin", "template_name": "Superhero Origin",
        "duration_target_seconds": 15,
        "result_video_url": "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/phototrailer/test/results/x.mp4",
        "result_video_key": "videos/phototrailer/test/results/x.mp4",
        "result_vertical_video_url": "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/phototrailer/test/results/x_vertical.mp4",
        "result_vertical_video_key": "videos/phototrailer/test/results/x_vertical.mp4",
        "public_share_slug": slug,
        "created_at": now, "completed_at": now, "updated_at": now,
    })
    try:
        async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
            r = await c.get(f"/api/photo-trailer/share/{slug}")
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["video_url"]
            assert body.get("vertical_video_url"), \
                f"share/:slug must expose vertical_video_url: {body.keys()}"
            assert "vertical" in body["vertical_video_url"]
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": job_id})
    cli.close()


# ─── /share/:slug returns null vertical when not rendered (no breakage) ───────
@pytest.mark.asyncio
async def test_share_endpoint_handles_missing_vertical_gracefully():
    """Trailers rendered before the vertical-cut feature should NOT 500;
    `vertical_video_url` should simply be null."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    token, uid = await _login()
    job_id = str(uuid.uuid4())
    slug = uuid.uuid4().hex[:10]
    now = datetime.now(timezone.utc).isoformat()
    await db.photo_trailer_jobs.insert_one({
        "_id": job_id, "user_id": uid, "status": "COMPLETED",
        "template_id": "superhero_origin", "template_name": "Superhero Origin",
        "duration_target_seconds": 15,
        "result_video_url": "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev/videos/phototrailer/test/results/x.mp4",
        "result_video_key": "videos/phototrailer/test/results/x.mp4",
        # NO vertical fields — legacy job
        "public_share_slug": slug,
        "created_at": now, "completed_at": now, "updated_at": now,
    })
    try:
        async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
            r = await c.get(f"/api/photo-trailer/share/{slug}")
            assert r.status_code == 200
            body = r.json()
            assert body["video_url"], "wide URL must still render"
            assert body.get("vertical_video_url") in (None, ""), \
                f"vertical_video_url should be None for legacy jobs, got {body.get('vertical_video_url')}"
    finally:
        await db.photo_trailer_jobs.delete_one({"_id": job_id})
    cli.close()
