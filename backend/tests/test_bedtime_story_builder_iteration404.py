"""
Bedtime Story Builder - Backend API Tests (Iteration 404)
Tests for /api/bedtime-story-builder/track and /api/bedtime-story-builder/admin/metrics endpoints
Plus verification of bug fix: no false 'Generation failed' toast
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestBedtimeStoryBuilderTrack:
    """Tests for /api/bedtime-story-builder/track endpoint"""
    
    def test_track_requires_auth(self):
        """Track endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            json={"event_type": "story_generated"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Track endpoint requires auth")
    
    def test_track_valid_event_story_generated(self, auth_headers):
        """Track accepts valid event type: story_generated"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            headers=auth_headers,
            json={"event_type": "story_generated"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("ok") == True, "Response should have ok=true"
        print("PASS: Track accepts story_generated event")
    
    def test_track_valid_event_play_clicked(self, auth_headers):
        """Track accepts valid event type: play_clicked"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            headers=auth_headers,
            json={"event_type": "play_clicked"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("ok") == True
        print("PASS: Track accepts play_clicked event")
    
    def test_track_valid_event_bedtime_mode_enabled(self, auth_headers):
        """Track accepts valid event type: bedtime_mode_enabled"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            headers=auth_headers,
            json={"event_type": "bedtime_mode_enabled"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASS: Track accepts bedtime_mode_enabled event")
    
    def test_track_valid_event_remix_clicked(self, auth_headers):
        """Track accepts valid event type: remix_clicked"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            headers=auth_headers,
            json={"event_type": "remix_clicked"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASS: Track accepts remix_clicked event")
    
    def test_track_valid_event_session_started(self, auth_headers):
        """Track accepts valid event type: session_started"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            headers=auth_headers,
            json={"event_type": "session_started"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASS: Track accepts session_started event")
    
    def test_track_valid_event_session_returned(self, auth_headers):
        """Track accepts valid event type: session_returned"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            headers=auth_headers,
            json={"event_type": "session_returned"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print("PASS: Track accepts session_returned event")
    
    def test_track_rejects_invalid_event_type(self, auth_headers):
        """Track rejects invalid event types with 400"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            headers=auth_headers,
            json={"event_type": "invalid_event_type"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Track rejects invalid event type with 400")
    
    def test_track_rejects_empty_event_type(self, auth_headers):
        """Track rejects empty event type"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/track",
            headers=auth_headers,
            json={"event_type": ""}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Track rejects empty event type")


class TestBedtimeStoryBuilderAdminMetrics:
    """Tests for /api/bedtime-story-builder/admin/metrics endpoint"""
    
    def test_metrics_requires_admin(self, auth_headers):
        """Metrics endpoint requires admin role"""
        response = requests.get(
            f"{BASE_URL}/api/bedtime-story-builder/admin/metrics",
            headers=auth_headers  # Regular user, not admin
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Metrics endpoint requires admin role")
    
    def test_metrics_returns_event_counts(self, admin_headers):
        """Metrics returns event counts for admin"""
        response = requests.get(
            f"{BASE_URL}/api/bedtime-story-builder/admin/metrics",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check structure
        assert "total_unique_users" in data, "Should have total_unique_users"
        assert "events" in data, "Should have events object"
        assert "retention" in data, "Should have retention object"
        
        # Check events structure
        events = data.get("events", {})
        assert "story_generated" in events, "Events should have story_generated count"
        assert "play_clicked" in events, "Events should have play_clicked count"
        assert "bedtime_mode_enabled" in events, "Events should have bedtime_mode_enabled count"
        assert "remix_clicked" in events, "Events should have remix_clicked count"
        assert "session_started" in events, "Events should have session_started count"
        assert "session_returned" in events, "Events should have session_returned count"
        
        # Check retention structure
        retention = data.get("retention", {})
        assert "started_users" in retention, "Retention should have started_users"
        assert "returned_users" in retention, "Retention should have returned_users"
        assert "next_day_retention_pct" in retention, "Retention should have next_day_retention_pct"
        
        print(f"PASS: Metrics returns event counts - {data['total_unique_users']} unique users")


class TestBedtimeStoryBuilderGenerate:
    """Tests for /api/bedtime-story-builder/generate endpoint - Bug fix verification"""
    
    def test_generate_returns_success_true(self, auth_headers):
        """Generate returns success=true for valid request (bug fix verification)"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "6-8",
                "theme": "Friendship",
                "moral": "Be kind",
                "length": "3",
                "voice_style": "calm_parent",
                "child_name": "TestChild",
                "mood": "calm"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # CRITICAL: Verify success=true (bug fix verification)
        assert data.get("success") == True, "Response MUST have success=true"
        
        # Verify story structure
        story = data.get("story", {})
        assert "title" in story, "Story should have title"
        assert "scenes" in story, "Story should have scenes array"
        assert len(story["scenes"]) >= 3, f"Should have at least 3 scenes"
        
        # Verify credits info
        assert data.get("credits_used") == 10, "Should use 10 credits"
        assert "remaining_credits" in data, "Should return remaining credits"
        
        print(f"PASS: Generate returns success=true with {len(story['scenes'])} scenes")
    
    def test_generate_no_error_in_response(self, auth_headers):
        """Generate response should NOT contain error fields on success"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "3-5",
                "theme": "Bedtime Calm",
                "moral": "Be thankful",
                "length": "3",
                "voice_style": "gentle_teacher",
                "mood": "sleepy"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # CRITICAL: No error fields should be present on success
        assert "error" not in data, "Success response should NOT have 'error' field"
        assert "detail" not in data, "Success response should NOT have 'detail' field"
        assert data.get("success") == True, "Must have success=true"
        
        print("PASS: Generate response has no error fields on success")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
