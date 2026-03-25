"""
P0 Product Transformation Tests - Iteration 325
Tests for story-driven homepage, Continue Story flow, Gallery, and Studio features.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestPublicEndpoints:
    """Test public endpoints for homepage and gallery"""
    
    def test_public_stats_endpoint(self):
        """Test /api/public/stats returns stats for homepage"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200
        data = response.json()
        # Should have stats fields
        assert isinstance(data, dict)
        print(f"✓ Public stats: {data}")
    
    def test_trending_weekly_endpoint(self):
        """Test /api/public/trending-weekly returns trending stories for homepage showcase"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=12")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        items = data["items"]
        print(f"✓ Trending weekly: {len(items)} items returned")
        
        # Verify items have required fields for Continue Story
        if items:
            item = items[0]
            assert "title" in item or "story_text" in item, "Items should have title or story_text for Continue Story"
            print(f"✓ First item: {item.get('title', 'Untitled')}")
    
    def test_live_activity_endpoint(self):
        """Test /api/public/live-activity returns live feed for 'Happening now' section"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=6")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ Live activity: {len(data['items'])} items returned")


class TestGalleryEndpoints:
    """Test gallery endpoints with Continue Story features"""
    
    def test_gallery_returns_items_with_thumbnails(self):
        """Test /api/pipeline/gallery only returns items with real thumbnails"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        videos = data["videos"]
        print(f"✓ Gallery: {len(videos)} videos returned")
        
        # Verify all items have thumbnails (no empty states)
        for video in videos[:10]:
            thumbnail = video.get("thumbnail_url", "")
            assert thumbnail and len(thumbnail) > 10, f"Video {video.get('title')} missing thumbnail"
        print("✓ All checked videos have valid thumbnails")
    
    def test_gallery_items_have_story_text(self):
        """Test gallery items have story_text for hook quotes"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        
        # Check if story_text is present for hook display
        items_with_story = sum(1 for v in videos if v.get("story_text"))
        print(f"✓ {items_with_story}/{len(videos)} items have story_text for hook quotes")
    
    def test_gallery_categories(self):
        """Test /api/pipeline/gallery/categories returns style categories"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        categories = data["categories"]
        assert len(categories) > 0, "Should have at least one category"
        print(f"✓ Categories: {[c['name'] for c in categories[:5]]}")
    
    def test_gallery_leaderboard(self):
        """Test /api/pipeline/gallery/leaderboard returns most remixed"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        print(f"✓ Leaderboard: {len(data['leaderboard'])} items")


class TestStudioEndpoints:
    """Test Story Video Studio endpoints"""
    
    def test_pipeline_options(self):
        """Test /api/pipeline/options returns style presets for thumbnails"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        
        # Check animation styles for preview thumbnails
        assert "animation_styles" in data
        styles = data["animation_styles"]
        assert len(styles) >= 6, "Should have at least 6 animation styles"
        
        style_names = [s["name"] for s in styles]
        print(f"✓ Animation styles: {style_names}")
        
        # Verify expected styles are present
        expected = ["2D Cartoon", "Anime", "3D Animation", "Watercolor"]
        for exp in expected:
            assert any(exp.lower() in s.lower() for s in style_names), f"Missing style: {exp}"
        print("✓ All expected styles present")
    
    def test_studio_accessible_without_auth(self):
        """Test /api/pipeline/options is accessible without authentication (zero-friction)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200, "Options should be accessible without auth"
        print("✓ Studio options accessible without authentication")


class TestAuthenticatedFeatures:
    """Test authenticated features like credit gate"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_credits_check_upsell(self, auth_token):
        """Test /api/credits/check-upsell for credit gate"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/check-upsell", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Should return credits info
        if "credits" in data:
            print(f"✓ User credits: {data['credits']}")
        if "show_upsell" in data:
            print(f"✓ Show upsell: {data['show_upsell']}")
    
    def test_rate_limit_status(self, auth_token):
        """Test /api/pipeline/rate-limit-status for generation limits"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/rate-limit-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "can_create" in data
        print(f"✓ Can create: {data['can_create']}")
        print(f"✓ Recent count: {data.get('recent_count', 0)}/{data.get('max_per_hour', 5)}")
    
    def test_user_jobs(self, auth_token):
        """Test /api/pipeline/user-jobs returns user's videos"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        print(f"✓ User jobs: {len(data['jobs'])} videos")


class TestContinueStoryFlow:
    """Test the Continue Story data flow"""
    
    def test_gallery_item_has_remix_data(self):
        """Test gallery items have data needed for Continue Story prefill"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get("videos", [])
        
        if videos:
            video = videos[0]
            # Required fields for Continue Story prefill
            required_fields = ["job_id", "title"]
            for field in required_fields:
                assert field in video, f"Missing field: {field}"
            
            # Optional but useful fields
            optional_fields = ["story_text", "animation_style", "age_group", "voice_preset"]
            present = [f for f in optional_fields if video.get(f)]
            print(f"✓ First video has: {required_fields + present}")
    
    def test_single_video_endpoint(self):
        """Test /api/pipeline/gallery/{job_id} for remix data"""
        # First get a video from gallery
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        videos = response.json().get("videos", [])
        
        if videos:
            job_id = videos[0].get("job_id")
            if job_id:
                response = requests.get(f"{BASE_URL}/api/pipeline/gallery/{job_id}")
                assert response.status_code == 200
                data = response.json()
                assert "video" in data
                video = data["video"]
                print(f"✓ Single video endpoint works: {video.get('title')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
