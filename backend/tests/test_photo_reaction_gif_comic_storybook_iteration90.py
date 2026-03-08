"""
Photo Reaction GIF Creator + Comic Story Book Builder Template Library Tests
Iteration 90 - E2E Testing

Tests:
1. Photo Reaction GIF Creator:
   - GET /api/reaction-gif/reactions - Returns 9 reactions, 5 styles
   - GET /api/reaction-gif/pricing - Returns pricing config
   - POST /api/reaction-gif/generate - Copyright keyword blocking
   - POST /api/reaction-gif/generate - Single reaction mode
   - POST /api/reaction-gif/generate - Pack mode

2. Comic Story Book Builder Template Library:
   - GET /api/comic-storybook-v2/genres - Returns 8 genres
   - POST /api/comic-storybook-v2/preview - Template library integration
   - POST /api/comic-storybook-v2/generate - Copyright keyword blocking
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://narrative-visuals-6.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "demo@example.com"
TEST_USER_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for demo user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestPhotoReactionGIFCreator:
    """Photo Reaction GIF Creator API Tests (4-step wizard)"""
    
    def test_reactions_endpoint_returns_9_reactions(self, auth_headers):
        """Verify /api/reaction-gif/reactions returns exactly 9 reaction types"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/reactions", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        reactions = data.get("reactions", {})
        
        # Verify 9 reactions
        assert len(reactions) == 9, f"Expected 9 reactions, got {len(reactions)}"
        
        # Verify specific reactions exist
        expected_reactions = ["happy", "laughing", "love", "cool", "surprised", "sad", "celebrate", "waving", "wow"]
        for reaction in expected_reactions:
            assert reaction in reactions, f"Missing reaction: {reaction}"
            assert "emoji" in reactions[reaction], f"Reaction {reaction} missing emoji"
        
        print(f"✓ 9 reactions verified: {list(reactions.keys())}")
    
    def test_reactions_endpoint_returns_5_styles(self, auth_headers):
        """Verify /api/reaction-gif/reactions returns exactly 5 GIF styles"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/reactions", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        styles = data.get("styles", {})
        
        # Verify 5 styles
        assert len(styles) == 5, f"Expected 5 styles, got {len(styles)}"
        
        # Verify specific styles exist
        expected_styles = ["cartoon_motion", "comic_bounce", "sticker_style", "neon_glow", "minimal_clean"]
        for style in expected_styles:
            assert style in styles, f"Missing style: {style}"
            assert "name" in styles[style], f"Style {style} missing name"
        
        print(f"✓ 5 styles verified: {list(styles.keys())}")
    
    def test_single_mode_pricing(self, auth_headers):
        """Verify single mode pricing: base 8cr + add-ons"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/reactions", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        pricing = data.get("pricing", {}).get("single", {})
        
        assert pricing.get("base") == 8, "Single mode base should be 8 credits"
        assert pricing.get("hd_quality") == 3, "HD quality add-on should be 3 credits"
        assert pricing.get("transparent_bg") == 3, "Transparent BG add-on should be 3 credits"
        assert pricing.get("text_caption") == 2, "Text caption add-on should be 2 credits"
        assert pricing.get("commercial_license") == 10, "Commercial license add-on should be 10 credits"
        
        print("✓ Single mode pricing verified: 8 base + add-ons")
    
    def test_pack_mode_pricing(self, auth_headers):
        """Verify pack mode pricing: base 25cr + add-ons"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/reactions", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        pricing = data.get("pricing", {}).get("pack", {})
        
        assert pricing.get("base") == 25, "Pack mode base should be 25 credits"
        assert pricing.get("hd_quality") == 5, "HD quality add-on should be 5 credits"
        assert pricing.get("commercial_license") == 15, "Commercial license add-on should be 15 credits"
        
        print("✓ Pack mode pricing verified: 25 base + add-ons (6 GIFs)")
    
    def test_copyright_keyword_blocking_caption(self, auth_headers):
        """Verify copyright keywords are blocked in captions"""
        # Test various copyright keywords
        blocked_keywords = ["marvel", "disney", "batman", "pokemon", "harry potter"]
        
        for keyword in blocked_keywords:
            # Create a test image (small PNG)
            test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
            
            files = {'photo': ('test.png', test_image, 'image/png')}
            data = {
                'mode': 'single',
                'reaction': 'happy',
                'style': 'cartoon_motion',
                'caption': f'I love {keyword} heroes!'
            }
            
            response = requests.post(
                f"{BASE_URL}/api/reaction-gif/generate",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            # Should be blocked with 400
            assert response.status_code == 400, f"Keyword '{keyword}' should be blocked, got {response.status_code}"
            assert "copyrighted" in response.text.lower() or "brand" in response.text.lower(), \
                f"Error message should mention copyright/brand for '{keyword}'"
        
        print(f"✓ Copyright keyword blocking verified for: {blocked_keywords}")


class TestComicStorybookTemplateLibrary:
    """Comic Story Book Builder Template Library Tests (8 genre-specific templates)"""
    
    def test_genres_endpoint_returns_8_genres(self, auth_headers):
        """Verify /api/comic-storybook-v2/genres returns exactly 8 genres"""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/genres", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        genres = data.get("genres", {})
        
        # Verify 8 genres
        assert len(genres) == 8, f"Expected 8 genres, got {len(genres)}"
        
        # Verify specific genres exist
        expected_genres = ["kids_adventure", "superhero", "fantasy", "comedy", "romance", "scifi", "mystery", "horror_lite"]
        for genre in expected_genres:
            assert genre in genres, f"Missing genre: {genre}"
            assert "name" in genres[genre], f"Genre {genre} missing name"
        
        print(f"✓ 8 genres verified: {list(genres.keys())}")
    
    def test_genres_have_correct_names(self, auth_headers):
        """Verify genre names match spec"""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/genres", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        genres = data.get("genres", {})
        
        expected_names = {
            "kids_adventure": "Kids Adventure",
            "superhero": "Superhero",
            "fantasy": "Fantasy",
            "comedy": "Comedy",
            "romance": "Romance",
            "scifi": "Sci-Fi",
            "mystery": "Mystery",
            "horror_lite": "Spooky Fun"
        }
        
        for genre_id, expected_name in expected_names.items():
            assert genres[genre_id]["name"] == expected_name, \
                f"Genre {genre_id} should be named '{expected_name}', got '{genres[genre_id]['name']}'"
        
        print("✓ All 8 genre names verified")
    
    def test_pricing_page_counts(self, auth_headers):
        """Verify page count pricing: 10=25cr, 20=45cr, 30=60cr"""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/genres", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        pricing = data.get("pricing", {}).get("pages", {})
        
        assert pricing.get("10") == 25 or pricing.get(10) == 25, "10 pages should be 25 credits"
        assert pricing.get("20") == 45 or pricing.get(20) == 45, "20 pages should be 45 credits"
        assert pricing.get("30") == 60 or pricing.get(30) == 60, "30 pages should be 60 credits"
        
        print("✓ Page pricing verified: 10pg=25cr, 20pg=45cr, 30pg=60cr")
    
    def test_addons_pricing(self, auth_headers):
        """Verify 5 add-ons with correct pricing"""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/genres", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        add_ons = data.get("pricing", {}).get("add_ons", {})
        
        assert add_ons.get("personalized_cover") == 4, "Personalized cover should be 4 credits"
        assert add_ons.get("dedication_page") == 2, "Dedication page should be 2 credits"
        assert add_ons.get("activity_pages") == 5, "Activity pages should be 5 credits"
        assert add_ons.get("hd_print") == 5, "HD print should be 5 credits"
        assert add_ons.get("commercial_license") == 15, "Commercial license should be 15 credits"
        
        print("✓ All 5 add-ons pricing verified")
    
    def test_copyright_keyword_blocking_storyIdea(self, auth_headers):
        """Verify copyright keywords are blocked in story idea"""
        blocked_keywords = ["batman", "spiderman", "harry potter", "naruto", "marvel"]
        
        for keyword in blocked_keywords:
            response = requests.post(
                f"{BASE_URL}/api/comic-storybook-v2/preview",
                headers=auth_headers,
                json={
                    "genre": "kids_adventure",
                    "storyIdea": f"A kid meets {keyword} and goes on an adventure",
                    "title": "My Adventure",
                    "pageCount": 10
                }
            )
            
            # Should be blocked with 400
            assert response.status_code == 400, \
                f"Keyword '{keyword}' in story should be blocked, got {response.status_code}"
            assert "copyrighted" in response.text.lower() or "brand" in response.text.lower(), \
                f"Error message should mention copyright/brand for '{keyword}'"
        
        print(f"✓ Copyright keyword blocking verified in storyIdea for: {blocked_keywords}")
    
    def test_copyright_keyword_blocking_title(self, auth_headers):
        """Verify copyright keywords are blocked in title"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/preview",
            headers=auth_headers,
            json={
                "genre": "fantasy",
                "storyIdea": "An original magical adventure story",
                "title": "The Hogwarts Adventure",  # Copyright keyword in title
                "pageCount": 20
            }
        )
        
        # Should be blocked with 400
        assert response.status_code == 400, f"Copyright in title should be blocked, got {response.status_code}"
        assert "copyrighted" in response.text.lower() or "brand" in response.text.lower()
        
        print("✓ Copyright keyword blocking verified in title")
    
    def test_preview_with_valid_content(self, auth_headers):
        """Verify preview works with original, non-copyrighted content"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/preview",
            headers=auth_headers,
            json={
                "genre": "kids_adventure",
                "storyIdea": "Luna the bunny discovers a magical garden where flowers can talk and teach her about kindness",
                "title": "Luna's Magical Garden",
                "pageCount": 10
            }
        )
        
        assert response.status_code == 200, f"Valid content should succeed, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "previewPages" in data, "Response should contain previewPages"
        
        print("✓ Preview with valid original content verified")
    
    def test_generate_with_template_content(self, auth_headers):
        """Test generate endpoint with template-style content"""
        # Using a template-like story from kids_adventure
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/generate",
            headers=auth_headers,
            json={
                "genre": "kids_adventure",
                "storyIdea": "It's Max's birthday, and a magical balloon floats down with a treasure map! Max and their best friend go on an exciting adventure through the neighborhood to find the hidden birthday surprise.",
                "title": "Max's Birthday Adventure",
                "author": "Test Author",
                "pageCount": 10,
                "addOns": {
                    "personalized_cover": True,
                    "dedication_page": False,
                    "activity_pages": False,
                    "hd_print": False,
                    "commercial_license": False
                },
                "dedicationText": None
            }
        )
        
        assert response.status_code == 200, f"Generate should succeed, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "jobId" in data, "Response should contain jobId"
        
        print(f"✓ Generate with template content verified, jobId: {data.get('jobId', 'N/A')[:8]}...")


class TestAPIEndpointAvailability:
    """Verify all required endpoints are available and authenticated"""
    
    def test_reaction_gif_pricing_endpoint(self, auth_headers):
        """Verify GET /api/reaction-gif/pricing returns pricing"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/pricing", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "pricing" in data, "Response should contain pricing"
        
        print("✓ /api/reaction-gif/pricing endpoint working")
    
    def test_comic_storybook_pricing_endpoint(self, auth_headers):
        """Verify GET /api/comic-storybook-v2/pricing returns pricing"""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/pricing", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "pricing" in data, "Response should contain pricing"
        
        print("✓ /api/comic-storybook-v2/pricing endpoint working")
    
    def test_reaction_gif_history_endpoint(self, auth_headers):
        """Verify GET /api/reaction-gif/history returns user history"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/history", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "jobs" in data, "Response should contain jobs array"
        assert "total" in data, "Response should contain total count"
        
        print("✓ /api/reaction-gif/history endpoint working")
    
    def test_comic_storybook_history_endpoint(self, auth_headers):
        """Verify GET /api/comic-storybook-v2/history returns user history"""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/history", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "jobs" in data, "Response should contain jobs array"
        assert "total" in data, "Response should contain total count"
        
        print("✓ /api/comic-storybook-v2/history endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
