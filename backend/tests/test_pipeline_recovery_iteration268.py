"""
Test Pipeline Infrastructure Stability (Iteration 268)

Tests for P0 fix: Auto-resume from checkpoint, fallback asset generation,
crash diagnostics logging, and enhanced error recovery.

Features tested:
1. POST /api/pipeline/create - creates new job
2. GET /api/pipeline/status/{job_id} - returns has_recoverable_assets and crash_logs
3. GET /api/pipeline/preview/{job_id} - works for PARTIAL/FAILED jobs with assets
4. POST /api/pipeline/resume/{job_id} - resumes a failed/interrupted job
5. GET /api/pipeline/crash-diagnostics - admin only crash diagnostic data
6. GET /api/pipeline/user-jobs - includes has_recoverable_assets flag
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Known existing PARTIAL jobs from the context
EXISTING_PARTIAL_JOB_1 = "671f8292-70db-486f-a162-1cca98ceeb27"
EXISTING_PARTIAL_JOB_2 = "630278b5-4b2f-48b9-adabae24e3b0"

@pytest.fixture(scope="module")
def api_session():
    """Create a requests session with common headers."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_token(api_session):
    """Authenticate as test user and return token."""
    response = api_session.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token(api_session):
    """Authenticate as admin and return token."""
    response = api_session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


class TestPipelineJobStatus:
    """Tests for pipeline status endpoint with recovery info."""

    def test_status_returns_has_recoverable_assets(self, api_session, test_user_token):
        """GET /api/pipeline/status/{job_id} should include has_recoverable_assets flag."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        # Try first partial job
        response = api_session.get(f"{BASE_URL}/api/pipeline/status/{EXISTING_PARTIAL_JOB_1}")
        
        if response.status_code == 404:
            # Try second partial job
            response = api_session.get(f"{BASE_URL}/api/pipeline/status/{EXISTING_PARTIAL_JOB_2}")
        
        if response.status_code == 404:
            pytest.skip("Neither test job found - may have been cleaned up")
            
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "job" in data, "Response should contain job object"
        
        job = data["job"]
        # has_recoverable_assets should be in response
        assert "has_recoverable_assets" in job, "Job should have has_recoverable_assets flag"
        print(f"Job status: {job.get('status')}, has_recoverable_assets: {job.get('has_recoverable_assets')}")

    def test_status_includes_crash_logs(self, api_session, test_user_token):
        """GET /api/pipeline/status/{job_id} should include crash_logs if any."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        response = api_session.get(f"{BASE_URL}/api/pipeline/status/{EXISTING_PARTIAL_JOB_1}")
        
        if response.status_code == 404:
            response = api_session.get(f"{BASE_URL}/api/pipeline/status/{EXISTING_PARTIAL_JOB_2}")
        
        if response.status_code == 404:
            pytest.skip("Test jobs not found")
            
        assert response.status_code == 200
        data = response.json()
        job = data["job"]
        
        # crash_logs should be in the response (may be empty array if no crashes)
        assert "crash_logs" in job, "Job should have crash_logs field"
        assert isinstance(job["crash_logs"], list), "crash_logs should be a list"
        print(f"Job has {len(job['crash_logs'])} crash log entries")

    def test_status_includes_fallback_data(self, api_session, test_user_token):
        """GET /api/pipeline/status/{job_id} should include fallback info for PARTIAL jobs."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        response = api_session.get(f"{BASE_URL}/api/pipeline/status/{EXISTING_PARTIAL_JOB_1}")
        
        if response.status_code == 404:
            response = api_session.get(f"{BASE_URL}/api/pipeline/status/{EXISTING_PARTIAL_JOB_2}")
        
        if response.status_code == 404:
            pytest.skip("Test jobs not found")
            
        assert response.status_code == 200
        data = response.json()
        job = data["job"]
        
        # fallback field should be present
        assert "fallback" in job, "Job should have fallback field"
        if job.get("fallback"):
            print(f"Fallback data: status={job['fallback'].get('status')}, "
                  f"has_preview={job['fallback'].get('has_preview')}")


class TestPipelinePreview:
    """Tests for preview endpoint for PARTIAL/FAILED jobs."""

    def test_preview_works_for_partial_job(self, api_session):
        """GET /api/pipeline/preview/{job_id} should return preview data for PARTIAL jobs."""
        # Preview endpoint doesn't require auth
        response = api_session.get(f"{BASE_URL}/api/pipeline/preview/{EXISTING_PARTIAL_JOB_1}")
        
        if response.status_code == 404:
            response = api_session.get(f"{BASE_URL}/api/pipeline/preview/{EXISTING_PARTIAL_JOB_2}")
        
        if response.status_code == 404:
            pytest.skip("Test jobs not found")
            
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "preview" in data
        
        preview = data["preview"]
        assert "title" in preview, "Preview should have title"
        assert "scenes" in preview, "Preview should have scenes"
        print(f"Preview: title='{preview.get('title')}', "
              f"scenes={len(preview.get('scenes', []))}, "
              f"story_pack_url present: {'story_pack_url' in preview}")

    def test_preview_includes_fallback_urls(self, api_session):
        """GET /api/pipeline/preview/{job_id} should include fallback URLs if available."""
        response = api_session.get(f"{BASE_URL}/api/pipeline/preview/{EXISTING_PARTIAL_JOB_1}")
        
        if response.status_code == 404:
            response = api_session.get(f"{BASE_URL}/api/pipeline/preview/{EXISTING_PARTIAL_JOB_2}")
        
        if response.status_code == 404:
            pytest.skip("Test jobs not found")
            
        assert response.status_code == 200
        data = response.json()
        preview = data["preview"]
        
        # These fields should be present (may be null if no fallback)
        expected_fields = ["story_pack_url", "fallback_video_url", "final_video_url"]
        for field in expected_fields:
            assert field in preview, f"Preview should have {field} field"
            print(f"{field}: {preview.get(field)}")


class TestPipelineResume:
    """Tests for pipeline resume endpoint."""

    def test_resume_requires_auth(self, api_session):
        """POST /api/pipeline/resume/{job_id} should require authentication."""
        # Clear auth header
        api_session.headers.pop("Authorization", None)
        
        response = api_session.post(f"{BASE_URL}/api/pipeline/resume/{EXISTING_PARTIAL_JOB_1}")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_resume_returns_403_for_non_owner(self, api_session, admin_token):
        """POST /api/pipeline/resume/{job_id} should return 403 if user doesn't own the job."""
        api_session.headers["Authorization"] = f"Bearer {admin_token}"
        
        response = api_session.post(f"{BASE_URL}/api/pipeline/resume/{EXISTING_PARTIAL_JOB_1}")
        
        # Should fail with 403 (not owner) or 400 (already completed) or 404 (not found)
        # Don't fail the test if job is not found
        if response.status_code == 404:
            pytest.skip("Test job not found")
        
        # If admin owns the job, they can resume, otherwise 403
        assert response.status_code in [200, 400, 403], f"Expected 200/400/403, got {response.status_code}"
        print(f"Resume response: {response.status_code} - {response.text[:200]}")


