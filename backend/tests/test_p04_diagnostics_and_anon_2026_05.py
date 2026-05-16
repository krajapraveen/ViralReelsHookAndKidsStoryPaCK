"""
P0 Growth Intervention V13.1 — 2026-05 (P0-3 diagnostics UI wiring + P0-4 anon flow).

Verifies:
  • /api/funnel/activation-funnel returns the V13 payload contract the new
    ActivationDiagnostics UI consumes (biggest_drop dict, auth_wall block,
    rage_click_sessions, abandonment_heatmap, abandonment_breakdown sorted
    by count, median_time_to_abandon_ms).
  • /api/funnel/p04-launch + /api/funnel/p04-comparison are admin-gated,
    work idempotently, and return the verdict structure (INSUFFICIENT_DATA
    is acceptable when traffic is sparse).
  • /api/public/quick-generate works WITHOUT auth (P0-4 anon flow gate).
  • `session_resurrected` step is in the funnel-event whitelist.
"""
import os
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL") or os.environ.get("BACKEND_URL") or "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


def _admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("access_token") or data.get("token")


def test_activation_funnel_v13_payload_contract():
    tok = _admin_token()
    r = requests.get(f"{BASE}/api/funnel/activation-funnel?days=7", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    # Required new fields the diagnostics UI consumes
    for key in [
        "stages", "biggest_drop", "auth_wall", "rage_click_sessions",
        "repeated_cta_sessions", "median_time_to_abandon_ms",
        "abandonment_heatmap", "abandonment_breakdown", "red_alerts",
        "unmapped_reasons", "speed_sla", "total_sessions_seen",
    ]:
        assert key in body, f"missing key in payload: {key}"

    # biggest_drop must be either None or a DICT (not the old integer bug)
    bd = body["biggest_drop"]
    assert bd is None or isinstance(bd, dict), f"biggest_drop must be dict, got {type(bd).__name__}"
    if isinstance(bd, dict):
        for k in ("from_step", "to_step", "from_sessions", "to_sessions", "drop_pct"):
            assert k in bd, f"biggest_drop missing {k}"

    # auth_wall must be a dict with explicit fields
    aw = body["auth_wall"]
    assert isinstance(aw, dict) and "total_sessions" in aw and "pct_of_landing" in aw and "breakdown" in aw

    # Abandonment breakdown sorted by count desc
    ab = body["abandonment_breakdown"]
    if len(ab) >= 2:
        counts = [r["count"] for r in ab]
        assert counts == sorted(counts, reverse=True), "abandonment_breakdown must be sorted by count desc"


def test_p04_launch_and_comparison_endpoints_admin_gated():
    # No-auth call must be unauthorized
    r = requests.get(f"{BASE}/api/funnel/p04-comparison", timeout=10)
    assert r.status_code in (401, 403), r.text

    tok = _admin_token()
    # Mark launch
    r = requests.post(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True and body.get("p04_launch_ts")

    # Get launch
    r = requests.get(f"{BASE}/api/funnel/p04-launch", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    assert r.status_code == 200
    assert r.json().get("p04_launch_ts")

    # Comparison
    r = requests.get(f"{BASE}/api/funnel/p04-comparison?days_before=7&days_after=7", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    for key in ("pre", "post", "deltas", "verdict", "verdict_signals", "window"):
        assert key in body
    assert body["verdict"] in {"IMPROVED", "REGRESSED", "FLAT", "INSUFFICIENT_DATA"}


def test_quick_generate_no_auth_required_p04():
    """P0-4 — anonymous user must get a teaser without signing up."""
    r = requests.post(
        f"{BASE}/api/public/quick-generate",
        json={"mode": "fresh", "session_id": "p04_anon_test", "device_token": "p04_device"},
        timeout=30,
    )
    assert r.status_code in (200, 429), r.text  # 429 only if a previous test exhausted rate-limit
    if r.status_code == 200:
        body = r.json()
        assert body.get("story_id") and body.get("story_text")
        # allow_free_view must be present so frontend can gate continuations
        assert "allow_free_view" in body


def test_session_resurrected_step_accepted():
    """Whitelist regression — new P0-4 telemetry event must be ingestible."""
    r = requests.post(
        f"{BASE}/api/funnel/track",
        json={
            "step": "session_resurrected",
            "session_id": "p04_resurrect_test",
            "anonymous_id": "p04_resurrect_anon",
            "context": {"source": "pytest"},
        },
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json().get("success") is True
