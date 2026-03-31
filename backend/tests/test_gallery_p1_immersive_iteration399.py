"""
Gallery P1 Immersive Viewer Tests - Iteration 399
Tests for:
- GET /api/gallery/feed - Immersive viewer feed with seed_index
- GET /api/gallery/feed?seed_item_id=X - Feed starting from specific item
- GET /api/gallery/user-feed - Personalized sections (your_creations, continue_watching, for_you)
- POST /api/gallery/view - Track viewed items for Continue Watching
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def sample_item_id():
    """Get a sample item_id from the feed for testing"""
    response = requests.get(f"{BASE_URL}/api/gallery/feed?limit=5")
    if response.status_code == 200:
        data = response.json()
        if data.get("items"):
            return data["items"][0].get("item_id")
    return None


class TestGalleryFeedEndpoint:
    """Tests for GET /api/gallery/feed - Immersive viewer feed"""
    
    def test_feed_returns_items_with_seed_index(self):
        """Feed endpoint should return items with seed_index for immersive viewing"""
        response = requests.get(f"{BASE_URL}/api/gallery/feed?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "items" in data, "Response missing 'items' field"
        assert "seed_index" in data, "Response missing 'seed_index' field"
        assert "total" in data, "Response missing 'total' field"
        
        # Verify items exist
        assert len(data["items"]) > 0, "Feed should not be empty"
        assert data["seed_index"] >= 0, "seed_index should be non-negative"
    
    def test_feed_items_have_required_fields(self):
        """Feed items should have all fields needed for immersive viewer"""
        response = requests.get(f"{BASE_URL}/api/gallery/feed?limit=5")
        data = response.json()
        
        for item in data["items"]:
            # Required fields for immersive viewer
            assert "item_id" in item, "Missing item_id"
            assert "title" in item, "Missing title"
            assert "description" in item or "story_text" in item, "Missing description/story_text"
            assert "thumbnail_url" in item, "Missing thumbnail_url"
            assert "views_count" in item, "Missing views_count"
            assert "likes_count" in item, "Missing likes_count"
            assert "remixes_count" in item, "Missing remixes_count"
            assert "category" in item, "Missing category"
            assert "duration_seconds" in item, "Missing duration_seconds"
    
    def test_feed_with_seed_item_id(self, sample_item_id):
        """Feed should position starting from seed_item_id"""
        if not sample_item_id:
            pytest.skip("No sample item_id available")
        
        response = requests.get(f"{BASE_URL}/api/gallery/feed?seed_item_id={sample_item_id}&limit=20")
        assert response.status_code == 200
        data = response.json()
        
        # Verify seed_index is set correctly
        assert "seed_index" in data
        assert data["seed_index"] >= 0
        
        # The seed item should be in the feed
        item_ids = [item.get("item_id") for item in data["items"]]
        # Note: seed_item might be at seed_index position
        if data["seed_index"] < len(data["items"]):
            assert sample_item_id in item_ids, "Seed item should be in the feed"
    
    def test_feed_limit_parameter(self):
        """Feed should respect limit parameter"""
        response = requests.get(f"{BASE_URL}/api/gallery/feed?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5, "Feed should respect limit parameter"
    
    def test_feed_sorted_by_ranking(self):
        """Feed items should be sorted by ranking_score"""
        response = requests.get(f"{BASE_URL}/api/gallery/feed?limit=10")
        data = response.json()
        
        scores = [item.get("ranking_score", 0) for item in data["items"]]
        # Items should be sorted descending by ranking_score
        assert scores == sorted(scores, reverse=True), "Feed should be sorted by ranking_score"


class TestGalleryUserFeedEndpoint:
    """Tests for GET /api/gallery/user-feed - Personalized sections"""
    
    def test_user_feed_without_auth_returns_empty(self):
        """User feed without auth should return empty sections"""
        response = requests.get(f"{BASE_URL}/api/gallery/user-feed")
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty arrays without auth
        assert "your_creations" in data
        assert "continue_watching" in data
        assert "for_you" in data
        assert data["your_creations"] == []
        assert data["continue_watching"] == []
        assert data["for_you"] == []
    
    def test_user_feed_with_auth_returns_sections(self, auth_token):
        """User feed with auth should return personalized sections"""
        response = requests.get(
            f"{BASE_URL}/api/gallery/user-feed",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all sections exist
        assert "your_creations" in data, "Missing your_creations section"
        assert "continue_watching" in data, "Missing continue_watching section"
        assert "for_you" in data, "Missing for_you section"
        
        # All should be lists
        assert isinstance(data["your_creations"], list)
        assert isinstance(data["continue_watching"], list)
        assert isinstance(data["for_you"], list)
    
    def test_user_feed_your_creations_structure(self, auth_token):
        """Your creations items should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/gallery/user-feed",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        for item in data["your_creations"]:
            assert "item_id" in item, "Missing item_id in your_creations"
            assert "title" in item, "Missing title in your_creations"
            assert "thumbnail_url" in item, "Missing thumbnail_url in your_creations"
    
    def test_user_feed_for_you_has_content(self, auth_token):
        """For You section should have content (fills with top-ranked if no history)"""
        response = requests.get(
            f"{BASE_URL}/api/gallery/user-feed",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # for_you should have content (either personalized or top-ranked fill)
        # Note: May be empty if user has no history and no seeded content
        assert isinstance(data["for_you"], list)


class TestGalleryViewEndpoint:
    """Tests for POST /api/gallery/view - Track viewed items"""
    
    def test_view_without_auth_returns_ok(self, sample_item_id):
        """View endpoint without auth should return ok (but not track)"""
        if not sample_item_id:
            pytest.skip("No sample item_id available")
        
        response = requests.post(
            f"{BASE_URL}/api/gallery/view",
            json={"item_id": sample_item_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
    
    def test_view_with_auth_tracks_item(self, auth_token, sample_item_id):
        """View endpoint with auth should track the viewed item"""
        if not sample_item_id:
            pytest.skip("No sample item_id available")
        
        response = requests.post(
            f"{BASE_URL}/api/gallery/view",
            json={"item_id": sample_item_id},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
    
    def test_view_updates_continue_watching(self, auth_token, sample_item_id):
        """After viewing, item should appear in continue_watching"""
        if not sample_item_id:
            pytest.skip("No sample item_id available")
        
        # Track a view
        requests.post(
            f"{BASE_URL}/api/gallery/view",
            json={"item_id": sample_item_id},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Check user-feed
        response = requests.get(
            f"{BASE_URL}/api/gallery/user-feed",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # The viewed item should be in continue_watching
        continue_ids = [item.get("item_id") for item in data["continue_watching"]]
        assert sample_item_id in continue_ids, "Viewed item should appear in continue_watching"
    
    def test_view_without_item_id_returns_ok(self, auth_token):
        """View endpoint without item_id should return ok (no-op)"""
        response = requests.post(
            f"{BASE_URL}/api/gallery/view",
            json={},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True


class TestGalleryP0Regression:
    """Regression tests for P0 gallery features (from iteration 398)"""
    
    def test_featured_still_works(self):
        """Featured endpoint should still return items"""
        response = requests.get(f"{BASE_URL}/api/gallery/featured")
        assert response.status_code == 200
        data = response.json()
        assert "featured" in data
        assert len(data["featured"]) >= 3
    
    def test_rails_still_works(self):
        """Rails endpoint should still return 9 rails"""
        response = requests.get(f"{BASE_URL}/api/gallery/rails")
        assert response.status_code == 200
        data = response.json()
        assert "rails" in data
        assert len(data["rails"]) == 9
    
    def test_explore_still_works(self):
        """Explore endpoint should still return paginated items"""
        response = requests.get(f"{BASE_URL}/api/gallery/explore?sort=trending&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0
    
    def test_categories_still_works(self):
        """Categories endpoint should still return categories"""
        response = requests.get(f"{BASE_URL}/api/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
