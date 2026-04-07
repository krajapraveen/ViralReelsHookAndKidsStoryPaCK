"""
Load Guard / Kill Switch API Tests - Iteration 458
===================================================
Tests for the Load Guard admission controller system with:
- Rolling-window trend detection (30s snapshots)
- Queue-class aware degradation (heavy/medium/light queues)
- Graded guard modes: NORMAL->STRESSED->SEVERE->CRITICAL
- Hysteresis/anti-flapping for recovery
- Admin manual controls (set mode, toggle auto, toggle bypass)
- Per-queue overload detection
- Structured 429 responses
- Every admission decision logged

Test credentials:
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026
- Free user: test@visionary-suite.com / Test@2026#
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
FREE_USER_EMAIL = "test@visionary-suite.com"
FREE_USER_PASSWORD = "Test@2026#"


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
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text[:200]}")


@pytest.fixture(scope="module")
def free_user_token():
    """Get free user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": FREE_USER_EMAIL,
        "password": FREE_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Free user authentication failed: {response.status_code} - {response.text[:200]}")


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def free_user_headers(free_user_token):
    """Headers with free user auth"""
    return {
        "Authorization": f"Bearer {free_user_token}",
        "Content-Type": "application/json"
    }


def reset_guard_to_normal(admin_headers):
    """Helper to reset guard mode to normal after tests"""
    requests.post(
        f"{BASE_URL}/api/admin/system-health/load-guard",
        headers=admin_headers,
        json={"action": "set_mode", "mode": None}
    )
    time.sleep(0.5)


# ─── LOAD GUARD STATUS ENDPOINT TESTS ─────────────────────────────────────────

class TestLoadGuardStatus:
    """Tests for GET /api/admin/system-health/load-guard"""
    
    def test_load_guard_status_returns_full_status(self, admin_headers):
        """GET /api/admin/system-health/load-guard returns full status with all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        data = response.json()
        
        # Verify guard_mode field
        assert "guard_mode" in data, "Missing guard_mode field"
        assert data["guard_mode"] in ["normal", "stressed", "severe", "critical"], f"Invalid guard_mode: {data['guard_mode']}"
        
        # Verify signals field
        assert "signals" in data, "Missing signals field"
        signals = data["signals"]
        assert "system_saturation_pct" in signals, "Missing system_saturation_pct in signals"
        assert "total_queued" in signals, "Missing total_queued in signals"
        assert "total_processing" in signals, "Missing total_processing in signals"
        
        # Verify per_queue field
        assert "per_queue" in data, "Missing per_queue field"
        per_queue = data["per_queue"]
        expected_queues = ["text", "image", "video", "audio", "export", "webhook", "analytics", "batch"]
        for queue in expected_queues:
            assert queue in per_queue, f"Missing queue type: {queue}"
        
        # Verify config field
        assert "config" in data, "Missing config field"
        config = data["config"]
        assert "auto_enabled" in config, "Missing auto_enabled in config"
        assert "manual_mode" in config, "Missing manual_mode in config"
        assert "premium_bypass" in config, "Missing premium_bypass in config"
        
        # Verify recovery field
        assert "recovery" in data, "Missing recovery field"
        assert "in_recovery" in data["recovery"], "Missing in_recovery in recovery"
        
        # Verify escalation field
        assert "escalation" in data, "Missing escalation field"
        assert "candidate_mode" in data["escalation"], "Missing candidate_mode in escalation"
        
        # Verify audit_log field
        assert "audit_log" in data, "Missing audit_log field"
        assert isinstance(data["audit_log"], list), "audit_log should be a list"
        
        print(f"✓ Load guard status returned with guard_mode={data['guard_mode']}, {len(per_queue)} queues")
    
    def test_load_guard_status_requires_admin(self, free_user_headers):
        """Non-admin user cannot access load-guard endpoints (403)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=free_user_headers
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("✓ Non-admin correctly rejected with 403")


# ─── LOAD GUARD CONTROL ENDPOINT TESTS ────────────────────────────────────────

