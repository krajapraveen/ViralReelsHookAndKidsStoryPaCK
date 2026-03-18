"""
Iteration 309 - P0 Bug Fixes Test Suite
Tests for 4 reported P0 bugs:
1. Story Video output is static slideshow (no motion) - Ken Burns motion system
2. Story Video form controls look disabled (dim text) - UI styling
3. Resume Your Story shows empty panels - Truthful fallback states
4. More Tools label has low visibility - Brighter label styling
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://growth-funnel-stable.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and return token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestPipelineOptionsAPI:
    """Test /api/pipeline/options endpoint returns correct structure"""
    
    def test_options_returns_success(self):
        """Options endpoint returns success"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
    
    def test_options_has_animation_styles(self):
        """Options endpoint returns animation_styles array"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        data = response.json()
        
        assert "animation_styles" in data
        assert isinstance(data["animation_styles"], list)
        assert len(data["animation_styles"]) >= 6, "Should have at least 6 animation styles"
        
        # Check structure of animation style
        style = data["animation_styles"][0]
        assert "id" in style
        assert "name" in style
        assert "style_prompt" in style
    
    def test_options_has_age_groups(self):
        """Options endpoint returns age_groups array"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        data = response.json()
        
        assert "age_groups" in data
        assert isinstance(data["age_groups"], list)
        assert len(data["age_groups"]) >= 5, "Should have at least 5 age groups"
        
        # Check structure of age group
        age = data["age_groups"][0]
        assert "id" in age
        assert "name" in age
        assert "max_scenes" in age
    
    def test_options_has_voice_presets(self):
        """Options endpoint returns voice_presets array"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        data = response.json()
        
        assert "voice_presets" in data
        assert isinstance(data["voice_presets"], list)
        assert len(data["voice_presets"]) >= 5, "Should have at least 5 voice presets"
        
        # Check structure of voice preset
        voice = data["voice_presets"][0]
        assert "id" in voice
        assert "name" in voice
        assert "voice" in voice
    
    def test_options_has_credit_costs(self):
        """Options endpoint returns credit_costs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        data = response.json()
        
        assert "credit_costs" in data
        costs = data["credit_costs"]
        assert "small" in costs
        assert "medium" in costs
        assert "large" in costs


class TestPipelineCreateAPI:
    """Test /api/pipeline/create endpoint accepts new fields"""
    
    def test_create_requires_auth(self):
        """Create endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Test Video",
            "story_text": "A" * 100
        })
        assert response.status_code in [401, 403, 422]
    
    def test_create_accepts_animation_style(self, auth_headers):
        """Create endpoint accepts animation_style field"""
        # This tests that the endpoint accepts the field, not full creation
        response = requests.post(f"{BASE_URL}/api/pipeline/create", 
            headers=auth_headers,
            json={
                "title": "Animation Test",
                "story_text": "A" * 100,
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            }
        )
        # Should not fail on field validation (400) - may get 402 for credits or succeed
        # We just want to verify the fields are accepted
        assert response.status_code != 422, f"Field validation failed: {response.text}"
    
    def test_create_requires_story_text_min_length(self, auth_headers):
        """Create endpoint validates story_text minimum length"""
        response = requests.post(f"{BASE_URL}/api/pipeline/create",
            headers=auth_headers,
            json={
                "title": "Test Video",
                "story_text": "Too short",  # Less than 50 chars
                "animation_style": "cartoon_2d"
            }
        )
        # Should fail validation for min length
        assert response.status_code == 422
    
    def test_create_requires_title_min_length(self, auth_headers):
        """Create endpoint validates title minimum length"""
        response = requests.post(f"{BASE_URL}/api/pipeline/create",
            headers=auth_headers,
            json={
                "title": "AB",  # Less than 3 chars
                "story_text": "A" * 100,
                "animation_style": "cartoon_2d"
            }
        )
        # Should fail validation for min length
        assert response.status_code == 422


class TestActiveChainsAPI:
    """Test Resume Your Story API - /api/photo-to-comic/active-chains"""
    
    def test_active_chains_requires_auth(self):
        """Active chains endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains")
        assert response.status_code in [401, 403]
    
    def test_active_chains_returns_array(self, auth_headers):
        """Active chains endpoint returns chains array"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "chains" in data
        assert isinstance(data["chains"], list)
    
    def test_active_chains_structure(self, auth_headers):
        """Active chains have proper structure (if any exist)"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=auth_headers)
        data = response.json()
        chains = data.get("chains", [])
        
        # If chains exist, verify structure
        if chains:
            chain = chains[0]
            assert "chain_id" in chain
            # preview_url may or may not exist - that's the point of truthful fallback


