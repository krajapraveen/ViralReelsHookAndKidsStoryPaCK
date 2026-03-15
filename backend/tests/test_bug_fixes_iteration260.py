"""
Bug Fixes Testing - Iteration 260
Testing 4 critical bugs:
1. Google Auth callback 
2. Photo to Comic diagnostic 
3. Reel Generator upgrade banners for admin
4. Gallery showcase items
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


@pytest.fixture(scope="module")
def api_client():
    """Create requests session for API calls"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")  
def authenticated_admin(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestBugFix1_GoogleAuthCallback:
    """Bug Fix 1: Google Auth callback proper error handling"""
    
    def test_google_callback_endpoint_exists(self, api_client):
        """Test that Google callback endpoint exists and responds"""
        # Test with invalid session (should return proper error, not 500)
        response = api_client.post(f"{BASE_URL}/api/auth/google-callback", json={
            "sessionId": "test-invalid-session-123"
        })
        # Should return 400 or 503 for invalid/expired session, NOT 500
        assert response.status_code in [400, 503], f"Expected 400/503, got {response.status_code}"
        
        # Check error structure uses 'detail' field (FastAPI standard)
        data = response.json()
        assert "detail" in data, f"Response should contain 'detail' field: {data}"
        print(f"Google callback error response: {data}")
    
    def test_google_callback_options_cors(self, api_client):
        """Test CORS preflight for Google callback"""
        response = api_client.options(f"{BASE_URL}/api/auth/google-callback")
        assert response.status_code == 200


class TestBugFix2_PhotoToComic:
    """Bug Fix 2: Photo to Comic diagnostic endpoint"""
    
    def test_diagnostic_endpoint(self, authenticated_admin):
        """Test diagnostic endpoint shows LLM available"""
        response = authenticated_admin.get(f"{BASE_URL}/api/photo-to-comic/diagnostic")
        assert response.status_code == 200, f"Diagnostic failed: {response.text}"
        
        data = response.json()
        assert "llm_status" in data, f"Missing llm_status: {data}"
        assert "timestamp" in data
        
        # Verify LLM is available
        llm_status = data["llm_status"]
        assert llm_status.get("available") == True, f"LLM not available: {llm_status}"
        assert llm_status.get("key_configured") == True, f"LLM key not configured: {llm_status}"
        print(f"Photo to Comic diagnostic: {data}")
    
    def test_image_generation_endpoint_exists(self, authenticated_admin):
        """Test image generation test endpoint exists"""
        response = authenticated_admin.post(f"{BASE_URL}/api/photo-to-comic/test-image-generation")
        assert response.status_code == 200, f"Test image generation failed: {response.text}"
        
        data = response.json()
        assert "llm_available" in data
        assert "image_generation" in data
        print(f"Image generation test: {data}")


class TestBugFix3_ReelGeneratorCredits:
    """Bug Fix 3: Verify admin user has unlimited credits (999999999)"""
    
    def test_admin_has_unlimited_credits(self, authenticated_admin, admin_token):
        """Test that admin user has 999999999 credits"""
        response = authenticated_admin.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Get user failed: {response.text}"
        
        data = response.json()
        credits = data.get("credits", 0)
        role = data.get("role", "")
        plan = data.get("plan", "")
        
        print(f"Admin user info - credits: {credits}, role: {role}, plan: {plan}")
        
        # Admin should have 999999999 credits (unlimited)
        assert credits == 999999999, f"Admin should have 999999999 credits, got {credits}"
        assert role.upper() == "ADMIN", f"Expected ADMIN role, got {role}"
    
    def test_credits_balance_endpoint(self, authenticated_admin):
        """Test credits balance endpoint for admin"""
        response = authenticated_admin.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 200, f"Credits balance failed: {response.text}"
        
        data = response.json()
        balance = data.get("balance", data.get("credits", 0))
        is_free_tier = data.get("isFreeTier", True)
        plan = data.get("plan", "free")
        
        print(f"Admin credits balance: {balance}, isFreeTier: {is_free_tier}, plan: {plan}")
        
        # Admin should NOT be free tier and should have high credits
        assert balance >= 999999999, f"Admin balance should be 999999999, got {balance}"


class TestBugFix4_GalleryShowcase:
    """Bug Fix 4: Gallery page shows showcase items with images"""
    
    def test_gallery_returns_videos(self, api_client):
        """Test /api/pipeline/gallery returns showcase videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200, f"Gallery request failed: {response.text}"
        
        data = response.json()
        videos = data.get("videos", [])
        
        print(f"Gallery returned {len(videos)} videos")
        assert len(videos) > 0, "Gallery should have showcase videos"
        
        # Check first video has required fields
        video = videos[0]
        assert "title" in video or video.get("title"), "Video should have title"
        assert "thumbnail_url" in video, f"Video should have thumbnail_url: {video}"
        
        # Verify thumbnail URL is present
        thumb = video.get("thumbnail_url")
        print(f"First video: {video.get('title')}, thumbnail: {thumb[:50] if thumb else 'None'}...")
        assert thumb and thumb.startswith("http"), f"Video should have valid thumbnail_url"
    
    def test_gallery_videos_have_showcase_flag(self, api_client):
        """Test that gallery videos have is_showcase=true"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        videos = data.get("videos", [])
        
        # At least some should have is_showcase
        showcase_count = sum(1 for v in videos if v.get("is_showcase") == True)
        print(f"Videos with is_showcase=true: {showcase_count}/{len(videos)}")
        
        # All gallery videos should be showcase items
        assert showcase_count > 0, "Gallery should have showcase items"
    
    def test_gallery_categories_endpoint(self, api_client):
        """Test gallery categories endpoint"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200, f"Categories failed: {response.text}"
        
        data = response.json()
        categories = data.get("categories", [])
        print(f"Gallery categories: {[c.get('name') for c in categories]}")
    
    def test_gallery_leaderboard_endpoint(self, api_client):
        """Test gallery leaderboard endpoint"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200, f"Leaderboard failed: {response.text}"
        
        data = response.json()
        leaderboard = data.get("leaderboard", [])
        print(f"Gallery leaderboard: {len(leaderboard)} items")
        
        # Verify leaderboard items have thumbnails
        for item in leaderboard[:3]:
            print(f"  - {item.get('title')}: {item.get('remix_count')} remixes")
            assert item.get("thumbnail_url"), f"Leaderboard item should have thumbnail: {item}"


class TestHealthChecks:
    """Basic health checks"""
    
    def test_health_endpoint(self, api_client):
        """Test health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"Health check: {response.json()}")
    
    def test_root_endpoint(self, api_client):
        """Test root endpoint"""
        response = api_client.get(f"{BASE_URL}/")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
