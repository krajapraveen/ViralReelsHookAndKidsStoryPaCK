"""
Gallery & Showcase API Tests - Iteration 163
Tests:
- Gallery listing endpoints
- Leaderboard (Most Remixed)
- Category filters
- Sort options (newest, trending, most_remixed)
- Presigned URLs verification (X-Amz-Signature)
- Regression tests for dashboard, remix, and engagement APIs
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get test user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text[:200]}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    return None


# =============================================================================
# GALLERY PUBLIC ENDPOINTS (No auth required)
# =============================================================================

class TestGalleryPublic:
    """Gallery API tests - public endpoints (no auth required)"""

    def test_gallery_listing_default(self, api_client):
        """GET /api/pipeline/gallery - default listing (newest sort)"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        
        data = response.json()
        assert "videos" in data, "Response should have 'videos' key"
        assert isinstance(data["videos"], list), "Videos should be a list"
        
        # Verify structure of video items
        if len(data["videos"]) > 0:
            video = data["videos"][0]
            assert "job_id" in video or "title" in video, "Video should have job_id or title"
            print(f"Gallery returned {len(data['videos'])} videos")
    
    def test_gallery_presigned_urls(self, api_client):
        """Verify gallery returns presigned URLs with X-Amz-Signature"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        videos = data.get("videos", [])
        
        presigned_count = 0
        for video in videos[:5]:  # Check first 5 videos
            output_url = video.get("output_url", "")
            thumbnail_url = video.get("thumbnail_url", "")
            
            # Check output_url for presigned signature
            if output_url and "X-Amz-Signature" in output_url:
                presigned_count += 1
            elif output_url:
                print(f"WARNING: output_url not presigned: {output_url[:100]}...")
            
            # Check thumbnail_url for presigned signature
            if thumbnail_url and "X-Amz-Signature" in thumbnail_url:
                presigned_count += 1
            elif thumbnail_url:
                print(f"WARNING: thumbnail_url not presigned: {thumbnail_url[:100]}...")
        
        print(f"Found {presigned_count} presigned URLs in first 5 videos")
        assert presigned_count > 0 or len(videos) == 0, "At least some URLs should be presigned"

    def test_gallery_sort_newest(self, api_client):
        """GET /api/pipeline/gallery?sort=newest"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=newest")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        print(f"Sort=newest returned {len(data['videos'])} videos")

    def test_gallery_sort_trending(self, api_client):
        """GET /api/pipeline/gallery?sort=trending"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=trending")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        print(f"Sort=trending returned {len(data['videos'])} videos")

    def test_gallery_sort_most_remixed(self, api_client):
        """GET /api/pipeline/gallery?sort=most_remixed"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=most_remixed")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        print(f"Sort=most_remixed returned {len(data['videos'])} videos")

    def test_gallery_leaderboard(self, api_client):
        """GET /api/pipeline/gallery/leaderboard - Most Remixed leaderboard"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data, "Response should have 'leaderboard' key"
        leaderboard = data["leaderboard"]
        assert isinstance(leaderboard, list), "Leaderboard should be a list"
        
        # Should return up to 5 items
        assert len(leaderboard) <= 10, "Leaderboard should have max 10 items"
        
        if len(leaderboard) > 0:
            item = leaderboard[0]
            assert "job_id" in item or "title" in item, "Leaderboard item should have job_id or title"
            
            # Check presigned URLs in leaderboard
            if item.get("thumbnail_url"):
                has_sig = "X-Amz-Signature" in item["thumbnail_url"]
                print(f"Leaderboard thumbnail presigned: {has_sig}")
            
        print(f"Leaderboard returned {len(leaderboard)} items")

    def test_gallery_categories(self, api_client):
        """GET /api/pipeline/gallery/categories - Get category counts"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data, "Response should have 'categories' key"
        categories = data["categories"]
        assert isinstance(categories, list), "Categories should be a list"
        
        # First category should be "All"
        if len(categories) > 0:
            all_cat = categories[0]
            assert all_cat.get("id") == "all", "First category should be 'all'"
            assert "count" in all_cat, "Category should have 'count'"
            assert "name" in all_cat, "Category should have 'name'"
        
        # Check for expected animation style categories
        category_ids = [c.get("id") for c in categories]
        print(f"Available categories: {category_ids}")

    def test_gallery_filter_by_category(self, api_client):
        """GET /api/pipeline/gallery?category=cartoon_2d"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=cartoon_2d")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        
        # Verify all returned videos match the category
        for video in data["videos"]:
            style = video.get("animation_style")
            assert style is None or style == "cartoon_2d", f"Expected cartoon_2d, got {style}"
        
        print(f"Category=cartoon_2d returned {len(data['videos'])} videos")

    def test_gallery_filter_watercolor(self, api_client):
        """GET /api/pipeline/gallery?category=watercolor"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=watercolor")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        print(f"Category=watercolor returned {len(data['videos'])} videos")


