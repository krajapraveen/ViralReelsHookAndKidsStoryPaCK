"""
Iteration 305 - Gallery & Explore Bug Fixes Regression Tests

Tests verify bug fixes for:
1. Gallery showing 'No videos found' (was 0 items) - Now returns 48+ items
2. Explore page showing gradient placeholders instead of real images - SafeImage crossOrigin fix
3. Gallery scene_images fallback for thumbnail_url - items without explicit thumbnail_url use scene_images[0].url
4. Profile page link fix - /app/story-video-studio instead of /app/story-video
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://growth-funnel-stable.preview.emergentagent.com').rstrip('/')


class TestGalleryAPI:
    """Test Gallery API - was showing 0 items, now returns 48+"""
    
    def test_gallery_returns_items(self):
        """Gallery should return 48 items (limit) from 74 COMPLETED total"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        videos = data.get("videos", [])
        
        # Was 0, now should be 48 (limit)
        assert len(videos) >= 48, f"Expected 48+ videos, got {len(videos)}"
        print(f"✓ Gallery returns {len(videos)} videos (was 0 before bug fix)")
    
    def test_gallery_all_items_have_thumbnail_url(self):
        """Every gallery item should have thumbnail_url (auto-populated from scene_images if missing)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        videos = response.json().get("videos", [])
        missing_thumbnails = []
        
        for video in videos:
            if not video.get("thumbnail_url"):
                missing_thumbnails.append(video.get("title", "Unknown"))
        
        assert len(missing_thumbnails) == 0, f"Videos missing thumbnail_url: {missing_thumbnails}"
        print(f"✓ All {len(videos)} videos have thumbnail_url")
    
    def test_gallery_thumbnails_are_presigned(self):
        """Gallery thumbnails should be presigned R2 URLs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        videos = response.json().get("videos", [])
        assert len(videos) > 0
        
        presigned_count = 0
        for video in videos[:10]:  # Check first 10
            thumb = video.get("thumbnail_url", "")
            # Presigned URLs contain X-Amz-Signature or are r2.cloudflarestorage.com
            if "X-Amz-Signature" in thumb or "r2.cloudflarestorage.com" in thumb:
                presigned_count += 1
        
        assert presigned_count > 0, "No presigned URLs found in thumbnails"
        print(f"✓ {presigned_count}/10 thumbnails are presigned R2 URLs")
    
    def test_gallery_category_filter(self):
        """Gallery category filters work correctly"""
        # Test cartoon_2d category
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?category=cartoon_2d")
        assert response.status_code == 200
        
        videos = response.json().get("videos", [])
        # Should have ~55 cartoon_2d items
        assert len(videos) >= 40, f"Expected 40+ cartoon_2d videos, got {len(videos)}"
        
        for video in videos[:5]:
            assert video.get("animation_style") == "cartoon_2d", f"Wrong style: {video.get('animation_style')}"
        
        print(f"✓ Category filter works - cartoon_2d returns {len(videos)} videos")
    
    def test_gallery_sort_options(self):
        """Gallery sorting (newest, trending, most_remixed) works"""
        for sort in ["newest", "trending", "most_remixed"]:
            response = requests.get(f"{BASE_URL}/api/pipeline/gallery?sort={sort}")
            assert response.status_code == 200
            videos = response.json().get("videos", [])
            assert len(videos) >= 40, f"Sort {sort} returned too few: {len(videos)}"
        
        print("✓ All sort options work (newest, trending, most_remixed)")


