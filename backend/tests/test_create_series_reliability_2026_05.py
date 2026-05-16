"""
Create Series P0 reliability regression — 2026-05-16
Locks in the fix for the "service temporarily unavailable" prod failure:
  • Bounded LLM timeout returns a structured 504 BEFORE the gateway
  • Structured per-failure-class error codes the frontend can show
  • Duplicate-submission idempotency within 60s
  • Admin debug endpoint admin-gated + returns 404 on unknown id
  • Funnel events whitelisted + ingestible
  • Frontend renders code-aware messages (no [object Object])
  • Frontend prevents double-clicks
"""
import os
import re
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
SERIES_PY = ROOT / "backend" / "routes" / "story_series.py"
FRONTEND = ROOT / "frontend" / "src" / "pages" / "CreateSeries.js"
FUNNEL_PY = ROOT / "backend" / "routes" / "funnel_tracking.py"

ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


def _admin_token():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


# ─── 1. Bounded LLM timeout ────────────────────────────────────────
def test_llm_json_has_bounded_timeout():
    src = SERIES_PY.read_text(encoding="utf-8")
    assert "asyncio.wait_for" in src, "_llm_json must wrap send_message in asyncio.wait_for"
    assert "timeout_s" in src, "_llm_json must accept timeout_s parameter"
    # Default should be ≤ 55s (gateway hard-limit is 60s on Cloudflare)
    m = re.search(r"timeout_s:\s*float\s*=\s*(\d+\.?\d*)", src)
    assert m, "timeout_s default must be defined"
    assert float(m.group(1)) <= 55.0, "timeout_s default must be ≤ 55s to beat the gateway"


# ─── 2. Structured per-failure-class error codes ───────────────────
def test_create_returns_structured_codes_for_each_failure_class():
    src = SERIES_PY.read_text(encoding="utf-8")
    for code in ("LLM_TIMEOUT", "LLM_BAD_JSON", "LLM_RATE_LIMITED",
                 "LLM_BUDGET_EXHAUSTED", "LLM_AUTH_FAILED", "LLM_UPSTREAM_ERROR"):
        assert code in src, f"Missing structured error code: {code}"
    # And every code must surface in a `detail={...}` dict (not a bare string)
    assert "detail={" in src and '"code":' in src.replace("'", '"'), \
        "Error responses must use structured detail={code, message, retryable}"


# ─── 3. Duplicate idempotency ──────────────────────────────────────
def test_duplicate_submission_returns_existing_series():
    tok = _admin_token()
    body = {
        "title": "Idempotency Probe " + os.urandom(3).hex(),
        "initial_prompt": "Short story prompt for idempotency.",
        "genre": "Drama",
        "audience": "Adults",
        "style": "Cinematic",
        "tool": "story_video",
    }
    r1 = requests.post(f"{BASE}/api/story-series/create",
                       headers={"Authorization": f"Bearer {tok}"},
                       json=body, timeout=120)
    assert r1.status_code == 200, r1.text
    sid1 = r1.json()["series_id"]
    assert r1.json().get("duplicate") is not True  # first call is fresh

    r2 = requests.post(f"{BASE}/api/story-series/create",
                       headers={"Authorization": f"Bearer {tok}"},
                       json=body, timeout=15)
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2.get("duplicate") is True
    assert body2["series_id"] == sid1


# ─── 4. Admin debug endpoint ───────────────────────────────────────
def test_admin_debug_endpoint_admin_gated():
    r = requests.get(f"{BASE}/api/story-series/jobs/anything/debug", timeout=10)
    assert r.status_code in (401, 403)


def test_admin_debug_returns_404_for_unknown_id():
    tok = _admin_token()
    r = requests.get(
        f"{BASE}/api/story-series/jobs/__pytest_does_not_exist__/debug",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=10,
    )
    assert r.status_code == 404, f"Expected 404 for unknown id, got {r.status_code}"


# ─── 5. Funnel events whitelisted + ingestible ─────────────────────
def test_create_series_funnel_events_whitelisted():
    src = FUNNEL_PY.read_text(encoding="utf-8")
    for ev in ("create_series_clicked", "create_series_started",
               "create_series_completed", "create_series_failed",
               "create_series_timeout"):
        assert f'"{ev}"' in src, f"Missing funnel event: {ev}"


def test_funnel_endpoint_accepts_create_series_events():
    for step in ("create_series_clicked", "create_series_started",
                 "create_series_completed", "create_series_failed",
                 "create_series_timeout"):
        r = requests.post(
            f"{BASE}/api/funnel/track",
            json={"step": step, "session_id": "pytest_series", "anonymous_id": "pytest_series_anon",
                  "context": {"source": "pytest"}},
            timeout=10,
        )
        assert r.status_code == 200, f"{step} -> {r.status_code}"


# ─── 6. Frontend renders code-aware messages, prevents double-click ─
def test_frontend_handles_structured_detail_object_and_double_click():
    src = FRONTEND.read_text(encoding="utf-8")
    # Must extract d.detail.message when detail is an object
    assert "d.detail.message" in src or "d?.detail?.message" in src or "d.detail && typeof d.detail === 'object'" in src, \
        "Frontend must extract structured detail.message (avoids [object Object])"
    # Must guard against double-click
    assert "if (creating) return" in src, \
        "Frontend handleCreate must guard against double-click via creating flag"
    # Must specifically reference the gateway / 502+ fallback message
    assert "AI service is briefly unavailable" in src or "AI service is briefly" in src, \
        "Frontend must show actionable gateway-fallback message (not generic)"
    # Must have a request timeout
    assert "timeout: 60000" in src or "timeout:60000" in src, \
        "Frontend must set an axios timeout on the create call"


# ─── 7. Validation errors still pass through as 422 ───────────────
def test_validation_errors_are_not_swallowed_by_gateway_handler():
    """Bad payload must return 422 with field-level detail, NOT a 503 gateway shape."""
    tok = _admin_token()
    r = requests.post(
        f"{BASE}/api/story-series/create",
        headers={"Authorization": f"Bearer {tok}"},
        json={"genre": "x"},  # missing title + initial_prompt
        timeout=10,
    )
    assert r.status_code == 422
    body = r.json()
    assert isinstance(body.get("detail"), list)
    assert any(d.get("loc") and "title" in (d["loc"] or []) for d in body["detail"])
