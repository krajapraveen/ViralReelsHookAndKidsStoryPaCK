"""
Backend API Tests for CreatorStudio AI - Refactored Modular Backend
Tests: Health, Auth, Credits, Creator Pro, TwinFinder, Admin, Payments
"""
import pytest
import requests
import os

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://legacy-user-fix.preview.emergentagent.com"

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestHealthEndpoints:
    """Health check endpoint tests"""
    
    def test_health_endpoint(self):
        """Test /api/health/ returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["version"] == "2.0.0"
        print(f"✓ Health check passed: {data}")
    
    def test_health_live(self):
        """Test /api/health/live liveness probe"""
        response = requests.get(f"{BASE_URL}/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        print(f"✓ Liveness probe passed: {data}")
    
    def test_health_ready(self):
        """Test /api/health/ready readiness probe"""
        response = requests.get(f"{BASE_URL}/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        print(f"✓ Readiness probe passed: {data}")


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_login_demo_user(self):
        """Test login with demo user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == DEMO_USER["email"]
        assert data["user"]["role"].lower() == "user"
        print(f"✓ Demo user login passed: {data['user']['email']}")
        return data["token"]
    
    def test_login_admin_user(self):
        """Test login with admin user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_USER["email"]
        assert data["user"]["role"].upper() == "ADMIN"
        print(f"✓ Admin user login passed: {data['user']['email']}, role: {data['user']['role']}")
        return data["token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_get_me_authenticated(self):
        """Test /api/auth/me with valid token"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_response.json()["token"]
        
        # Get user info
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == DEMO_USER["email"]
        print(f"✓ Get me endpoint passed: {data['email']}")
    
    def test_get_me_unauthenticated(self):
        """Test /api/auth/me without token returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        print("✓ Unauthenticated /me correctly rejected")


class TestCreditsEndpoints:
    """Credits API endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_get_balance_authenticated(self, auth_token):
        """Test /api/credits/balance with auth"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert isinstance(data["credits"], int)
        print(f"✓ Credits balance: {data['credits']}")
    
    def test_get_balance_unauthenticated(self):
        """Test /api/credits/balance without auth returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code in [401, 403]
        print("✓ Unauthenticated credits balance correctly rejected")
    
    def test_get_ledger(self, auth_token):
        """Test /api/credits/ledger returns transaction history"""
        response = requests.get(
            f"{BASE_URL}/api/credits/ledger",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "ledger" in data
        assert "total" in data
        print(f"✓ Credits ledger: {data['total']} transactions")


class TestCreatorProEndpoints:
    """Creator Pro Tools API tests"""
    
    def test_get_costs(self):
        """Test /api/creator-pro/costs returns feature costs"""
        response = requests.get(f"{BASE_URL}/api/creator-pro/costs")
        assert response.status_code == 200
        data = response.json()
        assert "costs" in data
        assert "features" in data
        # Verify expected features exist
        expected_features = ["hook_analyzer", "swipe_file", "bio_generator", "caption_generator"]
        for feature in expected_features:
            assert feature in data["costs"], f"Missing feature: {feature}"
        print(f"✓ Creator Pro costs: {len(data['costs'])} features")
        print(f"  Features: {list(data['costs'].keys())}")
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_hook_analyzer(self, auth_token):
        """Test hook analyzer endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/creator-pro/hook-analyzer",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"hook": "This secret trick will change your life forever", "niche": "motivation"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "analysis" in data
        assert "totalScore" in data["analysis"]
        print(f"✓ Hook analyzer: score {data['analysis']['totalScore']}")
    
    def test_caption_generator(self, auth_token):
        """Test caption generator endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/creator-pro/caption-generator",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"topic": "productivity", "tone": "engaging", "platform": "instagram"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "captions" in data
        print(f"✓ Caption generator: {len(data['captions'])} captions generated")


class TestTwinFinderEndpoints:
    """TwinFinder API tests"""
    
    def test_get_costs(self):
        """Test /api/twinfinder/costs returns feature costs"""
        response = requests.get(f"{BASE_URL}/api/twinfinder/costs")
        assert response.status_code == 200
        data = response.json()
        assert "costs" in data
        assert "features" in data
        # Verify expected costs
        assert "analyze_face" in data["costs"]
        assert "celebrity_match" in data["costs"]
        print(f"✓ TwinFinder costs: {data['costs']}")
    
    def test_get_celebrities(self):
        """Test /api/twinfinder/celebrities returns celebrity list"""
        response = requests.get(f"{BASE_URL}/api/twinfinder/celebrities")
        assert response.status_code == 200
        data = response.json()
        assert "celebrities" in data
        assert "total" in data
        assert data["total"] > 0
        print(f"✓ TwinFinder celebrities: {data['total']} in database")
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_dashboard(self, auth_token):
        """Test /api/twinfinder/dashboard returns dashboard data"""
        response = requests.get(
            f"{BASE_URL}/api/twinfinder/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert "costs" in data
        print(f"✓ TwinFinder dashboard: credits={data['credits']}")


class TestAdminEndpoints:
    """Admin API tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get auth token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        return response.json()["token"]
    
    @pytest.fixture
    def demo_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_admin_dashboard_with_admin(self, admin_token):
        """Test /api/admin/analytics/dashboard with admin user"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "generations" in data
        assert "revenue" in data
        print(f"✓ Admin dashboard: {data['users']['total']} users, {data['generations']['total']} generations")
    
    def test_admin_dashboard_with_non_admin(self, demo_token):
        """Test /api/admin/analytics/dashboard with non-admin user returns 403"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/dashboard",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 403
        print("✓ Admin dashboard correctly rejected non-admin user")
    
    def test_admin_dashboard_unauthenticated(self):
        """Test /api/admin/analytics/dashboard without auth returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard")
        assert response.status_code in [401, 403]
        print("✓ Admin dashboard correctly rejected unauthenticated request")


class TestPaymentsEndpoints:
    """Payments API tests"""
    
    def test_get_products(self):
        """Test /api/payments/products returns available products"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "razorpayKeyId" in data
        # Verify expected products
        expected_products = ["starter", "creator", "pro"]
        for product in expected_products:
            assert product in data["products"], f"Missing product: {product}"
        print(f"✓ Payment products: {list(data['products'].keys())}")
    
    def test_payments_health(self):
        """Test /api/payments/health returns gateway status"""
        response = requests.get(f"{BASE_URL}/api/payments/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["gateway"] == "razorpay"
        print(f"✓ Payments health: {data}")
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_payment_history(self, auth_token):
        """Test /api/payments/history returns user payment history"""
        response = requests.get(
            f"{BASE_URL}/api/payments/history",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        assert "total" in data
        print(f"✓ Payment history: {data['total']} orders")


# Note: Root endpoints (/ and /health) return frontend HTML, not backend JSON
# This is expected behavior as the frontend is served at the root


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
