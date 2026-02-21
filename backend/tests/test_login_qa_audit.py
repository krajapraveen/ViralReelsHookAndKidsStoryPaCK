"""
Login Page QA Audit - Backend API Tests
Tests for authentication endpoints, validation, and security
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLoginAPIValidation:
    """Test login endpoint field validations"""
    
    def test_health_check(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ Health check passed")
    
    def test_login_empty_email(self):
        """Test login with empty email - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "",
            "password": "Password123!"
        })
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✓ Empty email rejected")
    
    def test_login_invalid_email_format(self):
        """Test login with invalid email format"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid",
            "password": "Password123!"
        })
        assert response.status_code in [400, 401, 422], f"Expected 400/401/422, got {response.status_code}"
        print("✓ Invalid email format handled")
    
    def test_login_empty_password(self):
        """Test login with empty password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": ""
        })
        assert response.status_code in [400, 401, 422], f"Expected 400/401/422, got {response.status_code}"
        print("✓ Empty password rejected")
    
    def test_login_short_password(self):
        """Test login with password less than 8 chars"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "short"
        })
        # This should fail due to wrong password (actual validation is on submit)
        assert response.status_code in [400, 401, 422], f"Expected 400/401/422, got {response.status_code}"
        print("✓ Short password handled")


class TestLoginAPIAuthentication:
    """Test login authentication flows"""
    
    def test_login_valid_demo_credentials(self):
        """Test login with valid demo user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == "demo@example.com"
        print(f"✓ Demo user login successful, user: {data['user']['email']}")
    
    def test_login_valid_admin_credentials(self):
        """Test login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        print(f"✓ Admin user login successful, role: {data['user'].get('role', 'user')}")
    
    def test_login_invalid_credentials_generic_error(self):
        """Test that invalid credentials return generic error (security)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        # Check that error message is generic (doesn't reveal if email exists)
        error_detail = data.get("detail", "")
        assert "Invalid email or password" in error_detail, f"Expected generic error, got: {error_detail}"
        print("✓ Invalid credentials return generic error (security)")
    
    def test_login_wrong_password_generic_error(self):
        """Test that wrong password returns generic error (doesn't reveal email exists)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        error_detail = data.get("detail", "")
        # Should NOT say "password incorrect" - that would reveal email exists
        assert "Invalid email or password" in error_detail, f"Error message should be generic: {error_detail}"
        print("✓ Wrong password returns generic error (security)")


class TestForgotPasswordAPI:
    """Test forgot password endpoint"""
    
    def test_forgot_password_valid_email(self):
        """Test forgot password with valid email"""
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={
            "email": "demo@example.com"
        })
        assert response.status_code == 200, f"Forgot password failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Success should be True"
        print("✓ Forgot password returns success for valid email")
    
    def test_forgot_password_nonexistent_email_no_reveal(self):
        """Test forgot password doesn't reveal if email exists"""
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={
            "email": "nonexistent_user_xyz@example.com"
        })
        # Should still return success (security - don't reveal if email exists)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Should return success even for non-existent email"
        print("✓ Forgot password doesn't reveal if email exists (security)")


class TestTokenValidation:
    """Test token handling"""
    
    def test_me_endpoint_without_token(self):
        """Test /me endpoint without auth token - should fail"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401 without token, got {response.status_code}"
        print("✓ /me endpoint requires authentication")
    
    def test_me_endpoint_with_valid_token(self):
        """Test /me endpoint with valid token"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        assert login_response.status_code == 200, "Login failed"
        token = login_response.json()["token"]
        
        # Now test /me endpoint
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Failed to get user: {response.text}"
        data = response.json()
        assert "email" in data, "Email not in response"
        assert data["email"] == "demo@example.com"
        print("✓ /me endpoint works with valid token")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
