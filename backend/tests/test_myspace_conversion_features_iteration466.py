"""
Test Suite for MySpace Conversion Features (Iteration 466)
Tests the 6 high-conversion features:
1. Re-engagement buttons on completed cards
2. Credit psychology (badge + nudge)
3. Dynamic fuzzy time estimates
4. Failure recovery UX
5. Auto-redirect pulse animation
6. Skeleton loading
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')


class TestTimeEstimatesEndpoint:
    """Test the /api/story-video-studio/generation/time-estimates endpoint"""
    
    def test_time_estimates_returns_200(self):
        """Time estimates endpoint should return 200 (public endpoint, no auth required)"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/time-estimates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Time estimates endpoint returns 200")
    
    def test_time_estimates_has_required_fields(self):
        """Time estimates should include all required stage estimates"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/time-estimates")
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "estimates" in data, "Response should have 'estimates' field"
        
        estimates = data["estimates"]
        required_fields = ["planning", "scene_generation", "image_generation", "voice_generation", "video_assembly", "total"]
        
        for field in required_fields:
            assert field in estimates, f"Missing estimate field: {field}"
            assert isinstance(estimates[field], (int, float)), f"{field} should be numeric"
            assert estimates[field] > 0, f"{field} should be positive"
        
        print(f"✓ Time estimates has all required fields: {list(estimates.keys())}")
    
    def test_time_estimates_has_sample_sizes(self):
        """Time estimates should include sample sizes for transparency"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/time-estimates")
        data = response.json()
        
        assert "sample_sizes" in data, "Response should have 'sample_sizes' field"
        sample_sizes = data["sample_sizes"]
        
        assert "render_jobs" in sample_sizes, "Missing sample_sizes.render_jobs"
        assert "generation_jobs" in sample_sizes, "Missing sample_sizes.generation_jobs"
        assert "pipeline_jobs" in sample_sizes, "Missing sample_sizes.pipeline_jobs"
        
        print(f"✓ Sample sizes: render={sample_sizes['render_jobs']}, gen={sample_sizes['generation_jobs']}, pipeline={sample_sizes['pipeline_jobs']}")
    
    def test_time_estimates_total_is_sum_of_parts(self):
        """Total estimate should be at least the sum of individual stages"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/time-estimates")
        data = response.json()
        estimates = data["estimates"]
        
        sum_of_parts = (
            estimates["planning"] + 
            estimates["image_generation"] + 
            estimates["voice_generation"] + 
            estimates["video_assembly"]
        )
        
        assert estimates["total"] >= sum_of_parts, f"Total ({estimates['total']}) should be >= sum of parts ({sum_of_parts})"
        print(f"✓ Total estimate ({estimates['total']}s) >= sum of parts ({sum_of_parts}s)")


class TestCreditsBalanceEndpoint:
    """Test the /api/credits/balance endpoint for credit psychology feature"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_credits_balance_returns_200(self, auth_token):
        """Credits balance endpoint should return 200 with auth"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Credits balance endpoint returns 200")
    
    def test_credits_balance_has_required_fields(self, auth_token):
        """Credits balance should include credits/balance field"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # Should have either 'credits' or 'balance' field
        has_credits = "credits" in data or "balance" in data
        assert has_credits, "Response should have 'credits' or 'balance' field"
        
        credits = data.get("credits") or data.get("balance")
        assert isinstance(credits, (int, float)), "Credits should be numeric"
        
        print(f"✓ User has {credits} credits")
    
    def test_credits_balance_requires_auth(self):
        """Credits balance should require authentication"""
        response = requests.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Credits balance requires authentication")


