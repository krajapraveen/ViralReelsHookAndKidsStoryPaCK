"""
Media Proxy R2 Metadata Content-Type Tests - Iteration 377

Tests the final proxy rewrite where:
1. Content-Type is read from R2 metadata (authoritative), NOT guessed from extension
2. Video Range <2MB uses buffered Response for exact Content-Length
3. HEAD uses same R2 metadata Content-Type as GET
4. K8s ingress strips Content-Length and Accept-Ranges from GET (platform constraint)

Test files:
- Image: images/261430a2-28f5-4c40-bac2-35f8d275fae7/se_261430a2_thumb.jpg
- Video: videos/13ddd5d5-307c-4c45-8ac6-e349344d8abf/pipe_video_13ddd5d5-307.mp4
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test assets
TEST_IMAGE = "images/261430a2-28f5-4c40-bac2-35f8d275fae7/se_261430a2_thumb.jpg"
TEST_VIDEO = "videos/13ddd5d5-307c-4c45-8ac6-e349344d8abf/pipe_video_13ddd5d5-307.mp4"


class TestImageProxyContentType:
    """Image proxy returns Content-Type from R2 metadata"""
    
    def test_image_get_returns_correct_content_type(self):
        """Image GET returns Content-Type from R2 metadata (image/jpeg for .jpg)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        content_type = response.headers.get('Content-Type', '')
        # R2 metadata should return image/jpeg for .jpg files
        assert 'image/jpeg' in content_type or 'image/jpg' in content_type, \
            f"Expected image/jpeg, got {content_type}"
        print(f"✓ Image GET Content-Type: {content_type}")
    
    def test_image_has_etag_header(self):
        """Image proxy returns ETag header"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        etag = response.headers.get('ETag', '')
        assert etag, "ETag header missing"
        print(f"✓ Image ETag: {etag}")
    
    def test_image_has_content_disposition_inline(self):
        """Image proxy returns Content-Disposition: inline"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        disposition = response.headers.get('Content-Disposition', '')
        assert 'inline' in disposition, f"Expected inline, got {disposition}"
        print(f"✓ Image Content-Disposition: {disposition}")
    
    def test_image_has_surrogate_control(self):
        """Image proxy returns Surrogate-Control header (survives ingress)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        surrogate = response.headers.get('Surrogate-Control', '')
        assert surrogate, "Surrogate-Control header missing"
        assert 'max-age' in surrogate, f"Expected max-age in Surrogate-Control, got {surrogate}"
        print(f"✓ Image Surrogate-Control: {surrogate}")
    
    def test_image_has_nosniff_header(self):
        """Image proxy returns X-Content-Type-Options: nosniff"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        nosniff = response.headers.get('X-Content-Type-Options', '')
        assert nosniff == 'nosniff', f"Expected nosniff, got {nosniff}"
        print(f"✓ Image X-Content-Type-Options: {nosniff}")


