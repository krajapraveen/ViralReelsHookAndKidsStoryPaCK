"""
Test Suite: Same-Origin Proxy Routing for Dashboard Images (Iteration 373)

Tests that ALL homepage images route through the same-origin backend proxy
(/api/media/r2/{key}?w=480&q=80) instead of direct R2 CDN URLs.

This fixes Safari/Mobile CORS/ORB blocking issues.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestStoryFeedProxyURLs:
    """Verify /api/engagement/story-feed returns proxy URLs, NOT direct R2 CDN URLs"""

    def test_story_feed_returns_data(self):
        """Basic connectivity test"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        assert 'featured_story' in data
        assert 'trending_stories' in data
        print(f"✓ Story feed returned {len(data.get('trending_stories', []))} trending stories")

    def test_featured_story_uses_proxy_urls(self):
        """Featured story poster_url and thumbnail_small_url must be proxy paths"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        featured = data.get('featured_story')
        if featured:
            poster_url = featured.get('poster_url', '')
            thumb_url = featured.get('thumbnail_small_url', '')
            
            # Must start with /api/media/r2/
            assert poster_url.startswith('/api/media/r2/'), f"poster_url should be proxy path, got: {poster_url}"
            assert thumb_url.startswith('/api/media/r2/'), f"thumbnail_small_url should be proxy path, got: {thumb_url}"
            
            # Must NOT contain direct R2 CDN domain
            assert 'r2.dev' not in poster_url, f"poster_url should NOT contain r2.dev: {poster_url}"
            assert 'r2.dev' not in thumb_url, f"thumbnail_small_url should NOT contain r2.dev: {thumb_url}"
            
            print(f"✓ Featured story uses proxy URLs")
            print(f"  poster_url: {poster_url[:60]}...")
            print(f"  thumbnail_small_url: {thumb_url[:60]}...")
        else:
            pytest.skip("No featured story available")

    def test_trending_stories_use_proxy_urls(self):
        """All trending stories must use proxy URLs"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        trending = data.get('trending_stories', [])
        assert len(trending) > 0, "No trending stories found"
        
        direct_r2_count = 0
        proxy_count = 0
        
        for story in trending:
            poster = story.get('poster_url', '')
            thumb = story.get('thumbnail_small_url', '')
            
            for url in [poster, thumb]:
                if url:
                    if 'r2.dev' in url:
                        direct_r2_count += 1
                        print(f"✗ Direct R2 URL found: {url[:80]}")
                    elif url.startswith('/api/media/r2/'):
                        proxy_count += 1
        
        assert direct_r2_count == 0, f"Found {direct_r2_count} direct R2 CDN URLs (should be 0)"
        print(f"✓ All {proxy_count} trending story URLs use proxy paths")

    def test_fresh_stories_use_proxy_urls(self):
        """All fresh stories must use proxy URLs"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        fresh = data.get('fresh_stories', [])
        
        for story in fresh:
            poster = story.get('poster_url', '')
            thumb = story.get('thumbnail_small_url', '')
            
            for url in [poster, thumb]:
                if url:
                    assert 'r2.dev' not in url, f"Direct R2 URL found: {url}"
                    assert url.startswith('/api/media/r2/'), f"URL should be proxy path: {url}"
        
        print(f"✓ All {len(fresh)} fresh stories use proxy URLs")

    def test_proxy_urls_include_resize_params(self):
        """Proxy URLs must include resize params (?w=480&q=80 for cards, ?w=1200&q=85 for posters)"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        featured = data.get('featured_story', {})
        trending = data.get('trending_stories', [])
        
        # Check poster URLs have w=1200&q=85
        if featured:
            poster = featured.get('poster_url', '')
            assert 'w=1200' in poster, f"Poster URL missing w=1200: {poster}"
            assert 'q=85' in poster, f"Poster URL missing q=85: {poster}"
        
        # Check thumbnail URLs have w=480&q=80
        for story in trending[:5]:
            thumb = story.get('thumbnail_small_url', '')
            if thumb:
                assert 'w=480' in thumb, f"Thumbnail URL missing w=480: {thumb}"
                assert 'q=80' in thumb, f"Thumbnail URL missing q=80: {thumb}"
        
        print("✓ Proxy URLs include correct resize params")

    def test_no_direct_r2_urls_in_entire_feed(self):
        """Comprehensive check: NO direct R2 CDN URLs anywhere in the feed"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        # Collect all URLs from all sections
        all_urls = []
        
        # Featured story
        fs = data.get('featured_story', {})
        if fs:
            all_urls.extend([fs.get('poster_url'), fs.get('thumbnail_small_url'), 
                           fs.get('thumbnail_url'), fs.get('preview_url'), fs.get('output_url')])
        
        # All story arrays
        for section in ['trending_stories', 'fresh_stories', 'continue_stories', 'unfinished_worlds']:
            for story in data.get(section, []):
                all_urls.extend([story.get('poster_url'), story.get('thumbnail_small_url'),
                               story.get('thumbnail_url'), story.get('preview_url'), story.get('output_url')])
        
        # Filter out None values
        all_urls = [u for u in all_urls if u]
        
        # Check for direct R2 CDN URLs
        direct_r2 = [u for u in all_urls if 'r2.dev' in u or 'r2.cloudflarestorage.com' in u]
        proxy_urls = [u for u in all_urls if u.startswith('/api/media/r2/')]
        
        print(f"Total URLs checked: {len(all_urls)}")
        print(f"Proxy URLs (GOOD): {len(proxy_urls)}")
        print(f"Direct R2 URLs (BAD): {len(direct_r2)}")
        
        assert len(direct_r2) == 0, f"Found {len(direct_r2)} direct R2 CDN URLs: {direct_r2[:3]}"
        print("✓ No direct R2 CDN URLs found in entire feed")


class TestMediaProxyEndpoint:
    """Verify /api/media/r2/{path} proxy endpoint works correctly"""

    def test_proxy_returns_200_for_valid_image(self):
        """Proxy should return HTTP 200 for valid image keys"""
        # First get a valid image key from the feed
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        featured = data.get('featured_story', {})
        thumb_url = featured.get('thumbnail_small_url', '')
        
        if not thumb_url:
            pytest.skip("No thumbnail URL available")
        
        # Request the proxy URL
        full_url = f"{BASE_URL}{thumb_url}"
        img_response = requests.get(full_url, timeout=10)
        
        assert img_response.status_code == 200, f"Proxy returned {img_response.status_code} for {thumb_url}"
        print(f"✓ Proxy returned HTTP 200 for: {thumb_url[:60]}...")

    def test_proxy_returns_correct_content_type(self):
        """Proxy should return Content-Type: image/jpeg"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        featured = data.get('featured_story', {})
        thumb_url = featured.get('thumbnail_small_url', '')
        
        if not thumb_url:
            pytest.skip("No thumbnail URL available")
        
        full_url = f"{BASE_URL}{thumb_url}"
        img_response = requests.get(full_url, timeout=10)
        
        content_type = img_response.headers.get('Content-Type', '')
        assert 'image/' in content_type, f"Expected image content type, got: {content_type}"
        print(f"✓ Proxy returned Content-Type: {content_type}")

    def test_proxy_returns_cors_headers(self):
        """Proxy should return Access-Control-Allow-Origin: *"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        featured = data.get('featured_story', {})
        thumb_url = featured.get('thumbnail_small_url', '')
        
        if not thumb_url:
            pytest.skip("No thumbnail URL available")
        
        full_url = f"{BASE_URL}{thumb_url}"
        img_response = requests.get(full_url, timeout=10)
        
        cors_header = img_response.headers.get('Access-Control-Allow-Origin', '')
        assert cors_header == '*', f"Expected CORS header '*', got: {cors_header}"
        print(f"✓ Proxy returned Access-Control-Allow-Origin: {cors_header}")

    def test_proxy_options_preflight(self):
        """Proxy should handle OPTIONS preflight requests"""
        # Get a valid path
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        featured = data.get('featured_story', {})
        thumb_url = featured.get('thumbnail_small_url', '')
        
        if not thumb_url:
            pytest.skip("No thumbnail URL available")
        
        full_url = f"{BASE_URL}{thumb_url}"
        options_response = requests.options(full_url, timeout=10)
        
        # Should return 200 or 204 for preflight
        assert options_response.status_code in [200, 204], f"OPTIONS returned {options_response.status_code}"
        
        # Should have CORS headers
        cors_origin = options_response.headers.get('Access-Control-Allow-Origin', '')
        cors_methods = options_response.headers.get('Access-Control-Allow-Methods', '')
        
        assert cors_origin == '*', f"Missing CORS origin header"
        assert 'GET' in cors_methods, f"Missing GET in allowed methods: {cors_methods}"
        print(f"✓ OPTIONS preflight works correctly")

    def test_multiple_proxy_urls_return_200(self):
        """Test multiple proxy URLs from the feed"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        data = response.json()
        
        trending = data.get('trending_stories', [])[:5]
        
        success_count = 0
        fail_count = 0
        
        for story in trending:
            thumb_url = story.get('thumbnail_small_url', '')
            if thumb_url and thumb_url.startswith('/api/media/r2/'):
                full_url = f"{BASE_URL}{thumb_url}"
                try:
                    img_response = requests.get(full_url, timeout=10)
                    if img_response.status_code == 200:
                        success_count += 1
                    else:
                        fail_count += 1
                        print(f"✗ Failed: {thumb_url[:60]}... -> {img_response.status_code}")
                except Exception as e:
                    fail_count += 1
                    print(f"✗ Error: {thumb_url[:60]}... -> {e}")
        
        print(f"✓ {success_count}/{success_count + fail_count} proxy URLs returned HTTP 200")
        assert fail_count == 0, f"{fail_count} proxy URLs failed"


class TestExploreEndpointProxyURLs:
    """Verify /api/engagement/explore also uses proxy URLs"""

    def test_explore_uses_proxy_urls(self):
        """Explore endpoint should also return proxy URLs"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        assert response.status_code == 200
        data = response.json()
        
        stories = data.get('stories', [])
        
        direct_r2_count = 0
        proxy_count = 0
        
        for story in stories:
            thumb = story.get('thumbnail_url', '')
            if thumb:
                if 'r2.dev' in thumb:
                    direct_r2_count += 1
                elif thumb.startswith('/api/media/r2/'):
                    proxy_count += 1
        
        print(f"Explore: {proxy_count} proxy URLs, {direct_r2_count} direct R2 URLs")
        assert direct_r2_count == 0, f"Found {direct_r2_count} direct R2 URLs in explore"
        print(f"✓ Explore endpoint uses proxy URLs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
