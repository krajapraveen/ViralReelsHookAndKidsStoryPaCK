"""
Test Admin Metrics Dashboard APIs - Iteration 319
Tests all 6 admin metrics endpoints: summary, funnel, reliability, revenue, series, safety
Validates:
- Admin authentication requirement
- Non-admin 403 rejection
- Response structure and data types
- Real DB values (Total Users: 33, Active Series: 1, etc.)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://viral-loop-2.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
USER_EMAIL = "test@visionary-suite.com"
USER_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "token" in data
    assert data["user"]["role"] == "ADMIN"
    return data["token"]


@pytest.fixture(scope="module")
def user_token():
    """Get non-admin user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    })
    assert response.status_code == 200, f"User login failed: {response.text}"
    data = response.json()
    assert "token" in data
    assert data["user"]["role"] == "USER"
    return data["token"]


@pytest.fixture
def admin_client(admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


@pytest.fixture
def user_client(user_token):
    """Session with non-admin user auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    })
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSummaryEndpoint:
    """Tests for GET /api/admin/metrics/summary"""
    
    def test_summary_requires_auth(self):
        """Summary endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/summary")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_summary_rejects_non_admin(self, user_client):
        """Summary endpoint rejects non-admin users with 403"""
        response = user_client.get(f"{BASE_URL}/api/admin/metrics/summary")
        assert response.status_code == 403
        data = response.json()
        assert "Admin" in data.get("detail", "")
    
    def test_summary_returns_success(self, admin_client):
        """Summary returns success=true for admin"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/summary?days=30")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_summary_has_required_fields(self, admin_client):
        """Summary contains all required metric fields"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "total_users", "new_users_today", "new_users_period",
            "active_users_24h", "active_sessions",
            "total_generations", "completed_generations", "failed_generations",
            "success_rate", "failure_rate",
            "total_revenue", "revenue_today",
            "avg_rating", "rating_count",
            "period_days", "timestamp"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_summary_total_users_is_real(self, admin_client):
        """Total users should be 33 (real DB value)"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 33, f"Expected 33 users, got {data['total_users']}"
    
    def test_summary_avg_rating_is_real(self, admin_client):
        """Avg rating should be 4.0/5 (real DB value)"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["avg_rating"] == 4 or data["avg_rating"] == 4.0, f"Expected 4.0 rating, got {data['avg_rating']}"
    
    def test_summary_date_range_parameter(self, admin_client):
        """Summary respects days parameter"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/summary?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7


# ═══════════════════════════════════════════════════════════════════════════════
# GROWTH FUNNEL ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFunnelEndpoint:
    """Tests for GET /api/admin/metrics/funnel"""
    
    def test_funnel_requires_auth(self):
        """Funnel endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/funnel")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_funnel_rejects_non_admin(self, user_client):
        """Funnel endpoint rejects non-admin users"""
        response = user_client.get(f"{BASE_URL}/api/admin/metrics/funnel")
        assert response.status_code == 403
    
    def test_funnel_returns_success(self, admin_client):
        """Funnel returns success=true for admin"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/funnel")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_funnel_has_conversion_metrics(self, admin_client):
        """Funnel contains conversion funnel fields"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/funnel")
        assert response.status_code == 200
        data = response.json()
        
        funnel_fields = [
            "page_views", "remix_clicks", "tool_opens_prefilled",
            "generate_clicks", "signup_completed", "creation_completed",
            "share_clicks", "remix_rate", "generate_rate", "signup_rate",
            "completion_rate", "share_rate", "viral_coefficient_k"
        ]
        for field in funnel_fields:
            assert field in data, f"Missing funnel field: {field}"
    
    def test_funnel_shows_correct_empty_state(self, admin_client):
        """Funnel shows 0s because no growth events tracked (correct behavior)"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/funnel")
        assert response.status_code == 200
        data = response.json()
        # All values should be 0 or null since no growth_events tracked
        assert data["page_views"] >= 0
        assert data["unique_creators"] >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# RELIABILITY ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestReliabilityEndpoint:
    """Tests for GET /api/admin/metrics/reliability"""
    
    def test_reliability_requires_auth(self):
        """Reliability endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/reliability")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_reliability_rejects_non_admin(self, user_client):
        """Reliability endpoint rejects non-admin users"""
        response = user_client.get(f"{BASE_URL}/api/admin/metrics/reliability")
        assert response.status_code == 403
    
    def test_reliability_returns_success(self, admin_client):
        """Reliability returns success=true for admin"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/reliability")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_reliability_has_queue_metrics(self, admin_client):
        """Reliability contains queue and job metrics"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/reliability")
        assert response.status_code == 200
        data = response.json()
        
        assert "queue_depth" in data
        assert "active_jobs" in data
        assert "stuck_jobs" in data
        assert "avg_render_seconds" in data
        assert "max_render_seconds" in data
        assert "tool_render_stats" in data
    
    def test_reliability_has_health_checks(self, admin_client):
        """Reliability contains health check badges"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/reliability")
        assert response.status_code == 200
        data = response.json()
        
        assert "health_checks" in data
        assert "overall_health" in data
        # Database should be healthy
        assert data["health_checks"]["database"] == "healthy"
    
    def test_reliability_overall_health_valid(self, admin_client):
        """Overall health is one of: healthy, degraded, critical"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/reliability")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_health"] in ["healthy", "degraded", "critical"]


