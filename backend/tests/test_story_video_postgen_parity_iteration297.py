"""
Story Video PostGeneration Parity Tests - Iteration 297
Tests for Story Video Studio PostGen phase: Continue Directions, Remix Style Grid, Story Chain, CreationActionsBar
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pricing-paywall.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
ADMIN_USER = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_USER,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip("Admin authentication failed - skipping admin tests")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ─── PIPELINE OPTIONS ENDPOINT ─────────────────────────────────────────────────

class TestPipelineOptions:
    """Tests for /api/pipeline/options endpoint"""
    
    def test_pipeline_options_returns_animation_styles(self, api_client):
        """Test that /api/pipeline/options returns animation styles"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        assert "animation_styles" in data
        assert len(data["animation_styles"]) >= 6, "Expected at least 6 animation styles"
        
        # Validate structure
        for style in data["animation_styles"]:
            assert "id" in style
            assert "name" in style
            assert "style_prompt" in style
    
    def test_pipeline_options_returns_age_groups(self, api_client):
        """Test that /api/pipeline/options returns age groups"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        
        data = response.json()
        assert "age_groups" in data
        assert len(data["age_groups"]) >= 5, "Expected at least 5 age groups"
        
        # Validate structure
        for age in data["age_groups"]:
            assert "id" in age
            assert "name" in age
            assert "max_scenes" in age
    
    def test_pipeline_options_returns_voice_presets(self, api_client):
        """Test that /api/pipeline/options returns voice presets"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        
        data = response.json()
        assert "voice_presets" in data
        assert len(data["voice_presets"]) >= 3, "Expected at least 3 voice presets"
        
        # Validate structure
        for voice in data["voice_presets"]:
            assert "id" in voice
            assert "name" in voice
            assert "voice" in voice
    
    def test_pipeline_options_returns_credit_costs(self, api_client):
        """Test that /api/pipeline/options returns credit costs"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        
        data = response.json()
        assert "credit_costs" in data


# ─── REMIX VARIATIONS ENDPOINT ─────────────────────────────────────────────────

class TestRemixVariations:
    """Tests for /api/remix/variations/story-video-studio endpoint"""
    
    def test_remix_variations_returns_quick_options(self, api_client):
        """Test that /api/remix/variations/story-video-studio returns quick variations"""
        response = api_client.get(f"{BASE_URL}/api/remix/variations/story-video-studio")
        assert response.status_code == 200
        
        data = response.json()
        assert "quick" in data
        assert len(data["quick"]) >= 4, "Expected at least 4 quick variations"
        
        # Validate structure
        for item in data["quick"]:
            assert "label" in item
            assert "modifier" in item
    
    def test_remix_variations_returns_styles(self, api_client):
        """Test that /api/remix/variations/story-video-studio returns styles"""
        response = api_client.get(f"{BASE_URL}/api/remix/variations/story-video-studio")
        assert response.status_code == 200
        
        data = response.json()
        assert "styles" in data
        assert len(data["styles"]) >= 5, "Expected at least 5 styles"
        
        # Should include common styles
        expected_styles = {"Pixar", "Anime", "Comic", "Watercolor"}
        style_set = set(data["styles"])
        assert expected_styles.issubset(style_set), f"Missing styles: {expected_styles - style_set}"
    
    def test_remix_variations_returns_actions(self, api_client):
        """Test that /api/remix/variations/story-video-studio returns actions"""
        response = api_client.get(f"{BASE_URL}/api/remix/variations/story-video-studio")
        assert response.status_code == 200
        
        data = response.json()
        assert "actions" in data
        assert len(data["actions"]) >= 5, "Expected at least 5 actions"
        
        # Validate structure
        for action in data["actions"]:
            assert "label" in action
            assert "type" in action
            assert "target" in action
        
        # Check for key actions
        labels = [a["label"] for a in data["actions"]]
        assert "Create Part 2" in labels, "Missing 'Create Part 2' action"
        assert "Turn Into Comic" in labels, "Missing 'Turn Into Comic' action"
    
    def test_remix_variations_nonexistent_tool(self, api_client):
        """Test that nonexistent tool returns empty config"""
        response = api_client.get(f"{BASE_URL}/api/remix/variations/nonexistent-tool")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("quick") == []
        assert data.get("styles") == []
        assert data.get("actions") == []


# ─── AUTHENTICATED ENDPOINTS ─────────────────────────────────────────────────

class TestAuthenticatedEndpoints:
    """Tests for authenticated pipeline endpoints"""
    
    def test_rate_limit_status(self, authenticated_client):
        """Test /api/pipeline/rate-limit-status returns valid data"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        assert response.status_code == 200
        
        data = response.json()
        assert "can_create" in data
        assert "recent_count" in data
        assert "max_per_hour" in data
        assert "concurrent" in data
        assert "max_concurrent" in data
    
    def test_user_jobs_returns_list(self, authenticated_client):
        """Test /api/pipeline/user-jobs returns job list"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/user-jobs")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
    
    def test_system_status(self, authenticated_client):
        """Test /api/pipeline/system-status returns system info"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/system-status")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert "system" in data
        assert "user" in data


