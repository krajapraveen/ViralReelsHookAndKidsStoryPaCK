"""
Growth Engine Iteration 442 - Comprehensive Testing
Tests: Social proof banner, urgency text, analytics events, referral system, 
       Create Another section, watermark function verification
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
KNOWN_SHARE_ID = "96902ad4-066"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with authentication"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestGrowthAnalyticsEvents:
    """Test POST /api/growth/event for new growth funnel events"""
    
    def test_share_viewed_event(self):
        """Test share_viewed event tracking"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "share_viewed",
            "session_id": "test-session-442",
            "meta": {"share_id": KNOWN_SHARE_ID}
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "event_id" in data or data.get("deduplicated") == True
        print("✓ share_viewed event tracked successfully")
    
    def test_cta_clicked_event(self):
        """Test cta_clicked event tracking"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "cta_clicked",
            "session_id": "test-session-442",
            "meta": {"share_id": KNOWN_SHARE_ID, "location": "primary_btn"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ cta_clicked event tracked successfully")
    
    def test_remix_clicked_event(self):
        """Test remix_clicked event tracking"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "remix_clicked",
            "session_id": "test-session-442",
            "meta": {"share_id": KNOWN_SHARE_ID}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ remix_clicked event tracked successfully")
    
    def test_whatsapp_shared_event(self):
        """Test whatsapp_shared event tracking"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "whatsapp_shared",
            "session_id": "test-session-442",
            "meta": {"share_id": KNOWN_SHARE_ID}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ whatsapp_shared event tracked successfully")
    
    def test_download_triggered_event(self):
        """Test download_triggered event tracking"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "download_triggered",
            "session_id": "test-session-442",
            "meta": {"share_id": KNOWN_SHARE_ID}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ download_triggered event tracked successfully")
    
    def test_referral_link_copied_event(self):
        """Test referral_link_copied event tracking"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "referral_link_copied",
            "session_id": "test-session-442",
            "meta": {"share_id": KNOWN_SHARE_ID}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ referral_link_copied event tracked successfully")
    
    def test_first_video_created_event(self):
        """Test first_video_created event tracking"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "first_video_created",
            "session_id": "test-session-442",
            "user_id": "test-user-442"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ first_video_created event tracked successfully")
    
    def test_invalid_event_rejected(self):
        """Test that invalid events are rejected"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "invalid_event_name_xyz",
            "session_id": "test-session-442"
        })
        assert response.status_code == 400, f"Expected 400 for invalid event, got {response.status_code}"
        print("✓ Invalid event correctly rejected with 400")


class TestReferralSystem:
    """Test referral system endpoints at /api/referral/"""
    
    def test_get_referral_code(self, auth_headers):
        """Test GET /api/referral/code returns valid referral code"""
        response = requests.get(f"{BASE_URL}/api/referral/code", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "code" in data, "Response should contain 'code'"
        assert "link" in data, "Response should contain 'link'"
        assert len(data["code"]) >= 6, "Referral code should be at least 6 characters"
        print(f"✓ Referral code retrieved: {data['code']}")
        print(f"✓ Referral link: {data['link']}")
    
    def test_get_referral_stats(self, auth_headers):
        """Test GET /api/referral/stats returns referral statistics"""
        response = requests.get(f"{BASE_URL}/api/referral/stats", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "stats" in data, "Response should contain 'stats'"
        assert "tier" in data, "Response should contain 'tier'"
        stats = data["stats"]
        assert "totalReferrals" in stats
        assert "totalEarned" in stats
        print(f"✓ Referral stats: totalReferrals={stats['totalReferrals']}, totalEarned={stats['totalEarned']}")
        print(f"✓ Referral tier: {data['tier']}")
    
    def test_validate_referral_code_invalid(self):
        """Test POST /api/referral/validate/{code} with invalid code"""
        response = requests.post(f"{BASE_URL}/api/referral/validate/INVALID123")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("valid") == False, "Invalid code should return valid=False"
        print("✓ Invalid referral code correctly returns valid=False")
    
    def test_validate_referral_code_valid(self, auth_headers):
        """Test POST /api/referral/validate/{code} with valid code"""
        # First get a valid code
        code_response = requests.get(f"{BASE_URL}/api/referral/code", headers=auth_headers)
        if code_response.status_code != 200:
            pytest.skip("Could not get referral code")
        code = code_response.json().get("code")
        
        # Validate it
        response = requests.post(f"{BASE_URL}/api/referral/validate/{code}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("valid") == True, "Valid code should return valid=True"
        assert "bonusCredits" in data, "Response should contain bonusCredits"
        print(f"✓ Valid referral code {code} validated successfully")
        print(f"✓ Bonus credits: {data.get('bonusCredits')}")
    
    def test_referral_code_unauthenticated(self):
        """Test GET /api/referral/code requires authentication"""
        response = requests.get(f"{BASE_URL}/api/referral/code")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Referral code endpoint correctly requires authentication")


class TestSharePageAPI:
    """Test share page API endpoints"""
    
    def test_share_page_data(self):
        """Test GET /api/share/{share_id} returns required data"""
        response = requests.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        # Check for fields needed by social proof calculation
        assert "views" in data or "forks" in data, "Response should contain views or forks for social proof"
        print(f"✓ Share page data retrieved for {KNOWN_SHARE_ID}")
        print(f"✓ Views: {data.get('views', 0)}, Forks: {data.get('forks', 0)}")
    
    def test_share_page_invalid_id(self):
        """Test GET /api/share/{share_id} with invalid ID"""
        response = requests.get(f"{BASE_URL}/api/share/invalid-share-id-xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid share ID correctly returns 404")


class TestMySpaceCreateAnother:
    """Test My Space 'Create Another' section via API"""
    
    def test_user_jobs_endpoint(self, auth_headers):
        """Test GET /api/story-engine/user-jobs returns jobs"""
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=10", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "jobs" in data, "Response should contain 'jobs'"
        print(f"✓ User jobs endpoint working, returned {len(data['jobs'])} jobs")


class TestWatermarkFunctionCodeReview:
    """Code review verification for watermark end screen function"""
    
    def test_watermark_function_exists(self):
        """Verify add_watermark_endscreen function exists in ffmpeg_assembly.py"""
        ffmpeg_path = "/app/backend/services/story_engine/adapters/ffmpeg_assembly.py"
        assert os.path.exists(ffmpeg_path), f"File not found: {ffmpeg_path}"
        
        with open(ffmpeg_path, 'r') as f:
            content = f.read()
        
        # Check function definition
        assert "async def add_watermark_endscreen(" in content, \
            "add_watermark_endscreen function not found in ffmpeg_assembly.py"
        
        # Check function parameters
        assert "video_path: str" in content, "video_path parameter not found"
        assert "output_path: str" in content, "output_path parameter not found"
        assert "duration: float = 2.5" in content, "duration parameter with default 2.5 not found"
        assert "brand_text: str" in content, "brand_text parameter not found"
        assert "cta_text: str" in content, "cta_text parameter not found"
        assert "url_text: str" in content, "url_text parameter not found"
        
        # Check implementation details
        assert "Created with Visionary Suite" in content, "Default brand text not found"
        assert "Make yours in seconds" in content, "Default CTA text not found"
        assert "visionary-suite.com" in content, "Default URL text not found"
        assert "concat" in content.lower(), "Concat operation not found in watermark function"
        
        print("✓ add_watermark_endscreen function exists with correct signature")
        print("✓ Function has correct default parameters (2.5s duration, brand text, CTA, URL)")
        print("✓ Function uses ffmpeg concat to append end screen")
    
    def test_watermark_called_in_pipeline(self):
        """Verify watermark step is called in pipeline.py before upload"""
        pipeline_path = "/app/backend/services/story_engine/pipeline.py"
        assert os.path.exists(pipeline_path), f"File not found: {pipeline_path}"
        
        with open(pipeline_path, 'r') as f:
            content = f.read()
        
        # Check watermark is imported/called
        assert "add_watermark_endscreen" in content, \
            "add_watermark_endscreen not referenced in pipeline.py"
        
        # Check it's called in assembly stage
        assert "watermark" in content.lower(), "Watermark step not found in pipeline"
        
        # Verify it's before upload (check line ordering)
        watermark_pos = content.find("add_watermark_endscreen")
        upload_pos = content.find("_upload_to_r2")
        
        assert watermark_pos < upload_pos, \
            "Watermark should be called before upload to R2"
        
        print("✓ add_watermark_endscreen is called in pipeline.py")
        print("✓ Watermark step occurs before upload to R2")


class TestGrowthAnalyticsValidEvents:
    """Verify all required growth events are in VALID_EVENTS"""
    
    def test_valid_events_list(self):
        """Check growth_analytics.py has all required events"""
        analytics_path = "/app/backend/routes/growth_analytics.py"
        assert os.path.exists(analytics_path), f"File not found: {analytics_path}"
        
        with open(analytics_path, 'r') as f:
            content = f.read()
        
        required_events = [
            "share_viewed",
            "cta_clicked", 
            "remix_clicked",
            "download_triggered",
            "whatsapp_shared",
            "referral_link_copied",
            "first_video_created",
            "create_button_clicked"
        ]
        
        for event in required_events:
            assert f'"{event}"' in content, f"Event '{event}' not found in VALID_EVENTS"
            print(f"✓ Event '{event}' is in VALID_EVENTS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
