"""
R2 Media Proxy CORS Tests - Iteration 366
Tests for cross-browser CORS compatibility of R2 CDN proxy endpoints.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test image path from existing story
TEST_IMAGE_PATH = "images/261430a2-28f5-4c40-bac2-35f8d275fae7/se_261430a2_thumb.jpg"


class TestR2ProxyCORS:
    """R2 Media Proxy CORS endpoint tests"""
    
    def test_options_r2_returns_cors_headers(self):
        """OPTIONS /api/media/r2/{path} returns CORS headers"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}"
        response = requests.options(url)
        
        # Should return 200 OK or 204 No Content (both valid for CORS preflight)
        assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers, "Missing Access-Control-Allow-Origin header"
        assert response.headers.get("access-control-allow-origin") == "*", "CORS origin should be *"
        
        # Check allowed methods
        allowed_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allowed_methods, "GET should be allowed"
        assert "HEAD" in allowed_methods, "HEAD should be allowed"
        assert "OPTIONS" in allowed_methods, "OPTIONS should be allowed"
        
        print(f"PASS: OPTIONS returns CORS headers: {dict(response.headers)}")
    
    def test_get_r2_image_returns_200(self):
        """GET /api/media/r2/{valid_image_path} returns 200 with Content-Type"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}"
        response = requests.get(url)
        
        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check Content-Type is image/jpeg
        content_type = response.headers.get("content-type", "")
        assert "image/jpeg" in content_type, f"Expected image/jpeg, got {content_type}"
        
        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers, "Missing CORS header on GET"
        
        # Check Accept-Ranges for video compatibility
        assert "accept-ranges" in response.headers, "Missing Accept-Ranges header"
        
        print(f"PASS: GET returns 200 with Content-Type: {content_type}")
    
    def test_head_r2_returns_metadata(self):
        """HEAD /api/media/r2/{path} returns metadata without body"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}"
        response = requests.head(url)
        
        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check Content-Length is present
        assert "content-length" in response.headers, "Missing Content-Length header"
        content_length = int(response.headers.get("content-length", 0))
        assert content_length > 0, "Content-Length should be > 0"
        
        # Check Accept-Ranges
        assert "accept-ranges" in response.headers, "Missing Accept-Ranges header"
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers, "Missing CORS header on HEAD"
        
        print(f"PASS: HEAD returns metadata, Content-Length: {content_length}")
    
    def test_get_r2_nonexistent_returns_error(self):
        """GET /api/media/r2/{nonexistent_path} returns 404 or 500"""
        url = f"{BASE_URL}/api/media/r2/nonexistent/path/image.jpg"
        response = requests.get(url)
        
        # Should return 404 Not Found or 500 (R2 may return different errors)
        assert response.status_code in [404, 500], f"Expected 404 or 500, got {response.status_code}"
        
        print(f"PASS: GET nonexistent path returns {response.status_code}")
    
    def test_range_request_support(self):
        """GET with Range header - verify Accept-Ranges is supported"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}"
        headers = {"Range": "bytes=0-1023"}
        response = requests.get(url, headers=headers)
        
        # Should return 206 Partial Content OR 200 OK (CDN may not honor range for cached content)
        assert response.status_code in [200, 206], f"Expected 200 or 206, got {response.status_code}"
        
        # Check Accept-Ranges header is present (indicates range support)
        assert "accept-ranges" in response.headers, "Missing Accept-Ranges header"
        accept_ranges = response.headers.get("accept-ranges", "")
        assert accept_ranges == "bytes", f"Expected Accept-Ranges: bytes, got {accept_ranges}"
        
        if response.status_code == 206:
            # Check Content-Range header for partial content
            assert "content-range" in response.headers, "Missing Content-Range header"
            content_range = response.headers.get("content-range", "")
            print(f"PASS: Range request returns 206 with Content-Range: {content_range}")
        else:
            # CDN returned full content - this is acceptable for images
            print(f"PASS: Range request returns 200 (CDN served full content), Accept-Ranges: {accept_ranges}")


class TestDashboardMediaLoading:
    """Tests for dashboard media loading via proxy"""
    
    def test_story_feed_returns_media_urls(self):
        """Story feed endpoint returns media URLs that can be proxied"""
        # Login first
        login_url = f"{BASE_URL}/api/auth/login"
        login_response = requests.post(login_url, json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Login failed - skipping authenticated test")
        
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get story feed
        feed_url = f"{BASE_URL}/api/engagement/story-feed"
        feed_response = requests.get(feed_url, headers=headers)
        
        assert feed_response.status_code == 200, f"Expected 200, got {feed_response.status_code}"
        
        feed_data = feed_response.json()
        
        # Check featured story has thumbnail
        featured = feed_data.get("featured_story")
        if featured:
            thumb_url = featured.get("thumbnail_url") or featured.get("thumbnail_small_url")
            if thumb_url:
                print(f"Featured story thumbnail: {thumb_url[:80]}...")
                # If it's an R2 URL, verify it can be proxied
                if "r2.dev" in thumb_url:
                    # Extract path and test proxy
                    import re
                    match = re.match(r'https?://pub-[a-f0-9]+\.r2\.dev/(.+)$', thumb_url)
                    if match:
                        proxy_url = f"{BASE_URL}/api/media/r2/{match.group(1)}"
                        proxy_response = requests.head(proxy_url)
                        assert proxy_response.status_code == 200, f"Proxy failed for {proxy_url}"
                        print(f"PASS: R2 URL proxied successfully")
        
        # Check trending stories
        trending = feed_data.get("trending_stories", [])
        print(f"Found {len(trending)} trending stories")
        
        print("PASS: Story feed returns valid media URLs")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
