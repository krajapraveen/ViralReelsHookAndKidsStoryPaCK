"""
P0 2026-05-22 Phase A — Google Ads conversion truth audit.

Production bug class: "0 conversions despite 41k impressions and
7% CTR." Root causes (from the BEFORE audit):

  • No Google Ads conversion ID (AW-XXX) wired anywhere; only GA4.
  • No `send_to` parameter on any event.
  • No gclid / gbraid / wbraid / fbclid capture or persistence.
  • signup_completed fires GA4 only — never Google Ads.
  • first_project_created event did not exist.
  • payment_success fired frontend-optimistic, never webhook-confirmed.
  • Cross-domain attribution (Cashfree return) broken.

This suite pins the surgical wiring that fixes the bug class:

  Backend:
    1. POST /api/attribution/capture exists; payload schema is strict
       and idempotent (never clobbers a real gclid).
    2. get_attribution_for_user helper exists for webhook stamping.
    3. GET /api/users/me/activation exists.
    4. mark_first_project_if_needed is atomic compare-and-set.
    5. GET /api/cashfree/conversion-status exposes webhook_confirmed
       and conversion_fired.
    6. POST /api/cashfree/conversion-acknowledged is idempotent
       (predicate gates on webhook_confirmed AND not yet fired).
    7. Cashfree webhook sets webhook_confirmed=true on PAYMENT_SUCCESS.
    8. Cashfree webhook stamps the order with source_platform +
       attribution_snapshot from the user's most recent attribution.
    9. GENERATION_COLLECTIONS list pins the universal activation
       chokepoint — adding a new generator means editing this list.

  Frontend:
    10. utils/attribution.js captures click-IDs + utm_* on first load
        with 90-day persistence and idempotent backend POST.
    11. utils/googleAdsConversions.js exposes fireSignupConversion,
        fireFirstProjectConversion, firePurchaseConversion + dedupe.
    12. App.js boots attribution capture + Google Ads tag config.
    13. Signup.js (both email + google paths) and AuthCallback.js
        fire signup conversion AFTER server-confirmed signup.
    14. NotificationContext's notifyGenerationComplete is the
        universal chokepoint that polls /api/users/me/activation
        and fires first_project conversion on transition.
    15. Billing.js does NOT call analytics.trackPurchase optimistically;
        it polls /api/cashfree/conversion-status and fires only when
        webhook_confirmed AND not yet conversion_fired, then
        POSTs /api/cashfree/conversion-acknowledged.

A PR that weakens any of the above must edit this file deliberately
AND attach an 8-section bug-class report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

APP = Path("/app")
sys.path.insert(0, str(APP / "backend"))

ATTRIBUTION = APP / "backend/routes/attribution.py"
CONVERSIONS = APP / "backend/routes/conversions.py"
ACTIVATION = APP / "backend/services/activation_truth.py"
CASHFREE = APP / "backend/routes/cashfree_payments.py"
SERVER = APP / "backend/server.py"

ATTR_JS = APP / "frontend/src/utils/attribution.js"
ADS_JS = APP / "frontend/src/utils/googleAdsConversions.js"
APP_JS = APP / "frontend/src/App.js"
NOTIF_JS = APP / "frontend/src/contexts/NotificationContext.js"
SIGNUP_JS = APP / "frontend/src/pages/Signup.js"
AUTHCB_JS = APP / "frontend/src/pages/AuthCallback.js"
BILLING_JS = APP / "frontend/src/pages/Billing.js"


# ─── Backend: routes exist and are mounted ───────────────────────────


def test_attribution_router_exists_and_mounted():
    assert ATTRIBUTION.exists(), "backend/routes/attribution.py missing"
    src = ATTRIBUTION.read_text()
    assert "router = APIRouter(prefix=\"/attribution\"" in src, (
        "attribution router prefix must be exactly /attribution "
        "(api_router already adds /api)."
    )
    assert "@router.post(\"/capture\")" in src
    assert "async def get_attribution_for_user" in src

    server = SERVER.read_text()
    assert "from routes.attribution import router as attribution_router" in server
    assert "api_router.include_router(attribution_router)" in server


def test_conversions_router_exists_and_mounted():
    assert CONVERSIONS.exists(), "backend/routes/conversions.py missing"
    src = CONVERSIONS.read_text()
    assert "@router.get(\"/users/me/activation\")" in src
    assert "@router.get(\"/cashfree/conversion-status\")" in src
    assert "@router.post(\"/cashfree/conversion-acknowledged\")" in src

    server = SERVER.read_text()
    assert "from routes.conversions import router as conversions_router" in server
    assert "api_router.include_router(conversions_router)" in server


def test_attribution_capture_is_idempotent():
    """The capture endpoint must never overwrite an existing real
    gclid with an empty payload. This is the central guarantee for
    paid-click attribution surviving Cashfree's redirect."""
    src = ATTRIBUTION.read_text()
    # The set_fields dict must skip empty values for click-ID and
    # utm fields. Pin the loop that enforces this.
    assert "if v:" in src and "set_fields[fld] = v" in src, (
        "attribution capture must merge only non-empty fields so a "
        "later visit without a gclid cannot clobber the original."
    )
    # First-visit context (landing_path, referrer) must use $setOnInsert
    # so it is captured exactly once.
    assert "$setOnInsert" in src
    assert "first_landing_path" in src
    assert "first_referrer" in src