# =============================================================================
# REGRESSION TESTS - Dashboard & Engagement
# =============================================================================

class TestDashboardRegression:
    """Regression tests for dashboard functionality"""

    def test_engagement_dashboard(self, api_client, auth_token):
        """GET /api/engagement/dashboard - dashboard engagement data"""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "challenge" in data, "Response should have 'challenge'"
        assert "streak" in data, "Response should have 'streak'"
        assert "level" in data, "Response should have 'level'"
        assert "ideas" in data, "Response should have 'ideas'"
        print(f"Dashboard engagement: level={data['level'].get('level')}, streak={data['streak'].get('current')}")

    def test_engagement_trending(self, api_client):
        """GET /api/engagement/trending - public trending items"""
        response = api_client.get(f"{BASE_URL}/api/engagement/trending")
        assert response.status_code == 200
        
        data = response.json()
        assert "trending" in data
        
        # Check presigned URLs in trending items
        for item in data.get("trending", [])[:3]:
            if item.get("thumbnail_url"):
                has_sig = "X-Amz-Signature" in item["thumbnail_url"]
                print(f"Trending thumbnail presigned: {has_sig}")


# =============================================================================
# REGRESSION TESTS - Remix Variations
# =============================================================================

class TestRemixVariationsRegression:
    """Regression tests for remix variations API"""

    def test_remix_variations_story_video_studio(self, api_client):
        """GET /api/remix/variations/story-video-studio"""
        response = api_client.get(f"{BASE_URL}/api/remix/variations/story-video-studio")
        assert response.status_code == 200
        
        data = response.json()
        assert "quick_variations" in data
        assert "style_switches" in data
        assert "action_variations" in data
        
        print(f"Story Video Studio: {len(data['quick_variations'])} quick, {len(data['style_switches'])} styles")


# =============================================================================
# REGRESSION TESTS - Engagement Analytics
# =============================================================================

class TestEngagementAnalyticsRegression:
    """Regression tests for engagement analytics API"""

    def test_track_cta(self, api_client, auth_token):
        """POST /api/engagement-analytics/track-cta"""
        response = api_client.post(
            f"{BASE_URL}/api/engagement-analytics/track-cta",
            json={"cta_type": "gallery_remix", "source_page": "gallery"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print("CTA tracking: OK")


# =============================================================================
# REGRESSION TESTS - Tool Pages
# =============================================================================

class TestToolPagesRegression:
    """Regression tests for tool page API availability"""

    def test_health_endpoint(self, api_client):
        """GET /api/health"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("Health endpoint: OK")

    def test_pipeline_options(self, api_client):
        """GET /api/pipeline/options - story video studio options"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        
        data = response.json()
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        
        print(f"Pipeline options: {len(data['animation_styles'])} styles")

    def test_user_pipeline_jobs(self, api_client, auth_token):
        """GET /api/pipeline/user-jobs - authenticated endpoint"""
        response = api_client.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        print(f"User has {len(data['jobs'])} pipeline jobs")


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

class TestAuthentication:
    """Authentication tests"""

    def test_login_test_user(self, api_client):
        """Test user login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text[:200]}"
        data = response.json()
        assert data.get("token") or data.get("access_token"), "Response should contain token"
        print("Test user login: OK")

    def test_login_admin_user(self, api_client):
        """Admin user login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text[:200]}"
        print("Admin user login: OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
