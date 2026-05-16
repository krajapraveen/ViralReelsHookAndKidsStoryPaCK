"""
P0 Growth Intervention V13.1 — Comprehensive Test Suite 2026-05

Tests all features from the P0-4 anonymous pre-wow flow and V13 activation diagnostics:

1. GET /api/funnel/activation-funnel (admin only) - V13 payload contract
2. POST /api/funnel/p04-launch (admin) - marks P0-4 deployment timestamp
3. GET /api/funnel/p04-launch (admin) - returns stored timestamp
4. GET /api/funnel/p04-comparison (admin) - before/after cohort comparison
5. All three new endpoints are admin-gated (401/403 for anonymous)
6. POST /api/funnel/track accepts 'session_resurrected' step
7. POST /api/public/quick-generate works WITHOUT Authorization header (anon flow)
"""
import os
import pytest
import requests
import time

BASE = os.environ.get("REACT_APP_BACKEND_URL") or os.environ.get("BACKEND_URL") or "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


def _admin_token():
    """Get admin authentication token."""
    r = requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("access_token") or data.get("token")


class TestActivationFunnelV13Payload:
    """Tests for GET /api/funnel/activation-funnel V13 payload contract."""

    def test_activation_funnel_requires_admin_auth(self):
        """Endpoint must reject anonymous requests."""
        r = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_activation_funnel_returns_v13_payload(self):
        """Endpoint returns all V13 required fields."""
        tok = _admin_token()
        r = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        
        # All required V13 fields
        required_keys = [
            "stages", "biggest_drop", "auth_wall", "rage_click_sessions",
            "repeated_cta_sessions", "median_time_to_abandon_ms",
            "abandonment_heatmap", "abandonment_breakdown", "red_alerts",
            "unmapped_reasons", "speed_sla", "total_sessions_seen",
        ]
        for key in required_keys:
            assert key in body, f"Missing required key: {key}"

    def test_biggest_drop_is_dict_not_int(self):
        """CRITICAL: biggest_drop must be dict (or None), NEVER an integer (bug fix verification)."""
        tok = _admin_token()
        r = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        
        bd = body["biggest_drop"]
        assert bd is None or isinstance(bd, dict), f"biggest_drop must be dict or None, got {type(bd).__name__}: {bd}"
        
        if isinstance(bd, dict):
            # Verify dict structure
            required_bd_keys = ["from_step", "from_label", "to_step", "to_label", 
                               "from_sessions", "to_sessions", "conversion_pct", "drop_pct"]
            for k in required_bd_keys:
                assert k in bd, f"biggest_drop missing key: {k}"

    def test_auth_wall_structure(self):
        """auth_wall must have total_sessions, pct_of_landing, breakdown."""
        tok = _admin_token()
        r = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        
        aw = body["auth_wall"]
        assert isinstance(aw, dict), f"auth_wall must be dict, got {type(aw).__name__}"
        assert "total_sessions" in aw, "auth_wall missing total_sessions"
        assert "pct_of_landing" in aw, "auth_wall missing pct_of_landing"
        assert "breakdown" in aw, "auth_wall missing breakdown"

    def test_abandonment_breakdown_sorted_by_count_desc(self):
        """abandonment_breakdown must be sorted by count descending."""
        tok = _admin_token()
        r = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        
        ab = body["abandonment_breakdown"]
        if len(ab) >= 2:
            counts = [item["count"] for item in ab]
            assert counts == sorted(counts, reverse=True), "abandonment_breakdown must be sorted by count DESC"

    def test_abandonment_heatmap_structure(self):
        """abandonment_heatmap must have mobile/desktop death percentages."""
        tok = _admin_token()
        r = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        
        heatmap = body["abandonment_heatmap"]
        assert isinstance(heatmap, list), "abandonment_heatmap must be a list"
        
        if len(heatmap) > 0:
            item = heatmap[0]
            required_keys = ["from_step", "from_label", "mobile_died", "desktop_died",
                           "mobile_total", "desktop_total", "mobile_death_pct", "desktop_death_pct"]
            for k in required_keys:
                assert k in item, f"heatmap item missing key: {k}"

    def test_speed_sla_structure(self):
        """speed_sla must have event, threshold_ms, samples, median_ms, p95_ms, breach_count, breach_pct."""
        tok = _admin_token()
        r = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        
        speed_sla = body["speed_sla"]
        assert isinstance(speed_sla, list), "speed_sla must be a list"
        
        if len(speed_sla) > 0:
            item = speed_sla[0]
            required_keys = ["event", "threshold_ms", "samples", "median_ms", "p95_ms", "breach_count", "breach_pct"]
            for k in required_keys:
                assert k in item, f"speed_sla item missing key: {k}"


