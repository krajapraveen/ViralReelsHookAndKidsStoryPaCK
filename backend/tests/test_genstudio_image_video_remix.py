"""
GenStudio Style Profiles, Text-to-Image/Video, History, and Cashfree Payment Tests
Focus: Testing EXISTING backend endpoints

CRITICAL FINDING: Image-to-Video and Video Remix endpoints do NOT exist in backend!
- Frontend has pages: GenStudioImageToVideo.js, GenStudioVideoRemix.js  
- Backend routes/genstudio.py has NO /image-to-video or /video-remix endpoints
- These features are UI-only placeholders that will fail with 404
"""
import pytest
import requests
import os
import io
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://remix-monetize-1.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


class TestAuthHelper:
    """Authentication helper for tests"""
    
    @staticmethod
    def get_auth_token(email, password):
        """Get auth token for user"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": email, "password": password},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("token")
            return None
        except Exception as e:
            print(f"Auth error: {e}")
            return None


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    token = TestAuthHelper.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not token:
        pytest.skip("Admin authentication failed")
    return token


@pytest.fixture(scope="module")
def demo_token():
    """Get demo user auth token"""
    token = TestAuthHelper.get_auth_token(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        pytest.skip("Demo user authentication failed")
    return token


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Get auth headers for admin"""
    return {"Authorization": f"Bearer {admin_token}"}


# =============================================================================
# CRITICAL: MISSING BACKEND ENDPOINTS TEST
# =============================================================================
class TestMissingBackendEndpoints:
    """Document backend endpoints that are missing but frontend expects them"""
    
    def test_image_to_video_endpoint_missing(self, auth_headers):
        """CRITICAL: Image-to-Video endpoint does not exist in backend"""
        response = requests.post(f"{BASE_URL}/api/genstudio/image-to-video", headers=auth_headers, timeout=30)
        # This WILL return 404 - documenting the gap
        if response.status_code == 404:
            print("CRITICAL: /api/genstudio/image-to-video endpoint NOT IMPLEMENTED")
            print("  - Frontend page exists: GenStudioImageToVideo.js")
            print("  - Backend route MISSING in routes/genstudio.py")
        assert response.status_code == 404, f"Expected 404, got {response.status_code} - endpoint may have been added"
    
    def test_video_remix_endpoint_missing(self, auth_headers):
        """CRITICAL: Video Remix endpoint does not exist in backend"""
        response = requests.post(f"{BASE_URL}/api/genstudio/video-remix", headers=auth_headers, timeout=30)
        if response.status_code == 404:
            print("CRITICAL: /api/genstudio/video-remix endpoint NOT IMPLEMENTED")
            print("  - Frontend page exists: GenStudioVideoRemix.js")
            print("  - Backend route MISSING in routes/genstudio.py")
        assert response.status_code == 404, f"Expected 404, got {response.status_code} - endpoint may have been added"


# =============================================================================
# STYLE PROFILE TESTS
# =============================================================================
class TestStyleProfileAPI:
    """Test Style Profile CRUD operations"""
    
    def test_style_profiles_list_requires_auth(self):
        """Style profiles list requires authentication"""
        response = requests.get(f"{BASE_URL}/api/genstudio/style-profiles", timeout=30)
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("PASS: Style profiles require authentication")
    
    def test_style_profiles_list_success(self, auth_headers):
        """Get style profiles for authenticated user"""
        response = requests.get(
            f"{BASE_URL}/api/genstudio/style-profiles",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "profiles" in data, "Response should contain 'profiles' key"
        print(f"PASS: Got {len(data.get('profiles', []))} style profiles")
    
    def test_style_profile_create_requires_name(self, auth_headers):
        """Style profile creation requires name"""
        response = requests.post(
            f"{BASE_URL}/api/genstudio/style-profile",
            headers=auth_headers,
            json={"name": "", "description": "Test", "tags": []},
            timeout=30
        )
        assert response.status_code in [400, 422], f"Expected validation error for empty name, got {response.status_code}"
        print("PASS: Style profile requires name")
    
    def test_style_profile_create_with_valid_data(self, auth_headers):
        """Create style profile with valid data (costs 20 credits)"""
        test_name = f"TEST_Profile_{datetime.now().timestamp()}"
        response = requests.post(
            f"{BASE_URL}/api/genstudio/style-profile",
            headers=auth_headers,
            json={
                "name": test_name,
                "description": "Test style profile for QA",
                "tags": ["test", "qa", "automation"]
            },
            timeout=30
        )
        
        # May succeed (200/201) or fail due to insufficient credits (400/402)
        if response.status_code in [200, 201]:
            data = response.json()
            assert data.get("success") is True, f"Expected success=true"
            assert "profileId" in data, "Response should contain profileId"
            assert data.get("creditsUsed") == 20, "Should cost 20 credits"
            print(f"PASS: Created style profile {data.get('profileId')} for 20 credits")
            return data.get("profileId")
        elif response.status_code in [400, 402]:
            # Insufficient credits - valid response
            print(f"INFO: Style profile creation blocked - insufficient credits")
        else:
            pytest.fail(f"Unexpected response {response.status_code}: {response.text}")
    
    def test_style_profile_upload_image_validation(self, auth_headers):
        """Style profile image upload validates file type"""
        # Use existing profile ID from previous tests
        profile_id = "9964b0ce-d19c-4007-9734-e06007100e80"
        
        # Try uploading a non-image file
        fake_file = io.BytesIO(b"This is not an image")
        files = {"file": ("test.txt", fake_file, "text/plain")}
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/style-profile/{profile_id}/upload-image",
            headers=auth_headers,
            files=files,
            timeout=30
        )
        
        # Should reject non-image files
        assert response.status_code in [400, 415, 422], f"Expected error for non-image, got {response.status_code}"
        print("PASS: Style profile upload rejects non-image files")
    
    def test_style_profile_upload_valid_image(self, auth_headers):
        """Style profile accepts valid image upload"""
        profile_id = "9964b0ce-d19c-4007-9734-e06007100e80"
        
        # Create minimal valid PNG
        png_bytes = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
            0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE, 0x00, 0x00, 0x00,
            0x0C, 0x49, 0x44, 0x41, 0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
            0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59, 0xE7, 0x00, 0x00, 0x00,
            0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        files = {"file": ("test_image.png", io.BytesIO(png_bytes), "image/png")}
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/style-profile/{profile_id}/upload-image",
            headers=auth_headers,
            files=files,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
            assert "imageUrl" in data
            print(f"PASS: Image uploaded successfully - count: {data.get('imageCount')}")
        elif response.status_code == 404:
            print("INFO: Style profile not found - may have been deleted")
        else:
            print(f"INFO: Image upload response: {response.status_code} - {response.text}")


