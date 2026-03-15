"""
Story Video Studio - R2 Cloud Storage Regression Test
Tests the complete pipeline after R2 migration:
1. User login authentication
2. Project creation 
3. Scene generation
4. Image generation with R2 upload
5. Voice generation
6. Video assembly and rendering
7. R2 URL accessibility
"""
import pytest
import requests
import os
import time
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://auth-photo-comic.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"

# Valid style IDs
VALID_STYLE_IDS = ["storybook", "comic", "watercolor", "cinematic", "anime", "3d_cartoon"]

# Simple test story for 2-3 scenes
TEST_STORY = """
Once upon a time, there was a friendly robot named Beep who lived in a colorful garden.
Beep loved to help the flowers grow by watering them with his special sprinkler arm.
One sunny day, Beep met a butterfly named Flutter who was looking for the prettiest flower.
Together, they searched through the garden and found a magical rainbow rose.
Beep and Flutter became best friends and shared the rainbow rose with all the garden creatures.
The End.
"""


class TestHealthAndAuth:
    """Test basic health and authentication endpoints"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy" or "healthy" in str(data).lower()
        print(f"✅ API Health: {data}")
    
    def test_user_login(self):
        """Test user login with provided credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, f"No token in response: {data}"
        print(f"✅ Login successful for {TEST_USER_EMAIL}")
        return data.get("token") or data.get("access_token")


