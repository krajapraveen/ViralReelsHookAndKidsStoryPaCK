"""
Test Suite: Deterministic Media Pipeline - Iteration 378
Tests the Netflix-level media pipeline that generates thumbnail_small and poster_large during assembly.
Verifies Feed API returns ONLY these fields via same-origin proxy, no old fields leak.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://trust-engine-5.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestStoryFeedAPI:
    """Tests for GET /api/engagement/story-feed endpoint"""

    def test_story_feed_returns_200(self):
        """Feed API should return 200 OK"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Story feed returns 200 OK")

    def test_featured_story_has_thumbnail_small_url(self):
        """Featured story must have thumbnail_small_url field"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        featured = data.get("featured_story")
        assert featured is not None, "featured_story is missing"
        assert "thumbnail_small_url" in featured, "thumbnail_small_url field missing from featured_story"
        assert featured["thumbnail_small_url"] is not None, "thumbnail_small_url is null"
        print(f"PASS: Featured story has thumbnail_small_url: {featured['thumbnail_small_url'][:50]}...")

    def test_featured_story_has_poster_url(self):
        """Featured story must have poster_url field"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        featured = data.get("featured_story")
        assert featured is not None, "featured_story is missing"
        assert "poster_url" in featured, "poster_url field missing from featured_story"
        assert featured["poster_url"] is not None, "poster_url is null"
        print(f"PASS: Featured story has poster_url: {featured['poster_url'][:50]}...")

    def test_no_old_thumbnail_url_field_in_featured(self):
        """Old thumbnail_url field should NOT be in featured_story response"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        featured = data.get("featured_story", {})
        assert "thumbnail_url" not in featured, "OLD thumbnail_url field leaked into featured_story!"
        print("PASS: No old thumbnail_url field in featured_story")

    def test_no_scene_images_field_in_featured(self):
        """Old scene_images field should NOT be in featured_story response"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        featured = data.get("featured_story", {})
        assert "scene_images" not in featured, "OLD scene_images field leaked into featured_story!"
        print("PASS: No old scene_images field in featured_story")

    def test_trending_stories_have_thumbnail_small_url(self):
        """All trending stories must have thumbnail_small_url"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        trending = data.get("trending_stories", [])
        assert len(trending) > 0, "No trending stories returned"
        
        for i, story in enumerate(trending):
            assert "thumbnail_small_url" in story, f"trending_stories[{i}] missing thumbnail_small_url"
            assert story["thumbnail_small_url"] is not None, f"trending_stories[{i}] has null thumbnail_small_url"
        
        print(f"PASS: All {len(trending)} trending stories have thumbnail_small_url")

    def test_trending_stories_have_poster_url(self):
        """All trending stories must have poster_url"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        trending = data.get("trending_stories", [])
        assert len(trending) > 0, "No trending stories returned"
        
        for i, story in enumerate(trending):
            assert "poster_url" in story, f"trending_stories[{i}] missing poster_url"
            assert story["poster_url"] is not None, f"trending_stories[{i}] has null poster_url"
        
        print(f"PASS: All {len(trending)} trending stories have poster_url")

    def test_no_old_fields_in_trending_stories(self):
        """Old fields (thumbnail_url, scene_images) should NOT leak into trending_stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        trending = data.get("trending_stories", [])
        
        for i, story in enumerate(trending):
            assert "thumbnail_url" not in story, f"OLD thumbnail_url leaked into trending_stories[{i}]"
            assert "scene_images" not in story, f"OLD scene_images leaked into trending_stories[{i}]"
        
        print(f"PASS: No old fields leaked into {len(trending)} trending stories")

    def test_all_thumbnail_urls_are_same_origin_proxy(self):
        """All thumbnail_small_url values must start with /api/media/r2/"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        all_items = [data.get("featured_story")] if data.get("featured_story") else []
        all_items.extend(data.get("trending_stories", []))
        all_items.extend(data.get("fresh_stories", []))
        all_items.extend(data.get("continue_stories", []))
        all_items.extend(data.get("unfinished_worlds", []))
        
        bad_urls = []
        for item in all_items:
            if item and item.get("thumbnail_small_url"):
                url = item["thumbnail_small_url"]
                if not url.startswith("/api/media/r2/"):
                    bad_urls.append(f"{item.get('job_id', 'unknown')}: {url}")
        
        assert len(bad_urls) == 0, f"Found {len(bad_urls)} non-proxy thumbnail URLs: {bad_urls[:3]}"
        print(f"PASS: All {len(all_items)} items have same-origin proxy thumbnail URLs")

    def test_all_poster_urls_are_same_origin_proxy(self):
        """All poster_url values must start with /api/media/r2/"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        all_items = [data.get("featured_story")] if data.get("featured_story") else []
        all_items.extend(data.get("trending_stories", []))
        all_items.extend(data.get("fresh_stories", []))
        all_items.extend(data.get("continue_stories", []))
        all_items.extend(data.get("unfinished_worlds", []))
        
        bad_urls = []
        for item in all_items:
            if item and item.get("poster_url"):
                url = item["poster_url"]
                if not url.startswith("/api/media/r2/"):
                    bad_urls.append(f"{item.get('job_id', 'unknown')}: {url}")
        
        assert len(bad_urls) == 0, f"Found {len(bad_urls)} non-proxy poster URLs: {bad_urls[:3]}"
        print(f"PASS: All {len(all_items)} items have same-origin proxy poster URLs")


class TestMediaProxyEndpoint:
    """Tests for /api/media/r2/{path} proxy endpoint"""

    def test_image_proxy_returns_200(self):
        """Image proxy should return 200 for valid image path"""
        # Get a real image URL from the feed
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        featured = data.get("featured_story", {})
        thumb_url = featured.get("thumbnail_small_url")
        
        if thumb_url:
            full_url = f"{BASE_URL}{thumb_url}"
            img_response = requests.get(full_url)
            assert img_response.status_code == 200, f"Image proxy returned {img_response.status_code}"
            print(f"PASS: Image proxy returns 200 for {thumb_url[:50]}...")
        else:
            pytest.skip("No thumbnail URL available to test")

    def test_image_proxy_returns_correct_content_type(self):
        """Image proxy should return image/jpeg for JPEG images"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        featured = data.get("featured_story", {})
        thumb_url = featured.get("thumbnail_small_url")
        
        if thumb_url and thumb_url.endswith(('.jpg', '.jpeg', '.png')):
            full_url = f"{BASE_URL}{thumb_url}"
            img_response = requests.get(full_url)
            content_type = img_response.headers.get("Content-Type", "")
            assert "image/" in content_type, f"Expected image/* Content-Type, got {content_type}"
            print(f"PASS: Image proxy returns Content-Type: {content_type}")
        else:
            pytest.skip("No suitable image URL available to test")


