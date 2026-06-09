"""P0 2026-06 LEGAL — Privacy / Cookie policy mandatory disclosures.

User-mandated, platform-specific legal content. Generic templates
are explicitly rejected. The Privacy Policy and Cookie Policy MUST
disclose each of the following — any future PR that strips one of
them violates the contract this test enforces.

Registered under `make audit-boundaries`.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path("/app")
FRONTEND = REPO / "frontend"

PRIVACY = (FRONTEND / "src" / "pages" / "PrivacyPolicy.js").read_text()
COOKIE = (FRONTEND / "src" / "pages" / "CookiePolicy.js").read_text()
PUBLIC_SETTINGS = (FRONTEND / "src" / "pages" / "PublicPrivacySettings.js").read_text()
COOKIE_CONSENT = (FRONTEND / "src" / "components" / "CookieConsent.js").read_text()
INDEX_HTML = (FRONTEND / "public" / "index.html").read_text()
APP_JS = (FRONTEND / "src" / "App.js").read_text()
LANDING = (FRONTEND / "src" / "pages" / "Landing.js").read_text()


# ─────────────────────────────────────────────────────────────────────
# Section A — Platform-specific feature disclosure.
# Every Visionary Suite feature in the legal-scope brief MUST be
# named in the Privacy Policy so the policy is product-specific.
# ─────────────────────────────────────────────────────────────────────

REQUIRED_FEATURES = [
    "Story Video Studio",
    "Photo to Comic",
    "Comic Storybook",
    "Character Studio",
    "Story Series",
    "Reel Generator",
    "Brand Kit",
    "Bedtime Stories",
    "Reaction GIF",
    "Daily Viral Ideas",
    "MyTrailer",
]


def test_privacy_policy_lists_every_feature():
    missing = [f for f in REQUIRED_FEATURES if f not in PRIVACY]
    assert not missing, (
        f"Privacy Policy must enumerate every Visionary Suite feature so "
        f"users know which products the policy covers. Missing: {missing}"
    )


# ─────────────────────────────────────────────────────────────────────
# Section B — Facial image processing disclosure (mandatory).
# ─────────────────────────────────────────────────────────────────────


def test_privacy_policy_has_facial_image_disclosure_section():
    assert "Facial Image Processing" in PRIVACY, (
        "Privacy Policy must contain a dedicated `Facial Image Processing` section."
    )
    # The four mandatory negative commitments.
    assert "do not sell" in PRIVACY.lower() and "facial image" in PRIVACY.lower(), (
        "Must state explicitly that facial images are not sold."
    )
    assert "facial-recognition surveillance" in PRIVACY or "facial recognition" in PRIVACY.lower(), (
        "Must disclaim use for facial-recognition surveillance."
    )
    assert "biometric identification" in PRIVACY.lower(), (
        "Must disclaim biometric identification."
    )
    assert "law-enforcement" in PRIVACY.lower() or "law enforcement" in PRIVACY.lower(), (
        "Must disclaim use for law-enforcement identification."
    )
    # The positive commitment that images are used ONLY for the requested output.
    assert ("solely" in PRIVACY.lower()) or ("only" in PRIVACY.lower()), (
        "Must commit images are used solely/only for requested outputs."
    )


# ─────────────────────────────────────────────────────────────────────
# Section C — Voice / audio processing disclosure (mandatory).
# ─────────────────────────────────────────────────────────────────────


def test_privacy_policy_has_voice_audio_section():
    assert "Voice" in PRIVACY and "Audio" in PRIVACY
    # User confirmation that they hold rights.
    assert "rights" in PRIVACY.lower() and "audio" in PRIVACY.lower(), (
        "Must require user has rights to uploaded audio."
    )


# ─────────────────────────────────────────────────────────────────────
# Section D — AI service provider disclosure (mandatory).
# Must name the categories of provider that may receive user content.
# ─────────────────────────────────────────────────────────────────────


def test_privacy_policy_discloses_ai_providers():
    assert "AI Service Providers" in PRIVACY or "AI model providers" in PRIVACY, (
        "Privacy Policy must disclose that user content is transmitted "
        "to AI service providers."
    )
    for category in (
        "AI model providers",
        "Cloud infrastructure",
        "Authentication providers",
        "Payment processors",
        "Analytics",
    ):
        assert category in PRIVACY, (
            f"AI-provider disclosure must list `{category}` as a provider category."
        )


# ─────────────────────────────────────────────────────────────────────
# Section E — User-ownership clause (mandatory).
# ─────────────────────────────────────────────────────────────────────


def test_privacy_policy_has_user_ownership_clause():
    needle = "does not claim ownership"
    assert needle in PRIVACY, (
        f"Privacy Policy must contain the literal phrase `{needle}` so "
        f"the platform's non-ownership of user content is explicit."
    )
    # And the matching positive statement that users retain ownership.
    assert "retain ownership" in PRIVACY


def test_privacy_policy_has_generated_content_responsibility_clause():
    assert "AI-generated outputs may contain inaccuracies" in PRIVACY, (
        "Privacy Policy must contain the AI-generated content "
        "responsibility clause."
    )


def test_privacy_policy_has_copyright_responsibility_block():
    for right in ("Copyright", "Trademark", "publicity", "privacy"):
        assert right.lower() in PRIVACY.lower(), (
            f"Copyright-responsibility block must list `{right}`."
        )


# ─────────────────────────────────────────────────────────────────────
# Section F — GDPR + DPDP 2023 sections (mandatory).
# ─────────────────────────────────────────────────────────────────────


def test_privacy_policy_has_gdpr_section_with_named_articles():
    assert "GDPR" in PRIVACY
    # Article numbers nail down that the section is real, not lip-service.
    for art in ("Article 15", "Article 16", "Article 17", "Article 20"):
        assert art in PRIVACY, (
            f"GDPR section must cite `{art}` so the policy is enforceable."
        )


def test_privacy_policy_has_dpdp_act_section():
    assert "DPDP Act" in PRIVACY or "Digital Personal Data Protection Act 2023" in PRIVACY
    # The mandatory rights enumeration for India.
    assert "grievance redressal" in PRIVACY.lower() or "Grievance" in PRIVACY, (
        "DPDP section must enumerate the grievance-redressal right."
    )
    assert "nominate" in PRIVACY.lower(), (
        "DPDP section must enumerate the nomination right (Section 14 DPDP Act)."
    )


# ─────────────────────────────────────────────────────────────────────
# Section G — Web + iOS + Android coverage statement (mandatory).
# ─────────────────────────────────────────────────────────────────────


def test_privacy_policy_covers_web_ios_android():
    for surface in ("iOS application", "Android application", "website"):
        assert surface in PRIVACY, (
            f"Privacy Policy must explicitly cover `{surface}`."
        )


# ─────────────────────────────────────────────────────────────────────
# Section H — Contact + retention + deletion.
# ─────────────────────────────────────────────────────────────────────


def test_privacy_policy_has_contact_email():
    assert "privacy@visionary-suite.com" in PRIVACY
    assert "support@visionary-suite.com" in PRIVACY


def test_privacy_policy_states_30_day_soft_delete():
    assert "30-day soft-deletion" in PRIVACY or "30 day soft" in PRIVACY.lower(), (
        "Privacy Policy must commit to the 30-day soft-deletion period."
    )
    assert "permanent deletion" in PRIVACY.lower() or "permanently deleted" in PRIVACY.lower()


# ─────────────────────────────────────────────────────────────────────
# Section I — Cookie Policy structure.
# ─────────────────────────────────────────────────────────────────────


def test_cookie_policy_has_all_required_categories():
    for category in (
        "Essential Cookies",
        "Functional Cookies",
        "Analytics Cookies",
        "Performance Cookies",
        "Third-Party Cookies",
    ):
        assert category in COOKIE, f"Cookie Policy must define `{category}`."


def test_cookie_policy_has_consent_banner_triple_buttons():
    for label in ("Accept All", "Reject Non-Essential", "Manage Preferences"):
        assert label in COOKIE, (
            f"Cookie Policy must document the banner `{label}` choice."
        )


def test_cookie_policy_documents_consent_withdrawal_path():
    assert "Privacy Settings" in COOKIE
    assert "/privacy-settings" in COOKIE, (
        "Cookie Policy must link to the public /privacy-settings page "
        "for consent withdrawal."
    )


# ─────────────────────────────────────────────────────────────────────
# Section J — Consent banner: default-deny analytics + opt-in flow.
# Article 7(3) GDPR + DPDP Act: analytics MUST NOT load before consent.
# ─────────────────────────────────────────────────────────────────────


def test_gtag_consent_default_denies_analytics():
    """Google Consent Mode v2: analytics_storage must default to
    'denied'. CookieConsent updates to 'granted' only after the user
    opts in. Pinned literally so a future commit can't accidentally
    flip the default."""
    assert "gtag('consent', 'default'" in INDEX_HTML, (
        "index.html must set Google Consent Mode v2 default before "
        "gtag('config')."
    )
    assert "'analytics_storage': 'denied'" in INDEX_HTML, (
        "analytics_storage must default to 'denied' to comply with "
        "GDPR / DPDP pre-consent rules."
    )
    assert "'ad_storage': 'denied'" in INDEX_HTML


def test_posthog_init_opts_out_by_default():
    """PostHog must initialize in opted-out state so events don't
    fire before consent."""
    assert "opt_out_capturing_by_default: true" in INDEX_HTML, (
        "PostHog must initialize with opt_out_capturing_by_default=true. "
        "Without this, events fire before the user sees the consent banner."
    )


def test_cookie_consent_banner_has_required_buttons():
    """The CookieConsent component must expose all three banner choices
    using the exact legal-mandated labels."""
    for label in ("Accept All", "Reject Non-Essential", "Manage Preferences"):
        assert label in COOKIE_CONSENT, (
            f"CookieConsent component must expose `{label}` button label "
            f"verbatim (legal-audit mandated wording)."
        )
    # Stale wording must NOT linger — the legal audit explicitly rejected
    # "Reject All" / "Customize" as too ambiguous about what is rejected.
    assert ">Reject All<" not in COOKIE_CONSENT, (
        "Legacy `Reject All` label must be replaced by `Reject Non-Essential`."
    )
    assert ">Customize<" not in COOKIE_CONSENT, (
        "Legacy `Customize` label must be replaced by `Manage Preferences`."
    )


def test_cookie_consent_withdrawal_stops_session_recording():
    """Article 7(3) GDPR + DPDP withdrawal parity: rejecting analytics
    must immediately stop PostHog session recording, not just opt out
    of event capture. Without this, recordings continue for the rest
    of the session even after the user revokes consent."""
    assert "stopSessionRecording" in COOKIE_CONSENT, (
        "disableAnalytics must call posthog.stopSessionRecording() so "
        "consent withdrawal is immediate and complete."
    )


def test_posthog_session_recording_disabled_by_default():
    """Session recording must be opted-out at PostHog init. It only
    starts after the user opts in via the consent banner. This is the
    runtime counterpart of `opt_out_capturing_by_default: true`."""
    assert "disable_session_recording: true" in INDEX_HTML, (
        "PostHog init must include `disable_session_recording: true` "
        "so recordings never start before consent."
    )


def test_cookie_consent_default_state_is_essential_only():
    """When the banner first appears, all non-essential categories MUST
    default to OFF — the user has not yet consented."""
    # The defaultConsent constant must show analytics=false, marketing=false,
    # preferences=false at first paint.
    assert re.search(r"analytics:\s*false", COOKIE_CONSENT), (
        "CookieConsent default state must have analytics: false."
    )
    assert re.search(r"marketing:\s*false", COOKIE_CONSENT)


# ─────────────────────────────────────────────────────────────────────
# Section K — Routes + footer links.
# ─────────────────────────────────────────────────────────────────────


def test_routes_exist_for_all_legal_pages():
    for path in ('"/privacy-policy"', '"/cookie-policy"',
                 '"/terms-of-service"', '"/privacy-settings"'):
        assert path in APP_JS, (
            f"App.js must register route {path}."
        )


def test_footer_links_to_all_legal_pages():
    """Landing footer must link to Privacy / Cookie / Terms / Privacy
    Settings using the exact route paths (no stale `/privacy`, `/terms`,
    `/cookies` short paths)."""
    for tid in (
        "footer-privacy-link",
        "footer-cookie-link",
        "footer-terms-link",
        "footer-privacy-settings-link",
    ):
        assert tid in LANDING, f"Landing footer must expose `{tid}`."
    # No stale short paths.
    assert 'to="/privacy"' not in LANDING, (
        "Landing footer must use `/privacy-policy`, not the stale `/privacy` path."
    )
    assert 'to="/cookies"' not in LANDING


# ─────────────────────────────────────────────────────────────────────
# Section L — Public PrivacySettings page surfaces consent control.
# ─────────────────────────────────────────────────────────────────────


def test_public_privacy_settings_has_all_consent_controls():
    for tid in (
        "settings-row-necessary",
        "settings-row-analytics",
        "settings-row-marketing",
        "settings-row-preferences",
        "settings-save-btn",
        "settings-accept-all-btn",
        "settings-reject-all-btn",
        "settings-reset-banner-btn",
    ):
        assert tid in PUBLIC_SETTINGS, (
            f"Public PrivacySettings must expose `{tid}`."
        )
    assert "necessary: true" in PUBLIC_SETTINGS, (
        "Necessary toggle must be hard-coded to true (always on)."
    )


def test_public_privacy_settings_immediately_updates_gtag_and_posthog():
    """Saving consent must propagate to gtag + posthog IMMEDIATELY
    without a page reload — Article 7(3) GDPR requires withdrawal to
    be as easy as granting."""
    assert "gtag('consent', 'update'" in PUBLIC_SETTINGS
    assert "posthog.opt_in_capturing" in PUBLIC_SETTINGS
    assert "posthog.opt_out_capturing" in PUBLIC_SETTINGS