class TestRateLimitStatus:
    """Test rate limit status endpoint"""
    
    def test_rate_limit_status_requires_auth(self):
        """Rate limit status requires auth"""
        response = requests.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        assert response.status_code in [401, 403]
    
    def test_rate_limit_status_returns_fields(self, auth_headers):
        """Rate limit status returns expected fields"""
        response = requests.get(f"{BASE_URL}/api/pipeline/rate-limit-status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "can_create" in data
        assert isinstance(data["can_create"], bool)


class TestKenBurnsMotionSystem:
    """Test Ken Burns motion system implementation in pipeline_engine.py"""
    
    def test_ken_burns_function_exists(self):
        """Ken Burns filter function is importable"""
        from services.pipeline_engine import _build_ken_burns_filter
        assert callable(_build_ken_burns_filter)
    
    def test_ken_burns_returns_tuple(self):
        """Ken Burns function returns (src_w, src_h, filter_string) tuple"""
        from services.pipeline_engine import _build_ken_burns_filter
        result = _build_ken_burns_filter(0, 5.0, 960, 540, 24)
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        src_w, src_h, filter_str = result
        assert isinstance(src_w, int)
        assert isinstance(src_h, int)
        assert isinstance(filter_str, str)
    
    def test_ken_burns_scales_source_larger(self):
        """Ken Burns scales source 1.5x for zoompan headroom"""
        from services.pipeline_engine import _build_ken_burns_filter
        
        target_w, target_h = 960, 540
        src_w, src_h, _ = _build_ken_burns_filter(0, 5.0, target_w, target_h, 24)
        
        # Source should be 1.5x the target
        assert src_w == int(target_w * 1.5), f"Expected {int(target_w * 1.5)}, got {src_w}"
        assert src_h == int(target_h * 1.5), f"Expected {int(target_h * 1.5)}, got {src_h}"
    
    def test_ken_burns_contains_zoompan(self):
        """Ken Burns filter contains zoompan command"""
        from services.pipeline_engine import _build_ken_burns_filter
        _, _, filter_str = _build_ken_burns_filter(0, 5.0, 960, 540, 24)
        
        assert "zoompan=" in filter_str
    
    def test_ken_burns_has_motion_patterns(self):
        """Different scene indices produce different motion patterns"""
        from services.pipeline_engine import _build_ken_burns_filter, MOTION_PATTERNS
        
        assert len(MOTION_PATTERNS) >= 6, "Should have at least 6 motion patterns"
        
        # Test that different indices produce different filters
        filters = []
        for i in range(6):
            _, _, filter_str = _build_ken_burns_filter(i, 5.0, 960, 540, 24)
            filters.append(filter_str)
        
        # At least some should be different
        unique_filters = set(filters)
        assert len(unique_filters) >= 4, "Should have variety in motion patterns"
    
    def test_ken_burns_includes_output_size(self):
        """Ken Burns filter includes output dimensions"""
        from services.pipeline_engine import _build_ken_burns_filter
        
        target_w, target_h = 960, 540
        _, _, filter_str = _build_ken_burns_filter(0, 5.0, target_w, target_h, 24)
        
        assert f"s={target_w}x{target_h}" in filter_str


class TestMotionPatternsVariety:
    """Test that motion patterns provide visual variety"""
    
    def test_zoom_in_pattern(self):
        """zoom_in pattern starts zoomed out, zooms in"""
        from services.pipeline_engine import _build_ken_burns_filter
        _, _, filter_str = _build_ken_burns_filter(0, 5.0, 960, 540, 24)
        # Scene 0 should use zoom_in (first pattern)
        assert "min(1+0.25" in filter_str
    
    def test_pan_right_pattern(self):
        """pan_right pattern pans horizontally"""
        from services.pipeline_engine import _build_ken_burns_filter
        _, _, filter_str = _build_ken_burns_filter(1, 5.0, 960, 540, 24)
        # Scene 1 should use pan_right (second pattern)
        assert "z='1.15'" in filter_str
    
    def test_zoom_out_pattern(self):
        """zoom_out pattern starts zoomed in, zooms out"""
        from services.pipeline_engine import _build_ken_burns_filter
        _, _, filter_str = _build_ken_burns_filter(2, 5.0, 960, 540, 24)
        # Scene 2 should use zoom_out (third pattern)
        assert "eq(on,1),1.25" in filter_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
