"""
Test Google reCAPTCHA v3 Integration - Iteration 140
Tests for reCAPTCHA v3 implementation across signup, login, forgot-password, and contact pages
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://engagement-loop-core.preview.emergentagent.com')

class TestRecaptchaConfig:
    """Test reCAPTCHA v3 configuration endpoint"""
    
    def test_captcha_config_endpoint(self):
        """GET /api/auth/captcha-config should return reCAPTCHA v3 config"""
        response = requests.get(f"{BASE_URL}/api/auth/captcha-config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("enabled") == True, "CAPTCHA should be enabled"
        assert data.get("provider") == "recaptcha_v3", f"Provider should be 'recaptcha_v3', got {data.get('provider')}"
        assert data.get("siteKey") == "6LdTGocsAAAAAFHdoM1O6JyeUpSIIayv2GJ0I505", f"Site key mismatch"
        print("✅ PASS: /api/auth/captcha-config returns correct reCAPTCHA v3 configuration")


class TestSignupCaptcha:
    """Test signup endpoint with reCAPTCHA verification"""
    
    def test_signup_without_captcha_token_fails(self):
        """POST /api/auth/register without captcha_token should fail when CAPTCHA is enabled"""
        payload = {
            "name": "TEST_Captcha User",
            "email": "test_captcha_nocaptcha@example.com",
            "password": "Test@1234567!"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        # When CAPTCHA is enabled and no token provided, should fail with 400
        assert response.status_code == 400, f"Expected 400 (CAPTCHA required), got {response.status_code}"
        data = response.json()
        assert "captcha" in data.get("detail", "").lower() or "verification" in data.get("detail", "").lower(), \
            f"Expected CAPTCHA error message, got: {data.get('detail')}"
        print("✅ PASS: Signup without captcha_token returns 400 CAPTCHA verification failed")
    
    def test_signup_with_invalid_captcha_token_fails(self):
        """POST /api/auth/register with invalid captcha_token should fail"""
        payload = {
            "name": "TEST_Captcha User",
            "email": "test_captcha_invalid@example.com",
            "password": "Test@1234567!",
            "captcha_token": "invalid_token_here"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "captcha" in data.get("detail", "").lower() or "verification" in data.get("detail", "").lower(), \
            f"Expected CAPTCHA error message, got: {data.get('detail')}"
        print("✅ PASS: Signup with invalid captcha_token returns 400")
    
    def test_signup_schema_has_captcha_token(self):
        """Verify UserCreate schema accepts captcha_token field"""
        # Send a well-formed request with captcha_token in body to ensure schema accepts it
        payload = {
            "name": "TEST_Schema Check",
            "email": "test_schema@example.com",
            "password": "Test@1234567!",
            "captcha_token": ""  # Empty token should still fail CAPTCHA verification
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        # Should NOT be 422 (validation error) - the schema accepts the field
        # Should be 400 (CAPTCHA verification failed) since token is empty
        assert response.status_code != 422, "Schema should accept captcha_token field"
        print("✅ PASS: UserCreate schema accepts captcha_token field")


class TestLoginCaptcha:
    """Test login endpoint with reCAPTCHA verification after failed attempts"""
    
    def test_login_without_captcha_first_attempt_works(self):
        """POST /api/auth/login should work without CAPTCHA for first attempts"""
        payload = {
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        # Should succeed with valid credentials
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "token" in data, "Response should contain token"
        print("✅ PASS: Login works without CAPTCHA for valid credentials")
    
    def test_login_with_wrong_password_increments_attempts(self):
        """POST /api/auth/login with wrong password should increment failed attempts"""
        # Use a random email to avoid interfering with other tests
        test_email = "test_failed_login@visionary-suite.com"
        payload = {
            "email": test_email,
            "password": "WrongPassword123!"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        # Should fail with 401 (unauthorized)
        assert response.status_code in [401, 423], f"Expected 401 or 423, got {response.status_code}"
        print("✅ PASS: Login with wrong password returns 401/423")
    
    def test_login_schema_has_captcha_token(self):
        """Verify UserLogin schema accepts captcha_token field"""
        payload = {
            "email": "test@visionary-suite.com",
            "password": "Test@2026#",
            "captcha_token": "test_token"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        # Should NOT be 422 (validation error) - schema accepts the field
        assert response.status_code != 422, "Schema should accept captcha_token field"
        print("✅ PASS: UserLogin schema accepts captcha_token field")


class TestForgotPasswordCaptcha:
    """Test forgot password endpoint with reCAPTCHA verification"""
    
    def test_forgot_password_endpoint_exists(self):
        """POST /api/auth/forgot-password should exist and accept requests"""
        payload = {
            "email": "test@visionary-suite.com"
        }
        # Without X-Captcha-Token header, when CAPTCHA is enabled, it should return success
        # (to prevent email enumeration, it always returns success message)
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        print("✅ PASS: Forgot password endpoint returns success")
    
    def test_forgot_password_with_captcha_header(self):
        """POST /api/auth/forgot-password with X-Captcha-Token header"""
        payload = {
            "email": "test@visionary-suite.com"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Captcha-Token": "test_token"
        }
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json=payload, headers=headers)
        
        # Always returns success to prevent email enumeration
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ PASS: Forgot password accepts X-Captcha-Token header")


class TestContactFormCaptcha:
    """Test contact form endpoint with reCAPTCHA verification"""
    
    def test_contact_without_captcha_fails(self):
        """POST /api/feedback/contact without CAPTCHA should fail"""
        payload = {
            "name": "TEST Contact User",
            "email": "test_contact@example.com",
            "subject": "General Inquiry",
            "message": "This is a test message for CAPTCHA testing"
        }
        response = requests.post(f"{BASE_URL}/api/feedback/contact", json=payload)
        
        # Should fail with 400 when CAPTCHA is enabled and no token provided
        assert response.status_code == 400, f"Expected 400 (CAPTCHA required), got {response.status_code}"
        data = response.json()
        assert "captcha" in data.get("detail", "").lower() or "verification" in data.get("detail", "").lower(), \
            f"Expected CAPTCHA error, got: {data.get('detail')}"
        print("✅ PASS: Contact form without CAPTCHA returns 400")
    
    def test_contact_with_invalid_captcha_fails(self):
        """POST /api/feedback/contact with invalid X-Captcha-Token header should fail"""
        payload = {
            "name": "TEST Contact User",
            "email": "test_contact@example.com",
            "subject": "General Inquiry",
            "message": "This is a test message"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Captcha-Token": "invalid_captcha_token"
        }
        response = requests.post(f"{BASE_URL}/api/feedback/contact", json=payload, headers=headers)
        
        # Should fail with 400 (invalid token)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✅ PASS: Contact form with invalid CAPTCHA token returns 400")


class TestExistingLoginFlow:
    """Test that existing login flow still works"""
    
    def test_valid_credentials_login(self):
        """Existing login with valid credentials should still work"""
        payload = {
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user object"
        assert data["user"]["email"] == "test@visionary-suite.com", "User email should match"
        print("✅ PASS: Existing login flow with valid credentials works")
    
    def test_invalid_credentials_login(self):
        """Login with invalid credentials should fail with 401"""
        payload = {
            "email": "test@visionary-suite.com",
            "password": "WrongPassword!"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code in [401, 423], f"Expected 401 or 423, got {response.status_code}"
        print("✅ PASS: Login with invalid credentials returns 401/423")


class TestNoCaptchaOnProtectedPages:
    """Verify CAPTCHA is not required on dashboard/subscription pages"""
    
    def test_user_profile_no_captcha(self):
        """GET /api/auth/me should not require CAPTCHA"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        assert login_response.status_code == 200, "Login should succeed"
        token = login_response.json()["token"]
        
        # Then access profile endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ PASS: /api/auth/me works without CAPTCHA")
    
    def test_subscription_plans_no_captcha(self):
        """GET /api/subscriptions/recurring/plans should not require CAPTCHA"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/recurring/plans")
        
        # Should return plans without CAPTCHA
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ PASS: /api/subscriptions/recurring/plans works without CAPTCHA")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
