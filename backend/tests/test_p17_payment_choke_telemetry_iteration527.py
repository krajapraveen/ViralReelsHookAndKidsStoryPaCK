"""
P1.7 Payment Choke-Point Telemetry + Exit-Intent Survey + Paid-Funnel Session-Replay-Lite
Tests for iteration 527

Features tested:
1. GET /api/funnel/revenue-conversion - new metrics (login_redirect_dropoff_pct, cashfree_opened_pct, cashfree_success_pct, cashfree_dropoff_pct)
2. POST /api/funnel/track - new event names (login_page_loaded, cashfree_checkout_opened, cashfree_checkout_failed, checkout_exit_survey_*)
3. POST /api/funnel/checkout-exit-survey - valid/invalid answer handling
4. GET /api/funnel/checkout-exit-survey-summary - admin endpoint
5. GET /api/funnel/paid-funnel-sessions - admin session replay lite
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestRevenueConversionNewMetrics:
    """Test GET /api/funnel/revenue-conversion for P1.7 new metrics"""

    def test_revenue_conversion_returns_success(self, admin_headers):
        """Revenue conversion endpoint returns success"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=90",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_revenue_conversion_has_new_metrics_keys(self, admin_headers):
        """Metrics object contains P1.7 new keys"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=90",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        metrics = data.get("metrics", {})
        
        # P1.7 required metric keys
        required_keys = [
            "login_redirect_dropoff_pct",
            "cashfree_opened_pct",
            "cashfree_success_pct",
            "cashfree_dropoff_pct"
        ]
        for key in required_keys:
            assert key in metrics, f"Missing metric key: {key}"

    def test_revenue_conversion_has_new_totals_keys(self, admin_headers):
        """Totals object contains P1.7 new keys"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=90",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        totals = data.get("totals", {})
        
        # P1.7 required totals keys
        required_keys = [
            "payment_started_sessions",
            "login_loaded_sessions",
            "cashfree_open_sessions",
            "cashfree_fail_sessions"
        ]
        for key in required_keys:
            assert key in totals, f"Missing totals key: {key}"

    def test_revenue_conversion_metrics_are_numeric(self, admin_headers):
        """All P1.7 metrics are numeric values"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=90",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        metrics = data.get("metrics", {})
        
        numeric_keys = [
            "login_redirect_dropoff_pct",
            "cashfree_opened_pct",
            "cashfree_success_pct",
            "cashfree_dropoff_pct"
        ]
        for key in numeric_keys:
            value = metrics.get(key)
            assert isinstance(value, (int, float)), f"{key} should be numeric, got {type(value)}"


class TestFunnelTrackNewEvents:
    """Test POST /api/funnel/track accepts P1.7 new event names"""

    @pytest.mark.parametrize("event_name", [
        "login_page_loaded",
        "cashfree_checkout_opened",
        "cashfree_checkout_failed",
        "checkout_exit_survey_shown",
        "checkout_exit_survey_submitted",
        "checkout_exit_survey_dismissed"
    ])
    def test_track_accepts_new_event(self, event_name):
        """Funnel track accepts P1.7 new event names"""
        session_id = f"test-p17-{uuid.uuid4()}"
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": event_name,
                "session_id": session_id,
                "context": {
                    "source_page": "test",
                    "meta": {"test": True, "from": "experience", "paid_intent": True}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_track_rejects_invalid_step(self):
        """Funnel track rejects invalid step names"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "invalid_step_name_xyz",
                "session_id": f"test-invalid-{uuid.uuid4()}"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is False
        assert "error" in data