def test_source_platform_classification_present():
    src = ATTRIBUTION.read_text()
    assert "_classify_source_platform" in src
    assert "google_ads" in src
    assert "meta_ads" in src
    assert "ALLOWED_SOURCE_PLATFORMS" in src


# ─── Backend: activation truth ───────────────────────────────────────


def test_activation_service_exposes_canonical_api():
    assert ACTIVATION.exists()
    src = ACTIVATION.read_text()
    assert "async def mark_first_project_if_needed(" in src
    assert "async def get_activation_state(" in src
    assert "GENERATION_COLLECTIONS" in src


def test_first_project_uses_atomic_compare_and_set():
    src = ACTIVATION.read_text()
    # The atomic CAS predicate is the single guarantee that fire_now
    # transitions True exactly once across all tabs and retries.
    assert re.search(
        r'first_project_completed_at["\']\s*:\s*\{\s*["\']\$exists["\']\s*:\s*False',
        src,
    ), (
        "mark_first_project_if_needed must use an $exists: False "
        "predicate to make the transition atomic."
    )


def test_generation_collections_cover_all_modalities():
    """Hard requirement: first_project_created must fire for ALL
    generation modalities, not just one feature. Pin the list."""
    from services.activation_truth import GENERATION_COLLECTIONS
    names = {entry[0] for entry in GENERATION_COLLECTIONS}
    required = {
        "reaction_gif_jobs",
        "photo_to_comic_jobs",
        "storybook_jobs",
        "story_video_jobs",
        "youstar_jobs",
        "ai_studio_jobs",
    }
    missing = required - names
    assert not missing, (
        f"GENERATION_COLLECTIONS missing required modalities: {missing}. "
        "Add them so every generator participates in the activation event."
    )


# ─── Backend: cashfree webhook handshake ─────────────────────────────


def test_cashfree_webhook_sets_webhook_confirmed():
    src = CASHFREE.read_text()
    # On PAYMENT_SUCCESS_WEBHOOK, the orders update must set
    # webhook_confirmed=True. This is the canonical truth that gates
    # the frontend conversion fire.
    assert "webhook_confirmed" in src
    assert re.search(
        r'"webhook_confirmed"\s*:\s*True',
        src,
    ), "Cashfree webhook must set webhook_confirmed=True on success."


def test_cashfree_webhook_stamps_attribution():
    src = CASHFREE.read_text()
    assert "get_attribution_for_user" in src, (
        "Cashfree webhook must look up the user's attribution and "
        "stamp the order with source_platform + attribution_snapshot."
    )
    assert "attribution_snapshot" in src
    assert "source_platform" in src


def test_conversion_ack_is_idempotent():
    src = CONVERSIONS.read_text()
    # The compound predicate is the idempotency guarantee.
    assert '"webhook_confirmed": True' in src
    assert '"conversion_fired": {"$ne": True}' in src, (
        "POST /cashfree/conversion-acknowledged must only flip the "
        "flag when webhook has confirmed AND conversion has not yet "
        "been fired. Otherwise refresh/replay can double-acknowledge."
    )


# ─── Frontend: attribution capture ───────────────────────────────────


def test_frontend_attribution_module_complete():
    assert ATTR_JS.exists()
    src = ATTR_JS.read_text()
    assert "captureAttribution" in src
    assert "syncAttributionToBackend" in src
    assert "getAnonymousId" in src
    assert "getStoredAttribution" in src
    for p in ("gclid", "gbraid", "wbraid", "fbclid",
              "utm_source", "utm_medium", "utm_campaign",
              "utm_content", "utm_term"):
        assert f"'{p}'" in src, f"Attribution module missing param: {p}"
    # 90-day TTL constant
    assert "90 * 24 * 60 * 60 * 1000" in src
    # Source platform classification
    assert "_classifySourcePlatform" in src


