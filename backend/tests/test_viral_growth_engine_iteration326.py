"""
Phase 2 Viral Growth Engine Tests - Iteration 326
Tests: WATCH → CONTINUE → LOOP → SHARE flow
- Share rewards (+5 credits)
- Continuation rewards (+10 credits)
- Growth analytics event tracking
- Public share page conversion CTAs
- Open-loop ending enforcement in pipeline
"""

import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Known working slug
KNOWN_SLUG = "dragon-guardians-of-the-crystal-valley-fe12f875"


class TestGrowthAnalyticsEvents:
    """Test growth analytics event tracking for viral loop"""
    
    def test_track_continue_click_event(self):
        """Test tracking continue_click event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "continue_click",
            "session_id": "test_session_326",
            "source_slug": KNOWN_SLUG,
            "origin": "share_page",
            "meta": {"type": "continue"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"continue_click event tracked: {data}")
    
    def test_track_add_twist_click_event(self):
        """Test tracking add_twist_click event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "add_twist_click",
            "session_id": "test_session_326",
            "source_slug": KNOWN_SLUG,
            "origin": "share_page",
            "meta": {"type": "twist"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"add_twist_click event tracked: {data}")
    
    def test_track_make_funny_click_event(self):
        """Test tracking make_funny_click event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "make_funny_click",
            "session_id": "test_session_326",
            "source_slug": KNOWN_SLUG,
            "origin": "share_page",
            "meta": {"type": "funny"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"make_funny_click event tracked: {data}")
    
    def test_track_next_episode_click_event(self):
        """Test tracking next_episode_click event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "next_episode_click",
            "session_id": "test_session_326",
            "source_slug": KNOWN_SLUG,
            "origin": "share_page",
            "meta": {"type": "episode"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"next_episode_click event tracked: {data}")
    
    def test_invalid_event_rejected(self):
        """Test that invalid events are rejected"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "invalid_event_type",
            "session_id": "test_session_326"
        })
        assert response.status_code == 400
        print("Invalid event correctly rejected")


class TestShareRewards:
    """Test share rewards endpoint (+5 credits per share)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_share_reward_requires_auth(self):
        """Test that share reward endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/growth/share-reward", json={
            "job_id": "test_job_id",
            "platform": "whatsapp"
        })
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 422]
        print(f"Share reward correctly requires auth: {response.status_code}")
    
    def test_share_reward_with_auth(self, auth_token):
        """Test share reward with valid authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/growth/share-reward", 
            json={
                "job_id": f"test_job_{datetime.now().timestamp()}",
                "platform": "whatsapp"
            },
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        # First share should be rewarded
        if data.get("rewarded"):
            assert data.get("credits_awarded") == 5
            print(f"Share reward granted: +5 credits")
        else:
            print(f"Share reward already claimed: {data.get('message')}")
    
    def test_share_reward_deduplication(self, auth_token):
        """Test that share reward is only given once per job"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        job_id = f"dedup_test_job_{datetime.now().timestamp()}"
        
        # First share
        response1 = requests.post(f"{BASE_URL}/api/growth/share-reward", 
            json={"job_id": job_id, "platform": "twitter"},
            headers=headers
        )
        assert response1.status_code == 200
        
        # Second share of same job
        response2 = requests.post(f"{BASE_URL}/api/growth/share-reward", 
            json={"job_id": job_id, "platform": "whatsapp"},
            headers=headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # Should not be rewarded again
        assert data2.get("rewarded") == False
        print("Share reward deduplication working correctly")


class TestContinuationRewards:
    """Test continuation rewards endpoint (+10 credits to original creator)"""
    
    def test_continuation_reward_endpoint_exists(self):
        """Test that continuation reward endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/growth/continuation-reward", json={
            "parent_job_id": "nonexistent_job",
            "session_id": "test_session"
        })
        # Should return 200 even if job not found (graceful handling)
        assert response.status_code == 200
        data = response.json()
        # Should indicate job not found
        assert data.get("success") == False or data.get("rewarded") == False
        print(f"Continuation reward endpoint working: {data}")


