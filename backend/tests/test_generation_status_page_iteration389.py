"""
Test Suite: Universal Generation Status Page Verification (Iteration 389)
Tests the story-to-video generation flow including:
- Status endpoint response shape (timing, retry_info, notification_opt_in)
- Notification subscribe endpoint
- Validate-asset endpoint
- User jobs listing
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


class TestGenerationStatusPage:
    """Tests for Universal Generation Status Page features"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get authentication token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin authentication failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def completed_job_id(self, auth_token):
        """Get a completed job ID from user's jobs"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        if response.status_code == 200:
            jobs = response.json().get("jobs", [])
            # Find a completed story_engine job (not legacy)
            for job in jobs:
                if job.get("status") == "COMPLETED" and job.get("source") == "story_engine":
                    return job.get("job_id")
            # Fallback to any completed job
            for job in jobs:
                if job.get("status") == "COMPLETED":
                    return job.get("job_id")
        pytest.skip("No completed jobs found for testing")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 1: Status endpoint returns correct shape
    # ═══════════════════════════════════════════════════════════════
    def test_status_endpoint_returns_timing_object(self, auth_token, completed_job_id):
        """Verify /api/story-engine/status/{job_id} returns timing with elapsed_seconds and eta_seconds"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/status/{completed_job_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "job" in data, "Response should have job object"
        
        job = data["job"]
        assert "timing" in job, "Job should have timing object"
        
        timing = job["timing"]
        assert "elapsed_seconds" in timing, "timing should have elapsed_seconds"
        assert "eta_seconds" in timing, "timing should have eta_seconds"
        
        # For completed jobs, elapsed_seconds should be >= 0
        assert isinstance(timing["elapsed_seconds"], (int, float)), "elapsed_seconds should be numeric"
        assert timing["elapsed_seconds"] >= 0, "elapsed_seconds should be non-negative"
        
        print(f"✓ Status endpoint returns timing: elapsed={timing['elapsed_seconds']}s, eta={timing['eta_seconds']}")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 2: Status endpoint returns retry_info
    # ═══════════════════════════════════════════════════════════════
    def test_status_endpoint_returns_retry_info(self, auth_token, completed_job_id):
        """Verify /api/story-engine/status/{job_id} returns retry_info object"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/status/{completed_job_id}", headers=headers)
        
        assert response.status_code == 200
        job = response.json()["job"]
        
        assert "retry_info" in job, "Job should have retry_info object"
        
        retry_info = job["retry_info"]
        assert "current_attempt" in retry_info, "retry_info should have current_attempt"
        assert "max_attempts" in retry_info, "retry_info should have max_attempts"
        assert "can_retry" in retry_info, "retry_info should have can_retry"
        
        print(f"✓ Status endpoint returns retry_info: can_retry={retry_info['can_retry']}, attempts={retry_info['current_attempt']}")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 3: Status endpoint returns notification_opt_in
    # ═══════════════════════════════════════════════════════════════
    def test_status_endpoint_returns_notification_opt_in(self, auth_token, completed_job_id):
        """Verify /api/story-engine/status/{job_id} returns notification_opt_in field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/status/{completed_job_id}", headers=headers)
        
        assert response.status_code == 200
        job = response.json()["job"]
        
        assert "notification_opt_in" in job, "Job should have notification_opt_in field"
        assert isinstance(job["notification_opt_in"], bool), "notification_opt_in should be boolean"
        
        print(f"✓ Status endpoint returns notification_opt_in: {job['notification_opt_in']}")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 4: Status endpoint returns progress and current_step
    # ═══════════════════════════════════════════════════════════════
    def test_status_endpoint_returns_progress_fields(self, auth_token, completed_job_id):
        """Verify /api/story-engine/status/{job_id} returns progress and current_step"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/status/{completed_job_id}", headers=headers)
        
        assert response.status_code == 200
        job = response.json()["job"]
        
        assert "progress" in job, "Job should have progress field"
        assert "current_step" in job, "Job should have current_step field"
        assert "status" in job, "Job should have status field"
        
        # For completed jobs, progress should be 100
        if job["status"] == "COMPLETED":
            assert job["progress"] == 100, f"Completed job should have progress=100, got {job['progress']}"
        
        print(f"✓ Status endpoint returns progress={job['progress']}%, step={job['current_step']}")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 5: Status endpoint 404 for nonexistent job
    # ═══════════════════════════════════════════════════════════════
    def test_status_endpoint_404_for_nonexistent_job(self, auth_token):
        """Verify /api/story-engine/status/{fake_id} returns 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        fake_job_id = "nonexistent-job-id-12345"
        response = requests.get(f"{BASE_URL}/api/story-engine/status/{fake_job_id}", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Status endpoint returns 404 for nonexistent job")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 6: Notification subscribe endpoint works
    # ═══════════════════════════════════════════════════════════════
    def test_notification_subscribe_endpoint(self, auth_token, completed_job_id):
        """Verify POST /api/notifications/generation/{job_id}/subscribe works"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/notifications/generation/{completed_job_id}/subscribe",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "subscribed" in data, "Response should have subscribed field"
        
        print(f"✓ Notification subscribe endpoint works: subscribed={data.get('subscribed')}")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 7: Notification subscribe 404 for nonexistent job
    # ═══════════════════════════════════════════════════════════════
    def test_notification_subscribe_404_for_nonexistent_job(self, auth_token):
        """Verify POST /api/notifications/generation/{fake_id}/subscribe returns 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        fake_job_id = "nonexistent-job-id-67890"
        response = requests.post(
            f"{BASE_URL}/api/notifications/generation/{fake_job_id}/subscribe",
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Notification subscribe returns 404 for nonexistent job")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 8: Validate-asset endpoint returns correct shape
    # ═══════════════════════════════════════════════════════════════
    def test_validate_asset_endpoint(self, auth_token, completed_job_id):
        """Verify /api/story-engine/validate-asset/{job_id} returns correct ui_state"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/story-engine/validate-asset/{completed_job_id}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "ui_state" in data, "Response should have ui_state"
        assert data["ui_state"] in ["READY", "PARTIAL_READY", "FAILED", "PROCESSING"], \
            f"ui_state should be valid, got {data['ui_state']}"
        
        assert "preview_ready" in data, "Response should have preview_ready"
        assert "download_ready" in data, "Response should have download_ready"
        assert "share_ready" in data, "Response should have share_ready"
        
        print(f"✓ Validate-asset endpoint returns ui_state={data['ui_state']}, download_ready={data['download_ready']}")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 9: Validate-asset 404 for nonexistent job
    # ═══════════════════════════════════════════════════════════════
    def test_validate_asset_404_for_nonexistent_job(self, auth_token):
        """Verify /api/story-engine/validate-asset/{fake_id} returns 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        fake_job_id = "nonexistent-job-id-99999"
        response = requests.get(
            f"{BASE_URL}/api/story-engine/validate-asset/{fake_job_id}",
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Validate-asset returns 404 for nonexistent job")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 10: User jobs endpoint returns jobs list
    # ═══════════════════════════════════════════════════════════════
    def test_user_jobs_endpoint(self, auth_token):
        """Verify /api/story-engine/user-jobs returns jobs list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "jobs" in data, "Response should have jobs array"
        assert isinstance(data["jobs"], list), "jobs should be a list"
        
        if len(data["jobs"]) > 0:
            job = data["jobs"][0]
            assert "job_id" in job, "Job should have job_id"
            assert "status" in job, "Job should have status"
            assert "title" in job, "Job should have title"
        
        print(f"✓ User jobs endpoint returns {len(data['jobs'])} jobs")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 11: Story engine options endpoint
    # ═══════════════════════════════════════════════════════════════
    def test_story_engine_options_endpoint(self):
        """Verify /api/story-engine/options returns animation styles, age groups, voice presets"""
        response = requests.get(f"{BASE_URL}/api/story-engine/options")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "animation_styles" in data, "Response should have animation_styles"
        assert "age_groups" in data, "Response should have age_groups"
        assert "voice_presets" in data, "Response should have voice_presets"
        
        assert len(data["animation_styles"]) > 0, "Should have at least one animation style"
        assert len(data["age_groups"]) > 0, "Should have at least one age group"
        assert len(data["voice_presets"]) > 0, "Should have at least one voice preset"
        
        print(f"✓ Options endpoint returns {len(data['animation_styles'])} styles, {len(data['age_groups'])} ages, {len(data['voice_presets'])} voices")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 12: Rate limit status endpoint
    # ═══════════════════════════════════════════════════════════════
    def test_rate_limit_status_endpoint(self, auth_token):
        """Verify /api/story-engine/rate-limit-status returns rate limit info"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/rate-limit-status", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "can_create" in data, "Response should have can_create"
        assert "concurrent" in data, "Response should have concurrent"
        assert "max_concurrent" in data, "Response should have max_concurrent"
        
        print(f"✓ Rate limit status: can_create={data['can_create']}, concurrent={data['concurrent']}/{data['max_concurrent']}")
    
    # ═══════════════════════════════════════════════════════════════
    # TEST 13: Preview endpoint for completed job
    # ═══════════════════════════════════════════════════════════════
    def test_preview_endpoint(self, auth_token, completed_job_id):
        """Verify /api/story-engine/preview/{job_id} returns preview data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/story-engine/preview/{completed_job_id}",
            headers=headers
        )
        
        # Preview endpoint may return 200 or 404 depending on job type
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True, "Response should have success=True"
            assert "preview" in data, "Response should have preview object"
            
            preview = data["preview"]
            assert "title" in preview, "Preview should have title"
            assert "scenes" in preview, "Preview should have scenes"
            
            print(f"✓ Preview endpoint returns {len(preview.get('scenes', []))} scenes")
        else:
            print(f"✓ Preview endpoint returned {response.status_code} (job may be legacy)")


class TestPostgenPhaseActions:
    """Tests for postgen phase action buttons (Watch/Download/Share/Continue/Remix)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def completed_job_with_output(self, auth_token):
        """Get a completed job with output URL"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        if response.status_code == 200:
            jobs = response.json().get("jobs", [])
            for job in jobs:
                if job.get("status") == "COMPLETED" and job.get("output_url"):
                    return job
        pytest.skip("No completed job with output found")
    
    def test_completed_job_has_output_url(self, completed_job_with_output):
        """Verify completed job has output_url for Watch/Download"""
        assert completed_job_with_output.get("output_url"), "Completed job should have output_url"
        print(f"✓ Completed job has output_url: {completed_job_with_output['output_url'][:50]}...")
    
    def test_validate_asset_for_completed_job(self, auth_token, completed_job_with_output):
        """Verify validate-asset returns READY for completed job with output"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        job_id = completed_job_with_output["job_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/validate-asset/{job_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be READY or PARTIAL_READY for completed jobs
        assert data["ui_state"] in ["READY", "PARTIAL_READY"], \
            f"Expected READY/PARTIAL_READY, got {data['ui_state']}"
        
        print(f"✓ Validate-asset for completed job: ui_state={data['ui_state']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
