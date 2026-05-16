"""
P0 Layout Regression — Character Detail Help CTAs (2026-05-18)
================================================================

Renders the live Character Detail page at four mobile-class viewports
(iPhone SE 320×568, iPhone 12 390×844, Pixel 7 412×915, iPad Mini 768×1024)
and asserts:

  1. No two CTA bounding boxes overlap
  2. No CTA escapes the help-card container horizontally
  3. No CTA escapes the help-card container vertically
  4. All three CTAs are non-zero-sized and visible
  5. No horizontal scrollbar on the page (page width ≤ viewport width)

Run with: `pytest tests/test_character_help_layout_viewports_2026_05.py`

Note on flakiness
-----------------
This test depends on the live preview environment being awake. It uses a
generous wait for hydration; if a viewport check fails because the preview
hadn't woken up, re-run once. The assertions themselves are tight and
deterministic.
"""
from __future__ import annotations

import asyncio
import os
from typing import Tuple

import pytest
from playwright.async_api import async_playwright


VIEWPORTS = [
    ("iPhone SE", 320, 568),
    ("iPhone 12", 390, 844),
    ("Pixel 7", 412, 915),
    ("iPad Mini", 768, 1024),
]


def _preview_base() -> str:
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return "http://localhost:3000"


def _rects_overlap(a, b) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


async def _login_and_open_character(page, base: str, character_id: str) -> Tuple[bool, str]:
    """Log in as admin and navigate directly to the Character Detail page
    for the supplied character_id."""
    await page.goto(f"{base}/login", wait_until="domcontentloaded", timeout=20000)
    try:
        await page.wait_for_selector('[data-testid="login-email-input"]', timeout=10000)
    except Exception as e:
        return False, f"login form not found: {e}"
    await page.fill('[data-testid="login-email-input"]', "admin@creatorstudio.ai")
    await page.fill('[data-testid="login-password-input"]', "Cr3@t0rStud!o#2026")
    await page.click('[data-testid="login-submit-btn"]')
    await page.wait_for_timeout(3500)

    await page.goto(
        f"{base}/app/characters/{character_id}",
        wait_until="networkidle",
        timeout=20000,
    )
    await page.wait_for_timeout(2000)
    try:
        await page.wait_for_selector('[data-testid="character-attach-help"]', timeout=10000)
    except Exception as e:
        return False, f"help card never rendered: {e}"
    return True, "ok"


async def _ensure_seed_character() -> str:
    """Ensure the admin user has at least one character owned. Returns its id."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv
    import uuid
    load_dotenv("/app/backend/.env")
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    try:
        admin = await db.users.find_one({"email": "admin@creatorstudio.ai"}, {"_id": 0, "id": 1})
        uid = admin["id"]
        existing = await db.character_profiles.find_one(
            {"owner_user_id": uid}, {"_id": 0, "character_id": 1}
        )
        if existing and existing.get("character_id"):
            return existing["character_id"]
        cid = f"layout-test-char-{uuid.uuid4().hex[:12]}"
        await db.character_profiles.insert_one({
            "character_id": cid,
            "owner_user_id": uid,
            "name": "Layout Test Hero",
            "personality": "brave",
            "style": "cartoon_2d",
            "voice": "narrator_warm",
        })
        return cid
    finally:
        cli.close()


@pytest.mark.asyncio
async def test_character_help_card_has_no_overlap_at_all_viewports():
    base = _preview_base()
    character_id = await _ensure_seed_character()
    failures = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for name, width, height in VIEWPORTS:
                context = await browser.new_context(viewport={"width": width, "height": height})
                page = await context.new_page()
                ok, msg = await _login_and_open_character(page, base, character_id)
                if not ok:
                    failures.append(f"{name}: bootstrap failed: {msg}")
                    await context.close()
                    continue

                # Scroll the help card into view.
                help_card = page.locator('[data-testid="character-attach-help"]')
                await help_card.scroll_into_view_if_needed(timeout=4000)
                await page.wait_for_timeout(400)

                card_box = await help_card.bounding_box()
                if card_box is None:
                    failures.append(f"{name}: help card has no bounding box")
                    await context.close()
                    continue

                cta_ids = [
                    "cta-create-series-with-character",
                    "cta-open-my-series",
                    "cta-back-to-my-characters",
                ]
                boxes = []
                for tid in cta_ids:
                    el = page.locator(f'[data-testid="{tid}"]')
                    if await el.count() != 1:
                        failures.append(f"{name}: CTA {tid} not present exactly once")
                        continue
                    if not await el.is_visible():
                        failures.append(f"{name}: CTA {tid} not visible")
                        continue
                    b = await el.bounding_box()
                    if b is None or b["width"] == 0 or b["height"] == 0:
                        failures.append(f"{name}: CTA {tid} has zero size")
                        continue
                    boxes.append((tid, b))

                # 1. No pairwise CTA overlap
                for i, (id_a, ba) in enumerate(boxes):
                    for id_b, bb in boxes[i + 1 :]:
                        if _rects_overlap(ba, bb):
                            failures.append(
                                f"{name}: CTAs {id_a} and {id_b} overlap: "
                                f"{id_a}={ba} {id_b}={bb}"
                            )

                # 2. No CTA escapes the help-card container horizontally
                for tid, b in boxes:
                    if b["x"] < card_box["x"] - 1:
                        failures.append(
                            f"{name}: CTA {tid} starts left of card "
                            f"(cta_x={b['x']:.1f} card_x={card_box['x']:.1f})"
                        )
                    if b["x"] + b["width"] > card_box["x"] + card_box["width"] + 1:
                        failures.append(
                            f"{name}: CTA {tid} extends right of card "
                            f"(cta_right={b['x'] + b['width']:.1f} "
                            f"card_right={card_box['x'] + card_box['width']:.1f})"
                        )

                # 3. No CTA escapes vertically (must sit inside card box)
                for tid, b in boxes:
                    if b["y"] < card_box["y"] - 1:
                        failures.append(f"{name}: CTA {tid} above card top")
                    if b["y"] + b["height"] > card_box["y"] + card_box["height"] + 1:
                        failures.append(
                            f"{name}: CTA {tid} bottom escapes card "
                            f"(cta_bottom={b['y'] + b['height']:.1f} "
                            f"card_bottom={card_box['y'] + card_box['height']:.1f})"
                        )

                # 4. No horizontal page overflow at this viewport
                page_scroll_w = await page.evaluate("document.documentElement.scrollWidth")
                if page_scroll_w > width + 1:
                    failures.append(
                        f"{name}: horizontal overflow — scrollWidth={page_scroll_w} viewport={width}"
                    )

                await context.close()
        finally:
            await browser.close()

    assert not failures, "Layout regressions:\n  " + "\n  ".join(failures)
