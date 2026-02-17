"""
GenStudio API Tests - Testing all GenStudio endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGenStudioAPI:
    """Test GenStudio API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            print(f"Logged in successfully, token obtained")
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_genstudio_dashboard(self):
        """Test GenStudio dashboard endpoint"""
        response = self.session.get(f"{BASE_URL}/api/genstudio/dashboard")
        print(f"Dashboard response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify dashboard structure
        assert "credits" in data
        assert "stats" in data
        assert "templates" in data
        print(f"Dashboard data: credits={data.get('credits')}, stats={data.get('stats')}")
    
    def test_genstudio_templates(self):
        """Test GenStudio templates endpoint"""
        response = self.session.get(f"{BASE_URL}/api/genstudio/templates")
        print(f"Templates response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        print(f"Found {len(data.get('templates', []))} templates")
    
    def test_genstudio_style_profiles(self):
        """Test GenStudio style profiles endpoint"""
        response = self.session.get(f"{BASE_URL}/api/genstudio/style-profiles")
        print(f"Style profiles response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "profiles" in data
        print(f"Found {len(data.get('profiles', []))} style profiles")
    
    def test_genstudio_history(self):
        """Test GenStudio history endpoint"""
        response = self.session.get(f"{BASE_URL}/api/genstudio/history")
        print(f"History response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "totalPages" in data
        print(f"Found {len(data.get('jobs', []))} jobs, totalPages={data.get('totalPages')}")
    
    def test_credits_balance(self):
        """Test credits balance endpoint"""
        response = self.session.get(f"{BASE_URL}/api/credits/balance")
        print(f"Credits balance response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "balance" in data
        print(f"Credits balance: {data.get('balance')}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
