"""
Comprehensive A-Z QA Test Suite for CreatorStudio AI - Iteration 71
Tests all pages, forms, validations, and integrations using sync requests
"""
import pytest
import requests
import os
import time

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bugfix-preview-8.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
DEMO_CREDS = {"email": "demo@example.com", "password": "Password123!"}
INVALID_CREDS = {"email": "invalid@test.com", "password": "wrongpassword"}

class TestHealthAndBasics:
    """Basic health and connectivity tests"""
    
    def test_health_endpoint(self):
        """Health endpoint responds"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=30, allow_redirects=True)
        assert response.status_code in [200, 307]
        print(f"Health endpoint: {response.status_code}")
    
    def test_frontend_loads(self):
        """Frontend root loads"""
        response = requests.get(f"{BASE_URL}/", timeout=30)
        assert response.status_code == 200
        assert 'CreatorStudio' in response.text or 'root' in response.text
        print("Frontend loads successfully")


class TestLoginPage:
    """A) Login Page Tests - /login"""
    
    def test_login_page_loads(self):
        """Login page HTML loads"""
        response = requests.get(f"{BASE_URL}/login", timeout=30)
        assert response.status_code == 200
    
    def test_login_empty_email(self):
        """Email required validation"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "", "password": "testpass123"},
            timeout=30
        )
        assert response.status_code in [400, 422]
        print(f"Empty email: {response.status_code}")
    
    def test_login_invalid_email_formats(self):
        """Invalid email format validation"""
        invalid_emails = ["abc", "abc@", "@mail.com"]
        for email in invalid_emails:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": email, "password": "testpass123"},
                timeout=30
            )
            assert response.status_code in [400, 401, 422], f"Failed for email: {email}"
        print("Invalid emails rejected correctly")
    
    def test_login_empty_password(self):
        """Password required validation"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": ""},
            timeout=30
        )
        assert response.status_code in [400, 422]
        print(f"Empty password: {response.status_code}")
    
    def test_login_invalid_credentials(self):
        """Invalid credentials returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=INVALID_CREDS,
            timeout=30
        )
        assert response.status_code == 401
        print("Invalid credentials rejected with 401")
    
    def test_login_success_admin(self):
        """Successful admin login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_CREDS["email"]
        print(f"Admin login success - role: {data['user'].get('role', 'unknown')}")
    
    def test_login_success_demo(self):
        """Successful demo user login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=DEMO_CREDS,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print("Demo user login success")


class TestForgotPassword:
    """B) Reset Password Modal Tests"""
    
    def test_forgot_password_empty_email(self):
        """Email required"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": ""},
            timeout=30
        )
        assert response.status_code in [400, 422]
    
    def test_forgot_password_invalid_email(self):
        """Invalid email format"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "notanemail"},
            timeout=30
        )
        assert response.status_code in [400, 422]
    
    def test_forgot_password_success(self):
        """Always returns success (prevents enumeration)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "test@example.com"},
            timeout=30
        )
        assert response.status_code == 200
        print("Forgot password API working")


class TestSignup:
    """C) Signup Page Tests"""
    
    def test_signup_page_loads(self):
        """Signup page loads"""
        response = requests.get(f"{BASE_URL}/signup", timeout=30)
        assert response.status_code == 200
    
    def test_signup_empty_name(self):
        """Name required"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"name": "", "email": "test@test.com", "password": "Test123!@#"},
            timeout=30
        )
        assert response.status_code in [400, 422]
    
    def test_signup_empty_email(self):
        """Email required"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"name": "Test User", "email": "", "password": "Test123!@#"},
            timeout=30
        )
        assert response.status_code in [400, 422]
    
    def test_signup_weak_password(self):
        """Weak password rejected"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"name": "Test User", "email": "weak@test.com", "password": "weak"},
            timeout=30
        )
        assert response.status_code in [400, 422]
    
    def test_signup_duplicate_email(self):
        """Duplicate email rejected"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"name": "Test User", "email": ADMIN_CREDS["email"], "password": "Test123!@#"},
            timeout=30
        )
        assert response.status_code == 400


class TestProtectedRoutes:
    """D) Dashboard & Protected Routes"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=30)
        return response.json()["token"]
    
    @pytest.fixture
    def demo_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_CREDS, timeout=30)
        return response.json()["token"]
    
    def test_profile_requires_auth(self):
        """Profile endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/user/profile", timeout=30)
        assert response.status_code == 401
    
    def test_profile_with_auth(self, admin_token):
        """Profile accessible with auth"""
        response = requests.get(
            f"{BASE_URL}/api/user/profile",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        print(f"Profile loaded: {data['email']}")
    
    def test_credits_balance(self, admin_token):
        """Credits balance endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        assert "credits" in response.json()
        print(f"Credits: {response.json()['credits']}")


