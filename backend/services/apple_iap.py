"""Apple IAP verification service.

Wraps Apple's official `app-store-server-library` to:
  1. Verify + decode a StoreKit 2 `jwsRepresentation` (client-side purchase)
  2. Verify + decode an App Store Server Notification V2 `signedPayload`
     (renewals / refunds / cancellations)

The library handles JWS signature verification, X.509 certificate-chain
validation against Apple's bundled root CAs, and payload decoding into
strongly-typed models. This module exposes two thin, idempotent helpers
plus the two product-mapping tables the /api/iap/apple/verify and
/api/iap/apple/webhook routes rely on.

Credentials come from env vars:
  APPSTORE_ISSUER_ID      — from App Store Connect → Users and Access → Integrations
  APPSTORE_KEY_ID         — the key ID of the In-App Purchase key (.p8)
  APPSTORE_PRIVATE_KEY    — the FULL PEM contents of the .p8 file (with headers)
  APPSTORE_BUNDLE_ID      — defaults to com.visionarysuite.app
  APPSTORE_ENVIRONMENT    — 'production' or 'sandbox' (auto-detected per transaction too)
  APPSTORE_APP_APPLE_ID   — numeric App Store ID (required in production; optional in sandbox)

The service is lazy — it does not fail at import time if creds are
absent. The route calls `get_apple_iap_service()` which raises a clean
HTTPException if the env is not configured. This keeps preview / CI
runs healthy even before the App Store Connect banking is approved.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Product catalogue (locked in with iOS storefront config) ─────────────────

# Consumable credit packs — grant a fixed amount of credits per successful
# transaction, never expire, no auto-renew.
CONSUMABLE_CREDIT_MAP: dict[str, int] = {
    "com.visionarysuite.credits.60": 60,
    "com.visionarysuite.credits.150": 150,
    "com.visionarysuite.credits.400": 400,
    "com.visionarysuite.credits.800": 800,
}

# Auto-renewing subscriptions — activate premium tier + grant a period
# credit allowance. Credits stack (award_credits is additive) so a
# renewal grants the same allowance again.
SUBSCRIPTION_MAP: dict[str, dict[str, Any]] = {
    "com.visionarysuite.sub.weekly":    {"credits": 40,   "tier": "weekly"},
    "com.visionarysuite.sub.monthly":   {"credits": 200,  "tier": "monthly"},
    "com.visionarysuite.sub.quarterly": {"credits": 750,  "tier": "quarterly"},
    "com.visionarysuite.sub.yearly":    {"credits": 3000, "tier": "yearly"},
}

# ── Apple root certs (bundled) ───────────────────────────────────────────────

_CERT_DIR = Path(__file__).parent / "apple_certificates"
_CERT_FILES = (
    "AppleComputerRootCertificate.cer",
    "AppleIncRootCertificate.cer",
    "AppleRootCA-G2.cer",
    "AppleRootCA-G3.cer",
)


def _load_root_certificates() -> list[bytes]:
    certs: list[bytes] = []
    for name in _CERT_FILES:
        path = _CERT_DIR / name
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Apple root certificate {path}. Bundle these DER "
                f".cer files under services/apple_certificates/."
            )
        certs.append(path.read_bytes())
    return certs


# ── Service ──────────────────────────────────────────────────────────────────

class AppleIAPNotConfigured(RuntimeError):
    """Raised when Apple IAP env vars are unset (soft failure — the route
    returns HTTP 503 instead of crashing on import)."""


class AppleIAPVerificationError(RuntimeError):
    """Raised when a JWS payload fails signature / claim verification."""


class AppleIAPService:
    """Thin wrapper around SignedDataVerifier + AppStoreServerAPIClient.

    Instances are cheap to construct once and reused by the route via
    the module-level `get_apple_iap_service()` singleton.
    """

    def __init__(
        self,
        issuer_id: str,
        key_id: str,
        private_key_pem: str,
        bundle_id: str,
        environment: str,
        app_apple_id: Optional[int] = None,
    ):
        # Import inside __init__ so a missing library doesn't break the
        # entire backend on boot (the import itself does happen at module
        # load; but any surface error message ends up localized here).
        from appstoreserverlibrary.api_client import AppStoreServerAPIClient
        from appstoreserverlibrary.models.Environment import Environment
        from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier

        env_str = (environment or "").lower().strip()
        env_enum = Environment.PRODUCTION if env_str == "production" else Environment.SANDBOX

        # AppStoreServerAPIClient expects the PEM as *bytes*.
        self._api_client = AppStoreServerAPIClient(
            signing_key=private_key_pem.encode("utf-8"),
            key_id=key_id,
            issuer_id=issuer_id,
            bundle_id=bundle_id,
            environment=env_enum,
        )

        self._verifier = SignedDataVerifier(
            root_certificates=_load_root_certificates(),
            enable_online_checks=False,  # offline OCSP/CRL — no external hop per request
            environment=env_enum,
            bundle_id=bundle_id,
            app_apple_id=app_apple_id,
        )
        self.environment = env_enum
        self.bundle_id = bundle_id

    def verify_transaction(self, jws_representation: str):
        """Verify a StoreKit 2 signed transaction and return the decoded payload.

        Raises AppleIAPVerificationError on any failure — the route
        catches this and returns HTTP 400.
        """
        from appstoreserverlibrary.signed_data_verifier import VerificationException
        try:
            return self._verifier.verify_and_decode_signed_transaction(jws_representation)
        except VerificationException as exc:
            raise AppleIAPVerificationError(f"Invalid Apple transaction JWS: {exc}") from exc

    def verify_notification(self, signed_payload: str):
        """Verify an App Store Server Notification V2 signedPayload."""
        from appstoreserverlibrary.signed_data_verifier import VerificationException
        try:
            return self._verifier.verify_and_decode_notification(signed_payload)
        except VerificationException as exc:
            raise AppleIAPVerificationError(f"Invalid Apple notification: {exc}") from exc


# ── Singleton bootstrap ──────────────────────────────────────────────────────

_service_lock = threading.Lock()
_service_instance: Optional[AppleIAPService] = None


def _read_env_credentials() -> Optional[dict]:
    issuer = os.environ.get("APPSTORE_ISSUER_ID")
    key_id = os.environ.get("APPSTORE_KEY_ID")
    private_key = os.environ.get("APPSTORE_PRIVATE_KEY")
    bundle_id = os.environ.get("APPSTORE_BUNDLE_ID", "com.visionarysuite.app")
    environment = os.environ.get("APPSTORE_ENVIRONMENT", "production")
    app_apple_id_raw = os.environ.get("APPSTORE_APP_APPLE_ID")

    if not (issuer and key_id and private_key):
        return None

    # Support base64-encoded private key (safer round-trip through env).
    if private_key.strip().startswith("LS0t"):  # base64 of "---"
        import base64
        private_key = base64.b64decode(private_key).decode("utf-8")

    # Normalize any escaped-newline representations sometimes introduced
    # by env-var editors (e.g. `\n` literal in the value).
    if "\\n" in private_key and "\n" not in private_key:
        private_key = private_key.replace("\\n", "\n")

    try:
        app_apple_id = int(app_apple_id_raw) if app_apple_id_raw else None
    except ValueError:
        app_apple_id = None

    return {
        "issuer_id": issuer,
        "key_id": key_id,
        "private_key_pem": private_key,
        "bundle_id": bundle_id,
        "environment": environment,
        "app_apple_id": app_apple_id,
    }


def get_apple_iap_service() -> AppleIAPService:
    """Return the singleton service or raise AppleIAPNotConfigured."""
    global _service_instance
    if _service_instance is not None:
        return _service_instance
    with _service_lock:
        if _service_instance is not None:
            return _service_instance
        creds = _read_env_credentials()
        if not creds:
            raise AppleIAPNotConfigured(
                "Apple IAP not configured. Set APPSTORE_ISSUER_ID, "
                "APPSTORE_KEY_ID, APPSTORE_PRIVATE_KEY in the backend env."
            )
        _service_instance = AppleIAPService(**creds)
        logger.info(
            "Apple IAP service initialized (bundle=%s env=%s)",
            creds["bundle_id"], creds["environment"],
        )
        return _service_instance


def reset_apple_iap_service_for_tests() -> None:
    """Test-only — clear the singleton so each test can inject its own."""
    global _service_instance
    with _service_lock:
        _service_instance = None
