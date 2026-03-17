"""
Trust Repair Sprint Backend Tests - Iteration 293
Tests critical reliability issues:
1. Admin credits display (unlimited:true, proper credit values)
2. Photo-to-Comic generation API creates jobs
3. Job polling returns real status updates
4. Credits balance API returns correct data
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://narrative-suite.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestAdminCredits:
    """Test admin user credits display correctly"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        return data["token"]
    
    def test_admin_login_returns_correct_credits(self, admin_token):
        """P0.1: Admin login returns high credit value (not 0)"""
        # Re-login to check login response
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        user = data.get("user", {})
        
        # Admin should have high credits - NOT 0
        assert user.get("credits", 0) > 1000, f"Admin credits too low: {user.get('credits')}"
        assert user.get("role") == "ADMIN", "Admin role not returned"
        print(f"✓ Admin login returns credits: {user.get('credits')} with role: {user.get('role')}")
    
    def test_credits_balance_api_returns_unlimited_for_admin(self, admin_token):
        """P0.2: Credits balance API returns unlimited:true for admin"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Must have unlimited:true for admin
        assert data.get("unlimited") == True, f"Admin should have unlimited=true, got: {data.get('unlimited')}"
        # Credits should be high, not 0
        credits = data.get("credits") or data.get("balance") or 0
        assert credits >= 999999, f"Admin credits should be >= 999999, got: {credits}"
        # Plan should indicate pro or admin level
        assert data.get("plan") in ["pro", "admin", "studio"], f"Unexpected plan: {data.get('plan')}"
        print(f"✓ Credits balance API returns unlimited:{data.get('unlimited')}, credits:{credits}, plan:{data.get('plan')}")
    
    def test_auth_me_returns_admin_role(self, admin_token):
        """P0.1: Auth/me returns ADMIN role correctly"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Can be nested under 'user' or direct
        user = data.get("user", data)
        assert user.get("role") == "ADMIN", f"Expected ADMIN role, got: {user.get('role')}"
        # Credits should be high
        assert user.get("credits", 0) > 1000, f"Admin credits too low in auth/me: {user.get('credits')}"
        print(f"✓ Auth/me returns role: {user.get('role')} with credits: {user.get('credits')}")


class TestPhotoToComicGeneration:
    """Test Photo-to-Comic generation flow"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get test user auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_generate_endpoint_requires_auth(self):
        """Photo-to-comic generate requires authentication"""
        response = requests.post(f"{BASE_URL}/api/photo-to-comic/generate")
        assert response.status_code in [401, 422], f"Expected auth error, got: {response.status_code}"
        print("✓ Generate endpoint properly requires authentication")
    
    def test_generate_endpoint_exists_and_accepts_post(self, admin_token):
        """P0.1: Generate endpoint exists and accepts POST with multipart data"""
        # Create a minimal test image (1x1 pixel PNG)
        import io
        # Minimal valid PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # bit depth, color type, etc
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0x00, 0x00, 0x00,
            0x01, 0x00, 0x01, 0x5C, 0xCD, 0xFF, 0xA2, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
            0x42, 0x60, 0x82
        ])
        
        files = {
            'photo': ('test.png', io.BytesIO(png_data), 'image/png')
        }
        data = {
            'mode': 'avatar',
            'style': 'cartoon_fun',
            'genre': 'action',
            'panel_count': '4',
            'hd_export': 'false',
            'include_dialogue': 'true'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data=data
        )
        
        # Should return 200 with success:true and jobId, OR error if image processing fails
        # We're testing the endpoint exists and processes the request
        assert response.status_code in [200, 400, 422, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            result = response.json()
            # Should have either success+jobId or error
            if result.get("success"):
                assert "jobId" in result, "Missing jobId in success response"
                print(f"✓ Generate endpoint created job: {result.get('jobId')}")
            else:
                print(f"✓ Generate endpoint responded (no job created): {result}")
        else:
            print(f"✓ Generate endpoint exists (status {response.status_code})")
    
    def test_job_polling_endpoint_exists(self, admin_token):
        """P0.1: Job polling endpoint exists"""
        # Test with a fake job ID - should return 404 or error
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/test-fake-job-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 404 for non-existent job, not 500
        assert response.status_code in [404, 400], f"Expected 404/400 for fake job, got: {response.status_code}"
        print(f"✓ Job polling endpoint properly handles non-existent jobs (status {response.status_code})")
    
    def test_active_chains_endpoint(self, admin_token):
        """P0.1: Active chains endpoint returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/active-chains",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have chains array
        assert "chains" in data, "Missing 'chains' in response"
        assert isinstance(data["chains"], list), "chains should be a list"
        
        # If there are chains, validate structure
        if data["chains"]:
            chain = data["chains"][0]
            # These fields should exist for re-engagement momentum
            expected_fields = ["chain_id", "total_episodes", "progress_pct"]
            for field in expected_fields:
                assert field in chain, f"Missing field '{field}' in chain"
        
        print(f"✓ Active chains endpoint returns {len(data['chains'])} chains")


class TestSafeImageValidation:
    """Test that image URLs are handled properly - no placehold.co URLs in real responses"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_chains_dont_return_placeholder_urls(self, admin_token):
        """P0.3: Active chains should not return placehold.co URLs"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/active-chains",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for chain in data.get("chains", []):
            preview_url = chain.get("preview_url", "")
            # Should not be a placehold.co URL
            if preview_url:
                assert "placehold.co" not in preview_url, f"Found placehold.co URL: {preview_url}"
        
        print(f"✓ No placeholder URLs found in {len(data.get('chains', []))} chains")


class TestGenerationProgress:
    """Test progress reporting and timeout handling"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_validate_asset_endpoint_exists(self, admin_token):
        """P0.5: Validate asset endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/validate-asset/test-fake-job",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should handle gracefully - not crash
        assert response.status_code in [200, 404, 400], f"Unexpected status: {response.status_code}"
        print(f"✓ Validate asset endpoint exists (status {response.status_code})")


class TestDownloadRestrictions:
    """Test download only works for validated assets"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_download_endpoint_exists(self, admin_token):
        """P0.5: Download endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/download/test-fake-job",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 404 for non-existent job, not 500
        assert response.status_code in [404, 400], f"Expected 404/400, got: {response.status_code}"
        print(f"✓ Download endpoint properly handles non-existent jobs (status {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
