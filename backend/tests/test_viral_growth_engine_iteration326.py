"""
Phase 3 Testing: Content Flywheel Engine - Character Universe, Series Timeline, Rankings, Notifications
Tests for /api/universe/ routes: Follow, Feed, Rankings, Notifications, Series episodes/continue
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Known character ID (Finn)
KNOWN_CHARACTER_ID = "d8cf0208-ff0c-4c21-8725-ffa6326d8da9"


class TestUniverseRankings:
    """Rankings API - Public endpoint, no auth required"""
    
    def test_rankings_endpoint_returns_200(self):
        """GET /api/universe/rankings should return 200"""
        response = requests.get(f"{BASE_URL}/api/universe/rankings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_rankings_returns_expected_structure(self):
        """Rankings should return top_stories, top_characters, top_creators"""
        response = requests.get(f"{BASE_URL}/api/universe/rankings")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert "top_stories" in data, "Missing top_stories in response"
        assert "top_characters" in data, "Missing top_characters in response"
        assert "top_creators" in data, "Missing top_creators in response"
        
        # Validate top_stories is a list
        assert isinstance(data["top_stories"], list), "top_stories should be a list"
        
        # Validate top_characters is a list
        assert isinstance(data["top_characters"], list), "top_characters should be a list"
        
        # Validate top_creators is a list
        assert isinstance(data["top_creators"], list), "top_creators should be a list"
        
    def test_rankings_top_stories_structure(self):
        """Top stories should have expected fields"""
        response = requests.get(f"{BASE_URL}/api/universe/rankings")
        data = response.json()
        
        if len(data.get("top_stories", [])) > 0:
            story = data["top_stories"][0]
            # Check expected fields
            assert "job_id" in story or "title" in story, "Story should have job_id or title"


class TestCharacterStories:
    """Character Stories Feed - Public endpoint"""
    
    def test_character_stories_endpoint(self):
        """GET /api/universe/character/{id}/stories should return stories"""
        response = requests.get(f"{BASE_URL}/api/universe/character/{KNOWN_CHARACTER_ID}/stories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_character_stories_returns_expected_structure(self):
        """Character stories should return stories list and follower_count"""
        response = requests.get(f"{BASE_URL}/api/universe/character/{KNOWN_CHARACTER_ID}/stories")
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert "stories" in data, "Missing stories in response"
        assert "follower_count" in data, "Missing follower_count in response"
        assert isinstance(data["stories"], list), "stories should be a list"
        assert isinstance(data["follower_count"], int), "follower_count should be an integer"
        
    def test_character_stories_invalid_id_returns_404(self):
        """Invalid character ID should return 404"""
        response = requests.get(f"{BASE_URL}/api/universe/character/invalid-character-id-12345/stories")
        assert response.status_code == 404, f"Expected 404 for invalid character, got {response.status_code}"


class TestFollowCharacter:
    """Follow Character - Requires authentication"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping authenticated tests")
        
    def test_follow_requires_auth(self):
        """POST /api/universe/follow should require authentication"""
        response = requests.post(f"{BASE_URL}/api/universe/follow", json={
            "character_id": KNOWN_CHARACTER_ID
        })
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        
    def test_follow_toggle_with_auth(self, auth_token):
        """Follow toggle should work with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First call - toggle follow
        response = requests.post(
            f"{BASE_URL}/api/universe/follow",
            json={"character_id": KNOWN_CHARACTER_ID},
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "following" in data, "Response should include following state"
        first_state = data["following"]
        
        # Second call - should toggle to opposite state
        response2 = requests.post(
            f"{BASE_URL}/api/universe/follow",
            json={"character_id": KNOWN_CHARACTER_ID},
            headers=headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["following"] != first_state, "Follow should toggle state"
        
    def test_check_following_state(self, auth_token):
        """GET /api/universe/following/{character_id} should return following state"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/universe/following/{KNOWN_CHARACTER_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "following" in data, "Response should include following boolean"
        assert isinstance(data["following"], bool), "following should be a boolean"


class TestNotifications:
    """Notifications API - Requires authentication"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping authenticated tests")
        
    def test_notifications_requires_auth(self):
        """GET /api/universe/notifications should require authentication"""
        response = requests.get(f"{BASE_URL}/api/universe/notifications")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        
    def test_get_notifications_with_auth(self, auth_token):
        """Get notifications should return notifications list and unread_count"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/universe/notifications",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "notifications" in data, "Missing notifications in response"
        assert "unread_count" in data, "Missing unread_count in response"
        assert isinstance(data["notifications"], list), "notifications should be a list"
        assert isinstance(data["unread_count"], int), "unread_count should be an integer"
        
    def test_mark_notifications_read(self, auth_token):
        """POST /api/universe/notifications/read should mark all as read"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/universe/notifications/read",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True


class TestSeriesEpisodes:
    """Series Episodes API - Public endpoint"""
    
    def test_series_episodes_invalid_id_returns_404(self):
        """Invalid series ID should return 404"""
        response = requests.get(f"{BASE_URL}/api/universe/series/invalid-series-id-12345/episodes")
        assert response.status_code == 404, f"Expected 404 for invalid series, got {response.status_code}"
        
    def test_series_continue_invalid_id_returns_404(self):
        """Invalid series ID for continue should return 404"""
        response = requests.post(f"{BASE_URL}/api/universe/series/invalid-series-id-12345/continue")
        assert response.status_code == 404, f"Expected 404 for invalid series, got {response.status_code}"


class TestPublicCharacterPage:
    """Public Character Page API - No auth required"""
    
    def test_public_character_endpoint(self):
        """GET /api/public/character/{id} should return character data"""
        response = requests.get(f"{BASE_URL}/api/public/character/{KNOWN_CHARACTER_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_public_character_returns_expected_structure(self):
        """Public character should return character, visual_bible, social_proof, etc."""
        response = requests.get(f"{BASE_URL}/api/public/character/{KNOWN_CHARACTER_ID}")
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert "character" in data, "Missing character in response"
        
        character = data["character"]
        assert "name" in character, "Character should have name"
        
    def test_public_character_invalid_id_returns_error(self):
        """Invalid character ID should return error"""
        response = requests.get(f"{BASE_URL}/api/public/character/invalid-character-id-12345")
        # Should return 404 or success=False
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == False or "error" in data
        else:
            assert response.status_code == 404


class TestMyFollows:
    """My Follows API - Requires authentication"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping authenticated tests")
        
    def test_my_follows_requires_auth(self):
        """GET /api/universe/my-follows should require authentication"""
        response = requests.get(f"{BASE_URL}/api/universe/my-follows")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        
    def test_my_follows_with_auth(self, auth_token):
        """Get my follows should return list of followed characters"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/universe/my-follows",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "characters" in data, "Missing characters in response"
        assert isinstance(data["characters"], list), "characters should be a list"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
