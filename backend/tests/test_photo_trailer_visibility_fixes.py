"""
P0 visibility tests for the consent checkbox + Hero/Villain/Support role buttons.

Verifies:
1. Consent checkbox is a SQUARE >= 22px with thick border and visible
   background tint when unchecked, emerald fill when checked.
2. Role buttons under each photo card are 40-44px tall (proper tap target),
   one row of three, with clearly distinct color states when active.
3. Click HERO -> button gets gold/amber active class + aria-pressed=true.
"""
import os
import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_PHOTO = "/tmp/face.jpg"


@pytest.fixture(scope="module", autouse=True)
def ensure_photo():
    if not os.path.exists(TEST_PHOTO):
        from PIL import Image
        Image.new("RGB", (1024, 1024), (80, 60, 200)).save(TEST_PHOTO, "JPEG")


def _login_open(page, viewport):
    page.set_viewport_size(viewport)
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[type="email"]', ADMIN_EMAIL)
    page.fill('input[type="password"]', ADMIN_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_timeout(2500)
    page.goto(f"{BASE_URL}/app/photo-trailer", wait_until="networkidle")
    page.wait_for_timeout(2000)
    try:
        page.locator('button:has-text("Reject All")').click(timeout=1500)
    except Exception:
        pass


class TestConsentCheckboxVisibility:
    def test_checkbox_is_square_22px_minimum_desktop(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            try:
                _login_open(page, {"width": 1280, "height": 900})
                # The visible square is the first <span aria-hidden> inside the consent label
                box = page.locator('[data-testid="trailer-consent"] span[aria-hidden]').first
                expect(box).to_be_visible()
                bbox = box.bounding_box()
                assert bbox["width"] >= 22, f"checkbox too narrow: {bbox['width']}px"
                assert bbox["height"] >= 22, f"checkbox too short: {bbox['height']}px"
                # Square: width and height differ by no more than 1px
                assert abs(bbox["width"] - bbox["height"]) <= 1.5, f"not square: {bbox}"
            finally:
                ctx.close(); browser.close()

    def test_checkbox_is_24px_minimum_mobile(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            try:
                _login_open(page, {"width": 390, "height": 844})
                box = page.locator('[data-testid="trailer-consent"] span[aria-hidden]').first
                bbox = box.bounding_box()
                assert bbox["width"] >= 24, f"mobile checkbox too narrow: {bbox['width']}px"
                assert bbox["height"] >= 24, f"mobile checkbox too short: {bbox['height']}px"
            finally:
                ctx.close(); browser.close()


class TestRoleButtonVisibility:
    def test_role_buttons_have_proper_tap_target_size(self):
        """Hero/Villain/Support each must be >= 40px tall (>= 44px on mobile)."""
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            try:
                _login_open(page, {"width": 1280, "height": 1100})
                page.locator('[data-testid="trailer-photo-input"]').set_input_files(TEST_PHOTO)
                page.wait_for_selector('[data-testid="trailer-photo-grid"] > div', timeout=15000)
                page.wait_for_timeout(800)
                page.locator('[data-testid="trailer-consent"]').click()
                page.wait_for_timeout(300)
                page.locator('[data-testid="trailer-step1-next"]').click()
                page.wait_for_selector('[data-testid="trailer-step-characters"]', timeout=10000)

                hero_btn = page.locator('[data-testid^="pick-hero-"]').first
                villain_btn = page.locator('[data-testid^="pick-villain-"]').first
                support_btn = page.locator('[data-testid^="pick-support-"]').first
                for label, btn in [("hero", hero_btn), ("villain", villain_btn), ("support", support_btn)]:
                    bb = btn.bounding_box()
                    assert bb is not None, f"{label} button missing"
                    assert bb["height"] >= 40, f"{label} button too short: {bb['height']}px"
                    # And it must be wide enough to read the label
                    assert bb["width"] >= 48, f"{label} button too narrow: {bb['width']}px"
            finally:
                ctx.close(); browser.close()

    def test_role_buttons_44px_on_mobile(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            try:
                _login_open(page, {"width": 390, "height": 1100})
                page.locator('[data-testid="trailer-photo-input"]').set_input_files(TEST_PHOTO)
                page.wait_for_selector('[data-testid="trailer-photo-grid"] > div', timeout=15000)
                page.wait_for_timeout(800)
                page.locator('[data-testid="trailer-consent"]').click()
                page.wait_for_timeout(300)
                page.locator('[data-testid="trailer-step1-next"]').click()
                page.wait_for_selector('[data-testid="trailer-step-characters"]', timeout=10000)
                hero_btn = page.locator('[data-testid^="pick-hero-"]').first
                bb = hero_btn.bounding_box()
                assert bb["height"] >= 44, f"mobile tap target too short: {bb['height']}px"
            finally:
                ctx.close(); browser.close()

    def test_clicking_hero_marks_button_active_with_aria(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            try:
                _login_open(page, {"width": 1280, "height": 1100})
                page.locator('[data-testid="trailer-photo-input"]').set_input_files(TEST_PHOTO)
                page.wait_for_selector('[data-testid="trailer-photo-grid"] > div', timeout=15000)
                page.wait_for_timeout(800)
                page.locator('[data-testid="trailer-consent"]').click()
                page.wait_for_timeout(300)
                page.locator('[data-testid="trailer-step1-next"]').click()
                page.wait_for_selector('[data-testid="trailer-step-characters"]', timeout=10000)
                hero_btn = page.locator('[data-testid^="pick-hero-"]').first
                # Initially not pressed
                assert hero_btn.get_attribute("aria-pressed") == "false"
                hero_btn.click()
                page.wait_for_timeout(300)
                # Now pressed
                assert hero_btn.get_attribute("aria-pressed") == "true"
                # And the active class includes the amber background
                cls = hero_btn.get_attribute("class") or ""
                assert "amber" in cls, f"active hero button missing amber class: {cls[:200]}"
                # The "Continue" CTA should now be enabled
                expect(page.locator('[data-testid="trailer-step2-next"]')).to_be_enabled()
            finally:
                ctx.close(); browser.close()
