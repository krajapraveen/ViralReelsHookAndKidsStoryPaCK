"""
Comprehensive QA Tests for Sign-Up Page Validations
Testing: Full Name, Email, Password validations and registration flow
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSignupValidations:
    """Test sign-up form validations at API level"""
    
    # ========== Full Name Validation Tests ==========
    
    def test_register_empty_name(self):
        """Test registration with empty name - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "",
            "email": f"test_{int(time.time())}@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code in [400, 422]  # 422 for Pydantic validation
        print(f"  PASS: Empty name rejected with status {response.status_code}")
    
    def test_register_spaces_only_name(self):
        """Test registration with spaces-only name - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "     ",
            "email": f"test_{int(time.time())}@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code == 400
        print(f"  PASS: Spaces-only name rejected")
    
    def test_register_short_name(self):
        """Test registration with single character name - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "A",
            "email": f"test_{int(time.time())}@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code in [400, 422]
        print(f"  PASS: Short name rejected with status {response.status_code}")
    
    def test_register_numbers_only_name(self):
        """Test registration with numbers-only name - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "12345",
            "email": f"test_{int(time.time())}@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code == 400
        data = response.json()
        assert "letter" in data.get("detail", "").lower() or "only" in data.get("detail", "").lower()
        print(f"  PASS: Numbers-only name rejected with: {data.get('detail')}")
    
    def test_register_special_chars_only_name(self):
        """Test registration with special chars only name - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "!!!@@@",
            "email": f"test_{int(time.time())}@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code == 400
        print(f"  PASS: Special chars only name rejected")
    
    def test_register_valid_name_raja_praveen(self):
        """Test registration with valid name 'Raja Praveen' - should pass validation"""
        timestamp = int(time.time())
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Raja Praveen",
            "email": f"raja_praveen_{timestamp}@example.com",
            "password": "StrongPass123!"
        })
        # 200 = success, 400 with non-name error = name passed
        assert response.status_code in [200, 201]
        print(f"  PASS: 'Raja Praveen' accepted")
    
    def test_register_valid_name_with_hyphen(self):
        """Test registration with hyphenated name 'Mary-Anne' - should pass"""
        timestamp = int(time.time())
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Mary-Anne",
            "email": f"mary_anne_{timestamp}@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code in [200, 201]
        print(f"  PASS: 'Mary-Anne' accepted")
    
    def test_register_valid_short_name(self):
        """Test registration with short valid name 'John D' - should pass"""
        timestamp = int(time.time())
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "John D",
            "email": f"john_d_{timestamp}@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code in [200, 201]
        print(f"  PASS: 'John D' accepted")
    
    # ========== Email Validation Tests ==========
    
    def test_register_empty_email(self):
        """Test registration with empty email - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": "",
            "password": "StrongPass123!"
        })
        assert response.status_code in [400, 422]
        print(f"  PASS: Empty email rejected")
    
    def test_register_invalid_email_no_at(self):
        """Test registration with invalid email 'abc' - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": "abc",
            "password": "StrongPass123!"
        })
        assert response.status_code in [400, 422]
        print(f"  PASS: 'abc' email rejected")
    
    def test_register_invalid_email_no_domain(self):
        """Test registration with invalid email 'abc@' - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": "abc@",
            "password": "StrongPass123!"
        })
        assert response.status_code in [400, 422]
        print(f"  PASS: 'abc@' email rejected")
    
    def test_register_invalid_email_no_at_sign(self):
        """Test registration with invalid email 'abc.com' - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": "abc.com",
            "password": "StrongPass123!"
        })
        assert response.status_code in [400, 422]
        print(f"  PASS: 'abc.com' email rejected")
    
    def test_register_valid_email(self):
        """Test registration with valid email - should pass"""
        timestamp = int(time.time())
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"valid_email_{timestamp}@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code in [200, 201]
        print(f"  PASS: Valid email accepted")
    
    def test_register_email_normalized_lowercase(self):
        """Test that email is normalized to lowercase"""
        timestamp = int(time.time())
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"UPPERCASE_{timestamp}@EXAMPLE.COM",
            "password": "StrongPass123!"
        })
        if response.status_code in [200, 201]:
            data = response.json()
            user_email = data.get("user", {}).get("email", "")
            assert user_email == user_email.lower()
            print(f"  PASS: Email normalized to lowercase: {user_email}")
        else:
            print(f"  INFO: Registration returned {response.status_code}")
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email - should fail"""
        # Use known existing email
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": "demo@example.com",
            "password": "StrongPass123!"
        })
        assert response.status_code == 400
        data = response.json()
        assert "already" in data.get("detail", "").lower() or "exist" in data.get("detail", "").lower() or "registered" in data.get("detail", "").lower()
        print(f"  PASS: Duplicate email rejected with: {data.get('detail')}")
    
    # ========== Password Validation Tests ==========
    
    def test_register_empty_password(self):
        """Test registration with empty password - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"test_{int(time.time())}@example.com",
            "password": ""
        })
        assert response.status_code in [400, 422]
        print(f"  PASS: Empty password rejected")
    
    def test_register_short_password(self):
        """Test registration with short password (7 chars) - should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"test_{int(time.time())}@example.com",
            "password": "Pass1!x"  # 7 chars
        })
        assert response.status_code == 400
        data = response.json()
        assert "8" in data.get("detail", "") or "character" in data.get("detail", "").lower()
        print(f"  PASS: Short password rejected with: {data.get('detail')}")
    
    def test_register_password_no_uppercase(self):
        """Test registration with password missing uppercase - should fail"""
        time.sleep(2)  # Avoid rate limiting
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"test_{int(time.time())}@example.com",
            "password": "password1!"
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping test")
        assert response.status_code in [400, 422]
        data = response.json()
        assert "uppercase" in str(data).lower()
        print(f"  PASS: No uppercase password rejected")
    
    def test_register_password_no_lowercase(self):
        """Test registration with password missing lowercase - should fail"""
        time.sleep(2)  # Avoid rate limiting
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"test_{int(time.time())}@example.com",
            "password": "PASSWORD1!"
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping test")
        assert response.status_code in [400, 422]
        data = response.json()
        assert "lowercase" in str(data).lower()
        print(f"  PASS: No lowercase password rejected")
    
    def test_register_password_no_number(self):
        """Test registration with password missing number - should fail"""
        time.sleep(2)  # Avoid rate limiting
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"test_{int(time.time())}@example.com",
            "password": "Password!"
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping test")
        assert response.status_code in [400, 422]
        data = response.json()
        assert "number" in str(data).lower() or "digit" in str(data).lower()
        print(f"  PASS: No number password rejected")
    
    def test_register_password_no_special_char(self):
        """Test registration with password missing special char - should fail"""
        time.sleep(2)  # Avoid rate limiting
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"test_{int(time.time())}@example.com",
            "password": "Password1"
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping test")
        assert response.status_code in [400, 422]
        data = response.json()
        assert "special" in str(data).lower()
        print(f"  PASS: No special char password rejected")
    
    def test_register_valid_strong_password(self):
        """Test registration with valid strong password - should pass"""
        time.sleep(3)  # Avoid rate limiting
        timestamp = int(time.time())
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": f"strong_pwd_{timestamp}@example.com",
            "password": "StrongPass123!"
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping test")
        assert response.status_code in [200, 201]
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["credits"] == 100  # Should get 100 free credits
        print(f"  PASS: Valid strong password accepted, got {data['user']['credits']} credits")
    
    # ========== Registration Flow Tests ==========
    
    def test_register_returns_token(self):
        """Test that successful registration returns a JWT token"""
        time.sleep(3)  # Avoid rate limiting
        timestamp = int(time.time())
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Token Test",
            "email": f"token_test_{timestamp}@example.com",
            "password": "StrongPass123!"
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping test")
        assert response.status_code in [200, 201]
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 20  # JWT should be longer
        print(f"  PASS: Registration returns valid token")
    
    def test_register_returns_user_data(self):
        """Test that successful registration returns user data"""
        time.sleep(3)  # Avoid rate limiting
        timestamp = int(time.time())
        email = f"userdata_test_{timestamp}@example.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "User Data Test",
            "email": email,
            "password": "StrongPass123!"
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping test")
        assert response.status_code in [200, 201]
        data = response.json()
        assert "user" in data
        user = data["user"]
        assert user["email"] == email.lower()
        assert user["name"] == "User Data Test"
        assert "id" in user
        assert user["credits"] == 100
        print(f"  PASS: Registration returns complete user data")


class TestHealthEndpoint:
    """Test API health check"""
    
    def test_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"  PASS: Health check returns 200")
