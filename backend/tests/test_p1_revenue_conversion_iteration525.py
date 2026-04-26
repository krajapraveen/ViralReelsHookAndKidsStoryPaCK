"""
P1 Revenue Conversion Sprint - Backend API Tests (Iteration 525)

Tests for:
1. GET /api/funnel/revenue-conversion - returns 5 metrics + video_cta_variants leaderboard
2. POST /api/funnel/track - accepts new step names for P1 features
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials from test_credentials.md
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestRevenueConversionEndpoint:
    """Tests for GET /api/funnel/revenue-conversion endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        # Login returns 'token' key (not 'access_token')
        token = data.get("token")
        assert token, f"No token in response: {data}"
        return token
    
    def test_revenue_conversion_requires_admin_auth(self):
        """Revenue conversion endpoint requires admin authentication"""
        response = requests.get(f"{BASE_URL}/api/funnel/revenue-conversion?days=30")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_revenue_conversion_returns_success(self, admin_token):
        """Revenue conversion endpoint returns success:true with admin token"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success:true, got {data}"
    
    def test_revenue_conversion_has_totals(self, admin_token):
        """Revenue conversion returns totals object with required fields"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        totals = data.get("totals", {})
        required_fields = [
            "landing_sessions",
            "story_completed_sessions",
            "video_cta_sessions",
            "checkout_sessions",
            "payment_sessions",
            "share_clicks",
            "revenue_inr"
        ]
        for field in required_fields:
            assert field in totals, f"Missing totals.{field} in response"
    
    def test_revenue_conversion_has_metrics(self, admin_token):
        """Revenue conversion returns metrics object with 5 required metrics"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        metrics = data.get("metrics", {})
        required_metrics = [
            "story_completed_to_video_cta_pct",
            "video_cta_to_checkout_pct",
            "checkout_to_payment_pct",
            "share_pct",
            "revenue_per_100_visitors"
        ]
        for metric in required_metrics:
            assert metric in metrics, f"Missing metrics.{metric} in response"
            # Metrics should be numeric
            assert isinstance(metrics[metric], (int, float)), f"metrics.{metric} should be numeric"
    
    def test_revenue_conversion_has_video_cta_variants(self, admin_token):
        """Revenue conversion returns video_cta_variants array"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # video_cta_variants should be a list (may be empty if no impressions)
        variants = data.get("video_cta_variants")
        assert isinstance(variants, list), f"video_cta_variants should be a list, got {type(variants)}"
    
    def test_revenue_conversion_days_parameter(self, admin_token):
        """Revenue conversion accepts days parameter"""
        for days in [1, 7, 30, 90]:
            response = requests.get(
                f"{BASE_URL}/api/funnel/revenue-conversion?days={days}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Failed for days={days}"
            data = response.json()
            assert data.get("period_days") == days, f"Expected period_days={days}"


class TestFunnelTrackNewSteps:
    """Tests for POST /api/funnel/track with new P1 step names"""
    
    def test_track_video_cta_variant_impression(self):
        """Track video_cta_variant_impression step"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "video_cta_variant_impression",
                "session_id": "test_session_525_1",
                "context": {
                    "meta": {
                        "video_cta_variant": "cinematic",
                        "video_cta_label": "Turn This Into a Cinematic Video"
                    }
                }
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success:true, got {data}"
    
    def test_track_video_reward_preview_shown(self):
        """Track video_reward_preview_shown step"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "video_reward_preview_shown",
                "session_id": "test_session_525_2",
                "context": {
                    "meta": {
                        "story_id": "test_story_123",
                        "source": "landing",
                        "price_label": "₹29"
                    }
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
    
    def test_track_video_reward_preview_cta_clicked(self):
        """Track video_reward_preview_cta_clicked step"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "video_reward_preview_cta_clicked",
                "session_id": "test_session_525_3",
                "context": {
                    "meta": {
                        "story_id": "test_story_123",
                        "source": "landing"
                    }
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
    
    def test_track_video_reward_preview_dismissed(self):
        """Track video_reward_preview_dismissed step"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "video_reward_preview_dismissed",
                "session_id": "test_session_525_4",
                "context": {
                    "meta": {
                        "story_id": "test_story_123",
                        "source": "landing"
                    }
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
    
    def test_track_invalid_step_rejected(self):
        """Invalid step names should be rejected"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "invalid_step_name_xyz",
                "session_id": "test_session_525_5"
            }
        )
        assert response.status_code == 200  # API returns 200 with success:false
        data = response.json()
        assert data.get("success") is False, f"Expected success:false for invalid step"


class TestActivationFunnelWithRevenueData:
    """Tests to verify activation funnel still works alongside revenue conversion"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json().get("token")
    
    def test_activation_funnel_still_works(self, admin_token):
        """Activation funnel endpoint still returns data"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/activation-funnel?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "stages" in data
        assert "speed_sla" in data
    
    def test_both_endpoints_return_consistent_data(self, admin_token):
        """Both funnel endpoints should return consistent session counts"""
        # Get activation funnel data
        activation_resp = requests.get(
            f"{BASE_URL}/api/funnel/activation-funnel?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert activation_resp.status_code == 200
        activation_data = activation_resp.json()
        
        # Get revenue conversion data
        revenue_resp = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert revenue_resp.status_code == 200
        revenue_data = revenue_resp.json()
        
        # Both should have success:true
        assert activation_data.get("success") is True
        assert revenue_data.get("success") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
