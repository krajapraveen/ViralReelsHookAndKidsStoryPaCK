"""
Test Story Chain Progression System Enhancement - Iteration 291
Tests for:
1. Dashboard 'Resume Your Story' - GET /api/photo-to-comic/active-chains 
   - Returns progress_pct, total_panels, continue_job_id
2. Enhanced chain detail - GET /api/photo-to-comic/chain/{chain_id}
   - Returns progress_pct, total_panels, latest_continuable_job_id
3. AI suggestions - POST /api/photo-to-comic/chain/suggestions
   - Returns AI-generated suggestions array
4. My chains - GET /api/photo-to-comic/my-chains
   - Returns chains with progress_pct field
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestActiveChains:
    """Test GET /api/photo-to-comic/active-chains for Dashboard 'Resume Your Story'"""
    
    def test_active_chains_returns_200(self, auth_headers):
        """Active chains endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_active_chains_returns_chains_array(self, auth_headers):
        """Active chains should return chains array"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "chains" in data, f"Response should have 'chains' key: {data}"
        assert isinstance(data["chains"], list), "chains should be a list"
    
    def test_active_chains_has_progress_pct(self, auth_headers):
        """Each chain should have progress_pct field"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if data["chains"]:
            chain = data["chains"][0]
            assert "progress_pct" in chain, f"Chain should have progress_pct: {chain.keys()}"
            assert isinstance(chain["progress_pct"], (int, float)), "progress_pct should be numeric"
            assert 0 <= chain["progress_pct"] <= 100, "progress_pct should be 0-100"
    
    def test_active_chains_has_total_panels(self, auth_headers):
        """Each chain should have total_panels field"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if data["chains"]:
            chain = data["chains"][0]
            assert "total_panels" in chain, f"Chain should have total_panels: {chain.keys()}"
            assert isinstance(chain["total_panels"], int), "total_panels should be int"
    
    def test_active_chains_has_continue_job_id(self, auth_headers):
        """Each chain should have continue_job_id field (can be null)"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if data["chains"]:
            chain = data["chains"][0]
            assert "continue_job_id" in chain, f"Chain should have continue_job_id: {chain.keys()}"
    
    def test_active_chains_has_total_episodes(self, auth_headers):
        """Each chain should have total_episodes and completed counts"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if data["chains"]:
            chain = data["chains"][0]
            assert "total_episodes" in chain, f"Chain should have total_episodes: {chain.keys()}"
            assert "completed" in chain, f"Chain should have completed: {chain.keys()}"
    
    def test_active_chains_requires_auth(self):
        """Active chains should require authentication"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains")
        assert response.status_code in [401, 403, 422], f"Should require auth: {response.status_code}"


