"""
Photo to Comic UX + Storage Endpoints Tests - Iteration 288

Tests:
1. Storage APIs: presigned-upload, confirm-upload, cleanup-temp (admin-only)
2. Photo to Comic: generate endpoint structure (no actual generation), job status
3. Admin access restriction on cleanup-temp

Credentials:
- Test User: test@visionary-suite.com / Test@2026#
- Admin User: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://comic-pipeline-v2.preview.emergentagent.com').rstrip('/')

# ─── Helper Functions ────────────────────────────────────────────────────────

def get_auth_token(email: str, password: str) -> str:
    """Get auth token for a user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    return None

@pytest.fixture(scope="module")
def test_user_token():
    """Get test user token"""
    token = get_auth_token("test@visionary-suite.com", "Test@2026#")
    if not token:
        pytest.skip("Could not authenticate test user")
    return token

@pytest.fixture(scope="module")
def admin_user_token():
    """Get admin user token"""
    token = get_auth_token("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")
    if not token:
        pytest.skip("Could not authenticate admin user")
    return token

# ─── Storage Presigned Upload Tests ──────────────────────────────────────────

class TestStoragePresignedUpload:
    """Tests for POST /api/storage/presigned-upload"""
    
    def test_presigned_upload_returns_required_fields(self, test_user_token):
        """Presigned upload should return upload_url, public_url, storage_key"""
        response = requests.post(
            f"{BASE_URL}/api/storage/presigned-upload",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "filename": "test_photo.jpg",
                "content_type": "image/jpeg",
                "file_size": 1024 * 100,  # 100KB
                "purpose": "photo_upload"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "upload_url" in data, "Response should contain upload_url"
        assert "public_url" in data, "Response should contain public_url"
        assert "storage_key" in data, "Response should contain storage_key"
        
        # Validate URL format
        assert data["upload_url"].startswith("http"), "upload_url should be a valid URL"
        assert data["public_url"].startswith("http"), "public_url should be a valid URL"
    
    def test_presigned_upload_rejects_invalid_content_type(self, test_user_token):
        """Presigned upload should reject invalid file types"""
        response = requests.post(
            f"{BASE_URL}/api/storage/presigned-upload",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "filename": "test_file.exe",
                "content_type": "application/x-msdownload",
                "file_size": 1024,
                "purpose": "photo_upload"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid content type, got {response.status_code}"
    
    def test_presigned_upload_rejects_large_files(self, test_user_token):
        """Presigned upload should reject files over 15MB"""
        response = requests.post(
            f"{BASE_URL}/api/storage/presigned-upload",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "filename": "large_photo.jpg",
                "content_type": "image/jpeg",
                "file_size": 20 * 1024 * 1024,  # 20MB - over limit
                "purpose": "photo_upload"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for file over 15MB, got {response.status_code}"
    
    def test_presigned_upload_requires_auth(self):
        """Presigned upload should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/storage/presigned-upload",
            json={
                "filename": "test_photo.jpg",
                "content_type": "image/jpeg",
                "file_size": 1024,
                "purpose": "photo_upload"
            }
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"

# ─── Storage Confirm Upload Tests ────────────────────────────────────────────

class TestStorageConfirmUpload:
    """Tests for POST /api/storage/confirm-upload"""
    
    def test_confirm_upload_requires_auth(self):
        """Confirm upload should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/storage/confirm-upload",
            json={"storage_key": "test_key"}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_confirm_upload_returns_404_for_invalid_key(self, test_user_token):
        """Confirm upload should return 404 for non-existent storage key"""
        response = requests.post(
            f"{BASE_URL}/api/storage/confirm-upload",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"storage_key": "nonexistent_key_12345"}
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid key, got {response.status_code}"

# ─── Storage Cleanup Temp Tests ──────────────────────────────────────────────

class TestStorageCleanupTemp:
    """Tests for POST /api/storage/cleanup-temp - admin only"""
    
    def test_cleanup_temp_admin_access(self, admin_user_token):
        """Admin should be able to access cleanup-temp endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/storage/cleanup-temp",
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "expired_count" in data, "Response should contain expired_count"
        assert "ttl_hours" in data, "Response should contain ttl_hours"
    
    def test_cleanup_temp_non_admin_rejected(self, test_user_token):
        """Non-admin users should get 403 on cleanup-temp"""
        response = requests.post(
            f"{BASE_URL}/api/storage/cleanup-temp",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    def test_cleanup_temp_requires_auth(self):
        """Cleanup-temp should require authentication"""
        response = requests.post(f"{BASE_URL}/api/storage/cleanup-temp")
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"

# ─── Photo to Comic API Tests ────────────────────────────────────────────────

class TestPhotoToComicAPI:
    """Tests for Photo to Comic API endpoints"""
    
    def test_styles_endpoint(self, test_user_token):
        """GET /api/photo-to-comic/styles should return available styles"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/styles",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "styles" in data, "Response should contain styles"
        assert "pricing" in data, "Response should contain pricing"
        
        # Check we have styles (should be 12+ based on frontend code)
        assert len(data["styles"]) >= 10, f"Expected at least 10 styles, got {len(data['styles'])}"
    
    def test_pricing_endpoint(self, test_user_token):
        """GET /api/photo-to-comic/pricing should return pricing config"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/pricing",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "pricing" in data, "Response should contain pricing"
        pricing = data["pricing"]
        
        # Verify avatar pricing
        assert "comic_avatar" in pricing, "Should have comic_avatar pricing"
        assert pricing["comic_avatar"]["base"] == 3, "Avatar base should be 3 credits"
        
        # Verify strip pricing
        assert "comic_strip" in pricing, "Should have comic_strip pricing"
        assert "panels" in pricing["comic_strip"], "Strip should have panel pricing"
    
    def test_job_status_invalid_id(self, test_user_token):
        """GET /api/photo-to-comic/job/{id} should return 404 for invalid job"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/invalid-job-id-12345",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid job, got {response.status_code}"
    
    def test_history_endpoint(self, test_user_token):
        """GET /api/photo-to-comic/history should return user's history"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "jobs" in data, "Response should contain jobs array"
        assert "total" in data, "Response should contain total count"
        assert "page" in data, "Response should contain page number"
        assert isinstance(data["jobs"], list), "Jobs should be a list"
    
    def test_generate_endpoint_structure(self, test_user_token):
        """POST /api/photo-to-comic/generate should validate input"""
        # Test without photo - should return error
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": f"Bearer {test_user_token}"},
            data={
                "mode": "avatar",
                "style": "cartoon_fun",
                "genre": "action"
            }
        )
        
        # Should fail due to missing photo
        assert response.status_code in [400, 422], f"Expected 400/422 without photo, got {response.status_code}"
    
    def test_generate_blocked_content(self, test_user_token):
        """Generate should reject blocked/copyrighted content keywords"""
        import io
        
        # Create a minimal test image (1x1 pixel PNG)
        test_image = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
            0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
            0x0D, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
            0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        files = {"photo": ("test.png", io.BytesIO(test_image), "image/png")}
        data = {
            "mode": "avatar",
            "style": "cartoon_fun",
            "genre": "action",
            "custom_details": "Create a spiderman character"  # Blocked keyword
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": f"Bearer {test_user_token}"},
            files=files,
            data=data
        )
        
        assert response.status_code == 400, f"Expected 400 for blocked content, got {response.status_code}"
        assert "copyrighted" in response.text.lower() or "blocked" in response.text.lower() or "spiderman" in response.text.lower(), "Should mention copyrighted/blocked content"
    
    def test_diagnostic_endpoint(self, test_user_token):
        """GET /api/photo-to-comic/diagnostic should return system health"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/diagnostic",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "timestamp" in data, "Should have timestamp"
        assert "llm_status" in data, "Should have llm_status"
        assert "recent_jobs" in data, "Should have recent_jobs"

# ─── Credits & Auth Tests ────────────────────────────────────────────────────

class TestCreditsAndAuth:
    """Tests for credits and auth endpoints used by Photo to Comic page"""
    
    def test_credits_balance_endpoint(self, test_user_token):
        """GET /api/credits/balance should return user credits"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "credits" in data, "Response should contain credits"
        assert isinstance(data["credits"], (int, float)), "Credits should be numeric"
    
    def test_auth_me_endpoint(self, test_user_token):
        """GET /api/auth/me should return user info with plan"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should have user or plan info
        assert "user" in data or "plan" in data or "email" in data, "Should have user info"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