class TestCheckoutExitSurvey:
    """Test POST /api/funnel/checkout-exit-survey"""

    @pytest.mark.parametrize("answer", [
        "price",
        "payment_failed",
        "needed_more_trust",
        "just_browsing",
        "other"
    ])
    def test_checkout_exit_survey_accepts_valid_answer(self, answer):
        """Checkout exit survey accepts all valid answers"""
        session_id = f"test-ces-{uuid.uuid4()}"
        response = requests.post(
            f"{BASE_URL}/api/funnel/checkout-exit-survey",
            json={
                "answer": answer,
                "session_id": session_id,
                "note": "Test note" if answer == "other" else ""
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_checkout_exit_survey_rejects_invalid_answer(self):
        """Checkout exit survey rejects invalid answers"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/checkout-exit-survey",
            json={
                "answer": "invalid_answer_xyz",
                "session_id": f"test-ces-invalid-{uuid.uuid4()}"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is False
        assert "error" in data

    def test_checkout_exit_survey_accepts_note_with_other(self):
        """Checkout exit survey accepts note with 'other' answer"""
        session_id = f"test-ces-note-{uuid.uuid4()}"
        response = requests.post(
            f"{BASE_URL}/api/funnel/checkout-exit-survey",
            json={
                "answer": "other",
                "session_id": session_id,
                "note": "I had a specific issue with the payment flow"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


class TestCheckoutExitSurveySummary:
    """Test GET /api/funnel/checkout-exit-survey-summary (admin)"""

    def test_survey_summary_requires_auth(self):
        """Survey summary requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/checkout-exit-survey-summary?days=30"
        )
        assert response.status_code in [401, 403]

    def test_survey_summary_returns_success(self, admin_headers):
        """Survey summary returns success for admin"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/checkout-exit-survey-summary?days=30",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_survey_summary_has_required_fields(self, admin_headers):
        """Survey summary has required response fields"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/checkout-exit-survey-summary?days=30",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_responses" in data
        assert "by_answer" in data
        assert "recent_notes" in data
        assert isinstance(data["by_answer"], list)
        assert isinstance(data["recent_notes"], list)

    def test_survey_summary_by_answer_structure(self, admin_headers):
        """Survey summary by_answer has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/checkout-exit-survey-summary?days=30",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # If there are responses, check structure
        if data.get("by_answer"):
            for item in data["by_answer"]:
                assert "answer" in item
                assert "count" in item
                assert "pct" in item


class TestPaidFunnelSessions:
    """Test GET /api/funnel/paid-funnel-sessions (admin session replay lite)"""

    def test_paid_funnel_sessions_requires_auth(self):
        """Paid funnel sessions requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/paid-funnel-sessions?days=30&limit=20"
        )
        assert response.status_code in [401, 403]

    def test_paid_funnel_sessions_returns_success(self, admin_headers):
        """Paid funnel sessions returns success for admin"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/paid-funnel-sessions?days=30&limit=20",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_paid_funnel_sessions_has_required_fields(self, admin_headers):
        """Paid funnel sessions has required response fields"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/paid-funnel-sessions?days=30&limit=20",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "period_days" in data
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_paid_funnel_sessions_structure(self, admin_headers):
        """Paid funnel sessions have correct structure when present"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/paid-funnel-sessions?days=30&limit=20",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # If there are sessions, check structure
        if data.get("sessions"):
            session = data["sessions"][0]
            required_fields = [
                "session_id", "user_id", "device_type", "browser", "country",
                "first_step", "last_step", "intent_ts", "event_count", "outcome", "timeline"
            ]
            for field in required_fields:
                assert field in session, f"Missing session field: {field}"
            
            # Check outcome is valid
            assert session["outcome"] in ["paid", "abandoned", "intent_only"]
            
            # Check timeline structure
            assert isinstance(session["timeline"], list)
            if session["timeline"]:
                event = session["timeline"][0]
                assert "step" in event
                assert "ts" in event


class TestP0Regression:
    """Verify P0/P1 features still work (no regression)"""

    def test_activation_funnel_still_works(self, admin_headers):
        """Activation funnel endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/activation-funnel?days=7",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_purchase_survey_still_works(self):
        """Purchase survey endpoint still works"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/purchase-survey",
            json={
                "answer": "preview",
                "session_id": f"test-regression-{uuid.uuid4()}"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_purchase_survey_summary_still_works(self, admin_headers):
        """Purchase survey summary endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/purchase-survey-summary?days=30",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
