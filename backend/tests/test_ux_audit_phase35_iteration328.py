"""
Phase 3.5 UX Tightening - Behavioral Momentum Optimization Tests
Tests for:
1. Follow Feed API - GET /api/universe/follow-feed
2. Rankings API - GET /api/universe/rankings
3. Follow Toggle API - POST /api/universe/follow
4. Notifications API - GET /api/universe/notifications
5. Character Stories API - GET /api/universe/character/{id}/stories
6. Series Episodes API - GET /api/universe/series/{id}/episodes
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

# Known character IDs
FINN_CHARACTER_ID = "d8cf0208-ff0c-4c21-8725-ffa6326d8da9"
ZARA_CHARACTER_ID = "9c0c60aa-7fab-4885-bb4d-111287275ba5"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self, api_client):
        """Test API health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ API health check passed: {data}")


class TestFollowFeedAPI:
    """Tests for Follow Feed API - GET /api/universe/follow-feed"""
    
    def test_follow_feed_returns_stories_from_followed_characters(self, authenticated_client):
        """Follow Feed should return stories from characters user follows"""
        response = authenticated_client.get(f"{BASE_URL}/api/universe/follow-feed")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "stories" in data
        assert "has_follows" in data
        
        # If user follows characters, should have stories
        if data.get("has_follows"):
            stories = data.get("stories", [])
            print(f"✓ Follow Feed returned {len(stories)} stories")
            
            # Each story should have character_name attached
            for story in stories:
                assert "job_id" in story
                assert "title" in story
                # character_name should be attached if matched
                if "character_name" in story:
                    print(f"  - Story '{story.get('title')}' from character '{story.get('character_name')}'")
        else:
            print("✓ Follow Feed: User has no follows (expected empty)")
    
    def test_follow_feed_requires_auth(self, api_client):
        """Follow Feed should require authentication"""
        # Remove auth header temporarily
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/universe/follow-feed", headers=headers)
        assert response.status_code in [401, 403]
        print("✓ Follow Feed correctly requires authentication")


class TestFollowToggleAPI:
    """Tests for Follow Toggle API - POST /api/universe/follow"""
    
    def test_follow_toggle_works(self, authenticated_client):
        """Follow toggle should work for authenticated users"""
        # First, check current follow status
        check_response = authenticated_client.get(f"{BASE_URL}/api/universe/following/{FINN_CHARACTER_ID}")
        assert check_response.status_code == 200
        initial_following = check_response.json().get("following", False)
        print(f"  Initial following status: {initial_following}")
        
        # Toggle follow
        toggle_response = authenticated_client.post(
            f"{BASE_URL}/api/universe/follow",
            json={"character_id": FINN_CHARACTER_ID}
        )
        assert toggle_response.status_code == 200
        data = toggle_response.json()
        assert data.get("success") == True
        assert "following" in data
        
        new_following = data.get("following")
        print(f"✓ Follow toggle worked: {initial_following} -> {new_following}")
        
        # Toggle back to original state
        authenticated_client.post(
            f"{BASE_URL}/api/universe/follow",
            json={"character_id": FINN_CHARACTER_ID}
        )
    
    def test_follow_requires_auth(self, api_client):
        """Follow should require authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{BASE_URL}/api/universe/follow",
            json={"character_id": FINN_CHARACTER_ID},
            headers=headers
        )
        assert response.status_code in [401, 403]
        print("✓ Follow correctly requires authentication")


class TestNotificationsAPI:
    """Tests for Notifications API - GET /api/universe/notifications"""
    
    def test_notifications_returns_list(self, authenticated_client):
        """Notifications should return list with unread count"""
        response = authenticated_client.get(f"{BASE_URL}/api/universe/notifications")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "notifications" in data
        assert "unread_count" in data
        
        notifications = data.get("notifications", [])
        unread = data.get("unread_count", 0)
        print(f"✓ Notifications API returned {len(notifications)} notifications, {unread} unread")
        
        # Check notification structure
        if notifications:
            notif = notifications[0]
            assert "type" in notif
            assert "title" in notif
            print(f"  - Latest: [{notif.get('type')}] {notif.get('title')}")
    
    def test_notifications_requires_auth(self, api_client):
        """Notifications should require authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/universe/notifications", headers=headers)
        assert response.status_code in [401, 403]
        print("✓ Notifications correctly requires authentication")


class TestRankingsAPI:
    """Tests for Rankings API - GET /api/universe/rankings"""
    
    def test_rankings_returns_top_stories_characters_creators(self, api_client):
        """Rankings should return top stories, characters, and creators"""
        response = api_client.get(f"{BASE_URL}/api/universe/rankings")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        # Check all ranking categories
        assert "top_stories" in data
        assert "top_characters" in data
        assert "top_creators" in data
        
        top_stories = data.get("top_stories", [])
        top_characters = data.get("top_characters", [])
        top_creators = data.get("top_creators", [])
        
        print(f"✓ Rankings API returned:")
        print(f"  - {len(top_stories)} top stories")
        print(f"  - {len(top_characters)} top characters")
        print(f"  - {len(top_creators)} top creators")
        
        # Verify story structure
        if top_stories:
            story = top_stories[0]
            assert "job_id" in story
            assert "title" in story
            print(f"  - Top story: '{story.get('title')}' with {story.get('views', 0)} views")
        
        # Verify character structure
        if top_characters:
            char = top_characters[0]
            assert "character_id" in char
            assert "name" in char
            print(f"  - Top character: '{char.get('name')}' with {char.get('story_count', 0)} stories")


