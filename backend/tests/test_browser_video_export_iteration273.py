"""
Iteration 273: Browser Video Export - Asset Proxy and Export Functionality Tests

Tests the following features:
1. Asset proxy endpoint for CORS bypass
2. Preview endpoint data availability 
3. URL validation (R2 only)
4. Content-type detection
"""
import pytest
import requests
import os
import urllib.parse

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://create-share-remix.preview.emergentagent.com').rstrip('/')
TEST_JOB_ID = "a67ff269-1ba5-41d4-a827-9c97cff4d00d"


class TestAssetProxyEndpoint:
    """Test the /api/pipeline/asset-proxy endpoint for CORS bypass"""
    
    def test_asset_proxy_requires_url_param(self):
        """Endpoint should require URL parameter"""
        response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy")
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
        # Check for 'url' in the error message
        assert any("url" in str(item).lower() for item in data.get("detail", []))
    
    def test_asset_proxy_rejects_non_r2_urls(self):
        """Proxy should only allow R2 bucket URLs"""
        non_r2_urls = [
            "https://google.com/image.jpg",
            "https://example.com/test.png",
            "https://s3.amazonaws.com/bucket/file.mp3",
            "https://cdn.somethingelse.com/file.png",
        ]
        for url in non_r2_urls:
            encoded_url = urllib.parse.quote(url, safe='')
            response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
            assert response.status_code == 403, f"Should reject non-R2 URL: {url}"
            data = response.json()
            assert "R2" in data.get("detail", "")
    
    def test_asset_proxy_accepts_r2_domain_cloudflarestorage(self):
        """Proxy should accept r2.cloudflarestorage.com URLs"""
        # Get a real R2 URL from preview
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        assert preview_response.status_code == 200
        preview_data = preview_response.json()
        scenes = preview_data.get("preview", {}).get("scenes", [])
        assert len(scenes) > 0, "Test job should have scenes"
        
        image_url = scenes[0].get("image_url")
        assert image_url, "First scene should have image_url"
        assert "r2.cloudflarestorage.com" in image_url, "URL should be from R2"
        
        # Test the proxy
        encoded_url = urllib.parse.quote(image_url, safe='')
        response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
        assert response.status_code == 200, f"Should accept R2 URL, got {response.status_code}"
        assert response.headers.get("content-type") == "image/png"
        assert len(response.content) > 10000, "Image should have substantial content"
    
    def test_asset_proxy_returns_correct_content_type_for_image(self):
        """Proxy should return correct content-type header for images"""
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        preview_data = preview_response.json()
        image_url = preview_data.get("preview", {}).get("scenes", [])[0].get("image_url")
        
        encoded_url = urllib.parse.quote(image_url, safe='')
        response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
        assert response.status_code == 200
        # PNG images should return image/png
        assert response.headers.get("content-type") == "image/png"
    
    def test_asset_proxy_returns_correct_content_type_for_audio(self):
        """Proxy should return correct content-type header for audio"""
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        preview_data = preview_response.json()
        audio_url = preview_data.get("preview", {}).get("scenes", [])[0].get("audio_url")
        
        if audio_url:  # Only test if audio exists
            encoded_url = urllib.parse.quote(audio_url, safe='')
            response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
            assert response.status_code == 200
            # MP3 audio should return audio/mpeg
            assert response.headers.get("content-type") == "audio/mpeg"
    
    def test_asset_proxy_has_cors_headers(self):
        """Proxy should include CORS headers for client-side access"""
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        preview_data = preview_response.json()
        image_url = preview_data.get("preview", {}).get("scenes", [])[0].get("image_url")
        
        encoded_url = urllib.parse.quote(image_url, safe='')
        response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
        assert response.status_code == 200
        # Should have Access-Control-Allow-Origin header
        assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]
    
    def test_asset_proxy_has_cache_control(self):
        """Proxy should include cache control headers"""
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        preview_data = preview_response.json()
        image_url = preview_data.get("preview", {}).get("scenes", [])[0].get("image_url")
        
        encoded_url = urllib.parse.quote(image_url, safe='')
        response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
        assert response.status_code == 200
        # Should have cache-control header
        cache_control = response.headers.get("cache-control", "")
        # Either has max-age or no-cache (per the code it should have max-age=3600)
        assert "max-age" in cache_control or "cache" in cache_control


