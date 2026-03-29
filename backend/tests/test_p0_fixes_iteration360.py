"""
P0 Fixes Test Suite - Iteration 360
Tests for:
1. Story card click prefill (title, prompt, animation_style, parent_video_id)
2. SafeImage IntersectionObserver lazy loading
3. FFmpeg transition sanitization (cut/crossfade → fade)
"""
import pytest
import requests
import os
import sys

# Add backend to path for direct imports
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestStoryFeedAPI:
    """Test /api/engagement/story-feed returns correct data for prefill"""
    
    def test_story_feed_returns_required_fields(self):
        """Verify story feed returns all fields needed for prefill"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed?limit=5")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "trending" in data, "Response should have 'trending' key"
        
        if len(data["trending"]) > 0:
            story = data["trending"][0]
            # Check required fields for prefill
            assert "job_id" in story, "Story should have job_id for parent_video_id"
            assert "title" in story, "Story should have title for prefill"
            assert "hook_text" in story, "Story should have hook_text for prompt prefill"
            assert "animation_style" in story, "Story should have animation_style for prefill"
            print(f"✓ Story feed returns all prefill fields: title='{story.get('title', '')[:30]}...', animation_style='{story.get('animation_style')}'")
    
    def test_story_feed_hero_has_prefill_fields(self):
        """Verify hero story has all fields needed for Watch & Continue prefill"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed?limit=1")
        assert response.status_code == 200
        
        data = response.json()
        if "hero" in data and data["hero"]:
            hero = data["hero"]
            assert "job_id" in hero, "Hero should have job_id"
            assert "title" in hero, "Hero should have title"
            assert "hook_text" in hero, "Hero should have hook_text"
            assert "animation_style" in hero, "Hero should have animation_style"
            print(f"✓ Hero story has all prefill fields: job_id={hero.get('job_id')[:8]}...")
        else:
            pytest.skip("No hero story available")


class TestFFmpegTransitionSanitization:
    """Test FFmpeg transition name sanitization"""
    
    def test_sanitize_transition_function(self):
        """Test _sanitize_transition maps LLM names to valid FFmpeg xfade values"""
        from services.story_engine.adapters.ffmpeg_assembly import _sanitize_transition
        
        # Test cut → fade
        assert _sanitize_transition("cut") == "fade", "cut should map to fade"
        
        # Test crossfade → fade
        assert _sanitize_transition("crossfade") == "fade", "crossfade should map to fade"
        assert _sanitize_transition("cross_fade") == "fade", "cross_fade should map to fade"
        assert _sanitize_transition("cross-fade") == "fade", "cross-fade should map to fade"
        
        # Test valid transitions pass through
        assert _sanitize_transition("dissolve") == "dissolve", "dissolve should pass through"
        assert _sanitize_transition("wipeleft") == "wipeleft", "wipeleft should pass through"
        assert _sanitize_transition("zoomin") == "zoomin", "zoomin should pass through"
        
        # Test edge cases
        assert _sanitize_transition("") == "fade", "empty string should default to fade"
        assert _sanitize_transition(None) == "fade", "None should default to fade"
        assert _sanitize_transition("CROSSFADE") == "fade", "uppercase should be handled"
        assert _sanitize_transition("  cut  ") == "fade", "whitespace should be trimmed"
        
        # Test unknown transitions default to fade
        assert _sanitize_transition("unknown_transition") == "fade", "unknown should default to fade"
        assert _sanitize_transition("magic_wipe") == "fade", "invalid should default to fade"
        
        print("✓ All transition sanitization tests passed")
    
    def test_valid_xfade_transitions(self):
        """Verify all valid FFmpeg xfade transitions are recognized"""
        from services.story_engine.adapters.ffmpeg_assembly import _sanitize_transition
        
        valid_transitions = [
            "fade", "fadeblack", "fadewhite", "dissolve",
            "wipeleft", "wiperight", "wipeup", "wipedown",
            "slideleft", "slideright", "slideup", "slidedown",
            "circlecrop", "circleopen", "circleclose",
            "radial", "zoomin"
        ]
        
        for trans in valid_transitions:
            result = _sanitize_transition(trans)
            assert result == trans, f"{trans} should pass through unchanged, got {result}"
        
        print(f"✓ All {len(valid_transitions)} valid xfade transitions pass through correctly")


