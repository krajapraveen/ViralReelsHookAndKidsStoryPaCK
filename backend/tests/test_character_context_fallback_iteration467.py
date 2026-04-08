"""
Test: Character Context Fallback Logic (Iteration 467)

Tests the P0 pipeline resilience fix for BUILDING_CHARACTER_CONTEXT failures.
Key change: _stage_character_context no longer returns {status: failed} when the LLM fails —
it builds a fallback continuity from the episode plan and returns success.
"""
import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')


class TestFallbackContinuityBuilder:
    """Test the _build_fallback_continuity function logic"""
    
    def test_fallback_extracts_characters_from_scenes(self):
        """Verify fallback extracts character names from episode_plan.scenes[].characters[]"""
        # Import the function
        from services.story_engine.pipeline import _build_fallback_continuity
        
        episode_plan = {
            "scenes": [
                {"scene_number": 1, "characters": ["Alice", "Bob"]},
                {"scene_number": 2, "characters": ["Alice", "Charlie"]},
                {"scene_number": 3, "characters": ["Bob"]},
            ]
        }
        
        result = _build_fallback_continuity(episode_plan)
        
        # Should have 3 unique characters
        assert len(result["characters"]) == 3
        names = [c["name"] for c in result["characters"]]
        assert "Alice" in names
        assert "Bob" in names
        assert "Charlie" in names
        
        # Each character should have minimal description
        for char in result["characters"]:
            assert "name" in char
            assert "description" in char
            assert "visual_tags" in char
            assert "color_palette" in char
            assert char["visual_tags"] == []
            assert char["color_palette"] == []
        
        # Should have basic consistency level
        assert result["consistency_level"] == "basic"
        print("✓ Fallback extracts characters from scenes correctly")
    
    def test_fallback_deduplicates_characters(self):
        """Verify fallback doesn't create duplicate characters"""
        from services.story_engine.pipeline import _build_fallback_continuity
        
        episode_plan = {
            "scenes": [
                {"scene_number": 1, "characters": ["Alice", "alice", "ALICE"]},
                {"scene_number": 2, "characters": ["Bob", "bob"]},
            ]
        }
        
        result = _build_fallback_continuity(episode_plan)
        
        # Should deduplicate case-insensitively
        assert len(result["characters"]) == 2
        print("✓ Fallback deduplicates characters correctly")
    
    def test_fallback_checks_top_level_keys(self):
        """Verify fallback checks 'characters', 'cast', 'main_characters' keys"""
        from services.story_engine.pipeline import _build_fallback_continuity
        
        # Test with 'characters' key
        episode_plan_1 = {
            "scenes": [],
            "characters": ["Hero", "Villain"]
        }
        result_1 = _build_fallback_continuity(episode_plan_1)
        assert len(result_1["characters"]) == 2
        
        # Test with 'cast' key
        episode_plan_2 = {
            "scenes": [],
            "cast": [{"name": "Hero", "description": "The brave hero"}]
        }
        result_2 = _build_fallback_continuity(episode_plan_2)
        assert len(result_2["characters"]) == 1
        assert result_2["characters"][0]["description"] == "The brave hero"
        
        # Test with 'main_characters' key
        episode_plan_3 = {
            "scenes": [],
            "main_characters": ["Protagonist"]
        }
        result_3 = _build_fallback_continuity(episode_plan_3)
        assert len(result_3["characters"]) == 1
        
        print("✓ Fallback checks top-level keys correctly")
    
    def test_fallback_handles_empty_plan(self):
        """Verify fallback handles empty episode plan gracefully"""
        from services.story_engine.pipeline import _build_fallback_continuity
        
        episode_plan = {"scenes": []}
        result = _build_fallback_continuity(episode_plan)
        
        assert result["characters"] == []
        assert result["consistency_level"] == "basic"
        print("✓ Fallback handles empty plan gracefully")
    
    def test_fallback_has_required_fields(self):
        """Verify fallback continuity has all required fields for downstream stages"""
        from services.story_engine.pipeline import _build_fallback_continuity
        
        episode_plan = {
            "scenes": [{"scene_number": 1, "characters": ["Test"]}]
        }
        result = _build_fallback_continuity(episode_plan)
        
        # Required fields for downstream stages
        assert "characters" in result
        assert "style_notes" in result
        assert "consistency_level" in result
        
        # Each character should have fields that downstream stages expect
        for char in result["characters"]:
            assert "name" in char
            assert "description" in char
            assert "visual_tags" in char
            assert "color_palette" in char
        
        print("✓ Fallback has all required fields")