def test_app_boots_attribution_capture():
    src = APP_JS.read_text()
    assert "captureAttribution()" in src
    assert "syncAttributionToBackend(api)" in src
    assert "configureGoogleAdsTag()" in src


# ─── Frontend: Google Ads conversion helper ──────────────────────────


def test_google_ads_helper_exposes_three_fires():
    assert ADS_JS.exists()
    src = ADS_JS.read_text()
    assert "fireSignupConversion" in src
    assert "fireFirstProjectConversion" in src
    assert "firePurchaseConversion" in src
    assert "configureGoogleAdsTag" in src


def test_google_ads_helper_reads_env_vars():
    src = ADS_JS.read_text()
    for v in (
        "REACT_APP_GOOGLE_ADS_CONVERSION_ID",
        "REACT_APP_GOOGLE_ADS_LABEL_SIGNUP",
        "REACT_APP_GOOGLE_ADS_LABEL_FIRST_PROJECT",
        "REACT_APP_GOOGLE_ADS_LABEL_PURCHASE",
    ):
        assert v in src, f"Google Ads helper must read env var {v}"


def test_google_ads_helper_dedupes_per_transaction():
    src = ADS_JS.read_text()
    assert "DEDUPE_PREFIX" in src
    assert "_alreadyFired" in src
    assert "_markFired" in src
    # The dedupe key must include both label and transactionId so
    # signup vs first-project vs purchase do not collide.
    assert "_dedupeKey(label, transactionId)" in src


def test_google_ads_event_shape_is_canonical():
    """`gtag('event', 'conversion', { send_to, transaction_id,
    value, currency })` is the canonical Google Ads enhanced-
    conversion call shape. Anything else fails to attribute."""
    src = ADS_JS.read_text()
    assert "window.gtag('event', 'conversion'" in src
    for f in ("send_to", "transaction_id", "value", "currency"):
        assert f in src, f"Conversion event payload missing field: {f}"


# ─── Frontend: wiring at the three firing points ─────────────────────


def test_signup_email_fires_conversion_after_server_confirm():
    src = SIGNUP_JS.read_text()
    # The fire must happen AFTER the server-returned userId, not on
    # form submission. Pin the order.
    user_id_pos = src.find("const userId = response.data.user?.id;")
    fire_pos = src.find("fireSignupConversion(userId)")
    assert user_id_pos != -1 and fire_pos != -1, (
        "Signup.js email path must fire signup conversion AFTER "
        "extracting userId from the server response."
    )
    assert user_id_pos < fire_pos


def test_signup_google_path_fires_conversion():
    src = SIGNUP_JS.read_text()
    # Google-direct path inside Signup.js must also fire.
    assert "fireSignupConversion(user.id)" in src


def test_authcallback_fires_conversion_after_google_oauth():
    src = AUTHCB_JS.read_text()
    assert "fireSignupConversion(user.id)" in src
    # Must be inside the user-confirmed branch (only fire when we
    # actually have a user id from the OAuth response).
    assert "if (user?.id)" in src or "if (user.id)" in src


def test_notify_generation_complete_polls_activation():
    """The universal chokepoint: every generator that calls
    notifyGenerationComplete (Reaction GIF, Photo-to-Comic, Story
    Video, YouStar, AI Studio, …) automatically participates in the
    first-project conversion. Pin the call."""
    src = NOTIF_JS.read_text()
    assert "/api/users/me/activation" in src
    assert "fire_now === true" in src
    assert "fireFirstProjectConversion" in src


def test_billing_does_not_fire_optimistic_purchase():
    """The legacy frontend-optimistic call MUST be gone.

    The current code path goes through the webhook-confirmed handshake:
    poll /api/cashfree/conversion-status until webhook_confirmed=True,
    fire purchase conversion, then POST conversion-acknowledged. The
    old `analytics.trackPurchase(orderId, item, 'INR')` direct fire is
    the failure mode the user explicitly called out and must not
    return.
    """
    src = BILLING_JS.read_text()
    assert "analytics.trackPurchase(response.data.orderId, item, 'INR')" not in src, (
        "Legacy frontend-optimistic purchase fire is back. The "
        "purchase conversion MUST go through the webhook-confirmed "
        "handshake (conversion-status → fire → conversion-acknowledged)."
    )


def test_billing_uses_webhook_confirmed_handshake():
    src = BILLING_JS.read_text()
    assert "firePurchaseConversion" in src
    assert "/api/cashfree/conversion-status?order_id=" in src
    assert "/api/cashfree/conversion-acknowledged" in src
    assert "webhook_confirmed" in src
    assert "conversion_fired" in src
