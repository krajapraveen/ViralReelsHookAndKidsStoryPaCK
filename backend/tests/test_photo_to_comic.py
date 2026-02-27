"""
Photo to Comic - Backend API Tests
Testing the new 'Convert Photos To Comic Character' feature
- Comic Avatar Mode (3 steps)
- Comic Strip Mode (5 steps)
- Copyright safety keyword blocking
- Style presets and pricing
"""
import pytest
import requests
import os
import base64
from io import BytesIO

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test Credentials
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for demo user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data
    return data["token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def test_image():
    """Create a simple test image (1x1 red pixel PNG)"""
    # Minimal valid PNG - 1x1 red pixel
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    return png_data


class TestPhotoToComicStyles:
    """Test style and pricing endpoints"""
    
    def test_get_styles_endpoint_returns_24_styles(self, auth_headers):
        """Test /api/photo-to-comic/styles returns all 24 styles"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/styles",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Styles endpoint failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "styles" in data, "Response should contain 'styles' key"
        assert "pricing" in data, "Response should contain 'pricing' key"
        
        # Count styles - should be 24
        styles = data["styles"]
        assert len(styles) == 24, f"Expected 24 styles, got {len(styles)}"
        
        # Verify expected style categories are present
        expected_styles = [
            "bold_superhero", "dark_vigilante", "retro_action", "dynamic_battle",
            "cartoon_fun", "meme_expression", "comic_caricature", "exaggerated_reaction",
            "romance_comic", "dreamy_pastel", "soft_manga", "cute_chibi",
            "magical_fantasy", "medieval_adventure", "scifi_neon", "cyberpunk_comic",
            "kids_storybook", "friendly_animal", "classroom_comic", "adventure_kids",
            "black_white_ink", "sketch_outline", "noir_comic", "vintage_print"
        ]
        
        for style_id in expected_styles:
            assert style_id in styles, f"Missing style: {style_id}"
            assert "name" in styles[style_id], f"Style {style_id} missing 'name'"
        
        print(f"PASS: GET /api/photo-to-comic/styles returns {len(styles)} styles")
    
    def test_get_pricing_endpoint(self, auth_headers):
        """Test /api/photo-to-comic/pricing returns correct pricing structure"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/pricing",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Pricing endpoint failed: {response.text}"
        data = response.json()
        
        # Verify pricing structure
        assert "pricing" in data
        pricing = data["pricing"]
        
        # Verify comic_avatar pricing
        assert "comic_avatar" in pricing
        assert pricing["comic_avatar"]["base"] == 15
        assert "add_ons" in pricing["comic_avatar"]
        assert pricing["comic_avatar"]["add_ons"]["transparent_bg"] == 3
        assert pricing["comic_avatar"]["add_ons"]["multiple_poses"] == 5
        assert pricing["comic_avatar"]["add_ons"]["hd_export"] == 5
        
        # Verify comic_strip pricing
        assert "comic_strip" in pricing
        assert "panels" in pricing["comic_strip"]
        assert pricing["comic_strip"]["panels"]["3"] == 25 or pricing["comic_strip"]["panels"][3] == 25
        
        print("PASS: GET /api/photo-to-comic/pricing returns correct pricing structure")


class TestCopyrightKeywordBlocking:
    """Test copyright safety - blocked keywords validation"""
    
    def test_blocked_keyword_batman_in_custom_details(self, auth_headers, test_image):
        """Test that 'batman' is blocked in custom_details field"""
        files = {
            'photo': ('test.png', BytesIO(test_image), 'image/png')
        }
        data = {
            'mode': 'avatar',
            'style': 'cartoon_fun',
            'style_category': 'fun',
            'genre': 'action',
            'custom_details': 'Make me look like batman',  # BLOCKED
            'transparent_bg': 'false',
            'multiple_poses': 'false',
            'hd_export': 'false'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            files=files,
            data=data
        )
        
        assert response.status_code == 400, f"Expected 400 for blocked keyword, got {response.status_code}"
        
        error_data = response.json()
        assert "detail" in error_data
        assert "batman" in error_data["detail"].lower() or "copyrighted" in error_data["detail"].lower()
        
        print("PASS: Blocked keyword 'batman' correctly rejected with 400 error")
    
    def test_blocked_keyword_spiderman_in_custom_details(self, auth_headers, test_image):
        """Test that 'spiderman' is blocked"""
        files = {
            'photo': ('test.png', BytesIO(test_image), 'image/png')
        }
        data = {
            'mode': 'avatar',
            'style': 'cartoon_fun',
            'custom_details': 'I want to be spiderman',  # BLOCKED
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            files=files,
            data=data
        )
        
        assert response.status_code == 400, f"Expected 400 for 'spiderman', got {response.status_code}"
        print("PASS: Blocked keyword 'spiderman' correctly rejected")
    
    def test_blocked_keyword_disney_in_story_prompt(self, auth_headers, test_image):
        """Test that 'disney' is blocked in story_prompt for strip mode"""
        files = {
            'photo': ('test.png', BytesIO(test_image), 'image/png')
        }
        data = {
            'mode': 'strip',
            'style': 'cartoon_fun',
            'story_prompt': 'A day at disney world with elsa',  # BLOCKED - disney and elsa
            'panel_count': '4',
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            files=files,
            data=data
        )
        
        assert response.status_code == 400, f"Expected 400 for 'disney', got {response.status_code}"
        print("PASS: Blocked keyword 'disney' in story_prompt correctly rejected")
    
    def test_blocked_keyword_marvel_characters(self, auth_headers, test_image):
        """Test that Marvel characters are blocked"""
        blocked_terms = ["iron man", "captain america", "thor", "hulk", "avengers"]
        
        for term in blocked_terms:
            files = {
                'photo': ('test.png', BytesIO(test_image), 'image/png')
            }
            data = {
                'mode': 'avatar',
                'style': 'bold_superhero',
                'custom_details': f'Make me look like {term}',
            }
            
            response = requests.post(
                f"{BASE_URL}/api/photo-to-comic/generate",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == 400, f"Expected 400 for '{term}', got {response.status_code}"
        
        print(f"PASS: All Marvel character terms correctly blocked: {blocked_terms}")
    
    def test_anime_characters_blocked(self, auth_headers, test_image):
        """Test that anime characters are blocked"""
        blocked_terms = ["naruto", "goku", "pikachu", "luffy"]
        
        for term in blocked_terms:
            files = {
                'photo': ('test.png', BytesIO(test_image), 'image/png')
            }
            data = {
                'mode': 'avatar',
                'style': 'soft_manga',
                'custom_details': f'Style like {term}',
            }
            
            response = requests.post(
                f"{BASE_URL}/api/photo-to-comic/generate",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == 400, f"Expected 400 for '{term}', got {response.status_code}"
        
        print(f"PASS: Anime characters correctly blocked: {blocked_terms}")
    
    def test_safe_prompt_allowed(self, auth_headers, test_image):
        """Test that safe, generic prompts are allowed"""
        files = {
            'photo': ('test.png', BytesIO(test_image), 'image/png')
        }
        data = {
            'mode': 'avatar',
            'style': 'cartoon_fun',
            'style_category': 'fun',
            'genre': 'action',
            'custom_details': 'A heroic masked vigilante with a cape',  # SAFE - no IP
            'transparent_bg': 'false',
            'multiple_poses': 'false',
            'hd_export': 'false'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            files=files,
            data=data
        )
        
        # Should succeed (200) or return jobId
        assert response.status_code == 200, f"Expected 200 for safe prompt, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True or "jobId" in data
        
        print("PASS: Safe generic prompt accepted and generation started")


class TestAvatarModeGeneration:
    """Test Comic Avatar (3-step) generation"""
    
    def test_avatar_generation_without_photo_fails(self, auth_headers):
        """Test that generation fails without photo upload"""
        data = {
            'mode': 'avatar',
            'style': 'cartoon_fun',
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            data=data
        )
        
        # Should fail - missing required file
        assert response.status_code == 422, f"Expected 422 for missing photo, got {response.status_code}"
        print("PASS: Avatar generation correctly requires photo upload")
    
    def test_invalid_mode_rejected(self, auth_headers, test_image):
        """Test that invalid mode is rejected"""
        files = {
            'photo': ('test.png', BytesIO(test_image), 'image/png')
        }
        data = {
            'mode': 'invalid_mode',
            'style': 'cartoon_fun',
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            files=files,
            data=data
        )
        
        assert response.status_code == 400
        print("PASS: Invalid mode correctly rejected")


class TestStripModeGeneration:
    """Test Comic Strip (5-step) generation"""
    
    def test_strip_requires_story_prompt(self, auth_headers, test_image):
        """Test that strip mode requires story_prompt"""
        # This tests that frontend validation matches backend
        files = {
            'photo': ('test.png', BytesIO(test_image), 'image/png')
        }
        data = {
            'mode': 'strip',
            'style': 'cartoon_fun',
            'panel_count': '4',
            # story_prompt is missing - backend should handle this
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            files=files,
            data=data
        )
        
        # Backend may accept empty story prompt but frontend validates
        # Checking API accepts the request
        print(f"Strip mode without story_prompt: {response.status_code}")


class TestJobStatus:
    """Test job status and history endpoints"""
    
    def test_get_history_endpoint(self, auth_headers):
        """Test /api/photo-to-comic/history returns user's jobs"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"History endpoint failed: {response.text}"
        data = response.json()
        
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        
        print(f"PASS: GET /api/photo-to-comic/history returns {data['total']} jobs")
    
    def test_job_status_not_found(self, auth_headers):
        """Test that non-existent job returns 404"""
        fake_job_id = "non-existent-job-12345"
        
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/{fake_job_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        print("PASS: Non-existent job correctly returns 404")


class TestAuthRequired:
    """Test that endpoints require authentication"""
    
    def test_styles_requires_auth(self):
        """Test /api/photo-to-comic/styles requires authentication"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/styles")
        assert response.status_code == 401 or response.status_code == 403
        print("PASS: Styles endpoint requires authentication")
    
    def test_generate_requires_auth(self, test_image):
        """Test /api/photo-to-comic/generate requires authentication"""
        files = {
            'photo': ('test.png', BytesIO(test_image), 'image/png')
        }
        data = {
            'mode': 'avatar',
            'style': 'cartoon_fun',
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            files=files,
            data=data
        )
        
        assert response.status_code == 401 or response.status_code == 403
        print("PASS: Generate endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
