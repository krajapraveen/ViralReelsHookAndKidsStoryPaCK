"""P0 2026-06 — Sign in with Apple endpoint contract + verifier behavior.

Apple App Store rejected v1.0 of the iOS app under Guideline 4.8.0
because it offered Google Sign-In without Sign in with Apple. The
backend now exposes `POST /api/auth/apple-signin` which mirrors the
existing google-signin endpoint exactly (same JWT issuer, same
response shape).

This audit suite locks the contract:
  • The endpoint is registered with the right path + verb.
  • `identity_token` is required (FastAPI 422 on missing).
  • Verification short-circuits on bad/missing iss + aud + exp + sub.
  • A genuinely valid token (mocked Apple JWKS) returns
    `{token, user}` with the same shape as google-signin.
  • The first-party JWT is issued via `create_token` so it shares
    the secret + payload shape with the google-signin path.

The test signs synthetic tokens with a locally-generated RSA key
and patches `services.apple_signin._jwk_client` to return that key.
Apple's JWKS is never contacted. All claim-validation logic still
runs against PyJWT's real verification path.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

# Make the backend importable when this file is collected from /app.
BACKEND_ROOT = Path("/app/backend")
sys.path.insert(0, str(BACKEND_ROOT))


# ── 1. Source-level contract pins ───────────────────────────────────────────

AUTH_PY = BACKEND_ROOT / "routes/auth.py"
APPLE_SVC = BACKEND_ROOT / "services/apple_signin.py"


@pytest.fixture(scope="module")
def auth_src() -> str:
    return AUTH_PY.read_text()


@pytest.fixture(scope="module")
def apple_src() -> str:
    return APPLE_SVC.read_text()


def test_apple_signin_endpoint_registered(auth_src: str) -> None:
    assert '@router.post("/apple-signin")' in auth_src, (
        "POST /api/auth/apple-signin must be registered to satisfy "
        "Apple Guideline 4.8.0."
    )
    assert "async def apple_signin(" in auth_src, (
        "Handler must be named `apple_signin`."
    )


def test_apple_signin_request_schema_required_identity_token(auth_src: str) -> None:
    assert "class AppleSignInRequest(BaseModel):" in auth_src
    assert "identity_token: str = Field(..., min_length=1" in auth_src, (
        "identity_token must be required (FastAPI must return 422 when "
        "the field is missing or empty)."
    )


def test_apple_signin_response_shape_matches_google(auth_src: str) -> None:
    """The response must be `{token, user}` with the same user fields
    as google-signin, so the iOS app's existing auth state machine
    works without changes."""
    # The handler returns the same dict shape twice (existing + new user).
    # We check that both branches return user objects with the same keys.
    apple_handler_start = auth_src.index("async def apple_signin(")
    apple_handler = auth_src[apple_handler_start : apple_handler_start + 8000]
    for key in ('"token"', '"id"', '"email"', '"name"', '"role"',
                '"credits"', '"picture"'):
        assert key in apple_handler, (
            f"Apple sign-in response must include the {key} field to "
            f"match the google-signin contract."
        )


def test_apple_signin_uses_create_token_same_issuer(auth_src: str) -> None:
    """First-party JWT must come from the shared `create_token` helper
    so it carries the same secret + payload shape as google-signin."""
    apple_handler_start = auth_src.index("async def apple_signin(")
    apple_handler = auth_src[apple_handler_start : apple_handler_start + 8000]
    assert "create_token(" in apple_handler, (
        "Apple endpoint must call the shared `create_token` so its "
        "tokens share the secret + algorithm + payload shape with "
        "google-signin."
    )


def test_apple_verifier_pins_apple_constants(apple_src: str) -> None:
    assert 'APPLE_ISSUER = "https://appleid.apple.com"' in apple_src
    assert 'APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"' in apple_src
    # Multi-audience support is mandatory — the iOS bundle ID AND the
    # web Services ID must both be accepted by a single backend endpoint.
    assert 'def _resolve_audiences()' in apple_src, (
        "Verifier must compute APPLE_AUDIENCES from the comma-separated "
        "APPLE_AUDIENCES env var so iOS (bundle ID) and web (Services ID) "
        "can coexist without code changes."
    )
    assert 'APPLE_AUDIENCES: list[str] = _resolve_audiences()' in apple_src
    # Back-compat: APPLE_BUNDLE_ID is still honored when APPLE_AUDIENCES
    # is unset.
    assert 'os.environ.get("APPLE_BUNDLE_ID", "com.visionarysuite.app")' in apple_src
    # PyJWT must be passed the full list, not a single audience.
    assert 'audience=APPLE_AUDIENCES' in apple_src, (
        "jwt.decode must receive APPLE_AUDIENCES (the list) so any of "
        "the registered audiences is accepted."
    )


def test_apple_verifier_uses_pyjwkclient_with_cache(apple_src: str) -> None:
    """JWKS must be fetched via PyJWKClient with in-memory caching."""
    assert "PyJWKClient" in apple_src
    assert "cache_keys=True" in apple_src, (
        "PyJWKClient must be configured with cache_keys=True to avoid "
        "hammering Apple's JWKS endpoint on every sign-in."
    )


def test_apple_verifier_requires_all_critical_claims(apple_src: str) -> None:
    """iss, aud, exp, sub must all be marked required so PyJWT rejects
    tokens missing any of them."""
    assert '"require": ["iss", "aud", "exp", "sub"]' in apple_src, (
        "PyJWT decode options must require iss/aud/exp/sub."
    )
    for verify_flag in ("verify_signature", "verify_exp", "verify_iss", "verify_aud"):
        assert f'"{verify_flag}": True' in apple_src, (
            f"PyJWT decode must explicitly set {verify_flag}=True."
        )


# ── 2. Behavioral tests against the verifier with a mocked JWKS ─────────────


@pytest.fixture(scope="module")
def rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return SimpleNamespace(private_key=private_key, public_key=public_key, pem_private=pem_private)


def _make_token(rsa_key_pair, *, iss: str, aud: str, exp_delta: int, sub: str = "001234.abcdef.0000",
                email: str | None = None, email_verified: bool | None = None) -> str:
    payload: Dict[str, Any] = {
        "iss": iss,
        "aud": aud,
        "sub": sub,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_delta,
    }
    if email is not None:
        payload["email"] = email
    if email_verified is not None:
        payload["email_verified"] = email_verified
    return jwt.encode(
        payload, rsa_key_pair.pem_private, algorithm="RS256",
        headers={"kid": "test-kid"},
    )


class _FakeJWK:
    def __init__(self, public_key):
        self.key = public_key


class _FakeJWKClient:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):  # noqa: ARG002
        return _FakeJWK(self._public_key)


@pytest.fixture
def patched_jwk_client(rsa_key_pair):
    """Replace the singleton PyJWKClient with one that returns our test key."""
    from services import apple_signin

    fake = _FakeJWKClient(rsa_key_pair.public_key)
    original = apple_signin._jwk_client
    apple_signin._jwk_client = fake
    try:
        yield fake
    finally:
        apple_signin._jwk_client = original


def test_verifier_accepts_valid_token(rsa_key_pair, patched_jwk_client):
    from services.apple_signin import APPLE_AUDIENCE, verify_apple_identity_token

    token = _make_token(
        rsa_key_pair, iss="https://appleid.apple.com", aud=APPLE_AUDIENCE,
        exp_delta=600, email="reviewer@privaterelay.appleid.com", email_verified=True,
    )
    claims = verify_apple_identity_token(token)
    assert claims["sub"] == "001234.abcdef.0000"
    assert claims["email"] == "reviewer@privaterelay.appleid.com"


def test_verifier_rejects_wrong_issuer(rsa_key_pair, patched_jwk_client):
    from services.apple_signin import (
        APPLE_AUDIENCE, AppleIdentityTokenError, verify_apple_identity_token,
    )

    token = _make_token(
        rsa_key_pair, iss="https://evil.example.com", aud=APPLE_AUDIENCE,
        exp_delta=600,
    )
    with pytest.raises(AppleIdentityTokenError, match="issuer"):
        verify_apple_identity_token(token)


def test_verifier_rejects_wrong_audience(rsa_key_pair, patched_jwk_client):
    from services.apple_signin import AppleIdentityTokenError, verify_apple_identity_token

    token = _make_token(
        rsa_key_pair, iss="https://appleid.apple.com", aud="com.someone.else.app",
        exp_delta=600,
    )
    with pytest.raises(AppleIdentityTokenError, match="audience"):
        verify_apple_identity_token(token)


def test_verifier_rejects_expired_token(rsa_key_pair, patched_jwk_client):
    from services.apple_signin import (
        APPLE_AUDIENCE, AppleIdentityTokenError, verify_apple_identity_token,
    )

    token = _make_token(
        rsa_key_pair, iss="https://appleid.apple.com", aud=APPLE_AUDIENCE,
        exp_delta=-60,
    )
    with pytest.raises(AppleIdentityTokenError, match="expired"):
        verify_apple_identity_token(token)


def test_verifier_rejects_malformed_token(patched_jwk_client):
    from services.apple_signin import AppleIdentityTokenError, verify_apple_identity_token

    with pytest.raises(AppleIdentityTokenError):
        verify_apple_identity_token("definitely-not-a-jwt")


def test_verifier_rejects_empty_token(patched_jwk_client):
    from services.apple_signin import AppleIdentityTokenError, verify_apple_identity_token

    with pytest.raises(AppleIdentityTokenError, match="Missing"):
        verify_apple_identity_token("")


# ── 3. End-to-end FastAPI route — valid token → {token, user} ────────────────


@pytest.fixture
def app_client(rsa_key_pair):
    """TestClient with a mocked Mongo so the endpoint can hit the DB."""
    from server import app
    from services import apple_signin

    # Patch the JWKS singleton to return our local public key.
    original = apple_signin._jwk_client
    apple_signin._jwk_client = _FakeJWKClient(rsa_key_pair.public_key)

    # Mock the db.users + db.credit_ledger operations to in-memory state.
    users_state: list[dict] = []

    async def fake_find_one(query, projection=None):
        for u in users_state:
            if all(u.get(k) == v for k, v in query.items() if "$" not in str(k)):
                return {k: v for k, v in u.items() if k != "_id"}
        # Handle $or query (email OR appleSub) — only used for email lookup
        if isinstance(query, dict) and "$or" in query:
            for cond in query["$or"]:
                for u in users_state:
                    if all(u.get(k) == v for k, v in cond.items()):
                        return {k: v for k, v in u.items() if k != "_id"}
        return None

    async def fake_insert_one(doc):
        users_state.append(doc)
        return SimpleNamespace(inserted_id="fake-id")

    async def fake_update_one(query, update):
        for u in users_state:
            if all(u.get(k) == v for k, v in query.items()):
                u.update(update.get("$set", {}))
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)

    async def fake_login_activity(**kwargs):
        return None

    with (
        patch("routes.auth.db") as mock_db,
        patch("routes.login_activity.log_login_activity", new=fake_login_activity),
    ):
        mock_db.users.find_one = AsyncMock(side_effect=fake_find_one)
        mock_db.users.insert_one = AsyncMock(side_effect=fake_insert_one)
        mock_db.users.update_one = AsyncMock(side_effect=fake_update_one)
        mock_db.credit_ledger.insert_one = AsyncMock(side_effect=fake_insert_one)

        client = TestClient(app)
        try:
            yield client, users_state
        finally:
            apple_signin._jwk_client = original


def test_route_returns_422_when_identity_token_missing(app_client):
    client, _ = app_client
    resp = client.post("/api/auth/apple-signin", json={})
    assert resp.status_code == 422, (
        f"Missing identity_token must return 422; got {resp.status_code} {resp.text}"
    )


def test_route_returns_401_on_malformed_token(app_client):
    client, _ = app_client
    resp = client.post("/api/auth/apple-signin", json={"identity_token": "not-a-jwt"})
    assert resp.status_code == 401, (
        f"Malformed identity_token must return 401; got {resp.status_code} {resp.text}"
    )


def test_route_returns_401_on_wrong_audience(app_client, rsa_key_pair):
    client, _ = app_client
    bad_token = _make_token(
        rsa_key_pair, iss="https://appleid.apple.com", aud="com.someone.else.app",
        exp_delta=600,
    )
    resp = client.post("/api/auth/apple-signin", json={"identity_token": bad_token})
    assert resp.status_code == 401, (
        f"Wrong audience must return 401; got {resp.status_code} {resp.text}"
    )
    assert "audience" in resp.json()["detail"].lower()


def test_route_returns_200_and_token_for_valid_apple_token(app_client, rsa_key_pair):
    client, _users_state = app_client
    from services.apple_signin import APPLE_AUDIENCE
    token = _make_token(
        rsa_key_pair, iss="https://appleid.apple.com", aud=APPLE_AUDIENCE,
        exp_delta=600, sub="001999.aaaa.0000",
        email="newreviewer@privaterelay.appleid.com", email_verified=True,
    )
    resp = client.post(
        "/api/auth/apple-signin",
        json={
            "identity_token": token,
            "full_name": "Apple Reviewer",
            "email": "newreviewer@privaterelay.appleid.com",
        },
    )
    assert resp.status_code == 200, (
        f"Valid Apple token must return 200; got {resp.status_code} {resp.text}"
    )
    body = resp.json()
    assert set(body.keys()) == {"token", "user"}, (
        f"Response must be exactly {{token, user}}; got {set(body.keys())}"
    )
    assert isinstance(body["token"], str) and len(body["token"]) > 20
    for k in ("id", "email", "name", "role", "credits", "picture"):
        assert k in body["user"], f"user object missing `{k}`"
    assert body["user"]["email"] == "newreviewer@privaterelay.appleid.com"
    assert body["user"]["role"] == "user"


# ── 4. Multi-audience web-Services-ID behavior (Login + Signup web pages) ────


def test_verifier_accepts_any_configured_audience(rsa_key_pair, patched_jwk_client, monkeypatch):
    """The verifier must accept a token whose `aud` matches ANY of the
    audiences in APPLE_AUDIENCES — not just the first. This is the
    invariant the web Sign in with Apple flow depends on (the iOS app
    sends bundle ID, the web sends Services ID, same backend endpoint
    services both)."""
    from services import apple_signin

    # Patch in a multi-audience config the way prod deployment will
    # set it: bundle ID (iOS) + Services ID (web).
    monkeypatch.setattr(
        apple_signin, "APPLE_AUDIENCES",
        ["com.visionarysuite.app", "com.visionarysuite.web"],
    )

    # Token signed for the WEB Services ID — must verify.
    web_token = _make_token(
        rsa_key_pair, iss="https://appleid.apple.com",
        aud="com.visionarysuite.web", exp_delta=600,
        sub="001234.webuser.0001",
    )
    claims = apple_signin.verify_apple_identity_token(web_token)
    assert claims["aud"] == "com.visionarysuite.web"

    # Token signed for the iOS bundle ID on the same endpoint — must verify.
    ios_token = _make_token(
        rsa_key_pair, iss="https://appleid.apple.com",
        aud="com.visionarysuite.app", exp_delta=600,
        sub="001234.iosuser.0001",
    )
    claims_ios = apple_signin.verify_apple_identity_token(ios_token)
    assert claims_ios["aud"] == "com.visionarysuite.app"


def test_verifier_rejects_audience_not_in_list(rsa_key_pair, patched_jwk_client, monkeypatch):
    from services import apple_signin

    monkeypatch.setattr(
        apple_signin, "APPLE_AUDIENCES",
        ["com.visionarysuite.app", "com.visionarysuite.web"],
    )

    bad = _make_token(
        rsa_key_pair, iss="https://appleid.apple.com",
        aud="com.malicious.other", exp_delta=600,
    )
    with pytest.raises(apple_signin.AppleIdentityTokenError, match="audience"):
        apple_signin.verify_apple_identity_token(bad)


# ── 5. Login + Signup web pages render the Apple button ─────────────────────

LOGIN_PAGE = BACKEND_ROOT.parent / "frontend/src/pages/Login.js"
SIGNUP_PAGE = BACKEND_ROOT.parent / "frontend/src/pages/Signup.js"
APPLE_HOOK = BACKEND_ROOT.parent / "frontend/src/hooks/useAppleSignIn.js"
APPLE_DOMAIN_ASSOC = BACKEND_ROOT.parent / "frontend/public/.well-known/apple-developer-domain-association.txt"


@pytest.fixture(scope="module")
def login_src() -> str:
    return LOGIN_PAGE.read_text()


@pytest.fixture(scope="module")
def signup_src() -> str:
    return SIGNUP_PAGE.read_text()


@pytest.fixture(scope="module")
def apple_hook_src() -> str:
    return APPLE_HOOK.read_text()


def test_login_page_imports_apple_hook(login_src: str) -> None:
    assert "import { useAppleSignIn } from '../hooks/useAppleSignIn';" in login_src, (
        "Login.js must import the useAppleSignIn hook so the Continue "
        "with Apple button can be rendered."
    )


def test_login_page_renders_apple_button(login_src: str) -> None:
    assert 'data-testid="apple-signin-btn"' in login_src
    assert 'data-testid="apple-signin-popup-btn"' in login_src
    assert "Continue with Apple" in login_src, (
        "Login.js must show the official 'Continue with Apple' label."
    )
    assert "apple.configured" in login_src, (
        "Login.js must gate the Apple button on the hook's `configured` "
        "flag so the button is hidden when REACT_APP_APPLE_SERVICES_ID "
        "is not set (e.g. on staging before the Services ID is created)."
    )


def test_login_page_posts_identity_token_to_backend(login_src: str) -> None:
    assert "/api/auth/apple-signin" in login_src, (
        "Login.js must POST the identity_token to /api/auth/apple-signin."
    )
    # The same JWT-storage path must be used as Google so user.id, token,
    # and the post-login return-path handling are identical.
    apple_handler_start = login_src.index("handleAppleSuccess")
    apple_handler = login_src[apple_handler_start : apple_handler_start + 4000]
    assert "localStorage.setItem('token'" in apple_handler
    assert "safeRedirectPath" in apple_handler


def test_signup_page_imports_apple_hook(signup_src: str) -> None:
    assert "import { useAppleSignIn } from '../hooks/useAppleSignIn';" in signup_src


def test_signup_page_renders_apple_button(signup_src: str) -> None:
    assert 'data-testid="apple-signup-btn"' in signup_src
    assert 'data-testid="apple-signup-popup-btn"' in signup_src
    assert "Continue with Apple" in signup_src
    assert "apple.configured" in signup_src


def test_signup_page_posts_identity_token_to_backend(signup_src: str) -> None:
    assert "/api/auth/apple-signin" in signup_src
    apple_handler_start = signup_src.index("handleAppleSuccess")
    apple_handler = signup_src[apple_handler_start : apple_handler_start + 4000]
    assert "localStorage.setItem('token'" in apple_handler


# ── 6. Apple hook + SDK loading invariants ──────────────────────────────────


def test_apple_hook_uses_official_apple_sdk(apple_hook_src: str) -> None:
    assert "appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js" in apple_hook_src, (
        "Hook must load the official Apple JS SDK URL."
    )


def test_apple_hook_uses_popup_mode(apple_hook_src: str) -> None:
    assert "usePopup: true" in apple_hook_src, (
        "Popup mode is required — redirect mode would need a backend "
        "callback route + open-redirect protection."
    )


def test_apple_hook_reads_services_id_from_env(apple_hook_src: str) -> None:
    assert "process.env.REACT_APP_APPLE_SERVICES_ID" in apple_hook_src
    assert "process.env.REACT_APP_APPLE_REDIRECT_URI" in apple_hook_src


def test_apple_hook_extracts_id_token_from_response(apple_hook_src: str) -> None:
    """Apple JS SDK returns `{ authorization: { id_token, code, state }, user? }`.
    The hook must extract id_token from that exact path."""
    assert "response?.authorization?.id_token" in apple_hook_src or \
           "response.authorization.id_token" in apple_hook_src, (
        "Hook must read id_token from response.authorization.id_token."
    )


# ── 7. Domain-association file is present + has actionable instructions ─────


def test_apple_domain_association_file_exists() -> None:
    assert APPLE_DOMAIN_ASSOC.exists(), (
        f"Apple requires the verification file at /.well-known/"
        f"apple-developer-domain-association.txt. Expected at "
        f"{APPLE_DOMAIN_ASSOC}."
    )


def test_apple_domain_association_file_has_placeholder_or_real_content() -> None:
    """The file must either be the placeholder waiting for content, OR
    the real Apple verification content. It must never be empty."""
    content = APPLE_DOMAIN_ASSOC.read_text()
    assert content.strip(), "Apple domain-association file must not be empty."

