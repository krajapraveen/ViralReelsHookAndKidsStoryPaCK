"""
CreatorStudio AI API Tests
Tests for authentication, credits, generation, contact, and payment endpoints
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://video-job-queue-1.preview.emergentagent.com')

class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "email" in data
        assert data["email"] == "demo@example.com"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code in [400, 401, 403]
    
    def test_register_new_user(self):
        """Test new user registration gives 54 credits"""
        unique_email = f"test_{int(time.time())}@example.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "password123",
            "name": "Test User"
        })
        assert response.status_code in [200, 201]
        data = response.json()
        assert "token" in data
        
        # Verify 54 credits
        token = data["token"]
        credits_response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert credits_response.status_code == 200
        credits_data = credits_response.json()
        assert credits_data["balance"] == 54.0
        assert credits_data["isFreeTier"] == True
    
    def test_get_current_user(self):
        """Test getting current user info"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "password123"
        })
        token = login_response.json()["token"]
        
        # Get current user
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "name" in data
        assert "id" in data


class TestCreditsEndpoints:
    """Credits endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    def test_get_credits_balance(self, auth_token):
        """Test getting credit balance"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "isFreeTier" in data
        assert "hasPurchased" in data


class TestGenerationEndpoints:
    """Generation endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    def test_demo_reel_generation_no_auth(self):
        """Test demo reel generation without authentication"""
        response = requests.post(f"{BASE_URL}/api/generate/demo-reel", json={
            "topic": "Test topic for demo",
            "niche": "Luxury",
            "tone": "Bold",
            "duration": "30s",
            "language": "English",
            "goal": "Followers",
            "audience": "General"
        })
        assert response.status_code == 200
        data = response.json()
        assert "output" in data
        assert "status" in data
        assert data["status"] == "SUCCEEDED"
        
        # Verify demo watermark
        output = data["output"]
        assert "watermark" in output
        assert "demo_version" in output
        assert output["demo_version"] == True
    
    def test_reel_generation_with_auth(self, auth_token):
        """Test reel generation with authentication"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "topic": "Morning routines",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            }
        )
        # May fail if no credits, but should not be 500
        assert response.status_code in [200, 400, 402]
        
        if response.status_code == 200:
            data = response.json()
            assert "output" in data
            output = data["output"]
            assert "hooks" in output
            assert "best_hook" in output
            assert "script" in output


class TestContactEndpoints:
    """Contact endpoint tests"""
    
    def test_submit_contact_form(self):
        """Test contact form submission"""
        response = requests.post(f"{BASE_URL}/api/contact", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "General Inquiry",
            "message": "This is a test message from automated testing."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestReviewsEndpoints:
    """Reviews endpoint tests"""
    
    def test_get_reviews(self):
        """Test getting reviews list"""
        response = requests.get(f"{BASE_URL}/api/reviews")
        assert response.status_code == 200
        # Returns empty array or list of reviews
        data = response.json()
        assert isinstance(data, list)


class TestPaymentEndpoints:
    """Payment endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    def test_get_products(self):
        """Test getting products list"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            product = data[0]
            assert "id" in product
            assert "name" in product
            assert "type" in product
            assert "priceInr" in product
            assert "credits" in product
    
    def test_create_order_requires_auth(self):
        """Test that create order requires authentication"""
        response = requests.post(f"{BASE_URL}/api/payments/create-order", json={
            "productId": 1
        })
        assert response.status_code in [401, 403]
    
    def test_payment_history_requires_auth(self):
        """Test that payment history requires authentication"""
        response = requests.get(f"{BASE_URL}/api/payments/history")
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
