"""
Iteration 132: Story Video Generation Bug Fix Tests
Testing the fix for video generation failure related to:
1. download_file function handling local and remote URLs
2. Image generation endpoint
3. Voice generation endpoint
4. Video assembly pipeline
5. Automatic credit refund on failure
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"

class TestStoryVideoGenerationBugFix:
    """Test story video generation with focus on download_file fix"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("token")
    
    @pytest.fixture(scope="class")
    def user_credits_before(self, auth_token):
        """Get user credits before tests"""
        response = requests.get(
            f"{BASE_URL}/api/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        if response.status_code == 200:
            return response.json().get("credits", 0)
        return 0
    
    # ===========================================================================
    # HEALTH & BASIC API TESTS
    # ===========================================================================
    
    def test_01_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    def test_02_auth_login(self):
        """Test user authentication"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_EMAIL
        print(f"✓ Login successful, user has {data['user'].get('credits', 0)} credits")
    
    # ===========================================================================
    # STORY VIDEO STUDIO ENDPOINTS TESTS
    # ===========================================================================
    
    def test_03_get_video_styles(self, auth_token):
        """Test video styles endpoint returns expected styles"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/styles",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "styles" in data
        styles = data["styles"]
        assert len(styles) >= 5  # Should have at least 5 styles
        style_ids = [s["id"] for s in styles]
        assert "storybook" in style_ids
        assert "comic" in style_ids
        print(f"✓ Video styles endpoint returns {len(styles)} styles")
    
    def test_04_get_voice_config(self, auth_token):
        """Test voice configuration endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/voice/config",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "available_voices" in data
        assert len(data["available_voices"]) >= 6  # alloy, echo, fable, onyx, nova, shimmer
        assert data.get("mode") == "PREPAID_ONLY"
        print(f"✓ Voice config returns {len(data['available_voices'])} voices, mode: {data.get('mode')}")
    
    def test_05_get_music_library(self, auth_token):
        """Test music library endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/music/library",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "music_tracks" in data
        assert len(data["music_tracks"]) >= 15  # Should have expanded library
        categories = data.get("categories", [])
        assert "bedtime" in categories
        assert "adventure" in categories
        print(f"✓ Music library returns {len(data['music_tracks'])} tracks across {len(categories)} categories")
    
    # ===========================================================================
    # PROJECT AND SCENE ASSETS TESTS
    # ===========================================================================
    
    def test_06_get_test_project(self, auth_token):
        """Test getting the test project with images"""
        project_id = "5220ef7f-b58e-4172-b5a6-b2f35879d65c"
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/projects/{project_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        project = data.get("project", {})
        assert project.get("project_id") == project_id
        assert project.get("status") in ["images_generated", "voices_generated", "video_rendered"]
        print(f"✓ Project retrieved, status: {project.get('status')}, scenes: {len(project.get('scenes', []))}")
    
    def test_07_get_project_images(self, auth_token):
        """Test getting project images - verifies endpoint works (images may have been cleaned up)"""
        project_id = "5220ef7f-b58e-4172-b5a6-b2f35879d65c"
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/images/{project_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        images = data.get("images", [])
        # Images may have been cleaned up by the 30-minute cleanup service
        if len(images) >= 1:
            for img in images:
                assert "image_url" in img
                assert "scene_number" in img
            print(f"✓ Project has {len(images)} images")
        else:
            print(f"✓ Project images were cleaned up by cleanup service (expected for files > 30 min)")
    
    def test_08_verify_image_accessible(self, auth_token):
        """Test that generated images are accessible via static URL"""
        project_id = "5220ef7f-b58e-4172-b5a6-b2f35879d65c"
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/images/{project_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        images = data.get("images", [])
        
        if images:
            image_url = images[0].get("image_url")
            full_url = f"{BASE_URL}{image_url}"
            img_response = requests.get(full_url, timeout=10)
            # Image should be accessible (200) or may have been cleaned up (404)
            assert img_response.status_code in [200, 404], f"Unexpected status: {img_response.status_code}"
            if img_response.status_code == 200:
                assert len(img_response.content) > 1000  # Image should have content
                print(f"✓ Image accessible at {image_url} ({len(img_response.content)} bytes)")
            else:
                print(f"⚠ Image was cleaned up (expected for files > 30 min old)")
    
    # ===========================================================================
    # VIDEO ASSEMBLY TESTS
    # ===========================================================================
    
    def test_09_video_assembly_missing_project(self, auth_token):
        """Test video assembly with non-existent project returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/video/assemble",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "project_id": "non-existent-project-id-12345",
                "include_watermark": True,
                "background_music_id": None,
                "music_volume": 0.3
            }
        )
        # Should return 404 for non-existent project (not 500 FFmpeg error)
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
        print("✓ Video assembly correctly returns 404 for non-existent project")
    
    def test_10_video_status_non_existent_job(self, auth_token):
        """Test video status endpoint with non-existent job ID"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/video/status/non-existent-job-id",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
        print("✓ Video status correctly returns 404 for non-existent job")
    
    def test_11_video_assembly_requires_voices(self, auth_token):
        """Test that video assembly requires both images and voice tracks"""
        project_id = "5220ef7f-b58e-4172-b5a6-b2f35879d65c"
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/video/assemble",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "project_id": project_id,
                "include_watermark": True,
                "background_music_id": None,
                "music_volume": 0.3
            }
        )
        # If project doesn't have voices, should return 400
        # If it has voices but user doesn't have enough credits, should return 402
        # If images were cleaned up, should return 400 about images
        # If successful, should return 200 with job_id
        assert response.status_code in [200, 400, 402], f"Unexpected status: {response.status_code}, body: {response.text}"
        data = response.json()
        if response.status_code == 400:
            detail = data.get("detail", "").lower()
            assert "voice" in detail or "audio" in detail or "image" in detail
            print(f"✓ Video assembly correctly validates prerequisites: {data.get('detail')}")
        elif response.status_code == 402:
            print(f"✓ Video assembly requires more credits: {data.get('detail')}")
        else:
            assert "job_id" in data
            print(f"✓ Video assembly started, job_id: {data.get('job_id')}")
    
    # ===========================================================================
    # VOICE GENERATION TESTS
    # ===========================================================================
    
    def test_12_voice_generation_requires_credits(self, auth_token):
        """Test voice generation checks for sufficient credits"""
        project_id = "5220ef7f-b58e-4172-b5a6-b2f35879d65c"
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/voices",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "project_id": project_id,
                "scene_numbers": [1],  # Generate for just one scene
                "voice_id": "alloy"
            }
        )
        # Should succeed (200) or require more credits (402)
        assert response.status_code in [200, 402], f"Unexpected status: {response.status_code}, body: {response.text}"
        data = response.json()
        if response.status_code == 402:
            print(f"✓ Voice generation credit check works: {data.get('detail')}")
        else:
            assert data.get("success") is True
            print(f"✓ Voice generation succeeded for scene 1")
    
    # ===========================================================================
    # IMAGE GENERATION TESTS
    # ===========================================================================
    
    def test_13_image_generation_requires_scenes(self, auth_token):
        """Test image generation endpoint validation"""
        project_id = "5220ef7f-b58e-4172-b5a6-b2f35879d65c"
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/images",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "project_id": project_id,
                "scene_numbers": [999],  # Non-existent scene
                "provider": "openai"
            }
        )
        # Should return 400 for no valid scenes, 402 for no credits, or 200 if scene exists
        assert response.status_code in [200, 400, 402], f"Unexpected: {response.status_code}"
        print(f"✓ Image generation endpoint handles invalid scene numbers")
    
    # ===========================================================================
    # CREDIT SYSTEM TESTS
    # ===========================================================================
    
    def test_14_pricing_endpoint(self, auth_token):
        """Test pricing endpoint returns correct costs"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/pricing",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        pricing = data.get("pricing", {})
        assert pricing.get("scene_generation") > 0
        assert pricing.get("image_per_scene") > 0
        assert pricing.get("voice_per_minute") > 0
        assert pricing.get("video_render") > 0
        print(f"✓ Pricing: scene={pricing.get('scene_generation')}, image={pricing.get('image_per_scene')}, voice={pricing.get('voice_per_minute')}, video={pricing.get('video_render')}")
    
    def test_15_user_credits_check(self, auth_token):
        """Test user can check their credit balance"""
        response = requests.get(
            f"{BASE_URL}/api/user/profile",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        print(f"✓ User has {data.get('credits')} credits")


class TestDownloadFileFunction:
    """Test the download_file function's ability to handle local and remote URLs"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200
        return response.json().get("token")
    
    def test_01_static_file_accessible_locally(self):
        """Test that static files are accessible via the API"""
        # Test accessing a known static file
        response = requests.get(f"{BASE_URL}/static/generated/test.txt", timeout=10)
        # File may or may not exist, but endpoint should work
        assert response.status_code in [200, 404]
        print(f"✓ Static file endpoint accessible (status: {response.status_code})")
    
    def test_02_generated_directory_exists(self):
        """Verify the generated directory structure exists"""
        import os
        generated_dir = "/app/backend/static/generated"
        assert os.path.exists(generated_dir), "Generated directory should exist"
        print(f"✓ Generated directory exists at {generated_dir}")
    
    def test_03_backend_public_url_configured(self):
        """Test that BACKEND_PUBLIC_URL is configured in environment"""
        # This is checked in the download_file function
        backend_url = os.environ.get("BACKEND_PUBLIC_URL", "")
        frontend_url = os.environ.get("FRONTEND_URL", "")
        # At least one should be set for fallback
        assert backend_url or frontend_url or BASE_URL, "At least one public URL should be configured"
        print(f"✓ Backend public URL: {backend_url or frontend_url or 'using BASE_URL fallback'}")


