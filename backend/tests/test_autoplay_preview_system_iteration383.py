"""
Test Suite: Netflix-grade Autoplay Preview System with Blurhash
Iteration 383 - Tests for:
1. Blurhash blur placeholders (thumb_blur with inline_base64)
2. Feed API returns proper media structure (CDN paths, thumb_blur)
3. Preview event tracking endpoint
4. Backfill blur status and sync endpoints
5. CDN base URL in feed response
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_token(api_client):
    """Get test user authentication token."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code}")


class TestStoryFeedMediaStructure:
    """Tests for story-feed API media structure and CDN integration."""

    def test_story_feed_returns_200(self, api_client, test_user_token):
        """GET /api/engagement/story-feed returns 200."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: story-feed returns 200")

    def test_story_feed_has_cdn_base(self, api_client, test_user_token):
        """Feed API returns cdn_base URL for frontend CDN resolution."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        assert "cdn_base" in data, "cdn_base missing from response"
        cdn_base = data["cdn_base"]
        # CDN base should be R2 public URL
        assert cdn_base and "r2.dev" in cdn_base, f"cdn_base should contain r2.dev, got: {cdn_base}"
        print(f"PASS: cdn_base = {cdn_base}")

    def test_story_feed_has_hero_with_media(self, api_client, test_user_token):
        """Hero section has proper media structure."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        hero = data.get("hero")
        
        if hero:
            media = hero.get("media", {})
            # Check media structure exists
            assert "thumbnail_small_url" in media or "poster_large_url" in media, \
                "Hero media should have thumbnail_small_url or poster_large_url"
            print(f"PASS: Hero has media structure: {list(media.keys())}")
        else:
            print("INFO: No hero in response (cold start)")

    def test_story_feed_rows_have_media(self, api_client, test_user_token):
        """Story rows contain stories with proper media structure."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        rows = data.get("rows", [])
        
        assert len(rows) > 0, "Feed should have at least one row"
        
        stories_with_media = 0
        stories_with_blur = 0
        
        for row in rows:
            for story in row.get("stories", []):
                media = story.get("media", {})
                if media.get("thumbnail_small_url") or media.get("poster_large_url"):
                    stories_with_media += 1
                if media.get("thumb_blur"):
                    stories_with_blur += 1
        
        print(f"PASS: Found {stories_with_media} stories with media, {stories_with_blur} with thumb_blur")
        assert stories_with_media > 0, "At least some stories should have media"

    def test_thumb_blur_structure(self, api_client, test_user_token):
        """thumb_blur has correct inline_base64 structure."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        
        # Find a story with thumb_blur
        thumb_blur_found = None
        for row in data.get("rows", []):
            for story in row.get("stories", []):
                media = story.get("media", {})
                if media.get("thumb_blur"):
                    thumb_blur_found = media["thumb_blur"]
                    break
            if thumb_blur_found:
                break
        
        if thumb_blur_found:
            assert thumb_blur_found.get("type") == "inline_base64", \
                f"thumb_blur type should be inline_base64, got: {thumb_blur_found.get('type')}"
            value = thumb_blur_found.get("value", "")
            assert value.startswith("data:image/jpeg;base64,"), \
                f"thumb_blur value should be data URL, got: {value[:50]}..."
            print(f"PASS: thumb_blur has correct structure (type=inline_base64, value starts with data:image/jpeg;base64)")
        else:
            print("INFO: No thumb_blur found in feed (backfill may be needed)")

    def test_media_urls_are_proxy_paths(self, api_client, test_user_token):
        """Media URLs should be proxy paths (/api/media/r2/...) not direct CDN."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        
        proxy_paths = 0
        cdn_paths = 0
        
        for row in data.get("rows", []):
            for story in row.get("stories", []):
                media = story.get("media", {})
                for key in ["thumbnail_small_url", "poster_large_url", "preview_short_url"]:
                    url = media.get(key)
                    if url:
                        if url.startswith("/api/media/r2/"):
                            proxy_paths += 1
                        elif "r2.dev" in url:
                            cdn_paths += 1
        
        print(f"PASS: Found {proxy_paths} proxy paths, {cdn_paths} CDN paths")
        # Backend should return proxy paths, frontend resolves to CDN
        assert proxy_paths > 0 or cdn_paths == 0, "Backend should return proxy paths"


class TestPreviewEventTracking:
    """Tests for preview autoplay analytics tracking."""

    def test_preview_event_endpoint_exists(self, api_client, test_user_token):
        """POST /api/engagement/preview-event accepts events."""
        response = api_client.post(
            f"{BASE_URL}/api/engagement/preview-event",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "job_id": "test-job-123",
                "event_type": "preview_impression",
                "surface": "card"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=true, got: {data}"
        print("PASS: preview-event endpoint accepts impression events")

    def test_preview_play_event(self, api_client, test_user_token):
        """Track preview_play event."""
        response = api_client.post(
            f"{BASE_URL}/api/engagement/preview-event",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "job_id": "test-job-456",
                "event_type": "preview_play",
                "surface": "hero"
            }
        )
        assert response.status_code == 200
        assert response.json().get("success") == True
        print("PASS: preview_play event tracked")

    def test_preview_watch_complete_event(self, api_client, test_user_token):
        """Track preview_watch_complete event with watch_time."""
        response = api_client.post(
            f"{BASE_URL}/api/engagement/preview-event",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "job_id": "test-job-789",
                "event_type": "preview_watch_complete",
                "watch_time": 3.5,
                "surface": "card"
            }
        )
        assert response.status_code == 200
        assert response.json().get("success") == True
        print("PASS: preview_watch_complete event tracked with watch_time")

    def test_preview_click_event(self, api_client, test_user_token):
        """Track preview_click conversion event."""
        response = api_client.post(
            f"{BASE_URL}/api/engagement/preview-event",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "job_id": "test-job-abc",
                "event_type": "preview_click"
            }
        )
        assert response.status_code == 200
        assert response.json().get("success") == True
        print("PASS: preview_click event tracked")

    def test_preview_event_anonymous(self, api_client):
        """Preview events work for anonymous users."""
        response = api_client.post(
            f"{BASE_URL}/api/engagement/preview-event",
            json={
                "job_id": "test-job-anon",
                "event_type": "preview_impression"
            }
        )
        assert response.status_code == 200
        assert response.json().get("success") == True
        print("PASS: preview events work for anonymous users")


