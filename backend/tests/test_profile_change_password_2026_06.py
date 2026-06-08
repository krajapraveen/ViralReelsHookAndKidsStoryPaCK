"""P0 2026-06 — In-app Change Password (Profile → Security tab).

User-facing requirement:
  When the user clicks "Change Password" in Profile → Security tab,
  the UI must:
    • NOT send any password reset email.
    • Require the user to enter their CURRENT password.
    • Require a NEW password + CONFIRM password.
    • Validate all three against the database via PUT /api/auth/password.
    • Surface the actual backend reason on failure (wrong current,
      weak new, same as current, Google account, etc).

Backend contract (PUT /api/auth/password):
  • Auth-gated (JWT required).
  • Body: { currentPassword: str, newPassword: str }.
  • 200 + {success, message} on success.
  • 400 if:
      - User not found
      - authProvider == "google" (no password set)
      - currentPassword wrong (bcrypt mismatch)
      - newPassword fails strength rules
      - newPassword == currentPassword
  • Updates password hash + passwordChangedAt.
  • Does NOT send any email.

Frontend contract (Profile.js → Security tab):
  • Three inputs: currentPassword, newPassword, confirmPassword.
  • Show/hide toggles on all three (data-testid eye buttons).
  • Inline "Passwords do not match" hint when confirm != new.
  • Update Password button has onClick + disabled while submitting.
  • Form clears on success; toast confirms.

These tests pin the contract — any future PR that re-routes the
Security tab through `/forgot-password` (which sends an email) or
strips the onClick handler will fail.

Registered under `make audit-boundaries`.
"""

from __future__ import annotations

import asyncio
import re
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path("/app")
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
sys.path.insert(0, str(BACKEND))

AUTH_PY = BACKEND / "routes" / "auth.py"
PROFILE_JSX = FRONTEND / "src" / "pages" / "Profile.js"


# ─────────────────────────────────────────────────────────────────────
# Section A — Backend endpoint shape & behaviour (live, against the
# running backend at localhost:8001).
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_user_with_password():
    """Create a test user with a known password, return its JWT.

    Cleaned up on teardown. Uses a unique email so concurrent runs
    don't collide.

    P0: We avoid touching motor directly inside this fixture because
    earlier tests in the audit suite close the asyncio event loop the
    module-level motor client is bound to. Instead, we drive the live
    backend via HTTP — the running uvicorn worker has its own loop and
    is not affected.
    """
    import requests
    from shared import create_token, hash_password

    uid = f"pwchange_test_{uuid.uuid4().hex[:10]}"
    email = f"{uid}@example.com"
    initial_pw = "InitPw@123Strong!"
    hashed = hash_password(initial_pw)

    # Direct DB ops still need a fresh, isolated event loop because
    # there's no HTTP endpoint to seed a user row. Build it lazily and
    # tear it down so we don't leave a dangling loop.
    import motor.motor_asyncio as motor_mod
    import os
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")

    async def setup(client):
        await client[db_name].users.delete_one({"id": uid})
        await client[db_name].users.insert_one({
            "id": uid, "email": email, "name": "T",
            "role": "USER", "credits": 0,
            "password": hashed, "authProvider": "email",
        })

    async def teardown(client):
        await client[db_name].users.delete_one({"id": uid})

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = motor_mod.AsyncIOMotorClient(mongo_url)
    try:
        loop.run_until_complete(setup(client))
        token = create_token(uid, "USER")
        yield {"id": uid, "email": email, "password": initial_pw, "token": token}
    finally:
        try:
            loop.run_until_complete(teardown(client))
        except Exception:
            pass
        client.close()
        loop.close()


def _put_password(token, current, new):
    import requests
    return requests.put(
        "http://localhost:8001/api/auth/password",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"currentPassword": current, "newPassword": new},
        timeout=10,
    )