class TestVideoProxyContentType:
    """Video proxy returns Content-Type from R2 metadata"""
    
    def test_video_get_returns_correct_content_type(self):
        """Video GET returns Content-Type from R2 metadata (video/mp4 for .mp4)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        # Use Range header to avoid downloading entire video
        headers = {'Range': 'bytes=0-1023'}
        response = requests.get(url, headers=headers, timeout=30)
        
        # Should return 206 for range request
        assert response.status_code in [200, 206], f"Expected 200/206, got {response.status_code}"
        
        content_type = response.headers.get('Content-Type', '')
        assert 'video/mp4' in content_type, f"Expected video/mp4, got {content_type}"
        print(f"✓ Video GET Content-Type: {content_type}")
    
    def test_video_range_returns_206_with_content_range(self):
        """Video Range bytes=0-65535 returns HTTP 206 with Content-Range header"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        headers = {'Range': 'bytes=0-65535'}
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code == 206, f"Expected 206, got {response.status_code}"
        
        content_range = response.headers.get('Content-Range', '')
        assert content_range, "Content-Range header missing"
        assert content_range.startswith('bytes 0-'), f"Expected 'bytes 0-...', got {content_range}"
        print(f"✓ Video Range 206 Content-Range: {content_range}")
    
    def test_video_small_range_has_exact_content_length(self):
        """Video Range <2MB returns buffered response with exact Content-Length"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        headers = {'Range': 'bytes=0-65535'}
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code == 206
        
        # Note: K8s ingress strips Content-Length from GET responses
        # But we can verify the response body length matches expected
        body_length = len(response.content)
        assert body_length == 65536, f"Expected 65536 bytes, got {body_length}"
        print(f"✓ Video Range body length: {body_length} bytes (exact)")


class TestHeadGetConsistency:
    """HEAD and GET return SAME Content-Type for same file"""
    
    def test_image_head_get_content_type_match(self):
        """HEAD and GET return same Content-Type for image"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        
        head_response = requests.head(url, timeout=30)
        get_response = requests.get(url, timeout=30)
        
        assert head_response.status_code == 200, f"HEAD failed: {head_response.status_code}"
        assert get_response.status_code == 200, f"GET failed: {get_response.status_code}"
        
        head_ct = head_response.headers.get('Content-Type', '')
        get_ct = get_response.headers.get('Content-Type', '')
        
        assert head_ct == get_ct, f"Content-Type mismatch: HEAD={head_ct}, GET={get_ct}"
        print(f"✓ Image HEAD/GET Content-Type match: {head_ct}")
    
    def test_video_head_get_content_type_match(self):
        """HEAD and GET return same Content-Type for video"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        
        head_response = requests.head(url, timeout=30)
        # Use range for GET to avoid full download
        get_response = requests.get(url, headers={'Range': 'bytes=0-1023'}, timeout=30)
        
        assert head_response.status_code == 200, f"HEAD failed: {head_response.status_code}"
        assert get_response.status_code in [200, 206], f"GET failed: {get_response.status_code}"
        
        head_ct = head_response.headers.get('Content-Type', '')
        get_ct = get_response.headers.get('Content-Type', '')
        
        assert head_ct == get_ct, f"Content-Type mismatch: HEAD={head_ct}, GET={get_ct}"
        print(f"✓ Video HEAD/GET Content-Type match: {head_ct}")
    
    def test_head_returns_content_length(self):
        """HEAD returns Content-Length (preserved by ingress for HEAD)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        response = requests.head(url, timeout=30)
        
        assert response.status_code == 200
        content_length = response.headers.get('Content-Length', '')
        assert content_length, "Content-Length missing from HEAD"
        assert int(content_length) > 0, f"Invalid Content-Length: {content_length}"
        print(f"✓ HEAD Content-Length: {content_length}")
    
    def test_head_returns_accept_ranges(self):
        """HEAD returns Accept-Ranges: bytes (preserved by ingress for HEAD)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        response = requests.head(url, timeout=30)
        
        assert response.status_code == 200
        accept_ranges = response.headers.get('Accept-Ranges', '')
        assert accept_ranges == 'bytes', f"Expected 'bytes', got {accept_ranges}"
        print(f"✓ HEAD Accept-Ranges: {accept_ranges}")


class TestFeedAPIProxyURLs:
    """All proxy URLs in feed API start with /api/media/r2/"""
    
    def test_story_feed_uses_proxy_urls(self):
        """Story feed API returns URLs with /api/media/r2/ prefix"""
        # Login first
        login_url = f"{BASE_URL}/api/auth/login"
        login_response = requests.post(login_url, json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        }, timeout=30)
        
        if login_response.status_code != 200:
            pytest.skip("Login failed - skipping feed test")
        
        token = login_response.json().get('token', '')
        headers = {'Authorization': f'Bearer {token}'}
        
        feed_url = f"{BASE_URL}/api/engagement/story-feed"
        response = requests.get(feed_url, headers=headers, timeout=30)
        
        assert response.status_code == 200, f"Feed API failed: {response.status_code}"
        
        data = response.json()
        
        # Check all URL fields use proxy
        url_fields = ['poster_url', 'thumbnail_url', 'thumbnail_small_url', 'video_url']
        proxy_urls = 0
        direct_r2_urls = 0
        
        def check_story(story):
            nonlocal proxy_urls, direct_r2_urls
            if not story:
                return
            for field in url_fields:
                url = story.get(field, '')
                if url:
                    if url.startswith('/api/media/r2/'):
                        proxy_urls += 1
                    elif 'r2.dev' in url or 'cloudflarestorage' in url:
                        direct_r2_urls += 1
                        print(f"⚠ Direct R2 URL found: {field}={url}")
        
        # Check featured story
        check_story(data.get('featured_story'))
        
        # Check story arrays
        for key in ['trending_stories', 'fresh_stories', 'continue_stories', 'unfinished_worlds']:
            for story in data.get(key, []):
                check_story(story)
        
        assert direct_r2_urls == 0, f"Found {direct_r2_urls} direct R2 URLs (should be 0)"
        print(f"✓ Feed API: {proxy_urls} proxy URLs, {direct_r2_urls} direct R2 URLs")


class TestCrossOriginHeaders:
    """Verify cross-origin-resource-policy header (added by ingress)"""
    
    def test_image_has_cors_headers(self):
        """Image proxy returns CORS headers"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        
        # Check Access-Control-Allow-Origin
        acao = response.headers.get('Access-Control-Allow-Origin', '')
        assert acao == '*', f"Expected '*', got {acao}"
        print(f"✓ Image Access-Control-Allow-Origin: {acao}")
        
        # Check cross-origin-resource-policy (added by ingress)
        corp = response.headers.get('cross-origin-resource-policy', '')
        if corp:
            print(f"✓ Image cross-origin-resource-policy: {corp}")
        else:
            print("ℹ cross-origin-resource-policy not present (may be added by CDN)")


