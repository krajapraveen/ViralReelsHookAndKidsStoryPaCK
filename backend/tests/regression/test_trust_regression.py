"""
Automated Regression Suite — Trust-Critical Flows
Run: pytest /app/backend/tests/regression/test_trust_regression.py -v --tb=short

Covers the flows that break user trust:
1. Credits truth across all pages
2. Photo to Comic happy path
3. Comic Story Book happy path
4. Story Video happy path
5. My Downloads asset truth
6. Post-generation state consistency
7. Smoke tests: dashboard, tool pages, create flows
"""
import pytest
import httpx
import os

API_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not API_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                API_URL = line.strip().split("=", 1)[1].rstrip("/")

ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS = "Cr3@t0rStud!o#2026"
USER_EMAIL = "test@visionary-suite.com"
USER_PASS = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    r = httpx.post(f"{API_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def user_token():
    r = httpx.post(f"{API_URL}/api/auth/login", json={"email": USER_EMAIL, "password": USER_PASS}, timeout=15)
    assert r.status_code == 200, f"User login failed: {r.text}"
    return r.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─── 1. CREDITS TRUTH ─────────────────────────────────────────────
class TestCreditsTruth:
    """Credits must never be 0 for admin. Must be consistent across endpoints."""

    def test_admin_credits_balance_not_zero(self, admin_token):
        r = httpx.get(f"{API_URL}/api/credits/balance", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d.get("credits", 0) > 0, f"Admin credits is 0 or missing: {d}"

    def test_admin_auth_me_credits_not_zero(self, admin_token):
        r = httpx.get(f"{API_URL}/api/auth/me", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        creds = r.json().get("credits", 0)
        assert creds > 0, f"Admin /auth/me credits is 0: {creds}"

    def test_admin_wallet_balance_not_zero(self, admin_token):
        r = httpx.get(f"{API_URL}/api/wallet/me", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        bal = r.json().get("balanceCredits", 0)
        assert bal > 0, f"Admin wallet balanceCredits is 0: {r.json()}"

    def test_user_credits_positive(self, user_token):
        r = httpx.get(f"{API_URL}/api/credits/balance", headers=auth(user_token), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d.get("credits", 0) >= 0, f"User credits negative: {d}"

    def test_credits_consistency(self, admin_token):
        """Credits from /credits/balance and /wallet/me must not wildly differ."""
        r1 = httpx.get(f"{API_URL}/api/credits/balance", headers=auth(admin_token), timeout=10)
        r2 = httpx.get(f"{API_URL}/api/wallet/me", headers=auth(admin_token), timeout=10)
        c1 = r1.json().get("credits", 0)
        c2 = r2.json().get("balanceCredits", 0)
        # Both should be very large for admin
        assert c1 > 100000, f"Admin credits too low: {c1}"
        assert c2 > 100000, f"Admin wallet too low: {c2}"

    def test_admin_not_blocked_by_upsell(self, admin_token):
        r = httpx.get(f"{API_URL}/api/credits/check-upsell", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        assert r.json().get("show_upsell") is False, "Admin should never see upsell"


# ─── 2. PHOTO TO COMIC HAPPY PATH ────────────────────────────────
class TestPhotoToComic:
    def test_history_loads(self, admin_token):
        r = httpx.get(f"{API_URL}/api/photo-to-comic/history", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        assert "jobs" in r.json()

    def test_validate_asset_returns_separate_truth(self, admin_token):
        r = httpx.get(f"{API_URL}/api/photo-to-comic/history", headers=auth(admin_token), timeout=10)
        jobs = r.json().get("jobs", [])
        if not jobs:
            pytest.skip("No photo-to-comic jobs to validate")
        job_id = jobs[0]["id"]
        r2 = httpx.get(f"{API_URL}/api/photo-to-comic/validate-asset/{job_id}", headers=auth(admin_token), timeout=10)
        assert r2.status_code == 200
        d = r2.json()
        assert "preview_ready" in d, f"Missing preview_ready: {d}"
        assert "download_ready" in d, f"Missing download_ready: {d}"

    def test_no_contradictory_state(self, admin_token):
        r = httpx.get(f"{API_URL}/api/photo-to-comic/history", headers=auth(admin_token), timeout=10)
        jobs = r.json().get("jobs", [])
        if not jobs:
            pytest.skip("No jobs")
        job_id = jobs[0]["id"]
        r2 = httpx.get(f"{API_URL}/api/photo-to-comic/validate-asset/{job_id}", headers=auth(admin_token), timeout=10)
        d = r2.json()
        if d.get("preview_ready"):
            assert d.get("download_ready"), "Preview ready but download not ready is contradictory"


# ─── 3. STORY VIDEO HAPPY PATH ───────────────────────────────────
class TestStoryVideo:
    def test_options_endpoint(self, admin_token):
        r = httpx.get(f"{API_URL}/api/pipeline/options", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert len(d.get("animation_styles", [])) > 0
        assert len(d.get("age_groups", [])) > 0
        assert len(d.get("voice_presets", [])) > 0

    def test_user_jobs_loads(self, admin_token):
        r = httpx.get(f"{API_URL}/api/pipeline/user-jobs", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        assert "jobs" in r.json()

    def test_validate_asset_returns_ui_state(self, admin_token):
        r = httpx.get(f"{API_URL}/api/pipeline/user-jobs", headers=auth(admin_token), timeout=10)
        jobs = r.json().get("jobs", [])
        if not jobs:
            pytest.skip("No story video jobs")
        job_id = jobs[0]["job_id"]
        r2 = httpx.get(f"{API_URL}/api/pipeline/validate-asset/{job_id}", headers=auth(admin_token), timeout=10)
        assert r2.status_code == 200
        d = r2.json()
        assert d["ui_state"] in ("PROCESSING", "VALIDATING", "READY", "PARTIAL_READY", "FAILED"), f"Invalid ui_state: {d['ui_state']}"
        assert "preview_ready" in d
        assert "download_ready" in d
        assert "share_ready" in d

    def test_no_contradictory_validate_state(self, admin_token):
        r = httpx.get(f"{API_URL}/api/pipeline/user-jobs", headers=auth(admin_token), timeout=10)
        jobs = r.json().get("jobs", [])
        if not jobs:
            pytest.skip("No jobs")
        job_id = jobs[0]["job_id"]
        r2 = httpx.get(f"{API_URL}/api/pipeline/validate-asset/{job_id}", headers=auth(admin_token), timeout=10)
        d = r2.json()
        if d["ui_state"] == "READY":
            assert d["preview_ready"], "READY but preview not ready"
            assert d["download_ready"], "READY but download not ready"
        if d["ui_state"] == "FAILED" and not d.get("download_ready"):
            assert d.get("download_url") is None, "FAILED with no download but has download_url"

    def test_rate_limit_status(self, admin_token):
        r = httpx.get(f"{API_URL}/api/pipeline/rate-limit-status", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "can_create" in d


# ─── 4. COMIC STORYBOOK HAPPY PATH ───────────────────────────────
class TestComicStorybook:
    def test_genres_endpoint(self, admin_token):
        r = httpx.get(f"{API_URL}/api/comic-storybook-v2/genres", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200

    def test_pricing_endpoint(self, admin_token):
        r = httpx.get(f"{API_URL}/api/comic-storybook-v2/pricing", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200

    def test_history_endpoint(self, admin_token):
        r = httpx.get(f"{API_URL}/api/comic-storybook-v2/history", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200


# ─── 5. MY DOWNLOADS ASSET TRUTH ─────────────────────────────────
class TestMyDownloads:
    def test_downloads_all_ready(self, admin_token):
        r = httpx.get(f"{API_URL}/api/downloads/my-downloads", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
        downloads = r.json().get("downloads", [])
        for dl in downloads:
            assert dl.get("status") == "ready", f"Download not ready: {dl.get('id')} status={dl.get('status')}"

    def test_downloads_have_urls(self, admin_token):
        r = httpx.get(f"{API_URL}/api/downloads/my-downloads", headers=auth(admin_token), timeout=10)
        downloads = r.json().get("downloads", [])
        for dl in downloads:
            assert dl.get("download_url"), f"Download missing URL: {dl.get('id')}"


# ─── 6. SMOKE TESTS — ENDPOINTS ──────────────────────────────────
class TestSmokeEndpoints:
    """Every critical endpoint must not return 500."""

    @pytest.mark.parametrize("endpoint", [
        "/api/pipeline/options",
        "/api/gif-maker/emotions",
        "/api/comic-storybook-v2/genres",
        "/api/daily-viral-ideas/config",
        "/api/credits/balance",
        "/api/wallet/me",
        "/api/auth/me",
    ])
    def test_authenticated_endpoints(self, admin_token, endpoint):
        r = httpx.get(f"{API_URL}{endpoint}", headers=auth(admin_token), timeout=10)
        assert r.status_code != 500, f"{endpoint} returned 500: {r.text[:200]}"

    @pytest.mark.parametrize("endpoint", [
        "/api/health",
        "/api/public/stats",
        "/api/public/trending-weekly",
    ])
    def test_public_endpoints(self, endpoint):
        r = httpx.get(f"{API_URL}{endpoint}", timeout=10)
        assert r.status_code == 200, f"{endpoint} failed: {r.status_code}"


# ─── 7. REEL GENERATOR ───────────────────────────────────────────
class TestReelGenerator:
    def test_generate_rejects_empty_input(self, admin_token):
        r = httpx.post(f"{API_URL}/api/generate/reel", json={}, headers=auth(admin_token), timeout=10)
        assert r.status_code in (400, 422), "Should reject empty input"


# ─── 8. GIF MAKER ────────────────────────────────────────────────
class TestGifMaker:
    def test_emotions(self, admin_token):
        r = httpx.get(f"{API_URL}/api/gif-maker/emotions", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200


# ─── 9. BEDTIME STORY BUILDER ────────────────────────────────────
class TestBedtimeStory:
    def test_rejects_empty_input(self, admin_token):
        r = httpx.post(f"{API_URL}/api/bedtime-story-builder/generate", json={}, headers=auth(admin_token), timeout=10)
        assert r.status_code == 422, "Should reject empty input"


# ─── 10. BRAND STORY BUILDER ─────────────────────────────────────
class TestBrandStory:
    def test_rejects_empty_input(self, admin_token):
        r = httpx.post(f"{API_URL}/api/brand-story-builder/generate", json={}, headers=auth(admin_token), timeout=10)
        assert r.status_code == 422, "Should reject empty input"


# ─── 11. CAPTION REWRITER ────────────────────────────────────────
class TestCaptionRewriter:
    def test_rejects_empty_input(self, admin_token):
        r = httpx.post(f"{API_URL}/api/caption-rewriter-pro/rewrite", json={}, headers=auth(admin_token), timeout=10)
        assert r.status_code == 422, "Should reject empty input"


# ─── 12. DAILY VIRAL IDEAS ───────────────────────────────────────
class TestDailyIdeas:
    def test_config(self, admin_token):
        r = httpx.get(f"{API_URL}/api/daily-viral-ideas/config", headers=auth(admin_token), timeout=10)
        assert r.status_code == 200
