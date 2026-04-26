"""
P1.6 Trust + Urgency Sprint — Backend API Tests
Tests for:
1. GET /api/public/social-proof — returns {kind, label, count}
2. POST /api/funnel/purchase-survey — accepts answer, note, session_id, order_id, plan
3. GET /api/funnel/purchase-survey-summary — admin endpoint for survey rollup
4. POST /api/funnel/track — accepts new purchase_survey_* steps
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials from test_credentials.md
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        data = resp.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin login failed: {resp.status_code} - {resp.text}")


class TestSocialProofEndpoint:
    """Test GET /api/public/social-proof"""
    
    def test_social_proof_returns_success(self):
        """Social proof endpoint returns valid response"""
        resp = requests.get(f"{BASE_URL}/api/public/social-proof")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "kind" in data, "Response missing 'kind' field"
        assert "label" in data, "Response missing 'label' field"
        assert "count" in data, "Response missing 'count' field"
    
    def test_social_proof_kind_is_valid(self):
        """Social proof kind is either 'count' or 'qualitative'"""
        resp = requests.get(f"{BASE_URL}/api/public/social-proof")
        assert resp.status_code == 200
        data = resp.json()
        assert data["kind"] in ["count", "qualitative"], f"Invalid kind: {data['kind']}"
    
    def test_social_proof_label_format(self):
        """Social proof label matches expected format based on kind"""
        resp = requests.get(f"{BASE_URL}/api/public/social-proof")
        assert resp.status_code == 200
        data = resp.json()
        
        if data["kind"] == "qualitative":
            # Low volume fallback
            assert data["label"] == "Popular with parents tonight", f"Unexpected qualitative label: {data['label']}"
        else:
            # High volume — label should contain count + 'story videos created this week'
            assert "story videos created this week" in data["label"], f"Count label missing expected text: {data['label']}"
            # Count should be >= 100 for 'count' kind
            assert data["count"] >= 100, f"Count kind but count < 100: {data['count']}"
    
    def test_social_proof_count_is_integer(self):
        """Social proof count is a non-negative integer"""
        resp = requests.get(f"{BASE_URL}/api/public/social-proof")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["count"], int), f"Count is not int: {type(data['count'])}"
        assert data["count"] >= 0, f"Count is negative: {data['count']}"


class TestPurchaseSurveyEndpoint:
    """Test POST /api/funnel/purchase-survey"""
    
    def test_purchase_survey_accepts_valid_answer(self):
        """Purchase survey accepts valid answer"""
        resp = requests.post(f"{BASE_URL}/api/funnel/purchase-survey", json={
            "answer": "preview",
            "session_id": "test_session_526_1",
            "order_id": "test_order_526_1",
            "plan": "one_time"
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("success") is True, f"Expected success:true, got {data}"
    
    def test_purchase_survey_accepts_all_valid_answers(self):
        """Purchase survey accepts all 5 valid answer options"""
        valid_answers = ["preview", "price", "story", "needed_now", "other"]
        for i, answer in enumerate(valid_answers):
            resp = requests.post(f"{BASE_URL}/api/funnel/purchase-survey", json={
                "answer": answer,
                "session_id": f"test_session_526_{i+10}",
            })
            assert resp.status_code == 200, f"Failed for answer '{answer}': {resp.status_code}"
            data = resp.json()
            assert data.get("success") is True, f"Expected success for '{answer}', got {data}"
    
    def test_purchase_survey_rejects_invalid_answer(self):
        """Purchase survey rejects invalid answer"""
        resp = requests.post(f"{BASE_URL}/api/funnel/purchase-survey", json={
            "answer": "invalid_x",
            "session_id": "test_session_526_invalid",
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("success") is False, f"Expected success:false for invalid answer, got {data}"
        assert "error" in data, "Expected error message for invalid answer"
    
    def test_purchase_survey_accepts_note_with_other(self):
        """Purchase survey accepts note when answer is 'other'"""
        resp = requests.post(f"{BASE_URL}/api/funnel/purchase-survey", json={
            "answer": "other",
            "note": "I loved the animation style",
            "session_id": "test_session_526_note",
            "order_id": "test_order_526_note",
            "plan": "monthly"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True


class TestPurchaseSurveySummaryEndpoint:
    """Test GET /api/funnel/purchase-survey-summary (admin only)"""
    
    def test_survey_summary_requires_auth(self):
        """Survey summary endpoint requires admin auth"""
        resp = requests.get(f"{BASE_URL}/api/funnel/purchase-survey-summary")
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
    
    def test_survey_summary_returns_success(self, admin_token):
        """Survey summary returns valid response for admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/funnel/purchase-survey-summary?days=30", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("success") is True
    
    def test_survey_summary_has_required_fields(self, admin_token):
        """Survey summary has total_responses, by_answer, recent_notes"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/funnel/purchase-survey-summary?days=30", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_responses" in data, "Missing total_responses"
        assert "by_answer" in data, "Missing by_answer"
        assert "recent_notes" in data, "Missing recent_notes"
        assert isinstance(data["by_answer"], list), "by_answer should be a list"
        assert isinstance(data["recent_notes"], list), "recent_notes should be a list"
    
    def test_survey_summary_by_answer_structure(self, admin_token):
        """Survey summary by_answer has answer, count, pct fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/funnel/purchase-survey-summary?days=30", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data.get("by_answer", []):
            assert "answer" in item, "by_answer item missing 'answer'"
            assert "count" in item, "by_answer item missing 'count'"
            assert "pct" in item, "by_answer item missing 'pct'"


class TestFunnelTrackNewSteps:
    """Test POST /api/funnel/track accepts new purchase_survey_* steps"""
    
    def test_track_purchase_survey_shown(self):
        """Funnel track accepts purchase_survey_shown step"""
        resp = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "purchase_survey_shown",
            "session_id": "test_session_526_track_1",
            "context": {"order_id": "test_order", "plan": "one_time"}
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("success") is True
    
    def test_track_purchase_survey_submitted(self):
        """Funnel track accepts purchase_survey_submitted step"""
        resp = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "purchase_survey_submitted",
            "session_id": "test_session_526_track_2",
            "context": {"meta": {"answer": "preview"}}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
    
    def test_track_purchase_survey_dismissed(self):
        """Funnel track accepts purchase_survey_dismissed step"""
        resp = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "purchase_survey_dismissed",
            "session_id": "test_session_526_track_3",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
    
    def test_track_invalid_step_rejected(self):
        """Funnel track rejects invalid step"""
        resp = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "invalid_step_xyz",
            "session_id": "test_session_526_invalid",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is False


class TestActivationFunnelStillWorks:
    """Regression: activation funnel endpoint still works"""
    
    def test_activation_funnel_returns_success(self, admin_token):
        """Activation funnel endpoint returns valid response"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/funnel/activation-funnel?days=7", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("success") is True


class TestRevenueConversionStillWorks:
    """Regression: revenue conversion endpoint still works"""
    
    def test_revenue_conversion_returns_success(self, admin_token):
        """Revenue conversion endpoint returns valid response"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = requests.get(f"{BASE_URL}/api/funnel/revenue-conversion?days=7", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("success") is True
        assert "metrics" in data
        assert "video_cta_variants" in data
