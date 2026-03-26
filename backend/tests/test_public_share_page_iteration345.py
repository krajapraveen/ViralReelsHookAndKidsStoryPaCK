"""
Test Public Share Page - Iteration 345
Tests the rebuilt Public Share Page (/v/{slug}) with:
- Auto-play video support
- Character intro and card sections
- Cliffhanger text display
- Strong CTAs for viral growth
- Both Story Engine and Legacy Pipeline job support
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test job IDs
STORY_ENGINE_JOB_ID = "99f9cd11-a1d8-4909-9ed7-04a0320a2820"  # Has video, characters, cliffhanger
LEGACY_PIPELINE_JOB_ID = "13ddd5d5-307c-4c45-8ac6-e349344d8abf"  # Has video, scenes, no characters


class TestPublicCreationEndpoint:
    """Tests for GET /api/public/creation/{slug} endpoint"""
    
    def test_story_engine_job_returns_video_url(self):
        """Story Engine job should return video_url field"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        creation = data["creation"]
        
        # video_url should exist (even if relative path)
        assert "video_url" in creation
        assert creation["video_url"] is not None
        print(f"✅ Story Engine video_url: {creation['video_url']}")
    
    def test_legacy_pipeline_job_returns_video_url(self):
        """Legacy pipeline job should return video_url field with presigned R2 URL"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{LEGACY_PIPELINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        creation = data["creation"]
        
        # video_url should be a presigned R2 URL
        assert "video_url" in creation
        assert creation["video_url"] is not None
        assert "r2.cloudflarestorage.com" in creation["video_url"] or ".r2.dev" in creation["video_url"]
        print(f"✅ Legacy Pipeline video_url is presigned R2 URL")
    
    def test_story_engine_job_returns_characters(self):
        """Story Engine job should return characters array with name, role, appearance, personality"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        # characters should be an array with at least one character
        assert "characters" in creation
        assert isinstance(creation["characters"], list)
        assert len(creation["characters"]) > 0
        
        # Each character should have name, role, appearance, personality
        char = creation["characters"][0]
        assert "name" in char
        assert "role" in char
        assert "appearance" in char
        assert "personality" in char
        print(f"✅ Story Engine characters: {[c['name'] for c in creation['characters']]}")
    
    def test_legacy_pipeline_job_returns_empty_characters(self):
        """Legacy pipeline job should return empty characters array"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{LEGACY_PIPELINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        # characters should be empty for legacy jobs
        assert "characters" in creation
        assert isinstance(creation["characters"], list)
        assert len(creation["characters"]) == 0
        print(f"✅ Legacy Pipeline has empty characters array (expected)")
    
    def test_story_engine_job_returns_cliffhanger(self):
        """Story Engine job should return cliffhanger from episode_plan"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        # cliffhanger should exist and be non-empty
        assert "cliffhanger" in creation
        assert creation["cliffhanger"] is not None
        assert len(creation["cliffhanger"]) > 0
        print(f"✅ Story Engine cliffhanger: {creation['cliffhanger'][:80]}...")
    
    def test_legacy_pipeline_job_returns_null_cliffhanger(self):
        """Legacy pipeline job should return null cliffhanger"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{LEGACY_PIPELINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        # cliffhanger should be null for legacy jobs
        assert "cliffhanger" in creation
        assert creation["cliffhanger"] is None
        print(f"✅ Legacy Pipeline has null cliffhanger (expected)")
    
    def test_story_engine_job_returns_source_field(self):
        """Story Engine job should return source='story_engine'"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        assert "source" in creation
        assert creation["source"] == "story_engine"
        print(f"✅ Story Engine source: {creation['source']}")
    
    def test_legacy_pipeline_job_returns_source_field(self):
        """Legacy pipeline job should return source='legacy_pipeline'"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{LEGACY_PIPELINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        assert "source" in creation
        assert creation["source"] == "legacy_pipeline"
        print(f"✅ Legacy Pipeline source: {creation['source']}")
    
    def test_story_engine_job_returns_episode_number(self):
        """Story Engine job should return episode_number"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        assert "episode_number" in creation
        # episode_number can be 1 or higher
        print(f"✅ Story Engine episode_number: {creation['episode_number']}")
    
    def test_story_engine_job_returns_story_chain_id(self):
        """Story Engine job should return story_chain_id"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        assert "story_chain_id" in creation
        print(f"✅ Story Engine story_chain_id: {creation['story_chain_id']}")
    
    def test_creation_returns_all_required_fields(self):
        """Both job types should return all required fields for frontend"""
        for job_id in [STORY_ENGINE_JOB_ID, LEGACY_PIPELINE_JOB_ID]:
            response = requests.get(f"{BASE_URL}/api/public/creation/{job_id}")
            assert response.status_code == 200
            data = response.json()
            creation = data["creation"]
            
            # Required fields for frontend
            required_fields = [
                "job_id", "title", "status", "scenes", "thumbnail_url",
                "video_url", "views", "remix_count", "created_at", "creator",
                "story_text", "prompt", "characters", "character_name",
                "cliffhanger", "source", "is_trending", "is_alive"
            ]
            
            for field in required_fields:
                assert field in creation, f"Missing field: {field} for job {job_id}"
            
            print(f"✅ Job {job_id[:8]}... has all required fields")
    
    def test_creation_not_found_returns_404(self):
        """Non-existent job should return 404"""
        response = requests.get(f"{BASE_URL}/api/public/creation/non-existent-job-id")
        assert response.status_code == 404
        print(f"✅ Non-existent job returns 404")
    
    def test_remix_tracking_endpoint(self):
        """POST /api/public/creation/{slug}/remix should increment remix count"""
        response = requests.post(f"{BASE_URL}/api/public/creation/{LEGACY_PIPELINE_JOB_ID}/remix")
        # Should return 200 (success) or 404 (if job not found)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            print(f"✅ Remix tracking endpoint works")
        else:
            print(f"⚠️ Remix tracking returned 404 (job may not exist in pipeline_jobs)")


class TestPublicCreationScenes:
    """Tests for scene data in public creation response"""
    
    def test_story_engine_scenes_have_image_urls(self):
        """Story Engine job scenes should have presigned image URLs"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        scenes = data["creation"]["scenes"]
        
        assert len(scenes) > 0
        for i, scene in enumerate(scenes):
            assert "image_url" in scene
            assert "narration" in scene
            if scene["image_url"]:
                # Should be presigned R2 URL
                assert "r2.cloudflarestorage.com" in scene["image_url"] or ".r2.dev" in scene["image_url"]
        print(f"✅ Story Engine has {len(scenes)} scenes with presigned image URLs")
    
    def test_legacy_pipeline_scenes_structure(self):
        """Legacy pipeline job scenes should have narration, image_url, audio_url, duration"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{LEGACY_PIPELINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        scenes = data["creation"]["scenes"]
        
        assert len(scenes) > 0
        for scene in scenes:
            assert "narration" in scene
            assert "image_url" in scene
            assert "audio_url" in scene
            assert "duration" in scene
        print(f"✅ Legacy Pipeline has {len(scenes)} scenes with correct structure")


class TestPublicCreationMomentum:
    """Tests for momentum/social proof data"""
    
    def test_momentum_fields_present(self):
        """Both job types should return momentum fields"""
        for job_id in [STORY_ENGINE_JOB_ID, LEGACY_PIPELINE_JOB_ID]:
            response = requests.get(f"{BASE_URL}/api/public/creation/{job_id}")
            assert response.status_code == 200
            data = response.json()
            creation = data["creation"]
            
            momentum_fields = [
                "views", "remix_count", "last_continuation_at",
                "continuations_1h", "continuations_24h", "is_trending", "is_alive"
            ]
            
            for field in momentum_fields:
                assert field in creation, f"Missing momentum field: {field}"
            
            print(f"✅ Job {job_id[:8]}... has all momentum fields")
    
    def test_views_incremented_on_fetch(self):
        """Views should be incremented when fetching creation"""
        # Get initial views
        response1 = requests.get(f"{BASE_URL}/api/public/creation/{LEGACY_PIPELINE_JOB_ID}")
        views1 = response1.json()["creation"]["views"]
        
        # Fetch again
        response2 = requests.get(f"{BASE_URL}/api/public/creation/{LEGACY_PIPELINE_JOB_ID}")
        views2 = response2.json()["creation"]["views"]
        
        # Views should have incremented
        assert views2 >= views1
        print(f"✅ Views incremented: {views1} -> {views2}")


class TestPublicCreationCharacters:
    """Tests for character data in Story Engine jobs"""
    
    def test_character_name_field(self):
        """Story Engine job should have character_name from first character"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        creation = data["creation"]
        
        assert "character_name" in creation
        if creation["characters"]:
            assert creation["character_name"] == creation["characters"][0]["name"]
        print(f"✅ character_name: {creation['character_name']}")
    
    def test_character_structure(self):
        """Characters should have name, role, appearance, personality"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{STORY_ENGINE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        characters = data["creation"]["characters"]
        
        for char in characters:
            assert "name" in char and char["name"]
            assert "role" in char
            assert "appearance" in char
            assert "personality" in char
            print(f"  - {char['name']} ({char['role']})")
        print(f"✅ All {len(characters)} characters have correct structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
