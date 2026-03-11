"""
Iteration 107: Regression Testing After Production Stabilization
Focus: Login flows, My Downloads, Photo to Comic, Dashboard, Notifications
Tests base64 storage fix for images (old data with file paths should not crash)
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://generation-hotfix.preview.emergentagent.com"

# Test credentials from problem statement
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestHealthAndBasicEndpoints:
    """Test basic API health and status endpoints"""
    
    def test_health_endpoint(self):
        """Verify health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health endpoint: {data['status']}")
    
    def test_worker_system_status(self):
        """Check worker system status endpoint"""
        response = requests.get(f"{BASE_URL}/api/worker/system/status")
        # Should be 200 or 401 (auth required) - not 500
        assert response.status_code in [200, 401, 403], f"Worker status returned {response.status_code}"
        print(f"✓ Worker status endpoint: {response.status_code}")


class TestDemoUserLogin:
    """Test demo user authentication flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for demo user tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_login_demo_user(self):
        """Login with demo user credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data
        token = data.get("token") or data.get("access_token")
        assert len(token) > 0
        print(f"✓ Demo user login successful, token received")
        return token
    
    def test_login_with_wrong_password(self):
        """Ensure wrong password fails"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "WrongPassword"
        })
        assert response.status_code in [400, 401, 403]
        print(f"✓ Wrong password correctly rejected: {response.status_code}")
    
    def test_get_current_user(self):
        """Get current user after login"""
        # Login first
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert login_response.status_code == 200
        token = login_response.json().get("token") or login_response.json().get("access_token")
        
        # Get current user
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == DEMO_USER["email"]
        print(f"✓ Current user verified: {data.get('email')}")


class TestAdminUserLogin:
    """Test admin user authentication flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for admin user tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_login_admin_user(self):
        """Login with admin user credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data
        print(f"✓ Admin user login successful")
        return data.get("token") or data.get("access_token")


class TestMyDownloadsEndpoint:
    """Test My Downloads page backend - critical for base64 storage fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json().get("token") or response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_my_downloads_endpoint(self):
        """Test /api/downloads/my-downloads returns data (not crash on old file paths)"""
        response = self.session.get(f"{BASE_URL}/api/downloads/my-downloads")
        assert response.status_code == 200, f"My downloads failed: {response.text}"
        data = response.json()
        # Should have downloads array
        assert "downloads" in data
        assert isinstance(data["downloads"], list)
        assert "total" in data
        print(f"✓ My Downloads endpoint: {len(data['downloads'])} downloads, {data['total']} total")
        # Check if message exists
        if data.get("message"):
            print(f"  Info: {data['message']}")


class TestPhotoToComicEndpoints:
    """Test Photo to Comic feature endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json().get("token") or response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_styles_endpoint(self):
        """Get available comic styles"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/styles")
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        assert len(data["styles"]) > 0
        print(f"✓ Photo to Comic styles: {len(data['styles'])} styles available")
    
    def test_pricing_endpoint(self):
        """Get pricing information"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"✓ Photo to Comic pricing retrieved")
    
    def test_history_endpoint(self):
        """Get generation history"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/history")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        print(f"✓ Photo to Comic history: {len(data['jobs'])} jobs found")
    
    def test_diagnostic_endpoint(self):
        """Check diagnostic endpoint for system health"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/diagnostic")
        assert response.status_code == 200
        data = response.json()
        assert "llm_status" in data
        print(f"✓ Diagnostic: LLM available={data.get('llm_status', {}).get('available')}")


class TestDashboardEndpoints:
    """Test dashboard-related endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json().get("token") or response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_credits_balance(self):
        """Get user credits balance"""
        response = self.session.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data or "credits" in data
        balance = data.get("balance") or data.get("credits", 0)
        print(f"✓ Credits balance: {balance}")
    
    def test_wallet_endpoint(self):
        """Get wallet info"""
        response = self.session.get(f"{BASE_URL}/api/wallet/me")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Wallet endpoint: balance={data.get('balance', 'N/A')}")
    
    def test_generations_history(self):
        """Get recent generations"""
        response = self.session.get(f"{BASE_URL}/api/generate/?page=0&size=5")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Generations history retrieved")


class TestNotificationSystem:
    """Test notification endpoints - verify previous bug fixes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json().get("token") or response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_notifications(self):
        """Get user notifications"""
        response = self.session.get(f"{BASE_URL}/api/notifications?limit=50")
        assert response.status_code == 200
        data = response.json()
        # Should return list or object with notifications
        print(f"✓ Notifications endpoint: {response.status_code}")
    
    def test_unread_count(self):
        """Get unread notifications count"""
        response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200
        print(f"✓ Unread count endpoint: {response.status_code}")
    
    def test_poll_endpoint_no_403(self):
        """Verify poll endpoint doesn't return 403 (previous bug)"""
        response = self.session.get(f"{BASE_URL}/api/notifications/poll")
        # Should be 200, not 403
        assert response.status_code != 403, "Poll endpoint still returning 403!"
        assert response.status_code == 200
        print(f"✓ Notifications poll endpoint: 200 OK (no 403 bug)")
    
    def test_mark_all_read_no_403(self):
        """Verify mark-all-read doesn't return 403 (previous bug)"""
        response = self.session.post(f"{BASE_URL}/api/notifications/mark-all-read")
        # Should be 200, not 403
        assert response.status_code != 403, "Mark-all-read endpoint still returning 403!"
        assert response.status_code == 200
        print(f"✓ Mark all read endpoint: 200 OK (no 403 bug)")


class TestCreditAndMonetizationSystem:
    """Test credit and monetization endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json().get("token") or response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_credit_status(self):
        """Get credit status for header display"""
        response = self.session.get(f"{BASE_URL}/api/monetization/credit-status")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Credit status: {data}")
    
    def test_daily_reward_status(self):
        """Check daily reward status"""
        response = self.session.get(f"{BASE_URL}/api/monetization/daily-reward/status")
        assert response.status_code == 200
        print(f"✓ Daily reward status endpoint: {response.status_code}")


class TestComicStorybookEndpoints:
    """Test Comic Storybook Builder endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json().get("token") or response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_storybook_pricing(self):
        """Get storybook pricing"""
        response = self.session.get(f"{BASE_URL}/api/comic-storybook/pricing")
        if response.status_code == 200:
            print(f"✓ Comic Storybook pricing: available")
        else:
            print(f"⚠ Comic Storybook pricing: {response.status_code}")


class TestProfileEndpoints:
    """Test profile page endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json().get("token") or response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_profile(self):
        """Get user profile info"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        print(f"✓ Profile endpoint: email={data.get('email')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
