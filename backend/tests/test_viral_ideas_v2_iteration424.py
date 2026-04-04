"""
Viral Ideas V2 Phase 2 Tests - Iteration 424
Tests: Audio/Video workers, Feedback flow, Repair endpoint, Full pipeline
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Existing completed job for testing
EXISTING_JOB_ID = "ce680be0-51c6-4560-810e-25a058dfcd8d"

# Valid feedback signals
VALID_SIGNALS = ["useful", "not_useful", "regenerate_angle", "more_aggressive_hook", "safer_hook", "better_captions"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestDailyFeed:
    """Test daily feed endpoint."""
    
    def test_daily_feed_returns_ideas(self):
        """GET /api/viral-ideas/daily-feed returns ideas and niches."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/daily-feed")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ideas" in data
        assert "niches" in data
        assert len(data["ideas"]) > 0
        assert len(data["niches"]) > 0
    
    def test_daily_feed_filter_by_niche(self):
        """GET /api/viral-ideas/daily-feed?niche=Tech filters by niche."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/daily-feed?niche=Tech")
        assert response.status_code == 200
        data = response.json()
        # All ideas should be Tech niche
        for idea in data["ideas"]:
            assert idea["niche"] == "Tech"


class TestExistingCompletedJob:
    """Test existing completed job with all 7 assets."""
    
    def test_job_status_completed(self, auth_headers):
        """GET /api/viral-ideas/jobs/{job_id} returns completed status with 7 tasks."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify job status
        assert data["status"] == "completed"
        assert data["progress"]["percentage"] == 100
        assert data["progress"]["current_phase"] == "ready"
        
        # Verify all 7 tasks exist
        assert len(data["tasks"]) == 7
        task_types = {t["task_type"] for t in data["tasks"]}
        expected_types = {"hooks", "script", "captions", "thumbnail", "audio", "video", "packaging"}
        assert task_types == expected_types
        
        # Verify all tasks completed
        for task in data["tasks"]:
            assert task["status"] == "completed"
    
    def test_job_assets_include_audio_video(self, auth_headers):
        """GET /api/viral-ideas/jobs/{job_id}/assets includes voiceover and video."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/assets",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        asset_types = {a["asset_type"] for a in data["assets"]}
        
        # Verify all asset types present
        assert "hooks" in asset_types
        assert "script" in asset_types
        assert "captions" in asset_types
        assert "thumbnail" in asset_types
        assert "voiceover" in asset_types
        assert "video" in asset_types
        assert "zip_bundle" in asset_types
        
        # Verify voiceover has file_url
        voiceover = next(a for a in data["assets"] if a["asset_type"] == "voiceover")
        assert voiceover["file_url"] is not None
        assert "/api/static/generated/viral_audio/" in voiceover["file_url"]
        assert voiceover["mime_type"] == "audio/mpeg"
        
        # Verify video has file_url
        video = next(a for a in data["assets"] if a["asset_type"] == "video")
        assert video["file_url"] is not None
        assert "/api/static/generated/viral_videos/" in video["file_url"]
        assert video["mime_type"] == "video/mp4"


class TestStaticFileAccess:
    """Test static file accessibility for audio and video."""
    
    def test_audio_file_accessible(self, auth_headers):
        """Audio MP3 file is accessible at /api/static/generated/viral_audio/."""
        # Get asset URL first
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/assets",
            headers=auth_headers
        )
        data = response.json()
        voiceover = next(a for a in data["assets"] if a["asset_type"] == "voiceover")
        
        # Test file accessibility
        audio_url = f"{BASE_URL}{voiceover['file_url']}"
        audio_response = requests.head(audio_url)
        assert audio_response.status_code == 200
        assert "audio/mpeg" in audio_response.headers.get("content-type", "")
        assert int(audio_response.headers.get("content-length", 0)) > 0
    
    def test_video_file_accessible(self, auth_headers):
        """Video MP4 file is accessible at /api/static/generated/viral_videos/."""
        # Get asset URL first
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/assets",
            headers=auth_headers
        )
        data = response.json()
        video = next(a for a in data["assets"] if a["asset_type"] == "video")
        
        # Test file accessibility
        video_url = f"{BASE_URL}{video['file_url']}"
        video_response = requests.head(video_url)
        assert video_response.status_code == 200
        assert "video/mp4" in video_response.headers.get("content-type", "")
        assert int(video_response.headers.get("content-length", 0)) > 0


class TestFeedbackFlow:
    """Test feedback submission and retrieval."""
    
    def test_feedback_valid_signal_useful(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/feedback accepts 'useful' signal."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/feedback",
            headers=auth_headers,
            json={"signal": "useful", "asset_type": "script"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Feedback recorded"
    
    def test_feedback_valid_signal_not_useful(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/feedback accepts 'not_useful' signal."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/feedback",
            headers=auth_headers,
            json={"signal": "not_useful", "asset_type": "captions"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_feedback_valid_signal_regenerate_angle(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/feedback accepts 'regenerate_angle' signal."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/feedback",
            headers=auth_headers,
            json={"signal": "regenerate_angle"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_feedback_valid_signal_more_aggressive_hook(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/feedback accepts 'more_aggressive_hook' signal."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/feedback",
            headers=auth_headers,
            json={"signal": "more_aggressive_hook", "asset_type": "hooks"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_feedback_valid_signal_safer_hook(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/feedback accepts 'safer_hook' signal."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/feedback",
            headers=auth_headers,
            json={"signal": "safer_hook", "asset_type": "hooks"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_feedback_valid_signal_better_captions(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/feedback accepts 'better_captions' signal."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/feedback",
            headers=auth_headers,
            json={"signal": "better_captions", "asset_type": "captions"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_feedback_invalid_signal_rejected(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/feedback rejects invalid signals."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/feedback",
            headers=auth_headers,
            json={"signal": "invalid_signal_xyz"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid signal" in data["detail"]
    
    def test_feedback_summary_returns_aggregated_data(self, auth_headers):
        """GET /api/viral-ideas/feedback/summary returns aggregated feedback."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/feedback/summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        # Should have at least some feedback from our tests
        assert isinstance(data["summary"], list)


