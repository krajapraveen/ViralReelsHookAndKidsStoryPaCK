"""
Homepage Architecture Tests - Iteration 361
Tests for story-feed API, feed item schema, and homepage data structure.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestStoryFeedAPI:
    """Tests for /api/engagement/story-feed endpoint"""
    
    def test_story_feed_returns_200(self):
        """Story feed endpoint should return 200 OK"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Story feed returns 200 OK")
    
    def test_story_feed_has_required_keys(self):
        """Story feed should return all 5 row arrays + live_stats"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        required_keys = [
            "featured_story",
            "trending_stories",
            "fresh_stories",
            "continue_stories",
            "unfinished_worlds",
            "live_stats"
        ]
        
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"
        print(f"✓ Story feed has all required keys: {required_keys}")
    
    def test_featured_story_schema(self):
        """Featured story should have all required fields"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        featured = data.get("featured_story")
        
        if featured is None:
            pytest.skip("No featured story available")
        
        required_fields = [
            "job_id", "title", "hook_text", "story_prompt",
            "thumbnail_url", "poster_url", "preview_url", "output_url",
            "animation_style", "parent_video_id", "badge", "character_summary"
        ]
        
        for field in required_fields:
            assert field in featured, f"Featured story missing field: {field}"
        
        # Validate badge is FEATURED
        assert featured["badge"] == "FEATURED", f"Expected badge FEATURED, got {featured['badge']}"
        print(f"✓ Featured story has all required fields and FEATURED badge")
    
    def test_trending_stories_is_array(self):
        """Trending stories should be an array"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        assert isinstance(data["trending_stories"], list), "trending_stories should be a list"
        print(f"✓ Trending stories is array with {len(data['trending_stories'])} items")
    
    def test_fresh_stories_is_array(self):
        """Fresh stories should be an array"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        assert isinstance(data["fresh_stories"], list), "fresh_stories should be a list"
        print(f"✓ Fresh stories is array with {len(data['fresh_stories'])} items")
    
    def test_continue_stories_is_array(self):
        """Continue stories should be an array (empty without auth)"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        assert isinstance(data["continue_stories"], list), "continue_stories should be a list"
        print(f"✓ Continue stories is array with {len(data['continue_stories'])} items (no auth)")
    
    def test_unfinished_worlds_is_array(self):
        """Unfinished worlds should be an array"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        assert isinstance(data["unfinished_worlds"], list), "unfinished_worlds should be a list"
        print(f"✓ Unfinished worlds is array with {len(data['unfinished_worlds'])} items")
    
    def test_story_item_schema(self):
        """Each story item should have required fields for prefill"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        # Check first trending story
        if len(data["trending_stories"]) > 0:
            story = data["trending_stories"][0]
            required_fields = [
                "job_id", "title", "hook_text", "story_prompt",
                "thumbnail_url", "animation_style", "badge"
            ]
            for field in required_fields:
                assert field in story, f"Story item missing field: {field}"
            print(f"✓ Story items have all required fields for prefill")
        else:
            pytest.skip("No trending stories to validate")
    
    def test_live_stats_structure(self):
        """Live stats should have stories_today and total_stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        live_stats = data.get("live_stats", {})
        assert "stories_today" in live_stats, "Missing stories_today in live_stats"
        assert "total_stories" in live_stats, "Missing total_stories in live_stats"
        assert isinstance(live_stats["total_stories"], int), "total_stories should be int"
        print(f"✓ Live stats: {live_stats['total_stories']} total stories")


class TestStoryFeedWithAuth:
    """Tests for story-feed with authenticated user"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code}")
    
    def test_continue_stories_with_auth(self, auth_token):
        """Continue stories should return user's jobs when authenticated"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Continue stories should be populated for logged-in user
        assert isinstance(data["continue_stories"], list)
        print(f"✓ Continue stories with auth: {len(data['continue_stories'])} items")
        
        # If there are continue stories, verify badge
        if len(data["continue_stories"]) > 0:
            for story in data["continue_stories"]:
                assert story.get("badge") == "CONTINUE", f"Expected CONTINUE badge, got {story.get('badge')}"
            print("✓ All continue stories have CONTINUE badge")


class TestTrendingEndpoint:
    """Tests for /api/engagement/trending endpoint"""
    
    def test_trending_returns_200(self):
        """Trending endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/engagement/trending")
        assert response.status_code == 200
        print("✓ Trending endpoint returns 200")
    
    def test_trending_has_array(self):
        """Trending should return trending array"""
        response = requests.get(f"{BASE_URL}/api/engagement/trending")
        data = response.json()
        
        assert "trending" in data, "Missing 'trending' key"
        assert isinstance(data["trending"], list), "trending should be a list"
        print(f"✓ Trending has {len(data['trending'])} items")


class TestExploreEndpoint:
    """Tests for /api/engagement/explore endpoint"""
    
    def test_explore_returns_200(self):
        """Explore endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        assert response.status_code == 200
        print("✓ Explore endpoint returns 200")
    
    def test_explore_has_stories_array(self):
        """Explore should return stories array"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        data = response.json()
        
        assert "stories" in data, "Missing 'stories' key"
        assert isinstance(data["stories"], list), "stories should be a list"
        assert "total" in data, "Missing 'total' key"
        print(f"✓ Explore has {len(data['stories'])} stories, total: {data['total']}")
    
    def test_explore_pagination(self):
        """Explore should support cursor pagination"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore?cursor=0&limit=5")
        data = response.json()
        
        assert len(data["stories"]) <= 5, "Should respect limit parameter"
        print(f"✓ Explore pagination works: {len(data['stories'])} items with limit=5")


class TestEngagementDashboard:
    """Tests for /api/engagement/dashboard (requires auth)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code}")
    
    def test_dashboard_requires_auth(self):
        """Dashboard should require authentication"""
        response = requests.get(f"{BASE_URL}/api/engagement/dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Dashboard requires authentication")
    
    def test_dashboard_with_auth(self, auth_token):
        """Dashboard should return engagement data with auth"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/engagement/dashboard", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        required_keys = ["challenge", "streak", "level", "ideas"]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
        print(f"✓ Dashboard returns all engagement data: {list(data.keys())}")


class TestFeatureCardRoutes:
    """Tests for feature card navigation routes"""
    
    def test_story_video_studio_route(self):
        """Story Video Studio route should be accessible"""
        # This is a frontend route, just verify the API base is working
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("✓ API health check passed (frontend routes are client-side)")
    
    def test_story_series_api(self):
        """Story Series API should exist"""
        response = requests.get(f"{BASE_URL}/api/story-series/list")
        # May return 401 if auth required, but should not 404
        assert response.status_code != 404, "Story series endpoint should exist"
        print(f"✓ Story series endpoint exists (status: {response.status_code})")
    
    def test_characters_api(self):
        """Characters API should exist"""
        response = requests.get(f"{BASE_URL}/api/characters")
        # May return 401 if auth required, but should not 404
        assert response.status_code != 404, "Characters endpoint should exist"
        print(f"✓ Characters endpoint exists (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