class TestLoadGuardControl:
    """Tests for POST /api/admin/system-health/load-guard"""
    
    def test_set_mode_to_critical(self, admin_headers):
        """POST with action=set_mode changes guard mode to critical"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers,
                json={"action": "set_mode", "mode": "critical"}
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
            data = response.json()
            
            assert data.get("success") == True, "Expected success=True"
            assert data.get("action") == "set_mode", "Expected action=set_mode"
            assert data.get("mode") == "critical", "Expected mode=critical"
            
            # Verify status reflects the change
            assert "status" in data, "Missing status in response"
            assert data["status"]["guard_mode"] == "critical", "Guard mode not updated to critical"
            
            print("✓ Guard mode set to critical successfully")
        finally:
            reset_guard_to_normal(admin_headers)
    
    def test_set_mode_to_stressed(self, admin_headers):
        """POST with action=set_mode changes guard mode to stressed"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers,
                json={"action": "set_mode", "mode": "stressed"}
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            
            assert data.get("success") == True
            assert data["status"]["guard_mode"] == "stressed"
            
            print("✓ Guard mode set to stressed successfully")
        finally:
            reset_guard_to_normal(admin_headers)
    
    def test_set_mode_to_severe(self, admin_headers):
        """POST with action=set_mode changes guard mode to severe"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers,
                json={"action": "set_mode", "mode": "severe"}
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            
            assert data.get("success") == True
            assert data["status"]["guard_mode"] == "severe"
            
            print("✓ Guard mode set to severe successfully")
        finally:
            reset_guard_to_normal(admin_headers)
    
    def test_set_mode_to_null_resets_to_normal(self, admin_headers):
        """POST with action=set_mode and mode=null resets guard to normal"""
        # First set to critical
        requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_mode", "mode": "critical"}
        )
        
        # Then reset to normal
        response = requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_mode", "mode": None}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True
        assert data["status"]["guard_mode"] == "normal", "Guard mode should reset to normal"
        assert data["status"]["config"]["manual_mode"] is None, "Manual mode should be None"
        
        print("✓ Guard mode reset to normal when mode=null")
    
    def test_set_mode_invalid_returns_400(self, admin_headers):
        """POST with invalid mode value returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_mode", "mode": "invalid_mode"}
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid mode, got {response.status_code}"
        print("✓ Invalid mode correctly rejected with 400")
    
    def test_set_auto_toggle(self, admin_headers):
        """POST with action=set_auto toggles auto mode"""
        # Disable auto
        response = requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_auto", "auto_enabled": False}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("auto_enabled") == False
        
        # Re-enable auto
        response = requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_auto", "auto_enabled": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("auto_enabled") == True
        
        print("✓ Auto mode toggle works correctly")
    
    def test_set_bypass_toggle(self, admin_headers):
        """POST with action=set_bypass toggles premium bypass"""
        # Disable bypass
        response = requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_bypass", "premium_bypass": False}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("premium_bypass") == False
        
        # Re-enable bypass
        response = requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_bypass", "premium_bypass": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("premium_bypass") == True
        
        print("✓ Premium bypass toggle works correctly")
    
    def test_invalid_action_returns_400(self, admin_headers):
        """POST with invalid action returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "invalid_action"}
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid action, got {response.status_code}"
        print("✓ Invalid action correctly rejected with 400")
    
    def test_control_requires_admin(self, free_user_headers):
        """Non-admin user cannot control load-guard (403)"""
        response = requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=free_user_headers,
            json={"action": "set_mode", "mode": "critical"}
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("✓ Non-admin correctly rejected from control endpoint with 403")


# ─── LOAD GUARD DECISIONS ENDPOINT TESTS ──────────────────────────────────────

class TestLoadGuardDecisions:
    """Tests for GET /api/admin/system-health/load-guard/decisions"""
    
    def test_decisions_endpoint_returns_history(self, admin_headers):
        """GET /api/admin/system-health/load-guard/decisions returns admission decision history"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard/decisions",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        data = response.json()
        
        assert "decisions" in data, "Missing decisions field"
        assert isinstance(data["decisions"], list), "decisions should be a list"
        
        # If there are decisions, verify structure
        if len(data["decisions"]) > 0:
            decision = data["decisions"][0]
            assert "ts" in decision, "Decision missing timestamp"
            assert "decision" in decision, "Decision missing decision type"
            assert "admitted" in decision, "Decision missing admitted flag"
            assert "guard_mode" in decision, "Decision missing guard_mode"
        
        print(f"✓ Decisions endpoint returned {len(data['decisions'])} decisions")
    
    def test_decisions_accepts_limit_param(self, admin_headers):
        """GET /api/admin/system-health/load-guard/decisions accepts limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard/decisions?limit=10",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert len(data["decisions"]) <= 10, "Should respect limit parameter"
        print("✓ Decisions endpoint respects limit parameter")
    
    def test_decisions_requires_admin(self, free_user_headers):
        """Non-admin user cannot access decisions endpoint (403)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard/decisions",
            headers=free_user_headers
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("✓ Non-admin correctly rejected from decisions endpoint with 403")