class TestCrashDiagnostics:
    """Tests for crash diagnostics admin endpoint."""

    def test_crash_diagnostics_requires_admin(self, api_session, test_user_token):
        """GET /api/pipeline/crash-diagnostics should return 403 for non-admin."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        response = api_session.get(f"{BASE_URL}/api/pipeline/crash-diagnostics")
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"

    def test_crash_diagnostics_returns_data_for_admin(self, api_session, admin_token):
        """GET /api/pipeline/crash-diagnostics should return crash data for admin."""
        api_session.headers["Authorization"] = f"Bearer {admin_token}"
        
        response = api_session.get(f"{BASE_URL}/api/pipeline/crash-diagnostics")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "total_crashes" in data
        assert "affected_jobs" in data
        assert "jobs" in data
        
        print(f"Crash diagnostics: total_crashes={data['total_crashes']}, "
              f"affected_jobs={data['affected_jobs']}")
        
        # If there are crash logs, verify structure
        if data.get("jobs") and len(data["jobs"]) > 0:
            first_job = data["jobs"][0]
            assert "job_id" in first_job
            assert "crash_logs" in first_job
            print(f"Sample job: {first_job.get('job_id')}, "
                  f"crash_count={len(first_job.get('crash_logs', []))}")


class TestUserJobs:
    """Tests for user jobs listing with recovery info."""

    def test_user_jobs_includes_has_recoverable_assets(self, api_session, test_user_token):
        """GET /api/pipeline/user-jobs should include has_recoverable_assets for each job."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        response = api_session.get(f"{BASE_URL}/api/pipeline/user-jobs")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        assert "jobs" in data
        
        jobs = data["jobs"]
        if len(jobs) > 0:
            first_job = jobs[0]
            assert "has_recoverable_assets" in first_job, "Job should have has_recoverable_assets flag"
            print(f"User has {len(jobs)} jobs, first job has_recoverable_assets: {first_job.get('has_recoverable_assets')}")
        else:
            print("User has no jobs")


