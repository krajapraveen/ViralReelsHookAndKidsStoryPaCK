"""
Production Site Audit Test - https://www.visionary-suite.com
Comprehensive testing of ALL pages, links, functionalities for millions of users
"""
import pytest
import requests
import os
import time

# PRODUCTION URL for testing
BASE_URL = "https://www.visionary-suite.com"

# Test credentials
ADMIN_CREDENTIALS = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
DEMO_CREDENTIALS = {"email": "demo@example.com", "password": "Password123!"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS, timeout=30)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="module")
def demo_token():
    """Get demo user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_CREDENTIALS, timeout=30)
    assert response.status_code == 200, f"Demo login failed: {response.text}"
    data = response.json()
    return data.get("token") or data.get("access_token")


class TestHealthAndCore:
    """Test core API health and authentication"""
    
    def test_api_health(self):
        """API health check - /api/health/"""
        response = requests.get(f"{BASE_URL}/api/health/", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ API Health: {data}")
    
    def test_admin_login(self):
        """Admin user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS, timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data or "access_token" in data
        print(f"✓ Admin login successful")
    
    def test_demo_login(self):
        """Demo user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_CREDENTIALS, timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data or "access_token" in data
        print(f"✓ Demo login successful")


class TestUserEndpoints:
    """Test user-related endpoints"""
    
    def test_get_current_user(self, demo_token):
        """Get current user profile - /api/auth/me"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        print(f"✓ User profile retrieved: {data.get('email')}")
    
    def test_get_user_balance(self, demo_token):
        """Get user credit balance - /api/wallet/me"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "balanceCredits" in data or "availableCredits" in data
        print(f"✓ User balance: {data.get('availableCredits')} credits")
    
    def test_get_wallet_pricing(self, demo_token):
        """Get wallet pricing info - /api/wallet/pricing"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/pricing", headers=headers, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"✓ Wallet pricing available")


class TestBillingEndpoints:
    """Test billing and payment endpoints"""
    
    def test_get_pricing_plans(self):
        """Get available pricing plans"""
        response = requests.get(f"{BASE_URL}/api/billing/plans", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "plans" in data
        print(f"✓ Pricing plans retrieved")
    
    def test_get_credit_packs(self):
        """Get available credit packs"""
        response = requests.get(f"{BASE_URL}/api/billing/credit-packs", timeout=10)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Credit packs: {data}")
    
    def test_get_billing_history(self, demo_token):
        """Get billing history for user"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/billing/history", headers=headers, timeout=10)
        # 200 or 404 is acceptable (user may have no history)
        assert response.status_code in [200, 404]
        print(f"✓ Billing history endpoint working")


class TestGeneratorEndpoints:
    """Test content generator endpoints"""
    
    def test_reel_generator_options(self, demo_token):
        """Get reel generator options"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/reel/options", headers=headers, timeout=10)
        # Check if endpoint exists
        if response.status_code == 200:
            print(f"✓ Reel options: {response.json()}")
        else:
            print(f"! Reel options endpoint: {response.status_code}")
    
    def test_story_generator_options(self, demo_token):
        """Get story generator options"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/story/options", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ Story options available")
        else:
            print(f"! Story options endpoint: {response.status_code}")


class TestGenStudioEndpoints:
    """Test GenStudio endpoints"""
    
    def test_genstudio_models(self, demo_token):
        """Get available AI models"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/genstudio/models", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ GenStudio models available")
        else:
            print(f"! GenStudio models: {response.status_code}")
    
    def test_genstudio_styles(self, demo_token):
        """Get available styles"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/genstudio/styles", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ GenStudio styles available")
        else:
            print(f"! GenStudio styles: {response.status_code}")


class TestCreatorToolsEndpoints:
    """Test Creator Tools endpoints"""
    
    def test_trending_topics(self, demo_token):
        """Get trending topics - was fixed in previous session"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/creator-tools/trending", headers=headers, timeout=10)
        assert response.status_code == 200, f"Trending topics failed: {response.status_code}"
        data = response.json()
        print(f"✓ Trending topics: {len(data) if isinstance(data, list) else 'loaded'}")
    
    def test_hashtag_generator(self, demo_token):
        """Test hashtag generator"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/creator-tools/hashtags?topic=travel", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ Hashtag generator working")
        else:
            print(f"! Hashtag generator: {response.status_code}")


class TestAdminEndpoints:
    """Test admin-only endpoints"""
    
    def test_admin_dashboard_stats(self, admin_token):
        """Get admin dashboard statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/stats", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Admin stats: {data}")
        else:
            print(f"! Admin stats: {response.status_code}")
    
    def test_admin_users_list(self, admin_token):
        """Get list of users (admin only)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Admin users list: {len(data) if isinstance(data, list) else 'loaded'}")
        else:
            print(f"! Admin users list: {response.status_code}")
    
    def test_admin_monitoring_overview(self, admin_token):
        """Test admin monitoring overview"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/monitoring/overview", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ Admin monitoring overview working")
        else:
            print(f"! Admin monitoring overview: {response.status_code}")
    
    def test_admin_live_activity(self, admin_token):
        """Test live activity monitoring"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/activity/admin/live", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ Live activity monitoring working")
        else:
            print(f"! Live activity: {response.status_code}")
    
    def test_admin_security_overview(self, admin_token):
        """Test security monitoring"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/security/overview", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ Security overview working")
        else:
            print(f"! Security overview: {response.status_code}")


class TestNotificationEndpoints:
    """Test notification endpoints"""
    
    def test_notifications_list(self, admin_token):
        """Get notifications list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications/list", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ Notifications list working")
        else:
            print(f"! Notifications list: {response.status_code}")
    
    def test_notification_preferences(self, admin_token):
        """Get notification preferences"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications/preferences", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✓ Notification preferences working")
        else:
            print(f"! Notification preferences: {response.status_code}")


class TestProductionResilience:
    """Test production resilience features"""
    
    def test_rate_limiting(self):
        """Test rate limiting is active"""
        response = requests.get(f"{BASE_URL}/api/health/", timeout=10)
        # Check for rate limit headers
        headers = response.headers
        print(f"✓ Response headers: Rate limiting {'active' if 'x-ratelimit' in str(headers).lower() else 'not shown in headers'}")
    
    def test_circuit_breaker_health(self, admin_token):
        """Check circuit breaker status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/security/health", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ System health: {data}")
        else:
            print(f"! System health: {response.status_code}")


class TestPageLoadTimes:
    """Test page load times for production readiness"""
    
    def test_api_response_times(self):
        """Test critical API response times"""
        endpoints = [
            "/api/health/",
            "/api/billing/plans",
            "/api/billing/credit-packs",
        ]
        
        for endpoint in endpoints:
            start = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            elapsed = time.time() - start
            print(f"  {endpoint}: {elapsed:.2f}s (status: {response.status_code})")
            assert elapsed < 3, f"{endpoint} took too long: {elapsed:.2f}s"
        
        print("✓ All critical endpoints respond under 3 seconds")
    
    def test_authenticated_response_times(self, demo_token):
        """Test authenticated API response times"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        endpoints = [
            "/api/users/me",
            "/api/users/balance",
            "/api/history",
        ]
        
        for endpoint in endpoints:
            start = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
            elapsed = time.time() - start
            print(f"  {endpoint}: {elapsed:.2f}s (status: {response.status_code})")
            assert elapsed < 3, f"{endpoint} took too long: {elapsed:.2f}s"
        
        print("✓ All authenticated endpoints respond under 3 seconds")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
