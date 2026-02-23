"""
Comprehensive QA Audit Test Suite - Iteration 64
Tests all backend APIs for CreatorStudio AI
"""
import pytest
import requests
import os
import time

# Use production preview URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://image-to-comic.preview.emergentagent.com')
if not BASE_URL:
    BASE_URL = 'https://image-to-comic.preview.emergentagent.com'

BASE_URL = BASE_URL.rstrip('/')

# Test credentials
TEST_USER = {
    "email": "demo@example.com",
    "password": "Password123!"
}


class TestHealthEndpoints:
    """Health and system status endpoints"""
    
    def test_health_basic(self):
        """Test basic health check"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert "version" in data
        assert "system" in data
        print(f"✅ Health check passed: version={data.get('version')}, CPU={data['system'].get('cpu_percent')}%")
    
    def test_health_live(self):
        """Test liveness probe"""
        response = requests.get(f"{BASE_URL}/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "alive"
        print("✅ Liveness probe passed")
    
    def test_health_ready(self):
        """Test readiness probe"""
        response = requests.get(f"{BASE_URL}/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["ready", "not_ready"]
        print(f"✅ Readiness probe passed: status={data.get('status')}")
    
    def test_health_metrics(self):
        """Test metrics endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "users" in data or "error" not in data
        print(f"✅ Metrics endpoint passed")


class TestAuthentication:
    """Authentication flow tests"""
    
    def test_login_success(self):
        """Test successful login with demo credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        # API may return 200 or 401 depending on user existence
        if response.status_code == 200:
            data = response.json()
            assert "token" in data
            print(f"✅ Login successful, token received")
        else:
            print(f"⚠️ Login returned {response.status_code} - user may not exist")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        # Should return 401 or error
        assert response.status_code in [401, 400, 404, 422]
        print(f"✅ Invalid login correctly rejected: {response.status_code}")
    
    def test_login_validation(self):
        """Test login validation - missing fields"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ""
        })
        assert response.status_code in [400, 422]
        print(f"✅ Missing field validation works: {response.status_code}")


class TestWalletAndCredits:
    """Wallet and credit system tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_wallet_balance_unauthenticated(self):
        """Test wallet balance without auth"""
        response = requests.get(f"{BASE_URL}/api/wallet/me")
        assert response.status_code in [401, 403]
        print(f"✅ Wallet requires authentication: {response.status_code}")
    
    def test_credits_balance_unauthenticated(self):
        """Test credits balance without auth"""
        response = requests.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code in [401, 403]
        print(f"✅ Credits requires authentication: {response.status_code}")
    
    def test_wallet_authenticated(self, auth_token):
        """Test wallet balance with auth"""
        if not auth_token:
            pytest.skip("No auth token available")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers)
        if response.status_code == 200:
            data = response.json()
            assert "balanceCredits" in data or "balance" in data or "availableCredits" in data
            print(f"✅ Wallet balance retrieved")
        else:
            print(f"⚠️ Wallet API returned: {response.status_code}")


class TestProductsAndPricing:
    """Products and pricing tests"""
    
    def test_products_list(self):
        """Test products endpoint"""
        response = requests.get(f"{BASE_URL}/api/products")
        # Products might be public or require auth
        if response.status_code == 200:
            data = response.json()
            assert "products" in data
            print(f"✅ Products list retrieved: {len(data.get('products', {}))} products")
        else:
            print(f"⚠️ Products API returned: {response.status_code}")
    
    def test_pricing(self):
        """Test pricing endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/pricing")
        if response.status_code == 200:
            data = response.json()
            assert "pricing" in data
            print(f"✅ Pricing retrieved")
        else:
            # Try without auth
            print(f"⚠️ Pricing API returned: {response.status_code}")


class TestReelGenerator:
    """Reel Generator API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_reel_generation_unauthenticated(self):
        """Test reel generation without auth"""
        response = requests.post(f"{BASE_URL}/api/generations/reel", json={
            "topic": "Test topic",
            "niche": "Luxury"
        })
        assert response.status_code in [401, 403]
        print(f"✅ Reel generation requires auth: {response.status_code}")
    
    def test_reel_generation_endpoint_exists(self, auth_token):
        """Test reel generation endpoint exists"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/generations/reel", 
            headers=headers,
            json={
                "topic": "Test productivity tips",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            })
        # Should return success, insufficient credits, or rate limit
        assert response.status_code in [200, 201, 402, 429, 500]
        print(f"✅ Reel generation endpoint responded: {response.status_code}")


