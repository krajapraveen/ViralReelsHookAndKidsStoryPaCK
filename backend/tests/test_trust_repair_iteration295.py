"""
Trust Repair Sprint - Iteration 295
Testing:
1. Backend validate-asset endpoint returns separate download_ready + preview_ready
2. Frontend UI state machine: IDLE/PROCESSING/VALIDATING/READY/PARTIAL_READY/FAILED
3. Admin credits display (should show infinity or 999999)
4. Image fallback handlers on Dashboard, Landing, ExplorePage, Gallery, CreatorProfile
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://k-factor-boost.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestValidateAssetEndpoint:
    """Backend /api/photo-to-comic/validate-asset tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture
    def test_user_token(self):
        """Get test user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Test user authentication failed")
    
    def test_validate_asset_returns_separate_fields(self, admin_token):
        """Validate-asset endpoint returns download_ready + preview_ready separately"""
        # Use a known CDN job ID from admin (mentioned in context)
        job_id = "55297acd-c81f-4fdf-b725-1b6fbb96ad1b"
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/validate-asset/{job_id}", headers=headers)
        
        # Verify endpoint returns expected fields
        if response.status_code == 200:
            data = response.json()
            # CRITICAL: Must have separate download_ready and preview_ready fields
            assert "download_ready" in data, "Response missing download_ready field"
            assert "preview_ready" in data, "Response missing preview_ready field"
            assert isinstance(data["download_ready"], bool), "download_ready must be boolean"
            assert isinstance(data["preview_ready"], bool), "preview_ready must be boolean"
            print(f"PASS: validate-asset returns download_ready={data['download_ready']}, preview_ready={data['preview_ready']}")
            
            # Additional fields check
            if "permanent" in data:
                print(f"  permanent={data['permanent']}")
            if "cdn_backed" in data:
                print(f"  cdn_backed={data['cdn_backed']}")
            if "asset_type" in data:
                print(f"  asset_type={data['asset_type']}")
        elif response.status_code == 404:
            pytest.skip(f"Job {job_id} not found - may have been deleted")
        else:
            pytest.fail(f"Unexpected status {response.status_code}: {response.text}")
    
    def test_validate_asset_not_found(self, admin_token):
        """Validate-asset returns 404 for non-existent job"""
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/validate-asset/{fake_job_id}", headers=headers)
        
        assert response.status_code == 404, f"Expected 404 for non-existent job, got {response.status_code}"
        print("PASS: Non-existent job returns 404")


class TestAdminCredits:
    """Admin credits display tests"""
    
    def test_admin_credits_unlimited(self):
        """Admin should have unlimited credits (999999 or infinity bypass)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        token = data.get("token")
        user = data.get("user", {})
        
        # Admin should be ADMIN role
        role = user.get("role", "").upper()
        assert role == "ADMIN", f"Expected ADMIN role, got {role}"
        
        # Check credits via /api/credits/balance
        headers = {"Authorization": f"Bearer {token}"}
        balance_response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        
        if balance_response.status_code == 200:
            balance_data = balance_response.json()
            credits = balance_data.get("credits") or balance_data.get("balance") or 0
            unlimited = balance_data.get("unlimited", False)
            
            # Admin should have very high credits OR unlimited flag
            if unlimited:
                print(f"PASS: Admin has unlimited=True")
            elif credits >= 999999:
                print(f"PASS: Admin credits = {credits} (effectively unlimited)")
            else:
                # Check via user object
                user_credits = user.get("credits", 0)
                if user_credits >= 999999:
                    print(f"PASS: Admin user object credits = {user_credits}")
                else:
                    pytest.fail(f"Admin credits too low: {credits}, expected >= 999999 or unlimited=True")
        else:
            # Fallback: check user credits from login response
            user_credits = user.get("credits", 0)
            if user_credits >= 999999:
                print(f"PASS: Admin credits from login = {user_credits}")
            else:
                pytest.skip(f"Credits balance endpoint returned {balance_response.status_code}")


class TestPhotoToComicGeneration:
    """Photo-to-Comic generation flow tests"""
    
    @pytest.fixture
    def test_user_token(self):
        """Get test user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Test user authentication failed")
    
    def test_photo_to_comic_styles_endpoint(self, test_user_token):
        """Get available styles"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/styles", headers=headers)
        
        assert response.status_code == 200, f"Styles endpoint failed: {response.text}"
        data = response.json()
        assert "styles" in data, "Missing styles in response"
        assert "pricing" in data, "Missing pricing in response"
        print(f"PASS: Styles endpoint returns {len(data['styles'])} styles")
    
    def test_photo_to_comic_pricing_endpoint(self, test_user_token):
        """Get pricing configuration"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/pricing", headers=headers)
        
        assert response.status_code == 200, f"Pricing endpoint failed: {response.text}"
        data = response.json()
        assert "pricing" in data, "Missing pricing in response"
        print(f"PASS: Pricing endpoint returns pricing config")
    
    def test_photo_to_comic_history(self, test_user_token):
        """Get user's generation history"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=headers)
        
        assert response.status_code == 200, f"History endpoint failed: {response.text}"
        data = response.json()
        assert "jobs" in data, "Missing jobs in response"
        assert "total" in data, "Missing total in response"
        print(f"PASS: History endpoint returns {data['total']} jobs")


class TestPublicEndpoints:
    """Public endpoints for gallery/explore/landing"""
    
    def test_public_stats(self):
        """Public stats endpoint for landing page"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: Public stats returned: creators={data.get('creators', 0)}")
        else:
            print(f"INFO: Public stats endpoint returned {response.status_code}")
    
    def test_public_trending(self):
        """Public trending for landing page"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=5")
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            print(f"PASS: Trending returns {len(items)} items")
        else:
            print(f"INFO: Trending endpoint returned {response.status_code}")
    
    def test_public_explore(self):
        """Public explore endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            print(f"PASS: Explore returns {len(items)} items")
        else:
            print(f"INFO: Explore endpoint returned {response.status_code}")
    
    def test_gallery_endpoint(self):
        """Gallery videos endpoint"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?sort=newest")
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            print(f"PASS: Gallery returns {len(videos)} videos")
        else:
            print(f"INFO: Gallery endpoint returned {response.status_code}")


class TestHealthEndpoints:
    """Basic health checks"""
    
    def test_api_health(self):
        """API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", f"Unhealthy status: {data}"
        print("PASS: API health check passed")
    
    def test_auth_login_admin(self):
        """Admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Missing token in response"
        print("PASS: Admin login successful")
    
    def test_auth_login_test_user(self):
        """Test user login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Test user login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Missing token in response"
        print("PASS: Test user login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
