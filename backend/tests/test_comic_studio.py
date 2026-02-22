"""
Comic Studio Backend API Tests
Tests: Genres, Assets, Templates, Layouts, Story Generation, Export
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestComicStudioGenres:
    """Test comic genre endpoints"""
    
    def test_get_all_genres(self):
        """Test GET /api/comic/genres returns all 8 genres"""
        response = requests.get(f"{BASE_URL}/api/comic/genres")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "genres" in data, "Response should have 'genres' key"
        
        genres = data["genres"]
        assert len(genres) == 8, f"Expected 8 genres, got {len(genres)}"
        
        # Verify all expected genres are present
        expected_genres = ["superhero", "romance", "comedy", "scifi", "fantasy", "mystery", "horror", "kids"]
        genre_ids = [g["id"] for g in genres]
        for expected in expected_genres:
            assert expected in genre_ids, f"Missing genre: {expected}"
        
        # Verify genre structure
        for genre in genres:
            assert "id" in genre, "Genre should have 'id'"
            assert "name" in genre, "Genre should have 'name'"
            assert "description" in genre, "Genre should have 'description'"
            assert "colorGrading" in genre, "Genre should have 'colorGrading'"
            assert "sfx" in genre, "Genre should have 'sfx'"
            assert isinstance(genre["sfx"], list), "SFX should be a list"
        
        print(f"SUCCESS: Got {len(genres)} genres with correct structure")

    def test_get_genre_details_superhero(self):
        """Test GET /api/comic/genres/superhero returns detailed config"""
        response = requests.get(f"{BASE_URL}/api/comic/genres/superhero")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        genre = data.get("genre", {})
        
        assert genre.get("id") == "superhero"
        assert genre.get("name") == "Superhero"
        assert "overlays" in genre, "Should have overlays"
        assert "frameStyle" in genre, "Should have frameStyle"
        
        print("SUCCESS: Superhero genre details returned correctly")

    def test_get_genre_details_not_found(self):
        """Test GET /api/comic/genres/invalid returns 404"""
        response = requests.get(f"{BASE_URL}/api/comic/genres/invalid_genre_xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Invalid genre returns 404")


class TestComicStudioAssets:
    """Test comic assets endpoints"""
    
    def test_get_superhero_assets(self):
        """Test GET /api/comic/assets/superhero returns stickers, frames, bubbles, sfx"""
        response = requests.get(f"{BASE_URL}/api/comic/assets/superhero")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("genre") == "superhero"
        
        # Check stickers
        assert "stickers" in data, "Should have stickers"
        assert isinstance(data["stickers"], list), "Stickers should be a list"
        assert len(data["stickers"]) > 0, "Should have at least one sticker"
        
        # Check sticker structure
        sticker = data["stickers"][0]
        assert "id" in sticker, "Sticker should have 'id'"
        assert "url" in sticker, "Sticker should have 'url'"
        assert "name" in sticker, "Sticker should have 'name'"
        
        # Check frames
        assert "frames" in data, "Should have frames"
        assert len(data["frames"]) > 0, "Should have at least one frame"
        
        # Check bubbles
        assert "bubbles" in data, "Should have bubbles"
        assert len(data["bubbles"]) > 0, "Should have at least one bubble"
        
        # Check SFX
        assert "sfx" in data, "Should have sfx"
        assert isinstance(data["sfx"], list), "SFX should be a list"
        assert "BAM!" in data["sfx"] or "POW!" in data["sfx"], "Superhero SFX should include BAM! or POW!"
        
        print(f"SUCCESS: Superhero assets - {len(data['stickers'])} stickers, {len(data['frames'])} frames, {len(data['bubbles'])} bubbles, {len(data['sfx'])} sfx")

    def test_get_romance_assets(self):
        """Test GET /api/comic/assets/romance"""
        response = requests.get(f"{BASE_URL}/api/comic/assets/romance")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("genre") == "romance"
        assert "sfx" in data
        print("SUCCESS: Romance assets returned correctly")

    def test_get_assets_invalid_genre(self):
        """Test GET /api/comic/assets/invalid returns 404"""
        response = requests.get(f"{BASE_URL}/api/comic/assets/invalid_xyz")
        assert response.status_code == 404
        print("SUCCESS: Invalid genre assets returns 404")


class TestComicStudioTemplates:
    """Test story template endpoints"""
    
    def test_get_superhero_templates(self):
        """Test GET /api/comic/templates/superhero returns story templates"""
        response = requests.get(f"{BASE_URL}/api/comic/templates/superhero")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("genre") == "superhero"
        
        # Check templates
        assert "templates" in data, "Should have templates"
        templates = data["templates"]
        assert isinstance(templates, list), "Templates should be a list"
        assert len(templates) >= 1, "Should have at least one template"
        
        # Check template structure
        template = templates[0]
        assert "title" in template, "Template should have 'title'"
        assert "premise" in template, "Template should have 'premise'"
        assert "panels" in template, "Template should have 'panels'"
        assert "ending" in template, "Template should have 'ending'"
        
        # Check panels structure
        panels = template["panels"]
        assert len(panels) >= 4, "Should have at least 4 panels"
        panel = panels[0]
        assert "caption" in panel, "Panel should have 'caption'"
        assert "bubble" in panel, "Panel should have 'bubble'"
        
        # Check variables
        assert "variables" in data, "Should have variables for customization"
        variables = data["variables"]
        assert "character_names" in variables
        assert "places" in variables
        
        print(f"SUCCESS: Got {len(templates)} templates with {len(panels)} panels each")

    def test_get_all_genre_templates(self):
        """Test templates exist for all genres"""
        genres = ["superhero", "romance", "comedy", "scifi", "fantasy", "mystery", "horror", "kids"]
        
        for genre in genres:
            response = requests.get(f"{BASE_URL}/api/comic/templates/{genre}")
            assert response.status_code == 200, f"Templates for {genre} returned {response.status_code}"
            data = response.json()
            assert len(data.get("templates", [])) >= 1, f"Genre {genre} should have at least 1 template"
        
        print(f"SUCCESS: All {len(genres)} genres have story templates")


class TestComicStudioLayouts:
    """Test layout endpoint"""
    
    def test_get_layouts(self):
        """Test GET /api/comic/layouts returns 5 layouts"""
        response = requests.get(f"{BASE_URL}/api/comic/layouts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "layouts" in data, "Response should have 'layouts' key"
        
        layouts = data["layouts"]
        assert len(layouts) == 5, f"Expected 5 layouts, got {len(layouts)}"
        
        # Verify expected layout IDs
        layout_ids = [l["id"] for l in layouts]
        expected = ["1", "2h", "2v", "4", "6"]
        for exp in expected:
            assert exp in layout_ids, f"Missing layout: {exp}"
        
        # Verify layout structure
        for layout in layouts:
            assert "id" in layout
            assert "name" in layout
            assert "rows" in layout
            assert "cols" in layout
        
        print(f"SUCCESS: Got {len(layouts)} layouts: {layout_ids}")


class TestComicStudioExportCost:
    """Test export cost calculation"""
    
    def test_export_cost_default(self):
        """Test GET /api/comic/export-cost with defaults"""
        response = requests.get(f"{BASE_URL}/api/comic/export-cost")
        assert response.status_code == 200
        
        data = response.json()
        assert "totalCost" in data
        assert "breakdown" in data
        assert data["totalCost"] == 8, "Default 4-panel export should cost 8 credits"
        print("SUCCESS: Default export cost is 8 credits")

    def test_export_cost_more_panels(self):
        """Test export cost with more than 4 panels"""
        response = requests.get(f"{BASE_URL}/api/comic/export-cost?panel_count=6")
        assert response.status_code == 200
        
        data = response.json()
        assert data["totalCost"] == 10, "6-panel export should cost 10 credits"
        print("SUCCESS: 6-panel export cost is 10 credits")

    def test_export_cost_story_mode(self):
        """Test export cost with story mode enabled"""
        response = requests.get(f"{BASE_URL}/api/comic/export-cost?panel_count=4&story_mode=true")
        assert response.status_code == 200
        
        data = response.json()
        assert data["totalCost"] == 9, "4-panel + story mode should cost 9 credits (8+1)"
        assert data["breakdown"]["story_mode"] == 1
        print("SUCCESS: Story mode adds 1 credit")

    def test_export_cost_no_watermark(self):
        """Test export cost with watermark removal"""
        response = requests.get(f"{BASE_URL}/api/comic/export-cost?panel_count=4&remove_watermark=true")
        assert response.status_code == 200
        
        data = response.json()
        assert data["totalCost"] == 10, "4-panel + no watermark should cost 10 credits (8+2)"
        assert data["breakdown"]["watermark_removal"] == 2
        print("SUCCESS: Watermark removal adds 2 credits")

    def test_export_cost_all_options(self):
        """Test export cost with all options"""
        response = requests.get(f"{BASE_URL}/api/comic/export-cost?panel_count=6&story_mode=true&remove_watermark=true")
        assert response.status_code == 200
        
        data = response.json()
        expected = 10 + 1 + 2  # base (6 panels) + story + watermark
        assert data["totalCost"] == expected, f"Expected {expected}, got {data['totalCost']}"
        print(f"SUCCESS: All options export cost is {expected} credits")


class TestComicStudioStoryGeneration:
    """Test story generation (requires auth)"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth token for demo user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if login_response.status_code != 200:
            pytest.skip("Could not authenticate demo user")
        
        token = login_response.json().get("token")
        return {"Authorization": f"Bearer {token}"}

    def test_generate_story_superhero(self, auth_headers):
        """Test POST /api/comic/generate-story"""
        response = requests.post(
            f"{BASE_URL}/api/comic/generate-story",
            json={
                "genre": "superhero",
                "tone": "normal",
                "character_name": "TestHero",
                "panel_count": 4
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "title" in data, "Should have title"
        assert "premise" in data, "Should have premise"
        assert "panels" in data, "Should have panels"
        assert "ending" in data, "Should have ending"
        
        panels = data["panels"]
        assert len(panels) == 4, f"Should have 4 panels, got {len(panels)}"
        
        # Check panel structure
        panel = panels[0]
        assert "panelNumber" in panel
        assert "caption" in panel
        assert "bubbleText" in panel
        
        print(f"SUCCESS: Generated story '{data['title']}' with {len(panels)} panels")

    def test_generate_story_with_6_panels(self, auth_headers):
        """Test story generation with 6 panels"""
        response = requests.post(
            f"{BASE_URL}/api/comic/generate-story",
            json={
                "genre": "comedy",
                "character_name": "Funny Guy",
                "panel_count": 6
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["panels"]) == 6
        print("SUCCESS: Generated 6-panel comedy story")

    def test_generate_story_invalid_genre(self, auth_headers):
        """Test story generation with invalid genre"""
        response = requests.post(
            f"{BASE_URL}/api/comic/generate-story",
            json={
                "genre": "invalid_genre",
                "panel_count": 4
            },
            headers=auth_headers
        )
        assert response.status_code == 404
        print("SUCCESS: Invalid genre returns 404")

    def test_generate_story_requires_auth(self):
        """Test story generation without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/comic/generate-story",
            json={
                "genre": "superhero",
                "panel_count": 4
            }
        )
        assert response.status_code == 401 or response.status_code == 403
        print("SUCCESS: Story generation requires auth")


class TestComicStudioExport:
    """Test export endpoint (requires auth)"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth token for demo user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if login_response.status_code != 200:
            pytest.skip("Could not authenticate demo user")
        
        token = login_response.json().get("token")
        return {"Authorization": f"Bearer {token}"}

    def test_export_requires_auth(self):
        """Test export without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/comic/export",
            json={
                "export_type": "PNG",
                "panel_count": 4,
                "genre": "superhero",
                "has_watermark": True,
                "story_mode": False
            }
        )
        assert response.status_code in [401, 403]
        print("SUCCESS: Export requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