class TestAuthenticatedFeed:
    """Tests for authenticated story feed (continue_stories)"""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")

    def test_authenticated_feed_returns_continue_stories(self, auth_token):
        """Authenticated feed should include continue_stories"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # continue_stories may be empty if user has no stories, but field should exist
        assert "continue_stories" in data, "continue_stories field missing from authenticated feed"
        print(f"PASS: Authenticated feed has continue_stories ({len(data.get('continue_stories', []))} items)")

    def test_continue_stories_have_proper_media_fields(self, auth_token):
        """Continue stories should have thumbnail_small_url and poster_url"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=headers)
        data = response.json()
        continue_stories = data.get("continue_stories", [])
        
        for i, story in enumerate(continue_stories):
            assert "thumbnail_small_url" in story, f"continue_stories[{i}] missing thumbnail_small_url"
            assert "poster_url" in story, f"continue_stories[{i}] missing poster_url"
        
        print(f"PASS: All {len(continue_stories)} continue_stories have proper media fields")


class TestFeedDataIntegrity:
    """Tests for feed data integrity and structure"""

    def test_feed_has_all_required_sections(self):
        """Feed should have all required sections"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        required_sections = ["featured_story", "trending_stories", "fresh_stories", "unfinished_worlds", "live_stats"]
        for section in required_sections:
            assert section in data, f"Missing required section: {section}"
        
        print(f"PASS: Feed has all required sections: {required_sections}")

    def test_story_items_have_required_fields(self):
        """Story items should have all required fields"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        required_fields = ["id", "job_id", "title", "thumbnail_small_url", "poster_url", "badge"]
        
        # Check featured story
        featured = data.get("featured_story")
        if featured:
            for field in required_fields:
                assert field in featured, f"featured_story missing field: {field}"
        
        # Check trending stories
        for i, story in enumerate(data.get("trending_stories", [])[:5]):
            for field in required_fields:
                assert field in story, f"trending_stories[{i}] missing field: {field}"
        
        print("PASS: Story items have all required fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
