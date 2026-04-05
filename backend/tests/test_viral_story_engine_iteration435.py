"""
Viral Story Engine Tests - Iteration 435
Tests for Phase 4 viral loop features:
- Share page viral fields (forks, recentForks, storyContext, characters, tone, conflict, hookText, shareCaption, parentShareId)
- Fork API (no auth required, increments fork count, returns fork data)
- Story chain API (returns totalVersions)
- Share create with viral fields
- Alive signals (continuations_today, active_creators, stories_today, total_continuations, latest_fork)
- A/B impression tracking
- Featured story for first session
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test share ID from context - has 2 forks and characters
TEST_SHARE_ID = "b9658c73-be1"

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestShareViralFields:
    """Test GET /api/share/{shareId} returns all viral loop fields"""
    
    def test_share_returns_viral_fields(self):
        """Verify share endpoint returns all viral loop fields"""
        response = requests.get(f"{BASE_URL}/api/share/{TEST_SHARE_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        
        # Verify all viral loop fields are present
        assert "forks" in data, "Missing 'forks' field"
        assert "recentForks" in data, "Missing 'recentForks' field"
        assert "storyContext" in data, "Missing 'storyContext' field"
        assert "characters" in data, "Missing 'characters' field"
        assert "tone" in data, "Missing 'tone' field"
        assert "conflict" in data, "Missing 'conflict' field"
        assert "hookText" in data, "Missing 'hookText' field"
        assert "shareCaption" in data, "Missing 'shareCaption' field"
        assert "parentShareId" in data, "Missing 'parentShareId' field"
        
        print(f"PASS: Share returns all viral fields - forks={data['forks']}, characters={data['characters']}")
    
    def test_share_has_expected_data(self):
        """Verify the test share has expected data"""
        response = requests.get(f"{BASE_URL}/api/share/{TEST_SHARE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify expected values from context
        assert data.get("title") == "The Last Echo", f"Expected title 'The Last Echo', got {data.get('title')}"
        assert data.get("forks") >= 2, f"Expected at least 2 forks, got {data.get('forks')}"
        assert isinstance(data.get("characters"), list), "Characters should be a list"
        assert len(data.get("characters", [])) >= 3, f"Expected at least 3 characters, got {len(data.get('characters', []))}"
        
        # Verify characters include expected names
        chars = data.get("characters", [])
        assert "Lyra" in chars, f"Expected 'Lyra' in characters, got {chars}"
        
        print(f"PASS: Share has expected data - title={data['title']}, forks={data['forks']}, characters={chars}")
    
    def test_share_recent_forks_structure(self):
        """Verify recentForks has correct structure"""
        response = requests.get(f"{BASE_URL}/api/share/{TEST_SHARE_ID}")
        assert response.status_code == 200
        
        data = response.json()
        recent_forks = data.get("recentForks", [])
        
        assert isinstance(recent_forks, list), "recentForks should be a list"
        
        # If there are recent forks, verify structure
        if len(recent_forks) > 0:
            fork = recent_forks[0]
            assert "timestamp" in fork, "Recent fork should have timestamp"
        
        print(f"PASS: recentForks structure valid - count={len(recent_forks)}")
    
    def test_share_not_found(self):
        """Verify 404 for non-existent share"""
        response = requests.get(f"{BASE_URL}/api/share/nonexistent-share-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Non-existent share returns 404")


class TestForkAPI:
    """Test POST /api/share/{shareId}/fork - no auth required"""
    
    def test_fork_no_auth_required(self):
        """Verify fork endpoint works without authentication"""
        response = requests.post(f"{BASE_URL}/api/share/{TEST_SHARE_ID}/fork")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "fork" in data, "Response should contain 'fork' object"
        
        print("PASS: Fork endpoint works without auth")
    
    def test_fork_returns_required_fields(self):
        """Verify fork returns parentShareId, storyContext, characters, tone, conflict, type"""
        response = requests.post(f"{BASE_URL}/api/share/{TEST_SHARE_ID}/fork")
        assert response.status_code == 200
        
        data = response.json()
        fork = data.get("fork", {})
        
        # Verify all required fork fields
        assert "parentShareId" in fork, "Fork should have parentShareId"
        assert "storyContext" in fork, "Fork should have storyContext"
        assert "characters" in fork, "Fork should have characters"
        assert "tone" in fork, "Fork should have tone"
        assert "conflict" in fork, "Fork should have conflict"
        assert "type" in fork, "Fork should have type"
        
        # Verify parentShareId matches
        assert fork["parentShareId"] == TEST_SHARE_ID, f"Expected parentShareId={TEST_SHARE_ID}, got {fork['parentShareId']}"
        
        print(f"PASS: Fork returns all required fields - parentShareId={fork['parentShareId']}, type={fork['type']}")
    
    def test_fork_increments_count(self):
        """Verify fork increments the fork count on parent share"""
        # Get initial fork count
        response1 = requests.get(f"{BASE_URL}/api/share/{TEST_SHARE_ID}")
        assert response1.status_code == 200
        initial_forks = response1.json().get("forks", 0)
        
        # Create a fork
        response2 = requests.post(f"{BASE_URL}/api/share/{TEST_SHARE_ID}/fork")
        assert response2.status_code == 200
        
        # Get updated fork count
        response3 = requests.get(f"{BASE_URL}/api/share/{TEST_SHARE_ID}")
        assert response3.status_code == 200
        new_forks = response3.json().get("forks", 0)
        
        assert new_forks == initial_forks + 1, f"Expected forks to increment from {initial_forks} to {initial_forks + 1}, got {new_forks}"
        
        print(f"PASS: Fork increments count - {initial_forks} -> {new_forks}")
    
    def test_fork_not_found(self):
        """Verify 404 for fork on non-existent share"""
        response = requests.post(f"{BASE_URL}/api/share/nonexistent-share-id-12345/fork")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Fork on non-existent share returns 404")


class TestStoryChainAPI:
    """Test GET /api/share/{shareId}/chain - returns chain with totalVersions"""
    
    def test_chain_returns_total_versions(self):
        """Verify chain endpoint returns totalVersions"""
        response = requests.get(f"{BASE_URL}/api/share/{TEST_SHARE_ID}/chain")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "totalVersions" in data, "Response should contain 'totalVersions'"
        assert "chain" in data, "Response should contain 'chain'"
        assert "rootId" in data, "Response should contain 'rootId'"
        
        total = data.get("totalVersions", 0)
        assert total >= 1, f"Expected at least 1 version, got {total}"
        
        print(f"PASS: Chain returns totalVersions={total}, rootId={data.get('rootId')}")
    
    def test_chain_structure(self):
        """Verify chain items have correct structure"""
        response = requests.get(f"{BASE_URL}/api/share/{TEST_SHARE_ID}/chain")
        assert response.status_code == 200
        
        data = response.json()
        chain = data.get("chain", [])
        
        assert isinstance(chain, list), "Chain should be a list"
        
        if len(chain) > 0:
            item = chain[0]
            assert "id" in item, "Chain item should have id"
            assert "title" in item, "Chain item should have title"
            assert "createdAt" in item, "Chain item should have createdAt"
        
        print(f"PASS: Chain structure valid - {len(chain)} items")
    
    def test_chain_not_found(self):
        """Verify 404 for chain on non-existent share"""
        response = requests.get(f"{BASE_URL}/api/share/nonexistent-share-id-12345/chain")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Chain on non-existent share returns 404")


class TestShareCreateViralFields:
    """Test POST /api/share/create accepts and stores viral fields"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_create_share_with_viral_fields(self, auth_token):
        """Verify share create accepts viral fields"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        payload = {
            "generationId": f"test-gen-{int(time.time())}",
            "type": "STORY_VIDEO",
            "title": "Test Viral Story",
            "preview": "A test story for viral loop testing",
            "storyContext": "Test context for continuation",
            "characters": ["Hero", "Villain", "Sidekick"],
            "tone": "adventurous",
            "conflict": "Good vs Evil",
            "hookText": "What happens next will shock you...",
            "shareCaption": "I started this story, can you finish it?"
        }
        
        response = requests.post(f"{BASE_URL}/api/share/create", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "shareId" in data, "Response should contain shareId"
        assert "shareUrl" in data, "Response should contain shareUrl"
        
        share_id = data.get("shareId")
        print(f"PASS: Created share with viral fields - shareId={share_id}")
        
        # Verify the created share has the viral fields
        response2 = requests.get(f"{BASE_URL}/api/share/{share_id}")
        assert response2.status_code == 200
        
        share_data = response2.json()
        assert share_data.get("storyContext") == payload["storyContext"]
        assert share_data.get("characters") == payload["characters"]
        assert share_data.get("tone") == payload["tone"]
        assert share_data.get("conflict") == payload["conflict"]
        assert share_data.get("hookText") == payload["hookText"]
        assert share_data.get("shareCaption") == payload["shareCaption"]
        
        print(f"PASS: Share stores all viral fields correctly")


class TestAliveSignals:
    """Test GET /api/public/alive - returns real-time engagement data"""
    
    def test_alive_returns_required_fields(self):
        """Verify alive endpoint returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/public/alive")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required fields
        assert "continuations_today" in data, "Missing 'continuations_today'"
        assert "active_creators" in data, "Missing 'active_creators'"
        assert "stories_today" in data, "Missing 'stories_today'"
        assert "total_continuations" in data, "Missing 'total_continuations'"
        assert "latest_fork" in data, "Missing 'latest_fork'"
        
        print(f"PASS: Alive signals - continuations_today={data['continuations_today']}, active_creators={data['active_creators']}, stories_today={data['stories_today']}")
    
    def test_alive_latest_fork_structure(self):
        """Verify latest_fork has correct structure"""
        response = requests.get(f"{BASE_URL}/api/public/alive")
        assert response.status_code == 200
        
        data = response.json()
        latest_fork = data.get("latest_fork")
        
        # latest_fork can be None if no forks exist
        if latest_fork is not None:
            assert "timestamp" in latest_fork, "latest_fork should have timestamp"
            assert "parentTitle" in latest_fork, "latest_fork should have parentTitle"
        
        print(f"PASS: latest_fork structure valid - {latest_fork}")
    
    def test_alive_no_auth_required(self):
        """Verify alive endpoint works without authentication"""
        response = requests.get(f"{BASE_URL}/api/public/alive")
        assert response.status_code == 200, f"Expected 200 without auth, got {response.status_code}"
        print("PASS: Alive endpoint works without auth")


