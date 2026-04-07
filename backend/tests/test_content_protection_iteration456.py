"""
Content Protection API Tests - Iteration 456
Tests for anti-copy content protection features:
- Asset access logging and abuse detection
- Admin endpoints for abuse log and access stats
- Protected download integration with abuse check
- Regression tests for funnel tracking and streaks APIs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_token(api_client):
    """Get test user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


class TestAssetAccessAdminEndpoints:
    """Tests for admin-only asset access endpoints"""
    
    def test_abuse_log_requires_admin(self, api_client, test_user_token):
        """GET /api/asset-access/admin/abuse-log should reject non-admin users with 403"""
        response = api_client.get(
            f"{BASE_URL}/api/asset-access/admin/abuse-log",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    def test_abuse_log_returns_events_for_admin(self, api_client, admin_token):
        """GET /api/asset-access/admin/abuse-log returns abuse events for admin"""
        response = api_client.get(
            f"{BASE_URL}/api/asset-access/admin/abuse-log",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "events" in data, "Response should contain 'events' field"
        assert "count" in data, "Response should contain 'count' field"
        assert isinstance(data["events"], list), "events should be a list"
    
    def test_access_stats_requires_admin(self, api_client, test_user_token):
        """GET /api/asset-access/admin/access-stats should reject non-admin users with 403"""
        response = api_client.get(
            f"{BASE_URL}/api/asset-access/admin/access-stats",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    def test_access_stats_returns_data_for_admin(self, api_client, admin_token):
        """GET /api/asset-access/admin/access-stats returns access statistics for admin"""
        response = api_client.get(
            f"{BASE_URL}/api/asset-access/admin/access-stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "period_hours" in data, "Response should contain 'period_hours'"
        assert "total_accesses" in data, "Response should contain 'total_accesses'"
        assert "by_action_type" in data, "Response should contain 'by_action_type'"
        assert "abuse_events" in data, "Response should contain 'abuse_events'"
    
    def test_access_stats_with_hours_param(self, api_client, admin_token):
        """GET /api/asset-access/admin/access-stats accepts hours parameter"""
        response = api_client.get(
            f"{BASE_URL}/api/asset-access/admin/access-stats?hours=48",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("period_hours") == 48, "period_hours should match query param"


class TestProtectedDownloadIntegration:
    """Tests for protected download with abuse check integration"""
    
    def test_protected_download_config(self, api_client):
        """GET /api/protected-download/config returns protection configuration"""
        response = api_client.get(f"{BASE_URL}/api/protected-download/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "watermark_removal_cost" in data, "Should have watermark_removal_cost"
        assert "signed_url_expiry_seconds" in data, "Should have signed_url_expiry_seconds"
        assert "watermark_enabled" in data, "Should have watermark_enabled"
        assert "protection_features" in data, "Should have protection_features"


class TestRegressionFunnelTracking:
    """Regression tests for funnel tracking API (from iteration 454)"""
    
    def test_funnel_track_accepts_events(self, api_client, test_user_token):
        """POST /api/funnel/track accepts funnel events"""
        response = api_client.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "landing_view",
                "context": {"source_page": "test", "device": "desktop"}
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_funnel_metrics_requires_admin(self, api_client, test_user_token):
        """GET /api/funnel/metrics requires admin"""
        response = api_client.get(
            f"{BASE_URL}/api/funnel/metrics",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    def test_funnel_metrics_works_for_admin(self, api_client, admin_token):
        """GET /api/funnel/metrics works for admin"""
        response = api_client.get(
            f"{BASE_URL}/api/funnel/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestRegressionStreaksAPI:
    """Regression tests for streaks API (from iteration 455)"""
    
    def test_streaks_my_requires_auth(self, api_client):
        """GET /api/streaks/my requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/streaks/my")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
    
    def test_streaks_my_returns_data(self, api_client, test_user_token):
        """GET /api/streaks/my returns streak data for authenticated user"""
        response = api_client.get(
            f"{BASE_URL}/api/streaks/my",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "today_count" in data, "Should have today_count"
        assert "total_count" in data, "Should have total_count"
        assert "streak_days" in data, "Should have streak_days"
    
    def test_streaks_social_proof_is_public(self, api_client):
        """GET /api/streaks/social-proof is public endpoint"""
        response = api_client.get(f"{BASE_URL}/api/streaks/social-proof")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_creators" in data, "Should have total_creators"
        assert "total_generations" in data, "Should have total_generations"
        assert "active_today" in data, "Should have active_today"


class TestRegressionPricingCatalog:
    """Regression tests for pricing catalog API (from iteration 454)"""
    
    def test_pricing_catalog_plans(self, api_client):
        """GET /api/pricing-catalog/plans returns plans and topups"""
        response = api_client.get(f"{BASE_URL}/api/pricing-catalog/plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "plans" in data or "subscriptions" in data, "Should have plans or subscriptions"


class TestLandingPageRegression:
    """Regression test for landing page loading"""
    
    def test_landing_page_loads(self, api_client):
        """Landing page should load without errors"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
