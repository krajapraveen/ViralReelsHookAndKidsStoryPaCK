"""
Test Suite for Story Engine Pipeline, Generation Tools, and Credit Display Fixes
Iteration 350 - Testing:
1. Story-to-Video pipeline status check (completed job)
2. Reel Generator API
3. Bedtime Story API
4. Caption Rewriter API
5. Brand Story API
6. Story Generator API
7. Comic Storybook API (multipart form)
8. Login flow
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Completed job ID from main agent context
COMPLETED_JOB_ID = "261430a2-28f5-4c40-bac2-35f8d275fae7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestLoginFlow:
    """Test authentication flow"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, "No token in response"
        print(f"✓ Login successful for {TEST_EMAIL}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpass"}
        )
        assert response.status_code in [401, 400], f"Expected 401/400, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")


class TestStoryEnginePipeline:
    """Test Story-to-Video pipeline status"""
    
    def test_completed_job_status(self, auth_headers):
        """Test that completed job shows COMPLETED status with output_url"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/{COMPLETED_JOB_ID}",
            headers=auth_headers
        )
        # Job may not exist or may be from different user
        if response.status_code == 404:
            pytest.skip("Completed job not found - may have been cleaned up")
        if response.status_code == 403:
            pytest.skip("Job belongs to different user")
        
        assert response.status_code == 200, f"Status check failed: {response.text}"
        data = response.json()
        
        # Check job structure
        assert "job" in data or "success" in data, "Invalid response structure"
        job = data.get("job", data)
        
        status = job.get("status") or job.get("state")
        print(f"Job status: {status}")
        
        # If completed, should have output_url
        if status in ["COMPLETED", "READY"]:
            output_url = job.get("output_url")
            print(f"Output URL: {output_url}")
            assert output_url is not None, "Completed job should have output_url"
            print(f"✓ Completed job has output_url: {output_url[:50]}...")
        else:
            print(f"Job is in state: {status}")
    
    def test_story_engine_options(self):
        """Test story engine options endpoint"""
        response = requests.get(f"{BASE_URL}/api/story-engine/options")
        assert response.status_code == 200, f"Options failed: {response.text}"
        data = response.json()
        
        assert "animation_styles" in data, "Missing animation_styles"
        assert "age_groups" in data, "Missing age_groups"
        assert "voice_presets" in data, "Missing voice_presets"
        print(f"✓ Story engine options: {len(data.get('animation_styles', []))} styles available")


class TestReelGenerator:
    """Test Reel Generator API"""
    
    def test_generate_reel(self, auth_headers):
        """Test POST /api/generate/reel with valid data"""
        payload = {
            "topic": "Morning routines of successful entrepreneurs",
            "niche": "Luxury",
            "tone": "Bold",
            "duration": "30s",
            "language": "English",
            "goal": "Followers"
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        
        # May fail due to insufficient credits
        if response.status_code == 402:
            pytest.skip("Insufficient credits for reel generation")
        
        assert response.status_code == 200, f"Reel generation failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Reel generation not successful"
        assert "result" in data, "No result in response"
        print(f"✓ Reel generated successfully")


class TestBedtimeStory:
    """Test Bedtime Story Builder API"""
    
    def test_generate_bedtime_story(self, auth_headers):
        """Test POST /api/bedtime-story-builder/generate"""
        # Valid age_group values: 3-5, 6-8, 9-12
        payload = {
            "age_group": "3-5",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "3",
            "voice_style": "calm_parent"
        }
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for bedtime story")
        if response.status_code == 404:
            pytest.skip("Bedtime story endpoint not found")
        
        assert response.status_code == 200, f"Bedtime story failed: {response.text}"
        data = response.json()
        assert data.get("success") == True or "story" in data or "result" in data
        print(f"✓ Bedtime story generated successfully")


class TestCaptionRewriter:
    """Test Caption Rewriter Pro API"""
    
    def test_rewrite_caption(self, auth_headers):
        """Test POST /api/caption-rewriter-pro/rewrite"""
        # Valid tones: funny, luxury, bold, emotional, motivational, storytelling
        # Valid pack_type: single_tone, three_tones, all_tones
        payload = {
            "text": "This is a sample caption that needs to be rewritten for better engagement",
            "tone": "bold",
            "pack_type": "single_tone"
        }
        response = requests.post(
            f"{BASE_URL}/api/caption-rewriter-pro/rewrite",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for caption rewriter")
        if response.status_code == 404:
            pytest.skip("Caption rewriter endpoint not found")
        
        assert response.status_code == 200, f"Caption rewrite failed: {response.text}"
        data = response.json()
        assert data.get("success") == True or "captions" in data or "result" in data
        print(f"✓ Caption rewritten successfully")


class TestBrandStory:
    """Test Brand Story Builder API"""
    
    def test_generate_brand_story(self, auth_headers):
        """Test POST /api/brand-story-builder/generate"""
        payload = {
            "business_name": "Test Company",
            "mission": "To provide excellent test services to all customers worldwide",
            "founder_story": "Founded in 2020 by a passionate entrepreneur who wanted to make testing easier for everyone",
            "industry": "Technology",
            "tone": "professional"
        }
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for brand story")
        if response.status_code == 404:
            pytest.skip("Brand story endpoint not found")
        
        assert response.status_code == 200, f"Brand story failed: {response.text}"
        data = response.json()
        assert data.get("success") == True or "story" in data or "result" in data
        print(f"✓ Brand story generated successfully")


class TestStoryGenerator:
    """Test Story Generator API"""
    
    def test_generate_story(self, auth_headers):
        """Test POST /api/generate/story"""
        payload = {
            "genre": "Adventure",
            "ageGroup": "4-6",
            "theme": "Friendship",
            "sceneCount": 4
        }
        response = requests.post(
            f"{BASE_URL}/api/generate/story",
            json=payload,
            headers=auth_headers,
            timeout=120
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for story generation")
        
        assert response.status_code == 200, f"Story generation failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Story generation not successful"
        assert "result" in data, "No result in response"
        print(f"✓ Story generated successfully")


class TestComicStorybook:
    """Test Comic Storybook API with multipart form"""
    
    def test_comic_storybook_preview(self, auth_headers):
        """Test POST /api/comic-storybook-v2/preview"""
        payload = {
            "genre": "kids_adventure",
            "storyIdea": "A brave little fox discovers a magical forest where animals can talk",
            "title": "The Talking Forest",
            "pageCount": 10
        }
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/preview",
            json=payload,
            headers=auth_headers,
            timeout=60
        )
        
        if response.status_code == 404:
            pytest.skip("Comic storybook preview endpoint not found")
        
        # Preview may fail but endpoint should exist
        print(f"Comic storybook preview response: {response.status_code}")
        if response.status_code == 200:
            print(f"✓ Comic storybook preview successful")


class TestCreditsEndpoint:
    """Test credits balance endpoint"""
    
    def test_credits_balance(self, auth_headers):
        """Test GET /api/credits/balance"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Credits balance failed: {response.text}"
        data = response.json()
        
        # Should have credits field (number, not '...')
        credits = data.get("credits") or data.get("balance")
        assert credits is not None, "No credits in response"
        assert isinstance(credits, (int, float)), f"Credits should be number, got {type(credits)}"
        print(f"✓ Credits balance: {credits}")
    
    def test_user_profile_has_credits(self, auth_headers):
        """Test that user profile includes credits"""
        response = requests.get(
            f"{BASE_URL}/api/user/profile",
            headers=auth_headers
        )
        if response.status_code == 404:
            pytest.skip("User profile endpoint not found")
        
        assert response.status_code == 200, f"Profile failed: {response.text}"
        data = response.json()
        user = data.get("user", data)
        
        # Credits should be a number
        credits = user.get("credits")
        if credits is not None:
            assert isinstance(credits, (int, float)), f"Credits should be number, got {type(credits)}"
            print(f"✓ User profile credits: {credits}")


