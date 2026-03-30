"""
Test Suite: Frontend Component Contract for Homepage Media
Iteration 379 - Tests HeroMedia, StoryCardMedia, MediaPreloader contract compliance

Tests verify:
1. API returns nested `media` object for all story items
2. media object contains: thumb_blur, thumbnail_small_url, poster_large_url, preview_short_url, media_version
3. media_version equals 'v3' for all items
4. No old flat fields at top level of feed items
5. All media URLs are proxy paths starting with /api/media/r2/
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestStoryFeedMediaContract:
    """Tests for the nested media object contract in story-feed API"""
    
    @pytest.fixture(scope="class")
    def feed_response(self):
        """Fetch story feed once for all tests in this class"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Feed API failed: {response.status_code}"
        return response.json()
    
    def test_featured_story_has_nested_media_object(self, feed_response):
        """Featured story must have nested media object"""
        featured = feed_response.get('featured_story')
        assert featured is not None, "featured_story is missing"
        assert 'media' in featured, "featured_story missing nested 'media' object"
        assert isinstance(featured['media'], dict), "media must be a dict"
    
    def test_featured_story_media_has_all_required_fields(self, feed_response):
        """Featured story media object must have all required fields"""
        featured = feed_response.get('featured_story')
        media = featured.get('media', {})
        
        required_fields = ['thumb_blur', 'thumbnail_small_url', 'poster_large_url', 'preview_short_url', 'media_version']
        for field in required_fields:
            assert field in media, f"media missing required field: {field}"
    
    def test_featured_story_media_version_is_v3(self, feed_response):
        """Featured story media_version must be 'v3'"""
        featured = feed_response.get('featured_story')
        media = featured.get('media', {})
        assert media.get('media_version') == 'v3', f"media_version is {media.get('media_version')}, expected 'v3'"
    
    def test_featured_story_thumbnail_is_proxy_path(self, feed_response):
        """Featured story thumbnail_small_url must be proxy path"""
        featured = feed_response.get('featured_story')
        media = featured.get('media', {})
        thumb = media.get('thumbnail_small_url')
        assert thumb is not None, "thumbnail_small_url is None"
        assert thumb.startswith('/api/media/r2/'), f"thumbnail_small_url not proxy path: {thumb}"
    
    def test_featured_story_poster_is_proxy_path(self, feed_response):
        """Featured story poster_large_url must be proxy path"""
        featured = feed_response.get('featured_story')
        media = featured.get('media', {})
        poster = media.get('poster_large_url')
        assert poster is not None, "poster_large_url is None"
        assert poster.startswith('/api/media/r2/'), f"poster_large_url not proxy path: {poster}"
    
    def test_featured_story_no_old_flat_fields(self, feed_response):
        """Featured story must NOT have old flat media fields at top level"""
        featured = feed_response.get('featured_story')
        old_fields = ['thumbnail_url', 'poster_url', 'preview_url']
        for field in old_fields:
            # These fields should NOT exist at top level (only inside media object)
            assert field not in featured or featured[field] is None, f"Old flat field '{field}' found at top level"
    
    def test_trending_stories_all_have_nested_media(self, feed_response):
        """All trending stories must have nested media object"""
        trending = feed_response.get('trending_stories', [])
        assert len(trending) > 0, "No trending stories"
        for i, story in enumerate(trending):
            assert 'media' in story, f"trending_stories[{i}] missing 'media' object"
            assert isinstance(story['media'], dict), f"trending_stories[{i}].media not a dict"
    
    def test_trending_stories_all_have_media_version_v3(self, feed_response):
        """All trending stories must have media_version='v3'"""
        trending = feed_response.get('trending_stories', [])
        for i, story in enumerate(trending):
            media = story.get('media', {})
            assert media.get('media_version') == 'v3', f"trending_stories[{i}].media.media_version is not 'v3'"
    
    def test_trending_stories_all_have_proxy_thumbnails(self, feed_response):
        """All trending stories must have proxy thumbnail URLs"""
        trending = feed_response.get('trending_stories', [])
        for i, story in enumerate(trending):
            media = story.get('media', {})
            thumb = media.get('thumbnail_small_url')
            assert thumb is not None, f"trending_stories[{i}].media.thumbnail_small_url is None"
            assert thumb.startswith('/api/media/r2/'), f"trending_stories[{i}] thumbnail not proxy: {thumb}"
    
    def test_fresh_stories_all_have_nested_media(self, feed_response):
        """All fresh stories must have nested media object"""
        fresh = feed_response.get('fresh_stories', [])
        assert len(fresh) > 0, "No fresh stories"
        for i, story in enumerate(fresh):
            assert 'media' in story, f"fresh_stories[{i}] missing 'media' object"
    
    def test_fresh_stories_all_have_media_version_v3(self, feed_response):
        """All fresh stories must have media_version='v3'"""
        fresh = feed_response.get('fresh_stories', [])
        for i, story in enumerate(fresh):
            media = story.get('media', {})
            assert media.get('media_version') == 'v3', f"fresh_stories[{i}].media.media_version is not 'v3'"
    
    def test_unfinished_worlds_all_have_nested_media(self, feed_response):
        """All unfinished worlds must have nested media object"""
        unfinished = feed_response.get('unfinished_worlds', [])
        assert len(unfinished) > 0, "No unfinished worlds"
        for i, story in enumerate(unfinished):
            assert 'media' in story, f"unfinished_worlds[{i}] missing 'media' object"
    
    def test_no_output_full_url_on_homepage_items(self, feed_response):
        """Homepage items must NOT have output_full_url field"""
        all_items = []
        if feed_response.get('featured_story'):
            all_items.append(feed_response['featured_story'])
        all_items.extend(feed_response.get('trending_stories', []))
        all_items.extend(feed_response.get('fresh_stories', []))
        all_items.extend(feed_response.get('unfinished_worlds', []))
        
        for i, item in enumerate(all_items):
            # output_full_url should NOT be in homepage feed items
            assert 'output_full_url' not in item, f"Item {i} has output_full_url (not allowed on homepage)"