class TestReelGenerator:
    """E) Reel Generator Tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=30)
        return response.json()["token"]
    
    def test_reel_requires_auth(self):
        """Reel generation requires auth"""
        response = requests.post(
            f"{BASE_URL}/api/reels/generate",
            json={"topic": "test"},
            timeout=30
        )
        assert response.status_code == 401


class TestGenStudio:
    """G) GenStudio Tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=30)
        return response.json()["token"]
    
    def test_genstudio_history_requires_auth(self):
        """GenStudio history requires auth"""
        response = requests.get(f"{BASE_URL}/api/genstudio/history", timeout=30)
        assert response.status_code == 401
    
    def test_genstudio_history_with_auth(self, admin_token):
        """GenStudio history accessible"""
        response = requests.get(
            f"{BASE_URL}/api/genstudio/history",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        print("GenStudio history accessible")


class TestCreatorTools:
    """I) Creator Tools Tests"""
    
    def test_creator_tools_requires_auth(self):
        """Creator tools requires auth"""
        response = requests.post(
            f"{BASE_URL}/api/creator-tools/hashtags",
            json={"topic": "test"},
            timeout=30
        )
        assert response.status_code == 401


class TestComixAI:
    """J) Comix AI Tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=30)
        return response.json()["token"]
    
    def test_comix_styles(self, admin_token):
        """Comix styles endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/comix/styles",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        print(f"Comix styles: {len(data.get('styles', {}))}")
    
    def test_comix_jobs_list(self, admin_token):
        """Comix jobs list"""
        response = requests.get(
            f"{BASE_URL}/api/comix/jobs",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200


class TestGifMaker:
    """K) GIF Maker Tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=30)
        return response.json()["token"]
    
    def test_gif_emotions(self, admin_token):
        """GIF emotions endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/gif-maker/emotions",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "emotions" in data
        print(f"GIF emotions: {len(data.get('emotions', {}))}")
    
    def test_gif_jobs_list(self, admin_token):
        """GIF jobs list"""
        response = requests.get(
            f"{BASE_URL}/api/gif/jobs",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200


class TestAdminRoutes:
    """L) Admin Routes Tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=30)
        return response.json()["token"]
    
    @pytest.fixture
    def demo_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_CREDS, timeout=30)
        return response.json()["token"]
    
    def test_admin_analytics_requires_admin(self, demo_token):
        """Admin analytics requires admin role"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/dashboard",
            headers={"Authorization": f"Bearer {demo_token}"},
            timeout=30
        )
        assert response.status_code in [401, 403]
    
    def test_admin_analytics_with_admin(self, admin_token):
        """Admin analytics accessible"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        print("Admin analytics accessible")
    
    def test_admin_login_activity(self, admin_token):
        """Admin login activity"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        print("Admin login activity accessible")
    
    def test_admin_login_activity_stats(self, admin_token):
        """Admin login activity stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        print("Admin login stats accessible")


class TestBillingAndPayments:
    """H) Billing & Payments Tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=30)
        return response.json()["token"]
    
    def test_products_endpoint(self, admin_token):
        """Products list endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/cashfree/products",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        print(f"Products available: {len(data.get('products', {}))}")


class TestSecurityHeaders:
    """N) Security Tests"""
    
    def test_cors_preflight(self):
        """CORS preflight works"""
        response = requests.options(
            f"{BASE_URL}/api/auth/login",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST"
            },
            timeout=30
        )
        assert response.status_code in [200, 204, 307]
    
    def test_protected_without_auth(self):
        """Protected routes return 401"""
        protected_endpoints = [
            "/api/user/profile",
            "/api/credits/balance",
            "/api/genstudio/history",
            "/api/comix/jobs"
        ]
        for endpoint in protected_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
            assert response.status_code == 401, f"Endpoint {endpoint} should require auth"
        print("All protected routes require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
