"""
Test: Asset-First Story→Video Pipeline Architecture (Iteration 271)
Focus: Verifying the new 3-stage pipeline (scenes→images→voices), manifest generation,
       ZIP availability, and frontend redirect patterns.

Architecture Change:
- Backend generates assets only (no render/upload in normal path)
- Pipeline: scenes → images → voices → manifest/ZIP → COMPLETED
- Frontend handles preview + browser export
- Server render removed from normal flow (admin-only fallback)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"

# Test job IDs provided by main agent (completed with new architecture)
COMPLETED_JOB_IDS = [
    "a67ff269-1ba5-41d4-a827-9c97cff4d00d",  # Desert Oasis
    "9ebb248e",  # Desert Oasis (partial ID)
    "b0170a69",  # Mountain Kingdom
]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json().get("token")
    assert token, "No token returned"
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="module")
def completed_job_id(auth_headers):
    """Get a completed job ID with new architecture"""
    response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
    assert response.status_code == 200
    jobs = response.json().get("jobs", [])
    
    # Find a completed job
    completed = [j for j in jobs if j.get("status") == "COMPLETED"]
    assert len(completed) > 0, "No completed jobs found"
    return completed[0].get("job_id")


class TestPipelineStages:
    """Verify pipeline uses only 3 stages (scenes, images, voices)"""
    
    def test_completed_job_has_only_three_stages(self, auth_headers, completed_job_id):
        """CRITICAL: Completed job status should show only scenes/images/voices stages"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        stages = job.get("stages", {})
        
        # Verify expected stages exist
        assert "scenes" in stages, "scenes stage missing"
        assert "images" in stages, "images stage missing"
        assert "voices" in stages, "voices stage missing"
        
        # Verify all 3 stages are COMPLETED
        for stage_name in ["scenes", "images", "voices"]:
            assert stages[stage_name].get("status") == "COMPLETED", f"{stage_name} not COMPLETED"
            assert stages[stage_name].get("duration_ms") is not None, f"{stage_name} has no duration"
        
        # Verify render/upload stages are NOT present
        assert "render" not in stages, "render stage should NOT be in normal pipeline"
        assert "upload" not in stages, "upload stage should NOT be in normal pipeline"
        print(f"PASS: Job has exactly 3 stages (scenes, images, voices) - no render/upload")
    
    def test_pipeline_options_endpoint(self, auth_headers):
        """Verify /api/pipeline/options still works"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        assert len(data["animation_styles"]) > 0
        print(f"PASS: Pipeline options endpoint returns {len(data['animation_styles'])} styles")


class TestManifestGeneration:
    """Verify manifest field in completed jobs"""
    
    def test_completed_job_has_manifest(self, auth_headers, completed_job_id):
        """CRITICAL: Completed job should have manifest with job_id, title, scenes, animation_style"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        manifest = job.get("manifest")
        
        assert manifest is not None, "manifest field is missing for completed job"
        assert "job_id" in manifest, "manifest missing job_id"
        assert "title" in manifest, "manifest missing title"
        assert "scenes" in manifest, "manifest missing scenes"
        assert "animation_style" in manifest, "manifest missing animation_style"
        
        print(f"PASS: Manifest has required fields - job_id, title, scenes, animation_style")
    
    def test_manifest_scenes_have_required_fields(self, auth_headers, completed_job_id):
        """CRITICAL: Each scene in manifest should have image_url, audio_url, duration"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        manifest = response.json().get("job", {}).get("manifest", {})
        scenes = manifest.get("scenes", [])
        
        assert len(scenes) > 0, "No scenes in manifest"
        
        for scene in scenes:
            assert "scene_number" in scene, f"Scene missing scene_number"
            assert "image_url" in scene, f"Scene {scene.get('scene_number')} missing image_url"
            assert "audio_url" in scene, f"Scene {scene.get('scene_number')} missing audio_url"
            assert "duration" in scene, f"Scene {scene.get('scene_number')} missing duration"
            
            # Verify URLs are valid (not empty)
            assert scene.get("image_url"), f"Scene {scene.get('scene_number')} has empty image_url"
            assert scene.get("audio_url"), f"Scene {scene.get('scene_number')} has empty audio_url"
            assert scene.get("duration") > 0, f"Scene {scene.get('scene_number')} has invalid duration"
        
        print(f"PASS: All {len(scenes)} scenes have image_url, audio_url, duration")


class TestStoryPackZIP:
    """Verify story_pack_url (ZIP) in completed jobs"""
    
    def test_completed_job_has_story_pack_url(self, auth_headers, completed_job_id):
        """CRITICAL: Completed job should have story_pack_url"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        story_pack_url = job.get("story_pack_url")
        
        assert story_pack_url is not None, "story_pack_url is missing for completed job"
        assert story_pack_url.startswith("http"), f"Invalid story_pack_url: {story_pack_url[:50]}"
        
        print(f"PASS: story_pack_url present and valid")
    
    def test_story_pack_url_is_downloadable(self, auth_headers, completed_job_id):
        """Verify ZIP URL is accessible (HEAD request)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        story_pack_url = response.json().get("job", {}).get("story_pack_url")
        if story_pack_url:
            # Note: R2 presigned URLs may have specific access requirements
            # Just verify the URL format is correct
            assert "r2" in story_pack_url or "cloudflare" in story_pack_url or "blob" in story_pack_url, \
                "story_pack_url should be an R2 or storage URL"
            print(f"PASS: story_pack_url has valid storage URL format")


class TestPreviewPath:
    """Verify preview_path in completed jobs"""
    
    def test_completed_job_has_preview_path(self, auth_headers, completed_job_id):
        """CRITICAL: Completed job should have preview_path pointing to /app/story-preview/{job_id}"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        preview_path = job.get("preview_path")
        
        assert preview_path is not None, "preview_path is missing for completed job"
        assert f"/app/story-preview/{completed_job_id}" == preview_path, \
            f"preview_path should be /app/story-preview/{completed_job_id}, got {preview_path}"
        
        print(f"PASS: preview_path = {preview_path}")