# ─── 429 RESPONSE TESTS FOR DIFFERENT GUARD MODES ─────────────────────────────

class TestGuardMode429Responses:
    """Tests for 429 responses when guard is in different modes"""
    
    def test_critical_mode_blocks_free_user_pipeline_create(self, admin_headers, free_user_headers):
        """When guard is CRITICAL, free user pipeline/create returns HTTP 429"""
        try:
            # Set guard to critical
            set_response = requests.post(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers,
                json={"action": "set_mode", "mode": "critical"}
            )
            assert set_response.status_code == 200, f"Failed to set critical mode: {set_response.text[:200]}"
            
            time.sleep(0.5)  # Allow mode to propagate
            
            # Try to create pipeline job as free user
            # story_text must be >= 50 characters
            story_text = "This is a test story about a brave little rabbit who goes on an amazing adventure through the magical forest."
            
            response = requests.post(
                f"{BASE_URL}/api/pipeline/create",
                headers=free_user_headers,
                json={
                    "title": "Test Story",
                    "story_text": story_text,
                    "animation_style": "cartoon_2d",
                    "age_group": "kids_5_8",
                    "voice_preset": "narrator_warm"
                }
            )
            
            assert response.status_code == 429, f"Expected 429 in critical mode, got {response.status_code}: {response.text[:300]}"
            
            # Verify structured 429 response
            data = response.json()
            if "detail" in data:
                detail = data["detail"]
                if isinstance(detail, dict):
                    assert "error" in detail or "message" in detail, "429 response should have error or message"
                    if "retry_after_sec" in detail:
                        assert isinstance(detail["retry_after_sec"], int), "retry_after_sec should be int"
            
            print("✓ Critical mode correctly returns 429 for free user pipeline/create")
        finally:
            reset_guard_to_normal(admin_headers)
    
    def test_stressed_mode_blocks_free_user_heavy_job(self, admin_headers, free_user_headers):
        """When guard is STRESSED, free user pipeline/create for STORY_VIDEO (heavy job) returns 429"""
        try:
            # Set guard to stressed
            set_response = requests.post(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers,
                json={"action": "set_mode", "mode": "stressed"}
            )
            assert set_response.status_code == 200, f"Failed to set stressed mode: {set_response.text[:200]}"
            
            time.sleep(0.5)
            
            # Try to create pipeline job (STORY_VIDEO is a heavy job)
            story_text = "This is a test story about a brave little rabbit who goes on an amazing adventure through the magical forest."
            
            response = requests.post(
                f"{BASE_URL}/api/pipeline/create",
                headers=free_user_headers,
                json={
                    "title": "Test Story",
                    "story_text": story_text,
                    "animation_style": "cartoon_2d",
                    "age_group": "kids_5_8",
                    "voice_preset": "narrator_warm"
                }
            )
            
            # In stressed mode, free users with heavy jobs should get 429
            assert response.status_code == 429, f"Expected 429 in stressed mode for heavy job, got {response.status_code}: {response.text[:300]}"
            
            print("✓ Stressed mode correctly returns 429 for free user heavy job (STORY_VIDEO)")
        finally:
            reset_guard_to_normal(admin_headers)
    
    def test_severe_mode_blocks_free_user(self, admin_headers, free_user_headers):
        """When guard is SEVERE, free user pipeline/create returns 429"""
        try:
            # Set guard to severe
            set_response = requests.post(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers,
                json={"action": "set_mode", "mode": "severe"}
            )
            assert set_response.status_code == 200, f"Failed to set severe mode: {set_response.text[:200]}"
            
            time.sleep(0.5)
            
            story_text = "This is a test story about a brave little rabbit who goes on an amazing adventure through the magical forest."
            
            response = requests.post(
                f"{BASE_URL}/api/pipeline/create",
                headers=free_user_headers,
                json={
                    "title": "Test Story",
                    "story_text": story_text,
                    "animation_style": "cartoon_2d",
                    "age_group": "kids_5_8",
                    "voice_preset": "narrator_warm"
                }
            )
            
            assert response.status_code == 429, f"Expected 429 in severe mode, got {response.status_code}: {response.text[:300]}"
            
            print("✓ Severe mode correctly returns 429 for free user")
        finally:
            reset_guard_to_normal(admin_headers)
    
    def test_normal_mode_does_not_block_by_guard(self, admin_headers, free_user_headers):
        """When guard is NORMAL, free user pipeline/create should NOT be blocked by guard"""
        # Ensure guard is in normal mode
        reset_guard_to_normal(admin_headers)
        time.sleep(0.5)
        
        # Verify guard is normal
        status_response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers
        )
        assert status_response.status_code == 200
        status = status_response.json()
        assert status["guard_mode"] == "normal", f"Guard should be normal, got {status['guard_mode']}"
        
        story_text = "This is a test story about a brave little rabbit who goes on an amazing adventure through the magical forest."
        
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            headers=free_user_headers,
            json={
                "title": "Test Story Normal Mode",
                "story_text": story_text,
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            }
        )
        
        # In normal mode, should not get 429 from guard (may fail for other reasons like credits)
        # 429 from guard has specific structure, other 429s (rate limit) are different
        if response.status_code == 429:
            data = response.json()
            detail = data.get("detail", {})
            if isinstance(detail, dict):
                # Guard 429 has "admission_rejected" error
                assert detail.get("error") != "admission_rejected", "Should not be blocked by guard in normal mode"
        
        # Success or other error (not guard rejection) is acceptable
        print(f"✓ Normal mode does not block by guard (status: {response.status_code})")


