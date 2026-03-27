"""
Test Media Display Fix - Iteration 349
Tests for SafeImage component integration and media endpoints

Features tested:
1. Gallery page /api/pipeline/gallery returns videos with thumbnail_url
2. Gallery categories /api/pipeline/gallery/categories shows actual counts (not 0)
3. Explore page /api/engagement/explore returns stories with thumbnail_url
4. Landing page /api/public/trending-weekly returns items with thumbnail_url
5. Gallery leaderboard /api/pipeline/gallery/leaderboard returns items with thumbnail_url
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestGalleryEndpoints:
    """Test Gallery API endpoints for media display"""
    
    def test_gallery_returns_videos_with_thumbnails(self):
        """Gallery endpoint returns videos array with thumbnail_url and output_url"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "videos" in data, "Response should contain 'videos' key"
        
        videos = data["videos"]
        assert len(videos) > 0, "Gallery should have at least one video"
        
        # Check first video has required fields
        first_video = videos[0]
        assert "thumbnail_url" in first_video, "Video should have thumbnail_url"
        assert first_video["thumbnail_url"] is not None, "thumbnail_url should not be None"
        assert len(first_video["thumbnail_url"]) > 10, "thumbnail_url should be a valid URL"
        
        # Check output_url is present
        assert "output_url" in first_video, "Video should have output_url"
        
        print(f"Gallery returned {len(videos)} videos with thumbnails")
    
    def test_gallery_categories_shows_actual_count(self):
        """Gallery categories endpoint shows actual count (30), not 0"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "categories" in data, "Response should contain 'categories' key"
        
        categories = data["categories"]
        assert len(categories) > 0, "Should have at least one category"
        
        # Find 'all' category
        all_category = next((c for c in categories if c["id"] == "all"), None)
        assert all_category is not None, "Should have 'all' category"
        assert all_category["count"] > 0, f"All category count should be > 0, got {all_category['count']}"
        
        print(f"All category count: {all_category['count']}")
    
    def test_gallery_leaderboard_returns_items_with_thumbnails(self):
        """Gallery leaderboard returns most remixed items with thumbnails"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "leaderboard" in data, "Response should contain 'leaderboard' key"
        
        leaderboard = data["leaderboard"]
        # Leaderboard may be empty if no remixed items
        if len(leaderboard) > 0:
            first_item = leaderboard[0]
            assert "thumbnail_url" in first_item or "output_url" in first_item, \
                "Leaderboard item should have thumbnail_url or output_url"
            print(f"Leaderboard returned {len(leaderboard)} items")
        else:
            print("Leaderboard is empty (no remixed items)")


class TestExploreEndpoint:
    """Test Explore API endpoint for media display"""
    
    def test_explore_returns_stories_with_thumbnails(self):
        """Explore endpoint returns stories with thumbnail_url"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore?limit=12")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "stories" in data, "Response should contain 'stories' key"
        
        stories = data["stories"]
        assert len(stories) > 0, "Explore should have at least one story"
        
        # Check first story has thumbnail_url
        first_story = stories[0]
        assert "thumbnail_url" in first_story, "Story should have thumbnail_url"
        assert first_story["thumbnail_url"] is not None, "thumbnail_url should not be None"
        assert len(first_story["thumbnail_url"]) > 10, "thumbnail_url should be a valid URL"
        
        # Check hook_text is present
        assert "hook_text" in first_story, "Story should have hook_text"
        
        print(f"Explore returned {len(stories)} stories with thumbnails")
    
    def test_explore_returns_total_count(self):
        """Explore endpoint returns total count"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data, "Response should contain 'total' key"
        assert data["total"] > 0, f"Total should be > 0, got {data['total']}"
        
        print(f"Explore total: {data['total']}")
    
    def test_explore_category_counts(self):
        """Explore endpoint returns category counts"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data, "Response should contain 'categories' key"
        
        categories = data["categories"]
        assert "all" in categories, "Should have 'all' category count"
        assert categories["all"] > 0, f"All category count should be > 0, got {categories['all']}"
        
        print(f"Explore category counts: {categories}")


class TestLandingPageEndpoints:
    """Test Landing page API endpoints for media display"""
    
    def test_trending_weekly_returns_items_with_thumbnails(self):
        """Trending weekly endpoint returns items with thumbnail_url"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=12")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "items" in data, "Response should contain 'items' key"
        
        items = data["items"]
        assert len(items) > 0, "Trending should have at least one item"
        
        # Check first item has thumbnail_url
        first_item = items[0]
        assert "thumbnail_url" in first_item, "Item should have thumbnail_url"
        assert first_item["thumbnail_url"] is not None, "thumbnail_url should not be None"
        assert len(first_item["thumbnail_url"]) > 10, "thumbnail_url should be a valid URL"
        
        print(f"Trending weekly returned {len(items)} items with thumbnails")
    
    def test_live_activity_returns_items(self):
        """Live activity endpoint returns items"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=6")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "items" in data, "Response should contain 'items' key"
        
        print(f"Live activity returned {len(data['items'])} items")


class TestThumbnailURLValidity:
    """Test that thumbnail URLs are valid and accessible"""
    
    def test_gallery_thumbnail_url_format(self):
        """Gallery thumbnail URLs are properly formatted R2 URLs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        videos = data.get("videos", [])
        
        for video in videos[:3]:
            thumb_url = video.get("thumbnail_url", "")
            # Should be an R2 URL or presigned URL
            assert "r2" in thumb_url.lower() or "cloudflarestorage" in thumb_url.lower() or \
                   "X-Amz-Signature" in thumb_url, \
                   f"Thumbnail URL should be R2/presigned URL: {thumb_url[:100]}"
            print(f"Valid thumbnail URL: {thumb_url[:80]}...")
    
    def test_explore_thumbnail_url_format(self):
        """Explore thumbnail URLs are properly formatted R2 URLs"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        stories = data.get("stories", [])
        
        for story in stories[:3]:
            thumb_url = story.get("thumbnail_url", "")
            # Should be an R2 URL or presigned URL
            assert "r2" in thumb_url.lower() or "cloudflarestorage" in thumb_url.lower() or \
                   "X-Amz-Signature" in thumb_url, \
                   f"Thumbnail URL should be R2/presigned URL: {thumb_url[:100]}"
            print(f"Valid thumbnail URL: {thumb_url[:80]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
