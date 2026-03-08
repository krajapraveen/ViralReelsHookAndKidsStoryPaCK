"""
Story Video Studio - Phase 1-4 Endpoints Test Suite
Iteration 127: Testing all Story Video Studio endpoints

Endpoints Tested:
- Phase 1: GET /styles, GET /pricing, POST /projects/create, POST /generate-scenes, GET /prompt-pack
- Phase 2-4: GET /voice/config, GET /music/library, POST /music/upload
"""

import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestStoryVideoStudioPhase1:
    """Phase 1 - Story to Scenes Endpoints"""
    
    def test_get_styles_returns_6_styles(self):
        """GET /api/story-video-studio/styles - should return 6 video styles"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/styles")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "styles" in data
        assert len(data["styles"]) == 6
        
        # Verify style structure
        style_ids = [s["id"] for s in data["styles"]]
        expected_styles = ["storybook", "comic", "watercolor", "cinematic", "anime", "3d_cartoon"]
        for style_id in expected_styles:
            assert style_id in style_ids, f"Style '{style_id}' missing from response"
        
        # Verify each style has required fields
        for style in data["styles"]:
            assert "id" in style
            assert "name" in style
            assert "description" in style
            assert "prompt_style" in style

    def test_get_pricing_returns_4_credit_costs(self):
        """GET /api/story-video-studio/pricing - should return credit pricing with 4 items"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/pricing")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "pricing" in data
        
        # Verify all 4 credit costs (plus watermark_removal = 5)
        pricing = data["pricing"]
        assert "scene_generation" in pricing
        assert "image_per_scene" in pricing
        assert "voice_per_minute" in pricing
        assert "video_render" in pricing
        
        # Verify numeric values
        assert pricing["scene_generation"] == 5
        assert pricing["image_per_scene"] == 10
        assert pricing["voice_per_minute"] == 10
        assert pricing["video_render"] == 20
        
        # Verify example calculation
        assert "example_3min_video" in data
        example = data["example_3min_video"]
        assert example["total"] == 115  # 5 + 60 + 30 + 20

    def test_create_project_success(self):
        """POST /api/story-video-studio/projects/create - creates a new project"""
        payload = {
            "story_text": "Once upon a time in a faraway kingdom, there lived a young prince named Leo. Leo loved to explore the forest near the castle. One day he found a magical talking bird named Sparrow. Together they went on an adventure to find the hidden treasure of the ancient kings.",
            "title": "Test Story - Prince Leo",
            "language": "english",
            "age_group": "kids_5_8",
            "style_id": "storybook"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "project_id" in data
        assert len(data["project_id"]) > 0
        
        # Store project_id for cleanup
        TestStoryVideoStudioPhase1.test_project_id = data["project_id"]
        
        # Verify project data
        assert data["data"]["title"] == payload["title"]
        assert data["data"]["language"] == payload["language"]
        assert data["data"]["status"] == "draft"

    def test_create_project_rejects_copyrighted_content(self):
        """POST /api/story-video-studio/projects/create - rejects copyrighted characters"""
        payload = {
            "story_text": "Mickey Mouse went to Disneyland and met his friend Spider-Man. They had a great adventure together.",
            "title": "Disney Adventure",
            "language": "english",
            "age_group": "kids_5_8",
            "style_id": "storybook"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json=payload
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "copyrighted" in data["detail"].lower() or "blocked" in data["detail"].lower()

    def test_create_project_rejects_short_story(self):
        """POST /api/story-video-studio/projects/create - rejects stories under 50 chars"""
        payload = {
            "story_text": "Short story",
            "title": "Too Short",
            "language": "english",
            "age_group": "kids_5_8",
            "style_id": "storybook"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json=payload
        )
        assert response.status_code == 422  # Validation error

    def test_get_existing_project_prompt_pack(self):
        """GET /api/story-video-studio/projects/{id}/prompt-pack - returns prompt pack for existing project"""
        # Use the test project that was created during Phase 1 testing
        project_id = "65a17153-fa83-49c8-a37b-7ba8ba4f3727"
        
        response = requests.get(f"{BASE_URL}/api/story-video-studio/projects/{project_id}/prompt-pack")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "project_id" in data
        assert "character_bible" in data
        assert "scene_prompts" in data
        assert "voice_scripts" in data
        assert "stats" in data
        
        # Verify scene prompts structure
        assert len(data["scene_prompts"]) > 0
        for prompt in data["scene_prompts"]:
            assert "scene_number" in prompt
            assert "title" in prompt
            assert "prompt" in prompt
            assert "negative_prompt" in prompt

    def test_get_project_details(self):
        """GET /api/story-video-studio/projects/{id} - returns project details"""
        project_id = "65a17153-fa83-49c8-a37b-7ba8ba4f3727"
        
        response = requests.get(f"{BASE_URL}/api/story-video-studio/projects/{project_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "project" in data
        assert data["project"]["project_id"] == project_id

    def test_list_projects(self):
        """GET /api/story-video-studio/projects - lists user projects"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/projects")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "projects" in data
        assert isinstance(data["projects"], list)


class TestStoryVideoStudioPhase2Voice:
    """Phase 3 - Voice Generation Config Endpoints"""
    
    def test_get_voice_config_returns_prepaid_mode(self):
        """GET /api/story-video-studio/generation/voice/config - returns voice config with PREPAID_ONLY mode"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/voice/config")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "mode" in data
        assert data["mode"] == "PREPAID_ONLY"  # Default mode as per requirements
        
        # Verify available voices
        assert "available_voices" in data
        voices = data["available_voices"]
        assert len(voices) == 6  # alloy, echo, fable, onyx, nova, shimmer
        
        voice_ids = [v["id"] for v in voices]
        expected_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        for voice_id in expected_voices:
            assert voice_id in voice_ids, f"Voice '{voice_id}' missing"
        
        # Verify voice structure
        for voice in voices:
            assert "id" in voice
            assert "name" in voice
            assert "description" in voice
        
        # Verify cost info
        assert "cost_per_minute" in data
        assert data["cost_per_minute"] == 10
        
        # Verify requirements info
        assert "requirements" in data
        assert "PREPAID_ONLY" in data["requirements"]


class TestStoryVideoStudioPhase3Music:
    """Phase 4 - Music Library & Upload Endpoints"""
    
    def test_get_music_library_returns_pixabay_tracks(self):
        """GET /api/story-video-studio/generation/music/library - returns music tracks with Pixabay"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/music/library")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "music_tracks" in data
        
        tracks = data["music_tracks"]
        assert len(tracks) >= 5  # At least 5 Pixabay sample tracks
        
        # Verify Pixabay tracks structure
        pixabay_tracks = [t for t in tracks if t.get("source") == "pixabay"]
        assert len(pixabay_tracks) >= 5
        
        # Verify track structure
        for track in pixabay_tracks:
            assert "id" in track
            assert "name" in track
            assert "duration" in track
            assert "url" in track
            assert "source" in track
            assert "license" in track
            assert track["source"] == "pixabay"
            assert "pixabay" in track["license"].lower()
        
        # Verify categories
        assert "categories" in data
        expected_categories = ["bedtime", "adventure", "fantasy", "kids", "cinematic", "user_upload"]
        for cat in expected_categories:
            assert cat in data["categories"], f"Category '{cat}' missing"
        
        # Verify license info
        assert "license_info" in data
        assert "pixabay" in data["license_info"]
        assert "user_upload" in data["license_info"]

    def test_music_library_track_details(self):
        """Verify specific Pixabay track details"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/music/library")
        assert response.status_code == 200
        
        data = response.json()
        tracks = data["music_tracks"]
        
        # Verify expected track names
        track_names = [t["name"] for t in tracks]
        expected_tracks = ["Soft Piano Dreams", "Epic Adventure", "Magical Forest", "Happy Kids Playing", "Cinematic Emotional"]
        
        for name in expected_tracks:
            assert name in track_names, f"Track '{name}' missing"

    def test_music_upload_requires_confirm_rights(self):
        """POST /api/story-video-studio/generation/music/upload - requires rights confirmation"""
        # Try upload without confirming rights
        files = {'file': ('test.mp3', b'fake audio data', 'audio/mpeg')}
        data_form = {'name': 'Test Track', 'confirm_rights': 'false'}
        
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/generation/music/upload",
            files=files,
            data=data_form
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "rights" in data["detail"].lower()


class TestStoryVideoStudioAnalytics:
    """Analytics Endpoint"""
    
    def test_get_analytics(self):
        """GET /api/story-video-studio/analytics - returns studio analytics"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/analytics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "analytics" in data
        
        analytics = data["analytics"]
        assert "total_projects" in analytics
        assert "projects_by_status" in analytics
        assert "popular_styles" in analytics
        assert "total_credits_spent" in analytics


class TestStoryVideoStudioErrorHandling:
    """Error Handling Tests"""
    
    def test_get_nonexistent_project(self):
        """GET /api/story-video-studio/projects/{id} - 404 for nonexistent project"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/projects/nonexistent-id-12345")
        assert response.status_code == 404
        
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_prompt_pack_for_draft_project_fails(self):
        """GET /api/story-video-studio/projects/{id}/prompt-pack - fails for draft project"""
        # Create a draft project first
        payload = {
            "story_text": "A simple story about a cat named Whiskers who loved to play in the garden. One sunny day, Whiskers found a butterfly and chased it through the flowers.",
            "title": "Whiskers Draft",
            "language": "english",
            "age_group": "kids_3_5",
            "style_id": "storybook"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json=payload
        )
        
        if create_response.status_code == 200:
            project_id = create_response.json()["project_id"]
            
            # Try to get prompt pack for draft
            response = requests.get(f"{BASE_URL}/api/story-video-studio/projects/{project_id}/prompt-pack")
            assert response.status_code == 400
            
            data = response.json()
            assert "generate scenes first" in data["detail"].lower()
            
            # Cleanup
            requests.delete(f"{BASE_URL}/api/story-video-studio/projects/{project_id}")


