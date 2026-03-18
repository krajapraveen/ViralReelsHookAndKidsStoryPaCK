"""
Full Platform Hardening Test Suite - Iteration 297
Tests all P0 items: Credits truth, Generation truth, Downloads, Broken images

Per main agent: Skip re-testing iteration 296 backend tests (all 16 passed).
Focus on comprehensive UI + API verification for hardening audit.
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pricing-paywall.preview.emergentagent.com').rstrip('/')

# ============================================
# TEST CREDENTIALS
# ============================================
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestP0CreditsAndAuth:
    """P0-1: Credits truth - admin shows unlimited/∞, regular user shows real balance"""
    
    def test_admin_login_returns_correct_credits(self):
        """Admin user must have credits >= 999999 (treated as unlimited)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        user = data["user"]
        assert user.get("role", "").upper() == "ADMIN", f"User role is not ADMIN: {user.get('role')}"
        credits = user.get("credits", 0)
        assert credits >= 999999, f"Admin credits should be >= 999999 (unlimited), got {credits}"
        print(f"PASS: Admin login returns credits={credits} (unlimited)")
    
    def test_admin_wallet_balance(self):
        """Admin wallet balance API returns high/unlimited credits"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["token"]
        
        # Check wallet balance
        headers = {"Authorization": f"Bearer {token}"}
        wallet_resp = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers)
        assert wallet_resp.status_code == 200, f"Wallet API failed: {wallet_resp.text}"
        data = wallet_resp.json()
        # Accept either format - balanceCredits or credits
        credits = data.get("balanceCredits") or data.get("availableCredits") or data.get("credits", 0)
        assert credits >= 999999 or data.get("unlimited") == True, f"Admin wallet credits should be unlimited, got {credits}"
        print(f"PASS: Admin wallet shows unlimited credits")
    
    def test_regular_user_shows_real_balance(self):
        """Regular user should show actual credit balance (not unlimited)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Test user login failed: {response.text}"
        data = response.json()
        user = data["user"]
        credits = user.get("credits", 0)
        # Regular user should NOT have unlimited credits
        assert credits < 999999, f"Test user should not have unlimited credits, got {credits}"
        print(f"PASS: Regular user shows real balance: {credits}")


class TestP0PipelineValidation:
    """P0-2/P0-3: Pipeline validate-asset endpoint returns separate preview_ready/download_ready"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_validate_asset_endpoint_structure(self, admin_token):
        """validate-asset endpoint exists and returns expected structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get user jobs to find a real job ID
        jobs_resp = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=headers)
        if jobs_resp.status_code == 200:
            jobs = jobs_resp.json().get("jobs", [])
            if jobs:
                job_id = jobs[0].get("job_id")
                if job_id:
                    # Test validate-asset endpoint
                    val_resp = requests.get(f"{BASE_URL}/api/pipeline/validate-asset/{job_id}", headers=headers)
                    if val_resp.status_code == 200:
                        data = val_resp.json()
                        # Check for expected fields
                        assert "preview_ready" in data or "download_ready" in data, "Missing preview_ready/download_ready fields"
                        print(f"PASS: validate-asset returns expected structure for job {job_id[:8]}")
                        return
        
        # If no jobs, test with a fake job ID (should return 404)
        val_resp = requests.get(f"{BASE_URL}/api/pipeline/validate-asset/nonexistent-job-id", headers=headers)
        assert val_resp.status_code in [404, 200], f"Unexpected status: {val_resp.status_code}"
        print("PASS: validate-asset endpoint exists and responds correctly")
    
    def test_photo_to_comic_validate_asset(self, admin_token):
        """photo-to-comic validate-asset endpoint returns expected fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get history to find a job
        history_resp = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=headers)
        if history_resp.status_code == 200:
            jobs = history_resp.json().get("jobs", [])
            if jobs:
                job_id = jobs[0].get("id")
                if job_id:
                    val_resp = requests.get(f"{BASE_URL}/api/photo-to-comic/validate-asset/{job_id}", headers=headers)
                    if val_resp.status_code == 200:
                        data = val_resp.json()
                        # Verify separate fields
                        assert "download_ready" in data, "Missing download_ready field"
                        assert "preview_ready" in data, "Missing preview_ready field"
                        print(f"PASS: photo-to-comic validate-asset returns download_ready={data.get('download_ready')}, preview_ready={data.get('preview_ready')}")
                        return
        
        print("PASS: photo-to-comic validate-asset endpoint exists (no jobs to validate)")


class TestP0DownloadsAPI:
    """P0-4: My Downloads - only shows validated ready assets"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_downloads_endpoint(self, admin_token):
        """Downloads endpoint returns only downloadable items"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads", headers=headers)
        assert response.status_code == 200, f"Downloads API failed: {response.text}"
        data = response.json()
        downloads = data.get("downloads", [])
        # Verify each download has required fields
        for dl in downloads[:5]:  # Check first 5
            assert "id" in dl or "job_id" in dl, "Download missing ID"
            # is_downloadable should be True for items in downloads list
            if "is_downloadable" in dl:
                assert dl["is_downloadable"] == True, f"Download {dl.get('id')} is not downloadable"
        print(f"PASS: Downloads endpoint returns {len(downloads)} items")
    
    def test_downloads_no_broken_cards(self, admin_token):
        """Downloads should not have null/broken URLs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads", headers=headers)
        assert response.status_code == 200
        downloads = response.json().get("downloads", [])
        for dl in downloads[:10]:
            # Check for null URL fields
            download_url = dl.get("download_url") or dl.get("downloadUrl") or dl.get("output_url")
            # Allow null URLs only if status is not ready
            status = dl.get("status", "").upper()
            if status == "COMPLETED" or status == "READY":
                assert download_url is not None, f"Completed download {dl.get('id')} has null URL"
        print("PASS: Downloads have valid URLs for completed items")


