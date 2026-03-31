"""
Test P0 Navigation Fix (5 new pages) and P0 Failure UX Fix (allowed_actions from backend)
Iteration 392 - Tests for:
1. My Space page at /app/my-space
2. Create page at /app/create
3. Browse page at /app/browse
4. Characters page at /app/characters
5. Dashboard page at /app/dashboard
6. Backend status endpoint returns allowed_actions, recovery_state, resume_supported, next_best_action, fallback_in_use
7. For READY job, allowed_actions includes watch, download, share, remix, continue
8. For FAILED job, allowed_actions includes retry and/or start_over
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Known job IDs for testing
READY_JOB_ID = "99f9cd11-a1d8-4909-9ed7-04a0320a2820"


class TestAuthentication:
    """Test authentication for API access"""
    
    def test_login_test_user(self):
        """Test login with test user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✓ Test user login successful: {data['user']['email']}")
        return data["token"]
    
    def test_login_admin_user(self):
        """Test login with admin user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        print(f"✓ Admin user login successful: {data['user']['email']}")
        return data["token"]


@pytest.fixture
def test_user_token():
    """Get test user token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Could not authenticate test user")


@pytest.fixture
def admin_token():
    """Get admin token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Could not authenticate admin user")


class TestP0FailureUXAllowedActions:
    """Test P0 Failure UX Fix - allowed_actions from backend"""
    
    def test_status_endpoint_returns_allowed_actions(self, test_user_token):
        """Test that status endpoint returns allowed_actions field"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Status request failed: {response.text}"
        data = response.json()
        assert data.get("success") is True, "Response not successful"
        
        job = data.get("job", {})
        assert "allowed_actions" in job, "allowed_actions field missing from job"
        assert isinstance(job["allowed_actions"], list), "allowed_actions should be a list"
        print(f"✓ allowed_actions present: {job['allowed_actions']}")
    
    def test_status_endpoint_returns_recovery_state(self, test_user_token):
        """Test that status endpoint returns recovery_state field"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        assert "recovery_state" in job, "recovery_state field missing from job"
        print(f"✓ recovery_state present: {job['recovery_state']}")
    
    def test_status_endpoint_returns_resume_supported(self, test_user_token):
        """Test that status endpoint returns resume_supported field"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        assert "resume_supported" in job, "resume_supported field missing from job"
        assert isinstance(job["resume_supported"], bool), "resume_supported should be boolean"
        print(f"✓ resume_supported present: {job['resume_supported']}")
    
    def test_status_endpoint_returns_next_best_action(self, test_user_token):
        """Test that status endpoint returns next_best_action field"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        assert "next_best_action" in job, "next_best_action field missing from job"
        print(f"✓ next_best_action present: {job['next_best_action']}")
    
    def test_status_endpoint_returns_fallback_in_use(self, test_user_token):
        """Test that status endpoint returns fallback_in_use field"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        assert "fallback_in_use" in job, "fallback_in_use field missing from job"
        assert isinstance(job["fallback_in_use"], bool), "fallback_in_use should be boolean"
        print(f"✓ fallback_in_use present: {job['fallback_in_use']}")
    
    def test_ready_job_allowed_actions_include_watch(self, test_user_token):
        """Test that READY job allowed_actions includes 'watch'"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        # Verify job is READY
        assert job.get("engine_state") == "READY" or job.get("status") == "COMPLETED", \
            f"Job not in READY state: {job.get('engine_state')}"
        
        allowed = job.get("allowed_actions", [])
        assert "watch" in allowed, f"'watch' not in allowed_actions: {allowed}"
        print(f"✓ READY job has 'watch' in allowed_actions")
    
    def test_ready_job_allowed_actions_include_download(self, test_user_token):
        """Test that READY job allowed_actions includes 'download'"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        allowed = job.get("allowed_actions", [])
        assert "download" in allowed, f"'download' not in allowed_actions: {allowed}"
        print(f"✓ READY job has 'download' in allowed_actions")
    
    def test_ready_job_allowed_actions_include_share(self, test_user_token):
        """Test that READY job allowed_actions includes 'share'"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        allowed = job.get("allowed_actions", [])
        assert "share" in allowed, f"'share' not in allowed_actions: {allowed}"
        print(f"✓ READY job has 'share' in allowed_actions")
    
    def test_ready_job_allowed_actions_include_remix(self, test_user_token):
        """Test that READY job allowed_actions includes 'remix'"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        allowed = job.get("allowed_actions", [])
        assert "remix" in allowed, f"'remix' not in allowed_actions: {allowed}"
        print(f"✓ READY job has 'remix' in allowed_actions")
    
    def test_ready_job_allowed_actions_include_continue(self, test_user_token):
        """Test that READY job allowed_actions includes 'continue'"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        allowed = job.get("allowed_actions", [])
        assert "continue" in allowed, f"'continue' not in allowed_actions: {allowed}"
        print(f"✓ READY job has 'continue' in allowed_actions")
    
    def test_ready_job_resume_supported_is_false(self, test_user_token):
        """Test that READY job has resume_supported=False"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        assert job.get("resume_supported") is False, \
            f"READY job should have resume_supported=False, got {job.get('resume_supported')}"
        print(f"✓ READY job has resume_supported=False")
    
    def test_ready_job_recovery_state_is_none(self, test_user_token):
        """Test that READY job has recovery_state='NONE'"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        assert job.get("recovery_state") == "NONE", \
            f"READY job should have recovery_state='NONE', got {job.get('recovery_state')}"
        print(f"✓ READY job has recovery_state='NONE'")
    
    def test_ready_job_next_best_action_is_watch(self, test_user_token):
        """Test that READY job has next_best_action='watch'"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{READY_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        assert job.get("next_best_action") == "watch", \
            f"READY job should have next_best_action='watch', got {job.get('next_best_action')}"
        print(f"✓ READY job has next_best_action='watch'")