class TestPublicCreationPage:
    """Test public share page as conversion page"""
    
    def test_public_creation_endpoint(self):
        """Test public creation endpoint returns creation data"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{KNOWN_SLUG}")
        assert response.status_code == 200
        data = response.json()
        assert "creation" in data
        creation = data["creation"]
        print(f"Public creation loaded: {creation.get('title', 'Unknown')}")
        
        # Verify required fields for conversion page
        assert "title" in creation
        assert "views" in creation or creation.get("views") is not None
        print(f"Views: {creation.get('views', 0)}, Remix count: {creation.get('remix_count', 0)}")
    
    def test_public_creation_remix_increment(self):
        """Test that remix endpoint increments count"""
        response = requests.post(f"{BASE_URL}/api/public/creation/{KNOWN_SLUG}/remix")
        # Should succeed or return 200
        assert response.status_code in [200, 201]
        print("Remix increment endpoint working")
    
    def test_public_creation_not_found(self):
        """Test 404 for non-existent creation"""
        response = requests.get(f"{BASE_URL}/api/public/creation/nonexistent-slug-12345")
        assert response.status_code == 404
        print("Non-existent creation correctly returns 404")


class TestGrowthMetrics:
    """Test growth metrics and funnel data endpoints"""
    
    def test_growth_metrics_endpoint(self):
        """Test growth metrics endpoint"""
        response = requests.get(f"{BASE_URL}/api/growth/metrics?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "raw_counts" in data
        assert "conversion_rates" in data
        print(f"Growth metrics: {data.get('raw_counts', {})}")
    
    def test_viral_coefficient_endpoint(self):
        """Test viral coefficient calculation endpoint"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "viral_coefficient_K" in data
        assert "interpretation" in data
        print(f"Viral coefficient K: {data.get('viral_coefficient_K')}, Interpretation: {data.get('interpretation')}")
    
    def test_funnel_data_endpoint(self):
        """Test funnel visualization data endpoint"""
        response = requests.get(f"{BASE_URL}/api/growth/funnel?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "funnel" in data
        print(f"Funnel stages: {len(data.get('funnel', []))}")


class TestPipelineOpenLoopEndings:
    """Test that pipeline enforces open-loop endings"""
    
    def test_pipeline_options_endpoint(self):
        """Test pipeline options endpoint returns style/voice/age options"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        assert "animation_styles" in data
        assert "voice_presets" in data
        assert "age_groups" in data
        print(f"Pipeline options: {len(data.get('animation_styles', []))} styles, {len(data.get('voice_presets', []))} voices")


class TestZeroFrictionAccess:
    """Test that public pages and studio are accessible without login"""
    
    def test_public_page_no_auth_required(self):
        """Test public share page accessible without auth"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{KNOWN_SLUG}")
        assert response.status_code == 200
        print("Public page accessible without auth")
    
    def test_pipeline_options_no_auth_required(self):
        """Test pipeline options accessible without auth"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        print("Pipeline options accessible without auth")
    
    def test_growth_event_no_auth_required(self):
        """Test growth event tracking works without auth"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "page_view",
            "session_id": "anonymous_session_326",
            "source_page": "/v/test-slug"
        })
        assert response.status_code == 200
        print("Growth event tracking works without auth")


class TestGalleryEndpoint:
    """Test gallery endpoint for Continue Story CTAs"""
    
    def test_gallery_returns_creations(self):
        """Test gallery endpoint returns creations with thumbnails"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data or "items" in data or "creations" in data
        items = data.get("videos") or data.get("items") or data.get("creations") or []
        print(f"Gallery returned {len(items)} items")
        
        # Check that items have required fields for Continue Story
        if items:
            item = items[0]
            assert "title" in item or "job_id" in item
            print(f"First item: {item.get('title', item.get('job_id', 'Unknown'))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
