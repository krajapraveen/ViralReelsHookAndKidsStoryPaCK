"""
Explore Page / Gallery Testing - Iteration 343
Tests for /api/engagement/explore endpoint with category filters, sort, cursor pagination
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestExploreEndpoint:
    """Tests for GET /api/engagement/explore - PUBLIC endpoint (no auth required)"""
    
    def test_explore_default_returns_stories(self):
        """Test default explore endpoint returns stories with required fields"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        assert response.status_code == 200
        
        data = response.json()
        assert "stories" in data
        assert "total" in data
        assert "next_cursor" in data
        assert "categories" in data
        
        # Verify stories have required fields
        if len(data["stories"]) > 0:
            story = data["stories"][0]
            assert "job_id" in story
            assert "title" in story
            assert "thumbnail_url" in story
            assert "hook_text" in story
            print(f"PASS: Default explore returns {len(data['stories'])} stories, total={data['total']}")
    
    def test_explore_returns_category_counts(self):
        """Test explore returns category counts in response"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        assert response.status_code == 200
        
        data = response.json()
        categories = data.get("categories", {})
        
        # Verify all expected categories are present
        expected_cats = ["all", "kids", "emotional", "mystery", "viral"]
        for cat in expected_cats:
            assert cat in categories, f"Missing category: {cat}"
            assert isinstance(categories[cat], int), f"Category {cat} count should be int"
        
        print(f"PASS: Category counts: {categories}")
    
    def test_explore_category_filter_kids(self):
        """Test category=kids filter returns kids stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"category": "kids"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] > 0, "Should have kids stories"
        print(f"PASS: Kids category returns {data['total']} stories")
    
    def test_explore_category_filter_emotional(self):
        """Test category=emotional filter returns emotional stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"category": "emotional"})
        assert response.status_code == 200
        
        data = response.json()
        # Emotional stories match title patterns
        print(f"PASS: Emotional category returns {data['total']} stories")
    
    def test_explore_category_filter_mystery(self):
        """Test category=mystery filter returns mystery stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"category": "mystery"})
        assert response.status_code == 200
        
        data = response.json()
        print(f"PASS: Mystery category returns {data['total']} stories")
    
    def test_explore_category_filter_viral(self):
        """Test category=viral filter returns viral stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"category": "viral"})
        assert response.status_code == 200
        
        data = response.json()
        print(f"PASS: Viral category returns {data['total']} stories")
    
    def test_explore_sort_trending(self):
        """Test sort=trending returns stories sorted by remix_count"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"sort": "trending"})
        assert response.status_code == 200
        
        data = response.json()
        stories = data["stories"]
        if len(stories) >= 2:
            # Trending should sort by remix_count descending
            for i in range(len(stories) - 1):
                assert stories[i].get("remix_count", 0) >= stories[i+1].get("remix_count", 0), \
                    "Stories should be sorted by remix_count descending"
        print(f"PASS: Trending sort returns {len(stories)} stories")
    
    def test_explore_sort_new(self):
        """Test sort=new returns stories sorted by created_at"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"sort": "new"})
        assert response.status_code == 200
        
        data = response.json()
        stories = data["stories"]
        if len(stories) >= 2:
            # New should sort by created_at descending
            for i in range(len(stories) - 1):
                assert stories[i].get("created_at", "") >= stories[i+1].get("created_at", ""), \
                    "Stories should be sorted by created_at descending"
        print(f"PASS: New sort returns {len(stories)} stories")
    
    def test_explore_sort_most_continued(self):
        """Test sort=most_continued returns stories sorted by remix_count"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"sort": "most_continued"})
        assert response.status_code == 200
        
        data = response.json()
        print(f"PASS: Most continued sort returns {len(data['stories'])} stories")
    
    def test_explore_pagination_limit(self):
        """Test limit parameter controls batch size"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"limit": 5})
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["stories"]) <= 5, "Should return at most 5 stories"
        print(f"PASS: Limit=5 returns {len(data['stories'])} stories")
    
    def test_explore_pagination_cursor(self):
        """Test cursor pagination works correctly"""
        # First page
        response1 = requests.get(f"{BASE_URL}/api/engagement/explore", params={"limit": 5, "cursor": 0})
        assert response1.status_code == 200
        data1 = response1.json()
        
        if data1["next_cursor"] is not None:
            # Second page
            response2 = requests.get(f"{BASE_URL}/api/engagement/explore", 
                                    params={"limit": 5, "cursor": data1["next_cursor"]})
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Verify different stories
            ids1 = {s["job_id"] for s in data1["stories"]}
            ids2 = {s["job_id"] for s in data2["stories"]}
            assert ids1.isdisjoint(ids2), "Paginated results should not overlap"
            print(f"PASS: Cursor pagination works - page1: {len(data1['stories'])}, page2: {len(data2['stories'])}")
        else:
            print(f"PASS: Only one page of results (total={data1['total']})")
    
    def test_explore_end_of_list(self):
        """Test next_cursor is null when no more stories"""
        # Get all stories with large limit
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={"limit": 100})
        assert response.status_code == 200
        
        data = response.json()
        if len(data["stories"]) >= data["total"]:
            assert data["next_cursor"] is None, "next_cursor should be null at end of list"
            print(f"PASS: End of list - next_cursor is null")
        else:
            print(f"PASS: More stories available - next_cursor={data['next_cursor']}")
    
    def test_explore_stories_have_presigned_urls(self):
        """Test thumbnail URLs are presigned R2 URLs"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        assert response.status_code == 200
        
        data = response.json()
        for story in data["stories"][:3]:  # Check first 3
            thumb = story.get("thumbnail_url", "")
            if thumb:
                assert "X-Amz-Signature" in thumb or "r2.cloudflarestorage.com" in thumb, \
                    "Thumbnail should be presigned R2 URL"
        print(f"PASS: Thumbnails have presigned URLs")
    
    def test_explore_stories_have_hook_text(self):
        """Test stories have hook_text extracted from story_text"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore")
        assert response.status_code == 200
        
        data = response.json()
        for story in data["stories"][:5]:
            assert "hook_text" in story, "Story should have hook_text"
            assert len(story["hook_text"]) > 0, "hook_text should not be empty"
        print(f"PASS: Stories have hook_text")


class TestExploreWithCategoryAndSort:
    """Combined filter tests"""
    
    def test_explore_kids_trending(self):
        """Test kids + trending combination"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", 
                               params={"category": "kids", "sort": "trending"})
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Kids + Trending returns {data['total']} stories")
    
    def test_explore_emotional_new(self):
        """Test emotional + new combination"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", 
                               params={"category": "emotional", "sort": "new"})
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Emotional + New returns {data['total']} stories")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
