"""
Test Story Viewer API and Dashboard Card Routing Fix
Tests for iteration 492 - StoryViewerPage and Dashboard routing fix

Features tested:
1. GET /api/stories/viewer/{story_id} - Public viewer endpoint (no ownership check)
2. Story chain endpoint for episode navigation
3. Verify viewer endpoint returns all required fields
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Test data - battle-demo-root is owned by admin
TEST_STORY_ID = "battle-demo-root"


@pytest.fixture(scope="module")
def test_user_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code}")


class TestStoryViewerAPI:
    """Tests for GET /api/stories/viewer/{story_id} endpoint"""
    
    def test_viewer_endpoint_without_auth(self):
        """Viewer endpoint should work without authentication"""
        response = requests.get(f"{BASE_URL}/api/stories/viewer/{TEST_STORY_ID}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") is True
        assert "job" in data
        print(f"PASS: Viewer endpoint works without auth")
    
    def test_viewer_endpoint_with_test_user(self, test_user_token):
        """Test user can view admin's story (no ownership check)"""
        response = requests.get(
            f"{BASE_URL}/api/stories/viewer/{TEST_STORY_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") is True
        assert "job" in data
        print(f"PASS: Test user can view admin's story")
    
    def test_viewer_returns_required_fields(self, test_user_token):
        """Verify viewer endpoint returns all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/stories/viewer/{TEST_STORY_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        
        # Required fields per spec
        required_fields = [
            "job_id", "title", "story_text", "state",
            "output_url", "thumbnail_url", "animation_style",
            "scene_progress", "root_story_id", "chain_depth",
            "continuation_type", "total_children", "total_views",
            "total_shares", "battle_score", "creator_name"
        ]
        
        for field in required_fields:
            assert field in job, f"Missing required field: {field}"
        
        print(f"PASS: All required fields present in viewer response")
        print(f"  - title: {job.get('title')}")
        print(f"  - creator_name: {job.get('creator_name')}")
        print(f"  - chain_depth: {job.get('chain_depth')}")
        print(f"  - total_children: {job.get('total_children')}")
    
    def test_viewer_returns_correct_story_data(self, test_user_token):
        """Verify viewer returns correct story data for battle-demo-root"""
        response = requests.get(
            f"{BASE_URL}/api/stories/viewer/{TEST_STORY_ID}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        job = response.json().get("job", {})
        
        # Verify expected data for battle-demo-root
        assert job.get("job_id") == TEST_STORY_ID
        assert job.get("title") == "The Crystal Maze"
        assert "crystal" in job.get("story_text", "").lower()
        assert job.get("state") in ["READY", "PARTIAL_READY", "COMPLETED"]
        
        print(f"PASS: Viewer returns correct story data")
    
    def test_viewer_nonexistent_story(self, test_user_token):
        """Viewer should return 404 for non-existent story"""
        response = requests.get(
            f"{BASE_URL}/api/stories/viewer/nonexistent-story-id-12345",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 404
        print(f"PASS: Viewer returns 404 for non-existent story")


class TestStoryChainAPI:
    """Tests for story chain endpoint (episode navigation)"""
    
    def test_chain_endpoint_returns_episodes(self, test_user_token):
        """Chain endpoint should return episodes for navigation"""
        response = requests.get(
            f"{BASE_URL}/api/stories/{TEST_STORY_ID}/chain",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        
        # Check chain stats
        chain_stats = data.get("chain_stats", {})
        assert "total_nodes" in chain_stats
        assert "total_episodes" in chain_stats
        
        # Check episodes list
        episodes = data.get("episodes", [])
        assert len(episodes) >= 1, "Should have at least 1 episode"
        
        print(f"PASS: Chain endpoint returns episodes")
        print(f"  - Total nodes: {chain_stats.get('total_nodes')}")
        print(f"  - Total episodes: {chain_stats.get('total_episodes')}")
        print(f"  - Episodes count: {len(episodes)}")
    
    def test_chain_episodes_have_required_fields(self, test_user_token):
        """Episodes should have required fields for navigation"""
        response = requests.get(
            f"{BASE_URL}/api/stories/{TEST_STORY_ID}/chain",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        episodes = response.json().get("episodes", [])
        
        if len(episodes) > 0:
            episode = episodes[0]
            required_fields = ["job_id", "title", "chain_depth", "continuation_type"]
            for field in required_fields:
                assert field in episode, f"Episode missing field: {field}"
            print(f"PASS: Episodes have required fields for navigation")
        else:
            print(f"INFO: No episodes to verify fields")


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """API should be healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"PASS: API is healthy")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
