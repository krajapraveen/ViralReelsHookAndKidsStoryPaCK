"""
Frontend regression tests for the Photo Trailer waiting experience + MySpace.

These tests do NOT create real trailers (no LLM/Nano Banana/TTS spend).
They use Playwright route interception to stub the trailer pipeline APIs
so we can land on the Progress step deterministically and assert UI.

Verifies:
1. Progress screen shows the "you can leave" copy + 3 escape-hatch buttons.
2. "Stay and play while waiting" reveals 3 lightweight widgets (riddle, quote, fact).
3. The "Go to MySpace" button navigates to /app/my-space.
4. Completed Photo Trailers show up in Profile → MySpace as YouStar Trailer cards.
"""
import os
import json
import pytest
from playwright.sync_api import sync_playwright, expect, Route

BASE_URL = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_PHOTO = "/tmp/face.jpg"


@pytest.fixture(scope="module", autouse=True)
def ensure_test_photo():
    if not os.path.exists(TEST_PHOTO):
        from PIL import Image
        Image.new("RGB", (1024, 1024), (80, 60, 200)).save(TEST_PHOTO, "JPEG")


def _login(page):
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[type="email"]', ADMIN_EMAIL)
    page.fill('input[type="password"]', ADMIN_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_timeout(2500)


def _stub_pipeline_routes(page):
    """Intercept the create-job + poll endpoints so the test reaches the
    Progress step without spending any LLM credits.
    Lets uploads/init, uploads/photo, uploads/complete pass through (these
    are cheap), but stubs POST /jobs and GET /jobs/{id} to return a fake
    PROCESSING job that never completes during the test window."""
    fake_job_id = "stub-job-ux-test"
    fake_job = {
        "_id": fake_job_id,
        "status": "PROCESSING",
        "current_stage": "WRITING_TRAILER_SCRIPT",
        "progress_percent": 35,
        "template_id": "superhero_origin",
        "template_name": "Superhero Origin",
        "duration_target_seconds": 15,
        "result_video_url": None,
        "result_thumbnail_url": None,
    }

    def handle_post_job(route: Route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"job_id": fake_job_id, "status": "QUEUED"}))

    def handle_get_job(route: Route):
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(fake_job))

    page.route("**/api/photo-trailer/jobs", lambda r: handle_post_job(r) if r.request.method == "POST" else r.continue_())
    page.route(f"**/api/photo-trailer/jobs/{fake_job_id}*", handle_get_job)


def _walk_to_progress_step(page):
    """Steps 1→4 with stubbed job kickoff. Lands on Progress step.
    Generous waits so the test stays green even when the backend is busy
    serving other suite tests in parallel."""
    page.goto(f"{BASE_URL}/app/photo-trailer", wait_until="networkidle")
    page.wait_for_timeout(2500)
    try:
        page.locator('button:has-text("Reject All")').click(timeout=1500)
    except Exception:
        pass
    _stub_pipeline_routes(page)
    page.locator('[data-testid="trailer-photo-input"]').set_input_files(TEST_PHOTO)
    # Wait until the photo grid actually shows the uploaded item rather
    # than racing on a fixed timeout.
    page.wait_for_selector('[data-testid="trailer-photo-grid"] > div', timeout=20000)
    page.wait_for_timeout(800)
    page.locator('[data-testid="trailer-consent"]').click()
    page.wait_for_timeout(400)
    page.locator('[data-testid="trailer-step1-next"]').click()
    page.wait_for_selector('[data-testid="trailer-step-characters"]', timeout=15000)
    page.locator('button:has-text("Hero")').first.click()
    page.wait_for_timeout(400)
    page.locator('button:has-text("Continue")').last.click()
    page.wait_for_selector('[data-testid="trailer-templates-grid"]', timeout=10000)
    page.locator('[data-testid="trailer-templates-grid"] > button').first.click()
    page.wait_for_timeout(400)
    page.locator('button:has-text("Generate")').first.click()
    page.wait_for_selector('[data-testid="trailer-step-progress"]', timeout=15000)


class TestProgressUXAndPlayground:
    def test_progress_shows_leave_copy_and_three_buttons(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 1100})
            page = ctx.new_page()
            try:
                _login(page)
                _walk_to_progress_step(page)
                expect(page.locator('[data-testid="trailer-step-progress"]')).to_be_visible(timeout=10000)
                leave = page.locator('[data-testid="trailer-leave-card"]')
                expect(leave).to_be_visible()
                expect(leave).to_contain_text("can leave this page")
                expect(leave).to_contain_text("Profile → MySpace")
                expect(page.locator('[data-testid="trailer-go-myspace-btn"]')).to_be_visible()
                expect(page.locator('[data-testid="trailer-explore-other-btn"]')).to_be_visible()
                expect(page.locator('[data-testid="trailer-stay-play-btn"]')).to_be_visible()
            finally:
                ctx.close()
                browser.close()

    def test_stay_and_play_reveals_riddle_quote_fact(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 1100})
            page = ctx.new_page()
            try:
                _login(page)
                _walk_to_progress_step(page)
                expect(page.locator('[data-testid="trailer-waiting-playground"]')).to_have_count(0)
                page.locator('[data-testid="trailer-stay-play-btn"]').click()
                page.wait_for_timeout(500)
                expect(page.locator('[data-testid="trailer-waiting-playground"]')).to_be_visible()
                expect(page.locator('[data-testid="waiting-riddle"]')).to_be_visible()
                expect(page.locator('[data-testid="waiting-quote"]')).to_be_visible()
                expect(page.locator('[data-testid="waiting-fact"]')).to_be_visible()
                page.locator('[data-testid="waiting-riddle-choice-0"]').click()
                page.wait_for_timeout(300)
                expect(page.locator('[data-testid="waiting-riddle-next"]')).to_be_visible()
                # Toggle hide
                page.locator('[data-testid="trailer-stay-play-btn"]').click()
                page.wait_for_timeout(400)
                expect(page.locator('[data-testid="trailer-waiting-playground"]')).to_have_count(0)
            finally:
                ctx.close()
                browser.close()

    def test_go_to_myspace_button_navigates(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            try:
                _login(page)
                _walk_to_progress_step(page)
                expect(page.locator('[data-testid="trailer-go-myspace-btn"]')).to_be_visible(timeout=10000)
                page.locator('[data-testid="trailer-go-myspace-btn"]').click()
                page.wait_for_timeout(2500)
                assert "/app/my-space" in page.url, f"unexpected url: {page.url}"
            finally:
                ctx.close()
                browser.close()


class TestMySpaceTrailerVisibility:
    def test_completed_trailer_appears_in_myspace(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            try:
                _login(page)
                page.goto(f"{BASE_URL}/app/my-space", wait_until="networkidle")
                page.wait_for_timeout(3500)
                cards = page.locator('[data-testid^="myspace-trailer-card-"]')
                count = cards.count()
                assert count >= 1, f"no YouStar trailer cards in MySpace ({count})"
                # Some completed trailers must show a Play button
                play_btns = page.locator('[data-testid^="myspace-trailer-play-"]')
                assert play_btns.count() >= 1, "no Play buttons on completed trailer cards"
                # At least one card must surface the YouStar badge
                expect(cards.first).to_contain_text("YouStar Trailer")
            finally:
                ctx.close()
                browser.close()
