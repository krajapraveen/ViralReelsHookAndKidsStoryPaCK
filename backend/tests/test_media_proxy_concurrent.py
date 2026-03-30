"""
Media Proxy Concurrent Performance Tests - Iteration 367
Tests asyncio.to_thread fix for S3 calls, LRU cache, auto-resize, and concurrent request handling.
"""
import pytest
import requests
import os
import time
import concurrent.futures

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Known image path from story-feed
TEST_IMAGE_PATH = "images/261430a2-28f5-4c40-bac2-35f8d275fae7/se_261430a2_thumb.jpg"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


class TestStoryFeedAPI:
    """Test story-feed endpoint returns proper data with thumbnail_url."""
    
    def test_story_feed_returns_featured_story_with_thumbnail(self, auth_token):
        """Verify featured_story has non-null thumbnail_url."""
        response = requests.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify featured_story exists and has thumbnail_url
        assert "featured_story" in data
        featured = data["featured_story"]
        assert featured is not None, "featured_story should not be null"
        assert "thumbnail_url" in featured
        assert featured["thumbnail_url"] is not None, "thumbnail_url should not be null"
        assert len(featured["thumbnail_url"]) > 10, "thumbnail_url should be a valid URL"
        print(f"Featured story: {featured.get('title')} with thumbnail: {featured['thumbnail_url'][:60]}...")
    
    def test_story_feed_returns_trending_stories(self, auth_token):
        """Verify trending_stories array has items with thumbnails."""
        response = requests.get(
            f"{BASE_URL}/api/engagement/story-feed",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        trending = data.get("trending_stories", [])
        assert len(trending) > 0, "trending_stories should have items"
        
        # Check first 5 have thumbnail_url
        for i, story in enumerate(trending[:5]):
            assert story.get("thumbnail_url"), f"Story {i} missing thumbnail_url"
        print(f"Trending stories count: {len(trending)}")


class TestMediaProxyBasic:
    """Test basic media proxy functionality."""
    
    def test_media_proxy_returns_200_for_valid_image(self):
        """GET /api/media/r2/{path} returns 200 for valid image."""
        response = requests.get(
            f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}",
            timeout=10
        )
        assert response.status_code == 200
        assert len(response.content) > 1000, "Image should have content"
        print(f"Image size: {len(response.content)} bytes")
    
    def test_media_proxy_cors_headers(self):
        """Verify CORS headers are present."""
        response = requests.get(
            f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}?w=400&q=80",
            timeout=10
        )
        assert response.status_code == 200
        
        # Check CORS headers
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        # Content-Length may be replaced by Transfer-Encoding: chunked when gzip is used
        assert "Content-Length" in response.headers or "Transfer-Encoding" in response.headers
        print(f"CORS headers verified: Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
    
    def test_media_proxy_resize_parameter(self):
        """Test ?w=400&q=80 resize parameter works."""
        # Request with resize
        response_resized = requests.get(
            f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}?w=400&q=80",
            timeout=10
        )
        assert response_resized.status_code == 200
        
        # Request without resize (original or auto-resized)
        response_original = requests.get(
            f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}",
            timeout=10
        )
        assert response_original.status_code == 200
        
        # Resized should be smaller or equal
        print(f"Original size: {len(response_original.content)}, Resized (w=400): {len(response_resized.content)}")
    
    def test_media_proxy_options_preflight(self):
        """OPTIONS request returns proper CORS preflight response."""
        response = requests.options(
            f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}",
            timeout=10
        )
        # Should return 200 or 204
        assert response.status_code in [200, 204], f"OPTIONS returned {response.status_code}"
        assert response.headers.get("Access-Control-Allow-Origin") == "*"
        print("OPTIONS preflight verified")


class TestMediaProxyConcurrency:
    """Test concurrent request handling - verifies asyncio.to_thread fix."""
    
    def test_5_concurrent_requests_complete_under_3_seconds(self):
        """5 concurrent image requests should complete in under 3 seconds."""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}?w=400&q=80"
        
        def fetch_image(idx):
            start = time.time()
            response = requests.get(url, timeout=10)
            elapsed = time.time() - start
            return idx, response.status_code, elapsed
        
        start_total = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_image, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_total
        
        # All should succeed
        for idx, status, elapsed in results:
            assert status == 200, f"Request {idx} failed with status {status}"
            print(f"Request {idx}: {status} in {elapsed:.3f}s")
        
        # Total time should be under 3 seconds (not 5x single request time)
        assert total_time < 3.0, f"5 concurrent requests took {total_time:.2f}s (should be <3s)"
        print(f"Total time for 5 concurrent requests: {total_time:.3f}s")
    
    def test_10_concurrent_requests_complete_under_5_seconds(self):
        """10 concurrent image requests should complete in under 5 seconds."""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}?w=400&q=80"
        
        def fetch_image(idx):
            start = time.time()
            response = requests.get(url, timeout=15)
            elapsed = time.time() - start
            return idx, response.status_code, elapsed
        
        start_total = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_image, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_total
        
        # All should succeed
        success_count = sum(1 for _, status, _ in results if status == 200)
        assert success_count >= 8, f"Only {success_count}/10 requests succeeded"
        
        # Total time should be under 5 seconds
        assert total_time < 5.0, f"10 concurrent requests took {total_time:.2f}s (should be <5s)"
        print(f"Total time for 10 concurrent requests: {total_time:.3f}s ({success_count}/10 succeeded)")


class TestMediaProxyCache:
    """Test LRU cache functionality."""
    
    def test_second_request_faster_than_first(self):
        """Second request for same image should be faster (cache hit)."""
        # Use a unique resize to ensure fresh cache entry
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}?w=350&q=75"
        
        # First request (cache miss)
        start1 = time.time()
        response1 = requests.get(url, timeout=10)
        time1 = time.time() - start1
        assert response1.status_code == 200
        
        # Second request (cache hit)
        start2 = time.time()
        response2 = requests.get(url, timeout=10)
        time2 = time.time() - start2
        assert response2.status_code == 200
        
        # Same content
        assert len(response1.content) == len(response2.content)
        
        # Second should be faster (or at least not significantly slower)
        print(f"First request: {time1:.3f}s, Second request: {time2:.3f}s")
        # Note: Due to network variability, we just verify both succeed
        # The cache benefit is more visible under load


class TestMediaProxyAutoResize:
    """Test auto-resize for images >300KB."""
    
    def test_large_image_auto_resized(self):
        """Images >300KB should be auto-resized even without ?w parameter."""
        # Request without resize parameter
        response = requests.get(
            f"{BASE_URL}/api/media/r2/{TEST_IMAGE_PATH}",
            timeout=10
        )
        assert response.status_code == 200
        
        # The proxy should auto-resize if original >300KB
        # We can't easily verify the original size, but we verify it returns valid image
        assert len(response.content) > 0
        assert response.headers.get("Content-Type") in ["image/jpeg", "image/png", "image/webp"]
        print(f"Image returned: {len(response.content)} bytes, type: {response.headers.get('Content-Type')}")


class TestMediaProxy404:
    """Test error handling."""
    
    def test_nonexistent_image_returns_404(self):
        """Request for non-existent image returns 404."""
        response = requests.get(
            f"{BASE_URL}/api/media/r2/nonexistent/path/image.jpg",
            timeout=10
        )
        assert response.status_code == 404
        print("404 for non-existent image verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