# ─── BACKWARD COMPATIBILITY TESTS ─────────────────────────────────────────────

class TestBackwardCompatibility:
    """Tests for backward compatibility with existing endpoints"""
    
    def test_system_health_overview_still_works(self, admin_headers):
        """GET /api/admin/system-health/overview still works (backward compatibility)"""
        # Retry up to 3 times for transient 502 errors
        for attempt in range(3):
            response = requests.get(
                f"{BASE_URL}/api/admin/system-health/overview",
                headers=admin_headers
            )
            if response.status_code != 502:
                break
            time.sleep(1)  # Wait before retry
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        data = response.json()
        
        # Verify expected fields
        assert "timestamp" in data, "Missing timestamp"
        assert "queues" in data, "Missing queues"
        assert "workers" in data, "Missing workers"
        assert "database" in data, "Missing database"
        
        print("✓ System health overview endpoint still works")
    
    def test_guardrail_state_still_works(self, admin_headers):
        """GET /api/observability/guardrail-state still works (backward compatibility)"""
        response = requests.get(
            f"{BASE_URL}/api/observability/guardrail-state",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        data = response.json()
        
        # Verify expected fields
        assert "guardrails" in data, "Missing guardrails"
        assert "admission" in data, "Missing admission"
        
        # admission should contain guard info
        admission = data["admission"]
        assert "load_level" in admission or "guard" in admission, "Missing load info in admission"
        
        print("✓ Guardrail state endpoint still works")


# ─── AUDIT LOG TESTS ──────────────────────────────────────────────────────────

class TestAuditLog:
    """Tests for audit log recording of admin actions"""
    
    def test_audit_log_records_set_mode_action(self, admin_headers):
        """Audit log records admin set_mode actions with timestamps"""
        try:
            # Perform a set_mode action
            response = requests.post(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers,
                json={"action": "set_mode", "mode": "stressed"}
            )
            assert response.status_code == 200
            
            # Get status to check audit log
            status_response = requests.get(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers
            )
            assert status_response.status_code == 200
            data = status_response.json()
            
            audit_log = data.get("audit_log", [])
            assert len(audit_log) > 0, "Audit log should have entries"
            
            # Find the most recent set_manual_mode action
            recent_action = None
            for entry in reversed(audit_log):
                if entry.get("action") == "set_manual_mode":
                    recent_action = entry
                    break
            
            assert recent_action is not None, "Should find set_manual_mode action in audit log"
            assert "ts" in recent_action, "Audit entry should have timestamp"
            assert "admin" in recent_action, "Audit entry should have admin identifier"
            
            print(f"✓ Audit log records set_mode action with timestamp: {recent_action.get('ts')}")
        finally:
            reset_guard_to_normal(admin_headers)
    
    def test_audit_log_records_set_auto_action(self, admin_headers):
        """Audit log records admin set_auto actions"""
        # Toggle auto off and on
        requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_auto", "auto_enabled": False}
        )
        requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_auto", "auto_enabled": True}
        )
        
        # Get status to check audit log
        status_response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers
        )
        data = status_response.json()
        
        audit_log = data.get("audit_log", [])
        
        # Find set_auto_enabled actions
        auto_actions = [e for e in audit_log if e.get("action") == "set_auto_enabled"]
        assert len(auto_actions) > 0, "Should find set_auto_enabled actions in audit log"
        
        print(f"✓ Audit log records set_auto actions ({len(auto_actions)} found)")
    
    def test_audit_log_records_set_bypass_action(self, admin_headers):
        """Audit log records admin set_bypass actions"""
        # Toggle bypass off and on
        requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_bypass", "premium_bypass": False}
        )
        requests.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers,
            json={"action": "set_bypass", "premium_bypass": True}
        )
        
        # Get status to check audit log
        status_response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers
        )
        data = status_response.json()
        
        audit_log = data.get("audit_log", [])
        
        # Find set_premium_bypass actions
        bypass_actions = [e for e in audit_log if e.get("action") == "set_premium_bypass"]
        assert len(bypass_actions) > 0, "Should find set_premium_bypass actions in audit log"
        
        print(f"✓ Audit log records set_bypass actions ({len(bypass_actions)} found)")


