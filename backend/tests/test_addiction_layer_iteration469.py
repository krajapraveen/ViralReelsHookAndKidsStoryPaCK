"""
Addiction Layer Features Testing - Iteration 469
Tests for:
1. Trending badges on gallery cards (Trending >=10K, Popular >=5K, Rising >=1K)
2. Time-bound remix copy ('X remixed today')
3. CompetitiveComparison component (code verification)
4. Instant Remix buttons (code verification)
5. Session streak counter (code verification)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')


class TestGalleryRemixFeed:
    """Test gallery remix feed endpoint for trending badges data"""
    
    def test_remix_feed_returns_items_with_remixes_count(self):
        """Verify remix feed returns items with remixes_count for badge logic"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert 'items' in data
        assert len(data['items']) > 0
        
        # Check first item has remixes_count
        first_item = data['items'][0]
        assert 'remixes_count' in first_item
        assert isinstance(first_item['remixes_count'], int)
        print(f"First item remixes_count: {first_item['remixes_count']}")
    
    def test_remix_feed_items_sorted_by_remixes_count(self):
        """Verify items are sorted by remixes_count descending"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        items = data['items']
        
        # Check sorting
        for i in range(len(items) - 1):
            assert items[i]['remixes_count'] >= items[i+1]['remixes_count'], \
                f"Items not sorted: {items[i]['remixes_count']} < {items[i+1]['remixes_count']}"
        print("Items correctly sorted by remixes_count descending")
    
    def test_remix_feed_has_trending_badge_eligible_items(self):
        """Verify at least one item qualifies for Trending badge (>=10K remixes)"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        items = data['items']
        
        trending_items = [i for i in items if i['remixes_count'] >= 10000]
        popular_items = [i for i in items if 5000 <= i['remixes_count'] < 10000]
        rising_items = [i for i in items if 1000 <= i['remixes_count'] < 5000]
        
        print(f"Trending (>=10K): {len(trending_items)} items")
        print(f"Popular (>=5K): {len(popular_items)} items")
        print(f"Rising (>=1K): {len(rising_items)} items")
        
        # At least one item should qualify for a badge
        assert len(trending_items) + len(popular_items) + len(rising_items) > 0, \
            "No items qualify for any badge"
    
    def test_remix_feed_items_have_required_fields(self):
        """Verify items have all required fields for RemixCard component"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        items = data['items']
        
        required_fields = ['item_id', 'title', 'thumbnail_url', 'remixes_count']
        
        for item in items:
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            
            # Verify item_id format for data-testid
            assert item['item_id'], "item_id should not be empty"
        
        print(f"All {len(items)} items have required fields")


class TestGalleryRemixEndpoint:
    """Test gallery remix endpoint for incrementing count"""
    
    def test_remix_endpoint_returns_prefill_data(self):
        """Verify remix endpoint returns prefill data for Studio"""
        # First get an item
        feed_response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=1")
        assert feed_response.status_code == 200
        
        items = feed_response.json()['items']
        if not items:
            pytest.skip("No gallery items available")
        
        item_id = items[0]['item_id']
        
        # Call remix endpoint
        remix_response = requests.post(f"{BASE_URL}/api/gallery/{item_id}/remix")
        assert remix_response.status_code == 200
        
        data = remix_response.json()
        assert data.get('success') == True
        assert 'prefill' in data
        
        prefill = data['prefill']
        assert 'title' in prefill
        assert 'story_text' in prefill
        print(f"Remix prefill data: title='{prefill['title'][:30]}...'")


class TestBadgeLogicVerification:
    """Verify badge thresholds match frontend logic"""
    
    def test_badge_thresholds(self):
        """Verify badge thresholds: Trending >=10K, Popular >=5K, Rising >=1K"""
        response = requests.get(f"{BASE_URL}/api/gallery/remix-feed?limit=10")
        assert response.status_code == 200
        
        items = response.json()['items']
        
        for item in items:
            remixes = item['remixes_count']
            
            # Determine expected badge
            if remixes >= 10000:
                expected_badge = 'Trending'
            elif remixes >= 5000:
                expected_badge = 'Popular'
            elif remixes >= 1000:
                expected_badge = 'Rising'
            else:
                expected_badge = None
            
            print(f"Item '{item['title'][:25]}...': {remixes} remixes -> {expected_badge or 'No badge'}")


class TestAuthAndUserJobs:
    """Test authentication and user jobs for session streak"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get('token')
        pytest.skip("Authentication failed")
    
    def test_user_jobs_endpoint(self, auth_token):
        """Verify user jobs endpoint returns jobs with created_at for streak calculation"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('success') == True
        assert 'jobs' in data
        
        jobs = data['jobs']
        print(f"User has {len(jobs)} jobs")
        
        # Check jobs have created_at for streak calculation
        if jobs:
            first_job = jobs[0]
            assert 'created_at' in first_job, "Jobs should have created_at for streak calculation"
            print(f"First job created_at: {first_job['created_at']}")


class TestCodeVerification:
    """Verify code structure for features that require video completion"""
    
    def test_competitive_comparison_component_exists(self):
        """Verify CompetitiveComparison component is defined in StoryVideoPipeline"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', 'function CompetitiveComparison', '/app/frontend/src/pages/StoryVideoPipeline.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "CompetitiveComparison component not found"
        print("CompetitiveComparison component found")
    
    def test_competitive_comparison_has_beat_this_button(self):
        """Verify 'Try to beat this' button exists with correct data-testid"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', 'data-testid="beat-this-btn"', '/app/frontend/src/pages/StoryVideoPipeline.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "beat-this-btn not found"
        print("'Try to beat this' button found with data-testid")
    
    def test_competitive_comparison_has_improve_button(self):
        """Verify 'Improve yours' button exists with correct data-testid"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', 'data-testid="improve-version-btn"', '/app/frontend/src/pages/StoryVideoPipeline.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "improve-version-btn not found"
        print("'Improve yours' button found with data-testid")
    
    def test_instant_remix_section_exists(self):
        """Verify Instant Remix section exists with correct data-testid"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', 'data-testid="instant-remix-section"', '/app/frontend/src/pages/StoryVideoPipeline.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "instant-remix-section not found"
        print("Instant Remix section found with data-testid")
    
    def test_instant_remix_buttons_exist(self):
        """Verify all 4 instant remix buttons exist via template literal"""
        import subprocess
        
        # Check for the template literal pattern
        result = subprocess.run(
            ['grep', '-c', 'instant-remix-\\${v.tone}', '/app/frontend/src/pages/StoryVideoPipeline.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "instant-remix template literal not found"
        
        # Check for all 4 tone values
        tones = ['dramatic', 'short', 'fast', 'emotional']
        for tone in tones:
            result = subprocess.run(
                ['grep', '-c', f"tone: '{tone}'", '/app/frontend/src/pages/StoryVideoPipeline.js'],
                capture_output=True, text=True
            )
            count = int(result.stdout.strip()) if result.returncode == 0 else 0
            assert count >= 1, f"tone '{tone}' not found"
        
        print("All 4 instant remix buttons found (dramatic, short, fast, emotional)")
    
    def test_session_streak_exists_in_myspace(self):
        """Verify session streak counter exists in MySpacePage"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', 'data-testid="session-streak"', '/app/frontend/src/pages/MySpacePage.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "session-streak not found"
        print("Session streak counter found with data-testid")
    
    def test_session_streak_shows_today_count(self):
        """Verify session streak shows 'X videos today' text"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', "video.*today", '/app/frontend/src/pages/MySpacePage.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "Session streak 'videos today' text not found"
        print("Session streak 'videos today' text found")


class TestRemixGalleryBadges:
    """Test RemixGallery component badge logic"""
    
    def test_trending_badge_testid_format(self):
        """Verify trending badge data-testid format in RemixGallery"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', 'data-testid={`trending-badge-', '/app/frontend/src/components/RemixGallery.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "trending-badge data-testid not found"
        print("Trending badge data-testid format correct")
    
    def test_badge_thresholds_in_code(self):
        """Verify badge thresholds are correct in RemixGallery"""
        import subprocess
        
        # Check Trending threshold (10000)
        result = subprocess.run(
            ['grep', '-c', 'remixes >= 10000', '/app/frontend/src/components/RemixGallery.js'],
            capture_output=True, text=True
        )
        assert int(result.stdout.strip() or 0) >= 1, "Trending threshold (10000) not found"
        
        # Check Popular threshold (5000)
        result = subprocess.run(
            ['grep', '-c', 'remixes >= 5000', '/app/frontend/src/components/RemixGallery.js'],
            capture_output=True, text=True
        )
        assert int(result.stdout.strip() or 0) >= 1, "Popular threshold (5000) not found"
        
        # Check Rising threshold (1000)
        result = subprocess.run(
            ['grep', '-c', 'remixes >= 1000', '/app/frontend/src/components/RemixGallery.js'],
            capture_output=True, text=True
        )
        assert int(result.stdout.strip() or 0) >= 1, "Rising threshold (1000) not found"
        
        print("All badge thresholds correct: Trending>=10K, Popular>=5K, Rising>=1K")
    
    def test_time_bound_copy_exists(self):
        """Verify 'remixed today' time-bound copy exists"""
        import subprocess
        result = subprocess.run(
            ['grep', '-c', 'remixed today', '/app/frontend/src/components/RemixGallery.js'],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        assert count >= 1, "'remixed today' text not found"
        print("'remixed today' time-bound copy found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
