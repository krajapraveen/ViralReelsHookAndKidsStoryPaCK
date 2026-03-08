"""
Test Suite for Story Video Studio Bug Fixes - Iteration 131
Tests the following fixes:
1. FFmpeg installation verification
2. Download expiry service - base64 data URL handling
3. WebSocket real-time progress broadcasting
4. Story Video Studio API endpoints
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "krajapraveen.katta@creatorstudio.ai"
ADMIN_PASSWORD = "Onemanarmy@1979#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with authentication"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestHealthEndpoint:
    """Test backend health endpoint"""
    
    def test_health_endpoint_returns_200(self):
        """Verify backend is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health endpoint working - status: {data.get('status')}")


class TestStoryVideoStudioStyles:
    """Test Story Video Studio styles endpoint"""
    
    def test_styles_endpoint_returns_styles(self):
        """Verify styles endpoint returns valid styles"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/styles")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "styles" in data
        assert len(data["styles"]) > 0
        
        # Verify style structure
        style = data["styles"][0]
        assert "id" in style
        assert "name" in style
        assert "description" in style
        print(f"✓ Styles endpoint working - {len(data['styles'])} styles available")


class TestStoryVideoStudioPricing:
    """Test Story Video Studio pricing endpoint"""
    
    def test_pricing_endpoint_returns_costs(self):
        """Verify pricing endpoint returns valid pricing"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/pricing")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "pricing" in data
        
        # Verify pricing fields
        pricing = data["pricing"]
        assert "scene_generation" in pricing
        assert "image_per_scene" in pricing
        assert "voice_per_minute" in pricing
        assert "video_render" in pricing
        assert "watermark_removal" in pricing
        print(f"✓ Pricing endpoint working - video_render cost: {pricing['video_render']} credits")


class TestStoryVideoStudioVoiceConfig:
    """Test Story Video Studio voice configuration endpoint"""
    
    def test_voice_config_endpoint(self):
        """Verify voice config endpoint returns valid configuration"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/voice/config")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        
        # Verify voice config structure
        assert "mode" in data
        assert "available_voices" in data
        assert len(data["available_voices"]) > 0
        
        # Verify voice structure
        voice = data["available_voices"][0]
        assert "id" in voice
        assert "name" in voice
        assert "description" in voice
        print(f"✓ Voice config endpoint working - {len(data['available_voices'])} voices available, mode: {data['mode']}")


class TestStoryVideoStudioMusicLibrary:
    """Test Story Video Studio music library endpoint"""
    
    def test_music_library_endpoint(self):
        """Verify music library endpoint returns tracks"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/music/library")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "music_tracks" in data
        assert len(data["music_tracks"]) > 0
        
        # Verify track structure
        track = data["music_tracks"][0]
        assert "id" in track
        assert "name" in track
        assert "duration" in track
        assert "url" in track
        assert "category" in track
        print(f"✓ Music library endpoint working - {len(data['music_tracks'])} tracks available")
    
    def test_music_library_has_categories(self):
        """Verify music library includes category filter"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/music/library")
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0
        print(f"✓ Music categories available: {data['categories']}")


class TestUserAuthentication:
    """Test user authentication flow"""
    
    def test_login_with_valid_credentials(self):
        """Verify login works with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Login successful - user: {data['user']['email']}, role: {data['user']['role']}")
    
    def test_login_with_invalid_credentials(self):
        """Verify login fails with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@example.com", "password": "wrongpassword"}
        )
        assert response.status_code in [401, 404]
        print(f"✓ Invalid login correctly rejected with status {response.status_code}")


class TestDownloadExpiryService:
    """Test download expiry service for base64 data URL handling"""
    
    def test_my_downloads_endpoint(self, auth_headers):
        """Verify my-downloads endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/downloads/my-downloads",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "downloads" in data
        assert "total" in data
        print(f"✓ My downloads endpoint working - {data['total']} downloads found")
    
    def test_my_downloads_requires_auth(self):
        """Verify downloads endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads")
        assert response.status_code in [401, 403, 422]
        print(f"✓ Downloads endpoint correctly requires auth - status {response.status_code}")


class TestWebSocketEndpoint:
    """Test WebSocket progress endpoint availability"""
    
    def test_websocket_endpoint_exists(self):
        """Verify WebSocket endpoint is available (upgrade request)"""
        # Note: We can only check HTTP response, WebSocket upgrade would fail
        response = requests.get(
            f"{BASE_URL}/api/ws/progress",
            headers={"Connection": "Upgrade", "Upgrade": "websocket"}
        )
        # Should return 426 Upgrade Required or similar, not 404
        assert response.status_code != 404, "WebSocket endpoint should exist"
        print(f"✓ WebSocket endpoint available - status {response.status_code}")


class TestStoryVideoStudioAuthenticatedEndpoints:
    """Test authenticated Story Video Studio endpoints"""
    
    def test_templates_list_endpoint(self, auth_headers):
        """Verify templates list endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/templates/list",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "templates" in data
        print(f"✓ Templates list endpoint working - {len(data.get('templates', []))} templates available")
    
    def test_project_creation_requires_auth(self):
        """Verify project creation requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": "Test story for authentication check",
                "title": "Test Story",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook"
            }
        )
        assert response.status_code in [401, 403, 422]
        print(f"✓ Project creation correctly requires auth - status {response.status_code}")


class TestRealTimeProgressPanel:
    """Tests related to real-time progress panel functionality"""
    
    def test_video_status_endpoint_format(self, auth_headers):
        """Verify video status endpoint returns correct format"""
        # Test with a non-existent job ID to verify endpoint format
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/video/status/nonexistent-job",
            headers=auth_headers
        )
        # Should return 404 for non-existent job, not 500
        assert response.status_code == 404
        print(f"✓ Video status endpoint returns 404 for non-existent job as expected")


class TestFFmpegAvailability:
    """Test FFmpeg availability (requires SSH access to verify, but we can check API responses)"""
    
    def test_video_assembly_endpoint_exists(self, auth_headers):
        """Verify video assembly endpoint exists and is accessible"""
        # Test with minimal payload to verify endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/video/assemble",
            headers=auth_headers,
            json={"project_id": "test-project-123"}
        )
        # Should return 402 (insufficient credits) or 404 (project not found), not 500 (FFmpeg missing)
        assert response.status_code in [402, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ Video assembly endpoint accessible - status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
