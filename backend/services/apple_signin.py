"""Apple Sign-In (native iOS) identity-token verification.

Apple App Store Guideline 4.8.0 mandates that any app offering a third-party
SSO (Google) must also offer Sign in with Apple. The native iOS app obtains
an `identity_token` JWT via `ASAuthorizationController` and POSTs it to
`/api/auth/apple-signin`. This module is the verification layer.

Verification steps (all mandatory):
  1. Fetch + cache Apple's JWKS from https://appleid.apple.com/auth/keys
     (PyJWKClient handles network + key selection + in-memory caching).
  2. Pick the JWK whose `kid` matches the token header.
  3. Verify the RS256 signature with the matched RSA public key.
  4. Validate `iss == https://appleid.apple.com`, `aud == <bundle id>`,
     and `exp` strictly in the future. All four claims are *required*.
  5. Return the decoded claims dict on success.

Failures raise `AppleIdentityTokenError` with a short, log-safe message
so the FastAPI route can map every failure mode to HTTP 401 uniformly.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict

import jwt
from jwt import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
    PyJWKClient,
    PyJWKClientError,
)

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"

# Audience = the iOS bundle identifier registered in App Store Connect.
# Overridable via env so staging / future bundles can be supported
# without a code change.
APPLE_AUDIENCE = os.environ.get("APPLE_BUNDLE_ID", "com.visionarysuite.app")

# PyJWKClient already keeps the fetched JWKS in-process. We share a
# single instance across requests so the cache is hit; PyJWKClient is
# documented as thread-safe for reads.
_jwk_client_lock = threading.Lock()
_jwk_client: PyJWKClient | None = None


class AppleIdentityTokenError(Exception):
    """Raised when an Apple identity token fails any verification step."""


def _get_jwk_client() -> PyJWKClient:
    """Lazy + thread-safe singleton PyJWKClient pointed at Apple's JWKS.

    `cache_keys=True` enables in-memory caching of fetched keys for the
    process lifetime; PyJWKClient transparently refreshes when a kid
    is missed, which is exactly the behavior Apple's key rotation
    requires.
    """
    global _jwk_client
    if _jwk_client is None:
        with _jwk_client_lock:
            if _jwk_client is None:
                _jwk_client = PyJWKClient(APPLE_JWKS_URL, cache_keys=True)
    return _jwk_client


def verify_apple_identity_token(identity_token: str) -> Dict[str, Any]:
    """Verify an Apple-signed `identity_token` and return its claims.

    Raises `AppleIdentityTokenError` on any failure (bad signature,
    missing/wrong issuer, missing/wrong audience, expired, malformed,
    JWKS retrieval failure). The route handler converts that into
    HTTP 401.
    """
    if not identity_token or not isinstance(identity_token, str):
        raise AppleIdentityTokenError("Missing or invalid identity_token")

    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(identity_token).key
    except PyJWKClientError as exc:
        raise AppleIdentityTokenError(f"Unable to resolve Apple signing key: {exc}") from exc
    except InvalidTokenError as exc:
        # PyJWKClient raises this when the token header cannot be parsed.
        raise AppleIdentityTokenError("Malformed Apple identity token") from exc

    try:
        claims: Dict[str, Any] = jwt.decode(
            identity_token,
            signing_key,
            algorithms=["RS256"],
            audience=APPLE_AUDIENCE,
            issuer=APPLE_ISSUER,
            options={
                "require": ["iss", "aud", "exp", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
    except ExpiredSignatureError as exc:
        raise AppleIdentityTokenError("Apple identity token expired") from exc
    except InvalidIssuerError as exc:
        raise AppleIdentityTokenError("Invalid Apple token issuer") from exc
    except InvalidAudienceError as exc:
        raise AppleIdentityTokenError("Invalid Apple token audience") from exc
    except InvalidTokenError as exc:
        raise AppleIdentityTokenError(f"Invalid Apple identity token: {exc}") from exc

    # Defense in depth — PyJWT already enforces verify_exp, but a
    # belt-and-braces explicit check guards against future option
    # tweaks accidentally weakening this invariant.
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or exp <= datetime.now(timezone.utc).timestamp():
        raise AppleIdentityTokenError("Apple identity token expired")

    if not claims.get("sub"):
        raise AppleIdentityTokenError("Apple identity token missing sub claim")

    return claims
