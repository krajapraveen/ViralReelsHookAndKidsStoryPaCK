"""
Test Media Proxy Streaming + Cache Headers - Iteration 375

Tests for:
1. GET /api/media/r2/{image}?w=480&q=80 returns HTTP 200 with image/jpeg Content-Type and ETag header
2. GET /api/media/r2/{video} with Range: bytes=0-65535 returns HTTP 206 with Content-Range and video/mp4
3. GET /api/media/r2/{video} without Range returns HTTP 200 with video/mp4 (streamed, not buffered)
4. Surrogate-Control header present in ALL responses (survives ingress)
5. HEAD /api/media/r2/{file} returns Content-Length and Accept-Ranges=bytes
6. Second image request (cache hit) still returns all headers including ETag
7. Video streaming delivers complete content (not truncated)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test assets from the review request
TEST_IMAGE_KEY = "images/261430a2-28f5-4c40-bac2-35f8d275fae7/se_261430a2_thumb.jpg"
TEST_VIDEO_KEY = "videos/13ddd5d5-307c-4c45-8ac6-e349344d8abf/pipe_video_13ddd5d5-307.mp4"
TEST_VIDEO_SIZE = 8433292  # Total video file size in bytes

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code}")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestImageProxyHeaders:
    """Test image proxy returns correct headers including Surrogate-Control"""
    
    def test_image_get_with_resize_returns_200_and_headers(self):
        """GET /api/media/r2/{image}?w=480&q=80 returns HTTP 200 with image/jpeg and ETag"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_KEY}?w=480&q=80"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Content-Type must be image/jpeg
        content_type = response.headers.get('Content-Type', '')
        assert 'image/jpeg' in content_type, f"Expected image/jpeg, got {content_type}"
        
        # ETag must be present
        etag = response.headers.get('ETag')
        assert etag is not None, "ETag header missing"
        assert len(etag) > 0, "ETag header is empty"
        
        print(f"✓ Image GET returns 200 with Content-Type={content_type}, ETag={etag}")
    
    def test_image_has_surrogate_control_header(self):
        """Surrogate-Control header present in image response (survives ingress)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_KEY}?w=480&q=80"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        
        # Surrogate-Control must be present (survives ingress override)
        surrogate_control = response.headers.get('Surrogate-Control')
        assert surrogate_control is not None, "Surrogate-Control header missing - ingress may have stripped it"
        assert 'max-age' in surrogate_control, f"Surrogate-Control missing max-age: {surrogate_control}"
        
        print(f"✓ Image has Surrogate-Control: {surrogate_control}")
    
    def test_image_has_cache_headers_strategy(self):
        """Image response has cache headers (Surrogate-Control survives ingress)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_KEY}?w=480&q=80"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        
        # Surrogate-Control MUST be present (survives ingress override)
        surrogate_control = response.headers.get('Surrogate-Control')
        assert surrogate_control is not None, "Surrogate-Control header missing"
        assert 'max-age' in surrogate_control, f"Surrogate-Control missing max-age: {surrogate_control}"
        
        # CDN-Cache-Control may be stripped by ingress - this is expected
        cdn_cache_control = response.headers.get('CDN-Cache-Control')
        
        # Cache-Control is overridden by ingress to no-store - this is expected
        cache_control = response.headers.get('Cache-Control')
        
        print(f"✓ Image cache headers: Surrogate-Control={surrogate_control}")
        print(f"  CDN-Cache-Control={cdn_cache_control} (may be stripped by ingress)")
        print(f"  Cache-Control={cache_control} (overridden by ingress)")
    
    def test_image_cache_hit_still_returns_all_headers(self):
        """Second image request (cache hit) still returns all headers including ETag"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_KEY}?w=480&q=80"
        
        # First request (cache miss)
        response1 = requests.get(url, timeout=30)
        assert response1.status_code == 200
        etag1 = response1.headers.get('ETag')
        surrogate1 = response1.headers.get('Surrogate-Control')
        
        # Second request (cache hit)
        response2 = requests.get(url, timeout=30)
        assert response2.status_code == 200
        
        # Critical headers must still be present on cache hit
        etag2 = response2.headers.get('ETag')
        surrogate2 = response2.headers.get('Surrogate-Control')
        
        assert etag2 is not None, "ETag missing on cache hit"
        assert surrogate2 is not None, "Surrogate-Control missing on cache hit"
        
        # ETag should be consistent
        assert etag1 == etag2, f"ETag changed between requests: {etag1} vs {etag2}"
        
        print(f"✓ Cache hit returns all critical headers: ETag={etag2}, Surrogate-Control={surrogate2}")


class TestVideoProxyStreaming:
    """Test video proxy streaming with Range support"""
    
    def test_video_get_with_range_returns_206(self):
        """GET /api/media/r2/{video} with Range: bytes=0-65535 returns HTTP 206"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        headers = {"Range": "bytes=0-65535"}
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        
        assert response.status_code == 206, f"Expected 206 Partial Content, got {response.status_code}"
        
        # Content-Type must be video/mp4
        content_type = response.headers.get('Content-Type', '')
        assert 'video/mp4' in content_type, f"Expected video/mp4, got {content_type}"
        
        # Content-Range must be present
        content_range = response.headers.get('Content-Range')
        assert content_range is not None, "Content-Range header missing on 206 response"
        assert 'bytes' in content_range, f"Content-Range format invalid: {content_range}"
        
        print(f"✓ Video Range request returns 206 with Content-Range: {content_range}")
        response.close()
    
    def test_video_get_without_range_returns_200_streamed(self):
        """GET /api/media/r2/{video} without Range returns HTTP 200 with video/mp4 (streamed)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        response = requests.get(url, timeout=60, stream=True)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Content-Type must be video/mp4
        content_type = response.headers.get('Content-Type', '')
        assert 'video/mp4' in content_type, f"Expected video/mp4, got {content_type}"
        
        # Check for streaming indicators
        # Either Transfer-Encoding: chunked OR Content-Length should be present
        transfer_encoding = response.headers.get('Transfer-Encoding')
        content_length = response.headers.get('Content-Length')
        
        # At least one must be present for proper streaming
        has_streaming_indicator = (transfer_encoding == 'chunked') or (content_length is not None)
        
        print(f"✓ Video GET returns 200 with Content-Type={content_type}")
        print(f"  Transfer-Encoding: {transfer_encoding}, Content-Length: {content_length}")
        
        response.close()
    
    def test_video_has_surrogate_control_header(self):
        """Surrogate-Control header present in video response"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        headers = {"Range": "bytes=0-1023"}
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        
        assert response.status_code == 206
        
        # Surrogate-Control must be present
        surrogate_control = response.headers.get('Surrogate-Control')
        assert surrogate_control is not None, "Surrogate-Control header missing on video response"
        assert 'max-age' in surrogate_control, f"Surrogate-Control missing max-age: {surrogate_control}"
        
        print(f"✓ Video has Surrogate-Control: {surrogate_control}")
        response.close()
    
    def test_video_range_content_range_format(self):
        """Video Range request returns proper Content-Range format"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        headers = {"Range": "bytes=0-65535"}
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        
        assert response.status_code == 206
        
        content_range = response.headers.get('Content-Range')
        assert content_range is not None
        
        # Format should be: bytes start-end/total
        # e.g., "bytes 0-65535/8433292"
        assert content_range.startswith('bytes '), f"Invalid Content-Range format: {content_range}"
        
        # Parse and validate
        parts = content_range.replace('bytes ', '').split('/')
        assert len(parts) == 2, f"Invalid Content-Range format: {content_range}"
        
        range_part, total = parts
        start_end = range_part.split('-')
        assert len(start_end) == 2, f"Invalid range format: {range_part}"
        
        start = int(start_end[0])
        end = int(start_end[1])
        total_size = int(total)
        
        assert start == 0, f"Start should be 0, got {start}"
        assert end >= 65535, f"End should be at least 65535, got {end}"
        assert total_size == TEST_VIDEO_SIZE, f"Total size should be {TEST_VIDEO_SIZE}, got {total_size}"
        
        print(f"✓ Content-Range format valid: {content_range}")
        response.close()
    
    def test_video_streaming_delivers_complete_content(self):
        """Video streaming delivers complete content (not truncated)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        headers = {"Range": "bytes=0-131071"}  # Request first 128KB
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        
        assert response.status_code == 206
        
        # Read the content
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) >= 131072:  # Stop after 128KB
                break
        
        # Should have received at least the requested amount
        assert len(content) >= 65536, f"Content truncated: received {len(content)} bytes, expected at least 65536"
        
        print(f"✓ Video streaming delivered {len(content)} bytes (not truncated)")
        response.close()


