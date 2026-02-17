"""
Test Content Vault API endpoints
Tests for Kids Story Themes, Moral Templates, Reel Structures, and Viral Hooks
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = {
    "email": "demo@example.com",
    "password": "Password123!"
}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=TEST_USER,
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def authenticated_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestContentVaultAPI:
    """Test Content Vault endpoint"""
    
    def test_content_vault_returns_200(self, authenticated_client):
        """Test that Content Vault endpoint returns 200"""
        response = authenticated_client.get(f"{BASE_URL}/api/content/vault")
        assert response.status_code == 200
        print(f"Content Vault API returned status: {response.status_code}")
    
    def test_content_vault_returns_kids_themes(self, authenticated_client):
        """Test that Content Vault returns kids_themes array"""
        response = authenticated_client.get(f"{BASE_URL}/api/content/vault")
        assert response.status_code == 200
        
        data = response.json()
        assert "kids_themes" in data, "kids_themes key missing from response"
        assert isinstance(data["kids_themes"], list), "kids_themes should be a list"
        assert len(data["kids_themes"]) > 0, "kids_themes should not be empty"
        
        # Verify structure of first theme
        first_theme = data["kids_themes"][0]
        assert "theme" in first_theme, "theme field missing"
        assert "age_group" in first_theme, "age_group field missing"
        assert "moral" in first_theme, "moral field missing"
        
        print(f"Kids Themes count: {len(data['kids_themes'])}")
        print(f"First theme: {first_theme['theme']}")
    
    def test_content_vault_returns_moral_templates(self, authenticated_client):
        """Test that Content Vault returns moral_templates array"""
        response = authenticated_client.get(f"{BASE_URL}/api/content/vault")
        assert response.status_code == 200
        
        data = response.json()
        assert "moral_templates" in data, "moral_templates key missing from response"
        assert isinstance(data["moral_templates"], list), "moral_templates should be a list"
        assert len(data["moral_templates"]) > 0, "moral_templates should not be empty"
        
        # Verify structure of first template
        first_template = data["moral_templates"][0]
        assert "theme" in first_template, "theme field missing"
        assert "moral" in first_template, "moral field missing"
        
        print(f"Moral Templates count: {len(data['moral_templates'])}")
        print(f"First template theme: {first_template['theme']}")
    
    def test_content_vault_returns_reel_structures(self, authenticated_client):
        """Test that Content Vault returns reel_structures with best_for field"""
        response = authenticated_client.get(f"{BASE_URL}/api/content/vault")
        assert response.status_code == 200
        
        data = response.json()
        assert "reel_structures" in data, "reel_structures key missing from response"
        assert isinstance(data["reel_structures"], list), "reel_structures should be a list"
        assert len(data["reel_structures"]) > 0, "reel_structures should not be empty"
        
        # Verify structure of first reel structure
        first_structure = data["reel_structures"][0]
        assert "name" in first_structure, "name field missing"
        assert "structure" in first_structure, "structure field missing"
        assert "best_for" in first_structure, "best_for field missing"
        
        print(f"Reel Structures count: {len(data['reel_structures'])}")
        print(f"First structure: {first_structure['name']}")
        print(f"Best for: {first_structure['best_for']}")
    
    def test_content_vault_returns_viral_hooks(self, authenticated_client):
        """Test that Content Vault returns viral_hooks array"""
        response = authenticated_client.get(f"{BASE_URL}/api/content/vault")
        assert response.status_code == 200
        
        data = response.json()
        assert "viral_hooks" in data, "viral_hooks key missing from response"
        assert isinstance(data["viral_hooks"], list), "viral_hooks should be a list"
        assert len(data["viral_hooks"]) > 0, "viral_hooks should not be empty"
        
        # Verify structure of first hook
        first_hook = data["viral_hooks"][0]
        assert "hook" in first_hook, "hook field missing"
        assert "niche" in first_hook, "niche field missing"
        
        print(f"Viral Hooks count: {len(data['viral_hooks'])}")
    
    def test_content_vault_returns_totals(self, authenticated_client):
        """Test that Content Vault returns total counts"""
        response = authenticated_client.get(f"{BASE_URL}/api/content/vault")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_hooks" in data, "total_hooks missing"
        assert "total_structures" in data, "total_structures missing"
        assert "total_themes" in data, "total_themes missing"
        assert "total_morals" in data, "total_morals missing"
        
        print(f"Total hooks: {data['total_hooks']}")
        print(f"Total structures: {data['total_structures']}")
        print(f"Total themes: {data['total_themes']}")
        print(f"Total morals: {data['total_morals']}")
    
    def test_content_vault_returns_access_level(self, authenticated_client):
        """Test that Content Vault returns access_level for tier-based access"""
        response = authenticated_client.get(f"{BASE_URL}/api/content/vault")
        assert response.status_code == 200
        
        data = response.json()
        assert "access_level" in data, "access_level missing"
        assert "plan" in data, "plan missing"
        
        access = data["access_level"]
        assert "hooks" in access, "hooks access level missing"
        assert "structures" in access, "structures access level missing"
        assert "themes" in access, "themes access level missing"
        assert "morals" in access, "morals access level missing"
        
        print(f"User plan: {data['plan']}")
        print(f"Access level: {access}")
    
    def test_content_vault_niche_filter(self, authenticated_client):
        """Test Content Vault niche filter"""
        response = authenticated_client.get(f"{BASE_URL}/api/content/vault?niche=luxury")
        assert response.status_code == 200
        
        data = response.json()
        # When filtered by niche, all hooks should be from that niche
        for hook in data["viral_hooks"]:
            assert hook["niche"] == "luxury", f"Expected luxury niche, got {hook['niche']}"
        
        print(f"Filtered hooks count: {len(data['viral_hooks'])}")


class TestStoryGenerationAPI:
    """Test Story Generation endpoint"""
    
    def test_story_generation_endpoint_exists(self, authenticated_client):
        """Test that story generation endpoint exists"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/generate/story",
            json={
                "genre": "Fantasy",
                "ageGroup": "4-6",
                "theme": "Adventure",
                "sceneCount": 8
            }
        )
        # Should return 200 (success) or 400/503 (insufficient credits/service unavailable)
        assert response.status_code in [200, 400, 503], f"Unexpected status: {response.status_code}"
        print(f"Story generation status: {response.status_code}")


class TestPDFDownloadAPI:
    """Test PDF Download endpoints"""
    
    def test_generation_pdf_endpoint_exists(self, authenticated_client):
        """Test that generation PDF endpoint exists"""
        # First get a generation ID
        generations_response = authenticated_client.get(
            f"{BASE_URL}/api/generate/generations?type=STORY"
        )
        
        if generations_response.status_code == 200:
            data = generations_response.json()
            if data.get("content") and len(data["content"]) > 0:
                generation_id = data["content"][0]["id"]
                
                # Try to download PDF
                pdf_response = authenticated_client.get(
                    f"{BASE_URL}/api/generate/generations/{generation_id}/pdf"
                )
                assert pdf_response.status_code in [200, 404], f"Unexpected status: {pdf_response.status_code}"
                
                if pdf_response.status_code == 200:
                    assert pdf_response.headers.get("content-type") == "application/pdf"
                    print("PDF download successful")
                else:
                    print("PDF not found for this generation")
            else:
                print("No story generations found to test PDF download")
        else:
            print(f"Could not fetch generations: {generations_response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