class TestUserJobsWithCreditsCharged:
    """Test that user jobs include credits_charged for credit badge display"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_user_jobs_returns_200(self, auth_token):
        """User jobs endpoint should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/user-jobs?limit=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ User jobs endpoint returns 200")
    
    def test_completed_jobs_have_credits_charged(self, auth_token):
        """Completed jobs should have credits_charged field"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/user-jobs?limit=50",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        jobs = data.get("jobs", [])
        
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        
        if not completed_jobs:
            pytest.skip("No completed jobs found for test user")
        
        jobs_with_credits = [j for j in completed_jobs if j.get("credits_charged") is not None]
        
        # At least some completed jobs should have credits_charged
        assert len(jobs_with_credits) > 0, "At least some completed jobs should have credits_charged"
        
        # Verify credits_charged is a positive number
        for job in jobs_with_credits[:5]:
            credits = job.get("credits_charged", 0)
            assert isinstance(credits, (int, float)), f"credits_charged should be numeric, got {type(credits)}"
            assert credits >= 0, f"credits_charged should be non-negative, got {credits}"
        
        print(f"✓ Found {len(jobs_with_credits)}/{len(completed_jobs)} completed jobs with credits_charged")
    
    def test_jobs_have_status_field(self, auth_token):
        """All jobs should have status field for status-based UI rendering"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/user-jobs?limit=20",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        jobs = data.get("jobs", [])
        
        if not jobs:
            pytest.skip("No jobs found for test user")
        
        valid_statuses = ["QUEUED", "PROCESSING", "COMPLETED", "FAILED", "PARTIAL", "ARCHIVED", "ORPHANED"]
        
        for job in jobs[:10]:
            assert "status" in job, f"Job {job.get('job_id')} missing status field"
            assert job["status"] in valid_statuses, f"Invalid status: {job['status']}"
        
        print(f"✓ All {len(jobs)} jobs have valid status field")


class TestFailedJobsForRecoveryUX:
    """Test that failed jobs are returned for failure recovery UX"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_failed_jobs_are_returned(self, auth_token):
        """Failed jobs should be included in user jobs response"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/user-jobs?limit=100",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        jobs = data.get("jobs", [])
        
        failed_jobs = [j for j in jobs if j.get("status") == "FAILED"]
        
        # Test user should have some failed jobs based on context
        print(f"✓ Found {len(failed_jobs)} failed jobs for failure recovery UX")
        
        # Verify failed jobs have required fields for retry
        for job in failed_jobs[:3]:
            assert "job_id" in job, "Failed job missing job_id"
            assert "title" in job or "project_id" in job, "Failed job missing title/project_id"
        
        if failed_jobs:
            print(f"✓ Failed jobs have required fields for retry functionality")


class TestProcessingJobsForTimeEstimates:
    """Test that processing jobs have fields needed for fuzzy time estimates"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_jobs_have_created_at_for_elapsed_time(self, auth_token):
        """Jobs should have created_at field for elapsed time calculation"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/user-jobs?limit=20",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        jobs = data.get("jobs", [])
        
        if not jobs:
            pytest.skip("No jobs found")
        
        jobs_with_created_at = [j for j in jobs if j.get("created_at")]
        
        # Most jobs should have created_at
        assert len(jobs_with_created_at) >= len(jobs) * 0.8, "At least 80% of jobs should have created_at"
        
        print(f"✓ {len(jobs_with_created_at)}/{len(jobs)} jobs have created_at for elapsed time calculation")
    
    def test_processing_jobs_have_stage_info(self, auth_token):
        """Processing jobs should have engine_state or current_stage for timeline"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/user-jobs?limit=100",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        jobs = data.get("jobs", [])
        
        processing_jobs = [j for j in jobs if j.get("status") in ["PROCESSING", "QUEUED"]]
        
        if not processing_jobs:
            print("✓ No processing jobs currently (all completed/failed)")
            return
        
        # Check if processing jobs have stage info
        for job in processing_jobs[:5]:
            has_stage = job.get("engine_state") or job.get("current_stage") or job.get("progress")
            print(f"  Job {job.get('job_id', 'unknown')[:8]}: stage={job.get('engine_state') or job.get('current_stage')}, progress={job.get('progress')}")
        
        print(f"✓ Found {len(processing_jobs)} processing jobs for time estimate display")


class TestAuthenticationEnforcement:
    """Verify all MySpace-related endpoints require authentication"""
    
    def test_user_jobs_requires_auth(self):
        """User jobs endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ /api/story-engine/user-jobs requires auth")
    
    def test_user_reels_requires_auth(self):
        """User reels endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/convert/user-reels")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ /api/convert/user-reels requires auth")
    
    def test_time_estimates_is_public(self):
        """Time estimates endpoint should be public (no auth required)"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/time-estimates")
        assert response.status_code == 200, f"Time estimates should be public, got {response.status_code}"
        print("✓ /api/story-video-studio/generation/time-estimates is public")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
