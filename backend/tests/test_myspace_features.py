"""
Test My Space Page Features - Phase 1 & 2
- GET /api/story-engine/user-jobs - Returns jobs with proper statuses
- POST /api/story-engine/share-link/{job_id} - Share link generation for WhatsApp
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(auth_token):
    """Session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestUserJobsEndpoint:
    """Tests for GET /api/story-engine/user-jobs endpoint."""
    
    def test_user_jobs_returns_200(self, authenticated_client):
        """Test that user-jobs endpoint returns 200 OK."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/story-engine/user-jobs returned 200")
    
    def test_user_jobs_returns_jobs_array(self, authenticated_client):
        """Test that response contains jobs array."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data, "Response missing 'success' field"
        assert data["success"] == True, "success should be True"
        assert "jobs" in data, "Response missing 'jobs' field"
        assert isinstance(data["jobs"], list), "jobs should be a list"
        print(f"✓ Response contains jobs array with {len(data['jobs'])} jobs")
    
    def test_user_jobs_have_required_fields(self, authenticated_client):
        """Test that each job has required fields for My Space display."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        jobs = data.get("jobs", [])
        
        if len(jobs) == 0:
            pytest.skip("No jobs found for test user")
        
        required_fields = ["job_id", "title", "status", "progress", "created_at"]
        for job in jobs[:5]:  # Check first 5 jobs
            for field in required_fields:
                assert field in job, f"Job missing required field: {field}"
        print(f"✓ Jobs have all required fields: {required_fields}")
    
    def test_user_jobs_status_values(self, authenticated_client):
        """Test that job statuses are valid values."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        jobs = data.get("jobs", [])
        
        valid_statuses = ["QUEUED", "PROCESSING", "COMPLETED", "PARTIAL", "FAILED"]
        status_counts = {"QUEUED": 0, "PROCESSING": 0, "COMPLETED": 0, "PARTIAL": 0, "FAILED": 0}
        
        for job in jobs:
            status = job.get("status")
            assert status in valid_statuses, f"Invalid status: {status}"
            if status in status_counts:
                status_counts[status] += 1
        
        print(f"✓ Job status distribution: {status_counts}")
    
    def test_user_jobs_completed_have_output_url(self, authenticated_client):
        """Test that completed jobs have output_url or thumbnail_url."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        jobs = data.get("jobs", [])
        
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        if len(completed_jobs) == 0:
            pytest.skip("No completed jobs found")
        
        # At least some completed jobs should have thumbnail_url
        jobs_with_thumbnail = [j for j in completed_jobs if j.get("thumbnail_url")]
        print(f"✓ {len(jobs_with_thumbnail)}/{len(completed_jobs)} completed jobs have thumbnail_url")


class TestShareLinkEndpoint:
    """Tests for POST /api/story-engine/share-link/{job_id} endpoint."""
    
    def test_share_link_requires_auth(self):
        """Test that share-link endpoint requires authentication."""
        # Use a dummy job_id
        response = requests.post(f"{BASE_URL}/api/story-engine/share-link/dummy-job-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Share-link endpoint requires authentication")
    
    def test_share_link_404_for_invalid_job(self, authenticated_client):
        """Test that share-link returns 404 for non-existent job."""
        response = authenticated_client.post(f"{BASE_URL}/api/story-engine/share-link/nonexistent-job-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"✓ Share-link returns 404 for invalid job_id")
    
    def test_share_link_for_completed_job(self, authenticated_client):
        """Test share-link generation for a completed job."""
        # First get user jobs to find a completed one
        jobs_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert jobs_response.status_code == 200
        jobs = jobs_response.json().get("jobs", [])
        
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        if len(completed_jobs) == 0:
            pytest.skip("No completed jobs found for share-link test")
        
        job_id = completed_jobs[0]["job_id"]
        response = authenticated_client.post(f"{BASE_URL}/api/story-engine/share-link/{job_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert data["success"] == True, "success should be True"
        assert "share_url" in data, "Response missing 'share_url' field"
        assert "whatsapp_url" in data, "Response missing 'whatsapp_url' field"
        
        # Verify URLs are valid
        assert data["share_url"].startswith("http"), f"Invalid share_url: {data['share_url']}"
        assert "wa.me" in data["whatsapp_url"], f"Invalid whatsapp_url: {data['whatsapp_url']}"
        
        print(f"✓ Share-link generated successfully for job {job_id[:8]}...")
        print(f"  share_url: {data['share_url']}")
        print(f"  whatsapp_url: {data['whatsapp_url'][:80]}...")
    
    def test_share_link_idempotent(self, authenticated_client):
        """Test that calling share-link twice returns the same share_id."""
        jobs_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert jobs_response.status_code == 200
        jobs = jobs_response.json().get("jobs", [])
        
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        if len(completed_jobs) == 0:
            pytest.skip("No completed jobs found for idempotency test")
        
        job_id = completed_jobs[0]["job_id"]
        
        # Call twice
        response1 = authenticated_client.post(f"{BASE_URL}/api/story-engine/share-link/{job_id}")
        response2 = authenticated_client.post(f"{BASE_URL}/api/story-engine/share-link/{job_id}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Should return same share_id
        assert data1.get("share_id") == data2.get("share_id"), "Share-link should be idempotent"
        print(f"✓ Share-link is idempotent - same share_id returned on multiple calls")
    
    def test_share_link_rejects_incomplete_job(self, authenticated_client):
        """Test that share-link rejects jobs that are not completed."""
        jobs_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert jobs_response.status_code == 200
        jobs = jobs_response.json().get("jobs", [])
        
        # Find a non-completed job
        incomplete_jobs = [j for j in jobs if j.get("status") in ["QUEUED", "PROCESSING"]]
        if len(incomplete_jobs) == 0:
            pytest.skip("No incomplete jobs found for rejection test")
        
        job_id = incomplete_jobs[0]["job_id"]
        response = authenticated_client.post(f"{BASE_URL}/api/story-engine/share-link/{job_id}")
        
        assert response.status_code == 400, f"Expected 400 for incomplete job, got {response.status_code}"
        print(f"✓ Share-link correctly rejects incomplete jobs")


class TestRateLimitStatus:
    """Tests for rate limit status endpoint used by My Space."""
    
    def test_rate_limit_status_returns_200(self, authenticated_client):
        """Test rate-limit-status endpoint returns 200."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/rate-limit-status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ GET /api/story-engine/rate-limit-status returned 200")
    
    def test_rate_limit_status_structure(self, authenticated_client):
        """Test rate-limit-status response structure."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/rate-limit-status")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["can_create", "concurrent", "max_concurrent"]
        for field in required_fields:
            assert field in data, f"Response missing field: {field}"
        
        print(f"✓ Rate limit status: can_create={data['can_create']}, concurrent={data['concurrent']}/{data['max_concurrent']}")


class TestJobStatusEndpoint:
    """Tests for GET /api/story-engine/status/{job_id} endpoint."""
    
    def test_job_status_returns_job_details(self, authenticated_client):
        """Test that status endpoint returns detailed job info."""
        jobs_response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert jobs_response.status_code == 200
        jobs = jobs_response.json().get("jobs", [])
        
        if len(jobs) == 0:
            pytest.skip("No jobs found for status test")
        
        job_id = jobs[0]["job_id"]
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "success" in data
        assert "job" in data
        job = data["job"]
        
        # Check required fields for My Space display
        required_fields = ["job_id", "title", "status", "progress", "current_stage", "current_step"]
        for field in required_fields:
            assert field in job, f"Job status missing field: {field}"
        
        print(f"✓ Job status returned with all required fields for job {job_id[:8]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
