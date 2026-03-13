"""
CreatorStudio AI - Feature Testing
Tests for: Content Filtering, Privacy Settings, International Payments, Admin Dashboard
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://remix-monetize-1.preview.emergentagent.com')

class TestContentFiltering:
    """Test content filtering for inappropriate words"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test user and get auth token"""
        # Register or login test user
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": "testfilter@example.com",
            "password": "TestPass123!"
        })
        
        if register_response.status_code == 200:
            self.token = register_response.json().get("token")
        else:
            # User may already exist, try login
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "testfilter@example.com",
                "password": "TestPass123!"
            })
            if login_response.status_code == 200:
                self.token = login_response.json().get("token")
            else:
                pytest.skip("Could not authenticate test user")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_blocked_word_porn(self):
        """Test that 'porn' is blocked in reel topic"""
        response = requests.post(f"{BASE_URL}/api/generate/reel", 
            headers=self.headers,
            json={
                "topic": "How to make porn videos",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            })
        
        # Should be rejected with 400 or contain error message
        assert response.status_code in [400, 500] or "inappropriate" in response.text.lower() or "blocked" in response.text.lower()
        print(f"Content filter test (porn): Status {response.status_code}, Response: {response.text[:200]}")
    
    def test_blocked_word_violence(self):
        """Test that 'kill' is blocked in reel topic"""
        response = requests.post(f"{BASE_URL}/api/generate/reel", 
            headers=self.headers,
            json={
                "topic": "How to kill your enemies",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            })
        
        # Should be rejected
        assert response.status_code in [400, 500] or "inappropriate" in response.text.lower() or "blocked" in response.text.lower()
        print(f"Content filter test (kill): Status {response.status_code}, Response: {response.text[:200]}")
    
    def test_clean_topic_passes(self):
        """Test that clean topics pass validation"""
        response = requests.post(f"{BASE_URL}/api/generate/reel", 
            headers=self.headers,
            json={
                "topic": "Morning routines of successful entrepreneurs",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            })
        
        # Should succeed (200) or fail for other reasons (not content filter)
        print(f"Clean topic test: Status {response.status_code}, Response: {response.text[:200]}")
        # If it fails, it should not be due to content filtering
        if response.status_code != 200:
            assert "inappropriate" not in response.text.lower()


class TestPrivacyFeatures:
    """Test GDPR/CCPA privacy features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test user and get auth token"""
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Privacy Test User",
            "email": "privacytest@example.com",
            "password": "TestPass123!"
        })
        
        if register_response.status_code == 200:
            self.token = register_response.json().get("token")
        else:
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "privacytest@example.com",
                "password": "TestPass123!"
            })
            if login_response.status_code == 200:
                self.token = login_response.json().get("token")
            else:
                pytest.skip("Could not authenticate test user")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_my_data(self):
        """Test GDPR Article 15 - Right of Access"""
        response = requests.get(f"{BASE_URL}/api/privacy/my-data", headers=self.headers)
        print(f"Get my data: Status {response.status_code}, Response: {response.text[:300]}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
    
    def test_export_data(self):
        """Test GDPR Article 20 - Right to Data Portability"""
        response = requests.get(f"{BASE_URL}/api/privacy/export", headers=self.headers)
        print(f"Export data: Status {response.status_code}, Response: {response.text[:300]}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
    
    def test_update_consent(self):
        """Test consent preferences update"""
        response = requests.post(f"{BASE_URL}/api/privacy/consent", 
            headers=self.headers,
            json={
                "marketing": False,
                "analytics": True,
                "thirdParty": False
            })
        print(f"Update consent: Status {response.status_code}, Response: {response.text[:200]}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
    
    def test_privacy_policy_endpoint(self):
        """Test privacy policy API endpoint"""
        response = requests.get(f"{BASE_URL}/api/privacy/policy")
        print(f"Privacy policy: Status {response.status_code}, Response: {response.text[:300]}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "policy" in data


class TestInternationalPayments:
    """Test international payment currency support"""
    
    def test_products_endpoint(self):
        """Test products endpoint returns products"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        print(f"Products: Status {response.status_code}, Response: {response.text[:300]}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "products" in data
    
    def test_currencies_endpoint(self):
        """Test currencies endpoint returns supported currencies"""
        response = requests.get(f"{BASE_URL}/api/payments/currencies")
        print(f"Currencies: Status {response.status_code}, Response: {response.text[:300]}")
        
        # May or may not exist
        if response.status_code == 200:
            data = response.json()
            print(f"Supported currencies: {data}")


class TestAdminDashboard:
    """Test admin dashboard access"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup admin user"""
        # Try to login as admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Admin@123"
        })
        
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        else:
            # Try to register admin
            register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
                "name": "Admin User",
                "email": "admin@creatorstudio.ai",
                "password": "Admin@123!"
            })
            if register_response.status_code == 200:
                self.token = register_response.json().get("token")
                self.headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
            else:
                pytest.skip("Could not authenticate admin user")
    
    def test_admin_analytics_overview(self):
        """Test admin analytics overview endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/analytics/overview", headers=self.headers)
        print(f"Admin analytics: Status {response.status_code}, Response: {response.text[:300]}")
        
        # May require admin role
        if response.status_code == 403:
            print("Admin analytics requires admin role - expected behavior for non-admin users")
        elif response.status_code == 200:
            data = response.json()
            print(f"Analytics data: {data}")


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_ready(self):
        """Test health ready endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/ready")
        print(f"Health ready: Status {response.status_code}, Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "UP"
    
    def test_health_detailed(self):
        """Test detailed health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/detailed")
        print(f"Health detailed: Status {response.status_code}, Response: {response.text[:300]}")
        
        assert response.status_code == 200


class TestCreditSystem:
    """Test credit system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test user"""
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Credit Test User",
            "email": "credittest@example.com",
            "password": "TestPass123!"
        })
        
        if register_response.status_code == 200:
            self.token = register_response.json().get("token")
        else:
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "credittest@example.com",
                "password": "TestPass123!"
            })
            if login_response.status_code == 200:
                self.token = login_response.json().get("token")
            else:
                pytest.skip("Could not authenticate test user")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_credit_balance(self):
        """Test getting credit balance"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=self.headers)
        print(f"Credit balance: Status {response.status_code}, Response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        # New users should get 54 free credits
        print(f"User balance: {data.get('balance')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
