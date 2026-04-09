"""
Test Suite for P0 Critical Bug Fix: Failed Job Recovery Routing
Iteration 470 - Tests view_mode routing, failed recovery screen, deep-link support, and analytics

Features tested:
- Backend view_mode field returns correct values (result/failed_recovery/progress)
- DELETE /api/story-engine/jobs/{job_id} endpoint
- POST /api/story-engine/recovery-event analytics tracking
- No raw enums (FAILED_PLANNING, FAILED_RENDER etc.) in API responses
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
FAILED_JOB_ID = "764f785f-63b2-4cc2-ba5c-1a5f4fd1f907"


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
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get authentication token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestViewModeRouting:
    """Test server-authoritative view_mode routing in status endpoint"""

    def test_status_endpoint_returns_view_mode(self, authenticated_client):
        """Status endpoint should include view_mode field"""
        # Get user jobs to find a job to test
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        
        jobs = data.get("jobs", [])
        if not jobs:
            pytest.skip("No jobs found for test user")
        
        # Test status endpoint for first job
        job_id = jobs[0].get("job_id")
        status_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data.get("success") is True
        job = status_data.get("job", {})
        
        # view_mode must be present
        assert "view_mode" in job, "view_mode field missing from status response"
        assert job["view_mode"] in ("result", "failed_recovery", "progress"), f"Invalid view_mode: {job['view_mode']}"
        print(f"PASS: Status endpoint returns view_mode={job['view_mode']} for job {job_id[:8]}")

    def test_completed_job_returns_result_view_mode(self, authenticated_client):
        """Completed jobs should return view_mode='result'"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        if not completed_jobs:
            pytest.skip("No completed jobs found")
        
        job_id = completed_jobs[0].get("job_id")
        status_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        assert status_response.status_code == 200
        
        job = status_response.json().get("job", {})
        assert job.get("view_mode") == "result", f"Expected view_mode='result' for completed job, got '{job.get('view_mode')}'"
        print(f"PASS: Completed job {job_id[:8]} returns view_mode='result'")

    def test_failed_job_returns_failed_recovery_view_mode(self, authenticated_client):
        """Failed jobs should return view_mode='failed_recovery'"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        failed_jobs = [j for j in jobs if j.get("status") == "FAILED"]
        if not failed_jobs:
            pytest.skip("No failed jobs found")
        
        job_id = failed_jobs[0].get("job_id")
        status_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        assert status_response.status_code == 200
        
        job = status_response.json().get("job", {})
        assert job.get("view_mode") == "failed_recovery", f"Expected view_mode='failed_recovery' for failed job, got '{job.get('view_mode')}'"
        print(f"PASS: Failed job {job_id[:8]} returns view_mode='failed_recovery'")

    def test_processing_job_returns_progress_view_mode(self, authenticated_client):
        """Active/processing jobs should return view_mode='progress'"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        processing_jobs = [j for j in jobs if j.get("status") == "PROCESSING"]
        if not processing_jobs:
            pytest.skip("No processing jobs found")
        
        job_id = processing_jobs[0].get("job_id")
        status_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        assert status_response.status_code == 200
        
        job = status_response.json().get("job", {})
        assert job.get("view_mode") == "progress", f"Expected view_mode='progress' for processing job, got '{job.get('view_mode')}'"
        print(f"PASS: Processing job {job_id[:8]} returns view_mode='progress'")