class TestBackfillBlurEndpoints:
    """Tests for admin backfill blur endpoints."""

    def test_backfill_status_requires_admin(self, api_client, test_user_token):
        """GET /api/admin/backfill/thumb-blur/status requires admin."""
        response = api_client.get(
            f"{BASE_URL}/api/admin/backfill/thumb-blur/status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        # Should return error for non-admin
        data = response.json()
        assert data.get("error") == "Admin access required" or response.status_code == 403, \
            f"Expected admin error, got: {data}"
        print("PASS: backfill status requires admin access")

    def test_backfill_status_admin_access(self, api_client, admin_token):
        """Admin can access backfill status."""
        response = api_client.get(
            f"{BASE_URL}/api/admin/backfill/thumb-blur/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check response structure
        assert "missing" in data, "Response should have 'missing' counts"
        assert "done" in data, "Response should have 'done' counts"
        
        missing = data["missing"]
        done = data["done"]
        
        assert "total" in missing, "missing should have total"
        assert "total" in done, "done should have total"
        
        print(f"PASS: Backfill status - Missing: {missing['total']}, Done: {done['total']}")

    def test_backfill_sync_requires_admin(self, api_client, test_user_token):
        """POST /api/admin/backfill/thumb-blur/sync requires admin."""
        response = api_client.post(
            f"{BASE_URL}/api/admin/backfill/thumb-blur/sync?batch_size=1",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        assert data.get("error") == "Admin access required" or response.status_code == 403, \
            f"Expected admin error, got: {data}"
        print("PASS: backfill sync requires admin access")

    def test_backfill_sync_admin_can_run(self, api_client, admin_token):
        """Admin can run backfill sync (small batch)."""
        response = api_client.post(
            f"{BASE_URL}/api/admin/backfill/thumb-blur/sync?batch_size=2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check response structure
        assert "processed" in data, "Response should have 'processed' count"
        assert "success" in data, "Response should have 'success' count"
        
        print(f"PASS: Backfill sync ran - Processed: {data['processed']}, Success: {data['success']}")


class TestFeedAPIContract:
    """Tests for the complete feed API contract."""

    def test_feed_has_personalization_object(self, api_client, test_user_token):
        """Feed returns personalization metadata."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        
        assert "personalization" in data, "Feed should have personalization object"
        p = data["personalization"]
        assert "enabled" in p, "personalization should have enabled flag"
        assert "profile_strength" in p, "personalization should have profile_strength"
        assert "event_count" in p, "personalization should have event_count"
        print(f"PASS: Personalization - enabled={p['enabled']}, strength={p['profile_strength']}, events={p['event_count']}")

    def test_feed_has_rows_array(self, api_client, test_user_token):
        """Feed returns rows array with proper structure."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        
        assert "rows" in data, "Feed should have rows array"
        rows = data["rows"]
        assert isinstance(rows, list), "rows should be a list"
        
        if rows:
            row = rows[0]
            assert "key" in row, "Row should have key"
            assert "title" in row, "Row should have title"
            assert "stories" in row, "Row should have stories"
            print(f"PASS: Feed has {len(rows)} rows, first row: {row['key']}")
        else:
            print("INFO: Feed has empty rows (cold start)")

    def test_feed_has_features_array(self, api_client, test_user_token):
        """Feed returns features array."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        
        assert "features" in data, "Feed should have features array"
        features = data["features"]
        assert isinstance(features, list), "features should be a list"
        assert len(features) > 0, "features should not be empty"
        
        f = features[0]
        assert "name" in f, "Feature should have name"
        assert "key" in f, "Feature should have key"
        print(f"PASS: Feed has {len(features)} features, top feature: {f['key']}")

    def test_feed_has_live_stats(self, api_client, test_user_token):
        """Feed returns live_stats."""
        response = api_client.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        data = response.json()
        
        assert "live_stats" in data, "Feed should have live_stats"
        stats = data["live_stats"]
        assert "stories_today" in stats, "live_stats should have stories_today"
        assert "total_stories" in stats, "live_stats should have total_stories"
        print(f"PASS: live_stats - today={stats['stories_today']}, total={stats['total_stories']}")


class TestAnonymousFeed:
    """Tests for anonymous user feed access."""

    def test_anonymous_feed_works(self, api_client):
        """Anonymous users can access story feed."""
        response = api_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should have basic structure
        assert "rows" in data, "Anonymous feed should have rows"
        assert "features" in data, "Anonymous feed should have features"
        assert "cdn_base" in data, "Anonymous feed should have cdn_base"
        print("PASS: Anonymous feed works")

    def test_anonymous_personalization_disabled(self, api_client):
        """Anonymous users have personalization disabled."""
        response = api_client.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        p = data.get("personalization", {})
        assert p.get("enabled") == False, f"Anonymous personalization should be disabled, got: {p}"
        print("PASS: Anonymous personalization is disabled")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