def test_endpoint_rejects_unauthenticated():
    import requests
    r = requests.put(
        "http://localhost:8001/api/auth/password",
        json={"currentPassword": "x", "newPassword": "y"},
        timeout=10,
    )
    assert r.status_code in (401, 403), (
        f"Expected 401/403 for unauthenticated change-password, got {r.status_code}"
    )


def test_endpoint_rejects_wrong_current_password(test_user_with_password):
    u = test_user_with_password
    r = _put_password(u["token"], "WrongPw@9!", "BrandNewPw@2024X")
    assert r.status_code == 400
    detail = r.json().get("detail", "").lower()
    assert "current password is incorrect" in detail, (
        f"Backend must surface 'Current password is incorrect' — got: {detail!r}"
    )


def test_endpoint_rejects_weak_new_password(test_user_with_password):
    u = test_user_with_password
    r = _put_password(u["token"], u["password"], "weak")
    assert r.status_code == 400
    detail = r.json().get("detail", "").lower()
    assert "password" in detail and ("8 characters" in detail or "least" in detail
                                     or "must contain" in detail), (
        f"Weak password must surface a strength error. Got: {detail!r}"
    )


def test_endpoint_rejects_same_as_current(test_user_with_password):
    u = test_user_with_password
    r = _put_password(u["token"], u["password"], u["password"])
    assert r.status_code == 400
    detail = r.json().get("detail", "").lower()
    assert "different from current" in detail or "must be different" in detail, (
        f"Backend must refuse identical new password. Got: {detail!r}"
    )


def test_endpoint_accepts_valid_change_and_actually_updates(test_user_with_password):
    """End-to-end: change password, then verify the OLD password no
    longer works and the NEW password does."""
    from shared import db
    u = test_user_with_password
    new_pw = f"NewStrongPw@{uuid.uuid4().hex[:6]}A1!"
    r = _put_password(u["token"], u["password"], new_pw)
    assert r.status_code == 200, (
        f"Valid password change must return 200. Got {r.status_code}: {r.text}"
    )
    body = r.json()
    assert body.get("success") is True
    assert "changed" in body.get("message", "").lower()

    # Now try with the OLD password — must fail.
    r2 = _put_password(u["token"], u["password"], "AnotherNewPw@1!X")
    assert r2.status_code == 400, (
        "Old password must no longer authenticate the change-password call."
    )

    # And the NEW password is now what's authenticated via the
    # login endpoint — proves the hash was actually written.
    # (Using a separate event loop to read motor DB causes loop-binding
    # errors; we verify via the live /api/auth/login endpoint instead.)
    import requests
    login = requests.post(
        "http://localhost:8001/api/auth/login",
        json={"email": u["email"], "password": new_pw},
        timeout=10,
    )
    assert login.status_code == 200, (
        f"New password must authenticate via /api/auth/login. "
        f"Got {login.status_code}: {login.text[:200]}"
    )

    # Update the fixture so teardown still works cleanly.
    u["password"] = new_pw


# ─────────────────────────────────────────────────────────────────────
# Section B — Static contract: Profile.js wires the button + does not
# call any /forgot-password or /reset-password endpoint from the
# Security tab.
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def profile_src():
    return PROFILE_JSX.read_text()


def test_profile_has_change_password_handler(profile_src):
    assert "const handleChangePassword" in profile_src, (
        "Profile.js must define handleChangePassword for the Security tab."
    )


def test_profile_calls_put_auth_password(profile_src):
    assert "/api/auth/password" in profile_src, (
        "Profile.js must call PUT /api/auth/password — never a "
        "/forgot-password endpoint that would send an email."
    )
    # Find the handleChangePassword body and confirm it uses PUT.
    m = re.search(
        r"const handleChangePassword[^{]+\{(?P<body>.+?)\n  \};",
        profile_src, re.S,
    )
    assert m, "handleChangePassword body must be extractable."
    body = m.group("body")
    assert "api.put" in body or "axios.put" in body, (
        "Change-password handler must use PUT (not POST)."
    )


