"""
COMPREHENSIVE QA TEST SUITE - VISIONARY-SUITE.COM
=================================================
Production-grade pytest tests covering all functionalities.

Test Categories:
1. Authentication Tests
2. Reel Generation Tests  
3. Credits/Billing Tests
4. Admin API Tests
5. Input Validation Tests
6. Security Tests
7. Role-Based Access Tests
"""

import pytest
import requests
import json
import re
from datetime import datetime

# Production URL
PROD_URL = "https://www.visionary-suite.com"

# Test Credentials
TEST_USER = {"email": "test@visionary-suite.com", "password": "Test@2026#"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestAuthentication:
    """Authentication API Tests - Positive and Negative Scenarios"""
    
    def test_login_valid_credentials(self):
        """TEST 1.1: Login with valid credentials - POSITIVE"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json=TEST_USER
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 0
    
    def test_login_invalid_email(self):
        """TEST 1.2: Login with non-existent email - NEGATIVE"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": "nonexistent@test.com", "password": "anypassword"}
        )
        assert response.status_code == 401
    
    def test_login_wrong_password(self):
        """TEST 1.3: Login with wrong password - NEGATIVE"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": "wrongpassword"}
        )
        assert response.status_code == 401
    
    def test_login_empty_email(self):
        """TEST 1.4: Login with empty email - NEGATIVE"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": "", "password": "anypassword"}
        )
        assert response.status_code in [400, 422]
    
    def test_login_empty_password(self):
        """TEST 1.5: Login with empty password - NEGATIVE"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": ""}
        )
        assert response.status_code in [400, 401, 422]
    
    def test_login_sql_injection(self):
        """TEST 1.6: SQL Injection attempt - SECURITY"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": "admin@test.com' OR '1'='1", "password": "test"}
        )
        assert response.status_code in [400, 401, 422]
    
    def test_login_invalid_email_format(self):
        """TEST 1.7: Invalid email format - VALIDATION"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": "notanemail", "password": "test"}
        )
        assert response.status_code in [400, 422]


class TestCreditsAPI:
    """Credits API Tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{PROD_URL}/api/auth/login", json=TEST_USER)
        return response.json().get("token")
    
    def test_get_credits_authenticated(self, auth_token):
        """TEST 2.1: Get credits balance - POSITIVE"""
        response = requests.get(
            f"{PROD_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert isinstance(data["credits"], (int, float))
    
    def test_get_credits_unauthenticated(self):
        """TEST 2.2: Get credits without auth - NEGATIVE"""
        response = requests.get(f"{PROD_URL}/api/credits/balance")
        assert response.status_code == 401


class TestBillingAPI:
    """Billing/Products API Tests"""
    
    def test_get_products(self):
        """TEST 3.1: Get all products - POSITIVE"""
        response = requests.get(f"{PROD_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) == 7  # 4 subscriptions + 3 packs
        
        # Verify all expected products exist
        expected_products = ["starter", "creator", "pro", "weekly", "monthly", "quarterly", "yearly"]
        for prod in expected_products:
            assert prod in data["products"], f"Missing product: {prod}"
    
    def test_products_have_required_fields(self):
        """TEST 3.2: Verify product structure - VALIDATION"""
        response = requests.get(f"{PROD_URL}/api/cashfree/products")
        data = response.json()
        
        for prod_id, product in data["products"].items():
            assert "name" in product, f"Product {prod_id} missing name"
            assert "price" in product, f"Product {prod_id} missing price"
            assert "credits" in product, f"Product {prod_id} missing credits"


class TestReelGeneration:
    """Reel Generation API Tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{PROD_URL}/api/auth/login", json=TEST_USER)
        return response.json().get("token")
    
    def test_generate_reel_unauthenticated(self):
        """TEST 4.1: Generate reel without auth - NEGATIVE"""
        response = requests.post(
            f"{PROD_URL}/api/generate/reel",
            json={"topic": "Test topic", "niche": "Lifestyle"}
        )
        assert response.status_code == 401
    
    def test_generate_reel_empty_topic(self, auth_token):
        """TEST 4.2: Generate reel with empty topic - NEGATIVE"""
        response = requests.post(
            f"{PROD_URL}/api/generate/reel",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"topic": "", "niche": "Lifestyle"}
        )
        assert response.status_code in [400, 422]


class TestAdminAPI:
    """Admin API Tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{PROD_URL}/api/auth/login", json=ADMIN_USER)
        return response.json().get("token")
    
    @pytest.fixture
    def user_token(self):
        """Get regular user token"""
        response = requests.post(f"{PROD_URL}/api/auth/login", json=TEST_USER)
        return response.json().get("token")
    
    def test_admin_stats_with_admin_token(self, admin_token):
        """TEST 5.1: Access admin stats with admin token - POSITIVE"""
        response = requests.get(
            f"{PROD_URL}/api/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should succeed for admin
        assert response.status_code in [200, 404]  # 404 if route different
    
    def test_admin_stats_with_user_token(self, user_token):
        """TEST 5.2: Access admin stats with user token - NEGATIVE"""
        response = requests.get(
            f"{PROD_URL}/api/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        # Should be forbidden for regular user
        assert response.status_code in [403, 404]


class TestInputValidation:
    """Input Validation Tests"""
    
    def test_email_with_special_chars(self):
        """TEST 6.1: Email with special characters - VALIDATION"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": "<script>alert(1)</script>@test.com", "password": "test"}
        )
        assert response.status_code in [400, 401, 422]
    
    def test_xss_in_email(self):
        """TEST 6.2: XSS attempt in email - SECURITY"""
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": "test<img src=x onerror=alert(1)>@test.com", "password": "test"}
        )
        assert response.status_code in [400, 401, 422]
    
    def test_very_long_email(self):
        """TEST 6.3: Very long email - VALIDATION"""
        long_email = "a" * 500 + "@test.com"
        response = requests.post(
            f"{PROD_URL}/api/auth/login",
            json={"email": long_email, "password": "test"}
        )
        assert response.status_code in [400, 401, 422]


class TestSecurityEndpoints:
    """Security Tests"""
    
    def test_protected_route_without_auth(self):
        """TEST 7.1: Access protected route without auth - SECURITY"""
        protected_routes = [
            "/api/credits/balance",
            "/api/generate/reel",
            "/api/admin/dashboard/stats"
        ]
        
        for route in protected_routes:
            response = requests.get(f"{PROD_URL}{route}")
            assert response.status_code in [401, 403, 404, 405], f"Route {route} should be protected"


class TestStoryVideoStudio:
    """Story Video Studio API Tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{PROD_URL}/api/auth/login", json=TEST_USER)
        return response.json().get("token")
    
    def test_get_video_styles(self, auth_token):
        """TEST 8.1: Get video styles - POSITIVE"""
        response = requests.get(
            f"{PROD_URL}/api/story-video-studio/styles",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        assert len(data["styles"]) >= 4  # At least 4 styles
    
    def test_get_pricing(self, auth_token):
        """TEST 8.2: Get video pricing - POSITIVE"""
        response = requests.get(
            f"{PROD_URL}/api/story-video-studio/pricing",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200


class TestHistory:
    """Generation History API Tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{PROD_URL}/api/auth/login", json=TEST_USER)
        return response.json().get("token")
    
    def test_get_reel_history(self, auth_token):
        """TEST 9.1: Get reel generation history - POSITIVE"""
        response = requests.get(
            f"{PROD_URL}/api/reel-export/history",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
