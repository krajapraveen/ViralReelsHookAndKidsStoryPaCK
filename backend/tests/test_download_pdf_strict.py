"""
Strict QA Testing for Downloads, PDFs, and Image Generation
CreatorStudio AI - Focus on Download/PDF/Image functionality
"""
import pytest
import requests
import os
import json
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://visionary-qa.preview.emergentagent.com').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestAuthAndDownloads:
    """Test authentication and download functionality"""
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        """Login and get demo user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Demo login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login and get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_01_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data.get("file_expiry_minutes") == 3  # Verify 3-minute expiry
        print(f"Health check passed: {data}")
    
    def test_02_demo_login(self):
        """Test demo user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"Demo login successful, credits: {data['user'].get('credits', 0)}")
    
    def test_03_admin_login(self):
        """Test admin user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "ADMIN"
        print(f"Admin login successful, role: {data['user']['role']}")


class TestStoryToolsAPI:
    """Test Story Tools - Worksheets, Printable Books, PDF generation"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Demo login failed")
    
    def test_04_story_tools_worksheets_list(self, auth_headers):
        """Test worksheets list endpoint"""
        response = requests.get(f"{BASE_URL}/api/story-tools/worksheets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "worksheets" in data
        print(f"Worksheets count: {len(data['worksheets'])}")
    
    def test_05_story_tools_printable_books_list(self, auth_headers):
        """Test printable books list endpoint"""
        response = requests.get(f"{BASE_URL}/api/story-tools/printable-books", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "books" in data
        print(f"Printable books count: {len(data['books'])}")


class TestGenStudioAPI:
    """Test GenStudio - Image Generation, History, Downloads"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Demo login failed")
    
    def test_06_genstudio_dashboard(self, auth_headers):
        """Test GenStudio dashboard endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert "templates" in data
        assert "costs" in data
        assert "fileExpiryMinutes" in data
        assert data["fileExpiryMinutes"] == 3  # 3-minute expiry
        print(f"GenStudio dashboard: {data['credits']} credits, {len(data['templates'])} templates")
    
    def test_07_genstudio_templates(self, auth_headers):
        """Test GenStudio templates endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) > 0
        print(f"Templates available: {[t['name'] for t in data['templates'][:3]]}")
    
    def test_08_genstudio_history(self, auth_headers):
        """Test GenStudio history endpoint with jobs"""
        response = requests.get(f"{BASE_URL}/api/genstudio/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "fileExpiryMinutes" in data
        print(f"History: {data['total']} total jobs, {len(data['jobs'])} returned")
        
        # Check job structure if jobs exist
        if data["jobs"]:
            job = data["jobs"][0]
            assert "id" in job
            assert "status" in job
            assert "type" in job
            print(f"First job: {job['type']} - {job['status']}")


class TestWalletAPI:
    """Test Wallet/Credit Pipeline"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Demo login failed")
    
    def test_09_wallet_balance(self, auth_headers):
        """Test wallet balance endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/balance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "balanceCredits" in data
        assert "availableCredits" in data
        assert "reservedCredits" in data
        print(f"Wallet: {data['balanceCredits']} balance, {data['availableCredits']} available")
    
    def test_10_wallet_ledger(self, auth_headers):
        """Test wallet ledger endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/ledger", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "ledger" in data
        assert "total" in data
        print(f"Ledger: {data['total']} entries")
    
    def test_11_wallet_jobs(self, auth_headers):
        """Test wallet jobs list endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        print(f"Wallet jobs: {data['total']} total")


class TestPaymentAPIs:
    """Test Payment APIs - Cashfree and Products"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Demo login failed")
    
    def test_12_cashfree_products(self, auth_headers):
        """Test Cashfree products endpoint"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data or "creditPacks" in data or "products" in data
        print(f"Cashfree products: {list(data.keys())}")
    
    def test_13_payment_products(self, auth_headers):
        """Test payment products endpoint"""
        response = requests.get(f"{BASE_URL}/api/payments/products", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data or "creditPacks" in data
        print(f"Payment products: {list(data.keys())}")


class TestPrivacyAPI:
    """Test Privacy Settings API - GDPR, Data Export"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Demo login failed")
    
    def test_14_privacy_settings_get(self, auth_headers):
        """Test get privacy settings"""
        response = requests.get(f"{BASE_URL}/api/privacy/settings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "marketingEmails" in data or "settings" in data or "preferences" in data
        print(f"Privacy settings retrieved: {list(data.keys())}")
    
    def test_15_privacy_data_export(self, auth_headers):
        """Test data export endpoint"""
        response = requests.post(f"{BASE_URL}/api/privacy/export", headers=auth_headers)
        # Data export might return 200 with data or 202 for async processing
        assert response.status_code in [200, 202]
        data = response.json()
        print(f"Data export response: {list(data.keys()) if isinstance(data, dict) else 'OK'}")


class TestGenerationAPIs:
    """Test Generation APIs - Story and Reel"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Demo login failed")
    
    def test_16_generations_list(self, auth_headers):
        """Test generations list endpoint"""
        response = requests.get(f"{BASE_URL}/api/generate/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "generations" in data
        assert "total" in data
        print(f"Generations: {data['total']} total")
    
    def test_17_reel_validation_empty_topic(self, auth_headers):
        """Test reel generation rejects empty topic"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=auth_headers,
            json={
                "topic": "",  # Empty topic
                "niche": "Business",
                "tone": "Professional",
                "duration": "30s",
                "language": "English",
                "goal": "Engagement"
            }
        )
        # Should reject empty topic with 400 or 422
        assert response.status_code in [400, 422], f"Empty topic should be rejected, got {response.status_code}"
        print(f"Empty topic correctly rejected: {response.status_code}")


class TestAdminAPIs:
    """Test Admin APIs"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        """Get auth headers for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Admin login failed")
    
    def test_18_admin_stats(self, admin_headers):
        """Test admin stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "totalUsers" in data or "users" in data or "stats" in data
        print(f"Admin stats: {list(data.keys())[:5]}")
    
    def test_19_admin_users_list(self, admin_headers):
        """Test admin users list"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        print(f"Admin users list: {len(data['users'])} users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
