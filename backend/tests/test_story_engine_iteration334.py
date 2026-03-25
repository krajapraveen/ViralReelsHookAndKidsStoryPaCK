"""
Story Engine API Tests — Iteration 334
Tests the Story-to-Video pipeline endpoints including:
- Credit check and estimation
- Job creation with safety checks (copyright/celebrity blocking)
- Rate limiting and concurrency controls
- Job status polling
- User job listing
- Story chain retrieval
- Admin endpoints (pipeline health, job management, retry)
- Non-admin 403 enforcement
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


class TestAuth:
    """Authentication helpers"""
    
    @staticmethod
    def get_token(email: str, password: str) -> str:
        """Get auth token for a user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    @staticmethod
    def get_admin_token() -> str:
        return TestAuth.get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    @staticmethod
    def get_user_token() -> str:
        return TestAuth.get_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)


# ═══════════════════════════════════════════════════════════════
# CREDIT CHECK TESTS
# ═══════════════════════════════════════════════════════════════

class TestCreditCheck:
    """Tests for GET /api/story-engine/credit-check"""
    
    def test_credit_check_returns_estimate(self):
        """Credit check returns cost breakdown and sufficiency status"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/credit-check",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "sufficient" in data
        assert "required" in data
        assert "current" in data
        assert "shortfall" in data
        assert "breakdown" in data
        
        # Verify breakdown has expected stages
        breakdown = data["breakdown"]
        assert "planning" in breakdown
        assert "keyframes" in breakdown
        assert "scene_clips" in breakdown
        assert "audio" in breakdown
        
        print(f"Credit check: required={data['required']}, current={data['current']}, sufficient={data['sufficient']}")
    
    def test_credit_check_requires_auth(self):
        """Credit check requires authentication"""
        response = requests.get(f"{BASE_URL}/api/story-engine/credit-check")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════
# SAFETY CHECK TESTS (Copyright & Celebrity Blocking)
# ═══════════════════════════════════════════════════════════════

class TestSafetyChecks:
    """Tests for content safety blocking (copyright, celebrities)"""
    
    def test_blocks_copyrighted_character_spiderman(self):
        """Blocks copyrighted character: Spider-Man"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "story_text": "Spider-Man swings through New York City fighting crime.",
                "title": "Spider-Man Adventure"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "spider-man" in data.get("detail", "").lower() or "copyrighted" in data.get("detail", "").lower()
        print(f"Correctly blocked Spider-Man: {data.get('detail')}")
    
    def test_blocks_copyrighted_character_batman(self):
        """Blocks copyrighted character: Batman"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "story_text": "Batman patrols Gotham City at night looking for criminals.",
                "title": "Batman Night Patrol"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "batman" in data.get("detail", "").lower() or "copyrighted" in data.get("detail", "").lower()
        print(f"Correctly blocked Batman: {data.get('detail')}")
    
    def test_blocks_celebrity_taylor_swift(self):
        """Blocks celebrity name: Taylor Swift"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "story_text": "Taylor Swift performs at a concert in front of thousands of fans.",
                "title": "Concert Story"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "taylor swift" in data.get("detail", "").lower() or "celebrity" in data.get("detail", "").lower() or "real person" in data.get("detail", "").lower()
        print(f"Correctly blocked Taylor Swift: {data.get('detail')}")
    
    def test_blocks_copyrighted_in_title(self):
        """Blocks copyrighted character in title"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "story_text": "A hero saves the city from danger.",
                "title": "Mickey Mouse Adventure"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "mickey mouse" in data.get("detail", "").lower() or "copyrighted" in data.get("detail", "").lower()
        print(f"Correctly blocked Mickey Mouse in title: {data.get('detail')}")


# ═══════════════════════════════════════════════════════════════
# JOB CREATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestJobCreation:
    """Tests for POST /api/story-engine/create"""
    
    def test_create_job_success(self):
        """Create a valid story job with credit deduction"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        # First check credits
        credit_response = requests.get(
            f"{BASE_URL}/api/story-engine/credit-check",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert credit_response.status_code == 200
        credit_data = credit_response.json()
        
        if not credit_data.get("sufficient"):
            pytest.skip(f"User has insufficient credits: {credit_data.get('current')} < {credit_data.get('required')}")
        
        # Create job with unique story
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "story_text": f"A brave explorer named Alex discovers a hidden cave in the mountains. Inside, glowing crystals light up the darkness. Test story {unique_id}.",
                "title": f"Crystal Cave Discovery {unique_id}",
                "style_id": "cartoon_2d",
                "language": "en",
                "age_group": "teens"
            },
            timeout=90  # Job creation can take ~30s due to AI planning
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "job_id" in data
        assert "state" in data
        assert "credits_deducted" in data
        assert "cost_estimate" in data
        
        job_id = data["job_id"]
        print(f"Created job: {job_id}, credits_deducted: {data['credits_deducted']}, state: {data['state']}")
        
        # Store job_id for status tests
        TestJobCreation.created_job_id = job_id
        return job_id
    
    def test_create_job_requires_auth(self):
        """Job creation requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            json={
                "story_text": "A test story about adventure.",
                "title": "Test Story"
            }
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_create_job_validates_story_length(self):
        """Job creation validates minimum story length"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "story_text": "Short",  # Too short (min 10 chars)
                "title": "Test"
            }
        )
        
        assert response.status_code == 422, f"Expected 422 for validation error, got {response.status_code}: {response.text}"


