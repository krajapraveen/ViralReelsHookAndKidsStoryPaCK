"""
Retention Layer Testing - Iteration 471
Tests for:
1. In-App Notification System (NotificationBell, aggregated notifications)
2. Daily Challenge system (admin-configurable challenges)
3. Ownership Messaging (remix stats)
4. Mock email service (admin preview)
5. Soft leaderboard (Top Stories Today)
6. P0 regression: Failed job deep-link recovery
"""
import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
FAILED_JOB_ID = "764f785f-63b2-4cc2-ba5c-1a5f4fd1f907"
CHALLENGE_ID = "ch_766226ee017e"


@pytest.fixture(scope="module")
def test_user_token():
    """Get auth token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get auth token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture
def test_user_headers(test_user_token):
    return {"Authorization": f"Bearer {test_user_token}", "Content-Type": "application/json"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


class TestDailyChallengeSystem:
    """Tests for Daily Challenge endpoints"""

    def test_get_todays_challenge(self):
        """GET /api/retention/challenge/today returns today's challenge"""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/today")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        # Challenge may or may not exist for today
        challenge = data.get("challenge")
        if challenge:
            assert "challenge_id" in challenge
            assert "title" in challenge
            assert "active_date" in challenge
            print(f"Today's challenge: {challenge.get('title')} (ID: {challenge.get('challenge_id')})")
        else:
            print("No challenge configured for today")

    def test_create_challenge_admin_only(self, admin_headers):
        """POST /api/retention/challenge creates a new challenge (admin only)"""
        tomorrow = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))
        from datetime import timedelta
        future_date = (tomorrow + timedelta(days=30)).strftime("%Y-%m-%d")
        
        payload = {
            "title": "Test Challenge - Iteration 471",
            "prompt_seed": "Write a story about a magical adventure",
            "active_date": future_date,
            "category": "adventure"
        }
        response = requests.post(f"{BASE_URL}/api/retention/challenge", json=payload, headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        challenge = data.get("challenge")
        assert challenge is not None
        assert challenge.get("title") == payload["title"]
        assert challenge.get("active_date") == future_date
        assert "challenge_id" in challenge
        print(f"Created challenge: {challenge.get('challenge_id')}")

    def test_create_challenge_non_admin_forbidden(self, test_user_headers):
        """Non-admin cannot create challenges via POST /api/retention/challenge -> 403"""
        payload = {
            "title": "Unauthorized Challenge",
            "prompt_seed": "This should fail",
            "active_date": "2026-12-31",
            "category": "test"
        }
        response = requests.post(f"{BASE_URL}/api/retention/challenge", json=payload, headers=test_user_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Non-admin correctly blocked from creating challenges")

    def test_create_challenge_missing_fields(self, admin_headers):
        """POST /api/retention/challenge with missing fields returns 400"""
        payload = {"title": "Missing Date"}  # Missing active_date
        response = requests.post(f"{BASE_URL}/api/retention/challenge", json=payload, headers=admin_headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"

    def test_get_challenge_entries(self):
        """GET /api/retention/challenge/{challenge_id}/entries returns entries"""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/{CHALLENGE_ID}/entries")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "entries" in data
        print(f"Challenge {CHALLENGE_ID} has {len(data.get('entries', []))} entries")


class TestRemixStats:
    """Tests for Ownership Messaging / Remix Stats"""

    def test_get_remix_stats(self, test_user_headers):
        """POST /api/retention/remix-stats returns remix counts for given job_ids"""
        payload = {"job_ids": [FAILED_JOB_ID, "nonexistent-job-id"]}
        response = requests.post(f"{BASE_URL}/api/retention/remix-stats", json=payload, headers=test_user_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "stats" in data
        stats = data.get("stats", {})
        print(f"Remix stats: {stats}")

    def test_get_remix_stats_empty_list(self, test_user_headers):
        """POST /api/retention/remix-stats with empty list returns empty stats"""
        payload = {"job_ids": []}
        response = requests.post(f"{BASE_URL}/api/retention/remix-stats", json=payload, headers=test_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert data.get("stats") == {}

    def test_get_remix_stats_too_many_ids(self, test_user_headers):
        """POST /api/retention/remix-stats with >100 IDs returns empty stats"""
        payload = {"job_ids": [f"job-{i}" for i in range(101)]}
        response = requests.post(f"{BASE_URL}/api/retention/remix-stats", json=payload, headers=test_user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("stats") == {}


class TestTopStoriesLeaderboard:
    """Tests for Soft Leaderboard (Top Stories Today)"""

    def test_get_top_stories(self):
        """GET /api/retention/top-stories returns top stories (may be empty)"""
        response = requests.get(f"{BASE_URL}/api/retention/top-stories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "stories" in data
        stories = data.get("stories", [])
        print(f"Top stories count: {len(stories)}")
        # Stories may be empty if no gallery_opt_in jobs exist
        if stories:
            for story in stories[:3]:
                print(f"  - {story.get('title')} ({story.get('views', 0)} views)")


class TestEmailEventsPreview:
    """Tests for Mock Email Service Admin Preview"""

    def test_get_email_events_admin(self, admin_headers):
        """GET /api/retention/email-events returns simulated email events (admin only)"""
        response = requests.get(f"{BASE_URL}/api/retention/email-events", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "events" in data
        assert "total" in data
        events = data.get("events", [])
        print(f"Email events: {len(events)} (total: {data.get('total')})")
        if events:
            for event in events[:3]:
                print(f"  - {event.get('template')}: {event.get('subject')}")

    def test_get_email_events_non_admin_forbidden(self, test_user_headers):
        """Non-admin cannot access /api/retention/email-events -> 403"""
        response = requests.get(f"{BASE_URL}/api/retention/email-events", headers=test_user_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Non-admin correctly blocked from email events preview")


class TestNotificationSystem:
    """Tests for In-App Notification System"""

    def test_get_notifications(self, test_user_headers):
        """GET /api/universe/notifications returns user notifications"""
        response = requests.get(f"{BASE_URL}/api/universe/notifications", headers=test_user_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "notifications" in data
        assert "unread_count" in data
        notifications = data.get("notifications", [])
        unread = data.get("unread_count", 0)
        print(f"Notifications: {len(notifications)} (unread: {unread})")
        # Check notification structure
        for n in notifications[:3]:
            assert "type" in n
            assert "title" in n
            print(f"  - [{n.get('type')}] {n.get('title')}")

    def test_mark_notifications_read(self, test_user_headers):
        """POST /api/universe/notifications/read marks notifications as read"""
        response = requests.post(f"{BASE_URL}/api/universe/notifications/read", headers=test_user_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        print("Notifications marked as read")


class TestP0RegressionFailedJobRecovery:
    """P0 Regression: Failed job deep-link opens recovery screen"""

    def test_failed_job_status_returns_view_mode(self, test_user_headers):
        """GET /api/story-engine/status/{job_id} returns view_mode for failed jobs"""
        response = requests.get(f"{BASE_URL}/api/story-engine/status/{FAILED_JOB_ID}", headers=test_user_headers)
        # Job may not exist or may be owned by different user
        if response.status_code == 404:
            pytest.skip(f"Failed job {FAILED_JOB_ID} not found")
        if response.status_code == 403:
            pytest.skip(f"Failed job {FAILED_JOB_ID} not owned by test user")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        job = data.get("job", {})
        
        # Check view_mode field exists
        assert "view_mode" in job, "view_mode field missing from job response"
        view_mode = job.get("view_mode")
        print(f"Job {FAILED_JOB_ID} view_mode: {view_mode}")
        
        # If job is failed, view_mode should be 'failed_recovery'
        state = job.get("engine_state") or job.get("status")
        if state in ("FAILED", "FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER"):
            assert view_mode == "failed_recovery", f"Expected view_mode='failed_recovery' for failed job, got '{view_mode}'"
            print("PASS: Failed job correctly returns view_mode='failed_recovery'")

    def test_failed_job_has_failure_detail(self, test_user_headers):
        """Failed jobs should have human-readable failure_detail"""
        response = requests.get(f"{BASE_URL}/api/story-engine/status/{FAILED_JOB_ID}", headers=test_user_headers)
        if response.status_code in (404, 403):
            pytest.skip(f"Failed job {FAILED_JOB_ID} not accessible")
        
        data = response.json()
        job = data.get("job", {})
        state = job.get("engine_state") or job.get("status")
        
        if state in ("FAILED", "FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER"):
            failure_detail = job.get("failure_detail")
            if failure_detail:
                assert "title" in failure_detail
                assert "suggestion" in failure_detail
                print(f"Failure detail: {failure_detail.get('title')}")
            else:
                print("No failure_detail (may be legacy job)")


class TestDashboardIntegration:
    """Tests for Dashboard integration with retention features"""

    def test_dashboard_story_feed(self, test_user_headers):
        """GET /api/engagement/story-feed returns feed data"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=test_user_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Feed should have rows, features, etc.
        assert "rows" in data or "hero" in data or "features" in data
        print(f"Story feed loaded successfully")


class TestHealthCheck:
    """Basic health checks"""

    def test_api_health(self):
        """API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("API health: OK")

    def test_retention_routes_registered(self):
        """Verify retention routes are registered"""
        # Test a public endpoint
        response = requests.get(f"{BASE_URL}/api/retention/challenge/today")
        assert response.status_code == 200
        print("Retention routes registered: OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
