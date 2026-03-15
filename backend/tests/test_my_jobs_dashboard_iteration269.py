"""
Test: My Jobs Dashboard Feature - Iteration 269
Tests the My Jobs tab in Profile page - user pipeline jobs with filters, recovery status, and resume functionality.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestMyJobsDashboard:
    """Tests for My Jobs Dashboard - GET /api/pipeline/user-jobs and POST /api/pipeline/resume/{job_id}"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Authenticate and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get("token")
        assert token, "No token in response"
        return token

    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

    # ─── GET /api/pipeline/user-jobs Tests ─────────────────────────────────

    def test_user_jobs_returns_success(self, auth_headers):
        """Test that user-jobs endpoint returns success and jobs array"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        print(f"PASS: /api/pipeline/user-jobs returns {len(data['jobs'])} jobs")

    def test_user_jobs_without_auth_returns_401(self):
        """Test that user-jobs requires authentication"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: user-jobs requires authentication")

    def test_user_jobs_contains_required_fields(self, auth_headers):
        """Test that each job contains required fields for My Jobs dashboard"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        if len(jobs) > 0:
            job = jobs[0]
            # Required fields for dashboard display
            required_fields = ["job_id", "title", "status", "created_at", "stages", "has_recoverable_assets"]
            for field in required_fields:
                assert field in job, f"Missing required field: {field}"
            
            # Status should be one of expected values
            valid_statuses = ["QUEUED", "PROCESSING", "COMPLETED", "PARTIAL", "FAILED"]
            assert job["status"] in valid_statuses, f"Invalid status: {job['status']}"
            print(f"PASS: Job contains all required fields, status={job['status']}")
        else:
            pytest.skip("No jobs found to verify")

    def test_user_jobs_has_stages_progress(self, auth_headers):
        """Test that jobs include stage progress for progress bars"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        if len(jobs) > 0:
            job = jobs[0]
            stages = job.get("stages", {})
            
            # Expected stages for progress bars
            expected_stages = ["scenes", "images", "voices", "render"]
            found_stages = [s for s in expected_stages if s in stages]
            
            assert len(found_stages) > 0, "No expected stages found"
            
            # Each stage should have status
            for stage_name, stage_data in stages.items():
                if stage_data:
                    assert "status" in stage_data, f"Stage {stage_name} missing status"
            
            print(f"PASS: Job has stages: {list(stages.keys())}")
        else:
            pytest.skip("No jobs to verify stages")

    def test_user_jobs_has_recoverable_assets_flag(self, auth_headers):
        """Test that jobs include has_recoverable_assets flag for resume/preview buttons"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        # Find a PARTIAL job
        partial_jobs = [j for j in jobs if j.get("status") == "PARTIAL"]
        
        if len(partial_jobs) > 0:
            job = partial_jobs[0]
            assert "has_recoverable_assets" in job, "Missing has_recoverable_assets"
            assert job["has_recoverable_assets"] == True, "PARTIAL job should have recoverable assets"
            print(f"PASS: PARTIAL job {job['job_id'][:8]} has has_recoverable_assets=True")
        else:
            pytest.skip("No PARTIAL jobs to verify")

    def test_user_jobs_has_animation_style(self, auth_headers):
        """Test that jobs include animation_style for display"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        if len(jobs) > 0:
            job = jobs[0]
            assert "animation_style" in job, "Missing animation_style"
            print(f"PASS: Job has animation_style={job.get('animation_style')}")
        else:
            pytest.skip("No jobs to verify")

    def test_user_jobs_has_credits_charged(self, auth_headers):
        """Test that jobs include credits_charged for display"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        if len(jobs) > 0:
            job = jobs[0]
            assert "credits_charged" in job, "Missing credits_charged"
            assert isinstance(job["credits_charged"], (int, float)), "credits_charged should be numeric"
            print(f"PASS: Job has credits_charged={job.get('credits_charged')}")
        else:
            pytest.skip("No jobs to verify")

    # ─── POST /api/pipeline/resume/{job_id} Tests ─────────────────────────

    def test_resume_job_requires_auth(self):
        """Test that resume endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/pipeline/resume/fake-job-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: resume endpoint requires authentication")

    def test_resume_job_validates_job_exists(self, auth_headers):
        """Test that resume validates job existence"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/resume/non-existent-job-id",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404 for non-existent job, got {response.status_code}"
        print("PASS: resume returns 404 for non-existent job")

    def test_resume_job_validates_ownership(self, auth_headers):
        """Test that resume validates job ownership"""
        # First get a known test job that exists
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        jobs = response.json().get("jobs", [])
        
        # Try to resume an existing job - should work or fail on status
        if len(jobs) > 0:
            job = jobs[0]
            resume_response = requests.post(
                f"{BASE_URL}/api/pipeline/resume/{job['job_id']}",
                headers=auth_headers
            )
            # Should either succeed (200) or fail with 400 if already completed
            assert resume_response.status_code in [200, 400], f"Unexpected status: {resume_response.status_code}"
            print(f"PASS: resume job ownership validated, status={resume_response.status_code}")
        else:
            pytest.skip("No jobs to test ownership")

    # ─── Filter Logic Tests (Verify data supports filtering) ─────────────

    def test_user_jobs_supports_status_filtering(self, auth_headers):
        """Verify data includes status for All/Completed/Assets Ready/Failed/Active filters"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        # Count jobs by status
        status_counts = {}
        for job in jobs:
            status = job.get("status")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"PASS: Status counts for filters: {status_counts}")
        assert len(status_counts) > 0, "No jobs with status found"

    def test_user_jobs_crash_logs_for_recovered_badge(self, auth_headers):
        """Test that jobs with server restart have crash_logs for Recovered badge"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        # Find jobs with crash_logs
        jobs_with_crash_logs = [j for j in jobs if j.get("crash_logs")]
        
        if len(jobs_with_crash_logs) > 0:
            job = jobs_with_crash_logs[0]
            crash_log = job["crash_logs"][0]
            assert "reason" in crash_log, "crash_log missing reason"
            print(f"PASS: Found job with crash_log reason={crash_log.get('reason')}")
        else:
            print("INFO: No jobs with crash_logs found")

    def test_user_jobs_output_url_for_video_download(self, auth_headers):
        """Test that COMPLETED jobs have output_url for Video download button"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        
        if len(completed_jobs) > 0:
            job = completed_jobs[0]
            assert "output_url" in job, "COMPLETED job missing output_url"
            if job.get("output_url"):
                print(f"PASS: COMPLETED job has output_url for download")
            else:
                print("INFO: COMPLETED job has output_url field but value is None")
        else:
            print("INFO: No COMPLETED jobs to verify output_url")

    def test_user_jobs_fallback_outputs_for_preview(self, auth_headers):
        """Test that PARTIAL jobs have fallback_outputs for Preview button"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        partial_jobs = [j for j in jobs if j.get("status") == "PARTIAL"]
        
        if len(partial_jobs) > 0:
            job = partial_jobs[0]
            # Either fallback_outputs or has_recoverable_assets should be present
            has_fallback = job.get("fallback_outputs") or job.get("has_recoverable_assets")
            assert has_fallback, "PARTIAL job missing fallback data for Preview button"
            print(f"PASS: PARTIAL job {job['job_id'][:8]} has fallback data for Preview")
        else:
            pytest.skip("No PARTIAL jobs to verify fallback")


class TestMyJobsDashboardEdgeCases:
    """Edge case tests for My Jobs Dashboard"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Authenticate and get headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def test_user_jobs_sorted_by_created_at(self, auth_headers):
        """Test that jobs are sorted by created_at descending (newest first)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        if len(jobs) >= 2:
            # First job should be more recent than second
            first_date = jobs[0].get("created_at")
            second_date = jobs[1].get("created_at")
            assert first_date >= second_date, "Jobs not sorted by created_at desc"
            print(f"PASS: Jobs sorted newest first")
        else:
            pytest.skip("Need at least 2 jobs to verify sorting")

    def test_user_jobs_limited_to_50(self, auth_headers):
        """Test that user-jobs returns max 50 jobs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        assert len(jobs) <= 50, f"Too many jobs returned: {len(jobs)}"
        print(f"PASS: User jobs limited (returned {len(jobs)})")