class TestABImpression:
    """Test POST /api/public/ab-impression - tracks A/B variant impression"""
    
    def test_ab_impression_tracking(self):
        """Verify A/B impression tracking works"""
        payload = {
            "variant": "A",
            "action": "impression"
        }
        
        response = requests.post(f"{BASE_URL}/api/public/ab-impression", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ok") == True, f"Expected ok=True, got {data}"
        
        print("PASS: A/B impression tracking works for variant A")
    
    def test_ab_impression_variant_b(self):
        """Verify A/B impression tracking works for variant B"""
        payload = {
            "variant": "B",
            "action": "cta_click"
        }
        
        response = requests.post(f"{BASE_URL}/api/public/ab-impression", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") == True
        
        print("PASS: A/B impression tracking works for variant B")
    
    def test_ab_impression_no_auth_required(self):
        """Verify A/B impression works without authentication"""
        response = requests.post(f"{BASE_URL}/api/public/ab-impression", json={"variant": "C", "action": "test"})
        assert response.status_code == 200, f"Expected 200 without auth, got {response.status_code}"
        print("PASS: A/B impression works without auth")


class TestFeaturedStory:
    """Test GET /api/public/featured-story - returns featured story for first session"""
    
    def test_featured_story_endpoint(self):
        """Verify featured story endpoint works"""
        response = requests.get(f"{BASE_URL}/api/public/featured-story")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "found" in data, "Response should contain 'found' field"
        
        if data.get("found"):
            # If a featured story exists, verify structure
            assert "title" in data, "Featured story should have title"
            # shareId or jobId should be present
            assert "shareId" in data or "jobId" in data, "Featured story should have shareId or jobId"
        
        print(f"PASS: Featured story endpoint works - found={data.get('found')}")
    
    def test_featured_story_no_auth_required(self):
        """Verify featured story works without authentication"""
        response = requests.get(f"{BASE_URL}/api/public/featured-story")
        assert response.status_code == 200, f"Expected 200 without auth, got {response.status_code}"
        print("PASS: Featured story works without auth")
    
    def test_featured_story_structure_when_found(self):
        """Verify featured story has expected fields when found"""
        response = requests.get(f"{BASE_URL}/api/public/featured-story")
        assert response.status_code == 200
        
        data = response.json()
        
        if data.get("found"):
            # Verify optional fields that should be present
            expected_fields = ["title", "preview", "forks", "views"]
            for field in expected_fields:
                assert field in data, f"Featured story should have '{field}' field"
            
            print(f"PASS: Featured story has all expected fields - title={data.get('title')}")
        else:
            print("PASS: No featured story found (acceptable)")


class TestPublicEndpointsRegression:
    """Regression tests for existing public endpoints"""
    
    def test_public_stats(self):
        """Verify /api/public/stats still works"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "creators" in data or "videos_created" in data, "Stats should have creator or video counts"
        
        print(f"PASS: Public stats endpoint works")
    
    def test_public_live_activity(self):
        """Verify /api/public/live-activity still works"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=5")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        assert "items" in data, "Live activity should have items"
        
        print(f"PASS: Live activity endpoint works - {len(data.get('items', []))} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
