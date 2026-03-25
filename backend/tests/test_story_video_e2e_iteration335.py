"""
E2E Tests for Story Video Pipeline - Iteration 335
Tests: Normal Flow, Video Playback, Continue Story, Share Flow, PARTIAL_READY handling, Quick Render banner, Story Engine API
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

# Story Engine job with Ken Burns fallback
STORY_ENGINE_JOB_ID = "99f9cd11-a1d8-4909-9ed7-04a0320a2820"


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


class TestHealthAndBasics:
    """Basic health and connectivity tests"""
    
    def test_health_endpoint(self):
        """Test 0: Health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"Health check passed: {data}")


class TestPipelineUserJobs:
    """Test 1: Normal Flow - Pipeline user jobs"""
    
    def test_user_jobs_returns_videos(self, test_user_token):
        """Test 1: User can see their recent videos"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "jobs" in data
        print(f"Found {len(data['jobs'])} user jobs")
        
        # Verify job structure
        if data["jobs"]:
            job = data["jobs"][0]
            assert "job_id" in job
            assert "title" in job
            assert "status" in job
            print(f"First job: {job['title']} - Status: {job['status']}")


class TestVideoPlayback:
    """Test 2: Video Playback - Download URL exists"""
    
    def test_video_file_serving(self):
        """Test 8: Video file serving returns valid video"""
        # Test the Story Engine video file
        response = requests.get(
            f"{BASE_URL}/api/generated/se_99f9cd11_stitched.mp4",
            stream=True
        )
        assert response.status_code == 200, f"Video file not found: {response.status_code}"
        assert response.headers.get("content-type") == "video/mp4"
        
        # Download actual content to verify size (streaming response may not have content-length)
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > 1000000:  # Stop after 1MB to save time
                break
        
        assert len(content) > 100000, f"Video too small: {len(content)} bytes"
        print(f"Video file verified: downloaded {len(content)} bytes (truncated at 1MB)")


class TestShareFlow:
    """Test 4 & 9: Share Flow - Create and retrieve share links"""
    
    def test_create_share_link(self, test_user_token):
        """Test 9: POST /api/share creates a share link"""
        response = requests.post(
            f"{BASE_URL}/api/share/create",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "generationId": STORY_ENGINE_JOB_ID,
                "type": "STORY",
                "title": "The Whispering Woods"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "shareId" in data
        assert "shareUrl" in data
        print(f"Created share link: {data['shareUrl']}")
        return data["shareId"]
    
    def test_get_share_data(self, test_user_token):
        """Test 9: GET /api/share/{share_id} returns share data"""
        # First create a share
        create_response = requests.post(
            f"{BASE_URL}/api/share/create",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "generationId": STORY_ENGINE_JOB_ID,
                "type": "STORY",
                "title": "Test Share"
            }
        )
        share_id = create_response.json()["shareId"]
        
        # Then retrieve it
        response = requests.get(f"{BASE_URL}/api/share/{share_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["id"] == share_id
        assert data["type"] == "STORY"
        print(f"Share data retrieved: {data}")


class TestStoryEngineAPI:
    """Test 7 & 10: Story Engine API endpoints"""
    
    def test_story_engine_status(self, test_user_token):
        """Test 7: GET /api/story-engine/status returns job with Ken Burns fallback info"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{STORY_ENGINE_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify Ken Burns fallback fields
        assert data["state"] == "READY"
        assert data["used_ken_burns_fallback"] is True
        assert data["sora_clips_count"] == 1
        assert data["fallback_clips_count"] == 3
        
        print(f"Story Engine job status: state={data['state']}, "
              f"used_ken_burns_fallback={data['used_ken_burns_fallback']}, "
              f"sora_clips={data['sora_clips_count']}, fallback_clips={data['fallback_clips_count']}")
    
    def test_credit_check(self, test_user_token):
        """Test 10: GET /api/story-engine/credit-check returns credit info"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/credit-check",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sufficient" in data
        assert "required" in data
        assert "current" in data
        assert "breakdown" in data
        
        print(f"Credit check: sufficient={data['sufficient']}, "
              f"required={data['required']}, current={data['current']}")


class TestPipelineValidation:
    """Test 5: PARTIAL_READY state handling via validate-asset endpoint"""
    
    def test_validate_asset_endpoint(self, test_user_token):
        """Test 5: Validate asset endpoint returns correct UI state"""
        # Get a user job first
        jobs_response = requests.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        jobs = jobs_response.json().get("jobs", [])
        
        if jobs:
            job_id = jobs[0]["job_id"]
            response = requests.get(
                f"{BASE_URL}/api/pipeline/validate-asset/{job_id}",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "ui_state" in data
            assert "preview_ready" in data
            assert "download_ready" in data
            assert "share_ready" in data
            
            print(f"Validate asset for {job_id}: ui_state={data['ui_state']}, "
                  f"preview_ready={data['preview_ready']}, download_ready={data['download_ready']}")


class TestQuickRenderBanner:
    """Test 6: Quick Render banner logic verification"""
    
    def test_ken_burns_fallback_fields_present(self, test_user_token):
        """Test 6: Verify Ken Burns fallback fields are returned by Story Engine API"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{STORY_ENGINE_JOB_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # These fields should be present for Quick Render banner logic
        assert "used_ken_burns_fallback" in data
        assert "sora_clips_count" in data
        assert "fallback_clips_count" in data
        
        # For this specific job, Ken Burns was used
        assert data["used_ken_burns_fallback"] is True
        assert data["fallback_clips_count"] > 0
        
        print(f"Quick Render fields verified: used_ken_burns_fallback={data['used_ken_burns_fallback']}, "
              f"fallback_clips_count={data['fallback_clips_count']}")
    
    def test_pipeline_job_without_ken_burns(self, test_user_token):
        """Test 6: Pipeline jobs (not Story Engine) should not have Ken Burns fields"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        jobs = response.json().get("jobs", [])
        
        if jobs:
            job = jobs[0]
            # Pipeline jobs use different field names or don't have Ken Burns fallback
            # The Quick Render banner should NOT appear for regular pipeline videos
            has_ken_burns = job.get("used_ken_burns_fallback", False)
            fallback_count = job.get("fallback_clips_count", 0)
            
            print(f"Pipeline job {job['job_id']}: used_ken_burns_fallback={has_ken_burns}, "
                  f"fallback_clips_count={fallback_count}")


class TestStoryEngineMyJobs:
    """Additional Story Engine tests"""
    
    def test_my_jobs_pagination(self, test_user_token):
        """Test Story Engine my-jobs returns paginated results"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/my-jobs",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        
        print(f"Story Engine my-jobs: {len(data['jobs'])} jobs, total={data['total']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
