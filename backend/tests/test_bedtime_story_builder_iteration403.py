"""
Bedtime Story Builder - Backend API Tests
Tests for /api/bedtime-story-builder/config and /api/bedtime-story-builder/generate endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestBedtimeStoryBuilderConfig:
    """Tests for /api/bedtime-story-builder/config endpoint"""
    
    def test_config_returns_200(self):
        """Config endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Config endpoint returns 200")
    
    def test_config_has_age_groups(self):
        """Config contains ageGroups array"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        data = response.json()
        assert "ageGroups" in data, "Missing ageGroups in config"
        assert len(data["ageGroups"]) >= 3, "Should have at least 3 age groups"
        assert any(ag["id"] == "3-5" for ag in data["ageGroups"]), "Missing 3-5 age group"
        assert any(ag["id"] == "6-8" for ag in data["ageGroups"]), "Missing 6-8 age group"
        assert any(ag["id"] == "9-12" for ag in data["ageGroups"]), "Missing 9-12 age group"
        print("PASS: Config has all age groups")
    
    def test_config_has_themes(self):
        """Config contains themes array"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        data = response.json()
        assert "themes" in data, "Missing themes in config"
        assert len(data["themes"]) >= 5, "Should have at least 5 themes"
        print(f"PASS: Config has {len(data['themes'])} themes")
    
    def test_config_has_morals(self):
        """Config contains morals array"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        data = response.json()
        assert "morals" in data, "Missing morals in config"
        assert len(data["morals"]) >= 5, "Should have at least 5 morals"
        print(f"PASS: Config has {len(data['morals'])} morals")
    
    def test_config_has_lengths(self):
        """Config contains lengths array with 3, 5, 8 minute options"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        data = response.json()
        assert "lengths" in data, "Missing lengths in config"
        length_ids = [l["id"] for l in data["lengths"]]
        assert "3" in length_ids, "Missing 3 min length"
        assert "5" in length_ids, "Missing 5 min length"
        assert "8" in length_ids, "Missing 8 min length"
        print("PASS: Config has all length options")
    
    def test_config_has_voice_styles(self):
        """Config contains voiceStyles array"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        data = response.json()
        assert "voiceStyles" in data, "Missing voiceStyles in config"
        assert len(data["voiceStyles"]) >= 3, "Should have at least 3 voice styles"
        print(f"PASS: Config has {len(data['voiceStyles'])} voice styles")
    
    def test_config_has_pricing(self):
        """Config contains pricing info"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        data = response.json()
        assert "pricing" in data, "Missing pricing in config"
        assert data["pricing"]["story"] == 10, "Story should cost 10 credits"
        print("PASS: Config has correct pricing")


class TestBedtimeStoryBuilderGenerate:
    """Tests for /api/bedtime-story-builder/generate endpoint"""
    
    def test_generate_requires_auth(self):
        """Generate endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json={
                "age_group": "6-8",
                "theme": "Friendship",
                "moral": "Be kind",
                "length": "3",
                "voice_style": "calm_parent"
            }
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Generate endpoint requires auth")
    
    def test_generate_returns_structured_json(self, auth_headers):
        """Generate returns structured JSON with scenes array"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "6-8",
                "theme": "Friendship",
                "moral": "Be kind",
                "length": "3",
                "voice_style": "calm_parent",
                "child_name": "TestChild",
                "mood": "calm"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check success flag
        assert data.get("success") == True, "Response should have success=true"
        
        # Check story structure
        story = data.get("story", {})
        assert "title" in story, "Story should have title"
        assert "scenes" in story, "Story should have scenes array"
        assert isinstance(story["scenes"], list), "Scenes should be a list"
        assert len(story["scenes"]) >= 3, f"Should have at least 3 scenes, got {len(story['scenes'])}"
        
        # Check scene structure
        for i, scene in enumerate(story["scenes"]):
            assert "text" in scene, f"Scene {i} missing text"
            assert "scene_type" in scene, f"Scene {i} missing scene_type"
            assert "emotion" in scene, f"Scene {i} missing emotion"
        
        print(f"PASS: Generate returns structured JSON with {len(story['scenes'])} scenes")
    
    def test_generate_with_empty_child_name(self, auth_headers):
        """Generate works with empty child name (optional field)"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "3-5",
                "theme": "Bedtime Calm",
                "moral": "Be thankful",
                "length": "3",
                "voice_style": "gentle_teacher",
                "child_name": None,
                "mood": "sleepy"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Should succeed with empty child name"
        print("PASS: Generate works with empty child name")
    
    def test_generate_deducts_credits(self, auth_headers):
        """Generate deducts 10 credits"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "6-8",
                "theme": "Magic",
                "moral": "Be brave",
                "length": "5",
                "voice_style": "playful_storyteller",
                "mood": "adventure"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("credits_used") == 10, "Should use 10 credits"
        assert "remaining_credits" in data, "Should return remaining credits"
        print(f"PASS: Generate deducts 10 credits, remaining: {data['remaining_credits']}")
    
    def test_generate_invalid_age_group(self, auth_headers):
        """Generate rejects invalid age group"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "invalid",
                "theme": "Friendship",
                "moral": "Be kind",
                "length": "3",
                "voice_style": "calm_parent"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Generate rejects invalid age group")
    
    def test_generate_invalid_length(self, auth_headers):
        """Generate rejects invalid length"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "6-8",
                "theme": "Friendship",
                "moral": "Be kind",
                "length": "10",
                "voice_style": "calm_parent"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Generate rejects invalid length")
    
    def test_generate_with_remix_type(self, auth_headers):
        """Generate works with remix_type parameter"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "6-8",
                "theme": "Animals",
                "moral": "Help friends",
                "length": "3",
                "voice_style": "calm_parent",
                "child_name": "Alex",
                "mood": "funny",
                "remix_type": "space"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Remix should succeed"
        print("PASS: Generate works with remix_type")
    
    def test_generate_has_voice_notes(self, auth_headers):
        """Generate returns voice_notes array"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "9-12",
                "theme": "Adventure",
                "moral": "Try again",
                "length": "5",
                "voice_style": "playful_storyteller"
            }
        )
        assert response.status_code == 200
        data = response.json()
        story = data.get("story", {})
        assert "voice_notes" in story, "Story should have voice_notes"
        print(f"PASS: Generate returns {len(story.get('voice_notes', []))} voice notes")
    
    def test_generate_has_sfx_cues(self, auth_headers):
        """Generate returns sfx_cues array"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "3-5",
                "theme": "Nature",
                "moral": "Be thankful",
                "length": "3",
                "voice_style": "gentle_teacher"
            }
        )
        assert response.status_code == 200
        data = response.json()
        story = data.get("story", {})
        assert "sfx_cues" in story, "Story should have sfx_cues"
        print(f"PASS: Generate returns {len(story.get('sfx_cues', []))} SFX cues")
    
    def test_generate_has_metadata(self, auth_headers):
        """Generate returns metadata with character and place"""
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=auth_headers,
            json={
                "age_group": "6-8",
                "theme": "Dreams",
                "moral": "Believe in yourself",
                "length": "5",
                "voice_style": "calm_parent",
                "child_name": "Luna"
            }
        )
        assert response.status_code == 200
        data = response.json()
        story = data.get("story", {})
        metadata = story.get("metadata", {})
        assert "character" in metadata, "Metadata should have character"
        assert "word_count" in metadata, "Metadata should have word_count"
        print(f"PASS: Generate returns metadata with character: {metadata.get('character')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