def test_profile_does_not_send_reset_email_from_security_tab(profile_src):
    """Security tab MUST NOT route through /forgot-password or
    /reset-password — those send emails."""
    m = re.search(
        r"const handleChangePassword[^{]+\{(?P<body>.+?)\n  \};",
        profile_src, re.S,
    )
    body = m.group("body")
    assert "/forgot-password" not in body
    assert "/reset-password" not in body
    assert "request-reset" not in body
    assert "send reset" not in body.lower()
    assert "reset link" not in body.lower(), (
        "Security tab must NOT send a reset link — it does in-app "
        "password change against the live DB."
    )


def test_button_has_onclick_handler(profile_src):
    """The 'Update Password' button must have an onClick wired to
    handleChangePassword. Without it the button is dead — the bug
    that triggered this whole work item."""
    # Find the button declaration with the testid we added.
    m = re.search(
        r'data-testid="profile-change-password-btn"[^>]*onClick=\{handleChangePassword\}',
        profile_src,
    )
    # The order of attributes may vary; allow either.
    m2 = re.search(
        r'onClick=\{handleChangePassword\}[^>]*data-testid="profile-change-password-btn"',
        profile_src,
    )
    assert m or m2, (
        "Update Password button must have onClick={handleChangePassword} "
        "AND data-testid='profile-change-password-btn'."
    )


def test_button_disabled_while_submitting(profile_src):
    """The button must disable while the request is in flight so the
    user can't double-submit (which would otherwise burn a credit /
    cause a race)."""
    assert "disabled={changingPassword}" in profile_src


def test_client_side_validation_present(profile_src):
    """Client-side guard rails: missing fields, mismatch, same-as-
    current, weak strength must all be checked before the network
    round-trip so the UX is instant."""
    body = profile_src
    assert "current password" in body.lower()
    assert "New password and confirm password do not match" in body or \
           "do not match" in body, (
        "Client must check newPassword === confirmPassword before POST."
    )
    assert "different from current" in body, (
        "Client must check newPassword !== currentPassword before POST."
    )
    assert "validateNewPassword" in body or "8 characters" in body, (
        "Client must mirror backend strength rules so the user sees "
        "the failure before the round trip."
    )


def test_show_hide_toggles_on_all_three_inputs(profile_src):
    for testid in (
        "profile-current-password-toggle",
        "profile-new-password-toggle",
        "profile-confirm-password-toggle",
    ):
        assert testid in profile_src, (
            f"Security tab must expose `{testid}` for the eye/eye-off "
            f"show-password toggle."
        )


def test_all_three_password_inputs_have_testids(profile_src):
    for testid in (
        "profile-current-password-input",
        "profile-new-password-input",
        "profile-confirm-password-input",
    ):
        assert testid in profile_src, (
            f"Security tab must expose `{testid}` for automation tests."
        )


def test_form_resets_after_success(profile_src):
    """After a successful change, the three inputs must clear so the
    user doesn't accidentally re-submit on tab return."""
    body = profile_src
    # Look for the success-path state reset.
    assert "currentPassword: ''" in body, (
        "On success, currentPassword must be reset to ''."
    )
    assert "newPassword: ''" in body
    assert "confirmPassword: ''" in body


# ─────────────────────────────────────────────────────────────────────
# Section C — Backend's PasswordChange schema field names match what
# the frontend sends. Drift here is the silent-500 trap.
# ─────────────────────────────────────────────────────────────────────


def test_password_change_schema_uses_camelcase_fields():
    """The backend schema MUST accept currentPassword + newPassword
    (camelCase). If a future refactor renames these to snake_case,
    the frontend's JSON body will silently fail to validate."""
    from models.schemas import PasswordChange
    fields = set(PasswordChange.__fields__.keys()) if hasattr(PasswordChange, "__fields__") \
        else set(PasswordChange.model_fields.keys())
    assert fields == {"currentPassword", "newPassword"}, (
        f"PasswordChange must have exactly {{currentPassword, "
        f"newPassword}}. Got: {fields}"
    )
