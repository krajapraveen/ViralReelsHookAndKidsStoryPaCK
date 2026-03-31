"""
Test Suite for Universal Generation Status Page Features (Iteration 388)

Tests:
1. Backend: POST /api/notifications/generation/{job_id}/subscribe returns 404 for nonexistent jobs
2. Backend: GET /api/notifications/unread-count returns unread_count field
3. Backend: GET /api/story-engine/status/{job_id} returns timing.elapsed_seconds and timing.eta_seconds
4. Backend: GET /api/story-engine/status/{job_id} returns notification_opt_in field
5. Backend: GET /api/story-engine/status/{job_id} returns retry_info with can_retry field
6. Backend: GET /api/story-engine/status/{job_id} returns credits_refunded field
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


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


@pytest.fixture(scope="module")
def existing_job_id(authenticated_client):
    """Get an existing story_engine job ID from user's jobs (not legacy_pipeline)"""
    response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
    if response.status_code == 200:
        data = response.json()
        jobs = data.get("jobs", [])
        # Filter for story_engine jobs only (not legacy_pipeline)
        story_engine_jobs = [j for j in jobs if j.get("source") == "story_engine"]
        if story_engine_jobs:
            return story_engine_jobs[0].get("job_id")
        # Fallback to any job if no story_engine jobs
        if jobs:
            return jobs[0].get("job_id")
    pytest.skip("No existing jobs found for testing")


class TestNotificationSubscription:
    """Tests for POST /api/notifications/generation/{job_id}/subscribe"""
    
    def test_subscribe_nonexistent_job_returns_404(self, authenticated_client):
        """POST /api/notifications/generation/{job_id}/subscribe returns 404 for nonexistent jobs"""
        fake_job_id = str(uuid.uuid4())
        response = authenticated_client.post(
            f"{BASE_URL}/api/notifications/generation/{fake_job_id}/subscribe"
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"PASS: Subscribe to nonexistent job returns 404")
    
    def test_subscribe_existing_job_returns_success(self, authenticated_client, existing_job_id):
        """POST /api/notifications/generation/{job_id}/subscribe returns success for existing jobs"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/notifications/generation/{existing_job_id}/subscribe"
        )
        # Should return 200 for existing job
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        assert "subscribed" in data or "message" in data, f"Expected subscribed or message field, got {data}"
        print(f"PASS: Subscribe to existing job returns success")


class TestNotificationUnreadCount:
    """Tests for GET /api/notifications/unread-count"""
    
    def test_unread_count_returns_field(self, authenticated_client):
        """GET /api/notifications/unread-count returns unread_count field"""
        response = authenticated_client.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "unread_count" in data, f"Expected unread_count field, got {data}"
        assert isinstance(data["unread_count"], int), f"Expected unread_count to be int, got {type(data['unread_count'])}"
        print(f"PASS: Unread count endpoint returns unread_count field: {data['unread_count']}")


class TestStoryEngineStatusTiming:
    """Tests for timing fields in GET /api/story-engine/status/{job_id}"""
    
    def test_status_returns_timing_object(self, authenticated_client, existing_job_id):
        """GET /api/story-engine/status/{job_id} returns timing object"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        
        job = data.get("job", {})
        assert "timing" in job, f"Expected timing field in job, got keys: {job.keys()}"
        print(f"PASS: Status returns timing object")
    
    def test_status_timing_has_elapsed_seconds(self, authenticated_client, existing_job_id):
        """GET /api/story-engine/status/{job_id} returns timing.elapsed_seconds"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200
        data = response.json()
        
        job = data.get("job", {})
        timing = job.get("timing", {})
        assert "elapsed_seconds" in timing, f"Expected elapsed_seconds in timing, got {timing}"
        # elapsed_seconds can be 0 or positive int
        assert isinstance(timing["elapsed_seconds"], (int, float)), f"Expected elapsed_seconds to be numeric, got {type(timing['elapsed_seconds'])}"
        print(f"PASS: Status returns timing.elapsed_seconds: {timing['elapsed_seconds']}")
    
    def test_status_timing_has_eta_seconds(self, authenticated_client, existing_job_id):
        """GET /api/story-engine/status/{job_id} returns timing.eta_seconds (may be null for completed jobs)"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200
        data = response.json()
        
        job = data.get("job", {})
        timing = job.get("timing", {})
        assert "eta_seconds" in timing, f"Expected eta_seconds in timing, got {timing}"
        # eta_seconds can be null for completed jobs or a positive int for in-progress jobs
        eta = timing["eta_seconds"]
        assert eta is None or isinstance(eta, (int, float)), f"Expected eta_seconds to be null or numeric, got {type(eta)}"
        print(f"PASS: Status returns timing.eta_seconds: {eta}")


