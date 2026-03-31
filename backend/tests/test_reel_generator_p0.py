"""
Test Suite for Reel Generator P0 Upgrade
Tests the new input controls, enriched API response, and all new fields
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

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
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestReelGeneratorNewFields:
    """Test that the API accepts all new P0 fields"""
    
    def test_api_accepts_platform_field(self, auth_headers):
        """Test that platform field is accepted"""
        payload = {
            "topic": "TEST_platform_field_test",
            "platform": "TikTok",
            "hookStyle": "Curiosity",
            "reelFormat": "Talking Head",
            "ctaType": "Follow",
            "goal": "Followers",
            "outputType": "script_only"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        # Should not fail with 422 validation error
        assert response.status_code != 422, f"Platform field rejected: {response.text}"
        print(f"Platform field test: status={response.status_code}")
    
    def test_api_accepts_hook_style_field(self, auth_headers):
        """Test that hookStyle field is accepted"""
        payload = {
            "topic": "TEST_hook_style_test",
            "hookStyle": "Shock",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        assert response.status_code != 422, f"hookStyle field rejected: {response.text}"
        print(f"hookStyle field test: status={response.status_code}")
    
    def test_api_accepts_reel_format_field(self, auth_headers):
        """Test that reelFormat field is accepted"""
        payload = {
            "topic": "TEST_reel_format_test",
            "reelFormat": "Faceless",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        assert response.status_code != 422, f"reelFormat field rejected: {response.text}"
        print(f"reelFormat field test: status={response.status_code}")
    
    def test_api_accepts_cta_type_field(self, auth_headers):
        """Test that ctaType field is accepted"""
        payload = {
            "topic": "TEST_cta_type_test",
            "ctaType": "Buy",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        assert response.status_code != 422, f"ctaType field rejected: {response.text}"
        print(f"ctaType field test: status={response.status_code}")
    
    def test_api_accepts_output_type_field(self, auth_headers):
        """Test that outputType field is accepted"""
        payload = {
            "topic": "TEST_output_type_test",
            "outputType": "full_plan",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        assert response.status_code != 422, f"outputType field rejected: {response.text}"
        print(f"outputType field test: status={response.status_code}")
    
    def test_api_accepts_audience_field(self, auth_headers):
        """Test that audience field is accepted"""
        payload = {
            "topic": "TEST_audience_field_test",
            "audience": "Gen Z (13-24)",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        assert response.status_code != 422, f"audience field rejected: {response.text}"
        print(f"audience field test: status={response.status_code}")


class TestReelGeneratorFullGeneration:
    """Test full reel generation with all new fields and verify enriched response"""
    
    def test_full_generation_with_all_fields(self, auth_headers):
        """Test complete generation with all P0 fields and verify enriched JSON response"""
        payload = {
            "topic": "5 morning habits of successful entrepreneurs",
            "platform": "Instagram",
            "hookStyle": "Curiosity",
            "reelFormat": "Talking Head",
            "ctaType": "Follow",
            "goal": "Followers",
            "outputType": "full_plan",
            "niche": "Luxury",
            "tone": "Bold",
            "duration": "30s",
            "language": "English",
            "audience": "Young Professionals"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        
        assert response.status_code == 200, f"Generation failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should indicate success"
        assert "generationId" in data, "Response should contain generationId"
        assert "result" in data, "Response should contain result"
        assert "remainingCredits" in data, "Response should contain remainingCredits"
        
        result = data["result"]
        
        # Verify hooks array
        assert "hooks" in result, "Result should contain hooks array"
        assert isinstance(result["hooks"], list), "hooks should be a list"
        assert len(result["hooks"]) >= 1, "Should have at least 1 hook"
        print(f"✓ hooks: {len(result['hooks'])} variants")
        
        # Verify best_hook
        assert "best_hook" in result, "Result should contain best_hook"
        assert isinstance(result["best_hook"], str), "best_hook should be a string"
        print(f"✓ best_hook: {result['best_hook'][:50]}...")
        
        # Verify script with scenes
        assert "script" in result, "Result should contain script"
        assert "scenes" in result["script"], "Script should contain scenes"
        assert isinstance(result["script"]["scenes"], list), "scenes should be a list"
        assert len(result["script"]["scenes"]) >= 1, "Should have at least 1 scene"
        
        # Verify scene structure
        first_scene = result["script"]["scenes"][0]
        scene_fields = ["time", "on_screen_text", "voiceover", "visual_direction"]
        for field in scene_fields:
            if field in first_scene:
                print(f"✓ scene.{field} present")
        
        # Verify CTA in script
        if "cta" in result["script"]:
            print(f"✓ script.cta: {result['script']['cta'][:50]}...")
        
        # Verify voiceover_full (new P0 field)
        if "voiceover_full" in result:
            assert isinstance(result["voiceover_full"], str), "voiceover_full should be a string"
            print(f"✓ voiceover_full: {len(result['voiceover_full'])} chars")
        
        # Verify captions
        if "caption_short" in result:
            print(f"✓ caption_short present")
        if "caption_long" in result:
            print(f"✓ caption_long present")
        
        # Verify hashtags
        assert "hashtags" in result, "Result should contain hashtags"
        assert isinstance(result["hashtags"], list), "hashtags should be a list"
        print(f"✓ hashtags: {len(result['hashtags'])} tags")
        
        # Verify shot_list (new P0 field)
        if "shot_list" in result:
            assert isinstance(result["shot_list"], list), "shot_list should be a list"
            if len(result["shot_list"]) > 0:
                shot = result["shot_list"][0]
                print(f"✓ shot_list: {len(result['shot_list'])} shots")
                # Verify shot structure
                shot_fields = ["shot_number", "description", "type", "duration"]
                for field in shot_fields:
                    if field in shot:
                        print(f"  ✓ shot.{field} present")
        
        # Verify visual_prompts (new P0 field)
        if "visual_prompts" in result:
            assert isinstance(result["visual_prompts"], list), "visual_prompts should be a list"
            print(f"✓ visual_prompts: {len(result['visual_prompts'])} prompts")
        
        # Verify ai_recommendations (new P0 field)
        if "ai_recommendations" in result:
            rec = result["ai_recommendations"]
            assert isinstance(rec, dict), "ai_recommendations should be a dict"
            rec_fields = ["best_hook_type", "recommended_duration", "suggested_posting_time", 
                         "emotional_trigger", "retention_strategy"]
            for field in rec_fields:
                if field in rec:
                    print(f"✓ ai_recommendations.{field}: {rec[field][:30] if rec[field] else 'N/A'}...")
        
        # Verify posting_tips
        if "posting_tips" in result:
            assert isinstance(result["posting_tips"], list), "posting_tips should be a list"
            print(f"✓ posting_tips: {len(result['posting_tips'])} tips")
        
        print(f"\n✓ Full generation test PASSED - generationId: {data['generationId']}")
        return data


class TestReelGeneratorContentFiltering:
    """Test content filtering for inappropriate topics"""
    
    def test_inappropriate_content_blocked(self, auth_headers):
        """Test that inappropriate content is blocked"""
        payload = {
            "topic": "explicit adult content test",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=30
        )
        # Should be blocked with 400
        assert response.status_code == 400, f"Inappropriate content should be blocked: {response.status_code}"
        print("✓ Content filtering working - inappropriate content blocked")


class TestReelGeneratorValidation:
    """Test input validation"""
    
    def test_empty_topic_rejected(self, auth_headers):
        """Test that empty topic is rejected"""
        payload = {
            "topic": "",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 422, f"Empty topic should be rejected: {response.status_code}"
        print("✓ Empty topic validation working")
    
    def test_topic_too_short_rejected(self, auth_headers):
        """Test that topic < 3 chars is rejected"""
        payload = {
            "topic": "ab",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 422, f"Short topic should be rejected: {response.status_code}"
        print("✓ Short topic validation working")


class TestReelGeneratorDemoEndpoint:
    """Test demo endpoint (no auth required)"""
    
    def test_demo_reel_generation(self):
        """Test demo reel generation without authentication"""
        payload = {
            "topic": "productivity tips for remote workers",
            "niche": "Business",
            "platform": "Instagram"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/demo/reel",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200, f"Demo generation failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Demo should succeed"
        assert data.get("isDemo") == True, "Should be marked as demo"
        assert "result" in data, "Should contain result"
        
        result = data["result"]
        assert "hooks" in result, "Demo result should have hooks"
        assert "script" in result, "Demo result should have script"
        assert "hashtags" in result, "Demo result should have hashtags"
        
        print("✓ Demo endpoint working correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
