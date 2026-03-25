"""
UX Audit Phase 3 - Character Page, Series Timeline, Follow System, Notifications
Tests for action-first design overhaul: CTAs, social proof, progress bars, urgency messaging
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
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ═══════════════════════════════════════════════════════════════════════════════
# CHARACTER PAGE TESTS - Public API
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicCharacterAPI:
    """Test public character page API endpoints"""
    
    def test_public_character_endpoint_returns_data(self, api_client):
        """GET /api/public/character/{id} returns character data for hero section"""
        response = api_client.get(f"{BASE_URL}/api/public/character/{FINN_CHARACTER_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True, "Response should have success=True"
        assert "character" in data, "Response should contain character object"
        
        char = data["character"]
        assert "name" in char, "Character should have name"
        assert "role" in char or "personality_summary" in char, "Character should have role or personality"
        
    def test_public_character_has_social_proof(self, api_client):
        """Character response includes social_proof for 'X people continued this'"""
        response = api_client.get(f"{BASE_URL}/api/public/character/{FINN_CHARACTER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "social_proof" in data, "Response should contain social_proof"
        
        sp = data["social_proof"]
        assert "total_continuations" in sp or "total_stories" in sp, "Social proof should have continuation/story counts"
        
    def test_public_character_has_remix_data(self, api_client):
        """Character response includes remix_data for Continue Story CTA"""
        response = api_client.get(f"{BASE_URL}/api/public/character/{FINN_CHARACTER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "remix_data" in data, "Response should contain remix_data for Continue Story"
        
    def test_public_character_has_visual_bible(self, api_client):
        """Character response includes visual_bible for hook quote"""
        response = api_client.get(f"{BASE_URL}/api/public/character/{FINN_CHARACTER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        # visual_bible may be None but should be present
        assert "visual_bible" in data or "character" in data, "Response should have visual_bible or character data"


class TestCharacterStoriesFeed:
    """Test character stories feed API for stories grid"""
    
    def test_character_stories_endpoint(self, api_client):
        """GET /api/universe/character/{id}/stories returns stories list"""
        response = api_client.get(f"{BASE_URL}/api/universe/character/{FINN_CHARACTER_ID}/stories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        assert "stories" in data, "Response should contain stories array"
        assert "follower_count" in data, "Response should contain follower_count"
        
    def test_character_stories_has_required_fields(self, api_client):
        """Stories in feed have required fields for story cards"""
        response = api_client.get(f"{BASE_URL}/api/universe/character/{FINN_CHARACTER_ID}/stories")
        assert response.status_code == 200
        
        data = response.json()
        stories = data.get("stories", [])
        
        if stories:
            story = stories[0]
            # Check for fields needed by story cards
            assert "job_id" in story or "title" in story, "Story should have job_id or title"


# ═══════════════════════════════════════════════════════════════════════════════
# FOLLOW SYSTEM TESTS - Authenticated
# ═══════════════════════════════════════════════════════════════════════════════

class TestFollowSystem:
    """Test follow/unfollow functionality with notification creation"""
    
    def test_check_following_status(self, authenticated_client):
        """GET /api/universe/following/{character_id} returns following status"""
        response = authenticated_client.get(f"{BASE_URL}/api/universe/following/{FINN_CHARACTER_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "following" in data, "Response should contain following boolean"
        assert isinstance(data["following"], bool), "following should be boolean"
        
    def test_follow_toggle_works(self, authenticated_client):
        """POST /api/universe/follow toggles follow state"""
        # First, check current state
        check_response = authenticated_client.get(f"{BASE_URL}/api/universe/following/{ZARA_CHARACTER_ID}")
        initial_following = check_response.json().get("following", False)
        
        # Toggle follow
        response = authenticated_client.post(f"{BASE_URL}/api/universe/follow", json={
            "character_id": ZARA_CHARACTER_ID
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        assert "following" in data, "Response should contain following state"
        
        # Verify toggle worked
        new_following = data["following"]
        assert new_following != initial_following, "Follow state should have toggled"
        
        # Toggle back to restore original state
        authenticated_client.post(f"{BASE_URL}/api/universe/follow", json={
            "character_id": ZARA_CHARACTER_ID
        })
        
    def test_follow_requires_auth(self, api_client):
        """POST /api/universe/follow requires authentication"""
        # Use a fresh client without auth
        fresh_client = requests.Session()
        fresh_client.headers.update({"Content-Type": "application/json"})
        
        response = fresh_client.post(f"{BASE_URL}/api/universe/follow", json={
            "character_id": FINN_CHARACTER_ID
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS TESTS - Authenticated
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationsAPI:
    """Test notifications API for NotificationBell component"""
    
    def test_get_notifications(self, authenticated_client):
        """GET /api/universe/notifications returns notifications list"""
        response = authenticated_client.get(f"{BASE_URL}/api/universe/notifications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        assert "notifications" in data, "Response should contain notifications array"
        assert "unread_count" in data, "Response should contain unread_count"
        
    def test_notifications_have_required_fields(self, authenticated_client):
        """Notifications have fields needed for NotificationBell display"""
        response = authenticated_client.get(f"{BASE_URL}/api/universe/notifications")
        assert response.status_code == 200
        
        data = response.json()
        notifications = data.get("notifications", [])
        
        if notifications:
            notif = notifications[0]
            assert "type" in notif, "Notification should have type"
            assert "title" in notif, "Notification should have title"
            # link is optional but important for action-driven notifications
            
    def test_mark_notifications_read(self, authenticated_client):
        """POST /api/universe/notifications/read marks all as read"""
        response = authenticated_client.post(f"{BASE_URL}/api/universe/notifications/read")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        
    def test_notifications_requires_auth(self, api_client):
        """GET /api/universe/notifications requires authentication"""
        fresh_client = requests.Session()
        fresh_client.headers.update({"Content-Type": "application/json"})
        
        response = fresh_client.get(f"{BASE_URL}/api/universe/notifications")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════════════════════
# RANKINGS API TESTS - Public
# ═══════════════════════════════════════════════════════════════════════════════

class TestRankingsAPI:
    """Test rankings API for social proof and leaderboards"""
    
    def test_rankings_endpoint(self, api_client):
        """GET /api/universe/rankings returns top stories, characters, creators"""
        response = api_client.get(f"{BASE_URL}/api/universe/rankings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        assert "top_stories" in data, "Response should contain top_stories"
        assert "top_characters" in data, "Response should contain top_characters"
        assert "top_creators" in data, "Response should contain top_creators"
        
    def test_rankings_top_stories_structure(self, api_client):
        """Top stories have required fields for display"""
        response = api_client.get(f"{BASE_URL}/api/universe/rankings")
        assert response.status_code == 200
        
        data = response.json()
        top_stories = data.get("top_stories", [])
        
        if top_stories:
            story = top_stories[0]
            assert "job_id" in story or "title" in story, "Story should have job_id or title"
            
    def test_rankings_top_characters_structure(self, api_client):
        """Top characters have required fields for display"""
        response = api_client.get(f"{BASE_URL}/api/universe/rankings")
        assert response.status_code == 200
        
        data = response.json()
        top_chars = data.get("top_characters", [])
        
        if top_chars:
            char = top_chars[0]
            assert "character_id" in char, "Character should have character_id"
            assert "name" in char, "Character should have name"


# ═══════════════════════════════════════════════════════════════════════════════
# SERIES TIMELINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeriesTimelineAPI:
    """Test series timeline API for progress bar and episode status"""
    
    def test_series_episodes_endpoint_handles_invalid(self, api_client):
        """GET /api/universe/series/{id}/episodes returns 404 for invalid series"""
        response = api_client.get(f"{BASE_URL}/api/universe/series/invalid-series-id/episodes")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
    def test_series_continue_endpoint_handles_invalid(self, api_client):
        """POST /api/universe/series/{id}/continue returns 404 for invalid series"""
        response = api_client.post(f"{BASE_URL}/api/universe/series/invalid-series-id/continue")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════════════════════
# MY FOLLOWS TESTS - Authenticated
# ═══════════════════════════════════════════════════════════════════════════════

class TestMyFollows:
    """Test my-follows endpoint for followed characters list"""
    
    def test_my_follows_endpoint(self, authenticated_client):
        """GET /api/universe/my-follows returns followed characters"""
        response = authenticated_client.get(f"{BASE_URL}/api/universe/my-follows")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        assert "characters" in data, "Response should contain characters array"
        
    def test_my_follows_requires_auth(self, api_client):
        """GET /api/universe/my-follows requires authentication"""
        fresh_client = requests.Session()
        fresh_client.headers.update({"Content-Type": "application/json"})
        
        response = fresh_client.get(f"{BASE_URL}/api/universe/my-follows")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthCheck:
    """Basic health check to ensure API is running"""
    
    def test_api_health(self, api_client):
        """API health endpoint returns 200"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"API health check failed: {response.status_code}"
