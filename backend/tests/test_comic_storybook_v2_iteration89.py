"""
Comic Story Book Builder v2 API Tests - Iteration 89
Tests the new 5-step wizard feature with:
- 8 Story Genres
- Page count options (10/20/30 with pricing)
- Add-ons
- Copyright blocked keyword validation
- Generate and preview endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}

class TestComicStorybookV2Genres:
    """Test /api/comic-storybook-v2/genres endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Login and get auth token"""
        self.client = api_client
        response = self.client.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get('token')
        self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_genres_returns_8_genres(self, api_client):
        """Verify /api/comic-storybook-v2/genres returns exactly 8 genres"""
        response = self.client.get(f"{BASE_URL}/api/comic-storybook-v2/genres")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify genres key exists
        assert "genres" in data, "Response should contain 'genres' key"
        genres = data["genres"]
        
        # Verify exactly 8 genres
        assert len(genres) == 8, f"Expected 8 genres, got {len(genres)}"
        
        # Verify expected genres exist
        expected_genre_ids = [
            'kids_adventure', 'superhero', 'fantasy', 'comedy',
            'romance', 'scifi', 'mystery', 'horror_lite'
        ]
        for genre_id in expected_genre_ids:
            assert genre_id in genres, f"Missing genre: {genre_id}"
        
        # Verify each genre has a name
        for genre_id, genre_data in genres.items():
            assert "name" in genre_data, f"Genre {genre_id} missing 'name' field"
        
        print(f"SUCCESS: Got {len(genres)} genres - {list(genres.keys())}")


class TestComicStorybookV2Pricing:
    """Test /api/comic-storybook-v2/pricing endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Login and get auth token"""
        self.client = api_client
        response = self.client.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get('token')
        self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_pricing_structure(self, api_client):
        """Verify /api/comic-storybook-v2/pricing returns correct pricing"""
        response = self.client.get(f"{BASE_URL}/api/comic-storybook-v2/pricing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "pricing" in data, "Response should contain 'pricing' key"
        pricing = data["pricing"]
        
        # Verify page pricing
        assert "pages" in pricing, "Pricing should contain 'pages'"
        pages = pricing["pages"]
        
        # Expected: 10 pages = 25 cr, 20 pages = 45 cr, 30 pages = 60 cr
        assert pages.get("10") == 25 or pages.get(10) == 25, f"10 pages should cost 25 credits, got {pages.get('10') or pages.get(10)}"
        assert pages.get("20") == 45 or pages.get(20) == 45, f"20 pages should cost 45 credits, got {pages.get('20') or pages.get(20)}"
        assert pages.get("30") == 60 or pages.get(30) == 60, f"30 pages should cost 60 credits, got {pages.get('30') or pages.get(30)}"
        
        # Verify add-ons pricing
        assert "add_ons" in pricing, "Pricing should contain 'add_ons'"
        add_ons = pricing["add_ons"]
        
        expected_add_ons = ['personalized_cover', 'dedication_page', 'activity_pages', 'hd_print', 'commercial_license']
        for addon in expected_add_ons:
            assert addon in add_ons, f"Missing add-on: {addon}"
        
        print(f"SUCCESS: Pricing structure verified - Pages: {pages}, Add-ons: {list(add_ons.keys())}")


class TestComicStorybookV2BlockedKeywords:
    """Test copyright keyword blocking in /api/comic-storybook-v2/generate"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Login and get auth token"""
        self.client = api_client
        response = self.client.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get('token')
        self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_blocked_keyword_batman(self, api_client):
        """Verify 'batman' is blocked in story idea"""
        response = self.client.post(f"{BASE_URL}/api/comic-storybook-v2/generate", json={
            "genre": "superhero",
            "storyIdea": "A story about batman saving the city from villains",
            "title": "Hero Story",
            "author": "Test Author",
            "pageCount": 10
        })
        
        # Should return 400 for blocked content
        assert response.status_code == 400, f"Expected 400 for blocked keyword, got {response.status_code}"
        
        error_detail = response.json().get('detail', '')
        assert 'batman' in error_detail.lower() or 'copyright' in error_detail.lower() or 'brand' in error_detail.lower(), \
            f"Error should mention blocked keyword. Got: {error_detail}"
        
        print(f"SUCCESS: 'batman' correctly blocked with message: {error_detail}")
    
    def test_blocked_keyword_spiderman(self, api_client):
        """Verify 'spiderman' is blocked in story idea"""
        response = self.client.post(f"{BASE_URL}/api/comic-storybook-v2/generate", json={
            "genre": "superhero",
            "storyIdea": "Spiderman swings through the city fighting crime",
            "title": "Web Hero",
            "author": "Test Author",
            "pageCount": 10
        })
        
        assert response.status_code == 400, f"Expected 400 for blocked keyword, got {response.status_code}"
        print(f"SUCCESS: 'spiderman' correctly blocked")
    
    def test_blocked_keyword_in_title(self, api_client):
        """Verify blocked keywords in title are also rejected"""
        response = self.client.post(f"{BASE_URL}/api/comic-storybook-v2/generate", json={
            "genre": "fantasy",
            "storyIdea": "A magical adventure in an enchanted forest",
            "title": "Harry Potter Adventures",
            "author": "Test Author",
            "pageCount": 10
        })
        
        assert response.status_code == 400, f"Expected 400 for blocked title, got {response.status_code}"
        print(f"SUCCESS: 'harry potter' in title correctly blocked")
    
    def test_clean_content_accepted(self, api_client):
        """Verify clean content is accepted (no blocked keywords)"""
        response = self.client.post(f"{BASE_URL}/api/comic-storybook-v2/generate", json={
            "genre": "kids_adventure",
            "storyIdea": "A brave rabbit named Hoppy discovers a magical garden where flowers can sing and dance",
            "title": "Hoppy's Magical Garden",
            "author": "Test Author",
            "pageCount": 10
        })
        
        # Should return 200 (success) or 400 with insufficient credits (not blocked content error)
        if response.status_code == 400:
            error = response.json().get('detail', '')
            assert 'copyright' not in error.lower() and 'brand' not in error.lower(), \
                f"Clean content should not be blocked. Got: {error}"
            print(f"INFO: Request rejected due to: {error} (not a copyright block)")
        else:
            assert response.status_code == 200, f"Expected 200 for clean content, got {response.status_code}"
            print(f"SUCCESS: Clean content accepted, job created")