class TestPreviewEndpoint:
    """Test the /api/pipeline/preview/{job_id} endpoint"""
    
    def test_preview_endpoint_returns_success(self):
        """Preview endpoint should return success for completed job"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_preview_has_scenes_with_image_urls(self):
        """Preview should include scenes with image URLs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        data = response.json()
        preview = data.get("preview", {})
        scenes = preview.get("scenes", [])
        
        assert len(scenes) > 0, "Should have at least one scene"
        for scene in scenes:
            if scene.get("has_image"):
                assert scene.get("image_url"), f"Scene {scene.get('scene_number')} has_image but no URL"
    
    def test_preview_has_scenes_with_audio_urls(self):
        """Preview should include scenes with audio URLs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        data = response.json()
        preview = data.get("preview", {})
        scenes = preview.get("scenes", [])
        
        assert len(scenes) > 0, "Should have at least one scene"
        for scene in scenes:
            if scene.get("has_audio"):
                assert scene.get("audio_url"), f"Scene {scene.get('scene_number')} has_audio but no URL"
    
    def test_preview_has_correct_status(self):
        """Preview should show COMPLETED status for finished job"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        data = response.json()
        preview = data.get("preview", {})
        
        status = preview.get("status")
        assert status in ["COMPLETED", "PARTIAL"], f"Status should be COMPLETED or PARTIAL, got {status}"
    
    def test_preview_scenes_have_durations(self):
        """Preview scenes should have duration information"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        data = response.json()
        preview = data.get("preview", {})
        scenes = preview.get("scenes", [])
        
        for scene in scenes:
            if scene.get("has_audio"):
                duration = scene.get("duration")
                assert duration is not None and duration > 0, f"Scene {scene.get('scene_number')} should have positive duration"
    
    def test_preview_returns_404_for_invalid_job(self):
        """Preview should return 404 for non-existent job"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/invalid-job-id-12345")
        assert response.status_code == 404
    
    def test_preview_has_title_and_story_text(self):
        """Preview should include title and story text"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        data = response.json()
        preview = data.get("preview", {})
        
        assert preview.get("title"), "Preview should have a title"
        assert preview.get("story_text"), "Preview should have story text"
    
    def test_preview_scene_count_matches_metadata(self):
        """Scene count should match total_scenes metadata"""
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        data = response.json()
        preview = data.get("preview", {})
        
        total_scenes = preview.get("total_scenes", 0)
        scenes = preview.get("scenes", [])
        assert len(scenes) == total_scenes, f"Scene count mismatch: {len(scenes)} vs {total_scenes}"


class TestImageProxyContent:
    """Test that proxied images are valid and usable for video export"""
    
    def test_proxied_image_is_valid_png(self):
        """Proxied image should be a valid PNG file"""
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        preview_data = preview_response.json()
        image_url = preview_data.get("preview", {}).get("scenes", [])[0].get("image_url")
        
        encoded_url = urllib.parse.quote(image_url, safe='')
        response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
        
        # Check PNG magic bytes
        content = response.content
        assert content[:8] == b'\x89PNG\r\n\x1a\n', "Response should be valid PNG"
    
    def test_proxied_image_has_reasonable_size(self):
        """Proxied image should have reasonable file size for 720p video"""
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        preview_data = preview_response.json()
        image_url = preview_data.get("preview", {}).get("scenes", [])[0].get("image_url")
        
        encoded_url = urllib.parse.quote(image_url, safe='')
        response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
        
        # Image should be between 100KB and 10MB (reasonable for 720p scene)
        size_bytes = len(response.content)
        assert 100_000 < size_bytes < 10_000_000, f"Image size {size_bytes} bytes seems unusual"


class TestAllScenesAccessible:
    """Test that all scenes from a completed job are accessible via proxy"""
    
    def test_all_scene_images_accessible_via_proxy(self):
        """All scene images should be fetchable via the proxy"""
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        preview_data = preview_response.json()
        scenes = preview_data.get("preview", {}).get("scenes", [])
        
        for scene in scenes:
            image_url = scene.get("image_url")
            if image_url:
                encoded_url = urllib.parse.quote(image_url, safe='')
                response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
                assert response.status_code == 200, f"Scene {scene.get('scene_number')} image should be accessible"
                assert len(response.content) > 0, f"Scene {scene.get('scene_number')} image should have content"
    
    def test_all_scene_audio_accessible_via_proxy(self):
        """All scene audio files should be fetchable via the proxy"""
        preview_response = requests.get(f"{BASE_URL}/api/pipeline/preview/{TEST_JOB_ID}")
        preview_data = preview_response.json()
        scenes = preview_data.get("preview", {}).get("scenes", [])
        
        for scene in scenes:
            audio_url = scene.get("audio_url")
            if audio_url:
                encoded_url = urllib.parse.quote(audio_url, safe='')
                response = requests.get(f"{BASE_URL}/api/pipeline/asset-proxy?url={encoded_url}")
                assert response.status_code == 200, f"Scene {scene.get('scene_number')} audio should be accessible"
                assert len(response.content) > 0, f"Scene {scene.get('scene_number')} audio should have content"
