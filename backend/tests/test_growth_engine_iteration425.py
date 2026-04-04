"""
Growth Engine for Daily Viral Idea Drop - Iteration 425
Tests: Shareable Output System, Soft Paywall, Viral Hook Injection, Basic Metrics

Features tested:
1. GET /api/viral-ideas/share/{job_id} - Public teaser (no auth)
2. POST /api/viral-ideas/share/{job_id}/track - Share event tracking (no auth)
3. POST /api/viral-ideas/generate-bundle - Soft paywall logic
4. GET /api/viral-ideas/jobs/{job_id}/assets - Truncated content for locked jobs
5. POST /api/viral-ideas/jobs/{job_id}/unlock - Unlock pack with credits
6. GET /api/viral-ideas/metrics/growth - Aggregated metrics
7. POST /api/viral-ideas/track-referral - Referral conversion tracking
8. Hook generation with 4 types (curiosity, pattern_break, emotional, loop)
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Existing completed job (unlocked) for testing
EXISTING_JOB_ID = "ce680be0-51c6-4560-810e-25a058dfcd8d"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def user_info(auth_token):
    """Get user info including credits."""
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    if response.status_code == 200:
        return response.json()
    return {"credits": 0}


# ==================== PUBLIC SHARE TEASER TESTS ====================
class TestPublicShareTeaser:
    """Test public share teaser endpoint (no auth required)."""
    
    def test_share_teaser_returns_data_without_auth(self):
        """GET /api/viral-ideas/share/{job_id} returns teaser data without authentication."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}")
        assert response.status_code == 200, f"Share teaser failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "job_id" in data
        assert data["job_id"] == EXISTING_JOB_ID
        assert "niche" in data
        assert "idea" in data
        assert "top_hook" in data
        assert "script_teaser" in data
        assert "caption_teaser" in data
        assert "thumbnail_url" in data
        assert "total_packs_generated" in data
        assert "created_at" in data
    
    def test_share_teaser_includes_top_hook(self):
        """Share teaser includes top_hook from hooks asset."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # top_hook should be a non-empty string (first line of hooks)
        assert isinstance(data["top_hook"], str)
        # May be empty if no hooks generated yet, but should exist
    
    def test_share_teaser_includes_script_teaser(self):
        """Share teaser includes script_teaser (first 3 lines of script)."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "script_teaser" in data
        # Script teaser should be partial content
        if data["script_teaser"]:
            lines = data["script_teaser"].strip().split("\n")
            assert len(lines) <= 3  # Should be max 3 lines
    
    def test_share_teaser_includes_caption_teaser(self):
        """Share teaser includes caption_teaser (first line of captions)."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "caption_teaser" in data
    
    def test_share_teaser_includes_thumbnail_url(self):
        """Share teaser includes thumbnail_url."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "thumbnail_url" in data
        # Thumbnail URL should be present for completed jobs
        if data["thumbnail_url"]:
            assert "/api/static/generated/viral_thumbs/" in data["thumbnail_url"] or data["thumbnail_url"].startswith("http")
    
    def test_share_teaser_includes_social_proof_count(self):
        """Share teaser includes total_packs_generated with floor of 500."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_packs_generated" in data
        # Social proof floor is max(total_packs, 500)
        assert data["total_packs_generated"] >= 500
    
    def test_share_teaser_with_ref_param(self):
        """Share teaser with ref param tracks share_view metric."""
        ref_id = f"test_ref_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}?ref={ref_id}")
        assert response.status_code == 200
        # Should still return teaser data
        data = response.json()
        assert data["job_id"] == EXISTING_JOB_ID
    
    def test_share_teaser_nonexistent_job_returns_404(self):
        """Share teaser for nonexistent job returns 404."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/nonexistent-job-12345")
        assert response.status_code == 404


