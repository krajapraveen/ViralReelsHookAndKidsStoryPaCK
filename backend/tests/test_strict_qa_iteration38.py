"""
Strict QA Test Suite - Iteration 38
Tests all critical APIs and flows for CreatorStudio AI
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-to-video-35.preview.emergentagent.com').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestHealthEndpoints:
    """Health check tests"""
    
    def test_health_endpoint(self):
        """Test main health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        print(f"Health check passed - version: {data.get('version')}")


class TestAuthenticationFlow:
    """Authentication tests"""
    
    def test_login_success_demo_user(self):
        """Test login with demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"Demo user login successful")
        return data["token"]
    
    def test_login_success_admin_user(self):
        """Test login with admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"Admin user login successful")
        return data["token"]
    
    def test_login_failure_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "wrong_password"
        })
        assert response.status_code in [401, 400]
        print(f"Invalid credentials correctly rejected")


class TestCreditsAndWallet:
    """Credits and wallet tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_get_credits_balance(self, auth_token):
        """Test getting credit balance"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        print(f"Credits balance: {data['balance']}")
    
    def test_get_wallet(self, auth_token):
        """Test getting wallet details"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "balanceCredits" in data or "balance" in data
        print(f"Wallet data retrieved successfully")
    
    def test_get_wallet_ledger(self, auth_token):
        """Test getting wallet ledger"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/ledger", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data or isinstance(data, list)
        print(f"Wallet ledger retrieved")


class TestGenStudioAPI:
    """GenStudio API tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_genstudio_dashboard(self, auth_token):
        """Test GenStudio dashboard endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"GenStudio dashboard data retrieved")
    
    def test_genstudio_templates(self, auth_token):
        """Test GenStudio templates endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/genstudio/templates", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        print(f"GenStudio templates: {len(data['templates'])} templates available")
    
    def test_genstudio_history(self, auth_token):
        """Test GenStudio history endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/genstudio/history", headers=headers)
        assert response.status_code == 200
        print(f"GenStudio history retrieved")


class TestReelGeneration:
    """Reel generation tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_reel_generation_empty_topic_rejected(self, auth_token):
        """Test that empty topic is rejected"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/generate/reel", headers=headers, json={
            "topic": "",
            "niche": "General",
            "tone": "Bold",
            "duration": "30s",
            "goal": "Engagement",
            "language": "English"
        })
        assert response.status_code == 422
        print("Empty topic correctly rejected with 422")
    
    def test_demo_reel_generation(self):
        """Test demo reel generation (no auth)"""
        response = requests.post(f"{BASE_URL}/api/generate/demo/reel", json={
            "topic": "Digital Marketing Tips",
            "niche": "Business",
            "tone": "Bold",
            "duration": "30s",
            "goal": "Engagement",
            "language": "English"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("isDemo") == True
        assert "result" in data
        print(f"Demo reel generation successful")


class TestStoryGeneration:
    """Story generation tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_get_generations_history(self, auth_token):
        """Test getting generation history"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/generate/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "generations" in data
        print(f"Generation history: {data['total']} generations")


class TestBillingAndPayments:
    """Billing and payment tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_get_cashfree_products(self):
        """Test getting Cashfree products"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        print(f"Cashfree products: {len(data['products'])} products available")
    
    def test_get_payment_history(self, auth_token):
        """Test getting payment history"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/payments/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "payments" in data
        print(f"Payment history: {data.get('total', 0)} payments")


class TestProfileAndPrivacy:
    """Profile and privacy tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_get_profile(self, auth_token):
        """Test getting user profile"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        print(f"Profile retrieved for: {data['email']}")
    
    def test_privacy_export(self, auth_token):
        """Test privacy data export"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/privacy/export", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Privacy export successful")


class TestStoryTools:
    """Story tools tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_get_worksheets(self, auth_token):
        """Test getting worksheets"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-tools/worksheets", headers=headers)
        assert response.status_code == 200
        print(f"Worksheets endpoint accessible")
    
    def test_get_printable_books(self, auth_token):
        """Test getting printable books"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-tools/printable-books", headers=headers)
        assert response.status_code == 200
        print(f"Printable books endpoint accessible")


class TestAdminEndpoints:
    """Admin endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        return response.json()["token"]
    
    def test_admin_dashboard(self, admin_token):
        """Test admin dashboard access"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        print(f"Admin dashboard accessible")
    
    def test_admin_users_list(self, admin_token):
        """Test admin users list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Admin users list: {len(data.get('users', []))} users")
    
    def test_non_admin_blocked(self):
        """Test that non-admin users cannot access admin endpoints"""
        demo_response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        demo_token = demo_response.json()["token"]
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        assert response.status_code in [401, 403]
        print(f"Non-admin correctly blocked from admin endpoints")


class TestCreatorTools:
    """Creator tools tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_creator_tools_accessible(self, auth_token):
        """Test creator tools endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/creator-tools/calendar/generate", headers=headers)
        # Either 200 or 405 (if it requires POST)
        assert response.status_code in [200, 405, 422]
        print(f"Creator tools endpoint status: {response.status_code}")


class TestWalletJobs:
    """Wallet job tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_list_jobs(self, auth_token):
        """Test listing wallet jobs"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/jobs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        print(f"Wallet jobs: {len(data['jobs'])} jobs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
