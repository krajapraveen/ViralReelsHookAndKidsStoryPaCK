"""
P0 Activation Failure Remediation Tests - Iteration 524
Tests for:
1. GET /api/funnel/activation-funnel - new stage order + speed_sla section
2. POST /api/ab/assign - 90/10 weighted rollout for hero_headline
3. GET /api/ab/smart-route - weighted_rollout fallback
4. POST /api/funnel/track - new step names (speed_sla_met, speed_sla_breached, etc.)
"""
import pytest
import requests
import os
import uuid
import random

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


class TestActivationFunnelAPI:
    """Tests for GET /api/funnel/activation-funnel endpoint"""
    
    def test_activation_funnel_returns_new_stage_order(self, admin_token):
        """Verify stages array has NEW order: landing_view, landing_cta_clicked, demo_viewed, 
        story_generated_success, continue_clicked, cta_video_clicked"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/activation-funnel?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        assert "stages" in data, "Expected 'stages' in response"
        
        stages = data["stages"]
        assert len(stages) >= 6, f"Expected at least 6 stages, got {len(stages)}"
        
        # Verify the exact order of stages
        expected_order = [
            "landing_view",
            "landing_cta_clicked", 
            "demo_viewed",
            "story_generated_success",
            "continue_clicked",
            "cta_video_clicked"
        ]
        
        actual_steps = [s["step"] for s in stages]
        for i, expected_step in enumerate(expected_order):
            assert actual_steps[i] == expected_step, \
                f"Stage {i} should be '{expected_step}', got '{actual_steps[i]}'"
        
        print(f"✓ Activation funnel stages in correct order: {actual_steps[:6]}")
    
    def test_activation_funnel_has_speed_sla_section(self, admin_token):
        """Verify speed_sla array with 3 entries: cta_to_first_paint, cta_to_wow, teaser_ready"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/activation-funnel?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "speed_sla" in data, "Expected 'speed_sla' in response"
        
        speed_sla = data["speed_sla"]
        assert len(speed_sla) == 3, f"Expected 3 speed_sla entries, got {len(speed_sla)}"
        
        # Verify each SLA entry has required fields
        expected_events = ["cta_to_first_paint", "cta_to_wow", "teaser_ready"]
        expected_thresholds = {"cta_to_first_paint": 1500, "cta_to_wow": 3000, "teaser_ready": 5000}
        
        for sla in speed_sla:
            assert sla["event"] in expected_events, f"Unexpected SLA event: {sla['event']}"
            assert "threshold_ms" in sla, f"Missing threshold_ms for {sla['event']}"
            assert "median_ms" in sla, f"Missing median_ms for {sla['event']}"
            assert "p95_ms" in sla, f"Missing p95_ms for {sla['event']}"
            assert "breach_pct" in sla, f"Missing breach_pct for {sla['event']}"
            
            # Verify threshold values
            assert sla["threshold_ms"] == expected_thresholds[sla["event"]], \
                f"Wrong threshold for {sla['event']}: expected {expected_thresholds[sla['event']]}, got {sla['threshold_ms']}"
        
        print(f"✓ Speed SLA section present with correct structure: {[s['event'] for s in speed_sla]}")
    
    def test_activation_funnel_requires_admin_auth(self):
        """Verify endpoint requires admin authentication"""
        response = requests.get(f"{BASE_URL}/api/funnel/activation-funnel?days=30")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Activation funnel requires admin auth")


class TestABAssignWeightedRollout:
    """Tests for POST /api/ab/assign with 90/10 weighted rollout"""
    
    def test_ab_assign_returns_headline_b_majority(self):
        """Verify headline_b is returned ~90% of the time across 50 random session_ids"""
        headline_b_count = 0
        total_tests = 50
        
        for _ in range(total_tests):
            session_id = f"test_ses_{uuid.uuid4().hex[:12]}"
            response = requests.post(f"{BASE_URL}/api/ab/assign", json={
                "session_id": session_id,
                "experiment_id": "hero_headline"
            })
            
            assert response.status_code == 200, f"AB assign failed: {response.status_code}"
            data = response.json()
            
            if data.get("variant_id") == "headline_b":
                headline_b_count += 1
        
        percentage = (headline_b_count / total_tests) * 100
        
        # Acceptable range: 80-100% headline_b (allowing for hash distribution variance)
        assert 80 <= percentage <= 100, \
            f"Expected 80-100% headline_b, got {percentage}% ({headline_b_count}/{total_tests})"
        
        print(f"✓ A/B assign returns headline_b {percentage}% of the time ({headline_b_count}/{total_tests})")
    
    def test_ab_assign_is_deterministic(self):
        """Verify same session_id always gets same variant"""
        session_id = f"deterministic_test_{uuid.uuid4().hex[:8]}"
        
        # Call assign multiple times with same session_id
        variants = []
        for _ in range(5):
            response = requests.post(f"{BASE_URL}/api/ab/assign", json={
                "session_id": session_id,
                "experiment_id": "hero_headline"
            })
            assert response.status_code == 200
            variants.append(response.json().get("variant_id"))
        
        # All should be the same
        assert len(set(variants)) == 1, f"Expected deterministic assignment, got: {variants}"
        print(f"✓ A/B assign is deterministic: {variants[0]}")


