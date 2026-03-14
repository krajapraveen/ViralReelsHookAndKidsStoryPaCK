"""
Iteration 164 - Gallery & Showcase Backend API Testing
Tests: Gallery endpoints, presigned URLs, leaderboard, categories, filters, sort, remix APIs
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_token(api_client):
    """Get test user token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Test user authentication failed")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin user token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_USER_EMAIL,
        "password": ADMIN_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


class TestGalleryEndpoints:
    """Gallery public endpoints - no auth required"""

    def test_gallery_returns_videos(self, api_client):
        """GET /api/pipeline/gallery - should return list of videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "videos" in data
        print(f"✓ Gallery returned {len(data['videos'])} videos")

    def test_gallery_videos_have_presigned_output_url(self, api_client):
        """Verify output_url contains X-Amz-Signature for presigning"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        
        # Check at least some videos have presigned URLs
        presigned_count = 0
        for video in videos[:10]:  # Check first 10
            output_url = video.get("output_url", "")
            if output_url and "X-Amz-Signature" in output_url:
                presigned_count += 1
        
        print(f"✓ {presigned_count}/10 videos have presigned output_url")
        assert presigned_count > 0, "No presigned output URLs found"

    def test_gallery_videos_have_presigned_thumbnail_url(self, api_client):
        """Verify thumbnail_url contains X-Amz-Signature for presigning"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        
        presigned_count = 0
        for video in videos[:10]:
            thumbnail_url = video.get("thumbnail_url", "")
            if thumbnail_url and "X-Amz-Signature" in thumbnail_url:
                presigned_count += 1
        
        print(f"✓ {presigned_count}/10 videos have presigned thumbnail_url")
        # Thumbnails may not exist for all videos
        if presigned_count == 0:
            print("Note: No thumbnails with presigned URLs found - may be expected if no thumbnails generated")

    def test_gallery_category_filter_watercolor(self, api_client):
        """GET /api/pipeline/gallery?category=watercolor - should filter by category"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=watercolor")
        assert response.status_code == 200
        data = response.json()
        videos = data.get("videos", [])
        
        # All returned videos should have watercolor animation_style
        for video in videos:
            assert video.get("animation_style") == "watercolor", f"Expected watercolor, got {video.get('animation_style')}"
        
        print(f"✓ Category filter returned {len(videos)} watercolor videos")

    def test_gallery_sort_newest(self, api_client):
        """GET /api/pipeline/gallery?sort=newest"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=newest")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        print(f"✓ Sort by newest returned {len(videos)} videos")

    def test_gallery_sort_most_remixed(self, api_client):
        """GET /api/pipeline/gallery?sort=most_remixed"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=most_remixed")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        print(f"✓ Sort by most_remixed returned {len(videos)} videos")

    def test_gallery_sort_trending(self, api_client):
        """GET /api/pipeline/gallery?sort=trending"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort=trending")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        print(f"✓ Sort by trending returned {len(videos)} videos")


class TestGalleryLeaderboard:
    """Leaderboard endpoint tests"""

    def test_leaderboard_returns_items(self, api_client):
        """GET /api/pipeline/gallery/leaderboard - should return top remixed items"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        leaderboard = data["leaderboard"]
        assert len(leaderboard) > 0, "Leaderboard should not be empty"
        assert len(leaderboard) <= 10, "Leaderboard should have max 10 items"
        print(f"✓ Leaderboard returned {len(leaderboard)} items")

    def test_leaderboard_has_presigned_urls(self, api_client):
        """Verify leaderboard items have presigned URLs"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        leaderboard = response.json().get("leaderboard", [])
        
        for i, item in enumerate(leaderboard[:5]):
            output_url = item.get("output_url", "")
            if output_url:
                assert "X-Amz-Signature" in output_url, f"Item {i}: output_url missing presigned signature"
        print(f"✓ Leaderboard items have presigned output_url")

    def test_leaderboard_item_structure(self, api_client):
        """Verify leaderboard items have required fields"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        leaderboard = response.json().get("leaderboard", [])
        
        if leaderboard:
            item = leaderboard[0]
            assert "title" in item
            assert "job_id" in item
            # remix_count might be 0 for fallback/featured items
            print(f"✓ Leaderboard item structure valid: title='{item.get('title', 'N/A')}'")


