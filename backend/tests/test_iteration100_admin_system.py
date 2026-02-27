"""
Test Suite for Iteration 100 - Admin System, Auto-Refund, Self-Healing
Testing:
1. Admin system routes: refund-stats, self-healing-status, system-health
2. Comic Storybook v2 endpoints
3. Authentication flow
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


class TestHealthAndBasics:
    """Basic health and connectivity tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print(f"✓ Health check passed")
    
    def test_root_endpoint(self):
        """Test root endpoint - may return HTML or JSON"""
        response = requests.get(f"{BASE_URL}/")
        # Root may return HTML from React app or JSON from API
        assert response.status_code == 200, f"Root endpoint failed: {response.status_code}"
        print(f"✓ Root endpoint accessible")


class TestAuthentication:
    """Authentication flow tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        print(f"✓ Admin login successful")
        return data["token"]
    
    def test_demo_user_login(self):
        """Test demo user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        print(f"✓ Demo user login successful")
        return data["token"]


class TestAdminSystemRoutes:
    """Admin System Routes for Auto-Refund and Self-Healing"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed - skipping admin tests")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        """Get demo user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Demo login failed")
        return response.json().get("token")
    
    def test_refund_stats_endpoint(self, admin_token):
        """Test /api/admin/system/refund-stats endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/system/refund-stats", headers=headers)
        assert response.status_code == 200, f"Refund stats failed: {response.text}"
        data = response.json()
        # Verify response structure
        assert "period_days" in data, "Missing period_days in response"
        assert "total_refunds" in data, "Missing total_refunds in response"
        assert "total_credits_refunded" in data, "Missing total_credits_refunded"
        print(f"✓ Refund stats: {data.get('total_refunds')} refunds, {data.get('total_credits_refunded')} credits refunded")
    
    def test_refund_stats_requires_admin(self, demo_token):
        """Test refund-stats requires admin role"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/system/refund-stats", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Refund stats correctly requires admin role")
    
    def test_self_healing_status_endpoint(self, admin_token):
        """Test /api/admin/system/self-healing-status endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/system/self-healing-status", headers=headers)
        assert response.status_code == 200, f"Self-healing status failed: {response.text}"
        data = response.json()
        # Verify response structure
        assert "is_active" in data, "Missing is_active in response"
        assert "healing_in_progress" in data, "Missing healing_in_progress"
        print(f"✓ Self-healing status: active={data.get('is_active')}, issues_24h={data.get('issues_last_24h', 0)}")
    
    def test_self_healing_status_requires_admin(self, demo_token):
        """Test self-healing-status requires admin role"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/system/self-healing-status", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Self-healing status correctly requires admin role")
    
    def test_system_health_endpoint(self, admin_token):
        """Test /api/admin/system/system-health endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/system/system-health", headers=headers)
        assert response.status_code == 200, f"System health failed: {response.text}"
        data = response.json()
        # Verify response structure
        assert "status" in data, "Missing status in response"
        assert "metrics" in data, "Missing metrics in response"
        assert "timestamp" in data, "Missing timestamp"
        metrics = data.get("metrics", {})
        print(f"✓ System health: {data.get('status')}, error_rate={metrics.get('error_rate_percent', 0)}%")
    
    def test_system_health_requires_admin(self, demo_token):
        """Test system-health requires admin role"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/system/system-health", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ System health correctly requires admin role")


class TestComicStorybookV2:
    """Comic Storybook V2 endpoint tests"""
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        """Get demo user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Demo login failed")
        return response.json().get("token")
    
    def test_get_genres(self, demo_token):
        """Test /api/comic-storybook-v2/genres endpoint"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/genres", headers=headers)
        assert response.status_code == 200, f"Genres endpoint failed: {response.text}"
        data = response.json()
        assert "genres" in data, "Missing genres in response"
        assert "pricing" in data, "Missing pricing in response"
        genres = data.get("genres", {})
        assert len(genres) > 0, "No genres returned"
        print(f"✓ Comic genres: {len(genres)} genres available")
    
    def test_get_pricing(self, demo_token):
        """Test /api/comic-storybook-v2/pricing endpoint"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/pricing", headers=headers)
        assert response.status_code == 200, f"Pricing endpoint failed: {response.text}"
        data = response.json()
        assert "pricing" in data, "Missing pricing in response"
        pricing = data.get("pricing", {})
        assert "pages" in pricing, "Missing pages pricing"
        print(f"✓ Comic pricing loaded successfully")
    
    def test_preview_blocked_content(self, demo_token):
        """Test preview endpoint blocks copyrighted content"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/preview",
            headers=headers,
            json={
                "genre": "kids_adventure",
                "storyIdea": "A story about Spider-Man saving the city",
                "title": "My Comic",
                "pageCount": 10
            }
        )
        assert response.status_code == 400, f"Expected 400 for blocked content, got {response.status_code}"
        print(f"✓ Comic preview correctly blocks copyrighted content (Spider-Man)")
    
    def test_history_endpoint(self, demo_token):
        """Test /api/comic-storybook-v2/history endpoint"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/history", headers=headers)
        assert response.status_code == 200, f"History endpoint failed: {response.text}"
        data = response.json()
        assert "jobs" in data, "Missing jobs in response"
        assert "total" in data, "Missing total in response"
        print(f"✓ Comic history: {data.get('total', 0)} jobs found")


class TestUserProfileAndCredits:
    """User profile and credits tests"""
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        """Get demo user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Demo login failed")
        return response.json().get("token")
    
    def test_credits_balance(self, demo_token):
        """Test credits balance endpoint"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200, f"Credits balance failed: {response.text}"
        data = response.json()
        assert "credits" in data, "Missing credits in response"
        print(f"✓ Credits balance: {data.get('credits')} credits")
    
    def test_auth_me_endpoint(self, demo_token):
        """Test /api/auth/me endpoint"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        assert "user" in data, "Missing user in response"
        user = data.get("user", {})
        assert "email" in user, "Missing email in user"
        print(f"✓ Auth/me: {user.get('email')}")


class TestSelfHealingActivation:
    """Test self-healing activation/deactivation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json().get("token")
    
    def test_activate_self_healing(self, admin_token):
        """Test activating self-healing system"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/system/self-healing/activate", headers=headers)
        assert response.status_code == 200, f"Activate self-healing failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Activation did not succeed"
        print(f"✓ Self-healing activation: {data.get('message')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