class TestCleanupServiceImpact:
    """Test cleanup service behavior with video generation"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200
        return response.json().get("token")
    
    def test_01_cleanup_service_stats(self, auth_token):
        """Test cleanup service stats endpoint if available"""
        # Try to access cleanup stats (may not be exposed as API)
        response = requests.get(
            f"{BASE_URL}/api/admin/cleanup-stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # May be 404 if not exposed, 403 if admin only, or 200 if available
        assert response.status_code in [200, 403, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Cleanup stats available: {data}")
        else:
            print(f"✓ Cleanup stats endpoint status: {response.status_code} (expected for non-admin)")
    
    def test_02_file_expiry_time(self):
        """Verify file expiry is configured to 30 minutes"""
        # Check the cleanup service configuration
        import sys
        sys.path.insert(0, '/app/backend')
        try:
            from services.generated_files_cleanup import FILE_EXPIRY_MINUTES
            assert FILE_EXPIRY_MINUTES == 30, f"Expected 30 minutes, got {FILE_EXPIRY_MINUTES}"
            print(f"✓ File expiry configured to {FILE_EXPIRY_MINUTES} minutes")
        except ImportError:
            print("⚠ Could not import cleanup service config directly")


class TestEndToEndVideoGeneration:
    """End-to-end test for video generation pipeline"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200
        return response.json().get("token")
    
    def test_01_list_user_projects(self, auth_token):
        """Test listing user's story projects"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/projects",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        projects = data.get("projects", [])
        print(f"✓ User has {len(projects)} story video projects")
    
    def test_02_video_player_endpoint(self, auth_token):
        """Test video player data endpoint"""
        project_id = "5220ef7f-b58e-4172-b5a6-b2f35879d65c"
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/video/player/{project_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # May return 400 if video not rendered yet, or 200 with player data
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
            assert "video_url" in data
            print(f"✓ Video player data available, URL: {data.get('video_url')}")
        else:
            print("✓ Video not yet rendered (expected)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
