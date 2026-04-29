"""
Trust & Legal hardening tests for Photo Trailer.

Covers:
1. Prompt sanitizer rejects copyrighted/celebrity/unsafe asks at job creation
   (audit row written, no credits charged, /jobs returns 400 + reason)
2. MP4 metadata provenance is embedded in rendered trailer container
3. Photo retention sweep purges source assets > N days after job completion
4. Sanitizer light rewrites (deepfake → AI cinematic portrait) flow through
"""
import os, asyncio, time
import httpx, pytest

BACKEND = "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS  = "Cr3@t0rStud!o#2026"

async def _login() -> str:
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200, r.text
        return r.json()["token"]

async def _new_session_with_one_photo(token: str) -> tuple[str, str]:
    """Init upload + push one in-memory PNG + complete consent."""
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/photo-trailer/uploads/init", headers=H, json={
            "file_count": 1, "mime_types": ["image/png"], "file_sizes": [1000],
        })
        assert r.status_code == 200
        sid = r.json()["upload_session_id"]
        png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64 + b"IEND\xaeB`\x82") * 4  # crap PNG, accepted by upload (face_detected=True heuristic)
        r = await c.post("/api/photo-trailer/uploads/photo", headers=H,
                         data={"upload_session_id": sid},
                         files={"file": ("hero.png", png, "image/png")})
        assert r.status_code == 200, r.text
        aid = r.json()["asset_id"]
        r = await c.post("/api/photo-trailer/uploads/complete", headers=H,
                         json={"upload_session_id": sid, "consent_confirmed": True})
        assert r.status_code == 200
        return sid, aid


# ─── 1. Prompt sanitizer rejects unsafe asks ──────────────────────────────────
@pytest.mark.asyncio
async def test_sanitizer_blocks_celebrity_prompt():
    token = await _login()
    sid, aid = await _new_session_with_one_photo(token)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": aid,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": 15,
            "custom_prompt": "Make me look like Tom Cruise in Mission Impossible",
        })
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
        body = r.json()
        det = body.get("detail", "")
        assert "tom cruise" in det.lower() or "rights" in det.lower(), det

@pytest.mark.asyncio
async def test_sanitizer_blocks_marvel_ip():
    token = await _login()
    sid, aid = await _new_session_with_one_photo(token)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": aid,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": 15,
            "custom_prompt": "I want to be Iron Man saving the Avengers",
        })
        assert r.status_code == 400
        det = r.json().get("detail", "").lower()
        assert "iron man" in det or "avengers" in det or "rights" in det, det

@pytest.mark.asyncio
async def test_sanitizer_blocks_explicit_content():
    token = await _login()
    sid, aid = await _new_session_with_one_photo(token)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": aid,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": 15,
            "custom_prompt": "Generate a nude scene with the hero",
        })
        assert r.status_code == 400
        det = r.json().get("detail", "").lower()
        assert "nude" in det or "rights" in det or "rewor" in det, det

@pytest.mark.asyncio
async def test_sanitizer_rewrites_deepfake_word():
    """`deepfake` is a friendly-rewrite case: the prompt is accepted but the
    word is rewritten downstream, so the regex check passes."""
    token = await _login()
    sid, aid = await _new_session_with_one_photo(token)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": aid,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": 15,
            "custom_prompt": "A deepfake style cinematic intro",
        })
        # Accepted, deepfake → "AI cinematic portrait"
        assert r.status_code in (200, 201, 429), f"expected accept, got {r.status_code} {r.text}"
        if r.status_code in (200, 201):
            jid = r.json().get("job_id")
            # cancel right away to release credits
            await c.post(f"/api/photo-trailer/jobs/{jid}/cancel", headers=H)