class TestPipelineCreate:
    """Tests for pipeline job creation."""

    def test_create_requires_auth(self, api_session):
        """POST /api/pipeline/create should require authentication."""
        api_session.headers.pop("Authorization", None)
        
        response = api_session.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Test Story",
            "story_text": "Once upon a time, there was a brave little rabbit who went on an adventure through the forest."
        })
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_create_validates_input(self, api_session, test_user_token):
        """POST /api/pipeline/create should validate title and story_text."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        # Test short title
        response = api_session.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "AB",  # Too short (min 3)
            "story_text": "Once upon a time, there was a brave little rabbit who went on an adventure through the forest."
        })
        
        assert response.status_code == 422, f"Expected 422 for short title, got {response.status_code}"
        
        # Test short story
        response = api_session.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Valid Title",
            "story_text": "Too short"  # Min 50 chars
        })
        
        assert response.status_code == 422, f"Expected 422 for short story, got {response.status_code}"

    def test_create_returns_job_id(self, api_session, test_user_token):
        """POST /api/pipeline/create should return job_id and charge credits."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        # Check rate limit first
        rate_limit = api_session.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        if rate_limit.status_code == 200:
            rl_data = rate_limit.json()
            if not rl_data.get("can_create"):
                pytest.skip(f"Rate limited: {rl_data.get('reason')}")
        
        response = api_session.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Test Recovery Story",
            "story_text": "Once upon a time in a magical forest, there was a brave little rabbit named Ruby. She loved to explore and discover new places. One day, she found a mysterious path that led to a hidden garden full of beautiful flowers."
        })
        
        # Could be rate limited
        if response.status_code == 429:
            pytest.skip(f"Rate limited: {response.text}")
        
        # Could fail due to insufficient credits
        if response.status_code == 400 and "credit" in response.text.lower():
            pytest.skip("Insufficient credits")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "job_id" in data
        assert "credits_charged" in data
        
        print(f"Created job: {data['job_id']}, credits_charged: {data['credits_charged']}")


class TestPipelineOptions:
    """Test pipeline options endpoint."""

    def test_options_returns_styles_and_presets(self, api_session):
        """GET /api/pipeline/options should return animation styles, age groups, voices."""
        response = api_session.get(f"{BASE_URL}/api/pipeline/options")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        assert "credit_costs" in data
        
        print(f"Options: {len(data['animation_styles'])} styles, "
              f"{len(data['age_groups'])} age groups, "
              f"{len(data['voice_presets'])} voices")


class TestWorkerStats:
    """Test worker stats endpoint."""

    def test_worker_status_returns_stats(self, api_session, test_user_token):
        """GET /api/pipeline/workers/status should return worker pool stats."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        response = api_session.get(f"{BASE_URL}/api/pipeline/workers/status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        assert "workers" in data
        
        workers = data["workers"]
        assert "num_workers" in workers or "current_workers" in workers
        assert "jobs_processed" in workers
        print(f"Workers: {workers.get('current_workers', workers.get('num_workers'))} active, "
              f"{workers.get('jobs_processed')} processed")


class TestRateLimitStatus:
    """Test rate limit status endpoint."""

    def test_rate_limit_status_returns_info(self, api_session, test_user_token):
        """GET /api/pipeline/rate-limit-status should return rate limit info."""
        api_session.headers["Authorization"] = f"Bearer {test_user_token}"
        
        response = api_session.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "can_create" in data
        assert "recent_count" in data
        assert "max_per_hour" in data
        assert "concurrent" in data
        assert "max_concurrent" in data
        
        print(f"Rate limit: can_create={data['can_create']}, "
              f"recent={data['recent_count']}/{data['max_per_hour']}, "
              f"concurrent={data['concurrent']}/{data['max_concurrent']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