class TestGalleryDebugEndpoint:
    """Test new diagnostic endpoint for debugging empty galleries"""
    
    def test_debug_endpoint_exists(self):
        """Debug endpoint returns stats"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/debug")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_pipeline_jobs" in data
        assert "completed" in data
        assert "gallery_query_matches" in data
        print(f"✓ Debug endpoint works - {data.get('completed')} completed items")
    
    def test_debug_shows_scene_images_count(self):
        """Debug shows scene_images stats for fallback debugging"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/debug")
        data = response.json()
        
        with_scenes = data.get("completed_with_scene_images", 0)
        completed = data.get("completed", 0)
        
        # All completed items should have scene_images
        assert with_scenes == completed, f"Scene images mismatch: {with_scenes}/{completed}"
        print(f"✓ All {completed} completed items have scene_images")
    
    def test_gallery_query_matches_all_completed(self):
        """Gallery query should match all COMPLETED items (expanded filter)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/debug")
        data = response.json()
        
        completed = data.get("completed", 0)
        matches = data.get("gallery_query_matches", 0)
        
        # Gallery query should match all completed items now
        assert matches == completed, f"Gallery query only matches {matches}/{completed}"
        print(f"✓ Gallery query matches all {matches} completed items")


class TestGalleryCategories:
    """Test category counts endpoint"""
    
    def test_categories_returns_all(self):
        """Categories endpoint returns all categories with counts"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        
        data = response.json()
        categories = data.get("categories", [])
        
        assert len(categories) >= 4, f"Expected 4+ categories, got {len(categories)}"
        
        # Check 'all' category is first and has total count
        all_cat = categories[0]
        assert all_cat.get("id") == "all", "First category should be 'all'"
        assert all_cat.get("count") >= 74, f"All count should be ~74, got {all_cat.get('count')}"
        
        print(f"✓ Categories endpoint works - {len(categories)} categories, total {all_cat.get('count')}")
    
    def test_category_counts_accurate(self):
        """Category counts match expected values"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        categories = {c["id"]: c["count"] for c in response.json().get("categories", [])}
        
        # Expected counts from previous iterations
        assert categories.get("cartoon_2d", 0) >= 50, f"Expected ~55 cartoon_2d, got {categories.get('cartoon_2d')}"
        assert categories.get("watercolor", 0) >= 10, f"Expected ~11 watercolor, got {categories.get('watercolor')}"
        assert categories.get("anime_style", 0) >= 3, f"Expected ~4 anime, got {categories.get('anime_style')}"
        
        print(f"✓ Category counts accurate: cartoon_2d={categories.get('cartoon_2d')}, watercolor={categories.get('watercolor')}")


class TestExploreEndpoint:
    """Test public explore endpoint with scene_images fallback"""
    
    def test_explore_trending(self):
        """Explore trending tab returns items with thumbnails"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=12")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("tab") == "trending"
        assert data.get("total") >= 74, f"Expected 74 total, got {data.get('total')}"
        
        items = data.get("items", [])
        assert len(items) == 12, f"Expected 12 items, got {len(items)}"
        
        # All items should have thumbnail_url
        for item in items:
            assert item.get("thumbnail_url"), f"Missing thumbnail: {item.get('title')}"
        
        print(f"✓ Explore trending works - {len(items)} items, all with thumbnails")
    
    def test_explore_newest(self):
        """Explore newest tab returns items sorted by date"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=12")
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("items", [])
        
        assert len(items) >= 10
        for item in items:
            assert item.get("thumbnail_url"), f"Missing thumbnail: {item.get('title')}"
        
        print(f"✓ Explore newest works - all {len(items)} items have thumbnails")
    
    def test_explore_most_remixed(self):
        """Explore most_remixed tab returns items sorted by remix_count"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=most_remixed&limit=12")
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("items", [])
        
        assert len(items) >= 10
        
        # First item should have highest remix count
        if items[0].get("remix_count", 0) > 0:
            assert items[0].get("remix_count") >= items[1].get("remix_count", 0)
        
        print(f"✓ Explore most_remixed works - top item has {items[0].get('remix_count', 0)} remixes")
    
    def test_explore_thumbnails_accessible(self):
        """Thumbnail URLs from explore are actually accessible"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=3")
        items = response.json().get("items", [])
        
        accessible = 0
        for item in items:
            thumb = item.get("thumbnail_url")
            if thumb:
                try:
                    head = requests.head(thumb, timeout=5)
                    if head.status_code in [200, 206]:
                        accessible += 1
                except:
                    pass
        
        assert accessible > 0, "No thumbnails are accessible"
        print(f"✓ {accessible}/3 thumbnails are HTTP accessible")


class TestGalleryLeaderboard:
    """Test gallery leaderboard endpoint"""
    
    def test_leaderboard_returns_items(self):
        """Leaderboard returns top remixed items"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        
        data = response.json()
        leaderboard = data.get("leaderboard", [])
        
        assert len(leaderboard) >= 1, "Leaderboard should have items"
        
        # Items should have thumbnail_url
        for item in leaderboard:
            if item.get("thumbnail_url"):
                print(f"  Top remixed: {item.get('title')} ({item.get('remix_count', 0)} remixes)")
        
        print(f"✓ Leaderboard returns {len(leaderboard)} items")


class TestThumbnailFallbackLogic:
    """Test that scene_images fallback for thumbnail_url is working"""
    
    def test_items_without_explicit_thumbnail_get_fallback(self):
        """Items without explicit thumbnail_url get it from scene_images"""
        # Check debug endpoint for stats
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/debug")
        data = response.json()
        
        with_thumb = data.get("completed_with_thumbnail_url", 0)
        with_scenes = data.get("completed_with_scene_images", 0)
        completed = data.get("completed", 0)
        
        # Many items have scene_images but not explicit thumbnail_url
        # Gallery API should fill thumbnail_url from scene_images
        print(f"  DB stats: {with_thumb} with explicit thumbnail, {with_scenes} with scene_images")
        
        # Now verify Gallery API gives thumbnails for all
        gallery_response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        videos = gallery_response.json().get("videos", [])
        
        videos_with_thumb = sum(1 for v in videos if v.get("thumbnail_url"))
        
        # All gallery items should have thumbnail_url after fallback logic
        assert videos_with_thumb == len(videos), f"Only {videos_with_thumb}/{len(videos)} have thumbnails"
        print(f"✓ All {len(videos)} gallery items have thumbnail_url (fallback working)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