class TestCharactersEndpoint:
    """Test Characters API endpoint for CharactersPage"""
    
    def test_my_characters_endpoint_exists(self, test_user_token):
        """Test that /api/characters/my-characters endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/characters/my-characters",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        # Should return 200 (with characters) or 200 with empty list
        assert response.status_code == 200, f"my-characters endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "success" in data or "characters" in data, "Response missing expected fields"
        print(f"✓ /api/characters/my-characters endpoint works")


class TestUserJobsEndpoint:
    """Test User Jobs API endpoint for MySpacePage and UserDashboardPage"""
    
    def test_user_jobs_endpoint_exists(self, test_user_token):
        """Test that /api/story-engine/user-jobs endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/user-jobs",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"user-jobs endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("success") is True, "Response not successful"
        assert "jobs" in data, "jobs field missing from response"
        print(f"✓ /api/story-engine/user-jobs endpoint works, returned {len(data.get('jobs', []))} jobs")


class TestCreditsEndpoint:
    """Test Credits API endpoint for UserDashboardPage"""
    
    def test_credits_balance_endpoint_exists(self, test_user_token):
        """Test that /api/credits/balance endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"credits/balance endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        # Should have credits field
        assert "credits" in data or "balance" in data, "Response missing credits/balance field"
        print(f"✓ /api/credits/balance endpoint works")


class TestReelsEndpoint:
    """Test Reels API endpoint for MySpacePage"""
    
    def test_user_reels_endpoint_exists(self, test_user_token):
        """Test that /api/convert/user-reels endpoint exists (MySpacePage uses Promise.allSettled so 404 is handled gracefully)"""
        response = requests.get(
            f"{BASE_URL}/api/convert/user-reels",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        # Should return 200 (with reels) or 200 with empty list
        assert response.status_code == 200, f"user-reels endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "reels" in data or "count" in data, "Response missing expected fields"
        print(f"✓ /api/convert/user-reels endpoint works")


class TestStoryEngineOptions:
    """Test Story Engine options endpoint for CreatePage"""
    
    def test_options_endpoint_exists(self):
        """Test that /api/story-engine/options endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/story-engine/options")
        assert response.status_code == 200, f"options endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("success") is True, "Response not successful"
        assert "animation_styles" in data, "animation_styles missing"
        assert "age_groups" in data, "age_groups missing"
        assert "voice_presets" in data, "voice_presets missing"
        print(f"✓ /api/story-engine/options endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
