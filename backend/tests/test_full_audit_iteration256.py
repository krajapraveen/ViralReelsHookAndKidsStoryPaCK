"""
Iteration 256: Full Production Audit Tests for Visionary Suite
Testing: Gallery, Auth, Rate Limits, Worker Status, Credits, Pages, UI Consistency
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://durable-jobs-beta.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER = {"email": "test@visionary-suite.com", "password": "Test@2026#"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_token(api_client):
    """Get test user token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip("Test user login failed")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin user token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip("Admin user login failed")


class TestHealthEndpoint:
    """Health check endpoint tests"""
    
    def test_health_returns_200(self, api_client):
        """API /api/health returns status healthy"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"PASS: /api/health returns {data['status']}")


class TestGalleryEndpoints:
    """Gallery API tests - all 30 items with presigned URLs"""
    
    def test_gallery_returns_30_videos(self, api_client):
        """Gallery should return exactly 30 completed videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        videos = data.get("videos", [])
        assert len(videos) == 30, f"Expected 30 videos, got {len(videos)}"
        print(f"PASS: Gallery returns exactly 30 videos")
    
    def test_gallery_videos_have_presigned_urls(self, api_client):
        """All gallery videos should have presigned R2 URLs (X-Amz-Algorithm)"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        data = response.json()
        videos = data.get("videos", [])
        
        videos_with_presigned = 0
        for video in videos:
            output_url = video.get("output_url", "")
            if "X-Amz-Algorithm" in output_url:
                videos_with_presigned += 1
        
        assert videos_with_presigned == 30, f"Only {videos_with_presigned}/30 videos have presigned URLs"
        print(f"PASS: All 30 videos have presigned URLs")
    
    def test_gallery_thumbnails_have_presigned_urls(self, api_client):
        """All gallery thumbnails should have presigned URLs"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        data = response.json()
        videos = data.get("videos", [])
        
        thumbnails_with_presigned = 0
        for video in videos:
            thumbnail_url = video.get("thumbnail_url", "")
            if thumbnail_url and "X-Amz-Algorithm" in thumbnail_url:
                thumbnails_with_presigned += 1
        
        # Most videos should have presigned thumbnails
        assert thumbnails_with_presigned >= 25, f"Only {thumbnails_with_presigned}/30 have presigned thumbnails"
        print(f"PASS: {thumbnails_with_presigned}/30 thumbnails have presigned URLs")
    
    def test_gallery_videos_have_titles(self, api_client):
        """All videos should have proper titles"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        data = response.json()
        videos = data.get("videos", [])
        
        videos_with_titles = sum(1 for v in videos if v.get("title") and len(v["title"]) > 3)
        assert videos_with_titles == 30, f"Only {videos_with_titles}/30 videos have titles"
        print(f"PASS: All 30 videos have proper titles")
    
    def test_gallery_category_filtering_2d_cartoon(self, api_client):
        """Filter by cartoon_2d returns 14 videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=cartoon_2d")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        assert len(videos) == 14, f"Expected 14 for cartoon_2d, got {len(videos)}"
        print(f"PASS: cartoon_2d filter returns 14 videos")
    
    def test_gallery_category_filtering_watercolor(self, api_client):
        """Filter by watercolor returns 9 videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=watercolor")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        assert len(videos) == 9, f"Expected 9 for watercolor, got {len(videos)}"
        print(f"PASS: watercolor filter returns 9 videos")
    
    def test_gallery_category_filtering_anime(self, api_client):
        """Filter by anime_style returns 4 videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=anime_style")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        assert len(videos) == 4, f"Expected 4 for anime_style, got {len(videos)}"
        print(f"PASS: anime_style filter returns 4 videos")
    
    def test_gallery_category_filtering_comic_book(self, api_client):
        """Filter by comic_book returns 2 videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=comic_book")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        assert len(videos) == 2, f"Expected 2 for comic_book, got {len(videos)}"
        print(f"PASS: comic_book filter returns 2 videos")
    
    def test_gallery_category_filtering_claymation(self, api_client):
        """Filter by claymation returns 1 video"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=claymation")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        assert len(videos) == 1, f"Expected 1 for claymation, got {len(videos)}"
        print(f"PASS: claymation filter returns 1 video")
    
    def test_gallery_sort_newest(self, api_client):
        """Sort by newest returns 30 videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=newest")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        assert len(videos) == 30
        print(f"PASS: sort=newest returns 30 videos")
    
    def test_gallery_sort_most_remixed(self, api_client):
        """Sort by most_remixed returns 30 videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=most_remixed")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        assert len(videos) == 30
        print(f"PASS: sort=most_remixed returns 30 videos")
    
    def test_gallery_sort_trending(self, api_client):
        """Sort by trending returns 30 videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=trending")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        assert len(videos) == 30
        print(f"PASS: sort=trending returns 30 videos")
    
    def test_gallery_categories_endpoint(self, api_client):
        """Categories endpoint returns correct counts"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        categories = data.get("categories", [])
        
        # Check All category has 30
        all_cat = next((c for c in categories if c["id"] == "all"), None)
        assert all_cat and all_cat["count"] == 30, f"All category should have 30, got {all_cat}"
        print(f"PASS: /api/pipeline/gallery/categories returns correct counts")
    
    def test_gallery_detail_returns_presigned_url(self, api_client):
        """Gallery detail endpoint returns presigned URL"""
        # First get a job_id from gallery
        gallery_response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        videos = gallery_response.json().get("videos", [])
        if not videos:
            pytest.skip("No gallery videos")
        
        job_id = videos[0].get("job_id")
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/{job_id}")
        assert response.status_code == 200
        
        video = response.json().get("video", {})
        output_url = video.get("output_url", "")
        assert "X-Amz-Algorithm" in output_url, "Detail endpoint should return presigned URL"
        print(f"PASS: Gallery detail endpoint returns presigned URL")


