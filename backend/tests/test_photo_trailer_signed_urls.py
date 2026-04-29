"""
Signed-URL gateway tests for Photo Trailer.

Acceptance criteria from founder directive:
  1. Raw bucket URL inaccessible or expires (signed URLs carry X-Amz-Expires)
  2. Owner playback works (auth-gated /jobs/{id}/stream returns signed URL)
  3. Shared trailer page works (public /share/{slug} returns signed URL)
  4. No broken existing cards (legacy jobs without `result_video_key` still
     resolve via lazy migration from `result_video_url`)
"""
import os, asyncio, uuid, time
import httpx, pytest
from datetime import datetime, timezone, timedelta

BACKEND = "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS  = "Cr3@t0rStud!o#2026"

async def _login() -> str:
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200, r.text
        return r.json()["token"]

async def _find_completed_job(token: str) -> dict:
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.get("/api/photo-trailer/my-trailers?limit=20", headers=H)
        assert r.status_code == 200
        for t in r.json().get("trailers", []):
            if t.get("status") == "COMPLETED" and (t.get("result_video_url") or t.get("result_video_key")):
                return t
    return None


# ─── 1. Owner /stream returns a fresh signed URL ──────────────────────────────
@pytest.mark.asyncio
async def test_owner_stream_endpoint_returns_signed_url():
    token = await _login()
    job = await _find_completed_job(token)
    assert job, "no completed photo trailer in DB to test against"
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.get(f"/api/photo-trailer/jobs/{job['job_id']}/stream", headers=H)
        assert r.status_code == 200, r.text
        body = r.json()
        url = body.get("url", "")
        assert url.startswith("https://"), f"expected https URL, got {url[:60]}"
        assert "X-Amz-Signature=" in url, f"expected signed URL, got {url[:120]}"
        assert "X-Amz-Expires=" in url
        assert body["expires_in"] == 600
        # Signed URL must actually serve the video
        async with httpx.AsyncClient(timeout=60.0) as dl:
            v = await dl.get(url)
            assert v.status_code == 200, f"signed URL didn't serve: {v.status_code}"
            assert len(v.content) > 100_000  # MP4 should be > 100KB
            assert v.content[:8] != b"<?xml"   # not an error page

# ─── 2. /stream auth-gated (no token = 401) ───────────────────────────────────
@pytest.mark.asyncio
async def test_stream_endpoint_requires_auth():
    token = await _login()
    job = await _find_completed_job(token)
    assert job
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.get(f"/api/photo-trailer/jobs/{job['job_id']}/stream")
        assert r.status_code in (401, 403), f"expected unauthorised, got {r.status_code}"

# ─── 3. /stream blocks other users (403/404) ──────────────────────────────────
@pytest.mark.asyncio
async def test_stream_blocks_non_owner():
    token = await _login()
    job = await _find_completed_job(token)
    assert job
    # Login as test user
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.post("/api/auth/login",
                         json={"email": "test@visionary-suite.com", "password": "Test@2026#"})
        assert r.status_code == 200, r.text
        other_token = r.json()["token"]
        H2 = {"Authorization": f"Bearer {other_token}"}
        r2 = await c.get(f"/api/photo-trailer/jobs/{job['job_id']}/stream", headers=H2)
        assert r2.status_code == 404, f"expected 404 (not found for other user), got {r2.status_code}"


# ─── 4. Public /share/{slug} returns signed URL without auth ──────────────────
@pytest.mark.asyncio
async def test_public_share_endpoint_returns_signed_url():
    token = await _login()
    job = await _find_completed_job(token)
    assert job
    slug = job.get("public_share_slug")
    assert slug, f"no slug on completed job: {job}"
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        # NO auth header — public endpoint
        r = await c.get(f"/api/photo-trailer/share/{slug}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["slug"] == slug
        assert "X-Amz-Signature=" in body["video_url"]
        assert body["expires_in"] == 600
        assert body["title"]
        assert body["creator_first_name"]

# ─── 5. /share/{slug} 404 on bad slug ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_share_unknown_slug_404():
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.get("/api/photo-trailer/share/nonexistent99")
        assert r.status_code == 404


# ─── 6. Lazy-migration: legacy job (no result_video_key) auto-derives + works ─
@pytest.mark.asyncio
async def test_legacy_job_lazy_migration():
    """Force a job to look like a pre-signed-URL row (no result_video_key)
    and verify /stream still works via _strip_public_prefix migration."""
    from motor.motor_asyncio import AsyncIOMotorClient
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    token = await _login()
    job = await _find_completed_job(token)
    assert job
    job_id = job["job_id"]
    # Strip the key field to simulate a pre-migration row
    await db.photo_trailer_jobs.update_one(
        {"_id": job_id}, {"$unset": {"result_video_key": ""}})

    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=30.0) as c:
        r = await c.get(f"/api/photo-trailer/jobs/{job_id}/stream", headers=H)
        assert r.status_code == 200, r.text
        assert "X-Amz-Signature=" in r.json()["url"]

    # Verify the migration backfilled the key
    fresh = await db.photo_trailer_jobs.find_one({"_id": job_id}, {"result_video_key": 1})
    assert fresh.get("result_video_key"), f"migration didn't backfill key: {fresh}"
    cli.close()


# ─── 7. Signed URL has bounded TTL (parsed from X-Amz-Expires) ────────────────
@pytest.mark.asyncio
async def test_signed_url_has_short_ttl():
    token = await _login()
    job = await _find_completed_job(token)
    assert job
    H = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BACKEND, timeout=15.0) as c:
        r = await c.get(f"/api/photo-trailer/jobs/{job['job_id']}/stream", headers=H)
        url = r.json()["url"]
    import re
    m = re.search(r"X-Amz-Expires=(\d+)", url)
    assert m, f"no expires param in URL: {url[:200]}"
    expires = int(m.group(1))
    # Must be ≤ 1 hour (we set 600s default — never let it accidentally rise above an hour)
    assert expires <= 3600, f"signed URL TTL too long: {expires}s"
    assert expires >= 60,   f"signed URL TTL too short: {expires}s"