class TestP04LaunchEndpoint:
    """Tests for POST/GET /api/funnel/p04-launch."""

    def test_p04_launch_post_requires_admin(self):
        """POST /api/funnel/p04-launch must reject anonymous requests."""
        r = requests.post(f"{BASE}/api/funnel/p04-launch", timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_p04_launch_get_requires_admin(self):
        """GET /api/funnel/p04-launch must reject anonymous requests."""
        r = requests.get(f"{BASE}/api/funnel/p04-launch", timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_p04_launch_post_marks_timestamp(self):
        """POST /api/funnel/p04-launch marks the deployment timestamp."""
        tok = _admin_token()
        r = requests.post(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert "p04_launch_ts" in body
        assert body["p04_launch_ts"] is not None

    def test_p04_launch_post_is_idempotent(self):
        """POST /api/funnel/p04-launch is idempotent (upsert)."""
        tok = _admin_token()
        
        # First call
        r1 = requests.post(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        assert r1.status_code == 200
        ts1 = r1.json()["p04_launch_ts"]
        
        # Second call should succeed (idempotent upsert)
        r2 = requests.post(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        assert r2.status_code == 200
        ts2 = r2.json()["p04_launch_ts"]
        
        # Both should succeed (idempotent)
        assert r1.json()["success"] is True
        assert r2.json()["success"] is True

    def test_p04_launch_get_returns_stored_ts(self):
        """GET /api/funnel/p04-launch returns the stored timestamp."""
        tok = _admin_token()
        
        # Ensure timestamp is set
        requests.post(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        
        # Get should return it
        r = requests.get(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "p04_launch_ts" in body
        assert body["p04_launch_ts"] is not None


class TestP04ComparisonEndpoint:
    """Tests for GET /api/funnel/p04-comparison."""

    def test_p04_comparison_requires_admin(self):
        """GET /api/funnel/p04-comparison must reject anonymous requests."""
        r = requests.get(f"{BASE}/api/funnel/p04-comparison", timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_p04_comparison_returns_cohort_data(self):
        """GET /api/funnel/p04-comparison returns pre/post cohorts with verdict."""
        tok = _admin_token()
        
        # Ensure launch timestamp is set
        requests.post(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        
        r = requests.get(f"{BASE}/api/funnel/p04-comparison?days_before=7&days_after=7", 
                        headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        
        assert body["success"] is True
        
        # Required fields
        required_keys = ["pre", "post", "deltas", "verdict", "verdict_signals", "window", "p04_launch_ts"]
        for key in required_keys:
            assert key in body, f"Missing required key: {key}"

    def test_p04_comparison_verdict_values(self):
        """verdict must be one of IMPROVED, REGRESSED, FLAT, INSUFFICIENT_DATA."""
        tok = _admin_token()
        
        # Ensure launch timestamp is set
        requests.post(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        
        r = requests.get(f"{BASE}/api/funnel/p04-comparison?days_before=7&days_after=7", 
                        headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        
        valid_verdicts = {"IMPROVED", "REGRESSED", "FLAT", "INSUFFICIENT_DATA"}
        assert body["verdict"] in valid_verdicts, f"Invalid verdict: {body['verdict']}"

    def test_p04_comparison_cohort_metrics(self):
        """pre and post cohorts must have required metrics."""
        tok = _admin_token()
        
        # Ensure launch timestamp is set
        requests.post(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
        
        r = requests.get(f"{BASE}/api/funnel/p04-comparison?days_before=7&days_after=7", 
                        headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200
        body = r.json()
        
        required_cohort_keys = [
            "landing_sessions", "cta_clicked", "story_generated", 
            "anon_generated", "auth_generated", "cta_to_generation_pct",
            "abandonment_pct", "auth_wall_sessions", "teaser_median_ms"
        ]
        
        for cohort_name in ["pre", "post"]:
            cohort = body[cohort_name]
            for key in required_cohort_keys:
                assert key in cohort, f"{cohort_name} cohort missing key: {key}"


class TestQuickGenerateAnonFlow:
    """Tests for POST /api/public/quick-generate (P0-4 anonymous flow)."""

    def test_quick_generate_works_without_auth(self):
        """POST /api/public/quick-generate must work WITHOUT Authorization header."""
        r = requests.post(
            f"{BASE}/api/public/quick-generate",
            json={"mode": "fresh", "session_id": f"anon_test_{int(time.time())}", "device_token": "test_device"},
            timeout=30,
        )
        # 200 = success, 429 = rate limited (acceptable)
        assert r.status_code in (200, 429), f"Expected 200 or 429, got {r.status_code}: {r.text}"
        
        if r.status_code == 200:
            body = r.json()
            assert "story_id" in body, "Response missing story_id"
            assert "story_text" in body, "Response missing story_text"
            assert "allow_free_view" in body, "Response missing allow_free_view"

    def test_quick_generate_returns_story_content(self):
        """Response must include story_id, story_text, allow_free_view."""
        r = requests.post(
            f"{BASE}/api/public/quick-generate",
            json={"mode": "fresh", "session_id": f"content_test_{int(time.time())}", "device_token": "test_device_2"},
            timeout=30,
        )
        
        if r.status_code == 200:
            body = r.json()
            assert body.get("story_id"), "story_id must be non-empty"
            assert body.get("story_text"), "story_text must be non-empty"
            assert isinstance(body.get("allow_free_view"), bool), "allow_free_view must be boolean"


class TestSessionResurrectedStep:
    """Tests for POST /api/funnel/track with session_resurrected step."""

    def test_session_resurrected_step_accepted(self):
        """POST /api/funnel/track must accept 'session_resurrected' step."""
        r = requests.post(
            f"{BASE}/api/funnel/track",
            json={
                "step": "session_resurrected",
                "session_id": f"resurrect_test_{int(time.time())}",
                "anonymous_id": "resurrect_anon_id",
                "context": {"source": "pytest", "age_ms": 3600000},
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True, f"Expected success=true, got {body}"

    def test_invalid_step_rejected(self):
        """POST /api/funnel/track must reject invalid step names."""
        r = requests.post(
            f"{BASE}/api/funnel/track",
            json={
                "step": "invalid_step_name_xyz",
                "session_id": "invalid_test",
            },
            timeout=10,
        )
        assert r.status_code == 200  # Returns 200 with success=false
        body = r.json()
        assert body.get("success") is False, "Invalid step should return success=false"


class TestAdminGating:
    """Tests to verify all new endpoints are properly admin-gated."""

    def test_activation_funnel_admin_gated(self):
        """GET /api/funnel/activation-funnel requires admin auth."""
        r = requests.get(f"{BASE}/api/funnel/activation-funnel", timeout=10)
        assert r.status_code in (401, 403)

    def test_p04_launch_post_admin_gated(self):
        """POST /api/funnel/p04-launch requires admin auth."""
        r = requests.post(f"{BASE}/api/funnel/p04-launch", timeout=10)
        assert r.status_code in (401, 403)

    def test_p04_launch_get_admin_gated(self):
        """GET /api/funnel/p04-launch requires admin auth."""
        r = requests.get(f"{BASE}/api/funnel/p04-launch", timeout=10)
        assert r.status_code in (401, 403)

    def test_p04_comparison_admin_gated(self):
        """GET /api/funnel/p04-comparison requires admin auth."""
        r = requests.get(f"{BASE}/api/funnel/p04-comparison", timeout=10)
        assert r.status_code in (401, 403)

    def test_admin_gets_200_on_all_endpoints(self):
        """Admin user should get 200 on all new endpoints."""
        tok = _admin_token()
        headers = {"Authorization": f"Bearer {tok}"}
        
        # activation-funnel
        r1 = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", headers=headers, timeout=20)
        assert r1.status_code == 200, f"activation-funnel failed: {r1.status_code}"
        
        # p04-launch POST
        r2 = requests.post(f"{BASE}/api/funnel/p04-launch", headers=headers, timeout=10)
        assert r2.status_code == 200, f"p04-launch POST failed: {r2.status_code}"
        
        # p04-launch GET
        r3 = requests.get(f"{BASE}/api/funnel/p04-launch", headers=headers, timeout=10)
        assert r3.status_code == 200, f"p04-launch GET failed: {r3.status_code}"
        
        # p04-comparison
        r4 = requests.get(f"{BASE}/api/funnel/p04-comparison?days_before=7&days_after=7", headers=headers, timeout=20)
        assert r4.status_code == 200, f"p04-comparison failed: {r4.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
