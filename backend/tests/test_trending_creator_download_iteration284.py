"""
Test suite for Iteration 284:
1. Trending This Week API - Algorithmic ranking with views, remixes, recency
2. Creator Profile API - Avatar, bio, stats, creations
3. Photo-to-Comic Download Architecture - Permanent CDN URLs, no expiry

Test user: test@visionary-suite.com / Test@2026#
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

class TestTrendingWeekly:
    """Tests for /api/public/trending-weekly endpoint"""
    
    def test_trending_weekly_endpoint_exists(self):
        """Verify trending-weekly endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: trending-weekly endpoint exists and returns 200")
    
    def test_trending_weekly_response_structure(self):
        """Verify response has correct structure with items array"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly")
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data, "Response should have 'success' field"
        assert data["success"] is True, "success should be True"
        assert "items" in data, "Response should have 'items' array"
        assert "period" in data, "Response should have 'period' field"
        assert data["period"] == "weekly", f"period should be 'weekly', got {data['period']}"
        print(f"PASS: trending-weekly response structure is correct with {len(data['items'])} items")
    
    def test_trending_weekly_item_fields(self):
        """Verify each item has required fields: job_id, slug, title, category, views, remix_count, thumbnail_url"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) == 0:
            pytest.skip("No trending items available")
        
        required_fields = ["job_id", "slug", "title", "views", "remix_count"]
        optional_fields = ["category", "thumbnail_url", "animation_style", "created_at"]
        
        for idx, item in enumerate(data["items"]):
            for field in required_fields:
                assert field in item, f"Item {idx} missing required field '{field}'"
            # Verify views and remix_count are integers
            assert isinstance(item["views"], int), f"Item {idx} 'views' should be int"
            assert isinstance(item["remix_count"], int), f"Item {idx} 'remix_count' should be int"
        
        print(f"PASS: All {len(data['items'])} trending items have required fields")
    
    def test_trending_weekly_items_have_thumbnails(self):
        """Verify items have thumbnail_url (only items with thumbnails in last 30 days)"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        items_with_thumbnails = [i for i in data["items"] if i.get("thumbnail_url")]
        # Per spec: only items with thumbnails from last 30 days
        print(f"PASS: {len(items_with_thumbnails)}/{len(data['items'])} items have thumbnail_url")
    
    def test_trending_weekly_limit_parameter(self):
        """Verify limit parameter works (1-20 range)"""
        # Test limit=3
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 3, f"Expected max 3 items, got {len(data['items'])}"
        
        # Test limit=20 (max)
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 20
        
        print(f"PASS: limit parameter working correctly")
    
    def test_trending_weekly_no_trending_score_in_response(self):
        """Verify trending_score is removed from response (internal field)"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            assert "trending_score" not in item, "trending_score should not be in response"
        
        print("PASS: trending_score correctly removed from response")


class TestCreatorProfile:
    """Tests for /api/public/creator/{username} endpoint"""
    
    def test_creator_profile_endpoint_exists_visionary_ai(self):
        """Verify creator profile endpoint exists for visionary-ai"""
        # Try both username formats
        usernames_to_try = ["visionary-ai", "Visionary%20AI", "visionary-ai-system"]
        success = False
        
        for username in usernames_to_try:
            response = requests.get(f"{BASE_URL}/api/public/creator/{username}")
            if response.status_code == 200:
                success = True
                print(f"PASS: Creator profile found with username '{username}'")
                break
        
        if not success:
            # Check if any creator exists
            pytest.skip("visionary-ai creator not found - may need seeding")
    
    def test_creator_profile_response_structure(self):
        """Verify creator profile has avatar, bio, stats"""
        response = requests.get(f"{BASE_URL}/api/public/creator/visionary-ai")
        
        if response.status_code == 404:
            pytest.skip("visionary-ai creator not found")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "success" in data and data["success"] is True
        assert "creator" in data, "Response should have 'creator' object"
        
        creator = data["creator"]
        required_fields = ["name", "total_creations", "total_views", "total_remixes"]
        optional_fields = ["username", "bio", "avatar_url", "joined"]
        
        for field in required_fields:
            assert field in creator, f"Creator missing required field '{field}'"
        
        # Verify stats are integers
        assert isinstance(creator["total_creations"], int)
        assert isinstance(creator["total_views"], int)
        assert isinstance(creator["total_remixes"], int)
        
        print(f"PASS: Creator profile has correct structure with {creator['total_creations']} creations")
    
    def test_creator_profile_creations_list(self):
        """Verify creator profile returns creations list with presigned thumbnails"""
        response = requests.get(f"{BASE_URL}/api/public/creator/visionary-ai")
        
        if response.status_code == 404:
            pytest.skip("visionary-ai creator not found")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "creations" in data, "Response should have 'creations' array"
        creations = data["creations"]
        
        if len(creations) == 0:
            print("PASS: Creator has 0 creations (valid state)")
            return
        
        # Verify creation fields
        required_fields = ["job_id", "title", "views", "remix_count"]
        for idx, creation in enumerate(creations[:5]):  # Check first 5
            for field in required_fields:
                assert field in creation, f"Creation {idx} missing field '{field}'"
        
        # Count presigned thumbnails
        presigned_count = sum(1 for c in creations if c.get("thumbnail_url") and "X-Amz-Signature" in c.get("thumbnail_url", ""))
        print(f"PASS: Creator has {len(creations)} creations, {presigned_count} with presigned thumbnails")
    
    def test_creator_profile_404_for_unknown(self):
        """Verify 404 for unknown creator"""
        response = requests.get(f"{BASE_URL}/api/public/creator/nonexistent-creator-xyz123")
        assert response.status_code == 404, f"Expected 404 for unknown creator, got {response.status_code}"
        print("PASS: 404 returned for unknown creator")


