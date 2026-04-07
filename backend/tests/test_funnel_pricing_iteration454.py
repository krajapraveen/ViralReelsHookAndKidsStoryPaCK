"""
Funnel Tracking & Pricing API Tests - Iteration 454
Tests for:
- GET /api/pricing-catalog/plans (plans + topups)
- POST /api/funnel/track (all 11 funnel steps)
- GET /api/funnel/metrics (admin only)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
USER_EMAIL = "test@visionary-suite.com"
USER_PASSWORD = "Test@2026#"

# All 11 funnel steps
FUNNEL_STEPS = [
    "landing_view",
    "first_action_click",
    "generation_started",
    "generation_completed",
    "result_viewed",
    "second_action",
    "paywall_viewed",
    "plan_selected",
    "payment_started",
    "payment_abandoned",
    "payment_success",
]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def user_token():
    """Get regular user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("User authentication failed")


class TestPricingCatalogAPI:
    """Tests for GET /api/pricing-catalog/plans"""

    def test_get_plans_returns_200(self):
        """Pricing catalog endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/pricing-catalog/plans")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_plans_structure(self):
        """Plans have correct structure (id, name, period, price_inr, credits, features, badge)"""
        response = requests.get(f"{BASE_URL}/api/pricing-catalog/plans")
        data = response.json()
        plans = data.get("plans", [])
        
        assert len(plans) >= 4, "Should have at least 4 subscription plans"
        
        for plan in plans:
            assert "id" in plan, f"Plan missing 'id': {plan}"
            assert "name" in plan, f"Plan missing 'name': {plan}"
            assert "period" in plan, f"Plan missing 'period': {plan}"
            assert "price_inr" in plan, f"Plan missing 'price_inr': {plan}"
            assert "credits" in plan, f"Plan missing 'credits': {plan}"
            assert "features" in plan, f"Plan missing 'features': {plan}"
            assert "badge" in plan, f"Plan missing 'badge': {plan}"
            assert isinstance(plan["features"], list), "Features should be a list"

    def test_topups_structure(self):
        """Topups have correct structure (id, name, credits, price_inr, popular)"""
        response = requests.get(f"{BASE_URL}/api/pricing-catalog/plans")
        data = response.json()
        topups = data.get("topups", [])
        
        assert len(topups) >= 4, "Should have at least 4 topup packs"
        
        for topup in topups:
            assert "id" in topup, f"Topup missing 'id': {topup}"
            assert "name" in topup, f"Topup missing 'name': {topup}"
            assert "credits" in topup, f"Topup missing 'credits': {topup}"
            assert "price_inr" in topup, f"Topup missing 'price_inr': {topup}"
            assert "popular" in topup, f"Topup missing 'popular': {topup}"

    def test_plans_have_expected_periods(self):
        """Plans include weekly, monthly, quarterly, yearly"""
        response = requests.get(f"{BASE_URL}/api/pricing-catalog/plans")
        data = response.json()
        plans = data.get("plans", [])
        
        periods = [p["period"] for p in plans]
        assert "weekly" in periods, "Missing weekly plan"
        assert "monthly" in periods, "Missing monthly plan"
        assert "quarterly" in periods, "Missing quarterly plan"
        assert "yearly" in periods, "Missing yearly plan"

    def test_monthly_plan_has_popular_badge(self):
        """Monthly plan should have POPULAR badge"""
        response = requests.get(f"{BASE_URL}/api/pricing-catalog/plans")
        data = response.json()
        plans = data.get("plans", [])
        
        monthly = next((p for p in plans if p["period"] == "monthly"), None)
        assert monthly is not None, "Monthly plan not found"
        assert monthly.get("badge") == "POPULAR", "Monthly plan should have POPULAR badge"


class TestFunnelTrackingAPI:
    """Tests for POST /api/funnel/track"""

    def test_track_landing_view(self):
        """Track landing_view event"""
        session_id = f"test-{uuid.uuid4()}"
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "landing_view",
            "session_id": session_id,
            "context": {
                "source_page": "landing",
                "device": "desktop"
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert data.get("session_id") == session_id

    def test_track_all_11_funnel_steps(self):
        """All 11 funnel steps are accepted"""
        session_id = f"test-all-{uuid.uuid4()}"
        
        for step in FUNNEL_STEPS:
            response = requests.post(f"{BASE_URL}/api/funnel/track", json={
                "step": step,
                "session_id": session_id,
                "context": {
                    "source_page": "test",
                    "device": "desktop",
                    "generation_count": 1,
                    "plan_shown": "monthly",
                    "plan_selected": "monthly"
                }
            })
            assert response.status_code == 200, f"Step {step} failed with {response.status_code}"
            data = response.json()
            assert data.get("success") is True, f"Step {step} returned success=False"

    def test_track_invalid_step_rejected(self):
        """Invalid funnel step is rejected"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "invalid_step_xyz",
            "session_id": f"test-{uuid.uuid4()}",
            "context": {}
        })
        assert response.status_code == 200  # API returns 200 with success=False
        data = response.json()
        assert data.get("success") is False
        assert "Invalid step" in data.get("error", "")

    def test_track_with_context_fields(self):
        """Track event with all context fields"""
        session_id = f"test-ctx-{uuid.uuid4()}"
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "paywall_viewed",
            "session_id": session_id,
            "user_id": "test-user-123",
            "context": {
                "source_page": "studio",
                "device": "mobile",
                "generation_count": 3,
                "plan_shown": "quarterly",
                "plan_selected": None,
                "meta": {"reason": "credit_limit"}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_track_generates_session_id_if_missing(self):
        """Session ID is generated if not provided"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "landing_view",
            "context": {"source_page": "landing"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert data.get("session_id") is not None


class TestFunnelMetricsAPI:
    """Tests for GET /api/funnel/metrics (admin only)"""

    def test_metrics_requires_auth(self):
        """Metrics endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/funnel/metrics")
        assert response.status_code in [401, 403]

    def test_metrics_rejects_non_admin(self, user_token):
        """Non-admin users are rejected with 403"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/metrics",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
        data = response.json()
        assert "Admin access required" in data.get("detail", "")

    def test_metrics_returns_200_for_admin(self, admin_token):
        """Admin can access metrics"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_metrics_structure(self, admin_token):
        """Metrics response has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Check top-level fields
        assert "period_days" in data
        assert "total_sessions" in data
        assert "total_users" in data
        assert "funnel" in data
        assert "device_breakdown" in data
        assert "source_breakdown" in data
        assert "paywall_micro_funnel" in data

    def test_metrics_funnel_has_all_steps(self, admin_token):
        """Funnel array contains all 11 steps"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        funnel = data.get("funnel", [])
        
        funnel_steps = [f["step"] for f in funnel]
        for step in FUNNEL_STEPS:
            assert step in funnel_steps, f"Missing step in funnel: {step}"

    def test_metrics_funnel_step_structure(self, admin_token):
        """Each funnel step has count, conversion_from_top_pct, drop_off_from_prev_pct"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        funnel = data.get("funnel", [])
        
        for step_data in funnel:
            assert "step" in step_data
            assert "count" in step_data
            assert "conversion_from_top_pct" in step_data
            assert "drop_off_from_prev_pct" in step_data

    def test_metrics_paywall_micro_funnel(self, admin_token):
        """Paywall micro funnel contains paywall-specific steps"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        paywall_funnel = data.get("paywall_micro_funnel", [])
        
        paywall_steps = [p["step"] for p in paywall_funnel]
        expected = ["paywall_viewed", "plan_selected", "payment_started", "payment_abandoned", "payment_success"]
        for step in expected:
            assert step in paywall_steps, f"Missing paywall step: {step}"

    def test_metrics_with_days_param(self, admin_token):
        """Metrics endpoint accepts days parameter"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/metrics?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("period_days") == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