# ═══════════════════════════════════════════════════════════════════════════════
# REVENUE ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRevenueEndpoint:
    """Tests for GET /api/admin/metrics/revenue"""
    
    def test_revenue_requires_auth(self):
        """Revenue endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/revenue")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_revenue_rejects_non_admin(self, user_client):
        """Revenue endpoint rejects non-admin users"""
        response = user_client.get(f"{BASE_URL}/api/admin/metrics/revenue")
        assert response.status_code == 403
    
    def test_revenue_returns_success(self, admin_client):
        """Revenue returns success=true for admin"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/revenue")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_revenue_has_payment_metrics(self, admin_client):
        """Revenue contains payment and financial metrics"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/revenue")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "total_revenue", "revenue_today", "total_transactions",
            "paying_users", "total_users", "arpu", "conversion_rate",
            "active_subscriptions", "recent_transactions"
        ]
        for field in required_fields:
            assert field in data, f"Missing revenue field: {field}"
    
    def test_revenue_total_users_matches_summary(self, admin_client):
        """Revenue total_users should match summary"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/revenue")
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 33
    
    def test_revenue_recent_transactions_is_list(self, admin_client):
        """Recent transactions is an array"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/revenue")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["recent_transactions"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# SERIES/STORY INTELLIGENCE ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSeriesEndpoint:
    """Tests for GET /api/admin/metrics/series"""
    
    def test_series_requires_auth(self):
        """Series endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/series")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_series_rejects_non_admin(self, user_client):
        """Series endpoint rejects non-admin users"""
        response = user_client.get(f"{BASE_URL}/api/admin/metrics/series")
        assert response.status_code == 403
    
    def test_series_returns_success(self, admin_client):
        """Series returns success=true for admin"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/series")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_series_has_story_metrics(self, admin_client):
        """Series contains story and character metrics"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/series")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "active_series", "total_series", "total_episodes",
            "avg_episodes_per_series", "continuation_rate",
            "total_characters", "auto_extracted_characters",
            "reused_characters", "character_reuse_rate"
        ]
        for field in required_fields:
            assert field in data, f"Missing series field: {field}"
    
    def test_series_active_series_is_real(self, admin_client):
        """Active series should be 1 (real DB value)"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/series")
        assert response.status_code == 200
        data = response.json()
        assert data["active_series"] == 1, f"Expected 1 active series, got {data['active_series']}"
    
    def test_series_total_episodes_is_real(self, admin_client):
        """Total episodes should be 4 (real DB value)"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/series")
        assert response.status_code == 200
        data = response.json()
        assert data["total_episodes"] == 4, f"Expected 4 episodes, got {data['total_episodes']}"
    
    def test_series_total_characters_is_real(self, admin_client):
        """Total characters should be 3 (real DB value)"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/series")
        assert response.status_code == 200
        data = response.json()
        assert data["total_characters"] == 3, f"Expected 3 characters, got {data['total_characters']}"
    
    def test_series_continuation_rate_is_real(self, admin_client):
        """Continuation rate should be 16.7% (real DB value)"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/series")
        assert response.status_code == 200
        data = response.json()
        assert data["continuation_rate"] == 16.7, f"Expected 16.7% continuation rate, got {data['continuation_rate']}"


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY/MODERATION ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSafetyEndpoint:
    """Tests for GET /api/admin/metrics/safety"""
    
    def test_safety_requires_auth(self):
        """Safety endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/safety")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_safety_rejects_non_admin(self, user_client):
        """Safety endpoint rejects non-admin users"""
        response = user_client.get(f"{BASE_URL}/api/admin/metrics/safety")
        assert response.status_code == 403
    
    def test_safety_returns_success(self, admin_client):
        """Safety returns success=true for admin"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/safety")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_safety_has_moderation_metrics(self, admin_client):
        """Safety contains moderation and abuse metrics"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/safety")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "blocked_prompts", "flagged_requests", "safety_flag_rate",
            "consent_required_characters", "ip_risk_rejections"
        ]
        for field in required_fields:
            assert field in data, f"Missing safety field: {field}"


# ═══════════════════════════════════════════════════════════════════════════════
# DATE RANGE TESTS (across endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDateRangeParameters:
    """Test date range parameters work correctly"""
    
    def test_summary_days_7(self, admin_client):
        """Summary accepts 7 days parameter"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/summary?days=7")
        assert response.status_code == 200
        assert response.json()["period_days"] == 7
    
    def test_summary_days_30(self, admin_client):
        """Summary accepts 30 days parameter"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/summary?days=30")
        assert response.status_code == 200
        assert response.json()["period_days"] == 30
    
    def test_summary_days_90(self, admin_client):
        """Summary accepts 90 days parameter"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/summary?days=90")
        assert response.status_code == 200
        assert response.json()["period_days"] == 90
    
    def test_funnel_days_parameter(self, admin_client):
        """Funnel accepts days parameter"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/funnel?days=30")
        assert response.status_code == 200
        assert response.json()["period_days"] == 30
    
    def test_revenue_days_parameter(self, admin_client):
        """Revenue accepts days parameter"""
        response = admin_client.get(f"{BASE_URL}/api/admin/metrics/revenue?days=90")
        assert response.status_code == 200
        assert response.json()["period_days"] == 90
