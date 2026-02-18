"""
Comprehensive QA Test Suite for CreatorStudio AI
Tests both User and Admin flows end-to-end
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestHealthEndpoints:
    """Health check endpoints - run first"""
    
    def test_health_main(self):
        """Test main health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        
    def test_health_live(self):
        """Test liveness probe"""
        response = requests.get(f"{BASE_URL}/api/health/live")
        assert response.status_code == 200
        
    def test_health_ready(self):
        """Test readiness probe"""
        response = requests.get(f"{BASE_URL}/api/health/ready")
        assert response.status_code == 200


class TestAuthenticationFlows:
    """Authentication endpoint tests"""
    
    def test_login_demo_user_success(self):
        """Test demo user login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == DEMO_USER["email"]
        
    def test_login_admin_user_success(self):
        """Test admin user login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"].upper() == "ADMIN"
        
    def test_login_invalid_password(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_USER["email"],
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401
        
    def test_login_invalid_email(self):
        """Test login with non-existent email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 401
        
    def test_login_empty_fields(self):
        """Test login with empty fields"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "",
            "password": ""
        })
        assert response.status_code in [400, 401, 422]
        
    def test_get_me_without_auth(self):
        """Test /me endpoint without authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        
    def test_get_me_with_auth(self):
        """Test /me endpoint with valid token"""
        # Login first
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        
        # Get user info
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == DEMO_USER["email"]


class TestSignupFlow:
    """Signup/Registration tests"""
    
    def test_signup_invalid_email(self):
        """Test signup with invalid email format"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "invalid-email",
            "password": "Password123!",
            "name": "Test User"
        })
        assert response.status_code in [400, 422]
        
    def test_signup_weak_password(self):
        """Test signup with weak password"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "test_weak@example.com",
            "password": "123",
            "name": "Test User"
        })
        assert response.status_code == 400
        
    def test_signup_existing_email(self):
        """Test signup with already registered email"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": DEMO_USER["email"],
            "password": "Password123!",
            "name": "Test User"
        })
        assert response.status_code == 400


