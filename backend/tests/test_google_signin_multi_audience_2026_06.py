"""P0 2026-06 — Google Sign-In multi-audience validator.

Production incident:
  Mobile (iOS + Android) Google Sign-In failed with
  "Invalid Google credential: Token has wrong audience" because the
  backend validator only accepted tokens issued for the Web OAuth
  Client ID. Native mobile Client IDs issue tokens with their own
  `aud` claim, so a single-audience check rejected every mobile login.

Bug-class fix:
  • `_allowed_google_audiences()` returns the set of Client IDs the
    backend accepts: {Web, iOS, Android} for the Visionary Suite
    Global project (number 972517860807).
  • `id_token.verify_oauth2_token` is called WITHOUT the `audience`
    kwarg (library validates signature + issuer + expiry + nbf), then
    the manual `aud in allowed` check runs.
  • Downstream audience-equality gate also uses the allowed set so
    mobile tokens don't get rejected after the initial verify.
  • The auth-code (server-side exchange) flow continues to pass the
    Web Client ID directly to verify_oauth2_token — code exchange is
    web-only by design and the audience there is always Web.

These tests pin the contract — any future PR that drops a Client ID
from the set, re-introduces a single-audience equality check, or
passes the `audience=` arg back to verify_oauth2_token (which would
again reject mobile) will fail the audit.

Registered under `make audit-boundaries`.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path("/app")
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))

AUTH_PY = BACKEND / "routes" / "auth.py"


# ─────────────────────────────────────────────────────────────────────
# Section A — Allowed-audience set contains all three Client IDs.
# ─────────────────────────────────────────────────────────────────────


def test_allowed_audiences_includes_web_ios_android():
    from routes.auth import _allowed_google_audiences
    auds = _allowed_google_audiences()
    # The three Client IDs registered in Visionary Suite Global project.
    expected_ios = "972517860807-p850882qdt4qlpn7smv8e5id9mspdrmb.apps.googleusercontent.com"
    expected_android = "972517860807-qtp4vi1e7gp5rpqkr6sf94utla820ns4.apps.googleusercontent.com"
    assert expected_ios in auds, (
        "iOS Client ID must be in the allowed-audience set. Without it, "
        "iOS Google Sign-In re-breaks with 'Token has wrong audience'."
    )
    assert expected_android in auds, (
        "Android Client ID must be in the allowed-audience set. "
        "Same regression risk as iOS."
    )
    # Web Client ID comes from GOOGLE_CLIENT_ID env var — must be present
    # whenever the env is configured.
    from routes.auth import GOOGLE_CLIENT_ID
    if GOOGLE_CLIENT_ID:
        assert GOOGLE_CLIENT_ID in auds


def test_allowed_audiences_skips_unset_values():
    """If iOS / Android env vars are explicitly set to empty string,
    we should NOT include empty strings in the set (would let any
    aud-less token through)."""
    from routes import auth as auth_module
    orig_ios = auth_module.GOOGLE_IOS_CLIENT_ID
    orig_android = auth_module.GOOGLE_ANDROID_CLIENT_ID
    try:
        auth_module.GOOGLE_IOS_CLIENT_ID = ""
        auth_module.GOOGLE_ANDROID_CLIENT_ID = ""
        auds = auth_module._allowed_google_audiences()
        assert "" not in auds, (
            "Empty string must never appear in the allowed-audience "
            "set — that would weaken validation."
        )
    finally:
        auth_module.GOOGLE_IOS_CLIENT_ID = orig_ios
        auth_module.GOOGLE_ANDROID_CLIENT_ID = orig_android


def test_allowed_audiences_is_a_set_of_strings():
    from routes.auth import _allowed_google_audiences
    auds = _allowed_google_audiences()
    assert isinstance(auds, set)
    for a in auds:
        assert isinstance(a, str)
        assert a.endswith(".apps.googleusercontent.com"), (
            f"Allowed audience `{a}` does not look like a Google "
            f"Client ID — wrong env var wiring?"
        )


# ─────────────────────────────────────────────────────────────────────
# Section B — Static contract: verify_oauth2_token is called without
# the single-audience kwarg on the credential / tokeninfo paths.
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def google_signin_body():
    src = AUTH_PY.read_text()
    m = re.search(
        r"async def google_signin\([^)]*\)[^:]*:(?P<body>.+?)(?=\n@router\.|\n\nasync def |\n\ndef )",
        src, re.S,
    )
    assert m, "google_signin() must exist"
    return m.group("body")


def test_credential_flow_uses_no_audience_kwarg(google_signin_body):
    """Locate the credential-branch call to verify_oauth2_token and
    confirm it does NOT pass GOOGLE_CLIENT_ID as a positional audience.
    """
    # Find the elif data.credential branch.
    m = re.search(
        r"elif data\.credential:(?P<branch>.+?)(?=\n        else:|\n        elif )",
        google_signin_body, re.S,
    )
    assert m, "credential branch must exist"
    branch = m.group("branch")
    # The verify_oauth2_token call MUST pass exactly two args:
    # the token and the Request(). If a third positional arg is
    # present (the old GOOGLE_CLIENT_ID), mobile audiences will be
    # rejected by the library before our manual check runs.
    m2 = re.search(
        r"id_token\.verify_oauth2_token\(\s*(?P<args>[^)]+)\)",
        branch, re.S,
    )
    assert m2, "verify_oauth2_token call must exist in credential branch"
    args = m2.group("args")
    # Count top-level commas (very rough — splits across newlines).
    args_clean = re.sub(r"#[^\n]*", "", args)  # strip comments
    arg_count = len([a for a in re.split(r",\s*", args_clean.strip()) if a])
    assert arg_count == 2, (
        f"verify_oauth2_token in credential branch must take exactly 2 "
        f"args (token + Request). Got {arg_count}: {args_clean.strip()!r}. "
        f"Passing a 3rd positional `audience` arg silently re-introduces "
        f"the single-Client-ID bug that broke mobile sign-in."
    )


def test_credential_flow_manually_checks_allowed_audiences(google_signin_body):
    m = re.search(
        r"elif data\.credential:(?P<branch>.+?)(?=\n        else:|\n        elif )",
        google_signin_body, re.S,
    )
    branch = m.group("branch")
    assert "_allowed_google_audiences()" in branch, (
        "Credential branch must call _allowed_google_audiences() to "
        "validate the token's `aud` claim against the full Client ID set."
    )
    assert 'idinfo.get("aud")' in branch, (
        "Credential branch must compare idinfo['aud'] against the set."
    )


def test_tokeninfo_flow_uses_allowed_audiences(google_signin_body):
    """The access_token (implicit) flow hits Google's tokeninfo
    endpoint then must validate the returned `aud` against the
    multi-audience set — not just the Web Client ID."""
    # Find the if data.access_token: branch.
    m = re.search(
        r"if data\.access_token:(?P<branch>.+?)(?=\n        elif )",
        google_signin_body, re.S,
    )
    assert m, "access_token branch must exist"
    branch = m.group("branch")
    assert "_allowed_google_audiences()" in branch, (
        "Access-token branch must validate against the multi-audience "
        "set, otherwise mobile implicit-flow tokens still fail."
    )


def test_downstream_aud_check_uses_allowed_audiences(google_signin_body):
    """After verify_oauth2_token, a second `idinfo.get('aud') !=
    GOOGLE_CLIENT_ID` gate used to fire and would AGAIN reject mobile
    audiences even after the initial check passed. The downstream gate
    must use the allowed set too."""
    # Find the `if not data.access_token:` post-verify block.
    m = re.search(
        r"if not data\.access_token:(?P<block>.+?)# Extract user info",
        google_signin_body, re.S,
    )
    assert m, "post-verify user-info extraction block must exist"
    block = m.group("block")
    assert 'aud") != GOOGLE_CLIENT_ID' not in block, (
        "Downstream `aud != GOOGLE_CLIENT_ID` gate must NOT exist — "
        "it would reject mobile tokens after they passed the initial "
        "verify. Use _allowed_google_audiences() instead."
    )
    assert "_allowed_google_audiences()" in block, (
        "Downstream audience gate must reference the allowed set."
    )


# ─────────────────────────────────────────────────────────────────────
# Section C — Project number sanity: all three Client IDs share the
# same Google Cloud project number (972517860807). Catches typos /
# wrong-project copy-paste mistakes.
# ─────────────────────────────────────────────────────────────────────


def test_all_client_ids_share_same_project_number():
    from routes.auth import _allowed_google_audiences
    auds = _allowed_google_audiences()
    project_numbers = set()
    for a in auds:
        # Format: <project_number>-<random>.apps.googleusercontent.com
        m = re.match(r"^(\d+)-", a)
        assert m, f"Client ID {a!r} does not match Google's format"
        project_numbers.add(m.group(1))
    assert len(project_numbers) == 1, (
        f"All allowed Client IDs must belong to the same Google Cloud "
        f"project. Found: {project_numbers}. Mixed-project Client IDs "
        f"indicate a copy-paste error or a misconfigured env var."
    )
    # And specifically the Visionary Suite Global project.
    assert "972517860807" in project_numbers


# ─────────────────────────────────────────────────────────────────────
# Section D — Issuer check remains intact (don't accidentally weaken
# the rest of the validator while loosening audience).
# ─────────────────────────────────────────────────────────────────────


def test_issuer_check_still_enforced(google_signin_body):
    assert "accounts.google.com" in google_signin_body
    assert "Invalid token issuer" in google_signin_body, (
        "Issuer validation must still raise on bad issuer — "
        "loosening audience does NOT mean loosening issuer."
    )
