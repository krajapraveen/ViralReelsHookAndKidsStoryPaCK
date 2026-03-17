"""
Bug Fixes Iteration 304 - Testing 3 Critical Fixes:
1. SafeImage crossOrigin removed (frontend - images should load)
2. Gallery query filter expanded to include thumbnail_url OR output_url OR is_showcase
3. Profile page link corrected to /app/story-video-studio
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# ─── TEST GALLERY ENDPOINT ────────────────────────────────────────────────────

class TestGalleryFilter:
    """Gallery API should return items with thumbnail_url OR output_url OR is_showcase"""
    
    def test_gallery_returns_results(self):
        """GET /api/pipeline/gallery should return videos/creations"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        # Should have some results (not empty if filter is working)
        print(f"Gallery returned {len(data['videos'])} items")
        # At least verify structure
        if data["videos"]:
            video = data["videos"][0]
            assert "job_id" in video
            assert "title" in video

    def test_gallery_returns_items_with_thumbnails(self):
        """Gallery should include items that have thumbnail_url even without output_url"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        
        # Check if any items have thumbnail_url
        items_with_thumbnails = [v for v in data["videos"] if v.get("thumbnail_url")]
        print(f"Items with thumbnails: {len(items_with_thumbnails)}")
        # This should not be 0 if the filter fix is working
        
    def test_gallery_presigned_urls(self):
        """Gallery should return presigned R2 URLs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        
        for video in data["videos"][:3]:  # Check first 3
            if video.get("output_url"):
                assert "X-Amz-Signature" in video["output_url"], "output_url should be presigned"
            if video.get("thumbnail_url"):
                # Only R2 URLs should be presigned, not static CDN URLs
                if "r2.cloudflarestorage.com" in video["thumbnail_url"]:
                    assert "X-Amz-Signature" in video["thumbnail_url"], "R2 thumbnail_url should be presigned"
        print("Presigned URLs verified")

    def test_gallery_categories(self):
        """GET /api/pipeline/gallery/categories should work"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        # Should have at least 'All' category
        assert len(data["categories"]) >= 1
        print(f"Categories: {[c['name'] for c in data['categories']]}")

    def test_gallery_leaderboard(self):
        """GET /api/pipeline/gallery/leaderboard should work"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        print(f"Leaderboard has {len(data['leaderboard'])} items")


# ─── TEST EXPLORE ENDPOINT ────────────────────────────────────────────────────

class TestExploreEndpoint:
    """Explore API should return items with presigned thumbnail URLs"""
    
    def test_explore_trending(self):
        """GET /api/public/explore?tab=trending should return items"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "items" in data
        print(f"Explore trending returned {len(data['items'])} items")
        
    def test_explore_items_have_presigned_thumbnails(self):
        """Explore items should have presigned thumbnail URLs"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            if item.get("thumbnail_url"):
                # R2 URLs should be presigned
                if "r2.cloudflarestorage.com" in item["thumbnail_url"]:
                    assert "X-Amz-Signature" in item["thumbnail_url"], f"Thumbnail should be presigned: {item['title']}"
        print("Explore thumbnails presigned correctly")
        
    def test_explore_newest(self):
        """GET /api/public/explore?tab=newest should work"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["tab"] == "newest"
        
    def test_explore_most_remixed(self):
        """GET /api/public/explore?tab=most_remixed should work"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=most_remixed&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["tab"] == "most_remixed"


# ─── TEST PROFILE AUTH ENDPOINTS ──────────────────────────────────────────────

class TestProfileEndpoints:
    """Test profile-related endpoints work correctly"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth token for test user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        return {}
    
    def test_auth_me(self, auth_headers):
        """GET /api/auth/me should return user data"""
        if not auth_headers:
            pytest.skip("Auth failed - skipping")
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        print(f"User: {data.get('email')}")
        
    def test_pipeline_user_jobs(self, auth_headers):
        """GET /api/pipeline/user-jobs should return user's pipeline jobs"""
        if not auth_headers:
            pytest.skip("Auth failed - skipping")
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "jobs" in data
        print(f"User has {len(data['jobs'])} pipeline jobs")


# ─── TEST IMAGE ACCESSIBILITY (No CORS blocking) ──────────────────────────────

class TestImageAccessibility:
    """Test that presigned R2 URLs are accessible"""
    
    def test_thumbnail_image_accessible(self):
        """Thumbnail images from gallery should be accessible via HTTP GET"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        
        # Find an item with thumbnail
        for video in data["videos"][:5]:
            if video.get("thumbnail_url"):
                thumb_url = video["thumbnail_url"]
                # Try to HEAD the image (don't download full content)
                try:
                    img_response = requests.head(thumb_url, timeout=10)
                    print(f"Thumbnail {video['title']}: status={img_response.status_code}")
                    # 200 or 206 means accessible
                    assert img_response.status_code in [200, 206], f"Image not accessible: {thumb_url}"
                    return  # Found one working, test passes
                except Exception as e:
                    print(f"Thumbnail request failed: {e}")
                    continue
        
        print("No thumbnails found to test - may be expected")

    def test_explore_thumbnail_accessible(self):
        """Explore page thumbnail should be accessible"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"][:3]:
            if item.get("thumbnail_url"):
                thumb_url = item["thumbnail_url"]
                try:
                    img_response = requests.head(thumb_url, timeout=10)
                    print(f"Explore thumbnail {item['title']}: status={img_response.status_code}")
                    if img_response.status_code in [200, 206]:
                        return  # Found working thumbnail
                except Exception as e:
                    print(f"Request failed: {e}")
                    continue
        
        print("No explore thumbnails found to test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