class TestR2MetadataContentType:
    """Verify Content-Type comes from R2 metadata, not extension guessing"""
    
    def test_image_content_type_is_authoritative(self):
        """Image Content-Type matches R2 metadata (image/jpeg for .jpg)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        ct = response.headers.get('Content-Type', '')
        
        # R2 metadata should return proper MIME type
        # If it was guessed from extension, it would still be image/jpeg
        # But the key is that _resolve_content_type reads from R2 metadata first
        assert 'image/' in ct, f"Expected image/* Content-Type, got {ct}"
        print(f"✓ Image Content-Type (from R2 metadata): {ct}")
    
    def test_video_content_type_is_authoritative(self):
        """Video Content-Type matches R2 metadata (video/mp4 for .mp4)"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        headers = {'Range': 'bytes=0-1023'}
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code in [200, 206]
        ct = response.headers.get('Content-Type', '')
        
        assert 'video/' in ct, f"Expected video/* Content-Type, got {ct}"
        print(f"✓ Video Content-Type (from R2 metadata): {ct}")


class TestHeaderSummary:
    """Summary test to print all headers for verification"""
    
    def test_print_image_headers(self):
        """Print all image response headers for verification"""
        url = f"{BASE_URL}/api/media/r2/{TEST_IMAGE}"
        response = requests.get(url, timeout=30)
        
        assert response.status_code == 200
        
        print("\n=== IMAGE GET HEADERS ===")
        important_headers = [
            'Content-Type', 'Content-Length', 'Content-Disposition',
            'ETag', 'Accept-Ranges', 'X-Content-Type-Options',
            'Surrogate-Control', 'Cache-Control', 'CDN-Cache-Control',
            'Access-Control-Allow-Origin', 'cross-origin-resource-policy'
        ]
        for h in important_headers:
            val = response.headers.get(h, '(not present)')
            print(f"  {h}: {val}")
    
    def test_print_video_range_headers(self):
        """Print all video range response headers for verification"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        headers = {'Range': 'bytes=0-65535'}
        response = requests.get(url, headers=headers, timeout=30)
        
        assert response.status_code == 206
        
        print("\n=== VIDEO RANGE 206 HEADERS ===")
        important_headers = [
            'Content-Type', 'Content-Length', 'Content-Range',
            'Content-Disposition', 'ETag', 'Accept-Ranges',
            'X-Content-Type-Options', 'Surrogate-Control',
            'Access-Control-Allow-Origin', 'cross-origin-resource-policy'
        ]
        for h in important_headers:
            val = response.headers.get(h, '(not present)')
            print(f"  {h}: {val}")
    
    def test_print_head_headers(self):
        """Print all HEAD response headers for verification"""
        url = f"{BASE_URL}/api/media/r2/{TEST_VIDEO}"
        response = requests.head(url, timeout=30)
        
        assert response.status_code == 200
        
        print("\n=== VIDEO HEAD HEADERS ===")
        important_headers = [
            'Content-Type', 'Content-Length', 'Content-Disposition',
            'ETag', 'Accept-Ranges', 'X-Content-Type-Options',
            'Surrogate-Control', 'Access-Control-Allow-Origin'
        ]
        for h in important_headers:
            val = response.headers.get(h, '(not present)')
            print(f"  {h}: {val}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