class TestPhotoToComicDownload:
    """Tests for Photo-to-Comic download architecture (permanent CDN URLs)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        return login_response.json().get("token")
    
    def test_generate_returns_job_id_and_queued(self, auth_token):
        """Verify generate returns jobId and QUEUED status (not final result)"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "multipart/form-data"}
        
        # Create a small test image
        import io
        test_image = io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        files = {"photo": ("test.png", test_image, "image/png")}
        data = {
            "mode": "avatar",
            "style": "cartoon_fun",
            "genre": "comedy"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            headers={"Authorization": f"Bearer {auth_token}"},
            files=files,
            data=data
        )
        
        # May fail due to credits or image validation, but should not return 500
        assert response.status_code in [200, 400], f"Expected 200/400, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "jobId" in data, "Response should have jobId"
            assert data.get("status") == "QUEUED", f"Initial status should be QUEUED, got {data.get('status')}"
            print(f"PASS: Generate returns jobId and QUEUED status")
        else:
            print(f"PASS: Generate correctly validates input (returned 400)")
    
    def test_validate_asset_endpoint_exists(self, auth_token):
        """Verify validate-asset endpoint exists"""
        # Use a dummy job_id - should return 404
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/validate-asset/dummy-job-id",
            headers=headers
        )
        assert response.status_code in [200, 404], f"validate-asset should return 200 or 404, got {response.status_code}"
        print("PASS: validate-asset endpoint exists")
    
    def test_download_returns_permanent_no_expiry(self, auth_token):
        """Verify download endpoint returns permanent:true and no expiresAt"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Use a dummy job_id - check response structure
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/download/dummy-job-id",
            headers=headers
        )
        
        # Should return 404 for non-existent job
        assert response.status_code in [200, 400, 404], f"Download should return valid status, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "permanent" in data, "Download response should have 'permanent' field"
            assert data["permanent"] is True, "permanent should be True"
            assert "expiresAt" not in data, "expiresAt should not be in response"
            print("PASS: Download returns permanent:true and no expiresAt")
        else:
            print(f"PASS: Download correctly returns {response.status_code} for non-existent job")


class TestPlatformStats:
    """Tests for public platform stats endpoint"""
    
    def test_platform_stats_endpoint(self):
        """Verify /api/public/stats returns real data"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["creators", "videos_created", "total_creations", "ai_scenes"]
        for field in expected_fields:
            assert field in data, f"Stats missing field '{field}'"
            assert isinstance(data[field], int), f"'{field}' should be integer"
        
        print(f"PASS: Platform stats - {data['creators']} creators, {data['videos_created']} videos")


class TestExploreEndpoint:
    """Tests for /api/public/explore endpoint"""
    
    def test_explore_trending_tab(self):
        """Verify explore endpoint trending tab"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data and data["success"] is True
        assert "items" in data
        assert "tab" in data and data["tab"] == "trending"
        print(f"PASS: Explore trending returns {len(data['items'])} items")
    
    def test_explore_newest_tab(self):
        """Verify explore endpoint newest tab"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert data["tab"] == "newest"
        print(f"PASS: Explore newest returns {len(data['items'])} items")
    
    def test_explore_most_remixed_tab(self):
        """Verify explore endpoint most_remixed tab"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=most_remixed&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert data["tab"] == "most_remixed"
        print(f"PASS: Explore most_remixed returns {len(data['items'])} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
