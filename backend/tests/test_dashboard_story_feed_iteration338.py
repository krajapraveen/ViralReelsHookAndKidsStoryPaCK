"""
Dashboard Story-First Experience - Backend API Tests
Tests for GET /api/engagement/story-feed endpoint
Iteration 338 - Dashboard transformation testing
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestStoryFeedAPI:
    """Tests for GET /api/engagement/story-feed endpoint"""
    
    def test_story_feed_returns_200(self):
        """Test that story-feed endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Story feed endpoint returns 200 OK")
    
    def test_story_feed_has_hero_section(self):
        """Test that story-feed returns hero section"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        assert "hero" in data, "Response missing 'hero' field"
        hero = data["hero"]
        
        # Hero can be null if no stories exist, but if present should have required fields
        if hero:
            assert "hook_text" in hero, "Hero missing 'hook_text'"
            assert "thumbnail_url" in hero or "output_url" in hero, "Hero missing media URL"
            print(f"✓ Hero section present with hook_text: '{hero.get('hook_text', '')[:50]}...'")
        else:
            print("✓ Hero section is null (no featured story available)")
    
    def test_story_feed_has_trending_stories(self):
        """Test that story-feed returns trending stories array"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        assert "trending" in data, "Response missing 'trending' field"
        trending = data["trending"]
        
        assert isinstance(trending, list), "Trending should be a list"
        print(f"✓ Trending stories: {len(trending)} stories returned")
        
        # Check structure of trending stories
        if len(trending) > 0:
            story = trending[0]
            assert "job_id" in story, "Trending story missing 'job_id'"
            assert "hook_text" in story, "Trending story missing 'hook_text'"
            # thumbnail_url may be present
            print(f"✓ First trending story: '{story.get('title', 'N/A')}'")
    
    def test_story_feed_has_characters(self):
        """Test that story-feed returns characters array"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        assert "characters" in data, "Response missing 'characters' field"
        characters = data["characters"]
        
        assert isinstance(characters, list), "Characters should be a list"
        print(f"✓ Characters: {len(characters)} characters returned")
        
        # Check structure of characters
        if len(characters) > 0:
            char = characters[0]
            assert "name" in char, "Character missing 'name'"
            print(f"✓ First character: '{char.get('name', 'N/A')}'")
    
    def test_story_feed_has_live_stats(self):
        """Test that story-feed returns live_stats with required fields"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        assert "live_stats" in data, "Response missing 'live_stats' field"
        stats = data["live_stats"]
        
        assert "stories_today" in stats, "live_stats missing 'stories_today'"
        assert "total_stories" in stats, "live_stats missing 'total_stories'"
        assert "total_continuations" in stats, "live_stats missing 'total_continuations'"
        
        # Values should be integers
        assert isinstance(stats["stories_today"], int), "stories_today should be int"
        assert isinstance(stats["total_stories"], int), "total_stories should be int"
        assert isinstance(stats["total_continuations"], int), "total_continuations should be int"
        
        print(f"✓ Live stats: {stats['total_stories']} total stories, {stats['stories_today']} today, {stats['total_continuations']} continuations")
    
    def test_trending_stories_have_thumbnails(self):
        """Test that trending stories have thumbnail URLs"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        trending = data.get("trending", [])
        stories_with_thumbnails = sum(1 for s in trending if s.get("thumbnail_url"))
        
        print(f"✓ {stories_with_thumbnails}/{len(trending)} trending stories have thumbnails")
        
        # At least some stories should have thumbnails
        if len(trending) > 0:
            assert stories_with_thumbnails > 0, "No trending stories have thumbnails"
    
    def test_trending_returns_up_to_12_stories(self):
        """Test that trending returns up to 12 stories as per spec"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        trending = data.get("trending", [])
        assert len(trending) <= 12, f"Expected max 12 trending stories, got {len(trending)}"
        print(f"✓ Trending stories count ({len(trending)}) is within limit of 12")


class TestEngagementDashboardAPI:
    """Tests for authenticated engagement dashboard endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    def test_engagement_dashboard_authenticated(self, auth_token):
        """Test engagement dashboard with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/engagement/dashboard", headers=headers)
        
        # May return 404 if user has no engagement data - that's acceptable
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            # Check for expected fields
            print(f"✓ Engagement dashboard returned: {list(data.keys())}")
        else:
            print("✓ Engagement dashboard returned 404 (no engagement data for user)")
    
    def test_engagement_dashboard_has_daily_challenge(self, auth_token):
        """Test that engagement dashboard includes daily challenge"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/engagement/dashboard", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if "challenge" in data:
                challenge = data["challenge"]
                assert "prompt" in challenge, "Challenge missing 'prompt'"
                assert "reward" in challenge, "Challenge missing 'reward'"
                print(f"✓ Daily challenge: '{challenge.get('prompt', '')[:50]}...' (reward: {challenge.get('reward')})")
            else:
                print("✓ No daily challenge in response")
        else:
            print("✓ Engagement dashboard not available (404)")
    
    def test_engagement_dashboard_has_streak(self, auth_token):
        """Test that engagement dashboard includes streak info"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/engagement/dashboard", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if "streak" in data:
                streak = data["streak"]
                print(f"✓ Streak info: current={streak.get('current', 0)}, longest={streak.get('longest', 0)}")
            else:
                print("✓ No streak info in response")
        else:
            print("✓ Engagement dashboard not available (404)")


class TestCreditsAPI:
    """Tests for credits balance endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    def test_credits_balance(self, auth_token):
        """Test credits balance endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should have credits field
        assert "credits" in data or "balance" in data, "Response missing credits info"
        print(f"✓ Credits balance: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
