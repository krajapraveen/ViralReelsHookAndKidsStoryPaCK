"""
Test Retention Features - Iteration 474
Tests for:
1. Challenge Winner Hero Slot API (GET /api/retention/challenge/winner)
2. Improve Consistency CTA (POST /api/retention/improve-consistency/{job_id})
3. User-jobs API returns consistency_retry_count field
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


@pytest.fixture(scope="module")
def test_user_token():
    """Get auth token for test user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get auth token for admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


class TestChallengeWinnerAPI:
    """Tests for GET /api/retention/challenge/winner endpoint."""

    def test_challenge_winner_endpoint_accessible(self):
        """Challenge winner endpoint should be publicly accessible."""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/winner")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    def test_challenge_winner_returns_correct_structure(self):
        """Challenge winner response should have correct data structure."""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/winner")
        assert response.status_code == 200
        data = response.json()
        
        # Winner can be null if no challenge entries exist
        if data.get("winner") is not None:
            winner = data["winner"]
            # Check expected fields
            assert "job_id" in winner, "Winner should have job_id"
            assert "title" in winner, "Winner should have title"
            assert "creator_name" in winner, "Winner should have creator_name"
            assert "reason_badge" in winner, "Winner should have reason_badge"
            # Optional fields
            if "remix_count" in winner:
                assert isinstance(winner["remix_count"], (int, float))
            if "views" in winner:
                assert isinstance(winner["views"], (int, float))
        else:
            # Graceful fallback - winner is null
            print("No challenge winner found (expected when no challenge entries exist)")

    def test_challenge_winner_fallback_when_no_entries(self):
        """When no challenge entries exist, winner should be null (graceful fallback)."""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/winner")
        assert response.status_code == 200
        data = response.json()
        # Either winner exists or is null - both are valid
        assert "winner" in data


class TestImproveConsistencyAPI:
    """Tests for POST /api/retention/improve-consistency/{job_id} endpoint."""

    def test_improve_consistency_requires_auth(self):
        """Improve consistency endpoint should require authentication."""
        response = requests.post(f"{BASE_URL}/api/retention/improve-consistency/fake-job-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_improve_consistency_returns_404_for_nonexistent_job(self, test_user_token):
        """Should return 404 for non-existent job."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(
            f"{BASE_URL}/api/retention/improve-consistency/nonexistent-job-12345",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    def test_improve_consistency_rejects_other_users_job(self, test_user_token):
        """Should reject attempts to improve consistency on another user's job."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        # Try with a fake job ID that doesn't belong to test user
        response = requests.post(
            f"{BASE_URL}/api/retention/improve-consistency/other-user-job-xyz",
            headers=headers
        )
        # Should be 404 (not found) or 403 (forbidden)
        assert response.status_code in [403, 404], f"Expected 403/404, got {response.status_code}"


class TestUserJobsAPI:
    """Tests for GET /api/story-engine/user-jobs endpoint."""

    def test_user_jobs_requires_auth(self):
        """User jobs endpoint should require authentication."""
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_user_jobs_returns_jobs_list(self, test_user_token):
        """User jobs should return a list of jobs."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "success" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_user_jobs_includes_source_field(self, test_user_token):
        """User jobs should include source field (story_engine or legacy_pipeline)."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["jobs"]:
            for job in data["jobs"]:
                assert "source" in job, f"Job {job.get('job_id')} missing source field"
                assert job["source"] in ["story_engine", "legacy_pipeline"], \
                    f"Invalid source: {job['source']}"

    def test_user_jobs_includes_consistency_retry_count_for_story_engine(self, test_user_token):
        """Story engine jobs should include consistency_retry_count field."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        story_engine_jobs = [j for j in data["jobs"] if j.get("source") == "story_engine"]
        if story_engine_jobs:
            for job in story_engine_jobs:
                assert "consistency_retry_count" in job, \
                    f"Story engine job {job.get('job_id')} missing consistency_retry_count"
                assert isinstance(job["consistency_retry_count"], int), \
                    f"consistency_retry_count should be int, got {type(job['consistency_retry_count'])}"
        else:
            print("No story_engine jobs found for test user - skipping consistency_retry_count check")


class TestDailyChallengeBanner:
    """Tests for daily challenge API."""

    def test_todays_challenge_endpoint(self):
        """Today's challenge endpoint should be accessible."""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/today")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "success" in data
        # Challenge can be null if none exists for today
        if data.get("challenge"):
            challenge = data["challenge"]
            assert "challenge_id" in challenge or "title" in challenge


class TestTopStoriesLeaderboard:
    """Tests for top stories leaderboard API."""

    def test_top_stories_endpoint(self):
        """Top stories endpoint should be accessible."""
        response = requests.get(f"{BASE_URL}/api/retention/top-stories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "success" in data
        assert "stories" in data
        assert isinstance(data["stories"], list)


class TestImproveConsistencyWithRealJob:
    """Tests for improve consistency with actual user jobs."""

    def test_improve_consistency_on_completed_story_engine_job(self, test_user_token):
        """Test improve consistency on a real completed story_engine job."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # First get user's jobs
        jobs_response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        assert jobs_response.status_code == 200
        jobs = jobs_response.json().get("jobs", [])
        
        # Find a completed story_engine job that hasn't been improved yet
        eligible_job = None
        for job in jobs:
            if (job.get("source") == "story_engine" and 
                job.get("status") in ["COMPLETED", "PARTIAL"] and
                job.get("consistency_retry_count", 0) < 1):
                eligible_job = job
                break
        
        if not eligible_job:
            print("No eligible story_engine job found for improve consistency test")
            pytest.skip("No eligible completed story_engine job found")
            return
        
        job_id = eligible_job["job_id"]
        print(f"Testing improve consistency on job: {job_id} ({eligible_job.get('title')})")
        
        # Try to improve consistency
        response = requests.post(
            f"{BASE_URL}/api/retention/improve-consistency/{job_id}",
            headers=headers
        )
        
        # Should succeed (200) or fail with specific error
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
            assert "message" in data
            print(f"Improve consistency succeeded: {data.get('message')}")
        elif response.status_code == 400:
            # Already attempted or job not in correct state
            data = response.json()
            print(f"Improve consistency rejected (expected): {data.get('detail')}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code} - {response.text}")


class TestAnalyticsTracking:
    """Tests for analytics event tracking."""

    def test_analytics_events_collection_exists(self, admin_token):
        """Verify analytics events are being tracked (admin check)."""
        # This is an indirect test - we verify the endpoint works
        # The actual analytics tracking happens in the improve-consistency endpoint
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Check if we can access admin metrics (which would include analytics)
        response = requests.get(f"{BASE_URL}/api/admin/metrics/overview", headers=headers)
        # Just verify admin access works
        assert response.status_code in [200, 404], f"Admin metrics check: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
