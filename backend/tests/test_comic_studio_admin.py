"""
Comic Studio Admin API Tests
Tests: Admin genre management, template management, admin stats
Features: Admin CMS for genre pack and template management
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestComicStudioAdminAuth:
    """Test admin route authentication"""
    
    @pytest.fixture
    def demo_headers(self):
        """Get auth token for demo user (non-admin)"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if login_response.status_code != 200:
            pytest.skip("Could not authenticate demo user")
        
        token = login_response.json().get("token")
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def admin_headers(self):
        """Get auth token for admin user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if login_response.status_code != 200:
            pytest.skip("Could not authenticate admin user")
        
        token = login_response.json().get("token")
        return {"Authorization": f"Bearer {token}"}

    def test_admin_genres_requires_auth(self):
        """Test GET /api/comic/admin/genres requires authentication"""
        response = requests.get(f"{BASE_URL}/api/comic/admin/genres")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("SUCCESS: Admin genres endpoint requires authentication")

    def test_admin_genres_requires_admin_role(self, demo_headers):
        """Test GET /api/comic/admin/genres requires admin role"""
        response = requests.get(
            f"{BASE_URL}/api/comic/admin/genres",
            headers=demo_headers
        )
        assert response.status_code == 403, f"Expected 403 (forbidden for non-admin), got {response.status_code}"
        print("SUCCESS: Admin genres endpoint requires admin role")

    def test_admin_genres_accessible_by_admin(self, admin_headers):
        """Test GET /api/comic/admin/genres is accessible by admin"""
        response = requests.get(
            f"{BASE_URL}/api/comic/admin/genres",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "genres" in data
        genres = data["genres"]
        assert len(genres) >= 8, f"Expected at least 8 genres, got {len(genres)}"
        
        # Admin endpoint should return full config including overlays
        genre = genres[0]
        assert "id" in genre
        assert "name" in genre
        assert "overlays" in genre, "Admin view should include overlays"
        
        print(f"SUCCESS: Admin can access genres ({len(genres)} genres)")


class TestComicStudioAdminGenreManagement:
    """Test admin genre CRUD operations"""
    
    @pytest.fixture
    def admin_headers(self):
        """Get auth token for admin user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if login_response.status_code != 200:
            pytest.skip("Could not authenticate admin user")
        
        token = login_response.json().get("token")
        return {"Authorization": f"Bearer {token}"}

    def test_admin_create_genre(self, admin_headers):
        """Test POST /api/comic/admin/genres creates new genre"""
        test_genre = {
            "id": "test_genre_001",
            "name": "Test Genre",
            "description": "A test genre for testing",
            "colorGrading": {"contrast": 1.0, "saturation": 1.0, "brightness": 1.0},
            "sfx": ["TEST!", "BOOM!"],
            "bubbleStyle": "bold",
            "frameStyle": "angular"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comic/admin/genres",
            json=test_genre,
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("genre", {}).get("id") == "test_genre_001"
        
        print("SUCCESS: Admin can create new genre")
        
        # Cleanup - delete the test genre
        requests.delete(
            f"{BASE_URL}/api/comic/admin/genres/test_genre_001",
            headers=admin_headers
        )

    def test_admin_cannot_create_duplicate_genre(self, admin_headers):
        """Test admin cannot create genre with existing ID"""
        response = requests.post(
            f"{BASE_URL}/api/comic/admin/genres",
            json={
                "id": "superhero",  # Already exists
                "name": "Duplicate Superhero",
                "description": "Duplicate test"
            },
            headers=admin_headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("SUCCESS: Cannot create duplicate genre")

    def test_admin_update_genre(self, admin_headers):
        """Test PUT /api/comic/admin/genres/{id} updates genre"""
        # First create a test genre
        create_response = requests.post(
            f"{BASE_URL}/api/comic/admin/genres",
            json={
                "id": "test_update_genre",
                "name": "Original Name",
                "description": "Original description"
            },
            headers=admin_headers
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create test genre")
        
        # Update the genre
        update_response = requests.put(
            f"{BASE_URL}/api/comic/admin/genres/test_update_genre",
            json={
                "id": "test_update_genre",
                "name": "Updated Name",
                "description": "Updated description",
                "sfx": ["NEW!", "SFX!"]
            },
            headers=admin_headers
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}"
        
        data = update_response.json()
        assert data.get("genre", {}).get("name") == "Updated Name"
        
        print("SUCCESS: Admin can update genre")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/comic/admin/genres/test_update_genre",
            headers=admin_headers
        )

    def test_admin_cannot_delete_builtin_genres(self, admin_headers):
        """Test admin cannot delete built-in genres"""
        builtin_genres = ["superhero", "romance", "comedy"]
        
        for genre_id in builtin_genres:
            response = requests.delete(
                f"{BASE_URL}/api/comic/admin/genres/{genre_id}",
                headers=admin_headers
            )
            assert response.status_code == 400, f"Should not be able to delete {genre_id}"
        
        print("SUCCESS: Cannot delete built-in genres")


class TestComicStudioAdminTemplates:
    """Test admin template management"""
    
    @pytest.fixture
    def admin_headers(self):
        """Get auth token for admin user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if login_response.status_code != 200:
            pytest.skip("Could not authenticate admin user")
        
        token = login_response.json().get("token")
        return {"Authorization": f"Bearer {token}"}

    def test_admin_get_templates(self, admin_headers):
        """Test GET /api/comic/admin/templates/{genre_id}"""
        response = requests.get(
            f"{BASE_URL}/api/comic/admin/templates/superhero",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("genre") == "superhero"
        assert "templates" in data
        assert len(data["templates"]) >= 1
        
        print(f"SUCCESS: Admin can get templates ({len(data['templates'])} for superhero)")

    def test_admin_get_templates_requires_admin(self):
        """Test template admin endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/comic/admin/templates/superhero")
        assert response.status_code in [401, 403]
        print("SUCCESS: Admin templates requires authentication")

    def test_admin_create_template(self, admin_headers):
        """Test POST /api/comic/admin/templates creates new template"""
        new_template = {
            "genre": "superhero",
            "title": "Test Story",
            "premise": "A test story for testing",
            "panels": [
                {"caption": "Panel 1", "bubble": "Hello!"},
                {"caption": "Panel 2", "bubble": "Testing!"},
                {"caption": "Panel 3", "bubble": "Works!"},
                {"caption": "Panel 4", "bubble": "Great!"}
            ],
            "ending": "The end of the test."
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comic/admin/templates",
            json=new_template,
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("template", {}).get("title") == "Test Story"
        
        print("SUCCESS: Admin can create new template")


class TestComicStudioAdminStats:
    """Test admin statistics endpoint"""
    
    @pytest.fixture
    def admin_headers(self):
        """Get auth token for admin user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if login_response.status_code != 200:
            pytest.skip("Could not authenticate admin user")
        
        token = login_response.json().get("token")
        return {"Authorization": f"Bearer {token}"}

    def test_admin_get_stats(self, admin_headers):
        """Test GET /api/comic/admin/stats returns usage statistics"""
        response = requests.get(
            f"{BASE_URL}/api/comic/admin/stats",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "totalExports" in data, "Should have totalExports"
        assert "availableGenres" in data, "Should have availableGenres"
        assert "totalTemplates" in data, "Should have totalTemplates"
        assert "genreStats" in data, "Should have genreStats"
        
        assert data["availableGenres"] >= 8, "Should have at least 8 genres"
        
        print(f"SUCCESS: Admin stats - {data['totalExports']} exports, {data['availableGenres']} genres, {data['totalTemplates']} templates")

    def test_admin_stats_requires_admin(self):
        """Test stats endpoint requires admin role"""
        response = requests.get(f"{BASE_URL}/api/comic/admin/stats")
        assert response.status_code in [401, 403]
        print("SUCCESS: Admin stats requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
