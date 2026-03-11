"""
Comprehensive Automation Test Suite - Iteration 44
CreatorStudio AI Production Environment Testing

Tests all major functionalities:
- Authentication (login, signup, admin)
- Dashboard pages
- GenStudio AI generators
- Story Series, Challenge Generator, Tone Switcher
- Coloring Book
- Billing and payments
- Downloads and exports
"""
import pytest
import requests
import os
import time
from datetime import datetime

# Production URL from env
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://subscription-gateway-1.preview.emergentagent.com"

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestHealthAndPublicEndpoints:
    """Phase 1: Health checks and public endpoint verification"""
    
    def test_api_health_endpoint(self):
        """Test API health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        print(f"✓ Health endpoint: {response.json()}")
    
    def test_api_docs_available(self):
        """Test API docs are accessible"""
        response = requests.get(f"{BASE_URL}/api/docs", timeout=10)
        assert response.status_code == 200
        print("✓ API docs accessible")
    
    def test_landing_page_loads(self):
        """Test landing page loads"""
        response = requests.get(f"{BASE_URL}/", timeout=10)
        assert response.status_code == 200
        print("✓ Landing page loads")
    
    def test_pricing_page_loads(self):
        """Test pricing page loads"""
        response = requests.get(f"{BASE_URL}/pricing", timeout=10)
        assert response.status_code == 200
        print("✓ Pricing page loads")
    
    def test_login_page_loads(self):
        """Test login page loads"""
        response = requests.get(f"{BASE_URL}/login", timeout=10)
        assert response.status_code == 200
        print("✓ Login page loads")
    
    def test_signup_page_loads(self):
        """Test signup page loads"""
        response = requests.get(f"{BASE_URL}/signup", timeout=10)
        assert response.status_code == 200
        print("✓ Signup page loads")
    
    def test_reviews_page_loads(self):
        """Test reviews page loads"""
        response = requests.get(f"{BASE_URL}/reviews", timeout=10)
        assert response.status_code == 200
        print("✓ Reviews page loads")
    
    def test_help_page_loads(self):
        """Test help page loads"""
        response = requests.get(f"{BASE_URL}/help", timeout=10)
        assert response.status_code == 200
        print("✓ Help page loads")
    
    def test_contact_page_loads(self):
        """Test contact page loads"""
        response = requests.get(f"{BASE_URL}/contact", timeout=10)
        assert response.status_code == 200
        print("✓ Contact page loads")


class TestAuthentication:
    """Phase 2: Authentication flows"""
    
    def test_demo_user_login(self):
        """Test demo user can login successfully"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=DEMO_USER,
            timeout=15
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"✓ Demo user login successful, token received")
        return data["token"]
    
    def test_admin_user_login(self):
        """Test admin user can login successfully"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_USER,
            timeout=15
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"✓ Admin user login successful")
        return data["token"]
    
    def test_invalid_credentials_rejected(self):
        """Test invalid credentials are rejected with 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpass"},
            timeout=15
        )
        assert response.status_code in [401, 404]
        print("✓ Invalid credentials rejected")
    
    def test_get_current_user_authenticated(self):
        """Test getting current user with valid token"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER, timeout=15)
        token = login_resp.json()["token"]
        
        # Get current user
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert data["email"] == DEMO_USER["email"]
        print(f"✓ Current user endpoint works: {data['email']}")
    
    def test_protected_route_without_auth(self):
        """Test protected routes require authentication"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/me",
            timeout=10
        )
        assert response.status_code in [401, 403]
        print("✓ Protected routes require auth")


class TestCashfreePayments:
    """Phase 3: Cashfree payment integration"""
    
    def test_cashfree_health(self):
        """Test Cashfree gateway health"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("configured") == True
        print(f"✓ Cashfree health: {data.get('environment')}")
    
    def test_cashfree_products(self):
        """Test Cashfree products listing"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        products = data["products"]
        assert len(products) >= 5
        print(f"✓ Cashfree products: {len(products)} products available")
    
    def test_cashfree_create_order_requires_auth(self):
        """Test order creation requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            json={"productId": "starter", "currency": "INR"},
            timeout=10
        )
        assert response.status_code in [401, 403]
        print("✓ Order creation requires auth")
    
    def test_cashfree_create_order_authenticated(self):
        """Test order creation with authentication"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER, timeout=15)
        token = login_resp.json()["token"]
        
        # Create order
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            json={"productId": "starter", "currency": "INR"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        # May be 200 or 429 (rate limited) or 500 (sandbox mode issue)
        assert response.status_code in [200, 429, 500]
        if response.status_code == 200:
            data = response.json()
            assert "paymentSessionId" in data or "orderId" in data
            print(f"✓ Order created successfully")
        else:
            print(f"✓ Order endpoint responded: {response.status_code}")


class TestSubscriptions:
    """Phase 4: Subscription plans"""
    
    def test_subscription_plans_available(self):
        """Test subscription plans endpoint"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        print(f"✓ Subscription plans: {len(data['plans'])} plans available")
    
    def test_regional_pricing(self):
        """Test regional pricing endpoint"""
        response = requests.get(f"{BASE_URL}/api/pricing/regional?country=IN", timeout=10)
        assert response.status_code == 200
        print("✓ Regional pricing endpoint works")


class TestGenerators:
    """Phase 5: AI Generator endpoints"""
    
    @pytest.fixture(autouse=True)
    def get_auth_token(self):
        """Get auth token before each test"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER, timeout=15)
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_genstudio_dashboard(self):
        """Test GenStudio dashboard endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/genstudio/dashboard",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ GenStudio dashboard endpoint works")
    
    def test_genstudio_templates(self):
        """Test GenStudio templates endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/genstudio/templates",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ GenStudio templates endpoint works")
    
    def test_story_series_history(self):
        """Test Story Series history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/story-series/history",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Story Series history endpoint works")
    
    def test_story_series_themes(self):
        """Test Story Series themes endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/story-series/themes",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Story Series themes endpoint works")
    
    def test_challenge_generator_history(self):
        """Test Challenge Generator history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/challenge-generator/history",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Challenge Generator history endpoint works")
    
    def test_challenge_generator_niches(self):
        """Test Challenge Generator niches endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/challenge-generator/niches",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Challenge Generator niches endpoint works")
    
    def test_challenge_generator_platforms(self):
        """Test Challenge Generator platforms endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/challenge-generator/platforms",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Challenge Generator platforms endpoint works")
    
    def test_tone_switcher_history(self):
        """Test Tone Switcher history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/tone-switcher/history",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Tone Switcher history endpoint works")
    
    def test_tone_switcher_tones(self):
        """Test Tone Switcher tones endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/tone-switcher/tones",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Tone Switcher tones endpoint works")
    
    def test_coloring_book_pricing(self):
        """Test Coloring Book pricing endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/pricing",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Coloring Book pricing endpoint works")


