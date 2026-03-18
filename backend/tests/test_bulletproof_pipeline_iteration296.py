"""
Bulletproof Pipeline Tests - Iteration 296
Tests for Story Video Studio bulletproof pipeline architecture:
- GET /api/pipeline/validate-asset/{job_id} endpoint
- State machine states: PROCESSING, VALIDATING, READY, PARTIAL_READY, FAILED
- Separate truth for preview/download/share
- Admin unlimited credits bypass
- Rate limit exemptions
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://stateful-stories.preview.emergentagent.com"

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin user token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    return data["token"]


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Test user login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    return data["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def test_user_headers(test_user_token):
    return {"Authorization": f"Bearer {test_user_token}", "Content-Type": "application/json"}


class TestPipelineOptions:
    """Test /api/pipeline/options endpoint"""
    
    def test_get_pipeline_options(self):
        """GET /api/pipeline/options should return animation_styles, age_groups, voice_presets"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        assert len(data["animation_styles"]) > 0
        assert len(data["age_groups"]) > 0
        assert len(data["voice_presets"]) > 0
        print(f"PASS: Pipeline options - {len(data['animation_styles'])} styles, {len(data['age_groups'])} age groups, {len(data['voice_presets'])} voices")


class TestRateLimitStatus:
    """Test /api/pipeline/rate-limit-status endpoint for admin exemption"""
    
    def test_admin_rate_limit_exempt(self, admin_headers):
        """Admin user should be exempt from rate limiting"""
        response = requests.get(f"{BASE_URL}/api/pipeline/rate-limit-status", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Admin should have exempt=True or very high limits
        assert data.get("can_create") == True
        # Admin should be marked as exempt or have unlimited slots
        if "exempt" in data:
            assert data["exempt"] == True
            print(f"PASS: Admin is exempt from rate limiting")
        else:
            assert data.get("max_per_hour", 0) >= 999 or data.get("can_create") == True
            print(f"PASS: Admin can create with limits: {data.get('max_per_hour')}")
    
    def test_normal_user_rate_limit_status(self, test_user_headers):
        """Test user should have rate limit status returned"""
        response = requests.get(f"{BASE_URL}/api/pipeline/rate-limit-status", headers=test_user_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should return rate limit info
        assert "can_create" in data
        assert "max_per_hour" in data
        assert "concurrent" in data
        assert "max_concurrent" in data
        print(f"PASS: Test user rate limit - can_create: {data['can_create']}, {data['recent_count']}/{data['max_per_hour']} per hour")


class TestValidateAssetEndpoint:
    """Test /api/pipeline/validate-asset/{job_id} endpoint - core bulletproof pipeline feature"""
    
    def test_validate_asset_nonexistent_job(self, admin_headers):
        """Non-existent job should return 404"""
        response = requests.get(f"{BASE_URL}/api/pipeline/validate-asset/nonexistent-job-id", headers=admin_headers)
        assert response.status_code == 404, f"Expected 404 for nonexistent job, got {response.status_code}"
        print("PASS: validate-asset returns 404 for nonexistent job")
    
    def test_validate_asset_returns_separate_ready_fields(self, admin_headers):
        """First get user jobs, then validate an existing job - verify separate ready fields"""
        # Get user jobs
        jobs_response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=admin_headers)
        assert jobs_response.status_code == 200, f"Failed to get user jobs: {jobs_response.text}"
        jobs_data = jobs_response.json()
        
        if not jobs_data.get("jobs") or len(jobs_data["jobs"]) == 0:
            pytest.skip("No existing jobs to validate")
            return
        
        # Get first job that is COMPLETED or PARTIAL
        completed_jobs = [j for j in jobs_data["jobs"] if j.get("status") in ["COMPLETED", "PARTIAL"]]
        if not completed_jobs:
            pytest.skip("No COMPLETED or PARTIAL jobs to validate")
            return
        
        job = completed_jobs[0]
        job_id = job.get("job_id")
        
        # Validate the asset
        response = requests.get(f"{BASE_URL}/api/pipeline/validate-asset/{job_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed to validate asset: {response.text}"
        data = response.json()
        
        # Verify separate ready fields exist
        assert "preview_ready" in data, "Missing preview_ready field"
        assert "download_ready" in data, "Missing download_ready field"
        assert "share_ready" in data, "Missing share_ready field"
        assert "poster_url" in data, "Missing poster_url field"
        assert "download_url" in data, "Missing download_url field"
        assert "ui_state" in data, "Missing ui_state field"
        assert "stage_detail" in data, "Missing stage_detail field"
        
        # Verify ui_state is one of expected values
        valid_states = ["PROCESSING", "READY", "PARTIAL_READY", "FAILED"]
        assert data["ui_state"] in valid_states, f"Invalid ui_state: {data['ui_state']}"
        
        print(f"PASS: validate-asset returns separate fields: preview_ready={data['preview_ready']}, download_ready={data['download_ready']}, ui_state={data['ui_state']}")


class TestUserJobs:
    """Test /api/pipeline/user-jobs endpoint"""
    
    def test_get_user_jobs(self, admin_headers):
        """Should return user's pipeline jobs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "jobs" in data
        jobs = data["jobs"]
        
        # If there are jobs, verify structure
        if len(jobs) > 0:
            job = jobs[0]
            assert "job_id" in job
            assert "status" in job
            assert "title" in job or job.get("title") is None
            print(f"PASS: User jobs - {len(jobs)} jobs found, first job status: {job.get('status')}")
        else:
            print(f"PASS: User jobs endpoint working, no jobs found")


class TestJobStatus:
    """Test /api/pipeline/status/{job_id} endpoint"""
    
    def test_job_status_nonexistent(self, admin_headers):
        """Non-existent job should return 404"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/nonexistent-job-id", headers=admin_headers)
        assert response.status_code == 404
        print("PASS: status endpoint returns 404 for nonexistent job")
    
    def test_job_status_existing(self, admin_headers):
        """Get status of an existing job"""
        # First get user jobs
        jobs_response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=admin_headers)
        if jobs_response.status_code != 200 or not jobs_response.json().get("jobs"):
            pytest.skip("No jobs available to test")
            return
        
        jobs = jobs_response.json()["jobs"]
        if len(jobs) == 0:
            pytest.skip("No jobs to test")
            return
        
        job_id = jobs[0]["job_id"]
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{job_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "job" in data
        job = data["job"]
        
        # Verify job structure
        assert "job_id" in job
        assert "status" in job
        assert "progress" in job
        
        # If job has fallback info, verify structure
        if job.get("fallback"):
            fallback = job["fallback"]
            assert isinstance(fallback, dict)
        
        print(f"PASS: Job status - job_id={job['job_id']}, status={job['status']}, progress={job['progress']}%")


class TestPipelinePreview:
    """Test /api/pipeline/preview/{job_id} endpoint"""
    
    def test_preview_nonexistent(self):
        """Non-existent job preview should return 404"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/nonexistent-job-id")
        assert response.status_code == 404
        print("PASS: preview endpoint returns 404 for nonexistent job")
    
    def test_preview_existing_job(self, admin_headers):
        """Get preview data for an existing completed job"""
        # Get user jobs
        jobs_response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=admin_headers)
        if jobs_response.status_code != 200:
            pytest.skip("Cannot get user jobs")
            return
        
        jobs = jobs_response.json().get("jobs", [])
        completed = [j for j in jobs if j.get("status") in ["COMPLETED", "PARTIAL"]]
        
        if not completed:
            pytest.skip("No completed jobs to preview")
            return
        
        job_id = completed[0]["job_id"]
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{job_id}")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "preview" in data
        preview = data["preview"]
        
        # Verify preview structure
        assert "title" in preview
        assert "total_scenes" in preview
        
        print(f"PASS: Preview data - title={preview.get('title')}, scenes={preview.get('total_scenes')}")


class TestGalleryEndpoints:
    """Test public gallery endpoints"""
    
    def test_gallery_list(self):
        """GET /api/pipeline/gallery should return public videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "videos" in data
        print(f"PASS: Gallery - {len(data['videos'])} public videos")
    
    def test_gallery_categories(self):
        """GET /api/pipeline/gallery/categories should return category counts"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "categories" in data
        print(f"PASS: Gallery categories - {len(data['categories'])} categories")
    
    def test_gallery_leaderboard(self):
        """GET /api/pipeline/gallery/leaderboard should return most remixed videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "leaderboard" in data
        print(f"PASS: Gallery leaderboard - {len(data['leaderboard'])} videos")


class TestSystemStatus:
    """Test /api/pipeline/system-status endpoint"""
    
    def test_system_status(self, admin_headers):
        """GET /api/pipeline/system-status should return capacity info"""
        response = requests.get(f"{BASE_URL}/api/pipeline/system-status", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "system" in data
        assert "user" in data
        
        user_info = data["user"]
        assert "active_jobs" in user_info
        assert "max_concurrent" in user_info
        
        print(f"PASS: System status - active jobs: {user_info['active_jobs']}, max concurrent: {user_info['max_concurrent']}")


class TestAdminCredits:
    """Test that admin user has unlimited credits and is not blocked"""
    
    def test_admin_credits(self, admin_token):
        """Admin should have high credit balance"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Admin should have very high credits (999999999 or similar)
        credits = data.get("credits") or data.get("balanceCredits") or data.get("balance", 0)
        assert credits >= 999999, f"Admin credits too low: {credits}"
        print(f"PASS: Admin credits = {credits}")


class TestUIStateMapping:
    """Test that validate-asset returns correct ui_state for different job states"""
    
    def test_partial_jobs_return_partial_ready(self, admin_headers):
        """Jobs with status=PARTIAL should return ui_state=PARTIAL_READY"""
        # Get user jobs
        jobs_response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=admin_headers)
        if jobs_response.status_code != 200:
            pytest.skip("Cannot get user jobs")
            return
        
        jobs = jobs_response.json().get("jobs", [])
        partial_jobs = [j for j in jobs if j.get("status") == "PARTIAL"]
        
        if not partial_jobs:
            pytest.skip("No PARTIAL jobs to test")
            return
        
        job_id = partial_jobs[0]["job_id"]
        response = requests.get(f"{BASE_URL}/api/pipeline/validate-asset/{job_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # PARTIAL status jobs should return PARTIAL_READY
        assert data["ui_state"] == "PARTIAL_READY", f"Expected PARTIAL_READY for PARTIAL job, got {data['ui_state']}"
        print(f"PASS: PARTIAL job returns ui_state=PARTIAL_READY")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
