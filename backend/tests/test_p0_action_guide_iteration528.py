"""
P0 In-Product Guided Experience Tests (Iteration 528)
Tests for the 7 new funnel events:
- guide_opened
- guide_completed
- skipped_guide
- started_after_guide
- remix_after_guide
- continue_after_guide
- battle_after_guide
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


class TestGuideOpenedEvent:
    """Test guide_opened funnel event"""
    
    def test_guide_opened_accepted(self):
        """POST /api/funnel/track accepts guide_opened event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "guide_opened",
            "session_id": "test_session_guide_opened",
            "context": {
                "meta": {"action_id": "story_video", "forced": False}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: guide_opened event accepted")


class TestGuideCompletedEvent:
    """Test guide_completed funnel event"""
    
    def test_guide_completed_accepted(self):
        """POST /api/funnel/track accepts guide_completed event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "guide_completed",
            "session_id": "test_session_guide_completed",
            "context": {
                "meta": {"action_id": "continue", "elapsed_ms": 5000, "dont_show_again": True}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: guide_completed event accepted")


class TestSkippedGuideEvent:
    """Test skipped_guide funnel event"""
    
    def test_skipped_guide_accepted(self):
        """POST /api/funnel/track accepts skipped_guide event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "skipped_guide",
            "session_id": "test_session_skipped_guide",
            "context": {
                "meta": {"action_id": "remix", "elapsed_ms": 2000}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: skipped_guide event accepted")


class TestStartedAfterGuideEvent:
    """Test started_after_guide funnel event"""
    
    def test_started_after_guide_accepted(self):
        """POST /api/funnel/track accepts started_after_guide event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "started_after_guide",
            "session_id": "test_session_started_after_guide",
            "context": {
                "meta": {"action_id": "story_video"}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: started_after_guide event accepted")


class TestRemixAfterGuideEvent:
    """Test remix_after_guide funnel event"""
    
    def test_remix_after_guide_accepted(self):
        """POST /api/funnel/track accepts remix_after_guide event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "remix_after_guide",
            "session_id": "test_session_remix_after_guide",
            "context": {
                "meta": {"action_id": "remix"}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: remix_after_guide event accepted")


class TestContinueAfterGuideEvent:
    """Test continue_after_guide funnel event"""
    
    def test_continue_after_guide_accepted(self):
        """POST /api/funnel/track accepts continue_after_guide event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "continue_after_guide",
            "session_id": "test_session_continue_after_guide",
            "context": {
                "meta": {"action_id": "continue"}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: continue_after_guide event accepted")


class TestBattleAfterGuideEvent:
    """Test battle_after_guide funnel event"""
    
    def test_battle_after_guide_accepted(self):
        """POST /api/funnel/track accepts battle_after_guide event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "battle_after_guide",
            "session_id": "test_session_battle_after_guide",
            "context": {
                "meta": {"action_id": "battle"}
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("PASS: battle_after_guide event accepted")


class TestInvalidEventRejected:
    """Test that invalid events are rejected"""
    
    def test_invalid_event_rejected(self):
        """POST /api/funnel/track rejects invalid event names"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "invalid_event_name_xyz",
            "session_id": "test_session_invalid"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is False
        assert "Invalid step" in data.get("error", "")
        print("PASS: Invalid event rejected correctly")


class TestAllSevenEventsInSequence:
    """Test all 7 new events in a realistic sequence"""
    
    def test_full_guide_flow_sequence(self):
        """Test a complete guide flow: opened -> completed -> action_after_guide"""
        session_id = "test_full_guide_flow_session"
        
        # 1. Guide opened
        r1 = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "guide_opened",
            "session_id": session_id,
            "context": {"meta": {"action_id": "continue", "forced": False}}
        })
        assert r1.status_code == 200 and r1.json().get("success") is True
        print("  Step 1: guide_opened - PASS")
        
        # 2. Guide completed
        r2 = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "guide_completed",
            "session_id": session_id,
            "context": {"meta": {"action_id": "continue", "elapsed_ms": 8000, "dont_show_again": False}}
        })
        assert r2.status_code == 200 and r2.json().get("success") is True
        print("  Step 2: guide_completed - PASS")
        
        # 3. Action after guide
        r3 = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "continue_after_guide",
            "session_id": session_id,
            "context": {"meta": {"action_id": "continue"}}
        })
        assert r3.status_code == 200 and r3.json().get("success") is True
        print("  Step 3: continue_after_guide - PASS")
        
        print("PASS: Full guide flow sequence completed")
    
    def test_skipped_guide_flow(self):
        """Test guide skip flow: opened -> skipped"""
        session_id = "test_skipped_guide_flow_session"
        
        # 1. Guide opened
        r1 = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "guide_opened",
            "session_id": session_id,
            "context": {"meta": {"action_id": "battle", "forced": False}}
        })
        assert r1.status_code == 200 and r1.json().get("success") is True
        print("  Step 1: guide_opened - PASS")
        
        # 2. Guide skipped
        r2 = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "skipped_guide",
            "session_id": session_id,
            "context": {"meta": {"action_id": "battle", "elapsed_ms": 1500}}
        })
        assert r2.status_code == 200 and r2.json().get("success") is True
        print("  Step 2: skipped_guide - PASS")
        
        print("PASS: Skipped guide flow completed")


class TestP0Regression:
    """Regression tests for existing P0 features"""
    
    def test_activation_funnel_still_works(self, admin_token):
        """GET /api/funnel/activation-funnel still returns success"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/activation-funnel?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "stages" in data
        print("PASS: activation-funnel endpoint still works")
    
    def test_revenue_conversion_still_works(self, admin_token):
        """GET /api/funnel/revenue-conversion still returns success"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/revenue-conversion?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "metrics" in data
        print("PASS: revenue-conversion endpoint still works")
    
    def test_funnel_metrics_still_works(self, admin_token):
        """GET /api/funnel/metrics still returns success"""
        response = requests.get(
            f"{BASE_URL}/api/funnel/metrics?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "funnel" in data
        print("PASS: funnel/metrics endpoint still works")