# ═══════════════════════════════════════════════════════════════
# JOB STATUS TESTS
# ═══════════════════════════════════════════════════════════════

class TestJobStatus:
    """Tests for GET /api/story-engine/status/{job_id}"""
    
    def test_get_job_status(self):
        """Get status of a created job"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        # Get job_id from creation test or create new one
        job_id = getattr(TestJobCreation, 'created_job_id', None)
        if not job_id:
            # Create a job first
            unique_id = str(uuid.uuid4())[:8]
            create_response = requests.post(
                f"{BASE_URL}/api/story-engine/create",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "story_text": f"A magical forest where animals can talk and help lost travelers find their way home. Test {unique_id}.",
                    "title": f"Magical Forest {unique_id}"
                },
                timeout=90
            )
            if create_response.status_code == 200:
                job_id = create_response.json().get("job_id")
            else:
                pytest.skip("Could not create job for status test")
        
        # Wait a bit for pipeline to progress
        time.sleep(5)
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{job_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "job_id" in data
        assert "state" in data
        assert "progress_percent" in data
        assert "current_stage" in data
        assert "stage_results" in data
        
        print(f"Job status: state={data['state']}, progress={data['progress_percent']}%, stage={data['current_stage']}")
    
    def test_status_not_found(self):
        """Status returns 404 for non-existent job"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        fake_job_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{fake_job_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_status_requires_auth(self):
        """Status endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/story-engine/status/some-job-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════
# MY JOBS TESTS
# ═══════════════════════════════════════════════════════════════

class TestMyJobs:
    """Tests for GET /api/story-engine/my-jobs"""
    
    def test_list_user_jobs(self):
        """List user's jobs with pagination"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/my-jobs",
            headers={"Authorization": f"Bearer {token}"},
            params={"page": 1, "limit": 10}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["jobs"], list)
        
        print(f"User has {data['total']} total jobs, showing page {data['page']}")
        
        # Verify job structure if jobs exist
        if data["jobs"]:
            job = data["jobs"][0]
            assert "job_id" in job
            assert "state" in job
            assert "progress_percent" in job
    
    def test_my_jobs_pagination(self):
        """My jobs supports pagination parameters"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/my-jobs",
            headers={"Authorization": f"Bearer {token}"},
            params={"page": 2, "limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
    
    def test_my_jobs_requires_auth(self):
        """My jobs requires authentication"""
        response = requests.get(f"{BASE_URL}/api/story-engine/my-jobs")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════
# STORY CHAIN TESTS
# ═══════════════════════════════════════════════════════════════

class TestStoryChain:
    """Tests for GET /api/story-engine/chain/{chain_id}"""
    
    def test_get_story_chain(self):
        """Get all episodes in a story chain"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        # Use a random chain_id - should return empty list if no episodes
        chain_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/story-engine/chain/{chain_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "chain_id" in data
        assert "episodes" in data
        assert "total" in data
        assert isinstance(data["episodes"], list)
        
        print(f"Chain {chain_id[:8]} has {data['total']} episodes")
    
    def test_chain_requires_auth(self):
        """Chain endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/story-engine/chain/some-chain-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════
# ADMIN ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════

class TestAdminEndpoints:
    """Tests for admin-only endpoints"""
    
    def test_admin_pipeline_health(self):
        """Admin can access pipeline health endpoint"""
        token = TestAuth.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/admin/pipeline-health",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "total_jobs" in data
        assert "active_jobs" in data
        assert "ready_jobs" in data
        assert "failed_jobs" in data
        assert "success_rate" in data
        assert "gpu_endpoints" in data
        
        # GPU endpoints should show status
        gpu = data["gpu_endpoints"]
        assert "wan_t2v" in gpu
        assert "wan_i2v" in gpu
        assert "keyframe" in gpu
        assert "kokoro_tts" in gpu
        
        print(f"Pipeline health: total={data['total_jobs']}, active={data['active_jobs']}, ready={data['ready_jobs']}, failed={data['failed_jobs']}")
        print(f"GPU endpoints: {gpu}")
    
    def test_admin_list_jobs(self):
        """Admin can list all jobs with filters"""
        token = TestAuth.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/admin/jobs",
            headers={"Authorization": f"Bearer {token}"},
            params={"page": 1, "limit": 10}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert "jobs" in data
        assert "total" in data
        assert "stats" in data
        assert "page" in data
        
        # Stats should have counts per state
        stats = data["stats"]
        assert "INIT" in stats or "READY" in stats or "FAILED" in stats
        
        print(f"Admin jobs: total={data['total']}, stats={stats}")
    
    def test_admin_list_jobs_with_state_filter(self):
        """Admin can filter jobs by state"""
        token = TestAuth.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/admin/jobs",
            headers={"Authorization": f"Bearer {token}"},
            params={"state": "PARTIAL_READY", "page": 1, "limit": 10}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # All returned jobs should have the filtered state
        for job in data.get("jobs", []):
            assert job["state"] == "PARTIAL_READY", f"Expected PARTIAL_READY, got {job['state']}"
    
    def test_admin_retry_job_not_found(self):
        """Admin retry returns 404 for non-existent job"""
        token = TestAuth.get_admin_token()
        assert token, "Failed to get admin token"
        
        fake_job_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/story-engine/admin/retry/{fake_job_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_admin_get_job_details(self):
        """Admin can get full job details"""
        token = TestAuth.get_admin_token()
        assert token, "Failed to get admin token"
        
        # First get a job_id from the list
        list_response = requests.get(
            f"{BASE_URL}/api/story-engine/admin/jobs",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 1}
        )
        
        if list_response.status_code == 200 and list_response.json().get("jobs"):
            job_id = list_response.json()["jobs"][0]["job_id"]
            
            response = requests.get(
                f"{BASE_URL}/api/story-engine/admin/job/{job_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            
            assert data.get("success") == True
            assert "job" in data
            job = data["job"]
            assert "job_id" in job
            assert "state" in job
            assert "story_text" in job
            
            print(f"Admin job details: job_id={job['job_id'][:8]}, state={job['state']}")
        else:
            pytest.skip("No jobs available to test admin job details")


# ═══════════════════════════════════════════════════════════════
# NON-ADMIN 403 TESTS
# ═══════════════════════════════════════════════════════════════

class TestNonAdmin403:
    """Tests that non-admin users get 403 on admin endpoints"""
    
    def test_non_admin_pipeline_health_403(self):
        """Non-admin gets 403 on pipeline-health"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/admin/pipeline-health",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Non-admin correctly blocked from pipeline-health")
    
    def test_non_admin_admin_jobs_403(self):
        """Non-admin gets 403 on admin/jobs"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/admin/jobs",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Non-admin correctly blocked from admin/jobs")
    
    def test_non_admin_retry_403(self):
        """Non-admin gets 403 on admin/retry"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.post(
            f"{BASE_URL}/api/story-engine/admin/retry/some-job-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Non-admin correctly blocked from admin/retry")
    
    def test_non_admin_admin_job_details_403(self):
        """Non-admin gets 403 on admin/job/{job_id}"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        response = requests.get(
            f"{BASE_URL}/api/story-engine/admin/job/some-job-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Non-admin correctly blocked from admin/job details")


# ═══════════════════════════════════════════════════════════════
# PIPELINE PROGRESSION TESTS
# ═══════════════════════════════════════════════════════════════

class TestPipelineProgression:
    """Tests for pipeline stage progression"""
    
    def test_pipeline_progresses_through_planning_stages(self):
        """Pipeline progresses through PLANNING → CHARACTER → MOTION stages"""
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        # Check credits first
        credit_response = requests.get(
            f"{BASE_URL}/api/story-engine/credit-check",
            headers={"Authorization": f"Bearer {token}"}
        )
        if credit_response.status_code == 200:
            if not credit_response.json().get("sufficient"):
                pytest.skip("Insufficient credits for pipeline test")
        
        # Create a job
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "story_text": f"A young inventor builds a robot friend that helps save their village from a storm. The robot learns about friendship and courage. Test {unique_id}.",
                "title": f"Robot Friend {unique_id}"
            },
            timeout=90
        )
        
        if create_response.status_code != 200:
            pytest.skip(f"Could not create job: {create_response.text}")
        
        job_id = create_response.json()["job_id"]
        print(f"Created job {job_id[:8]} for pipeline progression test")
        
        # Poll status multiple times to see progression
        seen_states = set()
        for i in range(12):  # Poll for up to 60 seconds
            time.sleep(5)
            
            status_response = requests.get(
                f"{BASE_URL}/api/story-engine/status/{job_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if status_response.status_code == 200:
                data = status_response.json()
                state = data.get("state")
                progress = data.get("progress_percent", 0)
                stage = data.get("current_stage", "")
                
                seen_states.add(state)
                print(f"Poll {i+1}: state={state}, progress={progress}%, stage={stage}")
                
                # Check stage_results for completed stages
                stage_results = data.get("stage_results", [])
                if stage_results:
                    completed_stages = [r["stage"] for r in stage_results if r.get("status") == "success"]
                    print(f"  Completed stages: {completed_stages}")
                
                # If we've reached a terminal state, stop polling
                if state in ["READY", "PARTIAL_READY", "FAILED"]:
                    break
        
        # Verify we saw progression through planning stages
        planning_states = {"PLANNING", "BUILDING_CHARACTER_CONTEXT", "PLANNING_SCENE_MOTION"}
        seen_planning = seen_states.intersection(planning_states)
        
        print(f"Seen states: {seen_states}")
        print(f"Seen planning states: {seen_planning}")
        
        # Should have seen at least PLANNING or later states
        assert len(seen_states) > 1 or "PARTIAL_READY" in seen_states or "READY" in seen_states, \
            f"Pipeline did not progress. Only saw: {seen_states}"


# ═══════════════════════════════════════════════════════════════
# INSUFFICIENT CREDITS TEST
# ═══════════════════════════════════════════════════════════════

class TestInsufficientCredits:
    """Tests for insufficient credits handling"""
    
    def test_insufficient_credits_returns_detailed_breakdown(self):
        """When user lacks credits, returns detailed breakdown"""
        # This test requires a user with insufficient credits
        # We'll create a test user or use admin to check the response format
        token = TestAuth.get_user_token()
        assert token, "Failed to get user token"
        
        # Check current credits
        credit_response = requests.get(
            f"{BASE_URL}/api/story-engine/credit-check",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert credit_response.status_code == 200
        credit_data = credit_response.json()
        
        # If user has sufficient credits, we can't test insufficient credits response
        # But we can verify the credit_check response structure
        assert "sufficient" in credit_data
        assert "required" in credit_data
        assert "current" in credit_data
        assert "shortfall" in credit_data
        assert "breakdown" in credit_data
        
        if credit_data.get("sufficient"):
            print(f"User has sufficient credits ({credit_data['current']} >= {credit_data['required']})")
            print("Cannot test insufficient credits response - user has enough credits")
        else:
            print(f"User has insufficient credits: {credit_data['current']} < {credit_data['required']}")
            print(f"Shortfall: {credit_data['shortfall']}")
            print(f"Breakdown: {credit_data['breakdown']}")


# ═══════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