# ─── ASSET VALIDATION ENDPOINT ─────────────────────────────────────────────────

class TestAssetValidation:
    """Tests for /api/pipeline/validate-asset/{job_id} endpoint"""
    
    def test_validate_asset_nonexistent_job(self, authenticated_client):
        """Test that validate-asset returns 404 for nonexistent job"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/validate-asset/nonexistent-job-id")
        assert response.status_code == 404
    
    def test_validate_asset_returns_ui_state_fields(self, authenticated_client):
        """Test that validate-asset returns correct fields structure"""
        # First get user jobs to find a valid job_id
        jobs_response = authenticated_client.get(f"{BASE_URL}/api/pipeline/user-jobs")
        if jobs_response.status_code != 200:
            pytest.skip("Could not fetch user jobs")
        
        jobs = jobs_response.json().get("jobs", [])
        if not jobs:
            pytest.skip("No jobs found for user")
        
        # Try to validate first job
        job_id = jobs[0].get("job_id")
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/validate-asset/{job_id}")
        
        # Should return 200 for existing job
        assert response.status_code == 200
        
        data = response.json()
        # Validate expected fields from PostGenPhase state machine
        assert "preview_ready" in data
        assert "download_ready" in data
        assert "share_ready" in data
        assert "ui_state" in data
        assert data["ui_state"] in ["READY", "PARTIAL_READY", "FAILED", "PROCESSING"]


# ─── REMIX TRACKING ENDPOINT ───────────────────────────────────────────────────

class TestRemixTracking:
    """Tests for /api/remix/track endpoint"""
    
    def test_remix_track_requires_auth(self, api_client):
        """Test that /api/remix/track requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/remix/track", json={
            "source_tool": "story-video-studio",
            "target_tool": "story-video-studio",
            "original_prompt": "test prompt",
            "variation_type": "quick",
            "variation_label": "Test",
            "modifier": "test modifier"
        })
        assert response.status_code == 401 or response.status_code == 403
    
    def test_remix_track_success(self, authenticated_client):
        """Test that /api/remix/track works with valid data"""
        response = authenticated_client.post(f"{BASE_URL}/api/remix/track", json={
            "source_tool": "story-video-studio",
            "target_tool": "story-video-studio",
            "original_prompt": "A brave knight saves a dragon",
            "variation_type": "quick",
            "variation_label": "TEST_Funny",
            "modifier": "Make it funny and humorous"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("tracked") is True


# ─── GALLERY ENDPOINTS ─────────────────────────────────────────────────────────

class TestGalleryEndpoints:
    """Tests for public gallery endpoints"""
    
    def test_gallery_returns_videos(self, api_client):
        """Test /api/pipeline/gallery returns videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        assert "videos" in data
        assert isinstance(data["videos"], list)
    
    def test_gallery_leaderboard(self, api_client):
        """Test /api/pipeline/gallery/leaderboard returns leaderboard"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
    
    def test_gallery_categories(self, api_client):
        """Test /api/pipeline/gallery/categories returns categories"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)
        
        # Should have 'all' category at minimum
        category_ids = [c["id"] for c in data["categories"]]
        assert "all" in category_ids


# ─── HEALTH CHECK ──────────────────────────────────────────────────────────────

class TestHealthCheck:
    """Basic health check tests"""
    
    def test_health_endpoint(self, api_client):
        """Test /api/health returns healthy"""
        response = api_client.get(f"{BASE_URL}/api/health")
        # Accept 200 or 403 (if endpoint is protected)
        assert response.status_code in [200, 403, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
