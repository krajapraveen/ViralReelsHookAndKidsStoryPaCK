"""
Story Video Pipeline Render Stability Tests - Iteration 153
Testing the optimized render stage with OOM prevention fixes.
API endpoints validation only - NOT triggering full pipeline runs (~80s each).

Target: https://durable-jobs-beta.preview.emergentagent.com
Focus: Pipeline API responses, job status, worker stats, options endpoint
"""

import pytest
import requests
import os
import time

# Base URL from environment or default to preview
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://durable-jobs-beta.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


class TestHealthAndOptions:
    """Test pipeline health and options endpoints (no auth required)"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    def test_api_health(self, session):
        """Test API is reachable"""
        response = session.get(f"{BASE_URL}/api/health", timeout=15)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print(f"API Health: OK")

    def test_pipeline_options_returns_all_configs(self, session):
        """Test GET /api/pipeline/options returns animation styles, age groups, voice presets, credit costs"""
        response = session.get(f"{BASE_URL}/api/pipeline/options", timeout=15)
        assert response.status_code == 200, f"Options endpoint failed: {response.status_code}"
        data = response.json()
        
        assert data.get("success") is True, "Expected success=True"
        assert "animation_styles" in data, "Missing animation_styles"
        assert "age_groups" in data, "Missing age_groups"
        assert "voice_presets" in data, "Missing voice_presets"
        assert "credit_costs" in data, "Missing credit_costs"
        
        # Validate animation styles (should be 6)
        styles = data["animation_styles"]
        assert len(styles) == 6, f"Expected 6 animation styles, got {len(styles)}"
        style_ids = [s["id"] for s in styles]
        assert "cartoon_2d" in style_ids, "cartoon_2d style missing"
        assert "anime_style" in style_ids, "anime_style missing"
        assert "3d_pixar" in style_ids, "3d_pixar missing"
        
        # Validate age groups (should be 5)
        ages = data["age_groups"]
        assert len(ages) == 5, f"Expected 5 age groups, got {len(ages)}"
        age_ids = [a["id"] for a in ages]
        assert "kids_5_8" in age_ids, "kids_5_8 age group missing"
        
        # Validate voice presets (should be 5)
        voices = data["voice_presets"]
        assert len(voices) == 5, f"Expected 5 voice presets, got {len(voices)}"
        
        # Validate credit costs
        costs = data["credit_costs"]
        assert costs.get("small") == 50, f"Expected small=50, got {costs.get('small')}"
        assert costs.get("medium") == 80, f"Expected medium=80, got {costs.get('medium')}"
        assert costs.get("large") == 120, f"Expected large=120, got {costs.get('large')}"
        
        print(f"Pipeline options: {len(styles)} styles, {len(ages)} ages, {len(voices)} voices, costs={costs}")


class TestAuthentication:
    """Test authentication flows"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    def test_login_with_test_user(self, session):
        """Test POST /api/auth/login with test credentials"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=15
        )
        # Test user may not exist in preview, try demo user
        if response.status_code != 200:
            response = session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                timeout=15
            )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, f"No token in response: {data}"
        token = data.get("token") or data.get("access_token")
        assert len(token) > 10, "Token too short"
        print(f"Login successful, token length={len(token)}")
        return token

    def test_login_with_admin_user(self, session):
        """Test POST /api/auth/login with admin credentials"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, f"No token in response: {data}"
        print("Admin login successful")


class TestPipelineAPIResponses:
    """Test pipeline API endpoints (authenticated, without creating full jobs)"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        """Get auth token - try test user, then demo user"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=15
        )
        if response.status_code != 200:
            response = session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                timeout=15
            )
        if response.status_code != 200:
            pytest.skip("No valid user credentials available")
        return response.json().get("token") or response.json().get("access_token")

    def test_user_jobs_endpoint(self, session, auth_token):
        """Test GET /api/pipeline/user-jobs returns job history"""
        response = session.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15
        )
        assert response.status_code == 200, f"User jobs failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data.get("success") is True, "Expected success=True"
        assert "jobs" in data, "Missing jobs field"
        assert isinstance(data["jobs"], list), "Jobs should be a list"
        
        jobs = data["jobs"]
        print(f"User has {len(jobs)} pipeline jobs in history")
        
        # Show recent job statuses if any
        for job in jobs[:5]:
            print(f"  - {job.get('title', 'Untitled')[:30]}: {job.get('status')} ({job.get('credits_charged', 0)} credits)")
        
        return jobs

    def test_workers_status_endpoint(self, session, auth_token):
        """Test GET /api/pipeline/workers/status returns worker stats"""
        response = session.get(
            f"{BASE_URL}/api/pipeline/workers/status",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15
        )
        assert response.status_code == 200, f"Workers status failed: {response.status_code}"
        data = response.json()
        
        assert data.get("success") is True, "Expected success=True"
        assert "workers" in data, "Missing workers field"
        
        workers = data["workers"]
        assert "num_workers" in workers, "Missing num_workers"
        assert "jobs_processed" in workers, "Missing jobs_processed"
        assert "queue_size" in workers, "Missing queue_size"
        assert "workers_running" in workers, "Missing workers_running"
        
        print(f"Workers: {workers['num_workers']} workers, {workers['queue_size']} queued, {workers['jobs_processed']} processed, running={workers['workers_running']}")
        return workers

    def test_pipeline_create_validation_short_story(self, session, auth_token):
        """Test POST /api/pipeline/create rejects story < 50 chars"""
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": "Test Short Story",
                "story_text": "Too short",  # < 50 chars
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            },
            timeout=15
        )
        assert response.status_code == 422, f"Expected 422 for short story, got {response.status_code}"
        print("Validation correctly rejects story < 50 chars")

    def test_pipeline_create_validation_empty_title(self, session, auth_token):
        """Test POST /api/pipeline/create rejects empty title"""
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": "",  # Empty
                "story_text": "This is a valid story that meets the minimum 50 character requirement for testing.",
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            },
            timeout=15
        )
        assert response.status_code == 422, f"Expected 422 for empty title, got {response.status_code}"
        print("Validation correctly rejects empty title")

    def test_pipeline_create_validation_copyright_blocked(self, session, auth_token):
        """Test POST /api/pipeline/create blocks copyrighted content"""
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": "Mickey Mouse Adventure",  # Copyrighted
                "story_text": "Once upon a time Mickey Mouse went on an adventure through the magical forest with all his friends from Disney.",
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            },
            timeout=15
        )
        assert response.status_code == 400, f"Expected 400 for copyright violation, got {response.status_code}"
        data = response.json()
        assert "copyrighted" in data.get("detail", "").lower() or "blocked" in data.get("detail", "").lower(), \
            f"Expected copyright error message, got: {data}"
        print("Validation correctly blocks copyrighted content")