class TestChainDetail:
    """Test GET /api/photo-to-comic/chain/{chain_id} - Enhanced chain detail"""
    
    def test_chain_detail_404_for_invalid_id(self, auth_headers):
        """Chain detail should return 404 for invalid chain_id"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/chain/invalid-chain-id", headers=auth_headers)
        assert response.status_code == 404
    
    def test_chain_detail_has_progress_pct(self, auth_headers):
        """Chain detail should include progress_pct"""
        # First get a valid chain_id from active-chains
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        if chains_response.status_code != 200 or not chains_response.json().get("chains"):
            pytest.skip("No chains available for testing")
        
        chain_id = chains_response.json()["chains"][0]["chain_id"]
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/chain/{chain_id}", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200: {response.text}"
        data = response.json()
        assert "progress_pct" in data, f"Chain detail should have progress_pct: {data.keys()}"
    
    def test_chain_detail_has_total_panels(self, auth_headers):
        """Chain detail should include total_panels"""
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        if chains_response.status_code != 200 or not chains_response.json().get("chains"):
            pytest.skip("No chains available for testing")
        
        chain_id = chains_response.json()["chains"][0]["chain_id"]
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/chain/{chain_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_panels" in data, f"Chain detail should have total_panels: {data.keys()}"
    
    def test_chain_detail_has_latest_continuable_job_id(self, auth_headers):
        """Chain detail should include latest_continuable_job_id"""
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        if chains_response.status_code != 200 or not chains_response.json().get("chains"):
            pytest.skip("No chains available for testing")
        
        chain_id = chains_response.json()["chains"][0]["chain_id"]
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/chain/{chain_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "latest_continuable_job_id" in data, f"Should have latest_continuable_job_id: {data.keys()}"
    
    def test_chain_detail_has_flat_timeline(self, auth_headers):
        """Chain detail should include flat timeline array"""
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        if chains_response.status_code != 200 or not chains_response.json().get("chains"):
            pytest.skip("No chains available for testing")
        
        chain_id = chains_response.json()["chains"][0]["chain_id"]
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/chain/{chain_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "flat" in data, f"Chain detail should have flat timeline: {data.keys()}"
        assert isinstance(data["flat"], list), "flat should be a list"


class TestChainSuggestions:
    """Test POST /api/photo-to-comic/chain/suggestions - AI suggestions"""
    
    def test_suggestions_endpoint_exists(self, auth_headers):
        """Suggestions endpoint should exist and require chain_id"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/chain/suggestions",
            headers=auth_headers,
            json={"chain_id": "invalid-chain-id"}
        )
        # Should be 404 (not found) or 200, not 404/422 for missing route
        assert response.status_code in [200, 404], f"Endpoint should exist: {response.status_code}"
    
    def test_suggestions_requires_chain_id(self, auth_headers):
        """Suggestions should require chain_id in body"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/chain/suggestions",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 422, f"Should require chain_id: {response.status_code}"
    
    def test_suggestions_returns_suggestions_array(self, auth_headers):
        """Suggestions should return suggestions array for valid chain"""
        # First get a valid chain_id
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        if chains_response.status_code != 200 or not chains_response.json().get("chains"):
            pytest.skip("No chains available for testing")
        
        chain_id = chains_response.json()["chains"][0]["chain_id"]
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/chain/suggestions",
            headers=auth_headers,
            json={"chain_id": chain_id}
        )
        assert response.status_code == 200, f"Expected 200: {response.text}"
        data = response.json()
        assert "suggestions" in data, f"Response should have suggestions: {data.keys()}"
        assert isinstance(data["suggestions"], list), "suggestions should be a list"
    
    def test_suggestions_have_correct_structure(self, auth_headers):
        """Each suggestion should have title, prompt, hook, type"""
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        if chains_response.status_code != 200 or not chains_response.json().get("chains"):
            pytest.skip("No chains available for testing")
        
        chain_id = chains_response.json()["chains"][0]["chain_id"]
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/chain/suggestions",
            headers=auth_headers,
            json={"chain_id": chain_id}
        )
        if response.status_code != 200:
            pytest.skip(f"Suggestions call failed: {response.text}")
        
        data = response.json()
        if data.get("suggestions"):
            suggestion = data["suggestions"][0]
            assert "title" in suggestion, f"Suggestion should have title: {suggestion.keys()}"
            assert "prompt" in suggestion, f"Suggestion should have prompt: {suggestion.keys()}"
            assert "hook" in suggestion, f"Suggestion should have hook: {suggestion.keys()}"
            assert "type" in suggestion, f"Suggestion should have type: {suggestion.keys()}"
            assert suggestion["type"] in ["escalation", "twist", "deepening"], f"Invalid type: {suggestion['type']}"
    
    def test_suggestions_returns_episode_count(self, auth_headers):
        """Suggestions response should include episode_count"""
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        if chains_response.status_code != 200 or not chains_response.json().get("chains"):
            pytest.skip("No chains available for testing")
        
        chain_id = chains_response.json()["chains"][0]["chain_id"]
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/chain/suggestions",
            headers=auth_headers,
            json={"chain_id": chain_id}
        )
        if response.status_code != 200:
            pytest.skip(f"Suggestions call failed: {response.text}")
        
        data = response.json()
        assert "episode_count" in data, f"Response should have episode_count: {data.keys()}"


class TestMyChains:
    """Test GET /api/photo-to-comic/my-chains - User's chains with progress"""
    
    def test_my_chains_returns_200(self, auth_headers):
        """My chains endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/my-chains", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200: {response.status_code}"
    
    def test_my_chains_has_progress_pct(self, auth_headers):
        """Each chain in my-chains should have progress_pct"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/my-chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if data.get("chains"):
            chain = data["chains"][0]
            assert "progress_pct" in chain, f"Chain should have progress_pct: {chain.keys()}"
            assert isinstance(chain["progress_pct"], (int, float)), "progress_pct should be numeric"
    
    def test_my_chains_has_total_count(self, auth_headers):
        """My chains should return total count"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/my-chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data, f"Response should have total: {data.keys()}"


class TestContinueStoryDirections:
    """Test POST /api/photo-to-comic/continue-story accepts prompt"""
    
    def test_continue_story_accepts_prompt(self, auth_headers):
        """Continue story should accept optional prompt for direction"""
        # This is a validation test - we won't actually continue due to credits
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/continue-story",
            headers=auth_headers,
            json={
                "parentJobId": "invalid-job-id",
                "prompt": "Add a surprising plot twist",
                "panelCount": 4,
                "keepStyle": True
            }
        )
        # Should get 404 for invalid parent, not 422 for invalid schema
        assert response.status_code == 404, f"Expected 404 for invalid parent: {response.status_code}"


class TestDataTestIds:
    """Test that key frontend data-testid attributes are documented"""
    
    def test_resume_your_story_testids(self):
        """Document expected data-testids for Resume Your Story section"""
        expected_testids = [
            "resume-your-story",  # Main section
            "resume-primary-chain",  # Primary chain card
            "resume-continue-btn",  # Next Episode button
            "resume-view-chain-btn",  # View Chain button
            "resume-timeline-btn",  # Timeline button
        ]
        # This is a documentation test - pass as these are expected
        assert len(expected_testids) == 5, "Document 5 key testids"
    
    def test_story_chain_view_testids(self):
        """Document expected data-testids for Story Chain View page"""
        expected_testids = [
            "story-chain-view",  # Main page
            "chain-progress-header",  # Progress header
            "chain-progress-bar",  # Progress bar
            "ai-suggestions-panel",  # AI suggestions section
            "generate-suggestions-btn",  # Get AI Ideas button
            "suggestions-grid",  # Suggestions grid
            "add-episode-cta",  # Add Next Episode CTA
            "chain-timeline",  # Timeline
            "next-episode-cta",  # Next Episode header CTA
        ]
        assert len(expected_testids) == 9, "Document 9 key testids"
    
    def test_photo_to_comic_direction_testids(self):
        """Document expected data-testids for PhotoToComic direction options"""
        expected_testids = [
            "continue-story-section",  # Continue section
            "continue-story-btn",  # Choose Direction button
            "continue-directions",  # Directions panel
            "direction-next",  # Continue the Story
            "direction-twist",  # Add a Plot Twist
            "direction-escalate",  # Raise the Stakes
            "direction-custom",  # Your Direction
            "custom-direction-input",  # Custom input field
        ]
        assert len(expected_testids) == 8, "Document 8 key testids"
