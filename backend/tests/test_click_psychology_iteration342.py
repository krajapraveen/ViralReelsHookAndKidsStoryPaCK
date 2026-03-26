"""
Click Psychology Optimization - Backend API Tests (Iteration 342)
Tests for card-click tracking and card-analytics endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')


class TestCardClickTracking:
    """Tests for POST /api/engagement/card-click endpoint (PUBLIC - no auth required)"""
    
    def test_card_click_success(self):
        """Test card click tracking with valid data"""
        response = requests.post(
            f"{BASE_URL}/api/engagement/card-click",
            json={
                "story_id": "test_story_iteration342",
                "cta_variant": "See What Happens Next",
                "source": "dashboard"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: Card click tracked successfully")
    
    def test_card_click_variant_continue_this_story(self):
        """Test card click with 'Continue This Story' variant"""
        response = requests.post(
            f"{BASE_URL}/api/engagement/card-click",
            json={
                "story_id": "test_story_iteration342_v2",
                "cta_variant": "Continue This Story",
                "source": "dashboard"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: 'Continue This Story' variant tracked")
    
    def test_card_click_variant_what_happens_next(self):
        """Test card click with 'What Happens Next?' variant"""
        response = requests.post(
            f"{BASE_URL}/api/engagement/card-click",
            json={
                "story_id": "test_story_iteration342_v3",
                "cta_variant": "What Happens Next?",
                "source": "dashboard"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: 'What Happens Next?' variant tracked")


class TestCardAnalytics:
    """Tests for GET /api/engagement/card-analytics endpoint (PUBLIC - no auth required)"""
    
    def test_card_analytics_returns_data(self):
        """Test card analytics returns variant breakdown"""
        response = requests.get(f"{BASE_URL}/api/engagement/card-analytics")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_clicks" in data
        assert "variants" in data
        assert isinstance(data["variants"], list)
        
        print(f"PASS: Card analytics returned {data['total_clicks']} total clicks")
        print(f"  Variants: {data['variants']}")
    
    def test_card_analytics_variant_breakdown(self):
        """Test that analytics includes percentage breakdown"""
        response = requests.get(f"{BASE_URL}/api/engagement/card-analytics")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["variants"]) > 0:
            for variant in data["variants"]:
                assert "variant" in variant
                assert "clicks" in variant
                assert "pct" in variant
                assert isinstance(variant["pct"], (int, float))
            print(f"PASS: Variant breakdown includes percentages")
        else:
            print(f"INFO: No variants recorded yet")


class TestStoryFeed:
    """Tests for GET /api/engagement/story-feed endpoint"""
    
    def test_story_feed_returns_trending(self):
        """Test story feed returns trending stories with hook text"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "trending" in data
        assert "live_stats" in data
        
        trending = data["trending"]
        if len(trending) > 0:
            first_story = trending[0]
            assert "job_id" in first_story
            assert "title" in first_story
            assert "hook_text" in first_story
            print(f"PASS: Story feed returns {len(trending)} trending stories with hook_text")
            print(f"  First hook: {first_story['hook_text'][:60]}...")
        else:
            print(f"INFO: No trending stories available")
    
    def test_story_feed_live_stats(self):
        """Test story feed returns live stats"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        
        live_stats = data.get("live_stats", {})
        assert "total_stories" in live_stats
        assert "stories_today" in live_stats
        assert "total_continuations" in live_stats
        
        print(f"PASS: Live stats returned")
        print(f"  Total stories: {live_stats['total_stories']}")
        print(f"  Stories today: {live_stats['stories_today']}")
        print(f"  Total continuations: {live_stats['total_continuations']}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """Test API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"PASS: API is healthy")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