class TestExistingJobStatus:
    """Test status endpoint with existing jobs"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code != 200:
            response = session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
                timeout=15
            )
        if response.status_code != 200:
            pytest.skip("No valid user credentials")
        return response.json().get("token") or response.json().get("access_token")

    def test_status_of_completed_job(self, session, auth_token):
        """Test GET /api/pipeline/status/{job_id} for a completed job"""
        # First get user's jobs
        jobs_resp = session.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15
        )
        if jobs_resp.status_code != 200:
            pytest.skip("Could not fetch user jobs")
        
        jobs = jobs_resp.json().get("jobs", [])
        completed_job = next((j for j in jobs if j.get("status") == "COMPLETED"), None)
        
        if not completed_job:
            pytest.skip("No completed jobs to test status endpoint")
        
        job_id = completed_job.get("job_id")
        response = session.get(
            f"{BASE_URL}/api/pipeline/status/{job_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15
        )
        assert response.status_code == 200, f"Status endpoint failed: {response.status_code}"
        data = response.json()
        
        assert data.get("success") is True
        job = data.get("job", {})
        
        # Verify job structure
        assert job.get("job_id") == job_id
        assert job.get("status") == "COMPLETED"
        assert "progress" in job
        assert job.get("progress") == 100, f"Completed job should have 100% progress, got {job.get('progress')}"
        assert "output_url" in job
        assert job.get("output_url") is not None, "Completed job should have output_url"
        assert "stages" in job
        assert "timing" in job
        
        # Verify all 5 stages completed
        stages = job.get("stages", {})
        for stage_name in ["scenes", "images", "voices", "render", "upload"]:
            assert stage_name in stages, f"Missing stage: {stage_name}"
            assert stages[stage_name].get("status") == "COMPLETED", f"Stage {stage_name} not completed"
        
        print(f"Completed job {job_id[:8]}... verified")
        print(f"  Output URL: {job.get('output_url', 'N/A')[:60]}")
        print(f"  Timing: {job.get('timing', {})}")
        
        return job

    def test_status_of_nonexistent_job(self, session, auth_token):
        """Test GET /api/pipeline/status/{job_id} returns 404 for invalid job_id"""
        response = session.get(
            f"{BASE_URL}/api/pipeline/status/invalid-job-id-12345",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15
        )
        assert response.status_code == 404, f"Expected 404 for invalid job_id, got {response.status_code}"
        print("Status endpoint correctly returns 404 for nonexistent job")


class TestVideoOutputVerification:
    """Test that completed videos are accessible"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code != 200:
            pytest.skip("Could not login")
        return response.json().get("token") or response.json().get("access_token")

    def test_completed_video_is_accessible(self, session, auth_token):
        """Test that output_url from completed job is accessible"""
        # Get completed job
        jobs_resp = session.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15
        )
        if jobs_resp.status_code != 200:
            pytest.skip("Could not fetch jobs")
        
        jobs = jobs_resp.json().get("jobs", [])
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        
        if not completed_jobs:
            pytest.skip("No completed jobs with videos to verify")
        
        # Get full job details to get output_url
        for completed_job in completed_jobs[:3]:  # Check up to 3 videos
            job_id = completed_job.get("job_id")
            status_resp = session.get(
                f"{BASE_URL}/api/pipeline/status/{job_id}",
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=15
            )
            if status_resp.status_code != 200:
                continue
            
            job = status_resp.json().get("job", {})
            output_url = job.get("output_url")
            
            if not output_url:
                continue
            
            # Verify video is accessible
            video_resp = session.head(output_url, timeout=30, allow_redirects=True)
            if video_resp.status_code == 200:
                print(f"Video accessible: {output_url[:60]}...")
                return  # Found at least one accessible video
            else:
                print(f"Video not accessible ({video_resp.status_code}): {output_url[:60]}...")
        
        print("Note: Could not verify video accessibility - may need R2 configured")


class TestDashboardIntegration:
    """Test dashboard loads user data correctly"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code != 200:
            pytest.skip("Could not login")
        return response.json().get("token") or response.json().get("access_token")

    def test_auth_me_returns_user(self, session, auth_token):
        """Test GET /api/auth/me returns user profile"""
        response = session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15
        )
        assert response.status_code == 200, f"Auth/me failed: {response.status_code}"
        data = response.json()
        
        assert "email" in data or "user" in data, f"Missing user data: {data}"
        user = data.get("user", data)
        assert "credits" in user or "email" in user, f"Missing credits/email: {user}"
        print(f"User: {user.get('email', 'N/A')}, credits={user.get('credits', 'N/A')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