class TestStoryEngineStatusNotificationOptIn:
    """Tests for notification_opt_in field in GET /api/story-engine/status/{job_id}"""
    
    def test_status_returns_notification_opt_in(self, authenticated_client, existing_job_id):
        """GET /api/story-engine/status/{job_id} returns notification_opt_in field"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200
        data = response.json()
        
        job = data.get("job", {})
        assert "notification_opt_in" in job, f"Expected notification_opt_in field in job, got keys: {job.keys()}"
        assert isinstance(job["notification_opt_in"], bool), f"Expected notification_opt_in to be bool, got {type(job['notification_opt_in'])}"
        print(f"PASS: Status returns notification_opt_in: {job['notification_opt_in']}")


class TestStoryEngineStatusRetryInfo:
    """Tests for retry_info field in GET /api/story-engine/status/{job_id}"""
    
    def test_status_returns_retry_info_object(self, authenticated_client, existing_job_id):
        """GET /api/story-engine/status/{job_id} returns retry_info object"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200
        data = response.json()
        
        job = data.get("job", {})
        assert "retry_info" in job, f"Expected retry_info field in job, got keys: {job.keys()}"
        retry_info = job["retry_info"]
        assert isinstance(retry_info, dict), f"Expected retry_info to be dict, got {type(retry_info)}"
        print(f"PASS: Status returns retry_info object")
    
    def test_status_retry_info_has_can_retry(self, authenticated_client, existing_job_id):
        """GET /api/story-engine/status/{job_id} returns retry_info with can_retry field"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200
        data = response.json()
        
        job = data.get("job", {})
        retry_info = job.get("retry_info", {})
        assert "can_retry" in retry_info, f"Expected can_retry in retry_info, got {retry_info}"
        assert isinstance(retry_info["can_retry"], bool), f"Expected can_retry to be bool, got {type(retry_info['can_retry'])}"
        print(f"PASS: Status returns retry_info.can_retry: {retry_info['can_retry']}")
    
    def test_status_retry_info_has_current_attempt(self, authenticated_client, existing_job_id):
        """GET /api/story-engine/status/{job_id} returns retry_info with current_attempt field"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200
        data = response.json()
        
        job = data.get("job", {})
        retry_info = job.get("retry_info", {})
        assert "current_attempt" in retry_info, f"Expected current_attempt in retry_info, got {retry_info}"
        print(f"PASS: Status returns retry_info.current_attempt: {retry_info['current_attempt']}")


class TestStoryEngineStatusCreditsRefunded:
    """Tests for credits_refunded field in GET /api/story-engine/status/{job_id}"""
    
    def test_status_returns_credits_refunded(self, authenticated_client, existing_job_id):
        """GET /api/story-engine/status/{job_id} returns credits_refunded field"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200
        data = response.json()
        
        job = data.get("job", {})
        assert "credits_refunded" in job, f"Expected credits_refunded field in job, got keys: {job.keys()}"
        # credits_refunded should be 0 or positive int
        assert isinstance(job["credits_refunded"], (int, float)), f"Expected credits_refunded to be numeric, got {type(job['credits_refunded'])}"
        assert job["credits_refunded"] >= 0, f"Expected credits_refunded >= 0, got {job['credits_refunded']}"
        print(f"PASS: Status returns credits_refunded: {job['credits_refunded']}")


class TestStoryEngineStatusNonexistent:
    """Tests for nonexistent job handling"""
    
    def test_status_nonexistent_job_returns_404(self, authenticated_client):
        """GET /api/story-engine/status/{job_id} returns 404 for nonexistent jobs"""
        fake_job_id = str(uuid.uuid4())
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{fake_job_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"PASS: Status for nonexistent job returns 404")


class TestStoryEngineStatusFullResponse:
    """Test full status response structure"""
    
    def test_status_full_response_structure(self, authenticated_client, existing_job_id):
        """Verify full status response has all required fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{existing_job_id}")
        assert response.status_code == 200
        data = response.json()
        
        job = data.get("job", {})
        
        # Required fields for Generation Status Page
        required_fields = [
            "job_id", "title", "status", "progress", "current_stage",
            "timing", "notification_opt_in", "retry_info", "credits_refunded"
        ]
        
        missing_fields = [f for f in required_fields if f not in job]
        assert not missing_fields, f"Missing required fields: {missing_fields}"
        
        # Verify timing structure
        timing = job.get("timing", {})
        assert "elapsed_seconds" in timing, "Missing elapsed_seconds in timing"
        assert "eta_seconds" in timing, "Missing eta_seconds in timing"
        
        # Verify retry_info structure
        retry_info = job.get("retry_info", {})
        assert "can_retry" in retry_info, "Missing can_retry in retry_info"
        
        print(f"PASS: Full status response has all required fields")
        print(f"  - job_id: {job['job_id'][:8]}...")
        print(f"  - status: {job['status']}")
        print(f"  - progress: {job['progress']}%")
        print(f"  - timing.elapsed_seconds: {timing['elapsed_seconds']}")
        print(f"  - timing.eta_seconds: {timing['eta_seconds']}")
        print(f"  - notification_opt_in: {job['notification_opt_in']}")
        print(f"  - retry_info.can_retry: {retry_info['can_retry']}")
        print(f"  - credits_refunded: {job['credits_refunded']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