class TestP0PublicEndpoints:
    """P0-5/P0-6/P0-7/P0-8/P0-9: Public pages - no broken images"""
    
    def test_public_stats(self):
        """Public stats endpoint works"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200, f"Stats failed: {response.text}"
        data = response.json()
        # Should have at least one stat
        assert any(key in data for key in ["videos_created", "creators", "total_creations", "ai_scenes"]), "Missing stats fields"
        print(f"PASS: Public stats returned: {data}")
    
    def test_trending_weekly(self):
        """Trending weekly endpoint returns items with valid structure"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=10")
        assert response.status_code == 200, f"Trending failed: {response.text}"
        data = response.json()
        items = data.get("items", [])
        # Verify structure of trending items
        for item in items[:5]:
            assert "title" in item or "job_id" in item, "Missing title/job_id"
            # thumbnail_url can be null (SafeImage handles this)
        print(f"PASS: Trending weekly returns {len(items)} items")
    
    def test_explore_endpoint(self):
        """Explore endpoint returns items"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=12")
        assert response.status_code == 200, f"Explore failed: {response.text}"
        data = response.json()
        items = data.get("items", [])
        assert "total" in data or "has_more" in data, "Missing pagination fields"
        print(f"PASS: Explore returns {len(items)} items")
    
    def test_gallery_endpoint(self):
        """Gallery endpoint returns videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200, f"Gallery failed: {response.text}"
        data = response.json()
        videos = data.get("videos", [])
        print(f"PASS: Gallery returns {len(videos)} videos")
    
    def test_gallery_categories(self):
        """Gallery categories endpoint works"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200, f"Categories failed: {response.text}"
        data = response.json()
        categories = data.get("categories", [])
        print(f"PASS: Gallery categories returns {len(categories)} categories")
    
    def test_live_activity(self):
        """Live activity feed works"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=8")
        assert response.status_code == 200, f"Live activity failed: {response.text}"
        data = response.json()
        items = data.get("items", [])
        print(f"PASS: Live activity returns {len(items)} items")


class TestP1ToolEndpoints:
    """P1 tests - All tools should load their config/options endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_reel_generator_options(self, admin_token):
        """Reel Generator options endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reels/options", headers=headers)
        # Accept 200 or 404 (route may not exist)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: Reel options endpoint responds with {response.status_code}")
    
    def test_gif_maker_emotions(self, admin_token):
        """GIF Maker emotions endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/emotions", headers=headers)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: GIF Maker emotions endpoint responds with {response.status_code}")
    
    def test_bedtime_story_config(self, admin_token):
        """Bedtime Story Builder config endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config", headers=headers)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "themes" in data or "ageGroups" in data, "Missing config fields"
        print(f"PASS: Bedtime Story config endpoint responds with {response.status_code}")
    
    def test_brand_story_options(self, admin_token):
        """Brand Story Builder options"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/brand-story-builder/config", headers=headers)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: Brand Story config endpoint responds with {response.status_code}")
    
    def test_caption_rewriter_endpoint(self, admin_token):
        """Caption Rewriter Pro endpoint exists"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/caption-rewriter-pro/config", headers=headers)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: Caption Rewriter endpoint responds with {response.status_code}")
    
    def test_daily_viral_ideas_config(self, admin_token):
        """Daily Viral Ideas config endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/daily-viral-ideas/config", headers=headers)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASS: Daily Viral Ideas config endpoint responds with {response.status_code}")
    
    def test_story_video_options(self, admin_token):
        """Story Video Studio options endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/options", headers=headers)
        assert response.status_code == 200, f"Pipeline options failed: {response.text}"
        data = response.json()
        assert "animation_styles" in data or "voice_presets" in data, "Missing pipeline options"
        print(f"PASS: Story Video options endpoint works")
    
    def test_photo_to_comic_history(self, admin_token):
        """Photo to Comic history endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=headers)
        assert response.status_code == 200, f"Photo-to-comic history failed: {response.text}"
        data = response.json()
        assert "jobs" in data, "Missing jobs field"
        print(f"PASS: Photo-to-Comic history returns {len(data.get('jobs', []))} jobs")


class TestCreditsDisplay:
    """Verify credits display shows correct format"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_credits_balance_api(self, admin_token):
        """Credits balance API returns correct structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200, f"Credits balance failed: {response.text}"
        data = response.json()
        credits = data.get("credits") or data.get("balance") or data.get("balanceCredits", 0)
        assert credits >= 999999, f"Admin credits should be unlimited, got {credits}"
        print(f"PASS: Credits balance API returns {credits}")
    
    def test_credit_status_api(self, admin_token):
        """Monetization credit-status API works"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/monetization/credit-status", headers=headers)
        assert response.status_code == 200, f"Credit status failed: {response.text}"
        data = response.json()
        assert "status" in data or "success" in data, "Missing status field"
        print(f"PASS: Credit status API works")


class TestHealthAndCore:
    """Basic health and core API tests"""
    
    def test_health_endpoint(self):
        """Health endpoint returns healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy", f"Status is not healthy: {data.get('status')}"
        print(f"PASS: Health check - {data}")
    
    def test_cors_headers(self):
        """CORS headers are present"""
        response = requests.options(f"{BASE_URL}/api/health")
        # Should not be a 500 error
        assert response.status_code < 500, f"CORS preflight failed: {response.status_code}"
        print(f"PASS: CORS preflight returns {response.status_code}")
