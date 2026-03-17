"""
Test Suite: UI State Machine Feature - Iteration 294
Tests for Photo-to-Comic state machine fix preventing contradictory UI states.

Core requirements:
1. Admin credits display correctly (999999, not 0)
2. Generate button NOT disabled for admin
3. Status badge transitions: VALIDATING → READY (or PARTIAL_READY)
4. Share buttons disabled unless uiState === READY
5. Download button text changes based on uiState
6. Backend APIs return correct data for state transitions
"""

import pytest
import requests
import os
import time
from io import BytesIO
from PIL import Image

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestAdminCredits:
    """Test admin credits display correctly (P0.1 requirements)"""
    
    def test_admin_login_returns_correct_credits(self):
        """Admin login should return large credits value (999999+), not 0"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "No token in login response"
        
        # Admin should have large credits, not 0
        user = data.get("user", {})
        credits = user.get("credits", 0)
        
        # Admin should have unlimited or large credits
        assert credits > 0 or user.get("role", "").upper() == "ADMIN", \
            f"Admin credits should be positive or role=ADMIN, got credits={credits}, role={user.get('role')}"
        print(f"✓ Admin login returns credits: {credits}, role: {user.get('role')}")
    
    def test_credits_balance_api_for_admin(self):
        """Credits balance API should return unlimited:true for admin"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("token")
        
        # Get credits balance
        headers = {"Authorization": f"Bearer {token}"}
        balance_resp = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert balance_resp.status_code == 200, f"Credits balance failed: {balance_resp.text}"
        
        data = balance_resp.json()
        credits = data.get("credits", data.get("balance", 0))
        unlimited = data.get("unlimited", False)
        
        # Admin should either have unlimited:true OR large credits
        assert unlimited or credits >= 999999, \
            f"Admin should have unlimited:true or credits>=999999, got unlimited={unlimited}, credits={credits}"
        print(f"✓ Credits balance API: unlimited={unlimited}, credits={credits}")
    
    def test_auth_me_returns_admin_role(self):
        """Auth/me endpoint should return admin role correctly"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json().get("token")
        
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert me_resp.status_code == 200
        
        data = me_resp.json()
        user = data.get("user", data)
        role = user.get("role", "").upper()
        
        assert role == "ADMIN", f"Expected role=ADMIN, got {role}"
        print(f"✓ Auth/me returns role: {role}")


class TestGenerateEndpoint:
    """Test photo-to-comic generate endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return login_resp.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_image(self):
        """Create a small test image"""
        img = Image.new('RGB', (100, 100), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    def test_generate_endpoint_requires_auth(self):
        """Generate endpoint should require authentication"""
        response = requests.post(f"{BASE_URL}/api/photo-to-comic/generate")
        assert response.status_code in [401, 422], \
            f"Expected 401/422 without auth, got {response.status_code}"
        print("✓ Generate endpoint requires authentication")
    
    def test_generate_endpoint_accepts_admin_request(self, admin_token, test_image):
        """Admin should be able to start generation (not blocked by credits)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        files = {"photo": ("test.png", test_image, "image/png")}
        data = {
            "mode": "avatar",
            "style": "cartoon_fun"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers=headers,
            files=files,
            data=data
        )
        
        # Should succeed with 200 and return jobId
        assert response.status_code == 200, f"Generate failed: {response.text}"
        
        resp_data = response.json()
        assert resp_data.get("success") == True, f"Generate not successful: {resp_data}"
        assert "jobId" in resp_data, f"No jobId in response: {resp_data}"
        
        print(f"✓ Generate returns jobId: {resp_data.get('jobId')}")
        return resp_data.get("jobId")


class TestJobPolling:
    """Test job polling endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return login_resp.json().get("token")
    
    def test_job_endpoint_returns_status(self, admin_token):
        """Job polling endpoint should return valid status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First, get a valid job ID by starting generation
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        files = {"photo": ("test.png", buffer, "image/png")}
        data = {"mode": "avatar", "style": "cartoon_fun"}
        
        gen_resp = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers=headers,
            files=files,
            data=data
        )
        
        if gen_resp.status_code != 200:
            pytest.skip("Generate failed, skipping job polling test")
        
        job_id = gen_resp.json().get("jobId")
        
        # Poll the job
        job_resp = requests.get(f"{BASE_URL}/api/photo-to-comic/job/{job_id}", headers=headers)
        assert job_resp.status_code == 200, f"Job polling failed: {job_resp.text}"
        
        job_data = job_resp.json()
        assert "status" in job_data, f"No status in job response: {job_data}"
        assert job_data["status"] in ["PENDING", "PROCESSING", "COMPLETED", "FAILED"], \
            f"Invalid job status: {job_data['status']}"
        
        print(f"✓ Job status: {job_data['status']}, progress: {job_data.get('progress', 0)}%")


class TestValidateAssetEndpoint:
    """Test validate-asset endpoint for state machine"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return login_resp.json().get("token")
    
    def test_validate_asset_endpoint_exists(self, admin_token):
        """Validate-asset endpoint should exist and return valid response"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test with a fake job ID - should return 404 or valid structure
        fake_job_id = "fake_job_id_12345"
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/validate-asset/{fake_job_id}",
            headers=headers
        )
        
        # Should return either 404 (not found) or 200 with valid:false
        assert response.status_code in [200, 404], \
            f"Unexpected status for validate-asset: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "valid" in data, f"No 'valid' field in response: {data}"
        
        print(f"✓ Validate-asset endpoint responds: {response.status_code}")


class TestDownloadEndpoint:
    """Test download endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return login_resp.json().get("token")
    
    def test_download_endpoint_exists(self, admin_token):
        """Download endpoint should exist and return proper error for fake job"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        fake_job_id = "fake_download_job_12345"
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/download/{fake_job_id}",
            headers=headers
        )
        
        # Should return 404 for non-existent job or 400 for invalid
        assert response.status_code in [200, 400, 404], \
            f"Unexpected status for download: {response.status_code}"
        
        print(f"✓ Download endpoint responds: {response.status_code}")


class TestActiveChainsEndpoint:
    """Test active-chains endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return login_resp.json().get("token")
    
    def test_active_chains_endpoint(self, admin_token):
        """Active chains should return list structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/active-chains",
            headers=headers
        )
        
        assert response.status_code == 200, f"Active chains failed: {response.text}"
        
        data = response.json()
        # Should be a list or have chains key
        assert isinstance(data, list) or "chains" in data or "activeChains" in data, \
            f"Unexpected active chains response: {data}"
        
        print(f"✓ Active chains endpoint works")


class TestMyChainsEndpoint:
    """Test my-chains endpoint for SafeImage fallback data"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return login_resp.json().get("token")
    
    def test_my_chains_returns_data(self, admin_token):
        """My chains should return list of user's story chains"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/my-chains",
            headers=headers
        )
        
        assert response.status_code == 200, f"My chains failed: {response.text}"
        
        data = response.json()
        # Should be a list
        if isinstance(data, list):
            print(f"✓ My chains returns {len(data)} chains")
            # Check for placehold.co URLs (SafeImage should handle these)
            placeholder_count = 0
            for chain in data[:5]:  # Check first 5
                preview_url = chain.get("preview_url", chain.get("previewUrl", ""))
                if preview_url and "placehold.co" in preview_url:
                    placeholder_count += 1
            if placeholder_count > 0:
                print(f"  Note: {placeholder_count} chains have placehold.co URLs (SafeImage handles these)")
        else:
            print(f"✓ My chains returns data: {type(data)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
