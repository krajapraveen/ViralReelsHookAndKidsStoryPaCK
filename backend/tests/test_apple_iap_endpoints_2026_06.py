"""P0 2026-06 — Apple In-App Purchase endpoints contract + business rules.

Two surfaces:
  POST /api/iap/apple/verify   — Bearer-JWT auth, StoreKit 2 receipts
  POST /api/iap/apple/webhook  — App Store Server Notifications V2, no auth

This audit locks:
  • Endpoint registration + auth guards + validation
  • Product catalogue (consumables + subscriptions) is EXACTLY the values
    the App Store storefront was configured with — a diff means someone
    would over- or under-grant credits
  • Idempotency: the credit-grant reference_id format is `apple_iap:<txId>`
    so `award_credits` + `deduct_credits` dedupe across replays
  • Bundle-ID mismatch, productId mismatch, unknown product all reject
  • Webhook signs must return 200 on unknown types (Apple 3-day retry
    storm avoidance) but reject genuinely bad JWS

Registered in `make audit-boundaries`.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path("/app/backend")
sys.path.insert(0, str(BACKEND_ROOT))

APPLE_IAP_PY = BACKEND_ROOT / "services/apple_iap.py"
ROUTE_PY = BACKEND_ROOT / "routes/iap_apple.py"


# ── 1. Product catalogue is byte-exact ──────────────────────────────────────


def test_consumable_credit_map_locked() -> None:
    from services.apple_iap import CONSUMABLE_CREDIT_MAP
    assert CONSUMABLE_CREDIT_MAP == {
        "com.visionarysuite.credits.60": 60,
        "com.visionarysuite.credits.150": 150,
        "com.visionarysuite.credits.400": 400,
        "com.visionarysuite.credits.800": 800,
    }, (
        "Consumable credit grant table drives revenue. A diff here means "
        "we grant a different amount than the App Store storefront charges."
    )


def test_subscription_map_locked() -> None:
    from services.apple_iap import SUBSCRIPTION_MAP
    assert SUBSCRIPTION_MAP == {
        "com.visionarysuite.sub.weekly":    {"credits": 40,   "tier": "weekly"},
        "com.visionarysuite.sub.monthly":   {"credits": 200,  "tier": "monthly"},
        "com.visionarysuite.sub.quarterly": {"credits": 750,  "tier": "quarterly"},
        "com.visionarysuite.sub.yearly":    {"credits": 3000, "tier": "yearly"},
    }


# ── 2. Endpoint + schema pins ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def route_src() -> str:
    return ROUTE_PY.read_text()


def test_verify_endpoint_registered(route_src: str) -> None:
    assert '@router.post("/verify", response_model=AppleVerifyResponse)' in route_src
    assert "async def verify_apple_iap(" in route_src


def test_webhook_endpoint_registered(route_src: str) -> None:
    assert '@router.post("/webhook")' in route_src
    assert "async def apple_iap_webhook(" in route_src


def test_verify_requires_bearer_auth(route_src: str) -> None:
    # Bearer-JWT auth is non-negotiable — the client identity determines
    # which user gets credits.
    assert "user: dict = Depends(get_current_user)" in route_src, (
        "POST /api/iap/apple/verify must be authenticated via the "
        "shared get_current_user dependency."
    )


def test_webhook_has_no_bearer_auth(route_src: str) -> None:
    """Apple calls the webhook — there is no Bearer token to check.
    Authenticity comes entirely from the signedPayload JWS verification."""
    webhook_start = route_src.index("async def apple_iap_webhook(")
    webhook_signature = route_src[webhook_start : route_src.index(":", webhook_start)]
    assert "Depends(get_current_user)" not in webhook_signature, (
        "The webhook must NOT require Bearer auth — Apple cannot send one."
    )


def test_verify_uses_verified_product_id_not_body(route_src: str) -> None:
    """The credit-grant decision MUST be based on the JWS-verified productId,
    never the body-supplied one. Body is only used to sanity-check for
    client-side bugs."""
    assert "verified_product_id = getattr(tx, \"product_id\", None) or \"\"" in route_src
    # Product lookup uses the verified id.
    assert "CONSUMABLE_CREDIT_MAP.get(verified_product_id)" in route_src
    assert "SUBSCRIPTION_MAP.get(verified_product_id)" in route_src
    # Body/JWS cross-check exists and rejects on mismatch.
    assert "productId does not match verified receipt" in route_src


def test_verify_enforces_bundle_id_guard(route_src: str) -> None:
    assert "Bundle ID mismatch" in route_src, (
        "Verify must reject any receipt whose bundle_id is not the "
        "configured APPSTORE_BUNDLE_ID (com.visionarysuite.app)."
    )


def test_verify_idempotency_reference_id_format(route_src: str) -> None:
    """award_credits uses reference_id=`apple_iap:<transactionId>` so
    replays don't grant twice. Any change to this format silently
    breaks idempotency across releases."""
    assert 'reference_id = f"apple_iap:{verified_tx_id}"' in route_src


def test_refund_uses_distinct_reference_id(route_src: str) -> None:
    """Refund deductions must NOT share the grant's reference_id — the
    ledger stores one row per grant AND one row per refund."""
    assert 'reference_id=f"apple_iap_refund:{verified_tx_id}"' in route_src


def test_verify_writes_iap_transactions_row(route_src: str) -> None:
    assert "db.iap_transactions.find_one" in route_src, (
        "Verify must probe db.iap_transactions by transactionId to detect "
        "already-processed receipts."
    )
    assert "db.iap_transactions.insert_one" in route_src


def test_webhook_always_200s_on_unknown_types(route_src: str) -> None:
    """Apple retries non-200 for 3 days. Unknown notification types must
    be acked, not rejected."""
    assert "Always 200 so Apple stops retrying" in route_src


def test_webhook_handles_expected_notification_types(route_src: str) -> None:
    for grant in ("SUBSCRIBED", "DID_RENEW"):
        assert grant in route_src
    for revoke in ("EXPIRED", "REFUND", "REVOKE"):
        assert revoke in route_src


# ── 3. Verifier service pins ────────────────────────────────────────────────


@pytest.fixture(scope="module")
def service_src() -> str:
    return APPLE_IAP_PY.read_text()


def test_service_uses_official_apple_library(service_src: str) -> None:
    assert "from appstoreserverlibrary.api_client import AppStoreServerAPIClient" in service_src
    assert "from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier" in service_src


def test_service_bundles_all_four_root_certs(service_src: str) -> None:
    assert '"AppleComputerRootCertificate.cer"' in service_src
    assert '"AppleIncRootCertificate.cer"' in service_src
    assert '"AppleRootCA-G2.cer"' in service_src
    assert '"AppleRootCA-G3.cer"' in service_src
    for name in ("AppleComputerRootCertificate.cer", "AppleIncRootCertificate.cer",
                 "AppleRootCA-G2.cer", "AppleRootCA-G3.cer"):
        cert_path = BACKEND_ROOT / "services" / "apple_certificates" / name
        assert cert_path.exists() and cert_path.stat().st_size > 300, (
            f"{name} must be a real DER root cert (>300 bytes). "
            f"Got size={cert_path.stat().st_size if cert_path.exists() else 'missing'}"
        )


def test_service_reads_all_five_env_vars(service_src: str) -> None:
    for env in ("APPSTORE_ISSUER_ID", "APPSTORE_KEY_ID", "APPSTORE_PRIVATE_KEY",
                "APPSTORE_BUNDLE_ID", "APPSTORE_ENVIRONMENT"):
        assert env in service_src, f"Service must honor {env} env var."
    assert 'os.environ.get("APPSTORE_BUNDLE_ID", "com.visionarysuite.app")' in service_src


def test_service_supports_base64_private_key(service_src: str) -> None:
    """The .p8 PEM can be base64-encoded in the env to avoid newline
    corruption during copy/paste through the deploy dashboard."""
    assert 'base64.b64decode' in service_src


def test_service_singleton_is_lazy(service_src: str) -> None:
    """Missing creds MUST NOT crash the backend on boot. The service is
    only instantiated on first use — the route surfaces a 503 with a
    clean message if env is unset."""
    assert "class AppleIAPNotConfigured(RuntimeError):" in service_src
    assert "def get_apple_iap_service() -> AppleIAPService:" in service_src


# ── 4. End-to-end route behavior with mocked verifier ───────────────────────


@pytest.fixture
def app_client_with_mocked_apple(monkeypatch):
    """TestClient with Apple verifier + Mongo mocked.

    Injects a fake service into the singleton so verify_transaction()
    returns a deterministic transaction payload for whichever product
    the test asks for.
    """
    from server import app
    from services import apple_iap
    from routes import iap_apple as iap_route

    # In-memory user + transactions state.
    users_state: dict = {}
    txns_state: list = []
    ledger_state: list = []

    async def fake_login_get_current_user(*a, **kw):
        return users_state["current"]

    async def fake_users_find_one(query, projection=None):
        u = users_state["current"]
        if not u:
            return None
        if "id" in query and query["id"] != u["id"]:
            return None
        return {k: v for k, v in u.items()}

    async def fake_users_find_one_and_update(query, update, projection=None, return_document=None):
        u = users_state["current"]
        inc = update.get("$inc", {})
        set_ = update.get("$set", {})
        for k, v in inc.items():
            u[k] = int(u.get(k, 0)) + int(v)
        u.update(set_)
        return {k: v for k, v in u.items()}

    async def fake_users_update_one(query, update):
        u = users_state["current"]
        u.update(update.get("$set", {}))
        return SimpleNamespace(matched_count=1, modified_count=1)

    async def fake_iap_txns_find_one(query, projection=None):
        for t in txns_state:
            if all(t.get(k) == v for k, v in query.items()):
                return t
        return None

    async def fake_iap_txns_insert_one(doc):
        txns_state.append(doc)
        return SimpleNamespace(inserted_id="fake")

    async def fake_iap_txns_update_one(query, update, upsert=False):
        for t in txns_state:
            if all(t.get(k) == v for k, v in query.items()):
                t.update(update.get("$set", {}))
                return SimpleNamespace(matched_count=1)
        if upsert:
            doc = dict(query)
            doc.update(update.get("$setOnInsert", {}))
            doc.update(update.get("$set", {}))
            txns_state.append(doc)
        return SimpleNamespace(matched_count=0, upserted_id="fake" if upsert else None)

    async def fake_ledger_find_one(query, projection=None):
        for row in ledger_state:
            if all(row.get(k) == v for k, v in query.items()):
                return row
        return None

    async def fake_ledger_insert_one(doc):
        ledger_state.append(doc)
        return SimpleNamespace(inserted_id="fake")

    def make_tx(product_id, tx_id, expires_ms=None, purchase_ms=None, bundle="com.visionarysuite.app"):
        return SimpleNamespace(
            product_id=product_id,
            transaction_id=tx_id,
            original_transaction_id=tx_id,
            bundle_id=bundle,
            environment=SimpleNamespace(value="Sandbox"),
            expires_date=expires_ms,
            purchase_date=purchase_ms or int(time.time() * 1000),
        )

    tx_by_jws: dict = {}

    class FakeService:
        bundle_id = "com.visionarysuite.app"
        environment = SimpleNamespace(value="Sandbox")

        def verify_transaction(self, jws):
            if jws not in tx_by_jws:
                from services.apple_iap import AppleIAPVerificationError
                raise AppleIAPVerificationError("unknown mock jws")
            return tx_by_jws[jws]

        def verify_notification(self, sp):
            # subclass override in webhook tests
            raise NotImplementedError

    fake_service = FakeService()
    apple_iap._service_instance = fake_service

    # Patch DB + auth.
    from shared import get_current_user
    app.dependency_overrides[get_current_user] = lambda: users_state["current"]

    with patch("routes.iap_apple.db") as mock_route_db, \
         patch("routes.iap_apple.get_credits_service") as mock_get_credits_svc:
        mock_route_db.users.find_one = AsyncMock(side_effect=fake_users_find_one)
        mock_route_db.users.update_one = AsyncMock(side_effect=fake_users_update_one)
        mock_route_db.iap_transactions.find_one = AsyncMock(side_effect=fake_iap_txns_find_one)
        mock_route_db.iap_transactions.insert_one = AsyncMock(side_effect=fake_iap_txns_insert_one)
        mock_route_db.iap_transactions.update_one = AsyncMock(side_effect=fake_iap_txns_update_one)

        from services.credits_service import CreditsService
        credits_svc = CreditsService(users=MagicMock(), ledger=MagicMock())
        credits_svc.users.find_one = AsyncMock(side_effect=fake_users_find_one)
        credits_svc.users.find_one_and_update = AsyncMock(side_effect=fake_users_find_one_and_update)
        credits_svc.ledger.find_one = AsyncMock(side_effect=fake_ledger_find_one)
        credits_svc.ledger.insert_one = AsyncMock(side_effect=fake_ledger_insert_one)
        mock_get_credits_svc.return_value = credits_svc

        client = TestClient(app)
        try:
            yield SimpleNamespace(
                client=client,
                users_state=users_state,
                txns_state=txns_state,
                ledger_state=ledger_state,
                tx_by_jws=tx_by_jws,
                make_tx=make_tx,
                FakeService=FakeService,
                fake_service=fake_service,
            )
        finally:
            app.dependency_overrides.clear()
            apple_iap._service_instance = None


def test_consumable_grants_correct_credits(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u1", "role": "user", "credits": 0}
    ctx.tx_by_jws["JWS_A_MOCK_STORE"] = ctx.make_tx("com.visionarysuite.credits.150", "tx-100")
    r = ctx.client.post("/api/iap/apple/verify", json={
        "productId": "com.visionarysuite.credits.150",
        "transactionId": "tx-100",
        "jwsRepresentation": "JWS_A_MOCK_STORE",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["isConsumable"] is True
    assert body["creditsGranted"] == 150
    assert body["totalCredits"] == 150
    assert body["transactionId"] == "tx-100"
    assert body["alreadyProcessed"] is False


def test_consumable_replay_is_idempotent(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u2", "role": "user", "credits": 0}
    ctx.tx_by_jws["JWS_B_MOCK_STORE"] = ctx.make_tx("com.visionarysuite.credits.60", "tx-200")
    body = {"productId": "com.visionarysuite.credits.60", "transactionId": "tx-200",
            "jwsRepresentation": "JWS_B_MOCK_STORE"}
    r1 = ctx.client.post("/api/iap/apple/verify", json=body)
    r2 = ctx.client.post("/api/iap/apple/verify", json=body)
    assert r1.status_code == r2.status_code == 200
    # Second call must not grant additional credits — award_credits is
    # dedupe'd on reference_id, iap_transactions row already exists.
    assert r2.json()["alreadyProcessed"] is True
    assert r2.json()["totalCredits"] == 60, (
        "Replayed verify must not double-grant."
    )


def test_subscription_activates_plan_and_grants_credits(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u3", "role": "user", "credits": 0}
    future_ms = int((time.time() + 30 * 86400) * 1000)
    ctx.tx_by_jws["JWS_M_MOCK_STORE"] = ctx.make_tx(
        "com.visionarysuite.sub.monthly", "sub-500", expires_ms=future_ms,
    )
    r = ctx.client.post("/api/iap/apple/verify", json={
        "productId": "com.visionarysuite.sub.monthly",
        "transactionId": "sub-500",
        "jwsRepresentation": "JWS_M_MOCK_STORE",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["isConsumable"] is False
    assert body["tier"] == "monthly"
    assert body["subscriptionActive"] is True
    assert body["creditsGranted"] == 200
    assert body["totalCredits"] == 200
    # User doc must be flipped to premium
    u = ctx.users_state["current"]
    assert u["plan_type"] == "monthly"
    assert u["subscription_status"] == "active"
    assert u["subscription_platform"] == "apple"


def test_unknown_product_rejected(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u4", "role": "user", "credits": 0}
    ctx.tx_by_jws["JWS_X_MOCK_STORE"] = ctx.make_tx("com.someone.else.product", "tx-999")
    r = ctx.client.post("/api/iap/apple/verify", json={
        "productId": "com.someone.else.product",
        "transactionId": "tx-999",
        "jwsRepresentation": "JWS_X_MOCK_STORE",
    })
    assert r.status_code == 400
    assert "Unknown product" in r.json()["detail"]


def test_bundle_id_mismatch_rejected(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u5", "role": "user", "credits": 0}
    ctx.tx_by_jws["JWS_Y_MOCK_STORE"] = ctx.make_tx(
        "com.visionarysuite.credits.60", "tx-901", bundle="com.other.app",
    )
    r = ctx.client.post("/api/iap/apple/verify", json={
        "productId": "com.visionarysuite.credits.60",
        "transactionId": "tx-901",
        "jwsRepresentation": "JWS_Y_MOCK_STORE",
    })
    assert r.status_code == 400
    assert "Bundle ID mismatch" in r.json()["detail"]


def test_body_vs_jws_product_mismatch_rejected(app_client_with_mocked_apple):
    """Client claims to buy a $10 pack, JWS says $1 pack — must reject."""
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u6", "role": "user", "credits": 0}
    ctx.tx_by_jws["JWS_Z_MOCK_STORE"] = ctx.make_tx("com.visionarysuite.credits.60", "tx-902")
    r = ctx.client.post("/api/iap/apple/verify", json={
        "productId": "com.visionarysuite.credits.800",  # LIE: claims larger pack
        "transactionId": "tx-902",
        "jwsRepresentation": "JWS_Z_MOCK_STORE",
    })
    assert r.status_code == 400
    assert "does not match verified receipt" in r.json()["detail"]


def test_bad_jws_rejected_with_400(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u7", "role": "user", "credits": 0}
    r = ctx.client.post("/api/iap/apple/verify", json={
        "productId": "com.visionarysuite.credits.60",
        "transactionId": "tx-903",
        "jwsRepresentation": "NEVER_REGISTERED_JWS",
    })
    assert r.status_code == 400


# ── 5. Webhook behavior ─────────────────────────────────────────────────────


def test_webhook_missing_signed_payload_returns_400(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    r = ctx.client.post("/api/iap/apple/webhook", json={})
    assert r.status_code == 400
    assert "Missing signedPayload" in r.json()["detail"]


def test_webhook_bad_signature_returns_400(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    # Fake service: verify_notification always raises.
    from services import apple_iap
    from services.apple_iap import AppleIAPVerificationError

    class BadSigService(ctx.FakeService):
        def verify_notification(self, sp):
            raise AppleIAPVerificationError("bad sig")

    apple_iap._service_instance = BadSigService()
    r = ctx.client.post("/api/iap/apple/webhook", json={"signedPayload": "anything"})
    assert r.status_code == 400
    assert "bad sig" in r.json()["detail"].lower() or "invalid" in r.json()["detail"].lower()


def test_webhook_did_renew_grants_credits_and_updates_expiry(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    # Seed a user + prior iap_transactions row so the webhook can locate them.
    ctx.users_state["current"] = {"id": "u10", "role": "user", "credits": 200,
                                   "plan_type": "monthly",
                                   "subscription_status": "active"}
    ctx.txns_state.append({
        "userId": "u10",
        "productId": "com.visionarysuite.sub.monthly",
        "transactionId": "sub-1000",
        "originalTransactionId": "sub-1000",
        "source": "verify",
    })

    future_ms = int((time.time() + 60 * 86400) * 1000)
    renewal_tx = ctx.make_tx("com.visionarysuite.sub.monthly", "sub-1001",
                              expires_ms=future_ms)
    renewal_tx.original_transaction_id = "sub-1000"

    from services import apple_iap

    class RenewService(ctx.FakeService):
        def verify_notification(self, sp):
            data = SimpleNamespace(signed_transaction_info="RENEW_JWS")
            return SimpleNamespace(
                notification_type=SimpleNamespace(value="DID_RENEW"),
                subtype=None,
                data=data,
            )

        def verify_transaction(self, jws):
            if jws == "RENEW_JWS":
                return renewal_tx
            return super().verify_transaction(jws)

    apple_iap._service_instance = RenewService()
    r = ctx.client.post("/api/iap/apple/webhook", json={"signedPayload": "SP1"})
    assert r.status_code == 200
    body = r.json()
    assert body["notificationType"] == "DID_RENEW"
    assert body["processed"] is True
    u = ctx.users_state["current"]
    assert u["credits"] == 400, "DID_RENEW must grant +200 monthly credits"
    assert u["subscription_status"] == "active"


def test_webhook_refund_revokes_subscription_and_deducts(app_client_with_mocked_apple):
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u11", "role": "user", "credits": 250,
                                   "plan_type": "monthly",
                                   "subscription_status": "active"}
    ctx.txns_state.append({
        "userId": "u11",
        "productId": "com.visionarysuite.sub.monthly",
        "transactionId": "sub-2000",
        "originalTransactionId": "sub-2000",
        "source": "verify",
    })

    refund_tx = ctx.make_tx("com.visionarysuite.sub.monthly", "sub-2000")
    refund_tx.original_transaction_id = "sub-2000"

    from services import apple_iap

    class RefundService(ctx.FakeService):
        def verify_notification(self, sp):
            return SimpleNamespace(
                notification_type=SimpleNamespace(value="REFUND"),
                subtype=None,
                data=SimpleNamespace(signed_transaction_info="REFUND_JWS"),
            )

        def verify_transaction(self, jws):
            if jws == "REFUND_JWS":
                return refund_tx
            return super().verify_transaction(jws)

    apple_iap._service_instance = RefundService()
    r = ctx.client.post("/api/iap/apple/webhook", json={"signedPayload": "SP2"})
    assert r.status_code == 200
    assert r.json()["notificationType"] == "REFUND"
    u = ctx.users_state["current"]
    assert u["subscription_status"] == "refunded"
    assert u["credits"] == 50, "REFUND must deduct the 200-credit monthly grant"


def test_webhook_unknown_notification_type_still_200(app_client_with_mocked_apple):
    """Apple retries non-200 for 3 days — unknown types must NOT retry-storm."""
    ctx = app_client_with_mocked_apple
    from services import apple_iap

    class WeirdService(ctx.FakeService):
        def verify_notification(self, sp):
            return SimpleNamespace(
                notification_type=SimpleNamespace(value="SOMETHING_APPLE_INVENTED_LATER"),
                subtype=None,
                data=None,
            )

    apple_iap._service_instance = WeirdService()
    r = ctx.client.post("/api/iap/apple/webhook", json={"signedPayload": "SP3"})
    assert r.status_code == 200
    assert r.json()["notificationType"] == "SOMETHING_APPLE_INVENTED_LATER"
    assert r.json()["processed"] is False


# ── 6. Webhook retry-storm idempotency (Apple retries for 3 days) ───────────


def test_webhook_did_renew_idempotent_on_replay(app_client_with_mocked_apple):
    """Apple redelivers webhooks on any transient network flake. A replay of
    the same DID_RENEW must NOT grant credits twice."""
    ctx = app_client_with_mocked_apple
    ctx.users_state["current"] = {"id": "u20", "role": "user", "credits": 200,
                                   "plan_type": "monthly",
                                   "subscription_status": "active"}
    ctx.txns_state.append({
        "userId": "u20",
        "productId": "com.visionarysuite.sub.monthly",
        "transactionId": "sub-9000",
        "originalTransactionId": "sub-9000",
        "source": "verify",
    })

    future_ms = int((time.time() + 60 * 86400) * 1000)
    renewal_tx = ctx.make_tx("com.visionarysuite.sub.monthly", "sub-9001",
                              expires_ms=future_ms)
    renewal_tx.original_transaction_id = "sub-9000"

    from services import apple_iap

    class RenewService(ctx.FakeService):
        def verify_notification(self, sp):
            return SimpleNamespace(
                notification_type=SimpleNamespace(value="DID_RENEW"),
                subtype=None,
                data=SimpleNamespace(signed_transaction_info="RENEW_REPLAY_JWS"),
            )

        def verify_transaction(self, jws):
            if jws == "RENEW_REPLAY_JWS":
                return renewal_tx
            return super().verify_transaction(jws)

    apple_iap._service_instance = RenewService()
    # First delivery — grants
    r1 = ctx.client.post("/api/iap/apple/webhook", json={"signedPayload": "SP_R1"})
    assert r1.status_code == 200 and r1.json()["processed"] is True
    balance_after_first = ctx.users_state["current"]["credits"]
    assert balance_after_first == 400  # 200 seed + 200 renewal grant

    # Second delivery — same notification for same tx — must be a no-op
    r2 = ctx.client.post("/api/iap/apple/webhook", json={"signedPayload": "SP_R2"})
    assert r2.status_code == 200
    assert r2.json()["processed"] is False, (
        "Duplicate webhook delivery for the same (transactionId, notificationType) "
        "must be a no-op — Apple retries for 3 days on any transient failure."
    )
    assert ctx.users_state["current"]["credits"] == 400, (
        "Second delivery must NOT grant additional credits."
    )

