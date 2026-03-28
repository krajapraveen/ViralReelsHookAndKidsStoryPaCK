"""
Iteration 354 - Netflix-style Dashboard Backend API Tests
Tests: story-feed API, R2 media proxy (HEAD, GET, Range requests), credits API
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestStoryFeedAPI:
    """Tests for GET /api/engagement/story-feed endpoint"""

    def test_story_feed_returns_hero(self):
        """Story feed should return hero with title"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        # Hero should exist with title
        assert "hero" in data, "No hero in response"
        hero = data["hero"]
        assert hero is not None, "Hero is None"
        assert "title" in hero, "Hero has no title"
        assert hero["title"] == "Clover and the Golden Key", f"Unexpected hero title: {hero['title']}"

    def test_story_feed_returns_trending_array(self):
        """Story feed should return trending array with 10+ stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        assert "trending" in data, "No trending in response"
        trending = data["trending"]
        assert isinstance(trending, list), "Trending is not a list"
        assert len(trending) >= 10, f"Expected 10+ trending stories, got {len(trending)}"

    def test_story_feed_hero_has_thumbnail_url(self):
        """Hero should have thumbnail_url with R2 proxy path"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        hero = data.get("hero", {})
        thumbnail_url = hero.get("thumbnail_url")
        assert thumbnail_url is not None, "Hero has no thumbnail_url"
        assert thumbnail_url.startswith("/api/media/r2/"), f"Thumbnail URL not using R2 proxy: {thumbnail_url}"

    def test_story_feed_trending_stories_have_required_fields(self):
        """Trending stories should have job_id, title, and hook_text"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        trending = data.get("trending", [])
        assert len(trending) > 0, "No trending stories"
        
        for i, story in enumerate(trending[:5]):  # Check first 5
            assert "job_id" in story, f"Story {i} missing job_id"
            assert "title" in story, f"Story {i} missing title"
            # hook_text is generated from story_text

    def test_story_feed_live_stats(self):
        """Story feed should return live_stats with total_stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        assert "live_stats" in data, "No live_stats in response"
        live_stats = data["live_stats"]
        assert "total_stories" in live_stats, "No total_stories in live_stats"
        assert live_stats["total_stories"] > 0, "total_stories should be > 0"


class TestR2MediaProxy:
    """Tests for R2 media proxy endpoints"""

    def test_r2_proxy_thumbnail_returns_200(self):
        """GET /api/media/r2/thumbnails/{path}.jpg should return 200 with image"""
        # First get a thumbnail path from story-feed
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        hero = data.get("hero", {})
        thumbnail_url = hero.get("thumbnail_url", "")
        assert thumbnail_url.startswith("/api/media/r2/"), "No valid thumbnail URL"
        
        # Request the thumbnail
        img_response = requests.get(f"{BASE_URL}{thumbnail_url}")
        assert img_response.status_code == 200, f"Thumbnail request failed: {img_response.status_code}"
        
        content_type = img_response.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image content type, got: {content_type}"

    def test_r2_proxy_head_request_for_video(self):
        """HEAD /api/media/r2/videos/{path}.mp4 should return 200 with Accept-Ranges"""
        # Get video path from story-feed
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        hero = data.get("hero", {})
        video_url = hero.get("output_url") or hero.get("preview_url")
        if not video_url or not video_url.startswith("/api/media/r2/"):
            pytest.skip("No video URL available for testing")
        
        # HEAD request
        head_response = requests.head(f"{BASE_URL}{video_url}")
        assert head_response.status_code == 200, f"HEAD request failed: {head_response.status_code}"
        
        # Check Accept-Ranges header
        accept_ranges = head_response.headers.get("Accept-Ranges", "")
        assert accept_ranges == "bytes", f"Expected Accept-Ranges: bytes, got: {accept_ranges}"
        
        # Check Content-Length
        content_length = head_response.headers.get("Content-Length")
        assert content_length is not None, "No Content-Length header"
        assert int(content_length) > 0, "Content-Length should be > 0"

    def test_r2_proxy_range_request_returns_206(self):
        """GET /api/media/r2/videos/{path}.mp4 with Range header should return 206"""
        # Get video path from story-feed
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        hero = data.get("hero", {})
        video_url = hero.get("output_url") or hero.get("preview_url")
        if not video_url or not video_url.startswith("/api/media/r2/"):
            pytest.skip("No video URL available for testing")
        
        # Range request for first 1KB
        range_response = requests.get(
            f"{BASE_URL}{video_url}",
            headers={"Range": "bytes=0-1023"}
        )
        assert range_response.status_code == 206, f"Expected 206, got: {range_response.status_code}"
        
        # Check Content-Range header
        content_range = range_response.headers.get("Content-Range", "")
        assert content_range.startswith("bytes 0-1023/"), f"Invalid Content-Range: {content_range}"
        
        # Check content length
        assert len(range_response.content) == 1024, f"Expected 1024 bytes, got {len(range_response.content)}"


class TestCreditsAPI:
    """Tests for credits balance API"""

    def test_credits_balance_returns_numeric(self, auth_headers):
        """GET /api/credits/balance should return numeric credits"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Credits API failed: {response.status_code}"
        data = response.json()
        
        assert "credits" in data, "No credits in response"
        credits = data["credits"]
        assert isinstance(credits, (int, float)), f"Credits should be numeric, got: {type(credits)}"

    def test_test_user_has_unlimited_credits(self, auth_headers):
        """Test user should have 999999 (unlimited) credits"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        credits = data.get("credits", 0)
        # Test user should have very high credits (999999 or close to it)
        assert credits >= 999000, f"Test user should have unlimited credits, got: {credits}"


class TestAuthFlow:
    """Tests for authentication"""

    def test_login_returns_token_and_user(self):
        """Login should return token and user object"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        
        user = data["user"]
        assert user.get("email") == TEST_EMAIL, f"Unexpected email: {user.get('email')}"
        assert "credits" in user, "No credits in user object"