class TestCreditsEndpoints:
    """Credits and billing endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_credits_balance(self, auth_headers):
        """Test getting credit balance"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert isinstance(data["credits"], (int, float))
        
    def test_get_credits_ledger(self, auth_headers):
        """Test getting credit transaction history"""
        response = requests.get(f"{BASE_URL}/api/credits/ledger", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "ledger" in data or "transactions" in data or isinstance(data, list)


class TestPaymentsEndpoints:
    """Payment related endpoints"""
    
    def test_get_products(self):
        """Test getting available products/plans"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) > 0
        
    def test_payments_health(self):
        """Test payment gateway health"""
        response = requests.get(f"{BASE_URL}/api/payments/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("healthy") == True or data.get("status") == "healthy"
        
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
        
    def test_payment_history(self, auth_headers):
        """Test getting payment history"""
        response = requests.get(f"{BASE_URL}/api/payments/history", headers=auth_headers)
        assert response.status_code == 200


class TestGenStudioEndpoints:
    """GenStudio AI generation endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_genstudio_dashboard(self, auth_headers):
        """Test GenStudio dashboard data"""
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data or "costs" in data
        
    def test_genstudio_templates(self, auth_headers):
        """Test getting prompt templates"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data


class TestCreatorProEndpoints:
    """Creator Pro AI tools endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_creator_pro_costs(self, auth_headers):
        """Test getting feature costs"""
        response = requests.get(f"{BASE_URL}/api/creator-pro/costs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "costs" in data
        
    def test_bio_generator(self, auth_headers):
        """Test AI bio generator"""
        response = requests.post(
            f"{BASE_URL}/api/creator-pro/bio-generator",
            headers=auth_headers,
            json={
                "niche": "tech",
                "tone": "professional",
                "platform": "instagram"
            }
        )
        # May return 200 or 402 (insufficient credits)
        assert response.status_code in [200, 402]
        
    def test_hook_analyzer(self, auth_headers):
        """Test AI hook analyzer"""
        response = requests.post(
            f"{BASE_URL}/api/creator-pro/hook-analyzer",
            headers=auth_headers,
            json={"hook": "You won't believe what happened next!"}
        )
        assert response.status_code in [200, 402]
        
    def test_caption_generator(self, auth_headers):
        """Test AI caption generator"""
        response = requests.post(
            f"{BASE_URL}/api/creator-pro/caption-generator",
            headers=auth_headers,
            json={
                "topic": "morning routine",
                "tone": "casual",
                "platform": "tiktok"
            }
        )
        assert response.status_code in [200, 402]


class TestTwinFinderEndpoints:
    """TwinFinder face lookalike endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_twinfinder_costs(self, auth_headers):
        """Test getting TwinFinder costs"""
        response = requests.get(f"{BASE_URL}/api/twinfinder/costs", headers=auth_headers)
        assert response.status_code == 200
        
    def test_twinfinder_celebrities(self, auth_headers):
        """Test getting celebrity database"""
        response = requests.get(f"{BASE_URL}/api/twinfinder/celebrities", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "celebrities" in data
        
    def test_twinfinder_dashboard(self, auth_headers):
        """Test TwinFinder dashboard"""
        response = requests.get(f"{BASE_URL}/api/twinfinder/dashboard", headers=auth_headers)
        assert response.status_code == 200


class TestStoryToolsEndpoints:
    """Story generation and PDF tools"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_printable_books(self, auth_headers):
        """Test getting user's printable books"""
        response = requests.get(f"{BASE_URL}/api/story-tools/printable-books", headers=auth_headers)
        assert response.status_code == 200
        
    def test_get_worksheets(self, auth_headers):
        """Test getting user's worksheets"""
        response = requests.get(f"{BASE_URL}/api/story-tools/worksheets", headers=auth_headers)
        assert response.status_code == 200


class TestGenerationsEndpoints:
    """Content generation endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_generations(self, auth_headers):
        """Test getting user generations"""
        response = requests.get(f"{BASE_URL}/api/generate/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "generations" in data


class TestAdminEndpoints:
    """Admin dashboard and analytics endpoints"""
    
    @pytest.fixture
    def admin_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def user_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_admin_dashboard_with_admin(self, admin_headers):
        """Test admin dashboard access with admin user"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/dashboard",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        # Verify all expected sections
        assert "overview" in data["data"]
        assert "visitors" in data["data"]
        assert "satisfaction" in data["data"]
        assert "payments" in data["data"]
        
    def test_admin_dashboard_with_regular_user(self, user_headers):
        """Test admin dashboard access denied for regular user"""
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/dashboard",
            headers=user_headers
        )
        assert response.status_code == 403
        
    def test_admin_dashboard_without_auth(self):
        """Test admin dashboard access denied without auth"""
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard")
        assert response.status_code in [401, 403]
        
    def test_admin_users_list(self, admin_headers):
        """Test getting user list as admin"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/list",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        
    def test_admin_successful_payments(self, admin_headers):
        """Test getting successful payments"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/successful",
            headers=admin_headers
        )
        assert response.status_code == 200
        
    def test_admin_failed_payments(self, admin_headers):
        """Test getting failed payments"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/failed",
            headers=admin_headers
        )
        assert response.status_code == 200
        
    def test_admin_exceptions(self, admin_headers):
        """Test getting exception logs"""
        response = requests.get(
            f"{BASE_URL}/api/admin/exceptions/all",
            headers=admin_headers
        )
        assert response.status_code == 200
        
    def test_admin_feedback(self, admin_headers):
        """Test getting all feedback"""
        response = requests.get(
            f"{BASE_URL}/api/admin/feedback/all",
            headers=admin_headers
        )
        assert response.status_code == 200


class TestFeatureRequestsEndpoints:
    """Feature requests endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_feature_requests(self, auth_headers):
        """Test getting feature requests"""
        response = requests.get(f"{BASE_URL}/api/feature-requests/", headers=auth_headers)
        assert response.status_code == 200


class TestFeedbackEndpoints:
    """Feedback submission endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_submit_feedback(self, auth_headers):
        """Test submitting feedback"""
        response = requests.post(
            f"{BASE_URL}/api/feedback/",
            headers=auth_headers,
            json={
                "message": "Test feedback from QA",
                "rating": 5,
                "category": "general"
            }
        )
        assert response.status_code in [200, 201]


class TestContentVaultEndpoints:
    """Content vault storage endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_res.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_vault_items(self, auth_headers):
        """Test getting vault items"""
        response = requests.get(f"{BASE_URL}/api/content-vault/", headers=auth_headers)
        assert response.status_code == 200


class TestProtectedRouteAccess:
    """Test protected route access without authentication"""
    
    def test_credits_without_auth(self):
        """Credits endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code in [401, 403]
        
    def test_generations_without_auth(self):
        """Generations endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/generate/")
        assert response.status_code in [401, 403]
        
    def test_genstudio_without_auth(self):
        """GenStudio endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard")
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
