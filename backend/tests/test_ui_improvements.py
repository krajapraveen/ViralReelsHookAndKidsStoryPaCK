"""
Test Suite for CreatorStudio AI UI/UX Improvements and Payment Integration
Tests: Admin login, Story Generator, Reel Generator, Share modal, Cashfree payments
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://urgent-bugfix-1.preview.emergentagent.com')

class TestAdminCredentials:
    """Test admin login with new credentials"""
    
    def test_admin_login_success(self):
        """Admin should be able to login with new credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "ADMIN"
        assert data["user"]["email"] == "admin@creatorstudio.ai"
        print(f"Admin login successful, credits: {data['user']['credits']}")

    def test_demo_user_login(self):
        """Demo user should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "demo@example.com"


class TestCashfreePaymentGateway:
    """Test Cashfree payment gateway integration"""
    
    def test_cashfree_health_check(self):
        """Cashfree health endpoint should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["gateway"] == "cashfree"
        assert data["configured"] == True
        assert data["environment"] == "production"
        print(f"Cashfree gateway: {data}")

    def test_cashfree_products(self):
        """Cashfree products endpoint should return available products"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert data["gateway"] == "cashfree"
        assert data["configured"] == True
        
        # Verify product structure
        products = data["products"]
        assert "starter" in products
        assert "creator" in products
        assert "pro" in products
        
        # Verify starter pack details
        starter = products["starter"]
        assert starter["name"] == "Starter Pack"
        assert starter["credits"] == 100
        assert starter["price"] == 499
        print(f"Found {len(products)} products")


class TestStoryGeneratorAPI:
    """Test Story Generator API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_story_generation_endpoint(self, auth_token):
        """Story generation endpoint should accept requests"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/generate/story", 
            headers=headers,
            json={
                "ageGroup": "4-6",
                "genre": "Fantasy",
                "theme": "Friendship",
                "sceneCount": 8
            }
        )
        # Should either succeed or return appropriate error
        assert response.status_code in [200, 201, 400, 402]
        print(f"Story generation response: {response.status_code}")


class TestReelGeneratorAPI:
    """Test Reel Generator API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_reel_generation_endpoint(self, auth_token):
        """Reel generation endpoint should accept requests"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/generate/reel", 
            headers=headers,
            json={
                "topic": "Morning routines of successful entrepreneurs",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            }
        )
        # Should either succeed or return appropriate error
        assert response.status_code in [200, 201, 400, 402]
        print(f"Reel generation response: {response.status_code}")


class TestCreditsAPI:
    """Test Credits API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_credits_balance(self, auth_token):
        """Credits balance endpoint should return user balance"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # API returns 'credits' field
        assert "credits" in data or "balance" in data
        credits = data.get("credits") or data.get("balance")
        print(f"Credits balance: {credits}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
