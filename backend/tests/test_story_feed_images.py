"""
Test Story Feed API - Image Data Integrity
Verifies that the story-feed endpoint returns stories with non-null thumbnail_small_url and poster_url
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

class TestStoryFeedImages:
    """Tests for /api/engagement/story-feed image data integrity"""
    
    def test_story_feed_returns_stories(self):
        """Verify story-feed endpoint returns stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'trending_stories' in data, "Missing trending_stories in response"
        assert 'fresh_stories' in data, "Missing fresh_stories in response"
        assert 'featured_story' in data, "Missing featured_story in response"
        
        # Should have at least 20 stories total
        total_stories = len(data.get('trending_stories', [])) + len(data.get('fresh_stories', []))
        assert total_stories >= 20, f"Expected at least 20 stories, got {total_stories}"
        print(f"✓ Story feed returned {total_stories} stories")
    
    def test_all_stories_have_thumbnail_small_url(self):
        """Verify ALL stories have non-null thumbnail_small_url"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        all_stories = (
            data.get('trending_stories', []) + 
            data.get('fresh_stories', []) + 
            data.get('continue_stories', []) + 
            data.get('unfinished_worlds', [])
        )
        if data.get('featured_story'):
            all_stories.append(data['featured_story'])
        
        missing_thumb = []
        for story in all_stories:
            if not story.get('thumbnail_small_url'):
                missing_thumb.append(story.get('title', story.get('job_id', 'Unknown')))
        
        assert len(missing_thumb) == 0, f"Stories missing thumbnail_small_url: {missing_thumb}"
        print(f"✓ All {len(all_stories)} stories have thumbnail_small_url")
    
    def test_all_stories_have_poster_url(self):
        """Verify ALL stories have non-null poster_url"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        all_stories = (
            data.get('trending_stories', []) + 
            data.get('fresh_stories', []) + 
            data.get('continue_stories', []) + 
            data.get('unfinished_worlds', [])
        )
        if data.get('featured_story'):
            all_stories.append(data['featured_story'])
        
        missing_poster = []
        for story in all_stories:
            if not story.get('poster_url'):
                missing_poster.append(story.get('title', story.get('job_id', 'Unknown')))
        
        assert len(missing_poster) == 0, f"Stories missing poster_url: {missing_poster}"
        print(f"✓ All {len(all_stories)} stories have poster_url")
    
    def test_featured_story_has_valid_media(self):
        """Verify featured story has valid thumbnail_small_url and poster_url"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        featured = data.get('featured_story')
        
        assert featured is not None, "No featured story returned"
        assert featured.get('thumbnail_small_url'), "Featured story missing thumbnail_small_url"
        assert featured.get('poster_url'), "Featured story missing poster_url"
        assert featured.get('title'), "Featured story missing title"
        
        print(f"✓ Featured story '{featured.get('title')}' has valid media URLs")
    
    def test_r2_cdn_urls_are_valid(self):
        """Verify R2 CDN image URLs return HTTP 200"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        trending = data.get('trending_stories', [])[:5]  # Test first 5
        
        for story in trending:
            thumb_url = story.get('thumbnail_small_url')
            if thumb_url and 'r2.dev' in thumb_url:
                img_response = requests.head(thumb_url, timeout=10)
                assert img_response.status_code == 200, f"R2 CDN URL failed: {thumb_url}"
                print(f"✓ R2 CDN URL valid: {thumb_url[:60]}...")
    
    def test_trending_stories_have_badges(self):
        """Verify trending stories have badge field"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        trending = data.get('trending_stories', [])
        
        for story in trending[:10]:
            assert 'badge' in story, f"Story '{story.get('title')}' missing badge field"
        
        print(f"✓ All trending stories have badge field")
    
    def test_story_feed_response_structure(self):
        """Verify story-feed response has correct structure"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        
        # Required top-level fields
        required_fields = ['featured_story', 'trending_stories', 'fresh_stories', 'live_stats']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check story structure
        if data.get('trending_stories'):
            story = data['trending_stories'][0]
            story_fields = ['job_id', 'title', 'thumbnail_small_url', 'poster_url', 'badge']
            for field in story_fields:
                assert field in story, f"Story missing field: {field}"
        
        print("✓ Story feed response structure is valid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