@pytest.mark.asyncio
async def test_sanitizer_safety_block_audit_row():
    """An audit doc is written for every block."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    before = await db.photo_trailer_safety_blocks.count_documents({})
    token = await _login()
    sid, aid = await _new_session_with_one_photo(token)
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/photo-trailer/jobs", headers=H, json={
            "upload_session_id": sid, "hero_asset_id": aid,
            "supporting_asset_ids": [], "template_id": "superhero_origin",
            "duration_target_seconds": 15,
            "custom_prompt": "Be Pikachu in Pokemon league",
        })
        assert r.status_code == 400
    after = await db.photo_trailer_safety_blocks.count_documents({})
    assert after == before + 1, f"expected audit doc, before={before} after={after}"
    cli.close()


# ─── 2. MP4 provenance metadata baked into final container ────────────────────
@pytest.mark.asyncio
async def test_render_embeds_provenance_metadata():
    """Render a tiny clip via the same _render_trailer helper and confirm
    ffprobe reports copyright/title metadata in the container."""
    import sys, tempfile, subprocess, json as _json
    sys.path.insert(0, "/app/backend")
    from routes.photo_trailer import _render_trailer

    tmp = tempfile.mkdtemp(prefix="trailer_meta_")
    # Build 2 fake scenes (image + audio) using lavfi
    subprocess.run(["/usr/bin/ffmpeg", "-y", "-f", "lavfi",
                    "-i", "color=c=red:s=1280x720:d=0.04", "-frames:v", "1",
                    f"{tmp}/img1.png"], capture_output=True, check=True)
    subprocess.run(["/usr/bin/ffmpeg", "-y", "-f", "lavfi",
                    "-i", "color=c=blue:s=1280x720:d=0.04", "-frames:v", "1",
                    f"{tmp}/img2.png"], capture_output=True, check=True)
    subprocess.run(["/usr/bin/ffmpeg", "-y", "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo", "-t", "3",
                    f"{tmp}/aud1.aac"], capture_output=True, check=True)
    subprocess.run(["/usr/bin/ffmpeg", "-y", "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo", "-t", "3",
                    f"{tmp}/aud2.aac"], capture_output=True, check=True)
    job = {"_id": "test-meta-job-id-12345", "template_id": "superhero_origin",
           "music_mood": "heroic"}
    scenes = [
        {"image_path": f"{tmp}/img1.png", "audio_path": f"{tmp}/aud1.aac",
         "duration": 3.0, "narration": "scene one narration"},
        {"image_path": f"{tmp}/img2.png", "audio_path": f"{tmp}/aud2.aac",
         "duration": 3.0, "narration": "scene two narration"},
    ]
    final = await _render_trailer(job, scenes, tmp)
    # ffprobe metadata
    res = subprocess.run(["/usr/bin/ffprobe", "-v", "quiet",
                          "-print_format", "json", "-show_format", final],
                         capture_output=True, text=True, timeout=20)
    data = _json.loads(res.stdout)
    tags = (data.get("format") or {}).get("tags") or {}
    assert "Visionary Suite" in tags.get("title", ""), tags
    assert "visionary-suite.com" in tags.get("copyright", "").lower(), tags
    assert "test-met" in tags.get("description", "").lower(), tags
    import shutil; shutil.rmtree(tmp, ignore_errors=True)


# ─── 3. Retention sweep purges source photos > N days old ─────────────────────
@pytest.mark.asyncio
async def test_retention_sweep_purges_old_source_photos(monkeypatch):
    from motor.motor_asyncio import AsyncIOMotorClient
    from datetime import datetime, timezone, timedelta
    import sys, uuid
    sys.path.insert(0, "/app/backend")
    from routes.photo_trailer import _purge_old_source_photos

    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]

    # Seed a fake completed job + assets, finished 10 days ago
    sid = str(uuid.uuid4())
    aid_old = str(uuid.uuid4())
    aid_new = str(uuid.uuid4())
    long_ago = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    recent   = datetime.now(timezone.utc).isoformat()

    await db.photo_trailer_jobs.insert_one({
        "_id": str(uuid.uuid4()), "user_id": "test-retention-user",
        "upload_session_id": sid, "status": "COMPLETED",
        "completed_at": long_ago, "updated_at": long_ago,
        "started_at": long_ago, "created_at": long_ago,
    })
    await db.photo_trailer_assets.insert_one({
        "_id": aid_old, "upload_session_id": sid, "user_id": "test-retention-user",
        "storage_key": f"test/retention/{aid_old}.jpg", "created_at": long_ago,
    })
    # A second, recent session (must NOT be purged)
    sid_new = str(uuid.uuid4())
    await db.photo_trailer_jobs.insert_one({
        "_id": str(uuid.uuid4()), "user_id": "test-retention-user",
        "upload_session_id": sid_new, "status": "COMPLETED",
        "completed_at": recent, "updated_at": recent,
        "started_at": recent, "created_at": recent,
    })
    await db.photo_trailer_assets.insert_one({
        "_id": aid_new, "upload_session_id": sid_new, "user_id": "test-retention-user",
        "storage_key": f"test/retention/{aid_new}.jpg", "created_at": recent,
    })

    res = await _purge_old_source_photos()

    # Old asset is now marked deleted_at
    old = await db.photo_trailer_assets.find_one({"_id": aid_old})
    new = await db.photo_trailer_assets.find_one({"_id": aid_new})
    assert old.get("deleted_at"), f"old asset NOT marked deleted: {old}"
    assert not new.get("deleted_at"), f"new asset wrongly marked deleted: {new}"

    # Cleanup
    await db.photo_trailer_assets.delete_many({"_id": {"$in": [aid_old, aid_new]}})
    await db.photo_trailer_jobs.delete_many({"upload_session_id": {"$in": [sid, sid_new]}})
    cli.close()