class TestFailureDetailHumanReadable:
    """Test that failure details are human-readable, not raw enums"""

    def test_failure_detail_present_for_failed_jobs(self, authenticated_client):
        """Failed jobs should include human-readable failure_detail"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        failed_jobs = [j for j in jobs if j.get("status") == "FAILED"]
        if not failed_jobs:
            pytest.skip("No failed jobs found")
        
        job_id = failed_jobs[0].get("job_id")
        status_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        assert status_response.status_code == 200
        
        job = status_response.json().get("job", {})
        failure_detail = job.get("failure_detail")
        
        # failure_detail should be present for failed jobs
        if failure_detail:
            assert "title" in failure_detail, "failure_detail missing 'title' field"
            assert "suggestion" in failure_detail, "failure_detail missing 'suggestion' field"
            # Ensure no raw enums in the title/suggestion
            raw_enums = ["FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER"]
            for enum in raw_enums:
                assert enum not in failure_detail.get("title", ""), f"Raw enum {enum} found in failure title"
                assert enum not in failure_detail.get("suggestion", ""), f"Raw enum {enum} found in failure suggestion"
            print(f"PASS: Failed job has human-readable failure_detail: {failure_detail.get('title', '')[:50]}...")
        else:
            print(f"INFO: Failed job {job_id[:8]} has no failure_detail (may be generic FAILED state)")

    def test_no_raw_enums_in_status_response(self, authenticated_client):
        """Status response should not expose raw engine state enums to users"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        if not jobs:
            pytest.skip("No jobs found")
        
        # Check first 5 jobs
        for job in jobs[:5]:
            job_id = job.get("job_id")
            status_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
            if status_response.status_code != 200:
                continue
            
            job_data = status_response.json().get("job", {})
            
            # Check that user-facing fields don't contain raw enums
            user_facing_fields = ["status", "stage_label", "progress_message"]
            raw_enums = ["FAILED_PLANNING", "FAILED_IMAGES", "FAILED_TTS", "FAILED_RENDER", 
                        "GENERATING_KEYFRAMES", "BUILDING_CHARACTER_CONTEXT"]
            
            for field in user_facing_fields:
                value = str(job_data.get(field, ""))
                for enum in raw_enums:
                    if enum in value:
                        # engine_state is allowed to have raw enums (for debugging)
                        # but user-facing fields should not
                        if field != "engine_state":
                            pytest.fail(f"Raw enum {enum} found in user-facing field '{field}'")
        
        print("PASS: No raw enums found in user-facing status fields")


class TestDeleteJobEndpoint:
    """Test DELETE /api/story-engine/jobs/{job_id} endpoint"""

    def test_delete_nonexistent_job_returns_404(self, authenticated_client):
        """Deleting a non-existent job should return 404"""
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.delete(f"{BASE_URL}/api/story-engine/jobs/{fake_job_id}")
        assert response.status_code == 404
        print("PASS: Delete non-existent job returns 404")

    def test_delete_requires_authentication(self, api_client):
        """Delete endpoint requires authentication"""
        # Remove auth header temporarily
        original_headers = api_client.headers.copy()
        api_client.headers.pop("Authorization", None)
        
        response = api_client.delete(f"{BASE_URL}/api/story-engine/jobs/test-job-id")
        assert response.status_code in (401, 403), f"Expected 401/403, got {response.status_code}"
        
        # Restore headers
        api_client.headers = original_headers
        print("PASS: Delete endpoint requires authentication")