class TestStoryEngineCreateEndpoint:
    """Test /api/story-engine/create endpoint accepts valid parameters"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_create_endpoint_exists(self, auth_token):
        """Verify /api/story-engine/create endpoint exists"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Just check the endpoint responds (even with validation error is fine)
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers=headers,
            json={}
        )
        # Should not be 404
        assert response.status_code != 404, "Endpoint should exist"
        print(f"✓ /api/story-engine/create endpoint exists (status: {response.status_code})")
    
    def test_create_accepts_prefill_parameters(self, auth_token):
        """Verify create endpoint accepts title, prompt, animation_style, parent_video_id"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test with all prefill parameters
        payload = {
            "title": "Test Prefill Story",
            "story_text": "A test story for prefill validation",
            "animation_style": "watercolor",
            "parent_video_id": "test-parent-id-123"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/story-engine/create",
            headers=headers,
            json=payload
        )
        
        # Should accept the parameters (may fail for other reasons like credits)
        # But should not fail due to unknown parameters
        if response.status_code == 422:
            error = response.json()
            # Check if error is about unknown fields
            error_str = str(error).lower()
            assert "parent_video_id" not in error_str or "unknown" not in error_str, \
                "parent_video_id should be accepted"
            assert "animation_style" not in error_str or "unknown" not in error_str, \
                "animation_style should be accepted"
        
        print(f"✓ Create endpoint accepts prefill parameters (status: {response.status_code})")


class TestDashboardPrefillNavigation:
    """Test Dashboard navigation passes correct prefill data"""
    
    def test_story_card_prefill_structure(self):
        """Verify story card click should pass full prefill object"""
        # This is a code review test - verify the Dashboard.js code structure
        with open('/app/frontend/src/pages/Dashboard.js', 'r') as f:
            content = f.read()
        
        # Check StoryCard handleClick passes full prefill object
        assert "prefill: {" in content or "prefill:{" in content, \
            "StoryCard should pass prefill as object"
        assert "title: story.title" in content or "title:story.title" in content, \
            "Prefill should include title"
        assert "prompt: story.hook_text" in content or "prompt:story.hook_text" in content, \
            "Prefill should include prompt from hook_text"
        assert "animation_style: story.animation_style" in content or "animation_style:story.animation_style" in content, \
            "Prefill should include animation_style"
        assert "parent_video_id:" in content, \
            "Prefill should include parent_video_id"
        
        print("✓ Dashboard StoryCard passes full prefill object with all required fields")
    
    def test_hero_watch_continue_prefill(self):
        """Verify hero Watch & Continue button passes full prefill"""
        with open('/app/frontend/src/pages/Dashboard.js', 'r') as f:
            content = f.read()
        
        # Check hero button passes prefill with all fields
        # Look for the hero-play-btn onClick
        assert "hero-play-btn" in content, "Hero play button should exist"
        
        # The prefill should include current.title, current.hook_text, etc.
        assert "current.title" in content, "Hero prefill should use current.title"
        assert "current.hook_text" in content, "Hero prefill should use current.hook_text"
        assert "current.animation_style" in content, "Hero prefill should use current.animation_style"
        assert "current.job_id" in content, "Hero prefill should use current.job_id for parent_video_id"
        
        print("✓ Hero Watch & Continue button passes full prefill context")
    
    def test_create_bar_prefill(self):
        """Verify create bar passes prompt in prefill object"""
        with open('/app/frontend/src/pages/Dashboard.js', 'r') as f:
            content = f.read()
        
        # Check CreateBar passes prompt in prefill object
        assert "create-bar" in content, "Create bar should exist"
        assert "prefill: prompt" in content or "prefill:prompt" in content or \
               "prefill: { prompt }" in content or "prefill:{prompt}" in content, \
            "Create bar should pass prompt in prefill"
        
        print("✓ Create bar passes prompt in prefill object")


class TestSafeImageLazyLoading:
    """Test SafeImage uses IntersectionObserver for lazy loading"""
    
    def test_intersection_observer_implementation(self):
        """Verify SafeImage uses IntersectionObserver"""
        with open('/app/frontend/src/components/SafeImage.jsx', 'r') as f:
            content = f.read()
        
        # Check IntersectionObserver is used
        assert "IntersectionObserver" in content, \
            "SafeImage should use IntersectionObserver"
        
        # Check rootMargin for preloading
        assert "rootMargin" in content, \
            "IntersectionObserver should have rootMargin for preloading"
        assert "200px" in content, \
            "rootMargin should be 200px for preloading"
        
        # Check priority prop for eager loading
        assert "priority" in content, \
            "SafeImage should support priority prop"
        
        # Check inView state controls rendering
        assert "inView" in content, \
            "SafeImage should track inView state"
        
        print("✓ SafeImage implements IntersectionObserver with 200px rootMargin")
    
    def test_priority_images_load_eagerly(self):
        """Verify priority images bypass lazy loading"""
        with open('/app/frontend/src/components/SafeImage.jsx', 'r') as f:
            content = f.read()
        
        # Check priority images set inView immediately
        assert "priority" in content and "setInView" in content, \
            "Priority images should set inView immediately"
        
        # Check fetchPriority for priority images
        assert "fetchPriority" in content, \
            "Priority images should use fetchPriority='high'"
        
        print("✓ Priority images load eagerly with fetchPriority='high'")
    
    def test_dashboard_no_eager_preload(self):
        """Verify Dashboard doesn't eagerly preload all images"""
        with open('/app/frontend/src/pages/Dashboard.js', 'r') as f:
            content = f.read()
        
        # Check preloadImages is NOT used (was replaced with preloadHeroImage)
        assert "preloadImages" not in content or "preloadHeroImage" in content, \
            "Dashboard should use preloadHeroImage, not preloadImages"
        
        # Check only hero image is preloaded
        assert "preloadHeroImage" in content, \
            "Dashboard should preload only hero image"
        
        print("✓ Dashboard preloads only hero image, not all 16 images")


