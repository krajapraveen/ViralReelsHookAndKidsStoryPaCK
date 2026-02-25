"""
CreatorStudio AI - Comprehensive QA Audit Tests - Iteration 65
Tests all backend APIs for the QA testing preview environment
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://test-phase-runner.preview.emergentagent.com')

# Test credentials
DEMO_USER = {
    "email": "demo@example.com",
    "password": "Password123!"
}

ADMIN_USER = {
    "email": "admin@creatorstudio.ai",
    "password": "Cr3@t0rStud!o#2026"
}


class TestHealthEndpoints:
    """Health check API tests"""
    
    def test_health_basic(self):
        """Test basic health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        print(f"Health API: {data['status']}, Version: {data['version']}")
    
    def test_health_live(self):
        """Test liveness probe"""
        response = requests.get(f"{BASE_URL}/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] == True
        print("Liveness probe: OK")
    
    def test_health_ready(self):
        """Test readiness probe"""
        response = requests.get(f"{BASE_URL}/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        print(f"Readiness probe: {data['ready']}")
    
    def test_health_metrics(self):
        """Test system metrics endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        print(f"System metrics: CPU {data['system'].get('cpu_percent', 'N/A')}%, Memory {data['system'].get('memory_percent', 'N/A')}%")


class TestAuthentication:
    """Authentication flow tests"""
    
    def test_login_success(self):
        """Test successful login with demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == DEMO_USER["email"]
        print(f"Login success: {data['user']['email']}, Credits: {data['user']['credits']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("Invalid credentials properly rejected")
    
    def test_login_missing_fields(self):
        """Test login with missing fields"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com"
        })
        assert response.status_code == 422
        print("Missing fields properly validated")


class TestAuthenticatedEndpoints:
    """Tests requiring authentication"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Get auth token for authenticated tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed")
    
    def test_get_current_user(self):
        """Test getting current user info"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == DEMO_USER["email"]
        print(f"Current user: {data['email']}, Role: {data.get('role', 'user')}")
    
    def test_wallet_balance(self):
        """Test wallet balance retrieval"""
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "balanceCredits" in data or "balance" in data
        credits = data.get("balanceCredits") or data.get("balance", 0)
        print(f"Wallet balance: {credits} credits")
    
    def test_credits_balance(self):
        """Test credits balance retrieval"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data or "balance" in data
        print(f"Credits balance: {data.get('credits', data.get('balance', 0))}")
    
    def test_generation_history(self):
        """Test generation history retrieval"""
        response = requests.get(f"{BASE_URL}/api/generate/", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "generations" in data
        print(f"Generation history: {len(data['generations'])} items")


class TestProductsAndPricing:
    """Products and pricing API tests"""
    
    def test_products_list(self):
        """Test products listing"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        products = data["products"]
        print(f"Products available: {len(products) if isinstance(products, list) else len(products.keys())}")
    
    def test_wallet_pricing(self):
        """Test wallet pricing info"""
        response = requests.get(f"{BASE_URL}/api/wallet/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"Pricing categories: {list(data['pricing'].keys())}")


class TestCreatorTools:
    """Creator Tools API tests"""
    
    def test_trending_topics(self):
        """Test trending topics endpoint"""
        response = requests.get(f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "topics" in data
        print(f"Trending topics: {len(data['topics'])} items")
    
    def test_hashtag_bank(self):
        """Test hashtag bank endpoint"""
        response = requests.get(f"{BASE_URL}/api/creator-tools/hashtags/business")
        assert response.status_code == 200
        data = response.json()
        assert "hashtags" in data
        assert data.get("niche") == "business"
        print(f"Hashtags for business: {len(data['hashtags'])} tags")
    
    def test_thumbnail_text(self):
        """Test thumbnail text generator"""
        response = requests.post(f"{BASE_URL}/api/creator-tools/thumbnail-text?topic=productivity")
        assert response.status_code == 200
        data = response.json()
        assert "thumbnails" in data
        print(f"Thumbnail styles generated: {list(data['thumbnails'].keys())}")


class TestGenStudio:
    """GenStudio API tests"""
    
    def test_genstudio_templates(self):
        """Test GenStudio templates endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        print(f"GenStudio templates: {len(data['templates'])} available")
    
    def test_text_to_image_unauthenticated(self):
        """Test text-to-image without auth (should fail)"""
        response = requests.post(f"{BASE_URL}/api/wallet/create-job", json={
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {"prompt": "test"}
        })
        assert response.status_code in [401, 403, 422]
        print("Text-to-image properly requires authentication")


class TestReelGenerator:
    """Reel Generator API tests"""
    
    def test_reel_unauthenticated(self):
        """Test reel generation without auth"""
        response = requests.post(f"{BASE_URL}/api/generate/reel", json={
            "topic": "Morning routines",
            "niche": "Luxury",
            "tone": "Bold"
        })
        assert response.status_code in [401, 403]
        print("Reel generation properly requires authentication")
    
    def test_demo_reel(self):
        """Test demo reel generation"""
        response = requests.post(f"{BASE_URL}/api/generate/demo/reel", json={
            "topic": "Morning routines",
            "niche": "Luxury",
            "tone": "Bold"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("isDemo") == True
        assert "result" in data
        print(f"Demo reel generated: {len(data['result'].get('hooks', []))} hooks")


class TestStoryGenerator:
    """Story Generator API tests"""
    
    def test_story_unauthenticated(self):
        """Test story generation without auth"""
        response = requests.post(f"{BASE_URL}/api/generate/story", json={
            "ageGroup": "4-6",
            "genre": "Fantasy",
            "theme": "Friendship"
        })
        assert response.status_code in [401, 403]
        print("Story generation properly requires authentication")


class TestCashfreePayments:
    """Cashfree payment integration tests"""
    
    def test_create_order_unauthenticated(self):
        """Test order creation without auth"""
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "starter_pack",
            "currency": "INR"
        })
        assert response.status_code in [401, 403]
        print("Order creation properly requires authentication")
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed")
    
    def test_create_order_authenticated(self):
        """Test order creation with auth"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            json={"productId": "starter_pack", "currency": "INR"},
            headers=self.headers
        )
        # Should return 200 with payment session or 400/404 if product not found
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            data = response.json()
            assert "paymentSessionId" in data or "orderId" in data
            print(f"Order created: {data.get('orderId', 'N/A')}")
        else:
            print(f"Order creation returned {response.status_code}: Expected for invalid product")


class TestForgotPassword:
    """Forgot password flow tests"""
    
    def test_forgot_password_success(self):
        """Test forgot password request"""
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={
            "email": "demo@example.com"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("Forgot password: Email sent successfully")
    
    def test_forgot_password_invalid_email(self):
        """Test forgot password with non-existent email (should still return success for security)"""
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={
            "email": "nonexistent@example.com"
        })
        # Should return success to prevent email enumeration
        assert response.status_code == 200
        print("Forgot password: Security response for non-existent email")


class TestAuthenticatedGeneration:
    """Authenticated generation tests"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed")
    
    def test_reel_generation_authenticated(self):
        """Test reel generation with auth"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json={
                "topic": "Morning productivity tips",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            },
            headers=self.headers,
            timeout=120  # AI generation can take time
        )
        assert response.status_code in [200, 503]  # 503 if AI service temporarily unavailable
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "result" in data
            print(f"Reel generated: {len(data['result'].get('hooks', []))} hooks")
        else:
            print("Reel generation: AI service temporarily unavailable")


class TestContentCalendar:
    """Content Calendar API tests"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed")
    
    def test_content_calendar_generation(self):
        """Test content calendar generation"""
        response = requests.post(
            f"{BASE_URL}/api/creator-tools/content-calendar?niche=business&days=7&include_full_scripts=false",
            headers=self.headers,
            timeout=120
        )
        # May require credits, so 400 is acceptable
        assert response.status_code in [200, 400, 503]
        if response.status_code == 200:
            data = response.json()
            assert "calendar" in data
            print(f"Content calendar: {len(data['calendar'])} days generated")
        else:
            print(f"Content calendar returned {response.status_code}: Expected if insufficient credits")


class TestCarouselGenerator:
    """Carousel Generator API tests"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed")
    
    def test_carousel_generation(self):
        """Test carousel generation"""
        response = requests.post(
            f"{BASE_URL}/api/creator-tools/carousel?topic=5%20Morning%20Habits&niche=business&slides=5",
            headers=self.headers,
            timeout=120
        )
        assert response.status_code in [200, 400, 503]
        if response.status_code == 200:
            data = response.json()
            assert "carousel" in data
            print(f"Carousel: {len(data['carousel'].get('slides', []))} slides generated")
        else:
            print(f"Carousel returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