# ─── PER-QUEUE STATUS TESTS ───────────────────────────────────────────────────

class TestPerQueueStatus:
    """Tests for per-queue status in load guard"""
    
    def test_per_queue_has_all_queue_types(self, admin_headers):
        """per_queue field contains all 8 queue types"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        per_queue = data.get("per_queue", {})
        expected_queues = ["text", "image", "video", "audio", "export", "webhook", "analytics", "batch"]
        
        for queue in expected_queues:
            assert queue in per_queue, f"Missing queue type: {queue}"
        
        print(f"✓ All 8 queue types present in per_queue")
    
    def test_per_queue_has_required_fields(self, admin_headers):
        """Each queue in per_queue has required status fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        per_queue = data.get("per_queue", {})
        
        for queue_name, queue_data in per_queue.items():
            if queue_data.get("status") == "no_data":
                continue  # Skip queues with no data yet
            
            assert "queued" in queue_data, f"{queue_name} missing queued field"
            assert "processing" in queue_data, f"{queue_name} missing processing field"
            assert "weight_class" in queue_data, f"{queue_name} missing weight_class field"
            
            # Verify weight_class is valid
            assert queue_data["weight_class"] in ["light", "medium", "heavy"], \
                f"{queue_name} has invalid weight_class: {queue_data['weight_class']}"
        
        print("✓ Per-queue data has required fields with valid weight classes")


# ─── COMIC STORYBOOK ADMISSION TEST ───────────────────────────────────────────

class TestComicStorybookAdmission:
    """Tests for comic storybook admission with load guard"""
    
    def test_critical_mode_blocks_comic_storybook(self, admin_headers, free_user_headers):
        """When guard is CRITICAL, comic storybook generate returns 503 or 429"""
        import uuid
        try:
            # Set guard to critical
            set_response = requests.post(
                f"{BASE_URL}/api/admin/system-health/load-guard",
                headers=admin_headers,
                json={"action": "set_mode", "mode": "critical"}
            )
            assert set_response.status_code == 200
            
            time.sleep(0.5)
            
            # Use unique title to avoid idempotency conflicts
            unique_title = f"Test Comic {uuid.uuid4().hex[:8]}"
            
            # Try to generate comic storybook
            response = requests.post(
                f"{BASE_URL}/api/comic-storybook-v2/generate",
                headers=free_user_headers,
                json={
                    "genre": "kids_adventure",
                    "storyIdea": "A brave little rabbit goes on an adventure through the magical forest to find the golden carrot.",
                    "title": unique_title,
                    "author": "Test Author",
                    "pageCount": 10
                }
            )
            
            # Should be blocked - either 503 (admission rejected) or 429 (rate limit)
            # 409 is also acceptable if idempotency check happens before admission
            assert response.status_code in [429, 503, 409], \
                f"Expected 429, 503, or 409 in critical mode, got {response.status_code}: {response.text[:300]}"
            
            # If we got 503, verify it's from admission controller
            if response.status_code == 503:
                data = response.json()
                assert "detail" in data, "503 response should have detail"
            
            print(f"✓ Critical mode correctly blocks comic storybook (status: {response.status_code})")
        finally:
            reset_guard_to_normal(admin_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