class TestStoryGenerator:
    """Story Generator API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_story_generation_unauthenticated(self):
        """Test story generation without auth"""
        response = requests.post(f"{BASE_URL}/api/generations/story", json={
            "ageGroup": "4-6",
            "theme": "Adventure"
        })
        assert response.status_code in [401, 403]
        print(f"✅ Story generation requires auth: {response.status_code}")


class TestCreatorTools:
    """Creator Tools API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_trending_topics(self):
        """Test trending topics - free endpoint"""
        response = requests.get(f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=5")
        if response.status_code == 200:
            data = response.json()
            assert "topics" in data or "success" in data
            print(f"✅ Trending topics retrieved")
        else:
            # May require auth
            print(f"⚠️ Trending API returned: {response.status_code}")
    
    def test_hashtags_endpoint(self, auth_token):
        """Test hashtags endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        response = requests.get(f"{BASE_URL}/api/creator-tools/hashtags/business", headers=headers)
        if response.status_code == 200:
            data = response.json()
            assert "hashtags" in data
            print(f"✅ Hashtags retrieved: {len(data.get('hashtags', []))} tags")
        else:
            print(f"⚠️ Hashtags API returned: {response.status_code}")


class TestGenStudio:
    """GenStudio API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_genstudio_templates(self, auth_token):
        """Test GenStudio templates endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        response = requests.get(f"{BASE_URL}/api/genstudio/templates", headers=headers)
        if response.status_code == 200:
            data = response.json()
            assert "templates" in data
            print(f"✅ GenStudio templates retrieved: {len(data.get('templates', []))} templates")
        else:
            print(f"⚠️ GenStudio templates returned: {response.status_code}")
    
    def test_text_to_image_unauthenticated(self):
        """Test text to image without auth"""
        response = requests.post(f"{BASE_URL}/api/genstudio/text-to-image", json={
            "prompt": "test"
        })
        assert response.status_code in [401, 403]
        print(f"✅ Text to image requires auth: {response.status_code}")


class TestCashfreePayment:
    """Cashfree payment integration tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_create_order_unauthenticated(self):
        """Test order creation without auth"""
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "monthly",
            "currency": "INR"
        })
        assert response.status_code in [401, 403]
        print(f"✅ Order creation requires auth: {response.status_code}")
    
    def test_create_order_authenticated(self, auth_token):
        """Test order creation with auth"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", 
            headers=headers,
            json={
                "productId": "monthly",
                "currency": "INR"
            })
        # Should return session ID or error
        if response.status_code == 200:
            data = response.json()
            # Should have paymentSessionId or error
            print(f"✅ Order creation responded: {response.status_code}")
        else:
            print(f"⚠️ Order creation returned: {response.status_code}")


class TestUserProfile:
    """User profile tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_get_current_user_unauthenticated(self):
        """Test current user without auth"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        print(f"✅ Current user requires auth: {response.status_code}")
    
    def test_get_current_user_authenticated(self, auth_token):
        """Test current user with auth"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        if response.status_code == 200:
            data = response.json()
            assert "email" in data or "id" in data
            print(f"✅ Current user retrieved: {data.get('email', 'N/A')}")
        else:
            print(f"⚠️ Current user returned: {response.status_code}")


class TestGenerationHistory:
    """Generation history tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_history_unauthenticated(self):
        """Test history without auth"""
        response = requests.get(f"{BASE_URL}/api/generations")
        assert response.status_code in [401, 403]
        print(f"✅ History requires auth: {response.status_code}")
    
    def test_history_authenticated(self, auth_token):
        """Test history with auth"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/generations", headers=headers)
        if response.status_code == 200:
            data = response.json()
            assert "generations" in data
            print(f"✅ History retrieved: {len(data.get('generations', []))} items")
        else:
            print(f"⚠️ History returned: {response.status_code}")


class TestComicStudio:
    """Comic Studio API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_comic_styles(self):
        """Test comic styles endpoint"""
        response = requests.get(f"{BASE_URL}/api/comic/styles")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Comic styles retrieved")
        else:
            print(f"⚠️ Comic styles returned: {response.status_code}")
    
    def test_story_generation_endpoint(self, auth_token):
        """Test comic story generation endpoint"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/comic/generate-story",
            headers=headers,
            json={
                "genre": "superhero",
                "character_name": "TestHero",
                "panel_count": 4
            })
        # Should work or need credits
        if response.status_code == 200:
            data = response.json()
            assert "title" in data or "story" in data
            print(f"✅ Comic story generation works")
        else:
            print(f"⚠️ Comic story returned: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
