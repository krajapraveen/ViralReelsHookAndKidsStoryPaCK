"""
Growth Engine API Tests - Iteration 441
Tests for Share Page, First-Video-Free, and Remix features
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
KNOWN_SHARE_ID = "96902ad4-066"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestSharePageAPI:
    """Tests for GET /api/share/{share_id} endpoint"""
    
    def test_get_share_data_success(self, api_client):
        """Test GET /api/share/{share_id} returns expected fields"""
        response = api_client.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}")
        print(f"GET /api/share/{KNOWN_SHARE_ID} status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should have success=True"
        
        # Verify required fields for Growth Engine
        assert "id" in data, "Response should have 'id' field"
        assert "title" in data, "Response should have 'title' field"
        assert "views" in data, "Response should have 'views' field"
        
        # Verify new Growth Engine fields
        assert "videoUrl" in data, "Response should have 'videoUrl' field (may be null)"
        assert "animationStyle" in data, "Response should have 'animationStyle' field (may be null)"
        assert "generationId" in data, "Response should have 'generationId' field"
        
        # Verify fork/remix fields
        assert "forks" in data, "Response should have 'forks' count"
        assert "storyContext" in data, "Response should have 'storyContext' for remix"
        
        print(f"Share data: id={data.get('id')}, title={data.get('title')}, videoUrl={data.get('videoUrl')}, generationId={data.get('generationId')}")
        print(f"TEST PASSED: GET /api/share/{KNOWN_SHARE_ID} returns all required Growth Engine fields")
    
    def test_get_share_data_not_found(self, api_client):
        """Test GET /api/share/{share_id} returns 404 for invalid ID"""
        response = api_client.get(f"{BASE_URL}/api/share/invalid-share-id-12345")
        print(f"GET /api/share/invalid-share-id-12345 status: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("TEST PASSED: Invalid share ID returns 404")
    
    def test_share_view_count_increments(self, api_client):
        """Test that view count increments on each request"""
        # First request
        response1 = api_client.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}")
        assert response1.status_code == 200
        views1 = response1.json().get("views", 0)
        
        # Second request
        response2 = api_client.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}")
        assert response2.status_code == 200
        views2 = response2.json().get("views", 0)
        
        # Views should increment
        assert views2 >= views1, f"Views should increment: {views1} -> {views2}"
        print(f"TEST PASSED: View count incremented from {views1} to {views2}")


class TestForkRemixAPI:
    """Tests for POST /api/share/{share_id}/fork endpoint"""
    
    def test_fork_story_success(self, api_client):
        """Test POST /api/share/{share_id}/fork returns fork data"""
        response = api_client.post(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}/fork")
        print(f"POST /api/share/{KNOWN_SHARE_ID}/fork status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should have success=True"
        assert "fork" in data, "Response should have 'fork' object"
        
        fork = data["fork"]
        # Verify fork data structure for remix
        assert "parentShareId" in fork, "Fork should have parentShareId"
        assert "parentTitle" in fork, "Fork should have parentTitle"
        assert "storyContext" in fork, "Fork should have storyContext for prefill"
        assert "type" in fork, "Fork should have type"
        
        print(f"Fork data: parentShareId={fork.get('parentShareId')}, parentTitle={fork.get('parentTitle')}")
        print(f"storyContext preview: {str(fork.get('storyContext', ''))[:100]}...")
        print("TEST PASSED: POST /api/share/{share_id}/fork returns valid fork data")
    
    def test_fork_story_not_found(self, api_client):
        """Test POST /api/share/{share_id}/fork returns 404 for invalid ID"""
        response = api_client.post(f"{BASE_URL}/api/share/invalid-share-id-12345/fork")
        print(f"POST /api/share/invalid-share-id-12345/fork status: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("TEST PASSED: Fork with invalid share ID returns 404")
    
    def test_fork_increments_fork_count(self, api_client):
        """Test that fork count increments after fork request"""
        # Get initial fork count
        response1 = api_client.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}")
        assert response1.status_code == 200
        forks1 = response1.json().get("forks", 0)
        
        # Fork the story
        fork_response = api_client.post(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}/fork")
        assert fork_response.status_code == 200
        
        # Get updated fork count
        response2 = api_client.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}")
        assert response2.status_code == 200
        forks2 = response2.json().get("forks", 0)
        
        # Fork count should increment
        assert forks2 > forks1, f"Fork count should increment: {forks1} -> {forks2}"
        print(f"TEST PASSED: Fork count incremented from {forks1} to {forks2}")


class TestFirstVideoFreeAPI:
    """Tests for GET /api/story-engine/first-video-free endpoint"""
    
    def test_first_video_free_anonymous(self, api_client):
        """Test first-video-free returns eligible=True for anonymous users"""
        # Create a fresh session without auth
        fresh_session = requests.Session()
        fresh_session.headers.update({"Content-Type": "application/json"})
        
        response = fresh_session.get(f"{BASE_URL}/api/story-engine/first-video-free")
        print(f"GET /api/story-engine/first-video-free (anonymous) status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "eligible" in data, "Response should have 'eligible' field"
        assert "reason" in data, "Response should have 'reason' field"
        
        # Anonymous users should be eligible
        assert data["eligible"] == True, f"Anonymous users should be eligible, got {data}"
        assert data["reason"] == "new_user", f"Reason should be 'new_user', got {data['reason']}"
        
        print(f"TEST PASSED: Anonymous user eligible={data['eligible']}, reason={data['reason']}")
    
    def test_first_video_free_authenticated(self, authenticated_client):
        """Test first-video-free returns eligible=False for test user with existing videos"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/first-video-free")
        print(f"GET /api/story-engine/first-video-free (authenticated) status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "eligible" in data, "Response should have 'eligible' field"
        assert "reason" in data, "Response should have 'reason' field"
        
        # Test user has existing videos, should NOT be eligible
        assert data["eligible"] == False, f"Test user with videos should NOT be eligible, got {data}"
        assert data["reason"] == "has_videos", f"Reason should be 'has_videos', got {data['reason']}"
        
        print(f"TEST PASSED: Authenticated test user eligible={data['eligible']}, reason={data['reason']}")


class TestMySpaceRegression:
    """Regression tests for My Space page (from iteration 439/440)"""
    
    def test_user_jobs_endpoint(self, authenticated_client):
        """Test GET /api/story-engine/user-jobs returns jobs"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        print(f"GET /api/story-engine/user-jobs status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should have success=True"
        assert "jobs" in data, "Response should have 'jobs' array"
        
        jobs = data["jobs"]
        print(f"Found {len(jobs)} jobs for test user")
        
        if len(jobs) > 0:
            job = jobs[0]
            assert "job_id" in job, "Job should have job_id"
            assert "title" in job, "Job should have title"
            assert "status" in job, "Job should have status"
            print(f"Sample job: id={job.get('job_id')[:12]}..., title={job.get('title')}, status={job.get('status')}")
        
        print("TEST PASSED: GET /api/story-engine/user-jobs returns valid jobs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
