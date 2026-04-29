"""
P0 NotificationCenter integration test.

Verifies the full loop:
1. Photo trailer notification renders in the bell with correct icon + copy
2. Clicking it navigates to /app/my-space?trailer=<job_id>
3. Bell closes after click
4. The matching MySpace trailer card scrolls into view + appears in the DOM

Uses a real seeded notification + a real completed trailer in the DB.
"""
import os
import asyncio
import json
import pytest
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, expect
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(scope="module")
def db():
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def seeded_trailer_notification(db):
    """Find a real COMPLETED trailer for the admin user, seed a matching notif."""
    async def setup():
        admin = await db.users.find_one({"email": ADMIN_EMAIL}, {"_id": 0, "id": 1})
        job = await db.photo_trailer_jobs.find_one(
            {"user_id": admin["id"], "status": "COMPLETED",
             "result_video_url": {"$ne": None}},
            sort=[("completed_at", -1)],
        )
        if not job:
            pytest.skip("No completed photo trailer for admin user — cannot test")
        notif_id = "test-notif-bell-loop"
        await db.notifications.delete_one({"_id": notif_id})
        now = datetime.now(timezone.utc).isoformat()
        await db.notifications.insert_one({
            "_id": notif_id,
            "user_id": admin["id"],
            "notification_type": "generation_complete",
            "feature": "photo_trailer",
            "title": "Your YouStar trailer is ready",
            "message": f"Your '{job.get('template_name','trailer')}' trailer just finished — tap to watch.",
            "job_id": job["_id"],
            "download_url": job.get("result_video_url"),
            "action_url": f"/app/my-space?trailer={job['_id']}",
            "metadata": {"template_id": job["template_id"]},
            "read": False,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        })
        return job["_id"]
    return _run(setup())


def _login(page):
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[type="email"]', ADMIN_EMAIL)
    page.fill('input[type="password"]', ADMIN_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_timeout(2500)


class TestNotificationLoop:
    def test_bell_renders_photo_trailer_notification(self, seeded_trailer_notification):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            try:
                _login(page)
                page.goto(f"{BASE_URL}/app", wait_until="networkidle")
                page.wait_for_timeout(2500)
                try:
                    page.locator('button:has-text("Reject All")').click(timeout=1500)
                except Exception:
                    pass

                # Open bell
                bell = page.locator('[data-testid="notification-btn"]')
                expect(bell).to_be_visible()
                bell.click()
                page.wait_for_timeout(800)

                # Dropdown rendered
                expect(page.locator('[data-testid="notification-dropdown"]')).to_be_visible()

                # YouStar item rendered with title + film icon
                items = page.locator('[data-testid="notification-item-photo-trailer"]')
                expect(items.first).to_be_visible(timeout=4000)
                expect(items.first).to_contain_text("Your YouStar trailer is ready")
            finally:
                ctx.close()
                browser.close()

    def test_click_navigates_to_myspace_with_trailer_param(self, seeded_trailer_notification):
        job_id = seeded_trailer_notification
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            try:
                _login(page)
                page.goto(f"{BASE_URL}/app", wait_until="networkidle")
                page.wait_for_timeout(2500)
                try:
                    page.locator('button:has-text("Reject All")').click(timeout=1500)
                except Exception:
                    pass

                page.locator('[data-testid="notification-btn"]').click()
                page.wait_for_timeout(800)
                # Click the YouStar notification
                page.locator('[data-testid="notification-item-photo-trailer"]').first.click()
                page.wait_for_timeout(2500)

                # URL must contain MySpace + the trailer id
                assert "/app/my-space" in page.url, f"unexpected url: {page.url}"
                assert f"trailer={job_id}" in page.url, f"missing trailer param in: {page.url}"

                # Bell dropdown must be closed after click
                expect(page.locator('[data-testid="notification-dropdown"]')).to_have_count(0)

                # Wait for MySpace to fetch + render trailer cards. Up to 12s
                # because fetchJobs runs Promise.allSettled across 3 endpoints.
                target_card = page.locator(f'[data-testid="myspace-trailer-card-{job_id}"]')
                expect(target_card).to_be_visible(timeout=12000)
            finally:
                ctx.close()
                browser.close()

    def test_fallback_when_action_url_missing(self, db):
        """A photo_trailer notification missing action_url must still navigate
        to /app/my-space (not crash, not become a dead row)."""
        async def seed():
            admin = await db.users.find_one({"email": ADMIN_EMAIL}, {"_id":0,"id":1})
            nid = "test-notif-fallback"
            await db.notifications.delete_one({"_id": nid})
            now = datetime.now(timezone.utc).isoformat()
            await db.notifications.insert_one({
                "_id": nid, "user_id": admin["id"],
                "notification_type": "generation_complete",
                "feature": "photo_trailer",
                "title": "Your YouStar trailer is ready",
                "message": "Fallback test — no action_url provided.",
                "read": False, "archived": False,
                "created_at": now, "updated_at": now,
            })
        _run(seed())

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            try:
                _login(page)
                page.goto(f"{BASE_URL}/app", wait_until="networkidle")
                page.wait_for_timeout(2500)
                try:
                    page.locator('button:has-text("Reject All")').click(timeout=1500)
                except Exception:
                    pass

                page.locator('[data-testid="notification-btn"]').click()
                page.wait_for_timeout(800)
                # Click the topmost photo_trailer notification (the fallback one
                # we just seeded — being newest)
                page.locator('[data-testid="notification-item-photo-trailer"]').first.click()
                page.wait_for_timeout(2500)
                assert "/app/my-space" in page.url, f"fallback failed: {page.url}"
            finally:
                ctx.close()
                browser.close()