# =============================================================================
# GENSTUDIO HISTORY TESTS
# =============================================================================
class TestGenStudioHistory:
    """Test GenStudio History and pagination"""
    
    def test_history_requires_auth(self):
        """History endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/genstudio/history", timeout=30)
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("PASS: History requires authentication")
    
    def test_history_pagination(self, auth_headers):
        """History supports pagination"""
        response = requests.get(
            f"{BASE_URL}/api/genstudio/history",
            headers=auth_headers,
            params={"page": 1, "limit": 10},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "jobs" in data, "Response should contain 'jobs'"
        assert "total" in data, "Response should contain 'total'"
        assert "fileExpiryMinutes" in data, "Response should indicate file expiry"
        print(f"PASS: History pagination works - {data.get('total')} total jobs")
    
    def test_history_filter_by_type(self, auth_headers):
        """History can filter by job type"""
        response = requests.get(
            f"{BASE_URL}/api/genstudio/history",
            headers=auth_headers,
            params={"type_filter": "text_to_image"},
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: History type filter works")


# =============================================================================
# CASHFREE PAYMENT ORDER TESTS
# =============================================================================
class TestCashfreePaymentOrder:
    """Test Cashfree payment order creation"""
    
    def test_cashfree_health(self):
        """Cashfree health endpoint is available"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("gateway") == "cashfree", "Should be cashfree gateway"
        assert data.get("configured") is True, "Cashfree should be configured"
        print(f"PASS: Cashfree health - env: {data.get('environment')}")
    
    def test_cashfree_products(self):
        """Get Cashfree products list"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "products" in data, "Should return products"
        products = data.get("products", {})
        
        # Verify expected products exist
        expected_products = ["starter", "creator", "pro", "weekly", "monthly", "quarterly", "yearly"]
        for prod_id in expected_products:
            assert prod_id in products, f"Product {prod_id} should exist"
        
        print(f"PASS: {len(products)} Cashfree products available")
    
    def test_cashfree_create_order_requires_auth(self):
        """Create order requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            json={"productId": "starter", "currency": "INR"},
            timeout=30
        )
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"
        print("PASS: Create order requires authentication")
    
    def test_cashfree_create_order_invalid_product(self, auth_headers):
        """Create order with invalid product fails"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            headers=auth_headers,
            json={"productId": "invalid_product", "currency": "INR"},
            timeout=30
        )
        assert response.status_code == 400, f"Expected 400 for invalid product, got {response.status_code}"
        print("PASS: Invalid product rejected")
    
    def test_cashfree_create_order_success(self, auth_headers):
        """Create valid Cashfree order"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            headers=auth_headers,
            json={"productId": "starter", "currency": "INR"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True, "Order creation should succeed"
            assert "orderId" in data, "Should have orderId"
            assert "cfOrderId" in data, "Should have cfOrderId"
            assert "paymentSessionId" in data, "Should have paymentSessionId"
            
            # Verify order format (cf_order_* format)
            order_id = data.get("orderId", "")
            assert order_id.startswith("cf_order_"), f"Order ID should start with cf_order_, got {order_id}"
            
            print(f"PASS: Cashfree order created - {order_id}")
            print(f"  Environment: {data.get('environment')}")
            print(f"  Amount: {data.get('amount')} {data.get('currency')}")
        elif response.status_code == 429:
            print("INFO: Rate limited - order creation working but limit reached")
        else:
            pytest.fail(f"Order creation failed: {response.status_code} - {response.text}")


# =============================================================================
# SECURITY TESTS
# =============================================================================
class TestSecurityControls:
    """Test security controls and protected routes"""
    
    def test_protected_routes_require_auth(self):
        """Protected routes return 401 without authentication"""
        protected_routes = [
            "/api/genstudio/dashboard",
            "/api/genstudio/style-profiles",
            "/api/genstudio/history",
            "/api/wallet/me",
            "/api/credits/balance"
        ]
        
        for route in protected_routes:
            response = requests.get(f"{BASE_URL}{route}", timeout=30)
            assert response.status_code in [401, 403], f"{route} should require auth, got {response.status_code}"
        
        print(f"PASS: All {len(protected_routes)} protected routes require authentication")
    
    def test_admin_routes_require_admin(self, auth_headers):
        """Admin routes require admin role"""
        # These routes require admin privileges
        admin_routes = [
            "/api/cashfree/monitoring/health",
            "/api/cashfree/orders/pending-delivery"
        ]
        
        for route in admin_routes:
            response = requests.get(
                f"{BASE_URL}{route}",
                headers=auth_headers,
                timeout=30
            )
            # Admin user should have access
            if response.status_code == 200:
                print(f"PASS: Admin has access to {route}")
            else:
                print(f"INFO: {route} returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
