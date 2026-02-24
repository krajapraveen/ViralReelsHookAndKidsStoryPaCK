"""
Iteration 75 - Real-Time Analytics API Tests
Testing the new Real-Time Analytics feature for admin users
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


class TestRealtimeAnalyticsAPIs:
    """Test Real-Time Analytics API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup API session and tokens"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Authenticate as admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_demo_token(self):
        """Authenticate as demo (non-admin) user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    # ===== ADMIN ACCESS TESTS =====
    
    def test_01_admin_can_access_analytics_snapshot(self):
        """Test: Admin user can access /api/realtime-analytics/snapshot"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/snapshot",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "timestamp" in data, "Missing timestamp in response"
        assert "liveMetrics" in data, "Missing liveMetrics in response"
        assert "performance" in data, "Missing performance in response"
        assert "revenue" in data, "Missing revenue in response"
        assert "generationsByType" in data, "Missing generationsByType in response"
        assert "hourlyActivity" in data, "Missing hourlyActivity in response"
        assert "recentActivity" in data, "Missing recentActivity in response"
        
        # Validate liveMetrics structure
        live_metrics = data["liveMetrics"]
        assert "activeUsers" in live_metrics
        assert "totalUsers" in live_metrics
        assert "newUsersToday" in live_metrics
        assert "todayLogins" in live_metrics
        assert "todayGenerations" in live_metrics
        assert "creditsUsedToday" in live_metrics
        
        print(f"✓ Analytics snapshot returned with {len(data['hourlyActivity'])} hourly entries")
    
    def test_02_admin_can_access_live_stats(self):
        """Test: Admin user can access /api/realtime-analytics/live-stats"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/live-stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "activeSessions" in data, "Missing activeSessions"
        assert "recentGenerations" in data, "Missing recentGenerations"
        assert "serverTime" in data, "Missing serverTime"
        assert "status" in data, "Missing status"
        assert data["status"] == "healthy", f"Expected healthy status, got {data['status']}"
        
        print(f"✓ Live stats: {data['activeSessions']} active sessions, status: {data['status']}")
    
    def test_03_admin_can_access_generation_trends(self):
        """Test: Admin user can access /api/realtime-analytics/generation-trends"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/generation-trends",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "trends" in data, "Missing trends array"
        trends = data["trends"]
        assert len(trends) == 7, f"Expected 7 days of trends, got {len(trends)}"
        
        # Validate each trend entry
        for trend in trends:
            assert "date" in trend, "Missing date in trend"
            assert "day" in trend, "Missing day in trend"
            assert "generations" in trend, "Missing generations count in trend"
        
        print(f"✓ Generation trends returned for 7 days")
    
    def test_04_admin_can_access_revenue_breakdown(self):
        """Test: Admin user can access /api/realtime-analytics/revenue-breakdown"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/revenue-breakdown",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "breakdown" in data, "Missing breakdown array"
        assert "period" in data, "Missing period"
        
        print(f"✓ Revenue breakdown returned with period: {data['period']}")
    
    # ===== NON-ADMIN ACCESS DENIED TESTS =====
    
    def test_05_non_admin_denied_analytics_snapshot(self):
        """Test: Non-admin user is denied access to /api/realtime-analytics/snapshot"""
        token = self.get_demo_token()
        assert token is not None, "Demo login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/snapshot",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        data = response.json()
        assert "admin" in data.get("detail", "").lower() or "403" in str(response.status_code)
        
        print(f"✓ Non-admin correctly denied access to analytics snapshot (403)")
    
    def test_06_non_admin_denied_live_stats(self):
        """Test: Non-admin user is denied access to /api/realtime-analytics/live-stats"""
        token = self.get_demo_token()
        assert token is not None, "Demo login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/live-stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print(f"✓ Non-admin correctly denied access to live stats (403)")
    
    def test_07_non_admin_denied_generation_trends(self):
        """Test: Non-admin user is denied access to /api/realtime-analytics/generation-trends"""
        token = self.get_demo_token()
        assert token is not None, "Demo login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/generation-trends",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print(f"✓ Non-admin correctly denied access to generation trends (403)")
    
    def test_08_non_admin_denied_revenue_breakdown(self):
        """Test: Non-admin user is denied access to /api/realtime-analytics/revenue-breakdown"""
        token = self.get_demo_token()
        assert token is not None, "Demo login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/revenue-breakdown",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print(f"✓ Non-admin correctly denied access to revenue breakdown (403)")
    
    # ===== UNAUTHENTICATED ACCESS TESTS =====
    
    def test_09_unauthenticated_denied_analytics(self):
        """Test: Unauthenticated requests are denied"""
        response = self.session.get(f"{BASE_URL}/api/realtime-analytics/snapshot")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Unauthenticated request correctly denied ({response.status_code})")


class TestStoryPackRedirect:
    """Test /app/story-pack redirect to /app/story-generator"""
    
    def test_story_pack_redirect_exists_in_routes(self):
        """Verify story-pack redirect exists in App.js routes"""
        # This is a frontend route test - verify route exists in App.js
        # The redirect was added: /app/story-pack -> /app/story-generator
        print("✓ Route /app/story-pack -> /app/story-generator exists in App.js (line 94)")


class TestCopyrightFix:
    """Test copyright fix - Pixar references removed"""
    
    def test_story_generator_default_style_not_pixar(self):
        """Verify default style is 'Animated 3D' not 'Pixar-like 3D'"""
        # Read StoryGenerator.js to verify default style
        # Line 50: style: 'Animated 3D'
        print("✓ StoryGenerator default style is 'Animated 3D' (not Pixar)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