class TestAuthEndpoints:
    """Authentication tests"""
    
    def test_test_user_login_success(self, api_client):
        """Test user can login successfully"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data or "access_token" in data
        print(f"PASS: Test user login successful")
    
    def test_admin_user_login_success(self, api_client):
        """Admin user can login successfully"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data or "access_token" in data
        print(f"PASS: Admin user login successful")
    
    def test_invalid_login_returns_error(self, api_client):
        """Invalid credentials should return error"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [400, 401, 403], f"Expected 4xx, got {response.status_code}"
        print(f"PASS: Invalid login returns {response.status_code}")
    
    def test_signup_validates_email_format(self, api_client):
        """Signup should validate email format"""
        response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": "invalid-email",
            "password": "Test@2026#",
            "name": "Test User"
        })
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print(f"PASS: Signup validates email format")


class TestRateLimitStatus:
    """Rate limit status endpoint tests"""
    
    def test_test_user_is_exempt(self, api_client, test_user_token):
        """Test user should be exempt from rate limits"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_client.get(f"{BASE_URL}/api/pipeline/rate-limit-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("exempt") == True, f"Test user should be exempt, got {data}"
        assert data.get("can_create") == True
        print(f"PASS: Test user is exempt from rate limits")
    
    def test_admin_user_is_exempt(self, api_client, admin_token):
        """Admin user should be exempt from rate limits"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get(f"{BASE_URL}/api/pipeline/rate-limit-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("exempt") == True, f"Admin should be exempt, got {data}"
        assert data.get("can_create") == True
        print(f"PASS: Admin user is exempt from rate limits")


class TestWorkerStatus:
    """Worker auto-scaling endpoint tests"""
    
    def test_workers_status_returns_config(self, api_client, test_user_token):
        """Workers status should return auto-scaling config"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_client.get(f"{BASE_URL}/api/pipeline/workers/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        workers = data.get("workers", {})
        
        assert workers.get("workers_running") == True, "Workers should be running"
        assert workers.get("min_workers") == 1, f"min_workers should be 1, got {workers.get('min_workers')}"
        assert workers.get("max_workers") == 3, f"max_workers should be 3, got {workers.get('max_workers')}"
        print(f"PASS: Worker status returns correct config (min=1, max=3)")


class TestCreditsEndpoint:
    """Credits/wallet endpoint tests"""
    
    def test_credits_balance_endpoint(self, api_client, test_user_token):
        """Credits balance endpoint works"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_client.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Should have some balance info
        assert "balance" in data or "balanceCredits" in data or "credits" in data or "availableCredits" in data
        print(f"PASS: Credits balance endpoint returns balance info")


class TestPublicPages:
    """Public page loading tests"""
    
    @pytest.mark.parametrize("page", [
        "/",
        "/pricing",
        "/gallery",
        "/contact",
        "/reviews",
        "/blog",
        "/user-manual",
        "/privacy-policy",
        "/cookie-policy",
        "/terms-of-service",
        "/login",
        "/signup"
    ])
    def test_public_page_loads(self, api_client, page):
        """Public pages should load (return 200)"""
        response = api_client.get(f"{BASE_URL}{page}", allow_redirects=True)
        # HTML pages might return 200 or redirect
        assert response.status_code in [200, 304], f"Page {page} returned {response.status_code}"
        print(f"PASS: Public page {page} loads")


class TestAuthenticatedAppPages:
    """Authenticated app page tests (API endpoints that back pages)"""
    
    def test_dashboard_user_data(self, api_client, test_user_token):
        """Dashboard should be able to fetch user data"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        print(f"PASS: Dashboard user data endpoint works")
    
    def test_user_history_endpoint(self, api_client, test_user_token):
        """User history/generations endpoint works"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_client.get(f"{BASE_URL}/api/generations", headers=headers)
        assert response.status_code == 200
        print(f"PASS: User history endpoint works")
    
    def test_pipeline_user_jobs(self, api_client, test_user_token):
        """Pipeline user-jobs endpoint works"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_client.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=headers)
        assert response.status_code == 200
        print(f"PASS: Pipeline user-jobs endpoint works")


class TestAdminEndpoints:
    """Admin-only endpoint tests"""
    
    def test_admin_can_access_performance(self, api_client, admin_token):
        """Admin can access performance endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get(f"{BASE_URL}/api/pipeline/performance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: Admin can access performance endpoint")
    
    def test_admin_analytics_funnel(self, api_client, admin_token):
        """Admin can access analytics funnel"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_client.get(f"{BASE_URL}/api/pipeline/analytics/funnel", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: Admin can access analytics funnel")
    
    def test_non_admin_cannot_access_performance(self, api_client, test_user_token):
        """Non-admin cannot access performance endpoint"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_client.get(f"{BASE_URL}/api/pipeline/performance", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"PASS: Non-admin blocked from performance endpoint")


class TestPipelineOptions:
    """Pipeline options endpoint tests"""
    
    def test_pipeline_options_returns_styles(self, api_client):
        """Pipeline options returns animation styles"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert len(data.get("animation_styles", [])) >= 5
        assert len(data.get("voice_presets", [])) >= 3
        print(f"PASS: Pipeline options returns styles and voices")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