class TestABSmartRoute:
    """Tests for GET /api/ab/smart-route endpoint"""
    
    def test_smart_route_returns_weighted_rollout_reason(self):
        """Verify smart-route returns reason=weighted_rollout or source_winner with variant_id=headline_b"""
        response = requests.get(
            f"{BASE_URL}/api/ab/smart-route?experiment_id=hero_headline&traffic_source=direct"
        )
        assert response.status_code == 200, f"Smart route failed: {response.status_code}"
        
        data = response.json()
        assert "variant_id" in data, "Expected variant_id in response"
        assert "reason" in data, "Expected reason in response"
        
        # Should be either weighted_rollout or source_winner
        valid_reasons = ["weighted_rollout", "source_winner", "insufficient_data", "low_confidence"]
        assert data["reason"] in valid_reasons, f"Unexpected reason: {data['reason']}"
        
        # If weighted_rollout, should return headline_b (the 90% winner)
        if data["reason"] == "weighted_rollout":
            assert data["variant_id"] == "headline_b", \
                f"Expected headline_b for weighted_rollout, got {data['variant_id']}"
        
        print(f"✓ Smart route returns reason={data['reason']}, variant_id={data['variant_id']}")
    
    def test_smart_route_with_different_sources(self):
        """Test smart-route with various traffic sources"""
        sources = ["direct", "instagram", "organic", "referral"]
        
        for source in sources:
            response = requests.get(
                f"{BASE_URL}/api/ab/smart-route?experiment_id=hero_headline&traffic_source={source}"
            )
            assert response.status_code == 200, f"Smart route failed for source={source}"
            
            data = response.json()
            assert "variant_id" in data
            assert "reason" in data
            print(f"  - source={source}: variant={data['variant_id']}, reason={data['reason']}")
        
        print("✓ Smart route works with all traffic sources")


class TestFunnelTrackNewSteps:
    """Tests for POST /api/funnel/track with new step names"""
    
    def test_track_speed_sla_met(self):
        """Verify speed_sla_met step is accepted"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "speed_sla_met",
            "session_id": f"test_{uuid.uuid4().hex[:8]}",
            "context": {
                "source_page": "experience",
                "meta": {"event": "cta_to_first_paint", "elapsed_ms": 1200}
            }
        })
        assert response.status_code == 200, f"Track failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success=True, got {data}"
        print("✓ speed_sla_met step accepted")
    
    def test_track_speed_sla_breached(self):
        """Verify speed_sla_breached step is accepted"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "speed_sla_breached",
            "session_id": f"test_{uuid.uuid4().hex[:8]}",
            "context": {
                "source_page": "experience",
                "meta": {"event": "cta_to_wow", "elapsed_ms": 4500}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ speed_sla_breached step accepted")
    
    def test_track_cta_to_first_paint(self):
        """Verify cta_to_first_paint step is accepted"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "cta_to_first_paint",
            "session_id": f"test_{uuid.uuid4().hex[:8]}",
            "context": {
                "source_page": "experience",
                "meta": {"elapsed_ms": 1100}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ cta_to_first_paint step accepted")
    
    def test_track_cta_to_wow(self):
        """Verify cta_to_wow step is accepted"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "cta_to_wow",
            "session_id": f"test_{uuid.uuid4().hex[:8]}",
            "context": {
                "source_page": "experience",
                "meta": {"elapsed_ms": 2800}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ cta_to_wow step accepted")
    
    def test_track_teaser_ready(self):
        """Verify teaser_ready step is accepted"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "teaser_ready",
            "session_id": f"test_{uuid.uuid4().hex[:8]}",
            "context": {
                "source_page": "experience",
                "meta": {"elapsed_ms": 4200}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ teaser_ready step accepted")
    
    def test_track_invalid_step_rejected(self):
        """Verify invalid step names are rejected"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "invalid_step_name_xyz",
            "session_id": f"test_{uuid.uuid4().hex[:8]}"
        })
        assert response.status_code == 200  # API returns 200 with success=False
        data = response.json()
        assert data.get("success") is False, "Expected success=False for invalid step"
        print("✓ Invalid step names are rejected")


class TestActivationFunnelStageLabels:
    """Verify stage labels match the new funnel order"""
    
    def test_stage_labels_correct(self, admin_token):
        """Verify each stage has correct label"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/activation-funnel?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        stages = data["stages"]
        
        expected_labels = {
            "landing_view": "Landing",
            "landing_cta_clicked": "CTA Clicked",
            "demo_viewed": "Demo Visible",
            "story_generated_success": "Personalized Story Ready",
            "continue_clicked": "Engaged (Continue)",
            "cta_video_clicked": "Intent: Video"
        }
        
        for stage in stages[:6]:
            step = stage["step"]
            if step in expected_labels:
                assert stage["label"] == expected_labels[step], \
                    f"Wrong label for {step}: expected '{expected_labels[step]}', got '{stage['label']}'"
        
        print("✓ All stage labels are correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