class TestComicStorybookV2Preview:
    """Test /api/comic-storybook-v2/preview endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Login and get auth token"""
        self.client = api_client
        response = self.client.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get('token')
        self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_preview_endpoint_exists(self, api_client):
        """Verify preview endpoint accepts valid request"""
        response = self.client.post(f"{BASE_URL}/api/comic-storybook-v2/preview", json={
            "genre": "fantasy",
            "storyIdea": "A young wizard discovers a talking book that can transport them to magical worlds",
            "title": "The Magical Book",
            "pageCount": 20
        })
        
        # Should return 200 or 422 (validation error) but endpoint should exist
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "previewPages" in data or "success" in data
            print(f"SUCCESS: Preview generated")
        else:
            print(f"INFO: Preview endpoint returned {response.status_code}")


class TestComicStorybookV2GenreValidation:
    """Test genre validation in generate endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Login and get auth token"""
        self.client = api_client
        response = self.client.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get('token')
        self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_all_8_genres_accepted(self, api_client):
        """Verify all 8 genres are valid options"""
        genres = ['kids_adventure', 'superhero', 'fantasy', 'comedy', 'romance', 'scifi', 'mystery', 'horror_lite']
        
        for genre in genres:
            response = self.client.post(f"{BASE_URL}/api/comic-storybook-v2/generate", json={
                "genre": genre,
                "storyIdea": f"A wonderful {genre} story about courage and friendship",
                "title": f"Test {genre.title()} Story",
                "pageCount": 10
            })
            
            # Should not get "invalid genre" error
            if response.status_code == 400:
                error = response.json().get('detail', '')
                assert 'genre' not in error.lower() or 'invalid' not in error.lower(), \
                    f"Genre '{genre}' should be valid. Got: {error}"
        
        print(f"SUCCESS: All 8 genres are valid: {genres}")


class TestComicStorybookV2PageCountValidation:
    """Test page count validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Login and get auth token"""
        self.client = api_client
        response = self.client.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get('token')
        self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_valid_page_counts(self, api_client):
        """Verify valid page counts (10, 20, 30) are accepted"""
        valid_counts = [10, 20, 30]
        
        for count in valid_counts:
            response = self.client.post(f"{BASE_URL}/api/comic-storybook-v2/generate", json={
                "genre": "kids_adventure",
                "storyIdea": "A fun adventure story about a brave little mouse",
                "title": "Mouse Adventure",
                "pageCount": count
            })
            
            # Should not fail due to invalid page count
            if response.status_code == 400:
                error = response.json().get('detail', '')
                assert 'page' not in error.lower() or 'invalid' not in error.lower(), \
                    f"Page count {count} should be valid. Got: {error}"
        
        print(f"SUCCESS: Valid page counts accepted: {valid_counts}")


# Fixtures
@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session