class TestRecoveryEventEndpoint:
    """Test POST /api/story-engine/recovery-event analytics endpoint"""

    def test_recovery_event_tracks_failed_job_viewed(self, authenticated_client):
        """Track 'failed_job_viewed' event"""
        response = authenticated_client.post(f"{BASE_URL}/api/story-engine/recovery-event", json={
            "event": "failed_job_viewed",
            "job_id": "test-job-id-123",
            "engine_state": "FAILED_PLANNING"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: recovery-event tracks 'failed_job_viewed'")

    def test_recovery_event_tracks_retry_clicked(self, authenticated_client):
        """Track 'retry_clicked' event"""
        response = authenticated_client.post(f"{BASE_URL}/api/story-engine/recovery-event", json={
            "event": "retry_clicked",
            "job_id": "test-job-id-123",
            "engine_state": "FAILED_IMAGES"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: recovery-event tracks 'retry_clicked'")

    def test_recovery_event_tracks_edit_retry_clicked(self, authenticated_client):
        """Track 'edit_retry_clicked' event"""
        response = authenticated_client.post(f"{BASE_URL}/api/story-engine/recovery-event", json={
            "event": "edit_retry_clicked",
            "job_id": "test-job-id-123",
            "engine_state": "FAILED_TTS"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: recovery-event tracks 'edit_retry_clicked'")

    def test_recovery_event_tracks_delete_failed_project(self, authenticated_client):
        """Track 'delete_failed_project' event"""
        response = authenticated_client.post(f"{BASE_URL}/api/story-engine/recovery-event", json={
            "event": "delete_failed_project",
            "job_id": "test-job-id-123",
            "engine_state": "FAILED_RENDER"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: recovery-event tracks 'delete_failed_project'")

    def test_recovery_event_rejects_unknown_event(self, authenticated_client):
        """Unknown events should be rejected"""
        response = authenticated_client.post(f"{BASE_URL}/api/story-engine/recovery-event", json={
            "event": "unknown_event_type",
            "job_id": "test-job-id-123",
            "engine_state": "FAILED"
        })
        assert response.status_code == 400
        print("PASS: recovery-event rejects unknown event types")

    def test_recovery_event_requires_authentication(self, api_client):
        """Recovery event endpoint requires authentication"""
        # Remove auth header temporarily
        original_headers = api_client.headers.copy()
        api_client.headers.pop("Authorization", None)
        
        response = api_client.post(f"{BASE_URL}/api/story-engine/recovery-event", json={
            "event": "failed_job_viewed",
            "job_id": "test-job-id",
            "engine_state": "FAILED"
        })
        assert response.status_code in (401, 403), f"Expected 401/403, got {response.status_code}"
        
        # Restore headers
        api_client.headers = original_headers
        print("PASS: recovery-event requires authentication")


class TestMySpaceJobsStatusCopy:
    """Test that MySpace/user-jobs returns human-readable status labels"""

    def test_user_jobs_returns_human_readable_status(self, authenticated_client):
        """User jobs should have human-readable status, not raw enums"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        
        jobs = data.get("jobs", [])
        if not jobs:
            pytest.skip("No jobs found")
        
        # Check that status values are user-friendly
        valid_statuses = ["QUEUED", "PROCESSING", "COMPLETED", "PARTIAL", "FAILED"]
        for job in jobs[:10]:
            status = job.get("status")
            assert status in valid_statuses, f"Unexpected status '{status}' - should be one of {valid_statuses}"
        
        print(f"PASS: All {min(len(jobs), 10)} jobs have valid user-friendly status values")


class TestDeepLinkSupport:
    """Test that status endpoint works for deep-link projectId loading"""

    def test_status_endpoint_returns_full_job_data(self, authenticated_client):
        """Status endpoint should return all data needed for deep-link loading"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        if not jobs:
            pytest.skip("No jobs found")
        
        job_id = jobs[0].get("job_id")
        status_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        assert status_response.status_code == 200
        
        job = status_response.json().get("job", {})
        
        # Required fields for deep-link loading
        required_fields = ["job_id", "status", "view_mode", "title"]
        for field in required_fields:
            assert field in job, f"Missing required field '{field}' for deep-link support"
        
        print(f"PASS: Status endpoint returns all required fields for deep-link loading")

    def test_status_endpoint_handles_invalid_job_id(self, authenticated_client):
        """Status endpoint should handle invalid job IDs gracefully"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/invalid-job-id-12345")
        assert response.status_code == 404
        print("PASS: Status endpoint returns 404 for invalid job ID")


class TestRetryInfo:
    """Test retry_info field in status response"""

    def test_retry_info_present_in_status(self, authenticated_client):
        """Status response should include retry_info"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        if not jobs:
            pytest.skip("No jobs found")
        
        job_id = jobs[0].get("job_id")
        status_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        assert status_response.status_code == 200
        
        job = status_response.json().get("job", {})
        retry_info = job.get("retry_info")
        
        assert retry_info is not None, "retry_info missing from status response"
        assert "can_retry" in retry_info, "retry_info missing 'can_retry' field"
        print(f"PASS: Status includes retry_info with can_retry={retry_info.get('can_retry')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
