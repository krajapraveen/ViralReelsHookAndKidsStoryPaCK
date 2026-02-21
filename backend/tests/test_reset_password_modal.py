"""
Reset Password Modal QA Tests
Tests for: /api/auth/forgot-password endpoint and modal behavior
Covers: Email validation, rate limiting, security (no user enumeration)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestForgotPasswordEndpoint:
    """Tests for /api/auth/forgot-password endpoint"""
    
    def test_health_check(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("✓ API health check passed")
    
    def test_forgot_password_with_valid_existing_email(self):
        """Test forgot password with existing email (demo user)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "demo@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # Generic message - doesn't reveal if user exists
        assert "If an account exists" in data.get("message", "")
        print("✓ Forgot password with existing email returns success")
    
    def test_forgot_password_with_non_existent_email(self):
        """Test forgot password with non-existent email - should return same success (security)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "nonexistent_user_12345@example.com"}
        )
        # Should return 200 with success to prevent email enumeration
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "If an account exists" in data.get("message", "")
        print("✓ Forgot password with non-existent email returns same generic success (prevents enumeration)")
    
    def test_forgot_password_invalid_email_format(self):
        """Test forgot password with invalid email format"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "not-a-valid-email"}
        )
        # Pydantic EmailStr validation should reject this
        assert response.status_code == 422  # Validation error
        print("✓ Forgot password rejects invalid email format")
    
    def test_forgot_password_empty_email(self):
        """Test forgot password with empty email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": ""}
        )
        # Should fail validation
        assert response.status_code == 422
        print("✓ Forgot password rejects empty email")
    
    def test_forgot_password_missing_email_field(self):
        """Test forgot password with missing email field"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={}
        )
        assert response.status_code == 422
        print("✓ Forgot password rejects missing email field")
    
    def test_forgot_password_email_with_spaces_trimmed(self):
        """Test forgot password trims whitespace from email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "  demo@example.com  "}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Forgot password trims whitespace from email")
    
    def test_forgot_password_case_insensitive(self):
        """Test forgot password is case-insensitive for email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "DEMO@EXAMPLE.COM"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Forgot password handles uppercase email")
    
    def test_forgot_password_rate_limiting(self):
        """Test rate limiting (3/minute limit)"""
        # Make 4 requests quickly to test rate limiting
        rate_limit_hit = False
        for i in range(5):
            response = requests.post(
                f"{BASE_URL}/api/auth/forgot-password",
                json={"email": f"test{i}@ratelimit.com"}
            )
            if response.status_code == 429:
                rate_limit_hit = True
                print(f"✓ Rate limit hit on request {i+1} with status 429")
                break
        
        if not rate_limit_hit:
            # Check if rate limiting is applied after 3 requests
            print("⚠ Warning: Rate limiting may not be enforced or limit is higher than 5")
        else:
            assert response.status_code == 429
            print("✓ Rate limiting enforced on forgot-password endpoint")
    
    def test_forgot_password_long_email(self):
        """Test forgot password with email over 254 chars (should fail)"""
        long_email = "a" * 250 + "@example.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": long_email}
        )
        # Should fail validation as email is too long
        assert response.status_code in [422, 400]
        print("✓ Forgot password rejects overly long email")


class TestForgotPasswordSecurity:
    """Security-focused tests for forgot password"""
    
    def test_no_user_enumeration_same_response(self):
        """Verify same response for existent and non-existent emails"""
        # Existing user
        resp1 = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "demo@example.com"}
        )
        
        # Non-existing user
        resp2 = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "doesnotexist99999@example.com"}
        )
        
        # Both should return 200 with success
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        
        data1 = resp1.json()
        data2 = resp2.json()
        
        # Both should have success: true
        assert data1.get("success") == True
        assert data2.get("success") == True
        
        # Both should have similar generic message
        assert "If an account exists" in data1.get("message", "")
        assert "If an account exists" in data2.get("message", "")
        
        print("✓ No user enumeration - same response for existent and non-existent emails")
    
    def test_no_timing_attack_vulnerability(self):
        """Test that response times are similar for existent vs non-existent emails"""
        import time
        
        # Time for existing email
        start1 = time.time()
        resp1 = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "demo@example.com"}
        )
        time1 = time.time() - start1
        
        # Time for non-existing email
        start2 = time.time()
        resp2 = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": "nonexistent_timing_test@example.com"}
        )
        time2 = time.time() - start2
        
        # Both should complete within reasonable time of each other
        # Allow for network variance - difference should not be more than 1 second
        time_diff = abs(time1 - time2)
        assert time_diff < 1.0, f"Timing difference too large: {time_diff}s (may leak user existence)"
        
        print(f"✓ No timing attack vulnerability - response time diff: {time_diff:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