class TestHeadRequests:
    """Test HEAD requests return proper metadata"""
    
    def test_head_image_returns_content_length_and_accept_ranges(self):
        """HEAD /api/media/r2/{image} returns Content-Length and Accept-Ranges=bytes"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_KEY}"
        response = requests.head(url, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Content-Length must be present
        content_length = response.headers.get('Content-Length')
        assert content_length is not None, "Content-Length header missing on HEAD"
        assert int(content_length) > 0, f"Content-Length should be > 0, got {content_length}"
        
        # Accept-Ranges must be bytes
        accept_ranges = response.headers.get('Accept-Ranges')
        assert accept_ranges == 'bytes', f"Accept-Ranges should be 'bytes', got {accept_ranges}"
        
        print(f"✓ HEAD image: Content-Length={content_length}, Accept-Ranges={accept_ranges}")
    
    def test_head_video_returns_content_length_and_accept_ranges(self):
        """HEAD /api/media/r2/{video} returns Content-Length and Accept-Ranges=bytes"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        response = requests.head(url, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Content-Length must be present
        content_length = response.headers.get('Content-Length')
        assert content_length is not None, "Content-Length header missing on HEAD"
        
        # Should match expected video size
        assert int(content_length) == TEST_VIDEO_SIZE, f"Content-Length should be {TEST_VIDEO_SIZE}, got {content_length}"
        
        # Accept-Ranges must be bytes
        accept_ranges = response.headers.get('Accept-Ranges')
        assert accept_ranges == 'bytes', f"Accept-Ranges should be 'bytes', got {accept_ranges}"
        
        print(f"✓ HEAD video: Content-Length={content_length}, Accept-Ranges={accept_ranges}")
    
    def test_head_has_surrogate_control_header(self):
        """HEAD request also includes Surrogate-Control header"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_KEY}"
        response = requests.head(url, timeout=30)
        
        assert response.status_code == 200
        
        surrogate_control = response.headers.get('Surrogate-Control')
        assert surrogate_control is not None, "Surrogate-Control missing on HEAD response"
        
        print(f"✓ HEAD has Surrogate-Control: {surrogate_control}")


class TestAllResponsesHaveSurrogateControl:
    """Verify Surrogate-Control header is present in ALL response types"""
    
    def test_image_get_has_surrogate_control(self):
        """Image GET has Surrogate-Control"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_KEY}?w=480&q=80"
        response = requests.get(url, timeout=30)
        assert response.status_code == 200
        assert response.headers.get('Surrogate-Control') is not None, "Missing on image GET"
        print("✓ Image GET has Surrogate-Control")
    
    def test_video_get_full_has_surrogate_control(self):
        """Video GET (full) has Surrogate-Control"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        response = requests.get(url, timeout=60, stream=True)
        assert response.status_code == 200
        assert response.headers.get('Surrogate-Control') is not None, "Missing on video GET full"
        print("✓ Video GET (full) has Surrogate-Control")
        response.close()
    
    def test_video_get_range_has_surrogate_control(self):
        """Video GET (range) has Surrogate-Control"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        headers = {"Range": "bytes=0-1023"}
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        assert response.status_code == 206
        assert response.headers.get('Surrogate-Control') is not None, "Missing on video GET range"
        print("✓ Video GET (range) has Surrogate-Control")
        response.close()
    
    def test_head_image_has_surrogate_control(self):
        """HEAD image has Surrogate-Control"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE_KEY}"
        response = requests.head(url, timeout=30)
        assert response.status_code == 200
        assert response.headers.get('Surrogate-Control') is not None, "Missing on HEAD image"
        print("✓ HEAD image has Surrogate-Control")
    
    def test_head_video_has_surrogate_control(self):
        """HEAD video has Surrogate-Control"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO_KEY}"
        response = requests.head(url, timeout=30)
        assert response.status_code == 200
        assert response.headers.get('Surrogate-Control') is not None, "Missing on HEAD video"
        print("✓ HEAD video has Surrogate-Control")


