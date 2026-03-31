"""
Gallery API Tests - Netflix-style Discovery Engine
Tests for featured content, category rails, explore feed, and seeded demo content.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGalleryFeatured:
    """Tests for GET /api/gallery/featured endpoint"""
    
    def test_featured_returns_items(self):
        """Featured endpoint should return 3+ featured items"""
        response = requests.get(f"{BASE_URL}/api/gallery/featured")
        assert response.status_code == 200
        data = response.json()
        assert "featured" in data
        assert len(data["featured"]) >= 3, f"Expected 3+ featured items, got {len(data['featured'])}"
    
    def test_featured_item_structure(self):
        """Featured items should have required fields"""
        response = requests.get(f"{BASE_URL}/api/gallery/featured")
        data = response.json()
        for item in data["featured"]:
            assert "item_id" in item
            assert "title" in item
            assert "description" in item
            assert "thumbnail_url" in item
            assert "views_count" in item
            assert "likes_count" in item
            assert "remixes_count" in item
            assert "category" in item
            assert "duration_seconds" in item


class TestGalleryRails:
    """Tests for GET /api/gallery/rails endpoint"""
    
    def test_rails_returns_9_categories(self):
        """Rails endpoint should return 9 category rails"""
        response = requests.get(f"{BASE_URL}/api/gallery/rails")
        assert response.status_code == 200
        data = response.json()
        assert "rails" in data
        assert len(data["rails"]) == 9, f"Expected 9 rails, got {len(data['rails'])}"
    
    def test_rails_expected_categories(self):
        """Rails should include all expected categories"""
        response = requests.get(f"{BASE_URL}/api/gallery/rails")
        data = response.json()
        rail_ids = [r["id"] for r in data["rails"]]
        expected_ids = ["trending", "most_remixed", "kids", "reels", "emotional", "cinematic", "business", "luxury", "educational"]
        for expected_id in expected_ids:
            assert expected_id in rail_ids, f"Missing rail: {expected_id}"
    
    def test_rails_have_items(self):
        """Each rail should have items"""
        response = requests.get(f"{BASE_URL}/api/gallery/rails")
        data = response.json()
        for rail in data["rails"]:
            assert "items" in rail
            assert len(rail["items"]) > 0, f"Rail {rail['id']} has no items"
            assert "name" in rail
            assert "emoji" in rail


class TestGalleryExplore:
    """Tests for GET /api/gallery/explore endpoint"""
    
    def test_explore_returns_items(self):
        """Explore endpoint should return paginated items"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0, "Explore should never be empty (seeded content)"
        assert "total" in data
        assert "cursor" in data
        assert "has_more" in data
    
    def test_explore_category_filter(self):
        """Explore should filter by category"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore?category=Kids%20Stories")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0, "Kids Stories category should have items"
        for item in data["items"]:
            assert item["category"] == "Kids Stories", f"Item category mismatch: {item['category']}"
    
    def test_explore_sort_most_remixed(self):
        """Explore should sort by most_remixed"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore?sort=most_remixed&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        # Verify items are sorted by remixes_count descending
        remixes = [item.get("remixes_count", 0) for item in data["items"]]
        assert remixes == sorted(remixes, reverse=True), "Items not sorted by remixes_count"
    
    def test_explore_sort_trending(self):
        """Explore should sort by trending (ranking_score)"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore?sort=trending&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        # Verify items are sorted by ranking_score descending
        scores = [item.get("ranking_score", 0) for item in data["items"]]
        assert scores == sorted(scores, reverse=True), "Items not sorted by ranking_score"
    
    def test_explore_pagination(self):
        """Explore should support pagination"""
        response1 = requests.get(f"{BASE_URL}/api/gallery/explore?limit=5&cursor=0")
        response2 = requests.get(f"{BASE_URL}/api/gallery/explore?limit=5&cursor=5")
        assert response1.status_code == 200
        assert response2.status_code == 200
        data1 = response1.json()
        data2 = response2.json()
        # Items should be different
        ids1 = [item["item_id"] for item in data1["items"]]
        ids2 = [item["item_id"] for item in data2["items"]]
        assert ids1 != ids2 or len(ids1) == 0 or len(ids2) == 0, "Pagination not working"


class TestGalleryCategories:
    """Tests for GET /api/gallery/categories endpoint"""
    
    def test_categories_returns_list(self):
        """Categories endpoint should return category list with counts"""
        response = requests.get(f"{BASE_URL}/api/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0
    
    def test_categories_have_all_option(self):
        """Categories should include 'All' option"""
        response = requests.get(f"{BASE_URL}/api/gallery/categories")
        data = response.json()
        category_ids = [c["id"] for c in data["categories"]]
        assert "all" in category_ids, "Missing 'All' category"
    
    def test_categories_have_counts(self):
        """Each category should have a count"""
        response = requests.get(f"{BASE_URL}/api/gallery/categories")
        data = response.json()
        for cat in data["categories"]:
            assert "id" in cat
            assert "name" in cat
            assert "count" in cat
            assert cat["count"] >= 0


class TestGalleryNeverEmpty:
    """Tests to ensure gallery never shows empty state"""
    
    def test_featured_never_empty(self):
        """Featured should never be empty"""
        response = requests.get(f"{BASE_URL}/api/gallery/featured")
        data = response.json()
        assert len(data["featured"]) > 0, "Featured should never be empty"
    
    def test_explore_never_empty(self):
        """Explore should never be empty"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore")
        data = response.json()
        assert len(data["items"]) > 0, "Explore should never be empty"
    
    def test_rails_never_empty(self):
        """Rails should never be empty"""
        response = requests.get(f"{BASE_URL}/api/gallery/rails")
        data = response.json()
        assert len(data["rails"]) > 0, "Rails should never be empty"
        for rail in data["rails"]:
            assert len(rail["items"]) > 0, f"Rail {rail['id']} should never be empty"


class TestGalleryItemFields:
    """Tests for item field completeness"""
    
    def test_explore_items_have_remix_data(self):
        """Explore items should have data needed for remix"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore?limit=5")
        data = response.json()
        for item in data["items"]:
            assert "item_id" in item, "Missing item_id for remix"
            assert "title" in item, "Missing title for remix"
            # story_text or description needed for remix
            has_story = "story_text" in item or "description" in item
            assert has_story, "Missing story_text/description for remix"
    
    def test_items_have_thumbnail(self):
        """Items should have thumbnail_url"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore?limit=10")
        data = response.json()
        for item in data["items"]:
            assert "thumbnail_url" in item
            # thumbnail_url can be empty for some items (SafeImage handles fallback)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