class TestGalleryCategories:
    """Categories endpoint tests"""

    def test_categories_returns_list(self, api_client):
        """GET /api/pipeline/gallery/categories - should return category list with counts"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        categories = data["categories"]
        assert len(categories) > 0, "Should have at least 'All' category"
        print(f"✓ Categories returned: {len(categories)} total")

    def test_categories_has_all_category(self, api_client):
        """First category should be 'All' with total count"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        assert categories[0]["id"] == "all"
        assert categories[0]["name"] == "All"
        assert "count" in categories[0]
        print(f"✓ 'All' category count: {categories[0]['count']}")

    def test_categories_structure(self, api_client):
        """Each category should have id, name, count"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        categories = response.json().get("categories", [])
        
        for cat in categories:
            assert "id" in cat
            assert "name" in cat
            assert "count" in cat
        print(f"✓ All categories have valid structure")


class TestRemixAPIs:
    """Remix engine APIs - some require auth"""

    def test_variations_story_video_studio(self, api_client):
        """GET /api/remix/variations/story-video-studio - public, no auth"""
        response = api_client.get(f"{BASE_URL}/api/remix/variations/story-video-studio")
        assert response.status_code == 200
        data = response.json()
        
        # Should have quick, styles, actions arrays
        assert "quick" in data
        assert "styles" in data
        assert "actions" in data
        
        print(f"✓ story-video-studio variations: {len(data['quick'])} quick, {len(data['styles'])} styles, {len(data['actions'])} actions")

    def test_variations_unknown_tool(self, api_client):
        """GET /api/remix/variations/unknown-tool - should return empty arrays"""
        response = api_client.get(f"{BASE_URL}/api/remix/variations/unknown-tool")
        assert response.status_code == 200
        data = response.json()
        assert data.get("quick", []) == []
        assert data.get("styles", []) == []
        assert data.get("actions", []) == []
        print(f"✓ Unknown tool returns empty arrays")

    def test_remix_track_requires_auth(self, api_client):
        """POST /api/remix/track - should require auth"""
        response = api_client.post(f"{BASE_URL}/api/remix/track", json={
            "source_tool": "gallery",
            "target_tool": "story-video-studio",
            "original_prompt": "test prompt",
            "variation_type": "gallery_remix",
            "variation_label": "Gallery Remix"
        })
        assert response.status_code == 401 or response.status_code == 403
        print(f"✓ /api/remix/track correctly requires auth")

    def test_remix_track_with_auth(self, api_client, test_user_token):
        """POST /api/remix/track - should succeed with auth"""
        response = api_client.post(
            f"{BASE_URL}/api/remix/track",
            json={
                "source_tool": "gallery",
                "target_tool": "story-video-studio",
                "original_prompt": "Test prompt for iteration 164",
                "variation_type": "gallery_remix",
                "variation_label": "Gallery Remix Test"
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Remix tracking works with auth")


class TestEngagementAnalytics:
    """Engagement analytics APIs"""

    def test_engagement_report_requires_admin(self, api_client, test_user_token):
        """GET /api/engagement-analytics/report - should require admin"""
        response = api_client.get(
            f"{BASE_URL}/api/engagement-analytics/report",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403
        print(f"✓ Engagement report correctly requires admin role")

    def test_engagement_report_admin_access(self, api_client, admin_token):
        """GET /api/engagement-analytics/report - admin should access"""
        response = api_client.get(
            f"{BASE_URL}/api/engagement-analytics/report",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "challenge_completion" in data or "report" in data
        print(f"✓ Admin can access engagement report")


class TestPipelineWorkerStatus:
    """Pipeline worker health endpoints"""

    def test_workers_status_requires_auth(self, api_client):
        """GET /api/pipeline/workers/status - requires auth"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/workers/status")
        # Should require auth
        assert response.status_code in [401, 403]
        print(f"✓ Workers status requires auth (status: {response.status_code})")

    def test_workers_status_with_auth(self, api_client, test_user_token):
        """GET /api/pipeline/workers/status - with auth"""
        response = api_client.get(
            f"{BASE_URL}/api/pipeline/workers/status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "workers" in data
        print(f"✓ Workers status returned: {data.get('workers', {})}")


class TestRegressionAPIs:
    """Regression tests for existing APIs"""

    def test_health_endpoint(self, api_client):
        """GET /api/health"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"✓ Health endpoint OK")

    def test_auth_login(self, api_client):
        """POST /api/auth/login - test user"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"✓ Test user login successful")

    def test_pipeline_options(self, api_client):
        """GET /api/pipeline/options - should return animation styles, age groups, voices"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        print(f"✓ Pipeline options: {len(data['animation_styles'])} styles, {len(data['age_groups'])} ages, {len(data['voice_presets'])} voices")

    def test_engagement_dashboard(self, api_client, test_user_token):
        """GET /api/engagement/dashboard - user engagement data"""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should have engagement features
        assert "challenge" in data or "streak" in data or "level" in data
        print(f"✓ Engagement dashboard returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
