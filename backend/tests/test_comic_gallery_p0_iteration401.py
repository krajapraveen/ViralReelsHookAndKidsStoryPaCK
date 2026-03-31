"""
Test Suite for P0-A Gallery ImmersiveViewer Fallback and P0-B Comic Storybook Builder Features
Iteration 401

Tests:
- P0-A: Gallery ImmersiveViewer fallback for items without video
- P0-B: Comic Storybook Builder - Quick Presets, Story Helper Chips, Improve Idea, Localization, Deliverables
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=60
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestGalleryAPIs:
    """Test Gallery APIs for P0-A features"""
    
    def test_gallery_featured(self):
        """Test /api/gallery/featured returns featured items"""
        response = requests.get(f"{BASE_URL}/api/gallery/featured", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "featured" in data
        print(f"Featured items count: {len(data.get('featured', []))}")
    
    def test_gallery_rails(self):
        """Test /api/gallery/rails returns content rails"""
        response = requests.get(f"{BASE_URL}/api/gallery/rails", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "rails" in data
        print(f"Rails count: {len(data.get('rails', []))}")
    
    def test_gallery_explore(self):
        """Test /api/gallery/explore returns explore items"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore?sort=trending&limit=24", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        items = data.get("items", [])
        print(f"Explore items count: {len(items)}")
        
        # Check that items have expected fields for fallback preview
        if items:
            item = items[0]
            assert "title" in item or "item_id" in item
            # Items may or may not have video URLs
            has_video = bool(item.get("output_url") or item.get("full_video_url"))
            print(f"First item has video: {has_video}")
    
    def test_gallery_feed(self, auth_headers):
        """Test /api/gallery/feed returns personalized feed"""
        response = requests.get(
            f"{BASE_URL}/api/gallery/feed?seed_item_id=&limit=20",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"Feed items count: {len(data.get('items', []))}")


class TestComicStorybookImproveIdea:
    """Test P0-B: Improve Idea endpoint"""
    
    def test_improve_idea_basic(self, auth_headers):
        """Test /api/comic-storybook-v2/improve-idea with basic story"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/improve-idea",
            headers=auth_headers,
            json={
                "storyIdea": "A brave bunny goes on adventure",
                "genre": "kids_adventure",
                "ageGroup": "4-7",
                "language": "English",
                "readingLevel": "beginner"
            },
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "improved" in data
        assert len(data["improved"]) > len("A brave bunny goes on adventure")
        print(f"Improved story length: {len(data['improved'])} chars")
        if data.get("suggestedTitle"):
            print(f"Suggested title: {data['suggestedTitle']}")
    
    def test_improve_idea_with_hindi(self, auth_headers):
        """Test improve-idea with Hindi language"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/improve-idea",
            headers=auth_headers,
            json={
                "storyIdea": "A magical elephant helps village children",
                "genre": "kids_adventure",
                "ageGroup": "6-10",
                "language": "Hindi",
                "readingLevel": "intermediate"
            },
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"Hindi story improvement success: {data.get('success')}")
    
    def test_improve_idea_short_input_rejected(self, auth_headers):
        """Test that very short input is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/improve-idea",
            headers=auth_headers,
            json={
                "storyIdea": "hi",
                "genre": "kids_adventure"
            },
            timeout=30
        )
        assert response.status_code == 400
        print("Short input correctly rejected")


class TestComicStorybookGenerate:
    """Test P0-B: Generate endpoint with new fields"""
    
    def test_generate_with_language_fields(self, auth_headers):
        """Test /api/comic-storybook-v2/generate accepts language, ageGroup, readingLevel, bilingual"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/generate",
            headers=auth_headers,
            json={
                "genre": "kids_adventure",
                "storyIdea": "A brave little bunny named Benny discovers a magical garden where flowers can talk",
                "title": "Benny and the Talking Flowers",
                "author": "Test Author",
                "pageCount": 10,
                "language": "Hindi",
                "ageGroup": "4-7",
                "readingLevel": "beginner",
                "bilingual": "English"
            },
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "jobId" in data
        assert data.get("status") == "QUEUED"
        print(f"Job created: {data.get('jobId')}")
        print(f"Enforced pages: {data.get('enforcedPages')}")
        print(f"Queue: {data.get('queueName')}")
    
    def test_generate_with_all_languages(self, auth_headers):
        """Test generate accepts various languages"""
        languages = ["English", "Hindi", "Telugu", "Spanish", "French"]
        for lang in languages:
            response = requests.post(
                f"{BASE_URL}/api/comic-storybook-v2/generate",
                headers=auth_headers,
                json={
                    "genre": "fantasy",
                    "storyIdea": f"A magical story in {lang}",
                    "title": f"Test Story {lang}",
                    "pageCount": 10,
                    "language": lang,
                    "ageGroup": "6-10",
                    "readingLevel": "intermediate"
                },
                timeout=30
            )
            assert response.status_code == 200
            print(f"Language {lang}: PASS")
    
    def test_generate_with_all_age_groups(self, auth_headers):
        """Test generate accepts all age groups"""
        age_groups = ["3-6", "4-7", "6-10", "8-12", "12+"]
        for age in age_groups:
            response = requests.post(
                f"{BASE_URL}/api/comic-storybook-v2/generate",
                headers=auth_headers,
                json={
                    "genre": "comedy",
                    "storyIdea": f"A funny story for {age} year olds",
                    "title": f"Test Story Age {age}",
                    "pageCount": 10,
                    "ageGroup": age,
                    "readingLevel": "intermediate"
                },
                timeout=30
            )
            assert response.status_code == 200
            print(f"Age group {age}: PASS")
    
    def test_generate_with_all_reading_levels(self, auth_headers):
        """Test generate accepts all reading levels"""
        levels = ["beginner", "intermediate", "advanced"]
        for level in levels:
            response = requests.post(
                f"{BASE_URL}/api/comic-storybook-v2/generate",
                headers=auth_headers,
                json={
                    "genre": "mystery",
                    "storyIdea": f"A mystery story at {level} level",
                    "title": f"Test Story Level {level}",
                    "pageCount": 10,
                    "readingLevel": level
                },
                timeout=30
            )
            assert response.status_code == 200
            print(f"Reading level {level}: PASS")


class TestComicStorybookGenres:
    """Test Comic Storybook genres endpoint"""
    
    def test_get_genres(self, auth_headers):
        """Test /api/comic-storybook-v2/genres returns all genres"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook-v2/genres",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "genres" in data
        genres = data["genres"]
        expected_genres = ["kids_adventure", "superhero", "fantasy", "comedy", "romance", "scifi", "mystery", "horror_lite"]
        for genre in expected_genres:
            assert genre in genres, f"Missing genre: {genre}"
        print(f"All {len(expected_genres)} genres present")


class TestComicStorybookPricing:
    """Test Comic Storybook pricing endpoint"""
    
    def test_get_pricing(self, auth_headers):
        """Test /api/comic-storybook-v2/pricing returns pricing info"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook-v2/pricing",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        pricing = data["pricing"]
        assert "pages" in pricing
        assert "add_ons" in pricing
        # Check page pricing
        assert 10 in pricing["pages"]
        assert 20 in pricing["pages"]
        assert 30 in pricing["pages"]
        print(f"Page pricing: {pricing['pages']}")
        print(f"Add-ons: {list(pricing['add_ons'].keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
