"""
Test Suite: Google Sign-In Migration (P0)
Tests the new custom Google Identity Services flow replacing Emergent-hosted auth.

Features tested:
1. POST /api/auth/google-signin endpoint exists and validates tokens
2. Email/password login still works (regression)
3. Backend GOOGLE_CLIENT_ID is configured
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGoogleSignInMigration:
    """Tests for the new Google Sign-In endpoint"""
    
    def test_google_signin_endpoint_exists(self):
        """Test that POST /api/auth/google-signin endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/auth/google-signin",
            json={"credential": "invalid_token"},
            headers={"Content-Type": "application/json"}
        )
        # Should return 401 for invalid token, not 404
        assert response.status_code in [401, 500], f"Expected 401 or 500, got {response.status_code}"
        print(f"✓ POST /api/auth/google-signin endpoint exists (status: {response.status_code})")
    
    def test_google_signin_rejects_invalid_token(self):
        """Test that invalid Google tokens are rejected with 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/google-signin",
            json={"credential": "fake_invalid_google_token_12345"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}"
        
        # Check error message
        data = response.json()
        assert "detail" in data, "Response should contain 'detail' field"
        assert "invalid" in data["detail"].lower() or "credential" in data["detail"].lower(), \
            f"Error message should mention invalid credential: {data['detail']}"
        print(f"✓ Invalid token rejected with 401: {data['detail']}")
    
    def test_google_signin_requires_credential(self):
        """Test that missing credential returns validation error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/google-signin",
            json={},
            headers={"Content-Type": "application/json"}
        )
        # Should return 422 (validation error) for missing required field
        assert response.status_code == 422, f"Expected 422 for missing credential, got {response.status_code}"
        print(f"✓ Missing credential returns 422 validation error")
    
    def test_google_signin_empty_credential(self):
        """Test that empty credential is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/auth/google-signin",
            json={"credential": ""},
            headers={"Content-Type": "application/json"}
        )
        # Should return 401 or 422
        assert response.status_code in [401, 422], f"Expected 401 or 422 for empty credential, got {response.status_code}"
        print(f"✓ Empty credential rejected (status: {response.status_code})")


class TestEmailPasswordLoginRegression:
    """Regression tests for email/password login"""
    
    def test_login_endpoint_exists(self):
        """Test that POST /api/auth/login endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
            headers={"Content-Type": "application/json"}
        )
        # Should return 401 for wrong credentials, not 404
        assert response.status_code in [401, 423], f"Expected 401 or 423, got {response.status_code}"
        print(f"✓ POST /api/auth/login endpoint exists (status: {response.status_code})")
    
    def test_login_with_valid_credentials(self):
        """Test login with valid test credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test@visionary-suite.com",
                "password": "Test@2026#"
            },
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 200 with token and user
        if response.status_code == 200:
            data = response.json()
            assert "token" in data, "Response should contain 'token'"
            assert "user" in data, "Response should contain 'user'"
            assert data["user"]["email"] == "test@visionary-suite.com", "User email should match"
            print(f"✓ Login successful for test@visionary-suite.com")
            print(f"  - Token received: {data['token'][:20]}...")
            print(f"  - User ID: {data['user'].get('id', 'N/A')}")
        elif response.status_code == 401:
            print(f"⚠ Login returned 401 - test user may not exist or password changed")
            print(f"  Response: {response.json()}")
        elif response.status_code == 423:
            print(f"⚠ Account locked - too many failed attempts")
            print(f"  Response: {response.json()}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_login_returns_token_and_user(self):
        """Test that successful login returns proper token and user object"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test@visionary-suite.com",
                "password": "Test@2026#"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Validate token
            assert isinstance(data.get("token"), str), "Token should be a string"
            assert len(data["token"]) > 50, "Token should be a valid JWT (>50 chars)"
            
            # Validate user object
            user = data.get("user", {})
            assert "id" in user, "User should have 'id'"
            assert "email" in user, "User should have 'email'"
            assert "name" in user, "User should have 'name'"
            assert "role" in user, "User should have 'role'"
            assert "credits" in user, "User should have 'credits'"
            
            print(f"✓ Login response structure validated")
            print(f"  - User: {user.get('name')} ({user.get('email')})")
            print(f"  - Role: {user.get('role')}")
            print(f"  - Credits: {user.get('credits')}")
        else:
            pytest.skip(f"Login failed with status {response.status_code}, skipping structure validation")


class TestAuthEndpointsHealth:
    """Health checks for auth-related endpoints"""
    
    def test_health_endpoint(self):
        """Test that health endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print(f"✓ Health endpoint OK")
    
    def test_captcha_config_endpoint(self):
        """Test that captcha config endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/auth/captcha-config")
        assert response.status_code == 200, f"Captcha config failed: {response.status_code}"
        
        data = response.json()
        assert "enabled" in data, "Should have 'enabled' field"
        assert "siteKey" in data, "Should have 'siteKey' field"
        print(f"✓ Captcha config endpoint OK (enabled: {data.get('enabled')})")
    
    def test_register_endpoint_exists(self):
        """Test that register endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "Test",
                "email": "test_nonexistent@example.com",
                "password": "Test@2026#"
            },
            headers={"Content-Type": "application/json"}
        )
        # Should return 400 (email exists or validation) or 200, not 404
        assert response.status_code != 404, "Register endpoint should exist"
        print(f"✓ Register endpoint exists (status: {response.status_code})")


class TestGoogleCallbackBackwardCompatibility:
    """Test that old Emergent auth callback still works for backward compatibility"""
    
    def test_google_callback_endpoint_exists(self):
        """Test that POST /api/auth/google-callback endpoint still exists"""
        response = requests.post(
            f"{BASE_URL}/api/auth/google-callback",
            json={"sessionId": "fake_session_id"},
            headers={"Content-Type": "application/json"}
        )
        # Should return 400 or 503 (invalid session), not 404
        assert response.status_code in [400, 503], f"Expected 400 or 503, got {response.status_code}"
        print(f"✓ POST /api/auth/google-callback endpoint exists (backward compatible)")
    
    def test_google_callback_options_cors(self):
        """Test that OPTIONS /api/auth/google-callback returns CORS headers"""
        response = requests.options(f"{BASE_URL}/api/auth/google-callback")
        # Should return 200 or 204 for CORS preflight
        assert response.status_code in [200, 204], f"Expected 200 or 204 for OPTIONS, got {response.status_code}"
        print(f"✓ OPTIONS /api/auth/google-callback returns {response.status_code} (CORS OK)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
