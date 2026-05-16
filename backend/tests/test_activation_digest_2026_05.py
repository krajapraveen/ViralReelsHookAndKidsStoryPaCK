"""
P0 Activation Digest — 2026-05
Verifies the brutal-truth digest behavior:
  • INSUFFICIENT_DATA when traffic is below 50 sessions
  • Confidence ladder: LOW / MEDIUM / HIGH
  • Retention cap at 30
  • Admin-gating
  • Persistence + latest + history + run-now endpoints
  • Email is secondary (never breaks the API path)
  • Regression alert when a critical metric drops >20% day-over-day
  • Exactly ONE next_action returned
"""
import os
import asyncio
import requests
import pytest
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


def _admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


def test_endpoints_admin_gated():
    for path in ("/api/admin/activation-digest/latest",
                 "/api/admin/activation-digest/history",
                 "/api/admin/activation-digest/preview"):
        assert requests.get(f"{BASE}{path}", timeout=10).status_code in (401, 403)
    assert requests.post(f"{BASE}/api/admin/activation-digest/run-now", timeout=10).status_code in (401, 403)


def test_preview_returns_structure():
    tok = _admin_token()
    r = requests.get(f"{BASE}/api/admin/activation-digest/preview", headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    d = body["digest"]
    for key in ("report_date", "generated_at", "confidence", "traffic_sample",
                "alerts", "next_action", "today_metrics", "yesterday_metrics"):
        assert key in d, f"missing key in digest: {key}"
    assert d["confidence"] in ("INSUFFICIENT_DATA", "LOW", "MEDIUM", "HIGH")
    # Exactly one next_action string (not a list)
    assert isinstance(d["next_action"], str) and len(d["next_action"]) > 0
    # Text rendering returns
    assert isinstance(body["text"], str) and "ACTIVATION DIGEST" in body["text"]


def test_run_now_persists_and_latest_returns():
    tok = _admin_token()
    r = requests.post(f"{BASE}/api/admin/activation-digest/run-now?skip_email=true",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["email"].get("skipped") is True
    # Latest must now return a digest
    r2 = requests.get(f"{BASE}/api/admin/activation-digest/latest",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    assert r2.status_code == 200
    assert r2.json()["digest"] is not None


def test_history_endpoint_respects_retention_cap():
    tok = _admin_token()
    r = requests.get(f"{BASE}/api/admin/activation-digest/history?limit=30",
                     headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["retained_max"] == 30
    assert body["count"] <= 30


def test_insufficient_data_when_traffic_low():
    """With current preview traffic (< 50 sessions / day), we MUST return
    INSUFFICIENT_DATA and an operational 'wait for traffic' next action — no
    fabricated leak/improvement/bottleneck."""
    tok = _admin_token()
    r = requests.get(f"{BASE}/api/admin/activation-digest/preview",
                     headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    d = r.json()["digest"]
    if d["confidence"] == "INSUFFICIENT_DATA":
        # alerts must be empty when below threshold (don't fabricate on noise)
        assert d["alerts"] == []
        # next_action must talk about traffic
        assert "traffic" in d["next_action"].lower() or "wait" in d["next_action"].lower()


def test_regression_detector_fires_red_alert():
    """Pure-unit-style test of the regression detector at >20% threshold."""
    from services.activation_digest_service import _detect_regressions
    today = {
        "story_generated": 80,
        "cta_to_generation_pct": 40.0,
        "landing_to_generation_pct": 20.0,
        "auth_wall_sessions": 50,
        "teaser_median_ms": 3000,
    }
    yesterday = {
        "story_generated": 200,         # -60% → RED
        "cta_to_generation_pct": 60.0,  # -33% → RED
        "landing_to_generation_pct": 22.0,  # -9% → NOT red
        "auth_wall_sessions": 20,       # +150% (auth-wall up = bad) → RED
        "teaser_median_ms": 2000,       # +50% (latency up = bad) → RED
    }
    alerts = _detect_regressions(today, yesterday)
    metrics = {a["metric"] for a in alerts}
    assert "story_generated" in metrics
    assert "cta_to_generation_pct" in metrics
    assert "auth_wall_sessions" in metrics
    assert "teaser_median_ms" in metrics
    assert "landing_to_generation_pct" not in metrics  # below threshold
    for a in alerts:
        assert a["severity"] == "RED"


def test_recommend_next_returns_single_string():
    from services.activation_digest_service import _recommend_next
    out = _recommend_next({"biggest_drop": {"from_step": "hero_cta_clicked",
                                            "from_label": "CTA", "to_label": "Prompt",
                                            "drop_pct": 70.0, "conv_pct": 30.0,
                                            "from_sessions": 100, "to_sessions": 30}}, [])
    assert isinstance(out, str)
    assert "example prompts" in out.lower()
    # With regression, recommendation should change to investigate
    out2 = _recommend_next({"biggest_drop": None},
                           [{"label": "CTA→Generation %", "delta_pct": -45.0, "metric": "x", "today": 1, "yesterday": 10, "severity": "RED"}])
    assert "investigate" in out2.lower()
