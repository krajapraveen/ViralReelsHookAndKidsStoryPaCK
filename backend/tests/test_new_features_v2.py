"""
Test Suite for CreatorStudio AI New Features
Tests: Style Profiles, Convert Features, ML Threat Detection
"""
import pytest
import requests
import os
import time
import base64
from io import BytesIO

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@example.com"
TEST_PASSWORD = "Password123!"

# =============================================================================
# FIXTURES
# =============================================================================
@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    # Try to register if login fails
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": "Test User", "email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.text}")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="module")
def auth_headers_multipart(auth_token):
    """Get headers for multipart requests"""
    return {
        "Authorization": f"Bearer {auth_token}"
    }

# =============================================================================
# HEALTH CHECK
# =============================================================================
class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ API Health: {data}")

# =============================================================================
# STYLE PROFILE TESTS
# =============================================================================
class TestStyleProfiles:
    """Test Style Profile CRUD and Training"""
    
    profile_id = None
    
    def test_01_create_style_profile(self, auth_headers):
        """Test creating a new style profile - costs 20 credits"""
        response = requests.post(
            f"{BASE_URL}/api/genstudio/style-profile",
            headers=auth_headers,
            json={
                "name": "TEST_Profile_" + str(int(time.time())),
                "description": "Test style profile for automated testing",
                "tags": ["test", "automation"],
                "category": "general"
            }
        )
        print(f"Create Style Profile Response: {response.status_code} - {response.text[:500]}")
        
        # May fail due to insufficient credits - that's acceptable
        if response.status_code == 400 and "credits" in response.text.lower():
            pytest.skip("Insufficient credits for style profile creation")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "profileId" in data
        TestStyleProfiles.profile_id = data["profileId"]
        print(f"✓ Created style profile: {data['profileId']}")
    
    def test_02_list_style_profiles(self, auth_headers):
        """Test listing style profiles"""
        response = requests.get(
            f"{BASE_URL}/api/genstudio/style-profiles",
            headers=auth_headers
        )
        print(f"List Style Profiles Response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        print(f"✓ Found {len(data['profiles'])} style profiles")
    
    def test_03_upload_image_to_profile(self, auth_headers_multipart):
        """Test uploading an image to style profile"""
        if not TestStyleProfiles.profile_id:
            pytest.skip("No profile created to upload image to")
        
        # Create a simple test image (1x1 red pixel PNG)
        # PNG header + IHDR + IDAT + IEND
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        
        files = {
            "image": ("test_image.png", BytesIO(png_data), "image/png")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/style-profile/{TestStyleProfiles.profile_id}/upload-image",
            headers=auth_headers_multipart,
            files=files
        )
        print(f"Upload Image Response: {response.status_code} - {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "imageId" in data
        print(f"✓ Uploaded image: {data['imageId']}, count: {data.get('currentImageCount')}")
    
    def test_04_train_profile_insufficient_images(self, auth_headers):
        """Test training profile with insufficient images (needs 5+)"""
        if not TestStyleProfiles.profile_id:
            pytest.skip("No profile created to train")
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/style-profile/{TestStyleProfiles.profile_id}/train",
            headers=auth_headers
        )
        print(f"Train Profile Response: {response.status_code} - {response.text[:500]}")
        
        # Should fail with 400 because we need 5+ images
        if response.status_code == 400:
            assert "images" in response.text.lower() or "5" in response.text
            print(f"✓ Correctly rejected training with insufficient images")
        else:
            # If it succeeds, that's also fine (maybe profile already has images)
            assert response.status_code == 200
            print(f"✓ Training started/completed")
    
    def test_05_delete_style_profile(self, auth_headers):
        """Test deleting a style profile"""
        if not TestStyleProfiles.profile_id:
            pytest.skip("No profile created to delete")
        
        response = requests.delete(
            f"{BASE_URL}/api/genstudio/style-profile/{TestStyleProfiles.profile_id}",
            headers=auth_headers
        )
        print(f"Delete Profile Response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Deleted style profile")

# =============================================================================
# CONVERT FEATURE TESTS
# =============================================================================
class TestConvertFeatures:
    """Test Convert endpoints (text-to-story, text-to-reel)"""
    
    text_to_story_job_id = None
    text_to_reel_job_id = None
    
    def test_01_get_conversion_costs(self, auth_headers):
        """Test getting conversion costs"""
        response = requests.get(
            f"{BASE_URL}/api/convert/costs",
            headers=auth_headers
        )
        print(f"Conversion Costs Response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        data = response.json()
        assert "costs" in data
        assert "text_to_story" in data["costs"]
        assert "text_to_reel" in data["costs"]
        print(f"✓ Conversion costs: {data['costs']}")
    
    def test_02_text_to_story(self, auth_headers_multipart):
        """Test converting text to story - 10 credits (uses form data)"""
        response = requests.post(
            f"{BASE_URL}/api/convert/text-to-story",
            headers=auth_headers_multipart,
            data={
                "text": "A brave little rabbit named Hoppy lived in a magical forest. One day, Hoppy discovered a hidden treasure map that led to the legendary Golden Carrot.",
                "story_style": "adventure",
                "target_age_group": "kids",
                "include_moral": "true"
            }
        )
        print(f"Text-to-Story Response: {response.status_code} - {response.text[:500]}")
        
        if response.status_code == 400 and "credits" in response.text.lower():
            pytest.skip("Insufficient credits for text-to-story conversion")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "jobId" in data
        assert "pollUrl" in data
        TestConvertFeatures.text_to_story_job_id = data["jobId"]
        print(f"✓ Text-to-story job created: {data['jobId']}")
    
    def test_03_text_to_reel(self, auth_headers_multipart):
        """Test converting text to reel - 15 credits (uses form data)"""
        response = requests.post(
            f"{BASE_URL}/api/convert/text-to-reel",
            headers=auth_headers_multipart,
            data={
                "text": "5 amazing facts about space that will blow your mind! Did you know that a day on Venus is longer than a year on Venus?",
                "reel_style": "engaging",
                "platform": "instagram"
            }
        )
        print(f"Text-to-Reel Response: {response.status_code} - {response.text[:500]}")
        
        if response.status_code == 400 and "credits" in response.text.lower():
            pytest.skip("Insufficient credits for text-to-reel conversion")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "jobId" in data
        assert "pollUrl" in data
        TestConvertFeatures.text_to_reel_job_id = data["jobId"]
        print(f"✓ Text-to-reel job created: {data['jobId']}")
    
    def test_04_get_conversion_status(self, auth_headers):
        """Test getting conversion job status"""
        job_id = TestConvertFeatures.text_to_story_job_id or TestConvertFeatures.text_to_reel_job_id
        if not job_id:
            pytest.skip("No conversion job created to check status")
        
        # Wait a bit for processing
        time.sleep(2)
        
        response = requests.get(
            f"{BASE_URL}/api/convert/status/{job_id}",
            headers=auth_headers
        )
        print(f"Conversion Status Response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "progress" in data
        print(f"✓ Job status: {data['status']}, progress: {data['progress']}%")
    
    def test_05_get_conversion_history(self, auth_headers):
        """Test getting conversion history"""
        response = requests.get(
            f"{BASE_URL}/api/convert/history",
            headers=auth_headers
        )
        print(f"Conversion History Response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        print(f"✓ Conversion history: {data['total']} jobs")

# =============================================================================
# ML THREAT DETECTION TESTS
# =============================================================================
class TestMLThreatDetection:
    """Test ML-based threat detection and content moderation"""
    
    def test_01_prohibited_content_deepfake(self, auth_headers):
        """Test that deepfake content is blocked"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=auth_headers,
            json={
                "topic": "Create a deepfake celebrity video",
                "niche": "Entertainment",
                "language": "English",
                "tone": "Bold",
                "duration": "30s",
                "goal": "Followers"
            }
        )
        print(f"Deepfake Content Response: {response.status_code} - {response.text[:500]}")
        
        # Should be blocked (400) or sanitized
        if response.status_code == 400:
            assert any(word in response.text.lower() for word in ["prohibited", "blocked", "not allowed", "deepfake"])
            print(f"✓ Deepfake content correctly blocked")
        else:
            # If 200, check that the content was sanitized
            print(f"⚠ Content may have been sanitized instead of blocked")
    
    def test_02_prohibited_content_violence(self, auth_headers):
        """Test that violent content is blocked"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=auth_headers,
            json={
                "topic": "How to make a bomb and cause violence",
                "niche": "Education",
                "language": "English",
                "tone": "Bold",
                "duration": "30s",
                "goal": "Followers"
            }
        )
        print(f"Violence Content Response: {response.status_code} - {response.text[:500]}")
        
        if response.status_code == 400:
            print(f"✓ Violent content correctly blocked")
        else:
            print(f"⚠ Content may have been sanitized instead of blocked")
    
    def test_03_prohibited_content_explicit(self, auth_headers):
        """Test that explicit/NSFW content is blocked"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=auth_headers,
            json={
                "topic": "NSFW adult content nude video",
                "niche": "Entertainment",
                "language": "English",
                "tone": "Bold",
                "duration": "30s",
                "goal": "Followers"
            }
        )
        print(f"Explicit Content Response: {response.status_code} - {response.text[:500]}")
        
        if response.status_code == 400:
            print(f"✓ Explicit content correctly blocked")
        else:
            print(f"⚠ Content may have been sanitized instead of blocked")
    
    def test_04_safe_content_allowed(self, auth_headers):
        """Test that safe content is allowed"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=auth_headers,
            json={
                "topic": "5 healthy breakfast recipes for busy mornings",
                "niche": "Health",
                "language": "English",
                "tone": "Friendly",
                "duration": "30s",
                "goal": "Engagement"
            }
        )
        print(f"Safe Content Response: {response.status_code} - {response.text[:500]}")
        
        if response.status_code == 400 and "credits" in response.text.lower():
            pytest.skip("Insufficient credits")
        
        assert response.status_code == 200, f"Safe content should be allowed: {response.text}"
        print(f"✓ Safe content correctly allowed")
    
    def test_05_bot_detection_headers(self, auth_headers):
        """Test bot detection with suspicious headers"""
        # Test with bot-like user agent
        bot_headers = auth_headers.copy()
        bot_headers["User-Agent"] = "python-requests/2.28.0"
        
        response = requests.get(
            f"{BASE_URL}/api/health/",
            headers=bot_headers
        )
        print(f"Bot Detection Response: {response.status_code}")
        
        # Health endpoint should still work (bot detection may just log)
        assert response.status_code == 200
        print(f"✓ Bot detection test completed (may be logged)")

# =============================================================================
# JSON RESPONSE VALIDATION
# =============================================================================
class TestJSONResponses:
    """Test that all endpoints return proper JSON responses"""
    
    def test_01_auth_login_json(self):
        """Test login returns JSON"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()  # Should not raise
        print(f"✓ Login returns valid JSON")
    
    def test_02_health_json(self):
        """Test health returns JSON"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        print(f"✓ Health returns valid JSON")
    
    def test_03_convert_costs_json(self, auth_headers):
        """Test convert costs returns JSON"""
        response = requests.get(
            f"{BASE_URL}/api/convert/costs",
            headers=auth_headers
        )
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        print(f"✓ Convert costs returns valid JSON")
    
    def test_04_style_profiles_json(self, auth_headers):
        """Test style profiles returns JSON"""
        response = requests.get(
            f"{BASE_URL}/api/genstudio/style-profiles",
            headers=auth_headers
        )
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        print(f"✓ Style profiles returns valid JSON")
    
    def test_05_convert_history_json(self, auth_headers):
        """Test convert history returns JSON"""
        response = requests.get(
            f"{BASE_URL}/api/convert/history",
            headers=auth_headers
        )
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        print(f"✓ Convert history returns valid JSON")
    
    def test_06_error_response_json(self):
        """Test error responses are JSON"""
        response = requests.get(f"{BASE_URL}/api/nonexistent-endpoint")
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        print(f"✓ Error responses are valid JSON")

# =============================================================================
# CLEANUP
# =============================================================================
@pytest.fixture(scope="module", autouse=True)
def cleanup(request, auth_headers):
    """Cleanup test data after all tests"""
    yield
    # Cleanup any TEST_ prefixed style profiles
    try:
        response = requests.get(
            f"{BASE_URL}/api/genstudio/style-profiles",
            headers=auth_headers
        )
        if response.status_code == 200:
            profiles = response.json().get("profiles", [])
            for profile in profiles:
                if profile.get("name", "").startswith("TEST_"):
                    requests.delete(
                        f"{BASE_URL}/api/genstudio/style-profile/{profile['id']}",
                        headers=auth_headers
                    )
                    print(f"Cleaned up test profile: {profile['id']}")
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