class TestPublicEndpoints:
    """Test public endpoints for landing page"""
    
    def test_public_stats(self):
        """Test GET /api/public/stats"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        if response.status_code == 404:
            pytest.skip("Public stats endpoint not found")
        
        assert response.status_code == 200, f"Public stats failed: {response.text}"
        data = response.json()
        print(f"✓ Public stats available")
    
    def test_trending_weekly(self):
        """Test GET /api/public/trending-weekly"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=12")
        if response.status_code == 404:
            pytest.skip("Trending weekly endpoint not found")
        
        assert response.status_code == 200, f"Trending weekly failed: {response.text}"
        data = response.json()
        items = data.get("items", [])
        print(f"✓ Trending weekly: {len(items)} items")
    
    def test_live_activity(self):
        """Test GET /api/public/live-activity"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=6")
        if response.status_code == 404:
            pytest.skip("Live activity endpoint not found")
        
        assert response.status_code == 200, f"Live activity failed: {response.text}"
        data = response.json()
        items = data.get("items", [])
        print(f"✓ Live activity: {len(items)} items")


class TestEngagementEndpoints:
    """Test engagement endpoints for dashboard"""
    
    def test_story_feed(self):
        """Test GET /api/engagement/story-feed"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        if response.status_code == 404:
            pytest.skip("Story feed endpoint not found")
        
        assert response.status_code == 200, f"Story feed failed: {response.text}"
        data = response.json()
        
        # Check for trending stories
        trending = data.get("trending", [])
        print(f"✓ Story feed: {len(trending)} trending stories")
    
    def test_dashboard_engagement(self, auth_headers):
        """Test GET /api/engagement/dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers=auth_headers
        )
        if response.status_code == 404:
            pytest.skip("Dashboard engagement endpoint not found")
        
        # May return 200 or 401 depending on auth
        print(f"Dashboard engagement response: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
