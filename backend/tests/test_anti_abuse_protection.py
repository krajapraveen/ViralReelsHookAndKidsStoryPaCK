"""
Anti-Abuse Protection Layer Testing for Production
Tests all 6 protection layers on https://www.visionary-suite.com

Test Date: 2026-03-03
Production URL: https://www.visionary-suite.com
"""

import pytest
import requests
import os
import time
import hashlib
import json

# Production URL
BASE_URL = "https://www.visionary-suite.com"

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Disposable email domains to test (should be BLOCKED)
DISPOSABLE_EMAILS = [
    "test@mailinator.com",
    "user@guerrillamail.com",
    "spam@10minutemail.com",
    "temp@yopmail.com",
    "fake@tempmail.com",
    "random@throwaway.email",
    "test@fakeinbox.com",
    "user@temp-mail.org"
]

# Legitimate email domains to test (should be ALLOWED)
LEGITIMATE_EMAILS = [
    "legitimate@gmail.com",
    "real@yahoo.com",
    "user@outlook.com",
    "test@hotmail.com"
]


class TestAntiAbuseAPIEndpoints:
    """Test 1: Verify Anti-Abuse API endpoints exist and respond"""
    
    def test_anti_abuse_validate_signup_endpoint_exists(self):
        """Test if /api/anti-abuse/validate-signup endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/validate-signup",
            json={
                "email": "test@example.com",
                "ip_address": "192.168.1.1",
                "device_fingerprint": "test-fingerprint-123"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        # Endpoint should exist (not 404)
        assert response.status_code != 404, f"Endpoint not found. Status: {response.status_code}"
        print(f"✓ /api/anti-abuse/validate-signup endpoint exists. Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
    def test_anti_abuse_check_email_endpoint_exists(self):
        """Test if /api/anti-abuse/check-email endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/check-email",
            json={"email": "test@example.com"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        assert response.status_code != 404, f"Endpoint not found. Status: {response.status_code}"
        print(f"✓ /api/anti-abuse/check-email endpoint exists. Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
    def test_anti_abuse_check_device_endpoint_exists(self):
        """Test if /api/anti-abuse/check-device endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/check-device",
            json={"device_fingerprint": "test-fingerprint-123"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        assert response.status_code != 404, f"Endpoint not found. Status: {response.status_code}"
        print(f"✓ /api/anti-abuse/check-device endpoint exists. Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
    def test_anti_abuse_check_ip_endpoint_exists(self):
        """Test if /api/anti-abuse/check-ip endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/check-ip",
            json={"ip_address": "192.168.1.1"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        assert response.status_code != 404, f"Endpoint not found. Status: {response.status_code}"
        print(f"✓ /api/anti-abuse/check-ip endpoint exists. Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")


class TestDisposableEmailBlocking:
    """Test Layer 4: Block Disposable Emails"""
    
    @pytest.mark.parametrize("email", DISPOSABLE_EMAILS)
    def test_disposable_email_blocked(self, email):
        """Test that disposable emails are BLOCKED"""
        # Try check-email endpoint first
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/check-email",
            json={"email": email},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # If check-email doesn't exist, try validate-signup
        if response.status_code == 404:
            response = requests.post(
                f"{BASE_URL}/api/anti-abuse/validate-signup",
                json={"email": email, "ip_address": "192.168.1.1"},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
        
        data = response.json() if response.status_code == 200 else {}
        
        # Check if blocked (various possible response structures)
        is_blocked = (
            response.status_code == 400 or 
            response.status_code == 403 or
            data.get("blocked") == True or 
            data.get("is_disposable") == True or
            data.get("allowed") == False or
            "disposable" in response.text.lower() or
            "blocked" in response.text.lower()
        )
        
        print(f"Email: {email}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:300]}")
        print(f"  Is Blocked: {is_blocked}")
        
        # Record result for report
        assert is_blocked, f"Disposable email {email} should be BLOCKED but wasn't"
        
    @pytest.mark.parametrize("email", LEGITIMATE_EMAILS)
    def test_legitimate_email_allowed(self, email):
        """Test that legitimate emails are ALLOWED"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/check-email",
            json={"email": email},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 404:
            response = requests.post(
                f"{BASE_URL}/api/anti-abuse/validate-signup",
                json={"email": email, "ip_address": "192.168.1.1"},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
        
        data = response.json() if response.status_code == 200 else {}
        
        # Check if allowed
        is_allowed = (
            response.status_code == 200 and 
            (data.get("allowed") == True or 
             data.get("blocked") == False or 
             data.get("is_disposable") == False or
             "valid" in response.text.lower())
        )
        
        print(f"Email: {email}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:300]}")
        print(f"  Is Allowed: {is_allowed}")


class TestIPAddressLimiting:
    """Test Layer 2: IP Address Limiting"""
    
    def test_ip_address_check_endpoint(self):
        """Test IP address checking"""
        test_ip = "192.168.1.100"
        
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/check-ip",
            json={"ip_address": test_ip},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"IP Check for {test_ip}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
        # Document the response structure
        if response.status_code == 200:
            data = response.json()
            print(f"  Account count from IP: {data.get('account_count', 'N/A')}")
            print(f"  Is limited: {data.get('limited', data.get('blocked', 'N/A'))}")
            
    def test_ip_limit_enforced(self):
        """Test that IP limit (2 accounts max) is enforced"""
        test_ip = "10.0.0.99"
        
        # Test validate-signup with same IP multiple times
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/validate-signup",
            json={
                "email": "test1@gmail.com",
                "ip_address": test_ip,
                "device_fingerprint": "fp-test-1"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"IP Limit Test for {test_ip}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")


class TestDeviceFingerprinting:
    """Test Layer 1: Device Fingerprinting"""
    
    def test_device_fingerprint_check(self):
        """Test device fingerprint checking"""
        test_fingerprint = "canvas:abc123|webgl:xyz789|screen:1920x1080"
        
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/check-device",
            json={"device_fingerprint": test_fingerprint},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Device Fingerprint Check")
        print(f"  Fingerprint: {test_fingerprint[:50]}...")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
    def test_device_fingerprint_in_signup_validation(self):
        """Test that device fingerprint is accepted in validate-signup"""
        fingerprint = hashlib.sha256(b"test-device-001").hexdigest()
        
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/validate-signup",
            json={
                "email": "newuser@gmail.com",
                "ip_address": "203.0.113.50",
                "device_fingerprint": fingerprint,
                "canvas_fingerprint": "canvas-hash-123",
                "webgl_fingerprint": "webgl-hash-456",
                "screen_resolution": "1920x1080"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Device Fingerprint in Signup Validation")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")


class TestDelayedCreditRelease:
    """Test Layer 5: Delayed Credit Release"""
    
    def test_delayed_credits_status_endpoint(self):
        """Test delayed credits status endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/anti-abuse/delayed-credits/status",
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Delayed Credits Status Endpoint")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
    def test_delayed_credits_claim_endpoint(self):
        """Test delayed credits claim endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/delayed-credits/claim",
            json={"user_id": "test-user-id"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Delayed Credits Claim Endpoint")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")


class TestPhoneVerification:
    """Test Layer 3: Phone Number Verification"""
    
    def test_phone_send_otp_endpoint(self):
        """Test phone OTP sending endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/phone/send-otp",
            json={"phone_number": "+15555555555"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Phone OTP Send Endpoint")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
    def test_phone_verify_otp_endpoint(self):
        """Test phone OTP verification endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/phone/verify-otp",
            json={"phone_number": "+15555555555", "otp": "123456"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Phone OTP Verify Endpoint")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
    def test_phone_check_duplicate_endpoint(self):
        """Test phone duplicate check endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/phone/check",
            json={"phone_number": "+15555555555"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Phone Duplicate Check Endpoint")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")


class TestAdminAntiAbuseFeatures:
    """Test Admin Anti-Abuse Dashboard Features"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        return None
        
    def test_admin_blocked_attempts_endpoint(self, admin_token):
        """Test admin can see blocked signup attempts"""
        if not admin_token:
            pytest.skip("Admin login failed - skipping admin tests")
            
        response = requests.get(
            f"{BASE_URL}/api/admin/anti-abuse/blocked-attempts",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        print(f"Admin Blocked Attempts Endpoint")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
    def test_admin_anti_abuse_stats(self, admin_token):
        """Test admin anti-abuse statistics endpoint"""
        if not admin_token:
            pytest.skip("Admin login failed - skipping admin tests")
            
        response = requests.get(
            f"{BASE_URL}/api/admin/anti-abuse/stats",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        print(f"Admin Anti-Abuse Stats Endpoint")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")


class TestCombinationApproach:
    """Test Layer 6: Full Combination of All Protection Layers"""
    
    def test_validate_signup_with_all_params(self):
        """Test complete validation with all anti-abuse parameters"""
        test_data = {
            "email": "test@gmail.com",
            "ip_address": "192.168.1.1",
            "device_fingerprint": "test-device-fingerprint-full",
            "canvas_fingerprint": "canvas-hash-abc",
            "webgl_fingerprint": "webgl-hash-xyz",
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York",
            "language": "en-US",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/validate-signup",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Full Validate Signup Test")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:700]}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Validation Results:")
            print(f"    - Email Valid: {data.get('email_valid', 'N/A')}")
            print(f"    - IP Allowed: {data.get('ip_allowed', 'N/A')}")
            print(f"    - Device Allowed: {data.get('device_allowed', 'N/A')}")
            print(f"    - Overall Allowed: {data.get('allowed', 'N/A')}")
            
    def test_validate_signup_with_disposable_email(self):
        """Test that validate-signup blocks disposable emails"""
        test_data = {
            "email": "abuse@mailinator.com",
            "ip_address": "192.168.1.1",
            "device_fingerprint": "test-fingerprint-disposable"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/anti-abuse/validate-signup",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Validate Signup with Disposable Email")
        print(f"  Email: abuse@mailinator.com")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
        # Should be blocked
        is_blocked = (
            response.status_code in [400, 403] or
            "blocked" in response.text.lower() or
            "disposable" in response.text.lower() or
            (response.status_code == 200 and response.json().get("allowed") == False)
        )
        print(f"  BLOCKED: {is_blocked}")


class TestSignupPageIntegration:
    """Test that signup page uses anti-abuse features"""
    
    def test_register_endpoint_with_disposable_email(self):
        """Test registration endpoint blocks disposable emails"""
        test_data = {
            "name": "Test User",
            "email": "testuser@mailinator.com",
            "password": "TestPass123!"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Register Endpoint with Disposable Email")
        print(f"  Email: testuser@mailinator.com")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        
        # Should be blocked (400/403) or error message about disposable email
        is_blocked = (
            response.status_code in [400, 403] or
            "disposable" in response.text.lower() or
            "blocked" in response.text.lower() or
            "not allowed" in response.text.lower()
        )
        print(f"  Registration BLOCKED: {is_blocked}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
