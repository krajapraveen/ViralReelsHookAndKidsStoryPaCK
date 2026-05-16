"""
Single-scenario CTA1 verification — exact founder-spec checks
=============================================================
Runs the "Create Series with this Character" click flow against the
PREVIEW environment (production-equivalent code post-fix) and asserts
every founder-required outcome verbatim:

  1. URL becomes /app/story-series/create?character_id=<id>
  2. Create Series page opens (data-testid="create-series-page")
  3. Banner shows the actual character name (NOT "Selected character")
  4. No toast saying "Preselected character could not be loaded"
  5. No auth redirect (URL never contains /login after click)
  6. No console error (third-party CSP noise filtered)
"""
from __future__ import annotations

import os
import uuid

import pytest
from playwright.async_api import async_playwright
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")


NOISE_SUBSTRINGS = (
    "cloudflareinsights",
    "Content Security Policy",
    "posthog",
    "google-analytics",
    "googletagmanager",
    "favicon",
    "Failed to load resource",
)


def _preview_base() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:3000"


async def _ensure_seed_character():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    try:
        admin = await db.users.find_one(
            {"email": "admin@creatorstudio.ai"}, {"_id": 0, "id": 1}
        )
        uid = admin["id"]
        existing = await db.character_profiles.find_one(
            {"owner_user_id": uid},
            {"_id": 0, "character_id": 1, "name": 1},
        )
        if existing and existing.get("character_id"):
            return existing["character_id"], existing.get("name") or "Test Hero"
        cid = f"prod-verify-{uuid.uuid4().hex[:12]}"
        await db.character_profiles.insert_one({
            "character_id": cid,
            "owner_user_id": uid,
            "name": "Prod Verify Hero",
        })
        return cid, "Prod Verify Hero"
    finally:
        cli.close()


@pytest.mark.asyncio
async def test_cta1_create_series_preview_verification():
    """Single-scenario verification against the preview environment.
    Maps 1:1 to the founder's production-verification checklist."""
    base = _preview_base()
    character_id, character_name = await _ensure_seed_character()
    errs = []
    auth_url_after_click = []
    click_marker = {"clicked": False}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        def _on_msg(msg):
            if msg.type != "error":
                return
            text = msg.text or ""
            if any(noise in text for noise in NOISE_SUBSTRINGS):
                return
            errs.append(text)
        page.on("console", _on_msg)

        def _on_url(frame):
            try:
                url = frame.url
                # Only count auth redirects that happen AFTER the click —
                # the legitimate /login bootstrap visit is not a redirect.
                if click_marker["clicked"] and "/login" in url:
                    auth_url_after_click.append(url)
            except Exception:
                pass
        page.on("framenavigated", _on_url)

        # Login
        await page.goto(f"{base}/login", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector('[data-testid="login-email-input"]', timeout=10000)
        await page.fill('[data-testid="login-email-input"]', "admin@creatorstudio.ai")
        await page.fill('[data-testid="login-password-input"]', "Cr3@t0rStud!o#2026")
        await page.click('[data-testid="login-submit-btn"]')
        await page.wait_for_timeout(3500)

        # Open character detail
        await page.goto(
            f"{base}/app/characters/{character_id}",
            wait_until="networkidle",
            timeout=20000,
        )
        await page.wait_for_selector('[data-testid="character-attach-help"]', timeout=10000)
        await page.locator('[data-testid="character-attach-help"]').scroll_into_view_if_needed(timeout=4000)
        await page.wait_for_timeout(400)

        # Click CTA1
        click_marker["clicked"] = True
        await page.click('[data-testid="cta-create-series-with-character"]')
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(500)

        # Check 1: URL
        url = page.url
        assert "/app/story-series/create" in url, f"Wrong destination URL: {url}"
        assert f"character_id={character_id}" in url, f"Missing character_id in URL: {url}"

        # Check 2: Create Series page opens
        await page.wait_for_selector('[data-testid="create-series-page"]', timeout=6000)

        # Check 3: Banner shows the actual character name
        await page.locator('[data-testid="preselected-character-banner"]').wait_for(
            state="visible", timeout=8000
        )
        name_el = page.locator('[data-testid="preselected-character-name"]')
        await name_el.wait_for(state="visible", timeout=8000)
        rendered_name = (await name_el.inner_text()).strip()
        assert rendered_name and rendered_name != "Selected character", \
            f"Banner did not populate actual name: {rendered_name!r}"
        # The rendered name should equal the seeded character_name
        assert rendered_name == character_name, \
            f"Banner name mismatch: rendered={rendered_name!r} seeded={character_name!r}"

        # Check 4: No "Preselected character could not be loaded" toast
        # Toasts render via sonner; scan the DOM for the failure copy.
        page_text = (await page.locator("body").inner_text()).lower()
        forbidden = "preselected character could not be loaded"
        assert forbidden not in page_text, \
            f"Forbidden error toast surfaced: {forbidden!r}"

        # Check 5: No auth redirect after click
        assert "/login" not in url, f"Auth redirected on click: {url}"
        assert len(auth_url_after_click) == 0, \
            f"Post-click auth redirect navigations observed: {auth_url_after_click}"

        # Check 6: No console errors
        assert errs == [], f"Console errors during click flow: {errs}"

        # Emit a clean PASS log for the human review
        print("\n" + "=" * 70)
        print("PREVIEW VERIFICATION RESULT — CTA1 'Create Series with this Character'")
        print("=" * 70)
        print(f"  ✅ URL                : {url}")
        print(f"  ✅ Create Series page : create-series-page testid rendered")
        print(f"  ✅ Banner name        : {rendered_name!r}")
        print(f"  ✅ No 'could not be loaded' toast")
        print(f"  ✅ No auth redirect")
        print(f"  ✅ No console errors  (third-party CSP noise filtered)")
        print("=" * 70)

        await context.close()
        await browser.close()
