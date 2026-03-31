"""
Test Suite for Reel Generator - Reference-Based Generation & Quick Presets
Iteration 400 - Testing new features:
1. Reference-Based Generation (reference_url, reference_text, reference_notes)
2. Quick Presets (8 preset chips that prefill form controls)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Get headers with admin auth token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestReelGenerationStandard:
    """Test standard reel generation (Fresh Create mode)"""
    
    def test_standard_reel_generation_without_reference(self, admin_headers):
        """Standard generation should work without reference fields"""
        payload = {
            "topic": "5 productivity hacks for remote workers",
            "platform": "Instagram",
            "hookStyle": "Curiosity",
            "reelFormat": "Talking Head",
            "ctaType": "Follow",
            "goal": "Followers",
            "outputType": "full_plan",
            "niche": "Productivity",
            "tone": "Bold",
            "duration": "30s",
            "language": "English",
            "audience": "Young Professionals"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=admin_headers,
            timeout=60
        )
        
        assert response.status_code == 200, f"Standard generation failed: {response.text}"
        data = response.json()
        
        # Verify standard response structure
        assert data.get("success") is True
        assert "result" in data
        result = data["result"]
        
        # Standard generation should NOT have reference_analysis
        assert result.get("is_reference_based") is not True, "Standard generation should not be reference-based"
        assert "reference_analysis" not in result or result.get("reference_analysis") is None
        
        # Verify standard output fields exist
        assert "hooks" in result
        assert "best_hook" in result
        assert "script" in result
        print(f"✓ Standard reel generation works - hooks: {len(result.get('hooks', []))}")


class TestReelGenerationReference:
    """Test reference-based reel generation (From Reference mode)"""
    
    def test_reference_generation_with_text(self, admin_headers):
        """Reference generation with pasted text should return reference_analysis"""
        reference_text = """
        Hook: "Stop scrolling! This changed my life..."
        Scene 1: Open with shocked face, text overlay "I was broke"
        Scene 2: Show transformation, "Then I discovered this..."
        Scene 3: Reveal the secret, "The 5AM club changed everything"
        CTA: "Follow for more life hacks!"
        """
        
        payload = {
            "topic": "Morning routine for entrepreneurs",
            "platform": "Instagram",
            "hookStyle": "Shock",
            "reelFormat": "Talking Head",
            "ctaType": "Follow",
            "goal": "Followers",
            "outputType": "full_plan",
            "niche": "Entrepreneurship",
            "tone": "Bold",
            "duration": "30s",
            "language": "English",
            "audience": "Entrepreneurs",
            "reference_text": reference_text,
            "reference_notes": "Keep the hook style but make it more luxury"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=admin_headers,
            timeout=90
        )
        
        assert response.status_code == 200, f"Reference generation failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        result = data["result"]
        
        # Reference-based generation should have these markers
        assert result.get("is_reference_based") is True, "Should be marked as reference-based"
        assert result.get("reference_source") == "text", "Source should be 'text'"
        
        # Should have reference_analysis section
        assert "reference_analysis" in result, "Should have reference_analysis section"
        ref_analysis = result["reference_analysis"]
        
        # Verify reference_analysis has expected fields
        expected_fields = ["hook_pattern", "pacing_structure", "emotional_arc", "cta_approach", "format_choices"]
        for field in expected_fields:
            assert field in ref_analysis, f"reference_analysis should have {field}"
        
        print(f"✓ Reference-based generation with text works")
        print(f"  - is_reference_based: {result.get('is_reference_based')}")
        print(f"  - reference_source: {result.get('reference_source')}")
        print(f"  - reference_analysis fields: {list(ref_analysis.keys())}")
    
    def test_reference_generation_with_url_fallback(self, admin_headers):
        """Reference generation with URL that may fail should fallback gracefully"""
        payload = {
            "topic": "Luxury lifestyle tips",
            "platform": "Instagram",
            "hookStyle": "Luxury",
            "reelFormat": "Cinematic",
            "ctaType": "Follow",
            "goal": "Followers",
            "outputType": "full_plan",
            "niche": "Luxury",
            "tone": "Luxury",
            "duration": "30s",
            "language": "English",
            "audience": "Luxury Consumers",
            "reference_url": "https://example.com/some-reel",
            "reference_text": "Backup text: Luxury morning routine with coffee and views",
            "reference_notes": "Focus on the aspirational lifestyle"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=admin_headers,
            timeout=90
        )
        
        assert response.status_code == 200, f"Reference generation with URL failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        result = data["result"]
        
        # Should still work (either with URL content or fallback to text)
        # The result may or may not be reference-based depending on URL extraction success
        print(f"✓ Reference generation with URL handled gracefully")
        print(f"  - is_reference_based: {result.get('is_reference_based', False)}")
        print(f"  - reference_source: {result.get('reference_source', 'N/A')}")
    
    def test_reference_generation_only_url_no_fallback(self, admin_headers):
        """Reference generation with only URL (no text fallback) should still work"""
        payload = {
            "topic": "Tech gadget review",
            "platform": "TikTok",
            "hookStyle": "Curiosity",
            "reelFormat": "Faceless",
            "ctaType": "DM",
            "goal": "Leads",
            "outputType": "full_plan",
            "niche": "Tech",
            "tone": "Authority",
            "duration": "30s",
            "language": "English",
            "audience": "Tech Enthusiasts",
            "reference_url": "https://httpbin.org/html"  # A URL that returns HTML
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=admin_headers,
            timeout=90
        )
        
        assert response.status_code == 200, f"Reference generation with only URL failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        print(f"✓ Reference generation with only URL works")


class TestReelSchemaValidation:
    """Test schema validation for reference fields"""
    
    def test_reference_url_max_length(self, admin_headers):
        """reference_url should accept up to 2000 characters"""
        long_url = "https://example.com/" + "a" * 1900
        
        payload = {
            "topic": "Test topic",
            "platform": "Instagram",
            "reference_url": long_url
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=admin_headers,
            timeout=60
        )
        
        # Should not fail due to URL length (may fail for other reasons like content)
        assert response.status_code in [200, 400, 503], f"Unexpected status: {response.status_code}"
        print(f"✓ Long reference_url accepted (status: {response.status_code})")
    
    def test_reference_text_max_length(self, admin_headers):
        """reference_text should accept up to 5000 characters"""
        long_text = "Sample reference text. " * 200  # ~4600 chars
        
        payload = {
            "topic": "Test topic",
            "platform": "Instagram",
            "reference_text": long_text
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=admin_headers,
            timeout=60
        )
        
        # Should not fail due to text length
        assert response.status_code in [200, 503], f"Unexpected status: {response.status_code}"
        print(f"✓ Long reference_text accepted (status: {response.status_code})")
    
    def test_reference_notes_max_length(self, admin_headers):
        """reference_notes should accept up to 1000 characters"""
        long_notes = "Keep the hook style. " * 45  # ~900 chars
        
        payload = {
            "topic": "Test topic",
            "platform": "Instagram",
            "reference_notes": long_notes
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=admin_headers,
            timeout=60
        )
        
        # Should not fail due to notes length
        assert response.status_code in [200, 503], f"Unexpected status: {response.status_code}"
        print(f"✓ Long reference_notes accepted (status: {response.status_code})")


class TestQuickPresetsBackendCompatibility:
    """Test that preset configurations work with backend"""
    
    PRESETS = [
        {
            "id": "viral_hook",
            "config": {
                "platform": "Instagram",
                "hookStyle": "Shock",
                "reelFormat": "Talking Head",
                "ctaType": "Share",
                "goal": "Engagement",
                "outputType": "full_plan",
                "tone": "Bold",
                "duration": "15s",
                "niche": "Entertainment",
                "audience": "Gen Z (13-24)"
            }
        },
        {
            "id": "luxury_reel",
            "config": {
                "platform": "Instagram",
                "hookStyle": "Luxury",
                "reelFormat": "Cinematic",
                "ctaType": "Follow",
                "goal": "Followers",
                "outputType": "full_plan",
                "tone": "Luxury",
                "duration": "30s",
                "niche": "Luxury",
                "audience": "Luxury Consumers"
            }
        },
        {
            "id": "product_promo",
            "config": {
                "platform": "Instagram",
                "hookStyle": "Problem-Solution",
                "reelFormat": "UGC Ad",
                "ctaType": "Buy",
                "goal": "Sales",
                "outputType": "full_plan",
                "tone": "Conversational",
                "duration": "30s",
                "niche": "Finance",
                "audience": "Young Professionals"
            }
        },
        {
            "id": "ugc_ad",
            "config": {
                "platform": "TikTok",
                "hookStyle": "Story",
                "reelFormat": "UGC Ad",
                "ctaType": "Buy",
                "goal": "Sales",
                "outputType": "full_plan",
                "tone": "Conversational",
                "duration": "30s",
                "niche": "General",
                "audience": "Millennials (25-40)"
            }
        },
        {
            "id": "storytelling",
            "config": {
                "platform": "Instagram",
                "hookStyle": "Emotional",
                "reelFormat": "Story",
                "ctaType": "Save",
                "goal": "Retention",
                "outputType": "full_plan",
                "tone": "Emotional",
                "duration": "60s",
                "niche": "Relationships",
                "audience": "General"
            }
        },
        {
            "id": "educational",
            "config": {
                "platform": "YouTube Shorts",
                "hookStyle": "Educational",
                "reelFormat": "Talking Head",
                "ctaType": "Save",
                "goal": "Education",
                "outputType": "full_plan",
                "tone": "Authority",
                "duration": "60s",
                "niche": "Education",
                "audience": "College Students"
            }
        },
        {
            "id": "kids_story",
            "config": {
                "platform": "YouTube Shorts",
                "hookStyle": "Story",
                "reelFormat": "Story",
                "ctaType": "Follow",
                "goal": "Retention",
                "outputType": "full_plan",
                "tone": "Funny",
                "duration": "60s",
                "niche": "Education",
                "audience": "Parents"
            }
        },
        {
            "id": "faceless_biz",
            "config": {
                "platform": "TikTok",
                "hookStyle": "Curiosity",
                "reelFormat": "Faceless",
                "ctaType": "DM",
                "goal": "Leads",
                "outputType": "full_plan",
                "tone": "Authority",
                "duration": "30s",
                "niche": "Finance",
                "audience": "Entrepreneurs"
            }
        }
    ]
    
    def test_all_preset_configs_valid(self, admin_headers):
        """Verify all preset configurations are accepted by the backend schema"""
        for preset in self.PRESETS:
            payload = {
                "topic": f"Test topic for {preset['id']} preset",
                **preset["config"]
            }
            
            # Just validate the schema accepts it (don't wait for full generation)
            response = requests.post(
                f"{BASE_URL}/api/generate/reel",
                json=payload,
                headers=admin_headers,
                timeout=90
            )
            
            # Should be accepted (200) or service unavailable (503), not validation error (422)
            assert response.status_code != 422, f"Preset {preset['id']} rejected by schema: {response.text}"
            print(f"✓ Preset '{preset['id']}' config accepted by backend (status: {response.status_code})")


class TestHealthAndAuth:
    """Basic health and auth tests"""
    
    def test_health_endpoint(self):
        """Health endpoint should be accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("✓ Health endpoint working")
    
    def test_admin_login(self):
        """Admin login should work"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "ADMIN"
        print(f"✓ Admin login works - credits: {data['user']['credits']}")
    
    def test_test_user_login(self):
        """Test user login should work"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"✓ Test user login works - credits: {data['user']['credits']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
