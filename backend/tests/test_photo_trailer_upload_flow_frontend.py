"""
Frontend regression test for the Photo Trailer Step 1 (Upload) flow.

Reproduces the funnel-killer bug where the "Continue" CTA stayed disabled
even after a valid photo was uploaded + the consent box was tapped.

Verifies the contract:
  1. Add 1 valid photo  -> photo grid shows 1 item, hint says "Confirm photo rights..."
  2. Tap consent box    -> custom emerald checkbox shows checked, hint disappears
  3. CTA enabled        -> button no longer has `disabled` attribute
  4. Click CTA          -> advances to Step 2 (data-testid=trailer-step-characters)
  5. Without consent    -> CTA stays disabled even if photos uploaded
  6. Without photos     -> CTA stays disabled even if consent checked
"""
import os
import requests
import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_PHOTO = "/tmp/face.jpg"


@pytest.fixture(scope="module", autouse=True)
def ensure_test_photo():
    if not os.path.exists(TEST_PHOTO):
        from PIL import Image
        Image.new("RGB", (1024, 1024), (80, 60, 200)).save(TEST_PHOTO, "JPEG")


def _login_and_open_wizard(page):
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[type="email"]', ADMIN_EMAIL)
    page.fill('input[type="password"]', ADMIN_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_timeout(2500)
    page.goto(f"{BASE_URL}/app/photo-trailer")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    # dismiss cookie banner if present
    try:
        page.locator('button:has-text("Reject All")').click(timeout=1500)
    except Exception:
        pass


class TestPhotoTrailerUploadFlow:
    def test_continue_blocked_until_photo_and_consent(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            try:
                _login_and_open_wizard(page)

                # Initial state: no photos, no consent → CTA disabled, hint = "Add at least 1 photo"
                cta = page.locator('[data-testid="trailer-step1-next"]')
                expect(cta).to_be_disabled()
                expect(page.locator('[data-testid="trailer-step1-hint"]')).to_have_text(
                    "Add at least 1 photo to continue."
                )

                # Upload one valid photo
                page.locator('[data-testid="trailer-photo-input"]').set_input_files(TEST_PHOTO)
                page.wait_for_timeout(4000)  # backend roundtrip + state propagation

                # Photo grid should contain 1 item
                grid = page.locator('[data-testid="trailer-photo-grid"] > div')
                expect(grid).to_have_count(1)

                # CTA still disabled, but hint changed to "Confirm photo rights..."
                expect(cta).to_be_disabled()
                expect(page.locator('[data-testid="trailer-step1-hint"]')).to_have_text(
                    "Confirm photo rights to continue."
                )

                # Tap the consent box (label is clickable)
                page.locator('[data-testid="trailer-consent"]').click()
                page.wait_for_timeout(500)
                expect(page.locator('[data-testid="trailer-consent-checkbox"]')).to_be_checked()

                # CTA now enabled, hint gone
                expect(cta).to_be_enabled()
                expect(page.locator('[data-testid="trailer-step1-hint"]')).to_have_count(0)

                # Click CTA → Step 2 should render
                cta.click()
                page.wait_for_timeout(2500)
                expect(page.locator('[data-testid="trailer-step-characters"]')).to_be_visible()
            finally:
                ctx.close()
                browser.close()

    def test_consent_alone_does_not_enable_cta(self):
        """No photos uploaded — checking consent must NOT enable the button."""
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            try:
                _login_and_open_wizard(page)

                # No photos. Tap consent only.
                page.locator('[data-testid="trailer-consent"]').click()
                page.wait_for_timeout(400)
                expect(page.locator('[data-testid="trailer-consent-checkbox"]')).to_be_checked()

                # CTA must still be disabled
                expect(page.locator('[data-testid="trailer-step1-next"]')).to_be_disabled()
            finally:
                ctx.close()
                browser.close()

    def test_unchecking_consent_disables_cta_again(self):
        """Toggle: enable then untick → CTA must go back to disabled."""
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            try:
                _login_and_open_wizard(page)

                page.locator('[data-testid="trailer-photo-input"]').set_input_files(TEST_PHOTO)
                page.wait_for_timeout(4000)

                consent = page.locator('[data-testid="trailer-consent"]')
                cta = page.locator('[data-testid="trailer-step1-next"]')

                consent.click()
                page.wait_for_timeout(300)
                expect(cta).to_be_enabled()

                consent.click()  # untick
                page.wait_for_timeout(300)
                expect(page.locator('[data-testid="trailer-consent-checkbox"]')).not_to_be_checked()
                expect(cta).to_be_disabled()
                expect(page.locator('[data-testid="trailer-step1-hint"]')).to_have_text(
                    "Confirm photo rights to continue."
                )
            finally:
                ctx.close()
                browser.close()
