"""
Iteration 145 - P0 Bug Fixes Testing
=====================================
Tests for 3 P0 bugs:
1. GIF Maker page toast notification loop (frontend test - not covered here)
2. Rating API endpoint POST /api/user-analytics/rating
3. Promo Videos status API and file availability
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestSetup:
    """Shared test fixtures"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestRatingAPI(TestSetup):
    """P0 Bug #2: Rating API endpoint tests"""
    
    def test_rating_endpoint_returns_success(self, auth_headers):
        """Test POST /api/user-analytics/rating accepts rating and returns success"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers=auth_headers,
            json={
                "rating": 5,
                "feature_key": "reaction_gif",
                "comment": "Test rating submission"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success:true, got {data}"
        assert "rating_id" in data, f"Missing rating_id in response: {data}"
        print(f"✓ Rating API returned success with rating_id: {data.get('rating_id')}")
    
    def test_rating_1_to_5_accepted(self, auth_headers):
        """Test all ratings 1-5 are accepted"""
        for rating_value in [1, 2, 3, 4, 5]:
            # For low ratings, reason_type is required
            payload = {
                "rating": rating_value,
                "feature_key": "test_feature"
            }
            if rating_value <= 2:
                payload["reason_type"] = "other"
                payload["comment"] = f"Test comment for rating {rating_value}"
            
            response = requests.post(
                f"{BASE_URL}/api/user-analytics/rating",
                headers=auth_headers,
                json=payload
            )
            
            assert response.status_code == 200, f"Rating {rating_value} failed: {response.status_code}"
            assert response.json().get("success") is True, f"Rating {rating_value} not successful"
            print(f"✓ Rating {rating_value} accepted successfully")
    
    def test_rating_with_feature_key(self, auth_headers):
        """Test rating with feature_key parameter"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers=auth_headers,
            json={
                "rating": 4,
                "feature_key": "promo_videos",
                "comment": "Feature key test"
            }
        )
        
        assert response.status_code == 200
        assert response.json().get("success") is True
        print("✓ Rating with feature_key accepted")
    
    def test_low_rating_requires_reason(self, auth_headers):
        """Test that ratings 1-2 require reason_type"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers=auth_headers,
            json={"rating": 1, "feature_key": "test"}
        )
        
        # Should fail without reason_type for low ratings
        assert response.status_code == 400, f"Expected 400 for low rating without reason, got {response.status_code}"
        print("✓ Low rating correctly requires reason_type")


class TestPromoVideosAPI(TestSetup):
    """P0 Bug #3: Promo Videos API tests"""
    
    def test_promo_videos_status_endpoint(self):
        """Test GET /api/promo-videos/status returns 4 videos"""
        response = requests.get(f"{BASE_URL}/api/promo-videos/status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "videos" in data, f"Missing 'videos' key in response: {data}"
        
        videos = data["videos"]
        assert len(videos) == 4, f"Expected 4 videos, got {len(videos)}"
        print(f"✓ Promo videos status returns {len(videos)} videos")
    
    def test_all_videos_completed_status(self):
        """Test all 4 videos have status COMPLETED"""
        response = requests.get(f"{BASE_URL}/api/promo-videos/status")
        assert response.status_code == 200
        
        videos = response.json()["videos"]
        for video in videos:
            assert video["status"] == "COMPLETED", f"Video {video['id']} has status {video['status']}, expected COMPLETED"
            print(f"✓ Video {video['id']}: status=COMPLETED")
    
    def test_all_videos_have_download_url(self):
        """Test all videos have non-null downloadUrl"""
        response = requests.get(f"{BASE_URL}/api/promo-videos/status")
        assert response.status_code == 200
        
        videos = response.json()["videos"]
        for video in videos:
            assert video["downloadUrl"] is not None, f"Video {video['id']} has null downloadUrl"
            assert video["downloadUrl"].startswith("/api/generated/"), f"Video {video['id']} has invalid downloadUrl: {video['downloadUrl']}"
            print(f"✓ Video {video['id']}: downloadUrl={video['downloadUrl']}")
    
    def test_no_file_missing_status(self):
        """Test no video shows FILE_MISSING status"""
        response = requests.get(f"{BASE_URL}/api/promo-videos/status")
        assert response.status_code == 200
        
        videos = response.json()["videos"]
        file_missing_videos = [v for v in videos if v["status"] == "FILE_MISSING"]
        assert len(file_missing_videos) == 0, f"Found videos with FILE_MISSING status: {[v['id'] for v in file_missing_videos]}"
        print("✓ No videos have FILE_MISSING status")
    
    def test_video_metadata_present(self):
        """Test video metadata (platform, format, duration) present"""
        response = requests.get(f"{BASE_URL}/api/promo-videos/status")
        assert response.status_code == 200
        
        videos = response.json()["videos"]
        for video in videos:
            assert "platform" in video, f"Video {video['id']} missing platform"
            assert "format" in video, f"Video {video['id']} missing format"
            assert "duration" in video, f"Video {video['id']} missing duration"
            print(f"✓ Video {video['id']}: platform={video['platform']}, format={video['format']}, duration={video['duration']}")


class TestPromoVideoFiles(TestSetup):
    """Test actual video file downloads"""
    
    EXPECTED_VIDEOS = [
        "visionary_suite_instagram_reel.mp4",
        "visionary_suite_instagram_story.mp4",
        "visionary_suite_youtube_shorts.mp4",
        "visionary_suite_facebook_reel.mp4"
    ]
    
    def test_all_video_files_downloadable(self):
        """Test all 4 promo video files return HTTP 200"""
        for filename in self.EXPECTED_VIDEOS:
            # Use GET with stream=True and only fetch first chunk
            response = requests.get(f"{BASE_URL}/api/generated/{filename}", stream=True, timeout=10)
            assert response.status_code == 200, f"Video {filename} not downloadable: {response.status_code}"
            response.close()
            print(f"✓ {filename}: HTTP 200")
    
    def test_video_files_correct_content_type(self):
        """Test video files have video/mp4 content type"""
        for filename in self.EXPECTED_VIDEOS:
            response = requests.get(f"{BASE_URL}/api/generated/{filename}", stream=True, timeout=10)
            assert response.status_code == 200
            
            content_type = response.headers.get("content-type", "")
            response.close()
            # Accept video/mp4, application/octet-stream, or any video type
            assert "video" in content_type.lower() or "mp4" in content_type.lower() or "octet-stream" in content_type.lower(), \
                f"Video {filename} has unexpected content-type: {content_type}"
            print(f"✓ {filename}: content-type={content_type}")
    
    def test_video_files_have_content(self):
        """Test video files have actual content (size > 0)"""
        for filename in self.EXPECTED_VIDEOS:
            response = requests.get(f"{BASE_URL}/api/generated/{filename}", stream=True, timeout=10)
            assert response.status_code == 200
            
            content_length = response.headers.get("content-length")
            if content_length:
                response.close()
                assert int(content_length) > 100000, f"Video {filename} too small: {content_length} bytes"
                print(f"✓ {filename}: size={int(content_length) / 1024 / 1024:.2f} MB")
            else:
                # Read first chunk to verify content exists
                chunk = next(response.iter_content(chunk_size=1024), None)
                response.close()
                assert chunk is not None and len(chunk) > 0, f"Video {filename} has no content"
                print(f"✓ {filename}: has content (verified by GET)")


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """Test API is responding"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✓ API health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
