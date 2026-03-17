"""
Iteration 265: Fallback Pipeline System Tests
Tests for Story → Video fallback output system:
- GET /api/pipeline/preview/{job_id} - Public preview data
- GET /api/pipeline/assets/{job_id} - Individual asset links (auth required)
- POST /api/pipeline/notify-when-ready/{job_id} - Subscribe for notification
- POST /api/pipeline/generate-fallback/{job_id} - Manual fallback trigger
- GET /api/pipeline/status/{job_id} - Now includes fallback data
- GET /api/cashfree/products with x-country headers - Geo-IP currency detection
- Admin panel regression tests
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://comic-pipeline-v2.preview.emergentagent.com')

# Test jobs provided with fallback data
JOB_WITH_FALLBACK_VIDEO = "d870c412-dc39-4400-ab0e-f3a43a514182"
JOB_WITH_STORY_PACK = "b2fe2b5d-57ce-49bc-9751-4cb1ae05492b"

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200 and resp.json().get("token"):
        return resp.json()["token"]
    pytest.skip("Admin login failed")


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user authentication token."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if resp.status_code == 200 and resp.json().get("token"):
        return resp.json()["token"]
    pytest.skip("Test user login failed")


class TestFallbackPipelinePreview:
    """Tests for GET /api/pipeline/preview/{job_id} - Public preview endpoint"""
    
    def test_preview_job_with_fallback_video(self):
        """Test preview endpoint returns full scene data for job with fallback video."""
        resp = requests.get(f"{BASE_URL}/api/pipeline/preview/{JOB_WITH_FALLBACK_VIDEO}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("success") == True
        assert "preview" in data
        
        preview = data["preview"]
        assert preview.get("job_id") == JOB_WITH_FALLBACK_VIDEO
        assert preview.get("status") == "PARTIAL"
        assert "scenes" in preview
        assert isinstance(preview["scenes"], list)
        assert len(preview["scenes"]) > 0
        
        # Check scene structure
        scene = preview["scenes"][0]
        assert "scene_number" in scene
        assert "title" in scene
        assert "narration_text" in scene
        assert "image_url" in scene
        assert "audio_url" in scene
        assert "has_image" in scene
        assert "has_audio" in scene
        
        # Verify fallback URLs are provided
        assert preview.get("fallback_video_url") is not None, "Expected fallback_video_url in preview"
        assert preview.get("story_pack_url") is not None, "Expected story_pack_url in preview"
    
    def test_preview_job_with_story_pack_only(self):
        """Test preview endpoint for job with story pack (no fallback video)."""
        resp = requests.get(f"{BASE_URL}/api/pipeline/preview/{JOB_WITH_STORY_PACK}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("success") == True
        preview = data["preview"]
        assert preview.get("status") == "PARTIAL"
        assert len(preview.get("scenes", [])) > 0
    
    def test_preview_invalid_job(self):
        """Test preview returns 404 for non-existent job."""
        resp = requests.get(f"{BASE_URL}/api/pipeline/preview/invalid-job-id-12345")
        assert resp.status_code == 404


class TestFallbackPipelineAssets:
    """Tests for GET /api/pipeline/assets/{job_id} - Auth required asset links"""
    
    def test_assets_returns_individual_links(self, admin_token):
        """Test assets endpoint returns presigned URLs for all individual files."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/pipeline/assets/{JOB_WITH_FALLBACK_VIDEO}", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("success") == True
        assert "assets" in data
        
        assets = data["assets"]
        assert assets.get("job_id") == JOB_WITH_FALLBACK_VIDEO
        
        # Check images dict
        assert "images" in assets
        assert isinstance(assets["images"], dict)
        assert len(assets["images"]) > 0
        
        # Check audio dict
        assert "audio" in assets
        assert isinstance(assets["audio"], dict)
        assert len(assets["audio"]) > 0
        
        # Check fallback URLs
        assert assets.get("fallback_video") is not None, "Expected fallback_video URL"
        assert assets.get("story_pack_zip") is not None, "Expected story_pack_zip URL"
        
        # Verify URLs are presigned (contain signature params)
        for scene_num, url in assets["images"].items():
            assert "X-Amz-Signature" in url, f"Image {scene_num} URL should be presigned"
    
    def test_assets_unauthorized(self):
        """Test assets endpoint returns 401 without auth."""
        resp = requests.get(f"{BASE_URL}/api/pipeline/assets/{JOB_WITH_FALLBACK_VIDEO}")
        assert resp.status_code == 401
    
    def test_assets_wrong_user(self, test_user_token):
        """Test assets returns 403 for user who doesn't own the job."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        resp = requests.get(f"{BASE_URL}/api/pipeline/assets/{JOB_WITH_FALLBACK_VIDEO}", headers=headers)
        assert resp.status_code == 403


class TestPipelineStatusWithFallback:
    """Tests for GET /api/pipeline/status/{job_id} - Now includes fallback data"""
    
    def test_status_includes_fallback_data(self, admin_token):
        """Test status endpoint includes fallback data in response."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/pipeline/status/{JOB_WITH_FALLBACK_VIDEO}", headers=headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("success") == True
        job = data.get("job", {})
        
        assert job.get("status") == "PARTIAL"
        assert "fallback" in job, "Status should include fallback key"
        
        fallback = job["fallback"]
        assert fallback is not None
        assert fallback.get("status") in ["fallback_video", "story_pack", "preview_only", "none"]
        
        # Should have fallback video URL
        if job["status"] == "PARTIAL":
            assert fallback.get("fallback_video_url") is not None or fallback.get("story_pack_url") is not None


