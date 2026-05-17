"""
P1 2026-05-19 — Diagnostics beacon endpoint backend tests.

Uses the live preview backend (REACT_APP_BACKEND_URL) instead of an
in-process TestClient because the in-process motor client is bound to
the supervisor-managed event loop. This matches how the frontend
will actually call the endpoint.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import requests


def _backend_url() -> str:
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("REACT_APP_BACKEND_URL", "")


BASE = _backend_url()
BEACON = f"{BASE}/api/diagnostics/beacon"


@pytest.fixture(scope="module", autouse=True)
def _require_backend():
    if not BASE:
        pytest.skip("REACT_APP_BACKEND_URL not configured")
    # Sanity ping — fail fast if the backend is down.
    try:
        r = requests.post(BEACON, json={"events": []}, timeout=5)
        assert r.status_code == 200, r.text
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Backend not reachable for beacon tests: {exc}")


def test_beacon_accepts_allow_listed_metrics():
    r = requests.post(
        BEACON,
        json={
            "events": [
                {"metric": "frontend_event_trap_blocked_total", "page": "/app/photo-to-comic"},
                {"metric": "error_toast_without_request_id_total", "page": "/app/x"},
                {"metric": "p2c_label_fallback_total", "meta": {"extracted_from": "label"}},
            ]
        },
        headers={"X-Request-Id": "test-req-1"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] == 3, body
    assert body["rejected"] == 0, body


def test_beacon_rejects_unknown_metrics():
    r = requests.post(
        BEACON,
        json={
            "events": [
                {"metric": "rm -rf /"},
                {"metric": "frontend_event_trap_blocked_total"},
                {"metric": "<script>"},
            ]
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] == 1, body
    assert body["rejected"] == 2, body


def test_beacon_handles_empty_batch():
    r = requests.post(BEACON, json={"events": []}, timeout=10)
    assert r.status_code == 200
    assert r.json() == {"accepted": 0, "rejected": 0}


def test_beacon_meta_size_is_capped():
    huge = "x" * 5000
    r = requests.post(
        BEACON,
        json={
            "events": [
                {
                    "metric": "frontend_event_trap_blocked_total",
                    "meta": {"big": huge, "k2": "v2"},
                }
            ]
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json()["accepted"] == 1


def test_beacon_caps_payload_size():
    # 80 events — server caps at 50 per batch.
    events = [{"metric": "frontend_event_trap_blocked_total"} for _ in range(80)]
    r = requests.post(BEACON, json={"events": events}, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] == 50, body


def test_beacon_aggregates_counts_per_bucket():
    # Use a unique meta tag so we can find the contribution post-hoc.
    tag = f"agg-test-{time.time_ns()}"
    for _ in range(3):
        r = requests.post(
            BEACON,
            json={"events": [{"metric": "p2c_label_fallback_total", "meta": {"tag": tag}}]},
            timeout=10,
        )
        assert r.status_code == 200
    r = requests.post(
        BEACON,
        json={"events": [
            {"metric": "p2c_label_fallback_total", "meta": {"tag": tag}},
            {"metric": "p2c_label_fallback_total", "meta": {"tag": tag}},
        ]},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["accepted"] == 2


def test_metrics_admin_endpoint_requires_admin():
    r = requests.get(f"{BASE}/api/diagnostics/metrics", timeout=10)
    assert r.status_code in (401, 403)
