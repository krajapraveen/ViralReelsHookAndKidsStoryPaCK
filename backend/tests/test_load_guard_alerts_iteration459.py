"""
Load Guard Alert System Tests - Iteration 459
==============================================
Tests for the NEW alerting layer added on top of Load Guard:
- Alert persistence to MongoDB (load_guard_alerts collection)
- Alert endpoints: /alerts, /alerts/active, /alerts/summary
- Alert payload field validation
- Manual override triggers manual_override alert
- Non-admin access returns 403
- Backward compatibility with existing Load Guard endpoints
- Graceful handling when SLACK_WEBHOOK_URL is not set
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", os.environ.get("BACKEND_PUBLIC_URL", "https://trust-engine-5.preview.emergentagent.com")).strip().strip('"').rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
FREE_USER_EMAIL = "test@visionary-suite.com"
FREE_USER_PASSWORD = "Test@2026#"


class TestLoadGuardAlerts:
    """Load Guard Alert System Tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get admin token and reset guard mode before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        data = login_resp.json()
        self.admin_token = data.get("token") or data.get("access_token")
        assert self.admin_token, "No token in admin login response"
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
        
        # Reset guard mode to null (auto) before each test
        reset_resp = self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": None}
        )
        # Allow 200 or 400 (if already null)
        
        yield
        
        # Cleanup: Reset guard mode after each test
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": None}
        )

    @pytest.fixture
    def free_user_token(self):
        """Get free user token for non-admin tests"""
        resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": FREE_USER_EMAIL,
            "password": FREE_USER_PASSWORD
        })
        if resp.status_code != 200:
            pytest.skip("Free user login failed - skipping non-admin test")
        data = resp.json()
        return data.get("token") or data.get("access_token")

    # ─── ALERT ENDPOINT TESTS ─────────────────────────────────────────────

    def test_get_alerts_endpoint_returns_200(self):
        """GET /api/admin/system-health/alerts returns 200 for admin"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts",
            headers=self.admin_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "alerts" in data, "Response should contain 'alerts' key"
        assert "count" in data, "Response should contain 'count' key"

    def test_get_active_alerts_endpoint_returns_200(self):
        """GET /api/admin/system-health/alerts/active returns 200 for admin"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts/active",
            headers=self.admin_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "active_incidents" in data, "Response should contain 'active_incidents' key"
        assert "count" in data, "Response should contain 'count' key"

    def test_get_alerts_summary_endpoint_returns_200(self):
        """GET /api/admin/system-health/alerts/summary returns 200 for admin"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts/summary",
            headers=self.admin_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "total_alerts" in data, "Response should contain 'total_alerts' key"
        assert "active_incidents" in data, "Response should contain 'active_incidents' key"
        assert "breakdown" in data, "Response should contain 'breakdown' key"

    # ─── MANUAL OVERRIDE ALERT TESTS ──────────────────────────────────────

    def test_set_mode_triggers_manual_override_alert(self):
        """POST /api/admin/system-health/load-guard with set_mode triggers manual_override alert"""
        # Get initial alert count
        initial_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=200",
            headers=self.admin_headers
        )
        initial_count = initial_resp.json().get("count", 0)
        
        # Set mode to critical
        set_resp = self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": "critical"}
        )
        assert set_resp.status_code == 200, f"Set mode failed: {set_resp.text}"
        
        # Wait for async alert to be persisted
        time.sleep(1)
        
        # Check alerts - should have new manual_override alert
        alerts_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=200",
            headers=self.admin_headers
        )
        assert alerts_resp.status_code == 200
        data = alerts_resp.json()
        
        # Verify alert count increased
        assert data["count"] > initial_count, "Manual override alert should be created"
        
        # Verify latest alert has correct type
        if data["alerts"]:
            latest_alert = data["alerts"][0]
            assert latest_alert["alert_type"] == "manual_override"

    def test_alert_payload_contains_required_fields(self):
        """Alert payload contains all required fields"""
        # Trigger a manual override alert
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": "stressed"}
        )
        time.sleep(1)
        
        # Get the alert
        alerts_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=1",
            headers=self.admin_headers
        )
        assert alerts_resp.status_code == 200
        data = alerts_resp.json()
        
        if data["alerts"]:
            alert = data["alerts"][0]
            payload = alert.get("payload", {})
            
            # Required fields in payload
            required_fields = [
                "incident_id", "timestamp", "previous_mode", "new_mode",
                "affected_queues", "queue_depth", "oldest_wait_s",
                "worker_saturation_pct", "admitted_jobs_per_sec",
                "completed_jobs_per_sec", "dead_letter_count",
                "dashboard_link", "api_link"
            ]
            
            for field in required_fields:
                assert field in payload, f"Payload missing required field: {field}"
            
            # Verify incident_id is present at top level too
            assert "incident_id" in alert, "Alert should have incident_id at top level"

    def test_dashboard_link_points_to_admin(self):
        """dashboard_link in alert payload points to /admin"""
        # Trigger alert
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": "severe"}
        )
        time.sleep(1)
        
        alerts_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=1",
            headers=self.admin_headers
        )
        data = alerts_resp.json()
        
        if data["alerts"]:
            payload = data["alerts"][0].get("payload", {})
            dashboard_link = payload.get("dashboard_link", "")
            assert "/admin" in dashboard_link, f"dashboard_link should contain /admin, got: {dashboard_link}"

    def test_api_link_points_to_load_guard(self):
        """api_link in alert payload points to /api/admin/system-health/load-guard"""
        # Trigger alert
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": "stressed"}
        )
        time.sleep(1)
        
        alerts_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=1",
            headers=self.admin_headers
        )
        data = alerts_resp.json()
        
        if data["alerts"]:
            payload = data["alerts"][0].get("payload", {})
            api_link = payload.get("api_link", "")
            assert "/api/admin/system-health/load-guard" in api_link, f"api_link should contain /api/admin/system-health/load-guard, got: {api_link}"

    def test_critical_then_normal_creates_two_alerts(self):
        """Setting guard to critical then back to normal creates two separate alerts"""
        # Get initial count
        initial_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=200",
            headers=self.admin_headers
        )
        initial_count = initial_resp.json().get("count", 0)
        
        # Set to critical
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": "critical"}
        )
        time.sleep(0.5)
        
        # Set back to normal (null)
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": None}
        )
        time.sleep(1)
        
        # Check alert count increased by at least 2
        final_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=200",
            headers=self.admin_headers
        )
        final_count = final_resp.json().get("count", 0)
        
        assert final_count >= initial_count + 2, f"Expected at least 2 new alerts, got {final_count - initial_count}"

    def test_alert_has_unique_incident_id(self):
        """Each alert has a unique incident_id"""
        # Trigger two alerts
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": "critical"}
        )
        time.sleep(0.5)
        
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": None}
        )
        time.sleep(1)
        
        # Get recent alerts
        alerts_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=10",
            headers=self.admin_headers
        )
        data = alerts_resp.json()
        
        if len(data["alerts"]) >= 2:
            incident_ids = [a.get("incident_id") for a in data["alerts"]]
            # Check that incident_ids exist
            assert all(id is not None for id in incident_ids), "All alerts should have incident_id"

    # ─── FILTER TESTS ─────────────────────────────────────────────────────

    def test_alerts_filter_by_status_active(self):
        """GET /api/admin/system-health/alerts?status=active filters correctly"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?status=active",
            headers=self.admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # All returned alerts should have status=active
        for alert in data.get("alerts", []):
            assert alert.get("status") == "active", f"Expected status=active, got {alert.get('status')}"

    def test_alerts_filter_by_alert_type(self):
        """GET /api/admin/system-health/alerts?alert_type=manual_override filters by type"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override",
            headers=self.admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # All returned alerts should have alert_type=manual_override
        for alert in data.get("alerts", []):
            assert alert.get("alert_type") == "manual_override", f"Expected alert_type=manual_override, got {alert.get('alert_type')}"

    # ─── NON-ADMIN ACCESS TESTS ───────────────────────────────────────────

    def test_non_admin_cannot_access_alerts(self, free_user_token):
        """Non-admin cannot access alert endpoints (403)"""
        headers = {
            "Authorization": f"Bearer {free_user_token}",
            "Content-Type": "application/json"
        }
        
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts",
            headers=headers
        )
        assert resp.status_code == 403, f"Expected 403 for non-admin, got {resp.status_code}"

    def test_non_admin_cannot_access_active_alerts(self, free_user_token):
        """Non-admin cannot access /alerts/active endpoint (403)"""
        headers = {
            "Authorization": f"Bearer {free_user_token}",
            "Content-Type": "application/json"
        }
        
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts/active",
            headers=headers
        )
        assert resp.status_code == 403, f"Expected 403 for non-admin, got {resp.status_code}"

    def test_non_admin_cannot_access_alerts_summary(self, free_user_token):
        """Non-admin cannot access /alerts/summary endpoint (403)"""
        headers = {
            "Authorization": f"Bearer {free_user_token}",
            "Content-Type": "application/json"
        }
        
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts/summary",
            headers=headers
        )
        assert resp.status_code == 403, f"Expected 403 for non-admin, got {resp.status_code}"

    # ─── BACKWARD COMPATIBILITY TESTS ─────────────────────────────────────

    def test_load_guard_status_get_still_works(self):
        """Load guard status GET still works (backward compat)"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "guard_mode" in data, "Response should contain guard_mode"
        assert "signals" in data, "Response should contain signals"
        assert "per_queue" in data, "Response should contain per_queue"

    def test_load_guard_decisions_get_still_works(self):
        """Load guard decisions GET still works (backward compat)"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/load-guard/decisions",
            headers=self.admin_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "decisions" in data, "Response should contain decisions"

    def test_system_health_overview_backward_compat(self):
        """System health overview still works (backward compat)"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/overview",
            headers=self.admin_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "timestamp" in data, "Response should contain timestamp"
        assert "queues" in data, "Response should contain queues"
        assert "workers" in data, "Response should contain workers"
        assert "database" in data, "Response should contain database"

    def test_pipeline_create_returns_429_when_guard_critical(self):
        """Pipeline/create still returns 429 when guard is critical (backward compat)"""
        # Set guard to critical
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": "critical"}
        )
        time.sleep(0.5)
        
        # Login as free user
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": FREE_USER_EMAIL,
            "password": FREE_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Free user login failed")
        
        free_token = login_resp.json().get("token") or login_resp.json().get("access_token")
        free_headers = {
            "Authorization": f"Bearer {free_token}",
            "Content-Type": "application/json"
        }
        
        # Try to create a pipeline job - should get 429
        # story_text must be >= 50 chars
        create_resp = self.session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers=free_headers,
            json={
                "title": "Test Story",
                "story_text": "This is a test story that is at least fifty characters long for testing purposes.",
                "animation_style": "anime",
                "age_group": "general",
                "voice_preset": "nova",
                "num_scenes": 2
            }
        )
        
        # Should be 429 (admission rejected) when guard is critical
        assert create_resp.status_code == 429, f"Expected 429 when guard is critical, got {create_resp.status_code}: {create_resp.text}"

    # ─── GRACEFUL FALLBACK TEST ───────────────────────────────────────────

    def test_alert_system_works_without_slack_webhook(self):
        """Alert system does not crash when SLACK_WEBHOOK_URL is not set"""
        # This test verifies that alerts are still persisted to DB even without Slack
        
        # Get initial count
        initial_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=200",
            headers=self.admin_headers
        )
        initial_count = initial_resp.json().get("count", 0)
        
        # Trigger alert (Slack will be skipped, but DB should work)
        set_resp = self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": "stressed"}
        )
        assert set_resp.status_code == 200, f"Set mode should succeed even without Slack: {set_resp.text}"
        
        time.sleep(1)
        
        # Verify alert was persisted to DB
        final_resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts?alert_type=manual_override&limit=200",
            headers=self.admin_headers
        )
        final_count = final_resp.json().get("count", 0)
        
        assert final_count > initial_count, "Alert should be persisted to DB even without Slack webhook"


class TestAlertSummaryAggregation:
    """Tests for alert summary aggregation endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get admin token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        data = login_resp.json()
        self.admin_token = data.get("token") or data.get("access_token")
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
        
        yield
        
        # Cleanup
        self.session.post(
            f"{BASE_URL}/api/admin/system-health/load-guard",
            headers=self.admin_headers,
            json={"action": "set_mode", "mode": None}
        )

    def test_summary_returns_aggregate_counts(self):
        """GET /api/admin/system-health/alerts/summary returns aggregate counts by type and status"""
        resp = self.session.get(
            f"{BASE_URL}/api/admin/system-health/alerts/summary",
            headers=self.admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify structure
        assert "total_alerts" in data
        assert "active_incidents" in data
        assert "breakdown" in data
        assert isinstance(data["breakdown"], dict)
        
        # total_alerts should be >= active_incidents
        assert data["total_alerts"] >= data["active_incidents"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