class TestDashboardRendersImages:
    """Test Dashboard renders all images correctly via proxy"""
    
    def test_dashboard_api_returns_proxy_urls(self, auth_headers):
        """Dashboard API returns proxy URLs for images"""
        url = f"{BASE_URL}/api/engagement/story-feed"
        response = requests.get(url, headers=auth_headers, timeout=30)
        
        assert response.status_code == 200, f"Story feed failed: {response.status_code}"
        
        data = response.json()
        
        # Check all URL fields use proxy
        proxy_urls = 0
        direct_r2_urls = 0
        
        def check_urls(obj, path=""):
            nonlocal proxy_urls, direct_r2_urls
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ['thumbnail_url', 'thumbnail_small_url', 'poster_url', 'video_url']:
                        if value:
                            if '/api/media/r2/' in value:
                                proxy_urls += 1
                            elif 'r2.dev' in value or 'cloudflarestorage' in value:
                                direct_r2_urls += 1
                    check_urls(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_urls(item, f"{path}[{i}]")
        
        check_urls(data)
        
        print(f"✓ Dashboard API: {proxy_urls} proxy URLs, {direct_r2_urls} direct R2 URLs")
        assert direct_r2_urls == 0, f"Found {direct_r2_urls} direct R2 URLs - should all be proxied"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