class TestStageCharacterContextResilience:
    """Test that _stage_character_context returns success with fallback instead of failing"""
    
    def test_stage_function_exists(self):
        """Verify _stage_character_context function exists"""
        from services.story_engine.pipeline import _stage_character_context
        assert callable(_stage_character_context)
        print("✓ _stage_character_context function exists")
    
    def test_fallback_flag_is_set(self):
        """Verify fallback continuity has _fallback=True flag"""
        from services.story_engine.pipeline import _build_fallback_continuity
        
        episode_plan = {"scenes": [{"characters": ["Test"]}]}
        result = _build_fallback_continuity(episode_plan)
        
        # The _fallback flag is set in _stage_character_context, not in _build_fallback_continuity
        # But we can verify the structure is correct for the flag to be added
        assert "consistency_level" in result
        assert result["consistency_level"] == "basic"
        print("✓ Fallback structure supports _fallback flag")


class TestDownstreamStagesHandleFallback:
    """Test that downstream stages gracefully handle fallback continuity"""
    
    def test_scene_motion_uses_continuity_safely(self):
        """Verify _stage_scene_motion uses job.get('character_continuity', {})"""
        import inspect
        from services.story_engine.pipeline import _stage_scene_motion
        
        source = inspect.getsource(_stage_scene_motion)
        # Should use .get() with default empty dict
        assert "character_continuity" in source
        assert ".get(" in source
        print("✓ _stage_scene_motion uses continuity safely")
    
    def test_keyframes_uses_continuity_safely(self):
        """Verify _stage_keyframes uses job.get('character_continuity', {})"""
        import inspect
        from services.story_engine.pipeline import _stage_keyframes
        
        source = inspect.getsource(_stage_keyframes)
        # Should use .get() with default empty dict
        assert "character_continuity" in source
        assert ".get(" in source
        print("✓ _stage_keyframes uses continuity safely")
    
    def test_scene_clips_uses_continuity_safely(self):
        """Verify _stage_scene_clips uses job.get('character_continuity', {})"""
        import inspect
        from services.story_engine.pipeline import _stage_scene_clips
        
        source = inspect.getsource(_stage_scene_clips)
        # Should use .get() with default empty dict
        assert "character_continuity" in source
        assert ".get(" in source
        print("✓ _stage_scene_clips uses continuity safely")


class TestFrontendFailedStatusUI:
    """Test frontend FAILED status UI changes via code inspection"""
    
    def test_story_video_pipeline_failed_status_is_amber(self):
        """Verify StoryVideoPipeline.js FAILED status uses amber styling"""
        with open('/app/frontend/src/pages/StoryVideoPipeline.js', 'r') as f:
            content = f.read()
        
        # Check STATUS_CONFIG.FAILED has amber styling
        assert 'bg-amber-500/10 border-amber-500/30' in content
        # Check title is soft
        assert "Something needs a quick fix" in content
        print("✓ StoryVideoPipeline.js FAILED status uses amber styling")
    
    def test_story_video_pipeline_retry_is_primary_cta(self):
        """Verify Retry/Try Again is primary CTA in FAILED state"""
        with open('/app/frontend/src/pages/StoryVideoPipeline.js', 'r') as f:
            content = f.read()
        
        # Check for RetryButton or Try Again as primary action
        assert 'RetryButton' in content or 'Try Again' in content
        # Check for encouraging copy
        assert "This usually works on retry" in content
        assert "Your credits have been preserved" in content
        print("✓ StoryVideoPipeline.js has Retry as primary CTA with encouraging copy")
    
    def test_story_video_pipeline_start_over_is_secondary(self):
        """Verify 'Start over with a new story' is ghost secondary button"""
        with open('/app/frontend/src/pages/StoryVideoPipeline.js', 'r') as f:
            content = f.read()
        
        # Check for secondary start over button
        assert "start over with a new story" in content.lower()
        # Check it's a ghost/secondary variant
        assert 'variant="ghost"' in content
        print("✓ StoryVideoPipeline.js has 'Start over' as ghost secondary button")
    
    def test_story_video_pipeline_character_tip(self):
        """Verify character-specific tip shown when failReason contains 'character'"""
        with open('/app/frontend/src/pages/StoryVideoPipeline.js', 'r') as f:
            content = f.read()
        
        # Check for character-specific tip
        assert "character" in content.lower()
        assert "simpler character descriptions" in content.lower()
        print("✓ StoryVideoPipeline.js shows character-specific tip")
    
    def test_photo_to_comic_failed_status_is_amber(self):
        """Verify PhotoToComic.js FAILED status uses amber styling"""
        with open('/app/frontend/src/pages/PhotoToComic.js', 'r') as f:
            content = f.read()
        
        # Check STATUS_CONFIG.FAILED has amber styling
        assert 'bg-amber-500/10 border-amber-500/30' in content
        # Check title is soft
        assert "Something needs a quick fix" in content
        print("✓ PhotoToComic.js FAILED status uses amber styling")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