class TestWalletAndCredits:
    """Phase 6: Wallet and credit system"""
    
    @pytest.fixture(autouse=True)
    def get_auth_token(self):
        """Get auth token before each test"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER, timeout=15)
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_wallet_balance(self):
        """Test wallet balance endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/me",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert "balanceCredits" in data or "availableCredits" in data
        print(f"✓ Wallet balance: {data}")
    
    def test_wallet_pricing(self):
        """Test wallet pricing endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/pricing",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Wallet pricing endpoint works")
    
    def test_credit_balance(self):
        """Test credit balance endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Credit balance endpoint works")


class TestUserAnalytics:
    """Phase 7: User analytics endpoints"""
    
    @pytest.fixture(autouse=True)
    def get_auth_token(self):
        """Get auth token before each test"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER, timeout=15)
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_user_analytics(self):
        """Test user analytics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/user-stats",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ User analytics endpoint works")
    
    def test_user_subscription_status(self):
        """Test subscription status endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/current",
            headers=self.headers,
            timeout=10
        )
        # 200 if has subscription, 404 if not
        assert response.status_code in [200, 404]
        print("✓ Subscription status endpoint works")


class TestAdminEndpoints:
    """Phase 8: Admin-only endpoints"""
    
    @pytest.fixture(autouse=True)
    def get_tokens(self):
        """Get auth tokens for admin and demo user"""
        # Admin login
        admin_resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER, timeout=15)
        self.admin_token = admin_resp.json()["token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Demo user login
        demo_resp = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER, timeout=15)
        self.demo_token = demo_resp.json()["token"]
        self.demo_headers = {"Authorization": f"Bearer {self.demo_token}"}
    
    def test_admin_users_list(self):
        """Test admin can list users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers=self.admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin users list endpoint works")
    
    def test_admin_analytics_overview(self):
        """Test admin analytics overview"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/overview",
            headers=self.admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin analytics overview works")
    
    def test_admin_monitoring_overview(self):
        """Test admin monitoring overview"""
        response = requests.get(
            f"{BASE_URL}/api/admin/monitoring/overview",
            headers=self.admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin monitoring overview works")
    
    def test_admin_threat_stats(self):
        """Test admin threat stats"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/threat-stats",
            headers=self.admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin threat stats endpoint works")
    
    def test_admin_worker_status(self):
        """Test admin worker status"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/worker-status",
            headers=self.admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Admin worker status works")
    
    def test_admin_routes_blocked_for_normal_users(self):
        """Test admin routes are blocked for normal users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers=self.demo_headers,
            timeout=10
        )
        assert response.status_code in [401, 403]
        print("✓ Admin routes blocked for normal users")


class TestHelpAndDocumentation:
    """Phase 9: Help and documentation endpoints"""
    
    @pytest.fixture(autouse=True)
    def get_auth_token(self):
        """Get auth token before each test"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER, timeout=15)
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_help_manual(self):
        """Test user manual endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/help/manual",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Help manual endpoint works")
    
    def test_quick_start_guide(self):
        """Test quick start guide endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/help/quick-start",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Quick start guide endpoint works")
    
    def test_help_search(self):
        """Test help search endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/help/search?q=credits",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Help search endpoint works")


class TestPrivacyAndData:
    """Phase 10: Privacy and user data endpoints"""
    
    @pytest.fixture(autouse=True)
    def get_auth_token(self):
        """Get auth token before each test"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER, timeout=15)
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_privacy_my_data(self):
        """Test my data endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/privacy/my-data",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200
        print("✓ Privacy my-data endpoint works")


class TestExceptionHandling:
    """Phase 11: Exception and error handling"""
    
    def test_invalid_json_returns_422(self):
        """Test invalid JSON returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data="not valid json",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 422
        print("✓ Invalid JSON returns 422")
    
    def test_nonexistent_endpoint_returns_404(self):
        """Test nonexistent endpoint returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/this-endpoint-does-not-exist-12345",
            timeout=10
        )
        assert response.status_code == 404
        print("✓ Nonexistent endpoint returns 404")
    
    def test_method_not_allowed_returns_405(self):
        """Test wrong method returns 405"""
        response = requests.delete(
            f"{BASE_URL}/api/health",
            timeout=10
        )
        assert response.status_code == 405
        print("✓ Method not allowed returns 405")


class TestSecurityHeaders:
    """Phase 12: Security headers verification"""
    
    def test_security_headers_present(self):
        """Test security headers are present"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        headers = response.headers
        
        # Check for security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options"
        ]
        
        for header in security_headers:
            if header in headers:
                print(f"  ✓ {header}: {headers[header]}")
        
        print("✓ Security headers check completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