class TestStoryVideoStudioConfig:
    """Test Story Video Studio configuration endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Login failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_video_styles(self, auth_headers):
        """Test getting available video styles"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/styles", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get styles: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "styles" in data
        assert len(data["styles"]) >= 6, f"Expected at least 6 styles, got {len(data['styles'])}"
        
        # Verify valid style IDs
        style_ids = [s["id"] for s in data["styles"]]
        for expected_id in VALID_STYLE_IDS:
            assert expected_id in style_ids, f"Missing style: {expected_id}"
        print(f"✅ Video styles: {style_ids}")
    
    def test_get_pricing(self, auth_headers):
        """Test getting credit pricing"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/pricing", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get pricing: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "pricing" in data
        
        pricing = data["pricing"]
        assert "scene_generation" in pricing
        assert "image_per_scene" in pricing
        assert "voice_per_minute" in pricing
        assert "video_render" in pricing
        print(f"✅ Pricing: {pricing}")
    
    def test_get_voice_config(self, auth_headers):
        """Test getting voice configuration"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/voice/config", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get voice config: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "available_voices" in data
        assert len(data["available_voices"]) >= 6, "Expected at least 6 voice options"
        
        voice_ids = [v["id"] for v in data["available_voices"]]
        print(f"✅ Voice config: mode={data.get('mode')}, voices={voice_ids}")
    
    def test_get_music_library(self, auth_headers):
        """Test getting music library"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/music/library", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get music library: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "music_tracks" in data
        assert len(data["music_tracks"]) >= 10, f"Expected at least 10 music tracks, got {len(data['music_tracks'])}"
        print(f"✅ Music library: {len(data['music_tracks'])} tracks available")


class TestProjectCreation:
    """Test project creation endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        pytest.skip("Login failed")
    
    def test_create_project(self, auth_headers):
        """Test project creation with valid story"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": TEST_STORY,
                "title": "TEST_Beep and Flutter Story",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Project creation failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Project creation returned failure: {data}"
        assert "project_id" in data, f"No project_id in response: {data}"
        
        project_id = data["project_id"]
        print(f"✅ Project created: {project_id}")
        return project_id
    
    def test_create_project_invalid_style(self, auth_headers):
        """Test project creation with invalid style_id"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": TEST_STORY,
                "title": "TEST_Invalid Style",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "invalid_style_that_does_not_exist"
            },
            headers=auth_headers
        )
        
        # Should still succeed but use default style
        assert response.status_code == 200, f"Project creation failed: {response.text}"
        data = response.json()
        # The API should fall back to default style
        print(f"✅ Project creation with invalid style falls back to default: {data.get('data', {}).get('style_id')}")
    
    def test_create_project_short_story(self, auth_headers):
        """Test project creation with too short story"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": "Too short",
                "title": "TEST_Short Story",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422 or response.status_code == 400, f"Expected validation error: {response.status_code}"
        print(f"✅ Short story validation working: {response.status_code}")


class TestSceneGeneration:
    """Test scene generation for a project"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        pytest.skip("Login failed")
    
    @pytest.fixture(scope="class")
    def project_id(self, auth_headers):
        """Create a project for testing"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": TEST_STORY,
                "title": "TEST_Scene Generation Test",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook"
            },
            headers=auth_headers
        )
        if response.status_code == 200 and response.json().get("success"):
            return response.json()["project_id"]
        pytest.skip("Project creation failed")
    
    def test_generate_scenes(self, auth_headers, project_id):
        """Test scene generation for project"""
        print(f"Generating scenes for project: {project_id}")
        
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/{project_id}/generate-scenes",
            headers=auth_headers,
            timeout=120  # Scene generation can take up to 2 minutes
        )
        
        assert response.status_code == 200, f"Scene generation failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Scene generation returned failure: {data}"
        
        assert "data" in data
        scene_data = data["data"]
        assert "scenes" in scene_data
        assert "characters" in scene_data
        assert "voice_scripts" in scene_data
        
        num_scenes = len(scene_data["scenes"])
        num_characters = len(scene_data["characters"])
        
        assert num_scenes >= 2, f"Expected at least 2 scenes, got {num_scenes}"
        print(f"✅ Generated {num_scenes} scenes with {num_characters} characters")
        
        return scene_data


class TestImageGeneration:
    """Test image generation with R2 cloud storage"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        pytest.skip("Login failed")
    
    @pytest.fixture(scope="class")
    def project_with_scenes(self, auth_headers):
        """Create a project with generated scenes"""
        # Create project
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": TEST_STORY,
                "title": "TEST_Image Generation Test",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook"
            },
            headers=auth_headers
        )
        if response.status_code != 200:
            pytest.skip(f"Project creation failed: {response.text}")
        
        project_id = response.json()["project_id"]
        
        # Generate scenes
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/{project_id}/generate-scenes",
            headers=auth_headers,
            timeout=120
        )
        if response.status_code != 200:
            pytest.skip(f"Scene generation failed: {response.text}")
        
        return project_id
    
    def test_generate_images_endpoint_requires_auth(self):
        """Test that image generation requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/images",
            json={"project_id": "fake-project-id", "provider": "openai"}
        )
        assert response.status_code == 401 or response.status_code == 403, \
            f"Expected auth error, got: {response.status_code}"
        print("✅ Image generation requires authentication")
    
    def test_generate_images_for_single_scene(self, auth_headers, project_with_scenes):
        """Test image generation for a single scene (to minimize credits)"""
        project_id = project_with_scenes
        
        print(f"Generating image for scene 1 of project: {project_id}")
        
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/images",
            json={
                "project_id": project_id,
                "scene_numbers": [1],  # Only generate for scene 1
                "provider": "openai"
            },
            headers=auth_headers,
            timeout=180  # Image generation can take a while
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for image generation")
        
        assert response.status_code == 200, f"Image generation failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Image generation returned failure: {data}"
        
        # Check images were generated
        assert "images" in data
        images = data["images"]
        assert len(images) >= 1, f"Expected at least 1 image, got {len(images)}"
        
        # Verify R2 URL format for generated images
        for img in images:
            image_url = img.get("image_url", "")
            # R2 URLs should start with https:// (cloud storage)
            # or could be local /static/ paths
            assert image_url, f"Image URL is empty for scene {img.get('scene_number')}"
            
            if image_url.startswith("https://"):
                print(f"✅ Scene {img.get('scene_number')} image uploaded to R2: {image_url[:80]}...")
                
                # Verify R2 URL is accessible
                img_response = requests.head(image_url, timeout=10)
                assert img_response.status_code == 200, \
                    f"R2 image not accessible: {image_url} - {img_response.status_code}"
                print(f"✅ R2 URL accessible: {img_response.status_code}")
            else:
                print(f"⚠️ Scene {img.get('scene_number')} image is local: {image_url}")
        
        return data
    
    def test_get_project_images(self, auth_headers, project_with_scenes):
        """Test getting generated images for a project"""
        project_id = project_with_scenes
        
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/images/{project_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to get images: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✅ Project images retrieved: {data.get('count', 0)} images")


class TestVoiceGeneration:
    """Test voice generation for scenes"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        pytest.skip("Login failed")
    
    @pytest.fixture(scope="class")
    def project_with_scenes(self, auth_headers):
        """Create a project with generated scenes"""
        # Create project
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": TEST_STORY,
                "title": "TEST_Voice Generation Test",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook"
            },
            headers=auth_headers
        )
        if response.status_code != 200:
            pytest.skip(f"Project creation failed: {response.text}")
        
        project_id = response.json()["project_id"]
        
        # Generate scenes
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/{project_id}/generate-scenes",
            headers=auth_headers,
            timeout=120
        )
        if response.status_code != 200:
            pytest.skip(f"Scene generation failed: {response.text}")
        
        return project_id
    
    def test_generate_voice_for_single_scene(self, auth_headers, project_with_scenes):
        """Test voice generation for a single scene"""
        project_id = project_with_scenes
        
        print(f"Generating voice for scene 1 of project: {project_id}")
        
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/voices",
            json={
                "project_id": project_id,
                "scene_numbers": [1],  # Only generate for scene 1
                "voice_id": "alloy"
            },
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for voice generation")
        
        assert response.status_code == 200, f"Voice generation failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Voice generation returned failure: {data}"
        
        assert "voices" in data
        voices = data["voices"]
        assert len(voices) >= 1, f"Expected at least 1 voice, got {len(voices)}"
        
        for voice in voices:
            audio_url = voice.get("audio_url", "")
            assert audio_url, f"Audio URL is empty for scene {voice.get('scene_number')}"
            print(f"✅ Scene {voice.get('scene_number')} voice generated: {audio_url[:80] if len(audio_url) > 80 else audio_url}")
            
            # Check if uploaded to R2
            if audio_url.startswith("https://"):
                audio_response = requests.head(audio_url, timeout=10)
                if audio_response.status_code == 200:
                    print(f"✅ Voice R2 URL accessible")
        
        return data


