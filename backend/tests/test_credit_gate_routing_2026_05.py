"""
P0 REVENUE BUG FIX: Credit-Gate Modal Routing Tests
Tests for the routing fix in StoryVideoPipeline credit-gate modal:
- Buy Credits → /app/billing?tab=credits (NOT /app/profile or /pricing)
- View Plans → /app/billing?tab=plans (NOT /pricing or /profile)
- New funnel events: credit_gate_buy_credits_clicked, credit_gate_view_plans_clicked, billing_section_opened_from_gate
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCreditGateFunnelEvents:
    """Test that new funnel events for credit-gate routing are accepted"""
    
    def test_credit_gate_buy_credits_clicked_event_accepted(self):
        """credit_gate_buy_credits_clicked should be in FUNNEL_STEPS allowlist"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "credit_gate_buy_credits_clicked",
            "context": {
                "source_page": "story_video_pipeline",
                "meta": {"shortfall": 15}
            }
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print("PASS: credit_gate_buy_credits_clicked event accepted")
    
    def test_credit_gate_view_plans_clicked_event_accepted(self):
        """credit_gate_view_plans_clicked should be in FUNNEL_STEPS allowlist"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "credit_gate_view_plans_clicked",
            "context": {
                "source_page": "story_video_pipeline",
                "meta": {"shortfall": 10}
            }
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print("PASS: credit_gate_view_plans_clicked event accepted")
    
    def test_billing_section_opened_from_gate_event_accepted(self):
        """billing_section_opened_from_gate should be in FUNNEL_STEPS allowlist"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "billing_section_opened_from_gate",
            "context": {
                "source_page": "billing",
                "meta": {"tab": "credits"}
            }
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print("PASS: billing_section_opened_from_gate event accepted")
    
    def test_unknown_funnel_step_rejected(self):
        """Unknown funnel steps should still be rejected"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "invalid_step_xyz_123",
            "context": {}
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == False, f"Expected success=False for unknown step, got {data}"
        print("PASS: Unknown funnel step correctly rejected")


class TestPhotoTrailerTemplatesRegression:
    """Regression: Photo Trailer freeze HELD - should return 9 templates"""
    
    def test_photo_trailer_templates_returns_9(self):
        """GET /api/photo-trailer/templates should return exactly 9 templates"""
        response = requests.get(f"{BASE_URL}/api/photo-trailer/templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        templates = data.get("templates", [])
        assert len(templates) == 9, f"Expected 9 templates, got {len(templates)}"
        print(f"PASS: Photo Trailer returns {len(templates)} templates (freeze HELD)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