class TestRepairEndpoint:
    """Test repair endpoint."""
    
    def test_repair_endpoint_works(self, auth_headers):
        """POST /api/viral-ideas/jobs/{job_id}/repair initiates repair."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/repair",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Repair initiated" in data["message"]
    
    def test_repair_nonexistent_job_returns_404(self, auth_headers):
        """POST /api/viral-ideas/jobs/{invalid_id}/repair returns 404."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/nonexistent-job-id-12345/repair",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestMyJobs:
    """Test my-jobs endpoint."""
    
    def test_my_jobs_returns_user_jobs(self, auth_headers):
        """GET /api/viral-ideas/my-jobs returns user's jobs."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/my-jobs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        # Should include our existing job
        job_ids = [j["job_id"] for j in data["jobs"]]
        assert EXISTING_JOB_ID in job_ids


class TestGenerateBundleEndpoint:
    """Test generate-bundle endpoint (creates new job)."""
    
    def test_generate_bundle_creates_job_with_7_tasks(self, auth_headers):
        """POST /api/viral-ideas/generate-bundle creates job with 7 tasks."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/generate-bundle",
            headers=auth_headers,
            json={"idea": "TEST: 5 AI tools that will replace your job in 2026", "niche": "Tech"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "content pack is being created" in data["message"].lower()
        
        job_id = data["job_id"]
        
        # Wait a moment for orchestrator to create tasks
        time.sleep(2)
        
        # Verify job has 7 tasks
        job_response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{job_id}",
            headers=auth_headers
        )
        assert job_response.status_code == 200
        job_data = job_response.json()
        
        # Should have 7 tasks created
        assert len(job_data["tasks"]) == 7
        task_types = {t["task_type"] for t in job_data["tasks"]}
        expected_types = {"hooks", "script", "captions", "thumbnail", "audio", "video", "packaging"}
        assert task_types == expected_types


class TestAccessControl:
    """Test access control for jobs."""
    
    def test_job_access_denied_for_other_user(self, auth_headers):
        """GET /api/viral-ideas/jobs/{job_id} returns 403 for other user's job."""
        # Create a different user's token (admin)
        admin_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
        )
        if admin_response.status_code != 200:
            pytest.skip("Admin login failed - skipping access control test")
        
        admin_token = admin_response.json()["token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Try to access test user's job
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}",
            headers=admin_headers
        )
        # Should be 403 (access denied) since job belongs to test user
        assert response.status_code == 403
    
    def test_feedback_requires_auth(self):
        """POST /api/viral-ideas/jobs/{job_id}/feedback requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/feedback",
            json={"signal": "useful"}
        )
        assert response.status_code in [401, 403]


class TestZipBundle:
    """Test ZIP bundle accessibility."""
    
    def test_zip_bundle_accessible(self, auth_headers):
        """ZIP bundle file is accessible."""
        response = requests.get(
            f"{BASE_URL}/api/viral-ideas/jobs/{EXISTING_JOB_ID}/assets",
            headers=auth_headers
        )
        data = response.json()
        zip_bundle = next((a for a in data["assets"] if a["asset_type"] == "zip_bundle"), None)
        
        if zip_bundle and zip_bundle.get("file_url"):
            zip_url = f"{BASE_URL}{zip_bundle['file_url']}"
            zip_response = requests.head(zip_url)
            assert zip_response.status_code == 200
            assert "application/zip" in zip_response.headers.get("content-type", "") or \
                   "application/octet-stream" in zip_response.headers.get("content-type", "")
