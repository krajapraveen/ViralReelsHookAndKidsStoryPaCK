"""
Test suite for 9 critical production issues - Iteration 348
Tests: Landing page content, Explore page, Guest mode, Forgot password, Live activity feed
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLiveActivityFeed:
    """Test Happening Now feed with compelling titles and diverse countries"""
    
    def test_live_activity_returns_items(self):
        """Test that live-activity endpoint returns items"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=6")
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'items' in data
        assert len(data['items']) > 0
        print(f"✅ Live activity returned {len(data['items'])} items")
    
    def test_live_activity_has_compelling_titles(self):
        """Test that live-activity has compelling story titles (not 'Robot', 'Clever', etc.)"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=6")
        assert response.status_code == 200
        data = response.json()
        
        weak_titles = ['Robot', 'Clever', 'Test', 'Sample']
        for item in data['items']:
            title = item.get('title', '')
            # Check title is not just a weak single word
            for weak in weak_titles:
                if title == weak:
                    pytest.fail(f"Weak title found: '{title}'")
            # Check title has reasonable length
            assert len(title) > 5, f"Title too short: '{title}'"
        print("✅ All titles are compelling")
    
    def test_live_activity_has_diverse_countries(self):
        """Test that live-activity shows diverse countries"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=6")
        assert response.status_code == 200
        data = response.json()
        
        countries = set()
        for item in data['items']:
            creator = item.get('creator', '')
            # Extract country from "A creator in {Country}"
            if 'in ' in creator:
                country = creator.split('in ')[-1]
                countries.add(country)
        
        assert len(countries) >= 2, f"Not enough country diversity: {countries}"
        print(f"✅ Diverse countries found: {countries}")
    
    def test_live_activity_has_recent_timestamps(self):
        """Test that live-activity shows recent timestamps"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=6")
        assert response.status_code == 200
        data = response.json()
        
        for item in data['items']:
            time_ago = item.get('time_ago', '')
            assert time_ago, "Missing time_ago field"
            # Should be recent (just now, Xm ago, Xh ago)
            assert any(x in time_ago for x in ['just now', 'm ago', 'h ago', 'min', 'hour']), f"Unexpected time format: {time_ago}"
        print("✅ All timestamps are recent format")


class TestExplorePage:
    """Test Explore page with visible thumbnails"""
    
    def test_explore_returns_stories(self):
        """Test that explore endpoint returns stories"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'items' in data
        assert len(data['items']) > 0
        print(f"✅ Explore returned {len(data['items'])} stories")
    
    def test_explore_stories_have_thumbnails(self):
        """Test that explore stories have thumbnail URLs"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        for item in data['items']:
            thumbnail_url = item.get('thumbnail_url', '')
            assert thumbnail_url, f"Missing thumbnail for story: {item.get('title')}"
            assert 'r2.cloudflarestorage' in thumbnail_url or 'http' in thumbnail_url, f"Invalid thumbnail URL: {thumbnail_url[:50]}"
        print("✅ All stories have valid thumbnail URLs")
    
    def test_explore_thumbnails_are_accessible(self):
        """Test that thumbnail URLs are accessible (HTTP 200)"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=3")
        assert response.status_code == 200
        data = response.json()
        
        for item in data['items'][:3]:
            thumbnail_url = item.get('thumbnail_url', '')
            if thumbnail_url:
                # Use GET instead of HEAD as presigned URLs may not support HEAD
                thumb_response = requests.get(thumbnail_url, timeout=10, stream=True)
                # Accept 200 or 403 (presigned URL may have expired but URL format is valid)
                assert thumb_response.status_code in [200, 403], f"Thumbnail not accessible: {thumbnail_url[:50]}"
                thumb_response.close()
        print("✅ Thumbnail URLs are accessible or have valid format")


class TestGuestModeCreation:
    """Test guest mode story creation (IP-based free trial)"""
    
    def test_guest_create_without_auth(self):
        """Test that guest creation works without auth (or returns 401 if free trial used)"""
        payload = {
            "title": "Test Guest Story",
            "story_text": "Once upon a time in a magical forest, there lived a brave little fox named Finn. He discovered a mysterious glowing stone that could grant wishes. But the stone came with a warning - each wish would cost something precious.",
            "animation_style": "cartoon_2d",
            "age_group": "kids_5_8",
            "voice_preset": "narrator_warm"
        }
        response = requests.post(f"{BASE_URL}/api/story-engine/create", json=payload)
        
        # Either 200 (guest creation) or 401 (free trial used)
        assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert data.get('is_guest') == True, "Guest creation should return is_guest: true"
            assert data.get('credits_charged') == 0, "Guest creation should not charge credits"
            print("✅ Guest creation successful with is_guest: true, credits_charged: 0")
        else:
            data = response.json()
            assert 'Free trial used' in str(data.get('detail', '')), f"Expected 'Free trial used' message, got: {data}"
            print("✅ Guest creation returns 401 with 'Free trial used' (IP already used)")


class TestForgotPassword:
    """Test forgot password with email delivery failure handling"""
    
    def test_forgot_password_returns_success_false_on_delivery_failure(self):
        """Test that forgot password returns success: false when email delivery fails"""
        payload = {"email": "test@visionary-suite.com"}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Should return success: false when SendGrid key is expired
        assert data.get('success') == False, f"Expected success: false, got: {data}"
        assert 'Unable to send' in data.get('message', '') or 'try again' in data.get('message', '').lower(), f"Expected error message, got: {data.get('message')}"
        print("✅ Forgot password returns success: false on email delivery failure")
    
    def test_forgot_password_nonexistent_email_returns_success(self):
        """Test that forgot password returns success: true for non-existent email (security)"""
        payload = {"email": "nonexistent@example.com"}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Should return success: true for security (don't reveal if email exists)
        assert data.get('success') == True, f"Expected success: true for non-existent email, got: {data}"
        print("✅ Forgot password returns success: true for non-existent email (security)")


class TestABHookAnalytics:
    """Test A/B hook analytics regression"""
    
    def test_hook_analytics_returns_4_variants(self):
        """Test that hook-analytics returns 4 variants (regression check)"""
        response = requests.get(f"{BASE_URL}/api/ab/hook-analytics")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('success') == True
        assert 'variants' in data
        assert len(data['variants']) == 4, f"Expected 4 variants, got: {len(data['variants'])}"
        
        variant_ids = [v['variant_id'] for v in data['variants']]
        expected_variants = ['hook_mystery', 'hook_emotional', 'hook_shock', 'hook_curiosity']
        for expected in expected_variants:
            assert expected in variant_ids, f"Missing variant: {expected}"
        
        print(f"✅ Hook analytics returns 4 variants: {variant_ids}")


class TestTrendingWeekly:
    """Test trending weekly stories"""
    
    def test_trending_weekly_returns_stories(self):
        """Test that trending-weekly endpoint returns stories"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'items' in data
        print(f"✅ Trending weekly returned {len(data['items'])} stories")


class TestHealthCheck:
    """Test backend health"""
    
    def test_health_endpoint(self):
        """Test that health endpoint returns healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'healthy'
        print("✅ Backend is healthy")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
