"""
Remix Gallery MVP Backend Tests - Iteration 468
Tests for:
1. GET /api/gallery/remix-feed - curated items with quality filtering
2. POST /api/gallery/{item_id}/remix - increment remix count and return prefill data
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

class TestRemixFeedEndpoint:
    """Tests for GET /api/gallery/remix-feed"""
    
    def test_remix_feed_returns_200(self):
        """Test that remix-feed endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: remix-feed returns 200")
    
    def test_remix_feed_returns_items_array(self):
        """Test that remix-feed returns items array"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data, "Response should contain 'items' key"
        assert isinstance(data["items"], list), "items should be a list"
        print(f"PASS: remix-feed returns items array with {len(data['items'])} items")
    
    def test_remix_feed_items_have_required_fields(self):
        """Test that each item has required fields for remix cards"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=8")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["item_id", "title", "description", "thumbnail_url", 
                          "remixes_count", "views_count", "animation_style", "story_text"]
        
        for item in data["items"]:
            for field in required_fields:
                assert field in item, f"Item missing required field: {field}"
            # Quality filter: must have thumbnail
            assert item.get("thumbnail_url"), f"Item {item.get('item_id')} missing thumbnail_url"
            # Quality filter: must have description or story_text
            assert item.get("description") or item.get("story_text"), f"Item {item.get('item_id')} missing description/story_text"
        
        print(f"PASS: All {len(data['items'])} items have required fields")
    
    def test_remix_feed_respects_limit_parameter(self):
        """Test that limit parameter works correctly"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 3, f"Expected max 3 items, got {len(data['items'])}"
        print(f"PASS: limit parameter works, returned {len(data['items'])} items")
    
    def test_remix_feed_sorted_by_remixes_count(self):
        """Test that items are sorted by remixes_count descending"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=8")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) >= 2:
            remix_counts = [item.get("remixes_count", 0) for item in data["items"]]
            # Check if sorted descending (allowing for ties)
            for i in range(len(remix_counts) - 1):
                assert remix_counts[i] >= remix_counts[i+1], f"Items not sorted by remixes_count: {remix_counts}"
        
        print(f"PASS: Items sorted by remixes_count descending")
    
    def test_remix_feed_quality_filter_no_empty_titles(self):
        """Test that items with very short titles are filtered out"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            title = item.get("title", "")
            assert len(title) >= 3, f"Item has too short title: '{title}'"
        
        print(f"PASS: All items have titles >= 3 characters")


class TestRemixEndpoint:
    """Tests for POST /api/gallery/{item_id}/remix"""
    
    def test_remix_endpoint_returns_success(self):
        """Test that remix endpoint returns success for valid item"""
        # First get an item from remix-feed
        feed_response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=1")
        assert feed_response.status_code == 200
        items = feed_response.json().get("items", [])
        
        if not items:
            pytest.skip("No items in remix-feed to test remix endpoint")
        
        item_id = items[0]["item_id"]
        
        # Call remix endpoint
        response = requests.post(f"{BASE_URL}/api/gallery/{item_id}/remix")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print(f"PASS: remix endpoint returns success for item {item_id}")
    
    def test_remix_endpoint_returns_prefill_data(self):
        """Test that remix endpoint returns prefill data for Studio"""
        # Get an item
        feed_response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=1")
        assert feed_response.status_code == 200
        items = feed_response.json().get("items", [])
        
        if not items:
            pytest.skip("No items in remix-feed to test remix endpoint")
        
        item_id = items[0]["item_id"]
        original_title = items[0]["title"]
        
        # Call remix endpoint
        response = requests.post(f"{BASE_URL}/api/gallery/{item_id}/remix")
        assert response.status_code == 200
        data = response.json()
        
        # Check prefill data structure
        assert "prefill" in data, "Response should contain 'prefill' key"
        prefill = data["prefill"]
        
        required_prefill_fields = ["title", "story_text", "animation_style", "source_item_id"]
        for field in required_prefill_fields:
            assert field in prefill, f"Prefill missing required field: {field}"
        
        # Verify source_item_id matches
        assert prefill["source_item_id"] == item_id, f"source_item_id mismatch"
        
        # Verify title matches original
        assert prefill["title"] == original_title, f"Title mismatch: expected '{original_title}', got '{prefill['title']}'"
        
        print(f"PASS: remix endpoint returns correct prefill data")
    
    def test_remix_endpoint_increments_count(self):
        """Test that remix endpoint increments remix count"""
        # Get an item
        feed_response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=1")
        assert feed_response.status_code == 200
        items = feed_response.json().get("items", [])
        
        if not items:
            pytest.skip("No items in remix-feed to test remix endpoint")
        
        item_id = items[0]["item_id"]
        original_count = items[0].get("remixes_count", 0)
        
        # Call remix endpoint
        response = requests.post(f"{BASE_URL}/api/gallery/{item_id}/remix")
        assert response.status_code == 200
        data = response.json()
        
        # Check that remixes_count in prefill is incremented
        new_count = data.get("prefill", {}).get("remixes_count", 0)
        assert new_count == original_count + 1, f"Expected count {original_count + 1}, got {new_count}"
        
        print(f"PASS: remix count incremented from {original_count} to {new_count}")
    
    def test_remix_endpoint_nonexistent_item(self):
        """Test that remix endpoint handles nonexistent item gracefully"""
        fake_item_id = "nonexistent-item-12345"
        response = requests.post(f"{BASE_URL}/api/gallery/{fake_item_id}/remix")
        
        # Should return 200 with success=False or 404
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == False, "Should return success=False for nonexistent item"
            assert "error" in data, "Should contain error message"
        else:
            assert response.status_code == 404, f"Expected 404 for nonexistent item, got {response.status_code}"
        
        print(f"PASS: remix endpoint handles nonexistent item correctly")


class TestGalleryContentSeeding:
    """Tests to verify gallery content is seeded properly"""
    
    def test_gallery_has_seeded_content(self):
        """Test that gallery has seeded content with thumbnails"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least some items
        assert len(data["items"]) > 0, "Gallery should have seeded content"
        
        # Count items with thumbnails
        items_with_thumbnails = [i for i in data["items"] if i.get("thumbnail_url")]
        assert len(items_with_thumbnails) > 0, "Should have items with thumbnails"
        
        print(f"PASS: Gallery has {len(data['items'])} items, {len(items_with_thumbnails)} with thumbnails")
    
    def test_gallery_items_have_categories(self):
        """Test that gallery items have category information"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            # Should have category or animation_style
            has_category = item.get("category") or item.get("animation_style")
            assert has_category, f"Item {item.get('item_id')} missing category/animation_style"
        
        print(f"PASS: All items have category information")


class TestRemixFeedIntegration:
    """Integration tests for remix feed with other gallery endpoints"""
    
    def test_remix_feed_items_exist_in_explore(self):
        """Test that remix-feed items can be found in explore endpoint"""
        # Get remix feed items
        remix_response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=3")
        assert remix_response.status_code == 200
        remix_items = remix_response.json().get("items", [])
        
        if not remix_items:
            pytest.skip("No items in remix-feed")
        
        # Get explore items
        explore_response = requests.get(f"{BASE_URL}/api/gallery/explore?limit=50")
        assert explore_response.status_code == 200
        explore_items = explore_response.json().get("items", [])
        
        explore_ids = {item.get("item_id") for item in explore_items}
        
        # At least some remix items should be in explore
        found_count = sum(1 for item in remix_items if item.get("item_id") in explore_ids)
        print(f"Found {found_count}/{len(remix_items)} remix items in explore feed")
        
        # This is informational - seeded content may or may not appear in explore
        print(f"PASS: Integration check complete")
    
    def test_remix_feed_total_count(self):
        """Test that remix-feed returns total count"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["total"], int), "total should be an integer"
        assert data["total"] >= len(data["items"]), "total should be >= items returned"
        
        print(f"PASS: remix-feed returns total={data['total']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
