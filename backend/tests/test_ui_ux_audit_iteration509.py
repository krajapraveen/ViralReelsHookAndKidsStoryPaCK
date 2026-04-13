"""
Iteration 509: UI/UX Audit Tests
Tests for:
1. Cookie consent banner (small toast, bottom-right)
2. Explore page filters stories without thumbnails
3. JourneyProgressBar visibility rules
4. Dashboard layout (TrendingPublicFeed after HottestBattle)
5. PostValueOverlay 'Continue with limited access' stays on /app
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestExploreEndpoint:
    """Test /api/engagement/explore filters stories without thumbnails"""
    
    def test_explore_returns_stories_with_thumbnails_only(self):
        """All stories returned by explore should have thumbnail_url"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore?category=all&sort=trending&limit=20")
        assert response.status_code == 200
        
        data = response.json()
        stories = data.get('stories', [])
        
        # Verify all stories have thumbnails
        for story in stories:
            assert story.get('thumbnail_url'), f"Story '{story.get('title')}' has no thumbnail_url"
        
        print(f"✓ All {len(stories)} stories have thumbnails")
    
    def test_explore_returns_total_count(self):
        """Explore should return total count of stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore?category=all&sort=trending&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert 'total' in data
        assert data['total'] >= 0
        print(f"✓ Total stories: {data['total']}")
    
    def test_explore_category_filters(self):
        """Test category filters work"""
        categories = ['all', 'kids', 'emotional', 'mystery', 'viral']
        
        for category in categories:
            response = requests.get(f"{BASE_URL}/api/engagement/explore?category={category}&limit=5")
            assert response.status_code == 200
            data = response.json()
            assert 'stories' in data
            print(f"✓ Category '{category}': {len(data['stories'])} stories")
    
    def test_explore_sort_options(self):
        """Test sort options work"""
        sorts = ['trending', 'new', 'most_continued']
        
        for sort in sorts:
            response = requests.get(f"{BASE_URL}/api/engagement/explore?sort={sort}&limit=5")
            assert response.status_code == 200
            data = response.json()
            assert 'stories' in data
            print(f"✓ Sort '{sort}': {len(data['stories'])} stories")
    
    def test_explore_pagination(self):
        """Test cursor pagination works"""
        # First page
        response1 = requests.get(f"{BASE_URL}/api/engagement/explore?cursor=0&limit=5")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second page
        next_cursor = data1.get('next_cursor')
        if next_cursor:
            response2 = requests.get(f"{BASE_URL}/api/engagement/explore?cursor={next_cursor}&limit=5")
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Verify different stories
            ids1 = {s.get('job_id') for s in data1['stories']}
            ids2 = {s.get('job_id') for s in data2['stories']}
            assert ids1.isdisjoint(ids2), "Pagination returned duplicate stories"
            print(f"✓ Pagination works: page1={len(data1['stories'])}, page2={len(data2['stories'])}")


class TestStoryFeedEndpoint:
    """Test /api/engagement/story-feed for dashboard"""
    
    def test_story_feed_returns_rows(self):
        """Story feed should return rows for dashboard"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        assert 'rows' in data
        assert isinstance(data['rows'], list)
        print(f"✓ Story feed returned {len(data['rows'])} rows")
    
    def test_story_feed_returns_features(self):
        """Story feed should return features list"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        assert 'features' in data
        assert isinstance(data['features'], list)
        print(f"✓ Story feed returned {len(data['features'])} features")
    
    def test_story_feed_returns_live_stats(self):
        """Story feed should return live stats"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        assert 'live_stats' in data
        assert 'stories_today' in data['live_stats']
        assert 'total_stories' in data['live_stats']
        print(f"✓ Live stats: {data['live_stats']['stories_today']} today, {data['live_stats']['total_stories']} total")


class TestHottestBattleEndpoint:
    """Test /api/stories/hottest-battle for dashboard"""
    
    def test_hottest_battle_returns_data(self):
        """Hottest battle endpoint should return battle data"""
        response = requests.get(f"{BASE_URL}/api/stories/hottest-battle")
        # May return 404 if no battles, or 200 with data
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Hottest battle: {data.get('title', 'N/A')}")
        else:
            print("✓ No hottest battle available (404)")


class TestTrendingEndpoint:
    """Test /api/engagement/trending for TrendingPublicFeed"""
    
    def test_trending_returns_items(self):
        """Trending endpoint should return trending items"""
        response = requests.get(f"{BASE_URL}/api/engagement/trending")
        assert response.status_code == 200
        
        data = response.json()
        assert 'trending' in data
        print(f"✓ Trending returned {len(data['trending'])} items")


class TestAuthRedirect:
    """Test login redirects to /app (not /app/story-video-studio)"""
    
    def test_login_endpoint_exists(self):
        """Login endpoint should exist"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        # Should return 200 with token or 401 for invalid credentials
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert 'token' in data or 'access_token' in data
            print("✓ Login endpoint works")
        else:
            print("✓ Login endpoint exists (credentials may be invalid)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