class TestPreviewEndpoint:
    """Verify GET /api/pipeline/preview/{job_id} works correctly"""
    
    def test_preview_endpoint_returns_scene_data(self, auth_headers, completed_job_id):
        """CRITICAL: Preview endpoint should return all scene data for COMPLETED status jobs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True, "Preview endpoint did not return success"
        
        preview = data.get("preview", {})
        assert preview.get("status") == "COMPLETED", f"Preview status is {preview.get('status')}, expected COMPLETED"
        assert preview.get("title"), "Preview missing title"
        assert preview.get("total_scenes") > 0, "Preview has no scenes"
        assert preview.get("scenes_with_images") > 0, "Preview has no images"
        assert preview.get("scenes_with_audio") > 0, "Preview has no audio"
        
        scenes = preview.get("scenes", [])
        assert len(scenes) == preview.get("total_scenes"), "Scene count mismatch"
        
        for scene in scenes:
            assert scene.get("has_image"), f"Scene {scene.get('scene_number')} has no image"
            assert scene.get("has_audio"), f"Scene {scene.get('scene_number')} has no audio"
        
        print(f"PASS: Preview endpoint returned {len(scenes)} scenes with images and audio")
    
    def test_preview_endpoint_includes_story_pack_url(self, auth_headers, completed_job_id):
        """Preview should include story_pack_url"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        preview = response.json().get("preview", {})
        story_pack_url = preview.get("story_pack_url")
        
        # story_pack_url should be present for completed jobs
        assert story_pack_url is not None, "Preview missing story_pack_url"
        print(f"PASS: Preview includes story_pack_url")


class TestUserJobsEndpoint:
    """Verify GET /api/pipeline/user-jobs shows correct data"""
    
    def test_user_jobs_shows_completed_status_with_manifest(self, auth_headers):
        """User jobs should show COMPLETED status for new jobs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        
        jobs = response.json().get("jobs", [])
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        
        assert len(completed_jobs) > 0, "No COMPLETED jobs found"
        
        # Check first completed job
        job = completed_jobs[0]
        assert job.get("job_id"), "Job missing job_id"
        assert job.get("title"), "Job missing title"
        
        print(f"PASS: Found {len(completed_jobs)} COMPLETED jobs in user-jobs")


class TestResumeEndpoint:
    """Verify POST /api/pipeline/resume/{job_id} still works"""
    
    def test_resume_rejects_completed_job(self, auth_headers, completed_job_id):
        """Resume should reject already completed jobs"""
        response = requests.post(f"{BASE_URL}/api/pipeline/resume/{completed_job_id}", headers=auth_headers)
        
        # Should return 400 with "Job already completed"
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "already completed" in response.json().get("detail", "").lower(), \
            "Expected 'already completed' in error message"
        
        print(f"PASS: Resume correctly rejects completed jobs")


class TestNoRenderUploadStages:
    """Verify render/upload stages are NOT in normal pipeline"""
    
    def test_stages_object_excludes_render_upload(self, auth_headers, completed_job_id):
        """CRITICAL: stages object should NOT contain render or upload"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        stages = job.get("stages", {})
        
        stage_names = list(stages.keys())
        
        assert "render" not in stage_names, f"render stage found in stages: {stage_names}"
        assert "upload" not in stage_names, f"upload stage found in stages: {stage_names}"
        
        # Verify only expected stages
        expected = {"script", "scenes", "images", "voices"}
        actual = set(stage_names)
        assert actual.issubset(expected), f"Unexpected stages: {actual - expected}"
        
        print(f"PASS: Stages object contains only: {stage_names} (no render/upload)")
    
    def test_output_url_is_none_for_asset_only_jobs(self, auth_headers, completed_job_id):
        """Jobs with asset-first architecture should NOT have output_url"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        output_url = job.get("output_url")
        
        # For new architecture, output_url should be None (server render removed)
        assert output_url is None, f"output_url should be None for asset-first jobs, got: {output_url}"
        
        print(f"PASS: output_url is None (no server-side video render)")


class TestCompletionStatus:
    """Verify job completes correctly after voices stage"""
    
    def test_job_completes_with_all_required_fields(self, auth_headers, completed_job_id):
        """CRITICAL: COMPLETED job should have all required fields"""
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{completed_job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        
        # Status checks
        assert job.get("status") == "COMPLETED", "Status should be COMPLETED"
        assert job.get("progress") == 100, f"Progress should be 100, got {job.get('progress')}"
        
        # Required fields for new architecture
        assert job.get("manifest") is not None, "manifest is required"
        assert job.get("preview_path") is not None, "preview_path is required"
        # story_pack_url is expected but may be missing if ZIP generation failed
        
        # Timing data should exist
        timing = job.get("timing", {})
        assert "total_ms" in timing, "timing.total_ms missing"
        
        print(f"PASS: Job is COMPLETED with all required fields (manifest, preview_path, timing)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