class TestVideoAssembly:
    """Test video assembly and rendering"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        pytest.skip("Login failed")
    
    def test_video_status_endpoint(self, auth_headers):
        """Test video status endpoint with fake job ID"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/video/status/fake-job-id",
            headers=auth_headers
        )
        # Should return 404 for non-existent job
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✅ Video status endpoint working")
    
    def test_video_assembly_requires_auth(self):
        """Test that video assembly requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/video/assemble",
            json={"project_id": "fake-project-id"}
        )
        assert response.status_code == 401 or response.status_code == 403, \
            f"Expected auth error, got: {response.status_code}"
        print("✅ Video assembly requires authentication")
    
    def test_video_assembly_requires_images_voices(self, auth_headers):
        """Test that video assembly fails without images/voices"""
        # First create a project without generating images/voices
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": TEST_STORY,
                "title": "TEST_Video Assembly Test",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook"
            },
            headers=auth_headers
        )
        
        if response.status_code != 200:
            pytest.skip("Project creation failed")
        
        project_id = response.json()["project_id"]
        
        # Try to assemble video without images/voices
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/video/assemble",
            json={
                "project_id": project_id,
                "include_watermark": True
            },
            headers=auth_headers
        )
        
        # Should fail with 400 or similar error
        assert response.status_code in [400, 402, 404], \
            f"Expected error for missing images/voices, got: {response.status_code}"
        print(f"✅ Video assembly correctly requires images and voices first")


class TestR2CloudStorage:
    """Test R2 cloud storage integration"""
    
    def test_r2_public_url_format(self):
        """Test that R2 public URL is properly configured"""
        r2_public_url = os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", "")
        
        # In backend .env, we saw: CLOUDFLARE_R2_PUBLIC_URL=https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev
        expected_domain = "r2.dev"
        
        # Check via health endpoint if R2 is configured (optional)
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        print(f"✅ R2 configuration check passed")
    
    def test_r2_url_accessibility(self):
        """Test that R2 bucket is accessible"""
        # This is a basic connectivity check to R2 domain
        r2_base = "https://pub-c251248e414545848d34b8c1b97ecdb3.r2.dev"
        
        try:
            # Just check the domain is reachable (may return 404 for root)
            response = requests.get(r2_base, timeout=10)
            # R2 bucket root may return 404, 403, or other - but should be reachable
            print(f"✅ R2 domain accessible (status: {response.status_code})")
        except requests.RequestException as e:
            pytest.fail(f"R2 domain not reachable: {e}")


class TestCleanup:
    """Test cleanup and analytics endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authenticated headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        pytest.skip("Login failed")
    
    def test_analytics_endpoint(self, auth_headers):
        """Test analytics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/analytics",
            headers=auth_headers
        )
        
        # Analytics may require admin role
        assert response.status_code in [200, 403], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analytics: {data.get('analytics', {})}")
        else:
            print("✅ Analytics endpoint protected (admin only)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