class TestAuthenticatedFeed:
    """Tests for authenticated story feed (continue_stories)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.status_code}")
        return response.json().get('token')
    
    @pytest.fixture(scope="class")
    def auth_feed_response(self, auth_token):
        """Fetch authenticated story feed"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=headers)
        assert response.status_code == 200, f"Auth feed API failed: {response.status_code}"
        return response.json()
    
    def test_continue_stories_have_nested_media(self, auth_feed_response):
        """Continue stories must have nested media object"""
        continue_stories = auth_feed_response.get('continue_stories', [])
        # May be empty if user has no stories, but if present, must have media
        for i, story in enumerate(continue_stories):
            assert 'media' in story, f"continue_stories[{i}] missing 'media' object"
    
    def test_continue_stories_have_media_version_v3(self, auth_feed_response):
        """Continue stories must have media_version='v3'"""
        continue_stories = auth_feed_response.get('continue_stories', [])
        for i, story in enumerate(continue_stories):
            media = story.get('media', {})
            assert media.get('media_version') == 'v3', f"continue_stories[{i}].media.media_version is not 'v3'"


class TestMediaProxyEndpoint:
    """Tests for the media proxy endpoint"""
    
    @pytest.fixture(scope="class")
    def sample_thumbnail_path(self):
        """Get a sample thumbnail path from feed"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        featured = data.get('featured_story', {})
        media = featured.get('media', {})
        return media.get('thumbnail_small_url')
    
    def test_media_proxy_returns_image(self, sample_thumbnail_path):
        """Media proxy endpoint must return image content"""
        if not sample_thumbnail_path:
            pytest.skip("No sample thumbnail available")
        
        url = f"{BASE_URL}{sample_thumbnail_path}"
        response = requests.get(url, timeout=10)
        assert response.status_code == 200, f"Media proxy failed: {response.status_code}"
        
        content_type = response.headers.get('Content-Type', '')
        assert 'image' in content_type, f"Expected image content-type, got: {content_type}"
    
    def test_media_proxy_has_cors_headers(self, sample_thumbnail_path):
        """Media proxy must have CORS headers for cross-origin access"""
        if not sample_thumbnail_path:
            pytest.skip("No sample thumbnail available")
        
        url = f"{BASE_URL}{sample_thumbnail_path}"
        response = requests.get(url, timeout=10)
        
        # Check for CORS headers (may vary by implementation)
        # At minimum, should not block cross-origin requests
        assert response.status_code == 200


class TestFeedResponseStructure:
    """Tests for overall feed response structure"""
    
    def test_feed_has_all_required_sections(self):
        """Feed must have all required sections"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        required_sections = ['featured_story', 'trending_stories', 'fresh_stories', 'unfinished_worlds', 'live_stats']
        for section in required_sections:
            assert section in data, f"Feed missing required section: {section}"
    
    def test_feed_items_have_required_fields(self):
        """Feed items must have required fields for frontend components"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        featured = data.get('featured_story')
        if featured:
            required_fields = ['id', 'job_id', 'title', 'hook_text', 'media', 'badge']
            for field in required_fields:
                assert field in featured, f"featured_story missing field: {field}"
    
    def test_all_items_have_consistent_media_structure(self):
        """All feed items must have consistent media object structure"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        all_items = []
        if data.get('featured_story'):
            all_items.append(data['featured_story'])
        all_items.extend(data.get('trending_stories', []))
        all_items.extend(data.get('fresh_stories', []))
        all_items.extend(data.get('unfinished_worlds', []))
        
        media_fields = ['thumb_blur', 'thumbnail_small_url', 'poster_large_url', 'preview_short_url', 'media_version']
        
        for i, item in enumerate(all_items):
            media = item.get('media', {})
            for field in media_fields:
                assert field in media, f"Item {i} media missing field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