class TestFrontendRequirements:
    """Tests verifying frontend requirements are met by backend"""
    
    def test_pricing_has_4_items_for_display(self):
        """Verify pricing endpoint returns data for 4 credit cost cards"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/pricing")
        assert response.status_code == 200
        
        data = response.json()
        pricing = data["pricing"]
        
        # Frontend shows 4 pricing cards: scene_generation, image_per_scene, voice_per_minute, video_render
        required_keys = ["scene_generation", "image_per_scene", "voice_per_minute", "video_render"]
        for key in required_keys:
            assert key in pricing
            assert isinstance(pricing[key], int)

    def test_styles_have_all_fields_for_display(self):
        """Verify styles have all fields needed for frontend display"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/styles")
        assert response.status_code == 200
        
        data = response.json()
        for style in data["styles"]:
            assert "id" in style
            assert "name" in style
            assert "description" in style
            assert len(style["name"]) > 0
            assert len(style["description"]) > 0

    def test_voice_config_has_voice_options_for_select(self):
        """Verify voice config provides options for frontend Select component"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/voice/config")
        assert response.status_code == 200
        
        data = response.json()
        voices = data["available_voices"]
        
        for voice in voices:
            assert "id" in voice
            assert "name" in voice
            assert "description" in voice


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_projects():
    """Clean up test projects after all tests"""
    yield
    # Cleanup test projects created during testing
    try:
        if hasattr(TestStoryVideoStudioPhase1, 'test_project_id'):
            requests.delete(f"{BASE_URL}/api/story-video-studio/projects/{TestStoryVideoStudioPhase1.test_project_id}")
    except:
        pass
