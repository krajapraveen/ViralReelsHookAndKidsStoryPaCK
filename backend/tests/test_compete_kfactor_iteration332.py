"""
Iteration 332: Compete Mechanics, Animated Social Proof, ForceShareGate, K-Factor Admin Dashboard, Email Nudges
Tests for:
1. GET /api/compete/trending - Trending stories (truth-based, no synthetic data)
2. GET /api/compete/live-viewers - Real session count
3. POST /api/retention/test-email - Admin-only test nudge email
4. GET /api/retention/admin/email-nudges - Email nudge status with Resend active
5. GET /api/growth/viral-coefficient - K-factor metrics
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


class TestCompeteTrending:
    """Tests for GET /api/compete/trending endpoint"""

    def test_trending_endpoint_returns_success(self):
        """Test that trending endpoint returns success response"""
        response = requests.get(f"{BASE_URL}/api/compete/trending")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success: true"
        assert "has_data" in data, "Expected has_data field"
        
    def test_trending_endpoint_structure(self):
        """Test that trending endpoint returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/compete/trending")
        assert response.status_code == 200
        
        data = response.json()
        # Check all expected fields exist
        assert "top_story_today" in data, "Expected top_story_today field"
        assert "most_continued" in data, "Expected most_continued field"
        assert "fastest_character" in data, "Expected fastest_character field"
        assert "rising_stories" in data, "Expected rising_stories field"
        
    def test_trending_has_data_is_boolean(self):
        """Test that has_data is a boolean (truth-based)"""
        response = requests.get(f"{BASE_URL}/api/compete/trending")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data.get("has_data"), bool), "has_data should be boolean"
        
    def test_trending_rising_stories_is_list(self):
        """Test that rising_stories is a list"""
        response = requests.get(f"{BASE_URL}/api/compete/trending")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data.get("rising_stories"), list), "rising_stories should be a list"


class TestCompeteLiveViewers:
    """Tests for GET /api/compete/live-viewers endpoint"""

    def test_live_viewers_endpoint_returns_success(self):
        """Test that live-viewers endpoint returns success response"""
        response = requests.get(f"{BASE_URL}/api/compete/live-viewers")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success: true"
        
    def test_live_viewers_structure(self):
        """Test that live-viewers endpoint returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/compete/live-viewers")
        assert response.status_code == 200
        
        data = response.json()
        assert "viewers" in data, "Expected viewers field"
        assert "show" in data, "Expected show field"
        
    def test_live_viewers_count_is_integer(self):
        """Test that viewers count is an integer (real count, not fake)"""
        response = requests.get(f"{BASE_URL}/api/compete/live-viewers")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data.get("viewers"), int), "viewers should be an integer"
        assert data.get("viewers") >= 0, "viewers should be non-negative"
        
    def test_live_viewers_show_is_boolean(self):
        """Test that show field is boolean"""
        response = requests.get(f"{BASE_URL}/api/compete/live-viewers")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data.get("show"), bool), "show should be boolean"


class TestEmailNudgeAdmin:
    """Tests for email nudge admin endpoints"""

    def test_email_nudge_status_requires_auth(self):
        """Test that email nudge status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/retention/admin/email-nudges")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        
    def test_email_nudge_status_requires_admin(self, test_user_token):
        """Test that email nudge status requires admin role"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/admin/email-nudges", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        
    def test_email_nudge_status_admin_access(self, admin_token):
        """Test that admin can access email nudge status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/admin/email-nudges", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success: true"
        
    def test_email_nudge_status_structure(self, admin_token):
        """Test email nudge status response structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/admin/email-nudges", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "email_service_active" in data, "Expected email_service_active field"
        assert "pending_count" in data, "Expected pending_count field"
        assert "sent_count" in data, "Expected sent_count field"
        
    def test_email_nudge_resend_active(self, admin_token):
        """Test that Resend is active (RESEND_API_KEY is set)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/admin/email-nudges", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # RESEND_API_KEY is set in backend/.env, so email_service_active should be True
        assert data.get("email_service_active") is True, "Expected email_service_active: true (RESEND_API_KEY is set)"


class TestTestEmailEndpoint:
    """Tests for POST /api/retention/test-email endpoint"""

    def test_test_email_requires_auth(self):
        """Test that test-email requires authentication"""
        response = requests.post(f"{BASE_URL}/api/retention/test-email", json={
            "to": "test@example.com",
            "character": "Finn",
            "hook": "But something followed him..."
        })
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        
    def test_test_email_requires_admin(self, test_user_token):
        """Test that test-email requires admin role"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/retention/test-email", json={
            "to": "test@example.com",
            "character": "Finn",
            "hook": "But something followed him..."
        }, headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        
    def test_test_email_admin_access(self, admin_token):
        """Test that admin can send test email"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Note: Resend sandbox mode only allows sending to krajapraveen@gmail.com
        response = requests.post(f"{BASE_URL}/api/retention/test-email", json={
            "to": "krajapraveen@gmail.com",
            "character": "Finn",
            "hook": "But something followed him..."
        }, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return success or message about email status
        assert "success" in data or "message" in data, "Expected success or message field"


class TestViralCoefficient:
    """Tests for GET /api/growth/viral-coefficient endpoint"""

    def test_viral_coefficient_endpoint_exists(self):
        """Test that viral-coefficient endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_viral_coefficient_structure(self):
        """Test viral-coefficient response structure"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient")
        assert response.status_code == 200
        
        data = response.json()
        # K-factor endpoint returns data without success:true wrapper
        assert "viral_coefficient_K" in data, "Expected viral_coefficient_K field"
        
    def test_viral_coefficient_with_days_param(self):
        """Test viral-coefficient with days parameter"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient?days=30")
        assert response.status_code == 200
        
        data = response.json()
        assert "viral_coefficient_K" in data, "Expected viral_coefficient_K field"
        
    def test_viral_coefficient_k_is_numeric(self):
        """Test that K-factor is a numeric value"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient")
        assert response.status_code == 200
        
        data = response.json()
        k_value = data.get("viral_coefficient_K")
        assert isinstance(k_value, (int, float)), f"K-factor should be numeric, got {type(k_value)}"
        
    def test_viral_coefficient_has_components(self):
        """Test that viral-coefficient has components breakdown"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient")
        assert response.status_code == 200
        
        data = response.json()
        assert "components" in data, "Expected components field"
        
    def test_viral_coefficient_has_interpretation(self):
        """Test that viral-coefficient has interpretation"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient")
        assert response.status_code == 200
        
        data = response.json()
        assert "interpretation" in data, "Expected interpretation field"


class TestHealthCheck:
    """Basic health check tests"""

    def test_api_health(self):
        """Test that API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"API health check failed: {response.status_code}"
        
    def test_compete_routes_registered(self):
        """Test that compete routes are registered"""
        # Test trending endpoint
        response = requests.get(f"{BASE_URL}/api/compete/trending")
        assert response.status_code != 404, "Compete trending route not found"
        
        # Test live-viewers endpoint
        response = requests.get(f"{BASE_URL}/api/compete/live-viewers")
        assert response.status_code != 404, "Compete live-viewers route not found"