class TestNotifyWhenReady:
    """Tests for POST /api/pipeline/notify-when-ready/{job_id}"""
    
    def test_notify_already_done(self, admin_token):
        """Test notify returns immediately if job is already complete/partial."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.post(
            f"{BASE_URL}/api/pipeline/notify-when-ready/{JOB_WITH_FALLBACK_VIDEO}",
            headers=headers
        )
        # Should return 200 with already_done flag since job is PARTIAL
        assert resp.status_code in [200, 403], f"Got {resp.status_code}: {resp.text}"
        
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("success") == True
            # Job is already PARTIAL so should indicate already done
            assert data.get("already_done") == True or "completed" in data.get("message", "").lower()
    
    def test_notify_unauthorized(self):
        """Test notify returns 401 without auth."""
        resp = requests.post(f"{BASE_URL}/api/pipeline/notify-when-ready/{JOB_WITH_FALLBACK_VIDEO}")
        assert resp.status_code == 401


class TestGeoIPCurrencyDetection:
    """Tests for Geo-IP currency detection on Cashfree products endpoint"""
    
    def test_products_usd_for_us_header(self):
        """Test products endpoint returns USD pricing for US country header."""
        headers = {"x-country": "US"}
        resp = requests.get(f"{BASE_URL}/api/cashfree/products", headers=headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("detectedCurrency") == "USD"
        assert data.get("symbol") == "$"
        
        # Check products have USD pricing
        products = data.get("products", {})
        assert len(products) > 0
        
        for pid, product in products.items():
            assert product.get("displayCurrency") == "USD"
            assert product.get("displaySymbol") == "$"
            # displayPrice should be USD value (priceUsd)
            assert product.get("displayPrice") == product.get("priceUsd")
    
    def test_products_inr_for_in_header(self):
        """Test products endpoint returns INR pricing for IN country header."""
        headers = {"x-country": "IN"}
        resp = requests.get(f"{BASE_URL}/api/cashfree/products", headers=headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("detectedCurrency") == "INR"
        assert data.get("symbol") == "₹"
        
        # Check products have INR pricing
        products = data.get("products", {})
        for pid, product in products.items():
            assert product.get("displayCurrency") == "INR"
            assert product.get("displaySymbol") == "₹"
            # displayPrice should be INR value (price)
            assert product.get("displayPrice") == product.get("price")
    
    def test_products_default_usd(self):
        """Test products endpoint defaults to USD when no country header."""
        resp = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert resp.status_code == 200
        
        data = resp.json()
        # Should default to USD
        assert data.get("detectedCurrency") == "USD"
        assert data.get("symbol") == "$"


class TestAdminPanelRegression:
    """Regression tests for admin panel endpoints"""
    
    def test_admin_users_list(self, admin_token):
        """Test admin users list endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/users/list", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
    
    def test_admin_analytics_dashboard(self, admin_token):
        """Test admin analytics dashboard endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard?days=7", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") == True
    
    def test_admin_login_activity(self, admin_token):
        """Test admin login activity endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/login-activity", headers=headers)
        assert resp.status_code == 200
    
    def test_admin_system_health(self, admin_token):
        """Test admin system health endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/system/system-health", headers=headers)
        assert resp.status_code == 200
    
    def test_admin_audit_logs(self, admin_token):
        """Test admin audit logs endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/admin/audit-logs/logs", headers=headers)
        assert resp.status_code == 200


class TestGalleryShowcaseHandling:
    """Tests for Gallery handling showcase items without video URL"""
    
    def test_gallery_public_endpoint(self):
        """Test gallery public endpoint returns videos and showcases."""
        resp = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert resp.status_code == 200
        data = resp.json()
        assert "videos" in data
        assert isinstance(data["videos"], list)
    
    def test_gallery_categories(self):
        """Test gallery categories endpoint."""
        resp = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data
    
    def test_gallery_leaderboard(self):
        """Test gallery leaderboard endpoint."""
        resp = requests.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "leaderboard" in data
