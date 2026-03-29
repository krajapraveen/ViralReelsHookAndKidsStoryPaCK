"""
Continue Story Loop Optimization Tests - Iteration 362
Tests for the 5-part Continue Story Loop feature:
1. StoryPreview.js Continue overlay and CTAs
2. PublicCreation.js post-video overlay with cliffhanger
3. StoryVideoPipeline.js remix_data handler with hook_text/characters
4. Backend planning_llm.py cliffhanger enforcement
5. Homepage story cards with Continue Story CTAs
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')


class TestStoryFeedAPI:
    """Test story feed API returns data needed for Continue Story flow"""
    
    def test_story_feed_returns_trending_stories(self):
        """Story feed should return trending stories with hook_text for cliffhanger display"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Story feed failed: {response.text}"
        
        data = response.json()
        assert "trending_stories" in data, "Missing trending_stories in response"
        assert len(data["trending_stories"]) > 0, "No trending stories returned"
        
        # Verify first story has required fields for Continue flow
        story = data["trending_stories"][0]
        assert "job_id" in story, "Missing job_id in story"
        assert "title" in story, "Missing title in story"
        # hook_text is the cliffhanger text used in Continue CTAs
        assert "hook_text" in story or "story_prompt" in story, "Missing hook_text or story_prompt"
        
    def test_story_feed_returns_featured_story(self):
        """Featured story should have all fields needed for hero Continue CTA"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        if "featured_story" in data and data["featured_story"]:
            featured = data["featured_story"]
            assert "job_id" in featured, "Featured story missing job_id"
            assert "title" in featured, "Featured story missing title"
            # animation_style needed for prefill
            assert "animation_style" in featured or "style" in featured, "Featured story missing animation_style"


class TestStoryPreviewAPI:
    """Test story preview endpoint returns cliffhanger and characters for Continue flow"""
    
    def test_preview_endpoint_exists(self):
        """Preview endpoint should be accessible"""
        # Get a valid job_id from story feed
        feed_response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert feed_response.status_code == 200
        
        data = feed_response.json()
        if data.get("trending_stories"):
            job_id = data["trending_stories"][0]["job_id"]
            
            # Test preview endpoint
            preview_response = requests.get(f"{BASE_URL}/api/story-engine/preview/{job_id}")
            # May return 404 if job doesn't exist or 200 with preview data
            assert preview_response.status_code in [200, 404], f"Unexpected status: {preview_response.status_code}"
            
            if preview_response.status_code == 200:
                preview_data = preview_response.json()
                if preview_data.get("success") and preview_data.get("preview"):
                    preview = preview_data["preview"]
                    # Verify cliffhanger field exists (may be null)
                    assert "cliffhanger" in preview or "scenes" in preview, "Preview missing cliffhanger or scenes"


class TestPublicCreationAPI:
    """Test public creation endpoint returns cliffhanger and characters"""
    
    def test_public_creation_endpoint_structure(self):
        """Public creation endpoint should return creation with cliffhanger"""
        # This endpoint requires a valid slug - we'll test the structure
        # Using a known slug pattern
        response = requests.get(f"{BASE_URL}/api/public/creation/trust-engine-5")
        # May return 404 if slug doesn't exist
        if response.status_code == 200:
            data = response.json()
            if data.get("creation"):
                creation = data["creation"]
                # Verify fields needed for Continue flow
                assert "title" in creation, "Creation missing title"
                # cliffhanger or scenes should be present
                assert "cliffhanger" in creation or "scenes" in creation or "story_text" in creation, \
                    "Creation missing cliffhanger/scenes/story_text"


class TestBackendCliffhangerEnforcement:
    """Test that planning_llm.py has cliffhanger enforcement logic"""
    
    def test_planning_llm_file_exists(self):
        """planning_llm.py should exist with cliffhanger enforcement"""
        planning_file = "/app/backend/services/story_engine/adapters/planning_llm.py"
        assert os.path.exists(planning_file), f"planning_llm.py not found at {planning_file}"
        
    def test_cliffhanger_enforcement_code_present(self):
        """planning_llm.py should have cliffhanger enforcement logic"""
        planning_file = "/app/backend/services/story_engine/adapters/planning_llm.py"
        with open(planning_file, 'r') as f:
            content = f.read()
        
        # Check for cliffhanger enforcement logic
        assert 'cliffhanger' in content, "Missing 'cliffhanger' in planning_llm.py"
        assert 'len(plan.get("cliffhanger"' in content or 'len(plan.get(\'cliffhanger\'' in content, \
            "Missing cliffhanger length check"
        assert 'Weak/missing cliffhanger' in content or 'cliffhanger_fix' in content, \
            "Missing cliffhanger rewrite logic"
        
    def test_cliffhanger_minimum_length_check(self):
        """Cliffhanger enforcement should check for minimum length (15 chars)"""
        planning_file = "/app/backend/services/story_engine/adapters/planning_llm.py"
        with open(planning_file, 'r') as f:
            content = f.read()
        
        # Check for the specific length check
        assert '< 15' in content or '<15' in content, "Missing cliffhanger minimum length check (15 chars)"
        
    def test_cliffhanger_rewrite_llm_call(self):
        """Cliffhanger enforcement should have LLM rewrite call"""
        planning_file = "/app/backend/services/story_engine/adapters/planning_llm.py"
        with open(planning_file, 'r') as f:
            content = f.read()
        
        # Check for rewrite LLM call
        assert 'cliffhanger specialist' in content or 'cliffhanger_fix' in content, \
            "Missing cliffhanger rewrite LLM call"
        assert 'rewrite_llm' in content or 'cliff_text' in content, \
            "Missing cliffhanger rewrite implementation"


class TestFrontendContinueElements:
    """Test that frontend files have required Continue Story elements"""
    
    def test_story_preview_has_continue_overlay(self):
        """StoryPreview.js should have Continue overlay with data-testid"""
        preview_file = "/app/frontend/src/pages/StoryPreview.js"
        with open(preview_file, 'r') as f:
            content = f.read()
        
        # Check for Continue overlay
        assert 'showContinueOverlay' in content, "Missing showContinueOverlay state"
        assert 'scene-continue-overlay' in content, "Missing scene-continue-overlay data-testid"
        assert 'overlay-continue-story-btn' in content, "Missing overlay-continue-story-btn data-testid"
        
    def test_story_preview_has_header_continue_btn(self):
        """StoryPreview.js should have 'What Happens Next?' as PRIMARY header action"""
        preview_file = "/app/frontend/src/pages/StoryPreview.js"
        with open(preview_file, 'r') as f:
            content = f.read()
        
        assert 'header-continue-btn' in content, "Missing header-continue-btn data-testid"
        assert 'What Happens Next?' in content, "Missing 'What Happens Next?' text"
        
    def test_story_preview_has_banner_continue(self):
        """StoryPreview.js should have banner with cliffhanger text and Continue CTA"""
        preview_file = "/app/frontend/src/pages/StoryPreview.js"
        with open(preview_file, 'r') as f:
            content = f.read()
        
        assert 'banner-continue-btn' in content, "Missing banner-continue-btn data-testid"
        assert 'ready-banner' in content, "Missing ready-banner data-testid"
        assert 'preview.cliffhanger' in content, "Missing cliffhanger display in banner"
        
    def test_story_preview_has_sidebar_continue(self):
        """StoryPreview.js should have Continue Story section in sidebar"""
        preview_file = "/app/frontend/src/pages/StoryPreview.js"
        with open(preview_file, 'r') as f:
            content = f.read()
        
        assert 'sidebar-continue-btn' in content, "Missing sidebar-continue-btn data-testid"
        
    def test_story_preview_has_last_scene_arrow(self):
        """StoryPreview.js should have purple arrow button on last scene"""
        preview_file = "/app/frontend/src/pages/StoryPreview.js"
        with open(preview_file, 'r') as f:
            content = f.read()
        
        assert 'last-scene-continue-btn' in content, "Missing last-scene-continue-btn data-testid"
        assert 'ArrowRight' in content, "Missing ArrowRight icon for last scene"
        
    def test_story_preview_passes_hook_text_and_characters(self):
        """StoryPreview.js handleContinueStory should pass hook_text and characters"""
        preview_file = "/app/frontend/src/pages/StoryPreview.js"
        with open(preview_file, 'r') as f:
            content = f.read()
        
        assert 'hook_text: cliffhanger' in content or 'hook_text:' in content, \
            "Missing hook_text in remix_data"
        assert 'characters: preview.characters' in content or 'characters:' in content, \
            "Missing characters in remix_data"


class TestPublicCreationContinueElements:
    """Test PublicCreation.js has Continue Story elements"""
    
    def test_public_creation_has_post_video_overlay(self):
        """PublicCreation.js should have post-video overlay with cliffhanger"""
        public_file = "/app/frontend/src/pages/PublicCreation.js"
        with open(public_file, 'r') as f:
            content = f.read()
        
        assert 'post-video-overlay' in content, "Missing post-video-overlay data-testid"
        assert 'videoEnded' in content, "Missing videoEnded state"
        assert 'showOverlay' in content, "Missing showOverlay state"
        
    def test_public_creation_overlay_shows_cliffhanger(self):
        """PublicCreation.js overlay should show actual cliffhanger text"""
        public_file = "/app/frontend/src/pages/PublicCreation.js"
        with open(public_file, 'r') as f:
            content = f.read()
        
        assert 'cliffhangerText' in content, "Missing cliffhangerText variable"
        # Check that cliffhangerText is displayed in overlay
        assert 'cliffhangerText.length' in content or 'cliffhangerText &&' in content, \
            "Cliffhanger text not displayed in overlay"
        
    def test_public_creation_handle_continue_passes_hook_text(self):
        """PublicCreation.js handleContinue should pass hook_text and characters"""
        public_file = "/app/frontend/src/pages/PublicCreation.js"
        with open(public_file, 'r') as f:
            content = f.read()
        
        assert 'hook_text:' in content, "Missing hook_text in handleContinue"
        assert 'characters:' in content, "Missing characters in handleContinue"
        
    def test_public_creation_has_continue_ctas(self):
        """PublicCreation.js should have Continue Story CTAs"""
        public_file = "/app/frontend/src/pages/PublicCreation.js"
        with open(public_file, 'r') as f:
            content = f.read()
        
        assert 'overlay-continue-btn' in content, "Missing overlay-continue-btn data-testid"
        assert 'continue-story-btn' in content, "Missing continue-story-btn data-testid"
        assert 'header-continue-btn' in content, "Missing header-continue-btn data-testid"


class TestStoryVideoPipelineRemixData:
    """Test StoryVideoPipeline.js handles remix_data with hook_text and characters"""
    
    def test_pipeline_reads_hook_text_from_remix_data(self):
        """StoryVideoPipeline.js should read hook_text from remix_data"""
        pipeline_file = "/app/frontend/src/pages/StoryVideoPipeline.js"
        with open(pipeline_file, 'r') as f:
            content = f.read()
        
        assert 'hook_text' in content, "Missing hook_text handling"
        assert 'rd.remixFrom.hook_text' in content or 'remixFrom.hook_text' in content, \
            "Missing hook_text extraction from remixFrom"
        
    def test_pipeline_reads_characters_from_remix_data(self):
        """StoryVideoPipeline.js should read characters from remix_data"""
        pipeline_file = "/app/frontend/src/pages/StoryVideoPipeline.js"
        with open(pipeline_file, 'r') as f:
            content = f.read()
        
        assert 'characters' in content, "Missing characters handling"
        assert 'rd.remixFrom.characters' in content or 'remixFrom.characters' in content, \
            "Missing characters extraction from remixFrom"
        
    def test_pipeline_sets_remix_data_with_hook_and_characters(self):
        """StoryVideoPipeline.js should set remixData with hook_text and characters"""
        pipeline_file = "/app/frontend/src/pages/StoryVideoPipeline.js"
        with open(pipeline_file, 'r') as f:
            content = f.read()
        
        # Check for setRemixData call that includes hook_text and characters
        assert 'setRemixData' in content, "Missing setRemixData call"
        # Check the specific pattern where hook_text and characters are captured
        assert 'hook_text: rd.remixFrom.hook_text' in content or \
               'hook_text: pf.hook_text' in content, \
            "Missing hook_text capture in setRemixData"


class TestDataTestIdAttributes:
    """Test that all Continue-related elements have data-testid attributes"""
    
    def test_story_preview_data_testids(self):
        """StoryPreview.js should have all required data-testid attributes"""
        preview_file = "/app/frontend/src/pages/StoryPreview.js"
        with open(preview_file, 'r') as f:
            content = f.read()
        
        required_testids = [
            'header-continue-btn',
            'banner-continue-btn',
            'sidebar-continue-btn',
            'last-scene-continue-btn',
            'scene-continue-overlay',
            'overlay-continue-story-btn',
            'overlay-dismiss-btn',
            'ready-banner',
        ]
        
        for testid in required_testids:
            assert testid in content, f"Missing data-testid='{testid}' in StoryPreview.js"
            
    def test_public_creation_data_testids(self):
        """PublicCreation.js should have all required data-testid attributes"""
        public_file = "/app/frontend/src/pages/PublicCreation.js"
        with open(public_file, 'r') as f:
            content = f.read()
        
        required_testids = [
            'post-video-overlay',
            'overlay-continue-btn',
            'continue-story-btn',
            'header-continue-btn',
            'video-player',
            'story-hook',
        ]
        
        for testid in required_testids:
            assert testid in content, f"Missing data-testid='{testid}' in PublicCreation.js"


class TestHomepageStoryCards:
    """Test homepage story cards have Continue Story CTAs"""
    
    def test_dashboard_has_story_cards(self):
        """Dashboard should have story cards with Continue functionality"""
        dashboard_file = "/app/frontend/src/pages/Dashboard.js"
        if os.path.exists(dashboard_file):
            with open(dashboard_file, 'r') as f:
                content = f.read()
            
            # Check for story card click handler that prefills studio
            assert 'handleClick' in content or 'onClick' in content, \
                "Missing click handler for story cards"
            assert 'prefill' in content or 'remix_data' in content, \
                "Missing prefill/remix_data in story card click"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
