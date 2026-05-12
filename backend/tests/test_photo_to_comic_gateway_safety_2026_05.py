"""
P0 2026-05 — Photo to Comic create-comic regression.

Validates:
  1. Happy path — uploaded image + Comic Strip + Chibi + 6 panels succeeds.
  2. Unsupported style → controlled JSON 400 (NOT 500, NOT raw HTML).
  3. Frontend interceptor contract — when a route raises an HTTPException
     the response is application/json with a `detail` field. (Gateway 502
     HTML stripping is asserted in the JS interceptor test.)

These tests do NOT exercise the production nginx layer — they prove our
backend never emits raw HTML to the wire.
"""
import base64
import io
import re
import time

import pytest
import requests


def _read_env():
    with open("/app/frontend/.env") as f:
        m = re.search(r"^REACT_APP_BACKEND_URL=(.*)$", f.read(), flags=re.M)
    return m.group(1).strip()


API = _read_env()


def _login(email: str, password: str) -> str:
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("access_token") or data.get("token")


def _tiny_png() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login("admin@creatorstudio.ai", "Cr3@t0rStud!o#2026")


def test_happy_path_chibi_strip_6_panels(admin_token: str):
    """Replicates the exact failing combination from the user's screenshot."""
    files = {"photo": ("tiny.png", io.BytesIO(_tiny_png()), "image/png")}
    data = {
        "mode": "strip",
        "style": "cute_chibi",  # canonical backend enum for the "Chibi" UI tile
        "genre": "action",
        "panel_count": "6",
        "hd_export": "false",
        "include_dialogue": "true",
    }
    r = requests.post(
        f"{API}/api/photo-to-comic/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        files=files,
        data=data,
        timeout=60,
    )
    assert r.headers.get("content-type", "").startswith("application/json"), (
        f"Expected JSON, got content-type={r.headers.get('content-type')!r} body={r.text[:200]!r}"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    assert body.get("jobId")


def test_unsupported_style_returns_400_json(admin_token: str):
    """Unsupported style enum MUST return a controlled JSON 400 (not 500,
    not silent fallback to cartoon_fun, not raw HTML)."""
    files = {"photo": ("tiny.png", io.BytesIO(_tiny_png()), "image/png")}
    data = {
        "mode": "strip",
        "style": "definitely_not_a_real_style_xyz",
        "genre": "action",
        "panel_count": "4",
        "hd_export": "false",
        "include_dialogue": "true",
    }
    r = requests.post(
        f"{API}/api/photo-to-comic/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        files=files,
        data=data,
        timeout=30,
    )
    assert r.status_code == 400, r.text
    assert r.headers.get("content-type", "").startswith("application/json")
    payload = r.json()
    assert "detail" in payload
    assert "invalid style" in payload["detail"].lower()


def test_unsupported_mode_returns_400_json(admin_token: str):
    """Invalid mode must also be JSON 400."""
    files = {"photo": ("tiny.png", io.BytesIO(_tiny_png()), "image/png")}
    data = {
        "mode": "totally_invalid_mode",
        "style": "chibi",
        "genre": "action",
        "panel_count": "4",
        "hd_export": "false",
        "include_dialogue": "true",
    }
    r = requests.post(
        f"{API}/api/photo-to-comic/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        files=files,
        data=data,
        timeout=30,
    )
    assert r.status_code == 400, r.text
    assert r.headers.get("content-type", "").startswith("application/json")


def test_admin_unlimited_not_blocked_by_balance(admin_token: str):
    """Sanity — admin unlimited must NOT be credit-gated."""
    r = requests.get(
        f"{API}/api/credits/balance",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload.get("is_unlimited") is True
    # And the generate call still succeeds (separately covered above).
