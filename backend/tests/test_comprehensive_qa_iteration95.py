"""
Comprehensive QA Testing - Iteration 95
Testing all critical API endpoints and features
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://create-share-remix.preview.emergentagent.com')

class TestHealthAndAuth:
    """Health check and authentication tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")

    def test_login_admin(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] in ["ADMIN", "admin"]
        print(f"✓ Admin login successful: {data['user']['email']}")
        return data["token"]

    def test_login_demo_user(self):
        """Test demo user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"✓ Demo user login successful: {data['user']['email']}")
        return data["token"]

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 400]
        print("✓ Invalid login rejected correctly")


class TestWalletAndCredits:
    """Wallet and credits tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]

    def test_wallet_balance(self, admin_token):
        """Test wallet balance endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "availableCredits" in data or "balanceCredits" in data
        credits = data.get("availableCredits", data.get("balanceCredits", 0))
        print(f"✓ Wallet balance: {credits}")


class TestNewRebuiltFeatures:
    """Test new rebuilt feature endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]

    def test_story_episode_creator_preview(self, admin_token):
        """Test Story Episode Creator preview endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/story-episode-creator/preview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "episodes" in data
        print(f"✓ Story Episode Creator preview: {len(data.get('episodes', []))} episodes")

    def test_content_challenge_planner_preview(self, admin_token):
        """Test Content Challenge Planner preview endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/content-challenge-planner/preview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "daily_plans" in data
        print(f"✓ Content Challenge Planner preview: {len(data.get('daily_plans', []))} days")

    def test_caption_rewriter_preview(self, admin_token):
        """Test Caption Rewriter Pro preview endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/caption-rewriter-pro/preview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        print(f"✓ Caption Rewriter preview: {len(data.get('results', {}))} tones")


class TestBlueprintLibrary:
    """Test Blueprint Library endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]

    def test_blueprint_library_products(self, admin_token):
        """Test Blueprint Library products endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/blueprint-library/products", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data or isinstance(data, list)
        print(f"✓ Blueprint Library products loaded")


class TestAdminSecurity:
    """Test Admin Security Dashboard endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]

    def test_security_stats(self, admin_token):
        """Test security stats endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/security/ip/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Security stats: {data}")

    def test_security_blocked_ips(self, admin_token):
        """Test blocked IPs endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/security/ip/blocked", headers=headers)
        assert response.status_code == 200
        print("✓ Blocked IPs endpoint working")


class TestAdminAccess:
    """Test admin-only access control"""
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        return response.json()["token"]

    def test_non_admin_denied_security_stats(self, demo_token):
        """Test non-admin cannot access security stats"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/security/ip/stats", headers=headers)
        assert response.status_code == 403
        print("✓ Non-admin correctly denied access to security stats")

    def test_non_admin_denied_admin_audit(self, demo_token):
        """Test non-admin cannot access admin audit logs"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/audit/logs", headers=headers)
        assert response.status_code == 403
        print("✓ Non-admin correctly denied access to audit logs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
