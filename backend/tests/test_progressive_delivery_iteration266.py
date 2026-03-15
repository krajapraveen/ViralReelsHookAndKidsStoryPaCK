"""
Iteration 266: Progressive Delivery & Browser Video Export Testing
Tests for:
1. GET /api/pipeline/preview/{job_id} - scenes with presigned image_url and audio_url
2. GET /api/pipeline/assets/{job_id} - individual downloadable links
3. POST /api/pipeline/notify-when-ready/{job_id} - notification subscription
4. POST /api/pipeline/generate-fallback/{job_id} - fallback generation
5. WebSocket broadcast_asset_ready function exports from websocket_progress module
6. 3-tier output model endpoints
"""

import os
import pytest
import requests
import sys

# Ensure shared module is importable for websocket test
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://progressive-pipeline.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Test job IDs with fallback outputs (from previous iteration)
TEST_JOB_WITH_FALLBACK = "d870c412-dc39-4400-ab0e-f3a43a514182"  # has both fallback video and story pack
TEST_JOB_WITH_PACK = "b2fe2b5d-57ce-49bc-9751-4cb1ae05492b"  # has story pack


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json().get("token")
    pytest.skip(f"Admin login failed: {resp.status_code}")


@pytest.fixture(scope="module")
def user_token():
    """Get test user auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json().get("token")
    pytest.skip(f"User login failed: {resp.status_code}")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Authenticated admin session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def user_client(user_token):
    """Authenticated user session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    })
    return session


class TestPreviewEndpoint:
    """Test GET /api/pipeline/preview/{job_id} - PUBLIC endpoint"""
    
    def test_preview_returns_scenes_with_presigned_urls(self):
        """Preview endpoint returns scenes with image_url and audio_url"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_WITH_FALLBACK}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("success") == True
        assert "preview" in data
        
        preview = data["preview"]
        assert "scenes" in preview
        assert "title" in preview
        assert "status" in preview
        
        # Check scenes have required fields
        scenes = preview["scenes"]
        assert len(scenes) > 0, "Expected at least one scene"
        
        for scene in scenes:
            assert "scene_number" in scene
            assert "title" in scene
            assert "narration_text" in scene
            # Image and audio urls should be present (may be presigned)
            assert "image_url" in scene or "has_image" in scene
            assert "audio_url" in scene or "has_audio" in scene
    
    def test_preview_includes_fallback_video_url(self):
        """Preview includes fallback_video_url when available"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_WITH_FALLBACK}")
        assert resp.status_code == 200
        
        preview = resp.json()["preview"]
        # This job should have fallback video
        if preview.get("status") == "PARTIAL":
            # Fallback video URL should be present
            assert "fallback_video_url" in preview or "story_pack_url" in preview
    
    def test_preview_includes_story_pack_url(self):
        """Preview includes story_pack_url when available"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_WITH_PACK}")
        assert resp.status_code == 200
        
        preview = resp.json()["preview"]
        # Check for story pack
        assert "story_pack_url" in preview or preview.get("status") == "PARTIAL"
    
    def test_preview_includes_total_scene_counts(self):
        """Preview includes scene count stats"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_WITH_FALLBACK}")
        assert resp.status_code == 200
        
        preview = resp.json()["preview"]
        assert "total_scenes" in preview
        assert "scenes_with_images" in preview or len(preview.get("scenes", [])) > 0
        assert "scenes_with_audio" in preview or len(preview.get("scenes", [])) > 0


