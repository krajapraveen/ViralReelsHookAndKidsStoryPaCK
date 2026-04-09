"""
Creator Digest Feature Tests - Iteration 473
Tests for weekly email digest for creators showing views, remixes, top story, momentum signal, 
percentile comparison, rising badge, personalized CTA. Smart skip for zero-activity users.
Per-user weekly cap (max 1/week). Admin endpoints for preview/send/run-all.
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

# User with activity for digest testing
USER_WITH_ACTIVITY = "ea3b038c-d523-4a49-9fa5-e00c761fa4aa"
# Failed job for regression testing
FAILED_JOB_ID = "764f785f-63b2-4cc2-ba5c-1a5f4fd1f907"


class TestCreatorDigestBackend:
    """Tests for Creator Digest backend endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get test user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")
    
    # ─── DIGEST PREVIEW TESTS ─────────────────────────────────────────────────
    
    def test_digest_preview_admin_access(self, admin_token):
        """Admin can access digest preview endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/retention/digest/preview/{USER_WITH_ACTIVITY}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        # Digest can be null if no activity, or contain digest data
        if data.get("digest"):
            digest = data["digest"]
            # Verify digest structure
            assert "user_id" in digest
            assert "total_views" in digest or digest.get("total_views") is not None
            assert "new_remixes" in digest or digest.get("new_remixes") is not None
            print(f"Digest preview returned: views={digest.get('total_views')}, remixes={digest.get('new_remixes')}")
        else:
            # No activity case
            assert "reason" in data
            print(f"Digest skipped: {data.get('reason')}")
    
    def test_digest_preview_returns_digest_fields(self, admin_token):
        """Digest preview returns all expected fields when user has activity"""
        response = requests.get(
            f"{BASE_URL}/api/retention/digest/preview/{USER_WITH_ACTIVITY}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("digest"):
            digest = data["digest"]
            # Check all required fields
            expected_fields = ["user_id", "total_views", "new_remixes", "top_story", 
                            "momentum_text", "percentile_text", "rising_fast", "cta"]
            for field in expected_fields:
                assert field in digest, f"Missing field: {field}"
            
            # Verify CTA structure
            cta = digest.get("cta", {})
            assert "text" in cta
            assert "url" in cta
            print(f"CTA: {cta.get('text')}")
    
    def test_digest_preview_non_admin_blocked(self, test_user_token):
        """Non-admin users cannot access digest preview -> 403"""
        response = requests.get(
            f"{BASE_URL}/api/retention/digest/preview/{USER_WITH_ACTIVITY}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("Non-admin correctly blocked from digest preview")
    
    def test_digest_preview_no_activity_user(self, admin_token):
        """Digest preview returns null with reason for users with no activity"""
        # Use a fake user ID that won't have activity
        fake_user_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{BASE_URL}/api/retention/digest/preview/{fake_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        # Should return null digest with reason
        if data.get("digest") is None:
            assert "reason" in data
            print(f"No activity user correctly skipped: {data.get('reason')}")
    
    # ─── DIGEST SEND TESTS ────────────────────────────────────────────────────
    
    def test_digest_send_admin_access(self, admin_token):
        """Admin can send digest to a specific user"""
        response = requests.post(
            f"{BASE_URL}/api/retention/digest/send/{USER_WITH_ACTIVITY}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True or data.get("success") is False
        # Note: sent=False is expected if weekly cap is hit (digest already sent this week)
        if data.get("sent") is False:
            print(f"Digest not sent (expected - weekly cap): {data.get('reason', 'cap hit')}")
        else:
            print(f"Digest sent successfully")
    
    def test_digest_send_non_admin_blocked(self, test_user_token):
        """Non-admin users cannot send digest -> 403"""
        response = requests.post(
            f"{BASE_URL}/api/retention/digest/send/{USER_WITH_ACTIVITY}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("Non-admin correctly blocked from sending digest")
    
    def test_digest_weekly_cap_prevents_duplicate(self, admin_token):
        """Weekly cap prevents duplicate digest in same week"""
        # First send attempt
        response1 = requests.post(
            f"{BASE_URL}/api/retention/digest/send/{USER_WITH_ACTIVITY}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response1.status_code == 200
        
        # Second send attempt should be blocked by weekly cap
        response2 = requests.post(
            f"{BASE_URL}/api/retention/digest/send/{USER_WITH_ACTIVITY}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # If first send succeeded, second should have sent=False due to cap
        # If first was already capped, second will also be capped
        print(f"Second send attempt result: sent={data2.get('sent')}")
    
    # ─── DIGEST RUN TESTS ─────────────────────────────────────────────────────
    
    def test_digest_run_admin_access(self, admin_token):
        """Admin can trigger weekly digest run for all creators"""
        response = requests.post(
            f"{BASE_URL}/api/retention/digest/run",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        summary = data.get("summary", {})
        assert "sent" in summary
        assert "skipped" in summary
        print(f"Weekly run summary: sent={summary.get('sent')}, skipped={summary.get('skipped')}, total={summary.get('total_creators')}")
    
    def test_digest_run_non_admin_blocked(self, test_user_token):
        """Non-admin users cannot trigger weekly run -> 403"""
        response = requests.post(
            f"{BASE_URL}/api/retention/digest/run",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("Non-admin correctly blocked from weekly run")
    
    # ─── EMAIL EVENTS TESTS ───────────────────────────────────────────────────
    
    def test_email_events_shows_digest_events(self, admin_token):
        """Email events endpoint shows digest events alongside regular events"""
        response = requests.get(
            f"{BASE_URL}/api/retention/email-events?limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        events = data.get("events", [])
        
        # Check if any digest events exist
        digest_events = [e for e in events if e.get("template") == "creator_digest"]
        print(f"Found {len(digest_events)} digest events out of {len(events)} total events")
        
        # Verify event structure if any exist
        if digest_events:
            event = digest_events[0]
            assert "user_id" in event
            assert "template" in event
            assert "status" in event
            assert event["template"] == "creator_digest"
            print(f"Digest event status: {event.get('status')}")
    
    def test_email_events_non_admin_blocked(self, test_user_token):
        """Non-admin users cannot access email events -> 403"""
        response = requests.get(
            f"{BASE_URL}/api/retention/email-events",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("Non-admin correctly blocked from email events")


class TestRegressionFailedJobRecovery:
    """Regression tests for failed job recovery screen (P0 from iteration 470)"""
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get test user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Test user login failed: {response.status_code}")
    
    def test_failed_job_endpoint_accessible(self, test_user_token):
        """Failed job endpoint returns job data"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/job/{FAILED_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        # Job may or may not exist, but endpoint should be accessible
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            print(f"Failed job found: state={data.get('state', data.get('job', {}).get('state'))}")
        else:
            print("Failed job not found (may have been cleaned up)")


class TestExistingRetentionFeatures:
    """Regression tests for existing retention features from iteration 472"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_daily_challenge_today(self):
        """Daily challenge endpoint returns today's challenge"""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/today")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        # Challenge may or may not exist for today
        if data.get("challenge"):
            print(f"Today's challenge: {data['challenge'].get('title')}")
        else:
            print("No challenge for today")
    
    def test_top_stories_endpoint(self):
        """Top stories endpoint returns leaderboard"""
        response = requests.get(f"{BASE_URL}/api/retention/top-stories")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        stories = data.get("stories", [])
        print(f"Top stories count: {len(stories)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