class TestStudioPrefillHandling:
    """Test StoryVideoPipeline handles prefill correctly"""
    
    def test_studio_reads_prefill_object(self):
        """Verify Studio reads prefill as object with all fields"""
        with open('/app/frontend/src/pages/StoryVideoPipeline.js', 'r') as f:
            content = f.read()
        
        # Check prefill handling
        assert "prefill" in content, "Studio should handle prefill"
        
        # Check it handles both string and object prefill
        assert "typeof pf === 'string'" in content or "typeof pf==='string'" in content, \
            "Studio should handle legacy string prefill"
        assert "typeof pf === 'object'" in content or "typeof pf==='object'" in content, \
            "Studio should handle object prefill"
        
        # Check all fields are extracted
        assert "pf.title" in content, "Studio should extract title from prefill"
        assert "pf.prompt" in content, "Studio should extract prompt from prefill"
        assert "pf.animation_style" in content, "Studio should extract animation_style from prefill"
        assert "pf.parent_video_id" in content, "Studio should extract parent_video_id from prefill"
        
        print("✓ Studio reads prefill object with title, prompt, animation_style, parent_video_id")
    
    def test_studio_stays_in_input_phase(self):
        """Verify Studio doesn't auto-generate when freshSession is true"""
        with open('/app/frontend/src/pages/StoryVideoPipeline.js', 'r') as f:
            content = f.read()
        
        # Check freshSession flag is respected
        assert "freshSession" in content, "Studio should check freshSession flag"
        
        # Check auto-reconnect is blocked for fresh sessions
        assert "!locState?.freshSession" in content or "locState?.freshSession" in content, \
            "Studio should block auto-reconnect for fresh sessions"
        
        print("✓ Studio respects freshSession flag - stays in input phase")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
