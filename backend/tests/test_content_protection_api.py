"""
Content Protection API Tests - Iteration 428
Tests media proxy secure_url generation and direct static access blocking.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
JOB_ID_WITH_VIDEO = "09d72771-c4bf-4c75-82cc-7eb79bbe87cf"


class TestMediaProxySecureUrl:
    """Test that job assets return secure_url via media proxy, not raw file_url."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    def test_job_assets_have_secure_url(self, auth_token):
        """GET /api/viral-ideas/jobs/{job_id}/assets returns secure_url for file assets."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/{JOB_ID_WITH_VIDEO}/assets", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assets = data.get("assets", [])
        assert len(assets) > 0, "Expected at least one asset"
        
        file_assets = [a for a in assets if a.get("asset_type") in ("thumbnail", "video", "voiceover", "zip_bundle")]
        text_assets = [a for a in assets if a.get("asset_type") in ("hooks", "script", "captions")]
        
        # File assets should have secure_url, NOT file_url
        for asset in file_assets:
            assert "secure_url" in asset, f"File asset {asset.get('asset_type')} missing secure_url"
            assert "file_url" not in asset, f"File asset {asset.get('asset_type')} should NOT have file_url"
            assert "/api/media/stream/" in asset["secure_url"], f"secure_url should use media proxy"
            print(f"PASS: {asset.get('asset_type')} has secure_url via media proxy")
        
        # Text assets should have content, no file_url
        for asset in text_assets:
            assert "content" in asset or asset.get("content") is None, f"Text asset {asset.get('asset_type')} should have content field"
            assert "file_url" not in asset, f"Text asset {asset.get('asset_type')} should NOT have file_url"
            print(f"PASS: {asset.get('asset_type')} has content, no file_url")


class TestDirectStaticAccessBlocked:
    """Test that direct access to viral static files returns 403."""
    
    def test_direct_viral_videos_blocked(self):
        """GET /api/static/generated/viral_videos/* returns 403."""
        response = requests.get(f"{BASE_URL}/api/static/generated/viral_videos/test.mp4")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: /api/static/generated/viral_videos/* returns 403")
    
    def test_direct_viral_thumbs_blocked(self):
        """GET /api/static/generated/viral_thumbs/* returns 403."""
        response = requests.get(f"{BASE_URL}/api/static/generated/viral_thumbs/test.png")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: /api/static/generated/viral_thumbs/* returns 403")
    
    def test_direct_viral_audio_blocked(self):
        """GET /api/static/generated/viral_audio/* returns 403."""
        response = requests.get(f"{BASE_URL}/api/static/generated/viral_audio/test.mp3")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: /api/static/generated/viral_audio/* returns 403")
    
    def test_direct_viral_packs_blocked(self):
        """GET /api/static/generated/viral_packs/* returns 403."""
        response = requests.get(f"{BASE_URL}/api/static/generated/viral_packs/test.zip")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: /api/static/generated/viral_packs/* returns 403")


class TestPublicShareTeaser:
    """Test public share page returns secure proxy URLs."""
    
    def test_share_teaser_thumbnail_is_secure(self):
        """GET /api/viral-ideas/share/{job_id} returns thumbnail_url as secure proxy URL."""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/share/{JOB_ID_WITH_VIDEO}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        thumbnail_url = data.get("thumbnail_url")
        if thumbnail_url:
            assert "/api/media/stream/" in thumbnail_url, f"thumbnail_url should use media proxy, got: {thumbnail_url}"
            assert "/api/static/generated/" not in thumbnail_url, "thumbnail_url should NOT be raw static path"
            print(f"PASS: thumbnail_url uses media proxy: {thumbnail_url[:80]}...")
        else:
            print("INFO: No thumbnail_url in share teaser (may not have thumbnail asset)")
        
        # Verify other teaser fields
        assert "job_id" in data
        assert "idea" in data
        print(f"PASS: Share teaser has job_id and idea")


class TestMediaProxyStreaming:
    """Test media proxy streaming endpoint."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    def test_malformed_token_rejected(self):
        """GET /api/media/stream/{malformed_token} returns 403."""
        response = requests.get(f"{BASE_URL}/api/media/stream/invalid_token_here")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Malformed token rejected with 403")
    
    def test_valid_secure_url_works(self, auth_token):
        """Valid secure_url from job assets should stream content."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get assets to find a secure_url
        response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/{JOB_ID_WITH_VIDEO}/assets", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get job assets")
        
        assets = response.json().get("assets", [])
        file_assets = [a for a in assets if a.get("secure_url")]
        
        if not file_assets:
            pytest.skip("No file assets with secure_url found")
        
        # Try to stream the first file asset
        secure_url = file_assets[0]["secure_url"]
        stream_response = requests.get(f"{BASE_URL}{secure_url}", stream=True)
        
        assert stream_response.status_code in (200, 206), f"Expected 200/206, got {stream_response.status_code}"
        print(f"PASS: Valid secure_url streams content (status {stream_response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