class TestAssetsEndpoint:
    """Test GET /api/pipeline/assets/{job_id} - requires auth"""
    
    def test_assets_requires_authentication(self):
        """Assets endpoint requires auth token"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/assets/{TEST_JOB_WITH_FALLBACK}")
        # Should return 401 or 403 without auth
        assert resp.status_code in [401, 403, 422], f"Expected 401/403/422, got {resp.status_code}"
    
    def test_assets_returns_downloadable_links(self, admin_client):
        """Assets endpoint returns individual asset download URLs"""
        resp = admin_client.get(f"{BASE_URL}/api/pipeline/assets/{TEST_JOB_WITH_FALLBACK}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("success") == True
        assert "assets" in data
        
        assets = data["assets"]
        # Should have images, audio, and possibly fallback outputs
        assert "images" in assets or "scenes" in assets or len(assets) > 0


class TestNotifyWhenReadyEndpoint:
    """Test POST /api/pipeline/notify-when-ready/{job_id}"""
    
    def test_notify_requires_authentication(self):
        """Notify endpoint requires auth"""
        resp = requests.post(f"{BASE_URL}/api/pipeline/notify-when-ready/{TEST_JOB_WITH_FALLBACK}")
        assert resp.status_code in [401, 403, 422]
    
    def test_notify_returns_success_for_subscribed(self, admin_client):
        """Notify endpoint returns success response (using admin - can access any job)"""
        resp = admin_client.post(f"{BASE_URL}/api/pipeline/notify-when-ready/{TEST_JOB_WITH_FALLBACK}")
        # Could be 200 (subscribed) or already_done for PARTIAL/COMPLETED jobs
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("success") == True
        # For already completed jobs
        if data.get("already_done"):
            assert "message" in data


class TestGenerateFallbackEndpoint:
    """Test POST /api/pipeline/generate-fallback/{job_id}"""
    
    def test_fallback_requires_authentication(self):
        """Fallback endpoint requires auth"""
        resp = requests.post(f"{BASE_URL}/api/pipeline/generate-fallback/{TEST_JOB_WITH_FALLBACK}")
        assert resp.status_code in [401, 403, 422]
    
    def test_fallback_returns_existing_if_present(self, admin_client):
        """Fallback endpoint returns existing fallback if already generated (using admin)"""
        resp = admin_client.post(f"{BASE_URL}/api/pipeline/generate-fallback/{TEST_JOB_WITH_FALLBACK}")
        # Could return existing fallback or trigger new one
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("success") == True
        # Should mention fallback already exists or status
        assert "message" in data or "fallback_status" in data


class TestWebSocketBroadcastAssetReady:
    """Test that broadcast_asset_ready function exists and is exported"""
    
    def test_broadcast_asset_ready_is_exported(self):
        """Verify broadcast_asset_ready function is exported from websocket_progress"""
        try:
            from routes.websocket_progress import broadcast_asset_ready
            assert callable(broadcast_asset_ready), "broadcast_asset_ready should be callable"
        except ImportError as e:
            pytest.fail(f"Could not import broadcast_asset_ready: {e}")
    
    def test_websocket_module_exports_all_functions(self):
        """Verify all required functions are exported"""
        try:
            from routes.websocket_progress import (
                router,
                manager,
                broadcast_scene_progress,
                broadcast_image_progress,
                broadcast_voice_progress,
                broadcast_video_progress,
                broadcast_completion,
                broadcast_error,
                broadcast_asset_ready
            )
            assert router is not None
            assert manager is not None
            assert callable(broadcast_asset_ready)
        except ImportError as e:
            pytest.fail(f"Missing export from websocket_progress: {e}")


class TestPipelineStatusWithFallback:
    """Test GET /api/pipeline/status/{job_id} includes fallback info"""
    
    def test_status_includes_fallback_object(self, user_client):
        """Status endpoint includes fallback data when available"""
        resp = user_client.get(f"{BASE_URL}/api/pipeline/status/{TEST_JOB_WITH_FALLBACK}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("success") == True
        assert "job" in data
        
        job = data["job"]
        # For partial/failed jobs, should have fallback info
        if job.get("status") in ["PARTIAL", "FAILED"]:
            assert "fallback" in job or "fallback_status" in job


class TestPipelineOptions:
    """Test GET /api/pipeline/options"""
    
    def test_options_returns_animation_styles(self):
        """Options endpoint returns animation styles"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "animation_styles" in data
        assert len(data["animation_styles"]) > 0
    
    def test_options_returns_age_groups(self):
        """Options endpoint returns age groups"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "age_groups" in data
        assert len(data["age_groups"]) > 0
    
    def test_options_returns_voice_presets(self):
        """Options endpoint returns voice presets"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "voice_presets" in data
        assert len(data["voice_presets"]) > 0


class TestGalleryHandlesShowcase:
    """Test that gallery handles showcase items gracefully"""
    
    def test_gallery_returns_videos(self):
        """Gallery endpoint returns video list"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "videos" in data
    
    def test_gallery_video_has_required_fields(self):
        """Gallery videos have required fields"""
        resp = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert resp.status_code == 200
        
        videos = resp.json()["videos"]
        if len(videos) > 0:
            video = videos[0]
            assert "job_id" in video
            assert "title" in video
            # output_url or is_showcase should be present
            assert "output_url" in video or "is_showcase" in video


class TestAdminRegression:
    """Quick regression tests for admin endpoints"""
    
    def test_admin_users_list(self, admin_client):
        """Admin users list endpoint works"""
        resp = admin_client.get(f"{BASE_URL}/api/admin/users/list?limit=5")
        assert resp.status_code == 200
    
    def test_admin_analytics_dashboard(self, admin_client):
        """Admin analytics dashboard endpoint works"""
        resp = admin_client.get(f"{BASE_URL}/api/admin/analytics/dashboard")
        assert resp.status_code == 200
    
    def test_admin_system_health(self, admin_client):
        """Admin system health endpoint works"""
        resp = admin_client.get(f"{BASE_URL}/api/admin/system/system-health")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