class TestCharacterStoriesAPI:
    """Tests for Character Stories API - GET /api/universe/character/{id}/stories"""
    
    def test_character_stories_returns_feed(self, api_client):
        """Character stories should return stories featuring the character"""
        response = api_client.get(f"{BASE_URL}/api/universe/character/{FINN_CHARACTER_ID}/stories")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        assert "stories" in data
        assert "character_name" in data
        assert "follower_count" in data
        
        stories = data.get("stories", [])
        char_name = data.get("character_name")
        follower_count = data.get("follower_count", 0)
        
        print(f"✓ Character Stories API for '{char_name}':")
        print(f"  - {len(stories)} stories")
        print(f"  - {follower_count} followers")
        
        # Verify story structure
        if stories:
            story = stories[0]
            assert "job_id" in story
            assert "title" in story
            print(f"  - Latest: '{story.get('title')}'")
    
    def test_character_stories_404_for_invalid_id(self, api_client):
        """Character stories should return 404 for invalid character ID"""
        response = api_client.get(f"{BASE_URL}/api/universe/character/invalid-id-12345/stories")
        assert response.status_code == 404
        print("✓ Character Stories correctly returns 404 for invalid ID")


class TestSeriesEpisodesAPI:
    """Tests for Series Episodes API - GET /api/universe/series/{id}/episodes"""
    
    def test_series_episodes_structure(self, api_client):
        """Series episodes should return proper structure with lock status"""
        # First, try to find a series
        # This may 404 if no series exists, which is acceptable
        response = api_client.get(f"{BASE_URL}/api/universe/series/test-series-id/episodes")
        
        if response.status_code == 404:
            print("✓ Series Episodes correctly returns 404 for non-existent series")
            return
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        assert "series" in data
        assert "episodes" in data
        assert "next_episode_number" in data
        
        series = data.get("series", {})
        episodes = data.get("episodes", [])
        
        print(f"✓ Series Episodes API for '{series.get('title')}':")
        print(f"  - {len(episodes)} episodes")
        print(f"  - Next episode: {data.get('next_episode_number')}")
        
        # Verify episode structure with lock status
        for ep in episodes:
            assert "episode_number" in ep
            assert "locked" in ep
            assert "is_current" in ep
            assert "is_completed" in ep


class TestPublicCharacterPage:
    """Tests for Public Character Page API - GET /api/public/character/{id}"""
    
    def test_public_character_returns_data(self, api_client):
        """Public character page should return character data with remix info"""
        response = api_client.get(f"{BASE_URL}/api/public/character/{FINN_CHARACTER_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        assert "character" in data
        assert "visual_bible" in data
        assert "social_proof" in data
        
        character = data.get("character", {})
        social_proof = data.get("social_proof", {})
        
        print(f"✓ Public Character API for '{character.get('name')}':")
        print(f"  - Total stories: {social_proof.get('total_stories', 0)}")
        print(f"  - Total continuations: {social_proof.get('total_continuations', 0)}")
        
        # Check for hook_text (used in hero section)
        if character.get("hook_text"):
            print(f"  - Hook text: '{character.get('hook_text')[:50]}...'")
    
    def test_public_character_404_for_invalid_id(self, api_client):
        """Public character should return 404 for invalid ID"""
        response = api_client.get(f"{BASE_URL}/api/public/character/invalid-id-12345")
        assert response.status_code in [404, 200]  # May return 200 with error in body
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == False or "error" in str(data).lower()
        print("✓ Public Character correctly handles invalid ID")


class TestMyFollowsAPI:
    """Tests for My Follows API - GET /api/universe/my-follows"""
    
    def test_my_follows_returns_list(self, authenticated_client):
        """My follows should return list of followed characters"""
        response = authenticated_client.get(f"{BASE_URL}/api/universe/my-follows")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "characters" in data
        
        characters = data.get("characters", [])
        print(f"✓ My Follows API returned {len(characters)} followed characters")
        
        for char in characters:
            assert "character_id" in char
            assert "name" in char
            print(f"  - Following: '{char.get('name')}'")


class TestSeriesContinueAPI:
    """Tests for Series Continue API - POST /api/universe/series/{id}/continue"""
    
    def test_series_continue_returns_prompt(self, api_client):
        """Series continue should return prefilled prompt for next episode"""
        response = api_client.post(f"{BASE_URL}/api/universe/series/test-series-id/continue")
        
        if response.status_code == 404:
            print("✓ Series Continue correctly returns 404 for non-existent series")
            return
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        assert "prompt" in data
        assert "next_episode_number" in data
        assert "series_title" in data
        
        print(f"✓ Series Continue API:")
        print(f"  - Series: '{data.get('series_title')}'")
        print(f"  - Next episode: {data.get('next_episode_number')}")
        print(f"  - Prompt length: {len(data.get('prompt', ''))} chars")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