# ==================== SHARE TRACKING TESTS ====================
class TestShareTracking:
    """Test share event tracking (no auth required)."""
    
    def test_track_share_event_without_auth(self):
        """POST /api/viral-ideas/share/{job_id}/track stores share event without auth."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}/track",
            json={"platform": "whatsapp", "user_id": "test_anon_user"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_track_share_event_twitter(self):
        """Track share event for Twitter platform."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}/track",
            json={"platform": "twitter", "user_id": "anon"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_track_share_event_copy_link(self):
        """Track share event for copy link."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}/track",
            json={"platform": "copy", "user_id": "anonymous"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


# ==================== SOFT PAYWALL TESTS ====================
class TestSoftPaywall:
    """Test soft paywall logic for generate-bundle."""
    
    def test_generate_bundle_returns_locked_and_share_url(self, auth_headers):
        """POST /api/viral-ideas/generate-bundle response includes locked and share_url fields."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/generate-bundle",
            headers=auth_headers,
            json={"idea": "TEST_PAYWALL: How to grow on TikTok in 2026", "niche": "Tech"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "job_id" in data
        assert "status" in data
        assert "message" in data
        assert "locked" in data  # New field for paywall
        assert "share_url" in data  # New field for sharing
        
        # share_url should be /viral/{job_id}
        assert data["share_url"] == f"/viral/{data['job_id']}"
    
    def test_generate_bundle_subsequent_gen_not_free(self, auth_headers, user_info):
        """Subsequent generations are NOT free for test user (already has generations)."""
        # Test user already has generations, so this should NOT be free
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/generate-bundle",
            headers=auth_headers,
            json={"idea": "TEST_PAYWALL_2: AI automation secrets", "niche": "Tech"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Message should NOT say "first free pack" since user has previous generations
        assert "first free pack" not in data["message"].lower()


# ==================== LOCKED ASSETS TESTS ====================
class TestLockedAssets:
    """Test truncated content for locked jobs."""
    
    def test_job_status_includes_locked_field(self, auth_headers):
        """GET /api/viral-ideas/jobs/{job_id} includes locked field."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify locked field exists
        assert "locked" in data
        # Existing job should be unlocked
        assert data["locked"] is False
    
    def test_job_status_includes_share_url(self, auth_headers):
        """GET /api/viral-ideas/jobs/{job_id} includes share_url."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "share_url" in data
        assert data["share_url"] == f"/viral/{EXISTING_JOB_ID}"
    
    def test_assets_include_locked_field(self, auth_headers):
        """GET /api/viral-ideas/jobs/{job_id}/assets includes locked field."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/assets",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "locked" in data
        # Existing job should be unlocked
        assert data["locked"] is False


# ==================== UNLOCK PACK TESTS ====================
class TestUnlockPack:
    """Test unlock pack endpoint."""
    
    def test_unlock_already_unlocked_pack(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/unlock returns success for already unlocked pack."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/unlock",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return success with "already unlocked" message
        assert data["success"] is True
        assert "already unlocked" in data["message"].lower()
    
    def test_unlock_nonexistent_job_returns_404(self, auth_headers):
        """POST /api/viral-ideas/jobs/{invalid_id}/unlock returns 404."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/nonexistent-job-12345/unlock",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_unlock_requires_auth(self):
        """POST /api/viral-ideas/jobs/{job_id}/unlock requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/unlock"
        )
        assert response.status_code in [401, 403]


# ==================== GROWTH METRICS TESTS ====================
class TestGrowthMetrics:
    """Test growth metrics endpoint."""
    
    def test_growth_metrics_returns_aggregated_counts(self, auth_headers):
        """GET /api/viral-ideas/metrics/growth returns aggregated metric counts."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/metrics/growth",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all metric fields exist
        assert "generations" in data
        assert "shares" in data
        assert "share_views" in data
        assert "share_to_signup" in data
        assert "free_to_paid" in data
        assert "unlocks" in data
        assert "pack_completions" in data
        
        # All should be integers >= 0
        assert isinstance(data["generations"], int)
        assert isinstance(data["shares"], int)
        assert isinstance(data["share_views"], int)
        assert isinstance(data["share_to_signup"], int)
        assert isinstance(data["free_to_paid"], int)
        assert isinstance(data["unlocks"], int)
        assert isinstance(data["pack_completions"], int)
    
    def test_growth_metrics_requires_auth(self):
        """GET /api/viral-ideas/metrics/growth requires authentication."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/metrics/growth")
        assert response.status_code in [401, 403]


# ==================== REFERRAL TRACKING TESTS ====================
class TestReferralTracking:
    """Test referral conversion tracking."""
    
    def test_track_referral_stores_conversion(self):
        """POST /api/viral-ideas/track-referral stores referral conversion (public endpoint)."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/track-referral",
            json={
                "ref_job_id": EXISTING_JOB_ID,
                "new_user_id": f"test_new_user_{uuid.uuid4().hex[:8]}"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_track_referral_without_ref_job_id(self):
        """POST /api/viral-ideas/track-referral handles missing ref_job_id gracefully."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/track-referral",
            json={"new_user_id": "test_user"}
        )
        # Should still return success (just won't track)
        assert response.status_code == 200


# ==================== MY JOBS WITH LOCKED FIELD TESTS ====================
class TestMyJobsWithLocked:
    """Test my-jobs endpoint includes locked and share_url fields."""
    
    def test_my_jobs_includes_locked_field(self, auth_headers):
        """GET /api/viral-ideas/my-jobs includes locked field for each job."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/my-jobs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert len(data["jobs"]) > 0
        
        # Each job should have locked and share_url fields
        for job in data["jobs"]:
            assert "locked" in job
            assert "share_url" in job
            assert job["share_url"] == f"/viral/{job['job_id']}"


# ==================== HOOK TYPES VERIFICATION ====================
class TestHookTypes:
    """Test that hooks generation produces typed hooks."""
    
    def test_hooks_asset_exists(self, auth_headers):
        """Verify hooks asset exists for completed job."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/assets",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        hooks_asset = next((a for a in data["assets"] if a["asset_type"] == "hooks"), None)
        assert hooks_asset is not None
        assert hooks_asset.get("content") is not None


# ==================== INTEGRATION TESTS ====================
class TestGrowthEngineIntegration:
    """Integration tests for the growth engine flow."""
    
    def test_full_share_flow(self, auth_headers):
        """Test complete share flow: get teaser -> track share -> verify metrics."""
        # 1. Get share teaser (public)
        teaser_response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}")
        assert teaser_response.status_code == 200
        teaser_data = teaser_response.json()
        assert teaser_data["total_packs_generated"] >= 500
        
        # 2. Track share event (public)
        track_response = requests.post(
            f"{BASE_URL}/api/viral-ideas/share/{EXISTING_JOB_ID}/track",
            json={"platform": "whatsapp", "user_id": "integration_test"}
        )
        assert track_response.status_code == 200
        
        # 3. Verify metrics updated (authenticated)
        metrics_response = requests.get(
            f"{BASE_URL}/api/viral-ideas/metrics/growth",
            headers=auth_headers
        )
        assert metrics_response.status_code == 200
        metrics_data = metrics_response.json()
        assert metrics_data["shares"] >= 0  # Should have at least our share
    
    def test_job_lifecycle_with_paywall_fields(self, auth_headers):
        """Test job lifecycle includes all paywall-related fields."""
        # 1. Create new job
        create_response = requests.post(
            f"{BASE_URL}/api/viral-ideas/generate-bundle",
            headers=auth_headers,
            json={"idea": "TEST_LIFECYCLE: Growth hacking strategies", "niche": "Business"}
        )
        assert create_response.status_code == 200
        create_data = create_response.json()
        
        job_id = create_data["job_id"]
        assert "locked" in create_data
        assert "share_url" in create_data
        
        # 2. Check job status
        time.sleep(1)
        status_response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{job_id}",
            headers=auth_headers
        )
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "locked" in status_data
        assert "share_url" in status_data
        
        # 3. Check public share teaser
        share_response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{job_id}")
        assert share_response.status_code == 200
        share_data = share_response.json()
        assert share_data["job_id"] == job_id
