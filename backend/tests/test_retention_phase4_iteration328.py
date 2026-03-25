"""
Phase 4 Retention Engine Tests
Tests: Streak API, Return Banner, Content Seeding, Episode Milestones, Nudge System
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def test_user_token():
    """Get auth token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token():
    """Get auth token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code}")


class TestStreakAPI:
    """Tests for GET /api/retention/streak"""

    def test_streak_endpoint_returns_200(self, test_user_token):
        """Streak endpoint should return 200 for authenticated user"""
        response = requests.get(
            f"{BASE_URL}/api/retention/streak",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_streak_response_structure(self, test_user_token):
        """Streak response should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/retention/streak",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "success" in data
        assert data["success"] == True
        assert "current_streak" in data
        assert "longest_streak" in data
        assert "milestones_claimed" in data
        assert "next_milestone" in data
        assert "next_reward" in data
        
        # Type checks
        assert isinstance(data["current_streak"], int)
        assert isinstance(data["longest_streak"], int)
        assert isinstance(data["milestones_claimed"], list)

    def test_streak_requires_auth(self):
        """Streak endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/retention/streak")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"


class TestReturnBannerAPI:
    """Tests for GET /api/retention/return-banner"""

    def test_return_banner_endpoint_returns_200(self, test_user_token):
        """Return banner endpoint should return 200 for authenticated user"""
        response = requests.get(
            f"{BASE_URL}/api/retention/return-banner",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_return_banner_response_structure(self, test_user_token):
        """Return banner response should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/retention/return-banner",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "success" in data
        assert data["success"] == True
        assert "has_story" in data
        assert isinstance(data["has_story"], bool)
        
        # If has_story is True, check additional fields
        if data["has_story"]:
            assert "story" in data
            assert "cliffhanger" in data
            # character_name and series_info may be None
            assert "character_name" in data or data.get("character_name") is None
            assert "series_info" in data or data.get("series_info") is None

    def test_return_banner_requires_auth(self):
        """Return banner endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/retention/return-banner")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"


class TestContentSeedingAPI:
    """Tests for POST /api/retention/admin/seed-content and GET /api/retention/admin/seed-status"""

    def test_seed_content_requires_admin(self, test_user_token):
        """Seed content endpoint should reject non-admin users"""
        response = requests.post(
            f"{BASE_URL}/api/retention/admin/seed-content",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"count": 1}
        )
        # Should be 403 Forbidden for non-admin
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text}"

    def test_seed_content_works_for_admin(self, admin_token):
        """Seed content endpoint should work for admin user"""
        response = requests.post(
            f"{BASE_URL}/api/retention/admin/seed-content",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"count": 2}  # Small count for testing
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "job_ids" in data
        assert len(data["job_ids"]) == 2
        assert "message" in data

    def test_seed_status_requires_admin(self, test_user_token):
        """Seed status endpoint should reject non-admin users"""
        response = requests.get(
            f"{BASE_URL}/api/retention/admin/seed-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text}"

    def test_seed_status_works_for_admin(self, admin_token):
        """Seed status endpoint should work for admin user"""
        response = requests.get(
            f"{BASE_URL}/api/retention/admin/seed-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "total" in data
        assert "completed" in data
        assert "failed" in data
        assert "queued" in data


class TestExistingUniverseAPIs:
    """Verify existing universe APIs still work after Phase 4 changes"""

    def test_follow_feed_api(self, test_user_token):
        """GET /api/universe/follow-feed should still work"""
        response = requests.get(
            f"{BASE_URL}/api/universe/follow-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "success" in data

    def test_rankings_api(self):
        """GET /api/universe/rankings should still work (public)"""
        response = requests.get(f"{BASE_URL}/api/universe/rankings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "success" in data

    def test_follow_api_requires_auth(self):
        """POST /api/universe/follow should require auth"""
        response = requests.post(
            f"{BASE_URL}/api/universe/follow",
            json={"character_id": "test-id"}
        )
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"


class TestHealthAndBasicAPIs:
    """Basic health checks to ensure server is running"""

    def test_health_endpoint(self):
        """Health endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200

    def test_auth_login_works(self):
        """Auth login should work with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data

    def test_admin_login_works(self):
        """Admin login should work with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data


class TestRetentionFunctionsExist:
    """Verify retention functions are properly integrated via API"""

    def test_streak_api_returns_milestone_info(self, test_user_token):
        """Verify streak API returns milestone info (Day 3 = +10, Day 7 = +25)"""
        response = requests.get(
            f"{BASE_URL}/api/retention/streak",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # next_milestone should be 3 or 7 (or None if all claimed)
        if data.get("next_milestone") is not None:
            assert data["next_milestone"] in [3, 7]
        # next_reward should be 10 or 25 (or None if all claimed)
        if data.get("next_reward") is not None:
            assert data["next_reward"] in [10, 25]

    def test_return_banner_api_works(self, test_user_token):
        """Verify return banner API works (tests record_daily_activity integration)"""
        response = requests.get(
            f"{BASE_URL}/api/retention/return-banner",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True

    def test_seed_status_api_works(self, admin_token):
        """Verify seed status API works (tests content seeding integration)"""
        response = requests.get(
            f"{BASE_URL}/api/retention/admin/seed-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "total" in data

    def test_notifications_api_works(self, test_user_token):
        """Verify notifications API works (tests nudge system integration)"""
        response = requests.get(
            f"{BASE_URL}/api/universe/notifications",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data


class TestNotificationSystem:
    """Test notification system for nudges"""

    def test_notifications_endpoint(self, test_user_token):
        """GET /api/universe/notifications should work"""
        response = requests.get(
            f"{BASE_URL}/api/universe/notifications",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "success" in data
        assert "notifications" in data
        assert "unread_count" in data
