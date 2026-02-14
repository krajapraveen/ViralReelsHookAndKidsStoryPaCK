"""
Backend API Tests for CreatorStudio AI
Tests: Auth, Credits, Generation endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "email" in data
        assert data["email"] == "admin@creatorstudio.ai"
        
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code in [401, 403]


class TestCredits:
    """Credits endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_balance(self, auth_token):
        """Test getting credit balance"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert isinstance(data["balance"], (int, float))
        
    def test_get_balance_unauthorized(self):
        """Test getting balance without auth"""
        response = requests.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code in [401, 403]


class TestGeneration:
    """Generation endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_generations_list(self, auth_token):
        """Test getting generations list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/generate/generations", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "content" in data or isinstance(data, list)


class TestWorkerHealth:
    """Python worker health tests"""
    
    def test_worker_health(self):
        """Test worker health endpoint"""
        response = requests.get("http://localhost:5000/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"


class TestPayments:
    """Payment endpoint tests (public)"""
    
    def test_get_products(self):
        """Test getting payment products (public endpoint)"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        # Products may be empty if not configured
        data = response.json()
        assert isinstance(data, list)
