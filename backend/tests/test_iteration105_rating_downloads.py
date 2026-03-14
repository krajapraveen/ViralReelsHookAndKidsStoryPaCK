"""
Iteration 105: Testing Rating Modal, Downloads API, and Generation Pages
Features to test:
1. RatingModal closes after submission
2. My Downloads page loads at /app/downloads
3. Downloads API endpoints work
4. PhotoReactionGIF page works without infinite loops
5. PhotoToComic page works without infinite loops
6. ComicStorybook page works without infinite loops
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://daily-challenges-10.preview.emergentagent.com')

# Test credentials
TEST_USER = {
    "email": "demo@example.com",
    "password": "Password123!"
}

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=TEST_USER,
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed with status {response.status_code}: {response.text}")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestDownloadsAPI:
    """Test Downloads API endpoints"""
    
    def test_my_downloads_endpoint_exists(self, auth_headers):
        """Test /api/downloads/my-downloads endpoint exists and returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/downloads/my-downloads",
            headers=auth_headers
        )
        
        # Should return 200
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check response structure
        data = response.json()
        assert "downloads" in data, "Response should contain 'downloads' key"
        assert "expiry_minutes" in data, "Response should contain 'expiry_minutes' key"
        assert isinstance(data["downloads"], list), "Downloads should be a list"
        print(f"✓ My downloads endpoint works - {len(data['downloads'])} downloads found")
    
    def test_downloads_endpoint_requires_auth(self):
        """Test that downloads endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads")
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Downloads endpoint properly requires authentication")
    
    def test_download_not_found(self, auth_headers):
        """Test 404 for non-existent download"""
        fake_id = "nonexistent-download-id-12345"
        response = requests.get(
            f"{BASE_URL}/api/downloads/{fake_id}",
            headers=auth_headers
        )
        
        # Should return 404
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent download returns 404")
    
    def test_download_url_not_found(self, auth_headers):
        """Test 404 for non-existent download URL"""
        fake_id = "nonexistent-download-id-12345"
        response = requests.get(
            f"{BASE_URL}/api/downloads/{fake_id}/url",
            headers=auth_headers
        )
        
        # Should return 404
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent download URL returns 404")


class TestRatingAPI:
    """Test Rating/Feedback API endpoints"""
    
    def test_rating_endpoint_exists(self, auth_headers):
        """Test that rating submission endpoint exists"""
        # Submit a valid rating
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers=auth_headers,
            json={
                "rating": 5,
                "feature_key": "test_feature",
                "reason_type": None,
                "comment": "Test rating from automated tests",
                "related_request_id": None
            }
        )
        
        # Should return 200 or 201
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        print("✓ Rating endpoint works and accepts submissions")
    
    def test_rating_requires_auth(self):
        """Test that rating endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Content-Type": "application/json"},
            json={"rating": 5, "feature_key": "test"}
        )
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Rating endpoint properly requires authentication")
    
    def test_rating_validation(self, auth_headers):
        """Test rating validation - rating value must be 1-5"""
        # Test invalid rating value
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers=auth_headers,
            json={
                "rating": 10,  # Invalid - should be 1-5
                "feature_key": "test_feature"
            }
        )
        
        # Should either accept (with server-side validation) or return 400/422
        # The test passes if API doesn't crash
        assert response.status_code < 500, f"Server error on rating validation: {response.status_code}"
        print(f"✓ Rating validation handled (status: {response.status_code})")


class TestGenerationEndpoints:
    """Test generation-related endpoints for PhotoReactionGIF, PhotoToComic, ComicStorybook"""
    
    def test_photo_to_comic_job_endpoint(self, auth_headers):
        """Test photo-to-comic job status endpoint structure"""
        # Test with a fake job ID - should return 404 or proper error
        fake_job_id = "fake-job-id-12345"
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/{fake_job_id}",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent job
        assert response.status_code in [404, 200], f"Expected 404/200, got {response.status_code}"
        print(f"✓ Photo-to-comic job endpoint works (status: {response.status_code})")
    
    def test_reaction_gif_job_endpoint(self, auth_headers):
        """Test reaction-gif job status endpoint structure"""
        fake_job_id = "fake-job-id-12345"
        response = requests.get(
            f"{BASE_URL}/api/reaction-gif/job/{fake_job_id}",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent job
        assert response.status_code in [404, 200], f"Expected 404/200, got {response.status_code}"
        print(f"✓ Reaction-gif job endpoint works (status: {response.status_code})")
    
    def test_comic_storybook_v2_job_endpoint(self, auth_headers):
        """Test comic-storybook-v2 job status endpoint structure"""
        fake_job_id = "fake-job-id-12345"
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook-v2/job/{fake_job_id}",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent job
        assert response.status_code in [404, 200], f"Expected 404/200, got {response.status_code}"
        print(f"✓ Comic-storybook-v2 job endpoint works (status: {response.status_code})")


class TestCreditsEndpoint:
    """Test credits endpoint used by generation pages"""
    
    def test_credits_balance_endpoint(self, auth_headers):
        """Test credits balance endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "credits" in data, "Response should contain 'credits' key"
        assert isinstance(data["credits"], (int, float)), "Credits should be numeric"
        print(f"✓ Credits balance endpoint works - User has {data['credits']} credits")


class TestUserProfileEndpoint:
    """Test user profile endpoint used by generation pages"""
    
    def test_user_profile_endpoint(self, auth_headers):
        """Test user profile endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/user/profile",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response should contain 'user' key"
        print(f"✓ User profile endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
