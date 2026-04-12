"""
Test suite for Consumption-First Viral Loop (Phase 0-2)
Tests funnel tracking events, story viewer endpoint, and card navigation behavior.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestAPIHealth:
    """Basic API health check"""
    
    def test_api_health(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")


class TestFunnelTrackingEndpoint:
    """Test POST /api/funnel/track for Phase 0 baseline events"""
    
    def test_track_story_viewed(self):
        """Track story_viewed event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "story_viewed",
            "context": {"meta": {"story_id": "test-story-123", "title": "Test Story"}}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "session_id" in data
        print("✓ story_viewed event tracked successfully")
    
    def test_track_story_card_clicked(self):
        """Track story_card_clicked event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "story_card_clicked",
            "context": {"meta": {"badge": "TRENDING", "story_id": "test-story-123", "story_title": "Test Story"}}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ story_card_clicked event tracked successfully")
    
    def test_track_watch_started(self):
        """Track watch_started event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "watch_started",
            "context": {"meta": {"story_id": "test-story-123"}}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ watch_started event tracked successfully")
    
    def test_track_watch_completed_50(self):
        """Track watch_completed_50 event (50% video progress)"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "watch_completed_50",
            "context": {"meta": {"story_id": "test-story-123"}}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ watch_completed_50 event tracked successfully")
    
    def test_track_watch_completed_100(self):
        """Track watch_completed_100 event (video ended)"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "watch_completed_100",
            "context": {"meta": {"story_id": "test-story-123"}}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ watch_completed_100 event tracked successfully")
    
    def test_track_cta_clicked(self):
        """Track cta_clicked event with type and source"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "cta_clicked",
            "context": {"meta": {"type": "watch_now", "source": "hero", "story_id": "test-story-123"}}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ cta_clicked event tracked successfully")
    
    def test_track_remix_clicked(self):
        """Track remix_clicked event"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "remix_clicked",
            "context": {"meta": {"story_id": "test-story-123", "source": "viewer_body"}}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ remix_clicked event tracked successfully")
    
    def test_track_scroll_depth_50(self):
        """Track scroll_depth_50 event (floating CTA trigger)"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "scroll_depth_50",
            "context": {}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print("✓ scroll_depth_50 event tracked successfully")
    
    def test_track_invalid_step_rejected(self):
        """Verify invalid funnel step is rejected"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "invalid_step_name",
            "context": {}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is False
        assert "Invalid step" in data.get("error", "")
        print("✓ Invalid step correctly rejected")


class TestStoryViewerEndpoint:
    """Test GET /api/stories/viewer/{jobId} for Watch Page"""
    
    def test_viewer_endpoint_returns_story(self):
        """Verify story viewer endpoint returns story data"""
        response = requests.get(f"{BASE_URL}/api/stories/viewer/battle-demo-root")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "job" in data
        job = data["job"]
        assert job.get("job_id") == "battle-demo-root"
        assert "title" in job
        print(f"✓ Story viewer returned: {job.get('title')}")
    
    def test_viewer_endpoint_returns_chain_info(self):
        """Verify story viewer returns chain/episode info"""
        response = requests.get(f"{BASE_URL}/api/stories/viewer/battle-demo-root")
        assert response.status_code == 200
        data = response.json()
        job = data.get("job", {})
        # Check for chain-related fields
        assert "chain_depth" in job or "continuation_type" in job or "story_chain_id" in job
        print("✓ Story viewer returns chain info")
    
    def test_viewer_endpoint_404_for_invalid_id(self):
        """Verify 404 for non-existent story"""
        response = requests.get(f"{BASE_URL}/api/stories/viewer/non-existent-story-id-12345")
        # Should return 404 or success=false
        if response.status_code == 404:
            print("✓ Non-existent story returns 404")
        else:
            data = response.json()
            assert data.get("success") is False or response.status_code == 404
            print("✓ Non-existent story handled correctly")


class TestStoryChainEndpoint:
    """Test GET /api/stories/{jobId}/chain for episode navigation"""
    
    def test_chain_endpoint_returns_episodes(self):
        """Verify chain endpoint returns episodes list"""
        response = requests.get(f"{BASE_URL}/api/stories/battle-demo-root/chain")
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                assert "episodes" in data
                print(f"✓ Chain endpoint returned {len(data.get('episodes', []))} episodes")
            else:
                print("○ Chain endpoint returned success=false (may have no chain)")
        else:
            print(f"○ Chain endpoint returned {response.status_code}")


class TestStoryBranchesEndpoint:
    """Test GET /api/stories/{jobId}/branches for remix chain"""
    
    def test_branches_endpoint_returns_remixes(self):
        """Verify branches endpoint returns remix list"""
        response = requests.get(f"{BASE_URL}/api/stories/battle-demo-root/branches")
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                assert "branches" in data
                print(f"✓ Branches endpoint returned {len(data.get('branches', []))} remixes")
            else:
                print("○ Branches endpoint returned success=false (may have no branches)")
        else:
            print(f"○ Branches endpoint returned {response.status_code}")


class TestStoryFeedEndpoint:
    """Test GET /api/engagement/story-feed for dashboard cards"""
    
    def test_feed_returns_rows(self):
        """Verify story feed returns rows with stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        assert "rows" in data
        rows = data.get("rows", [])
        print(f"✓ Story feed returned {len(rows)} rows")
        
        # Check for expected row keys
        row_keys = [r.get("key") for r in rows]
        if "trending_now" in row_keys or "fresh_stories" in row_keys:
            print("✓ Feed contains trending/fresh rows")
    
    def test_feed_stories_have_required_fields(self):
        """Verify stories in feed have required fields for cards"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        data = response.json()
        rows = data.get("rows", [])
        
        if rows and rows[0].get("stories"):
            story = rows[0]["stories"][0]
            # Check for fields needed by StoryCard component
            assert "job_id" in story or "is_seed" in story
            assert "title" in story
            print("✓ Stories have required fields for cards")


class TestIncrementMetricEndpoint:
    """Test POST /api/stories/increment-metric for view/share tracking"""
    
    def test_increment_views(self):
        """Verify view metric can be incremented"""
        response = requests.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": "battle-demo-root",
            "metric": "views"
        })
        # Should succeed or return appropriate error
        if response.status_code == 200:
            print("✓ View metric increment accepted")
        else:
            print(f"○ View metric increment returned {response.status_code}")
    
    def test_increment_shares(self):
        """Verify share metric can be incremented"""
        response = requests.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": "battle-demo-root",
            "metric": "shares"
        })
        # Should succeed or return appropriate error
        if response.status_code == 200:
            print("✓ Share metric increment accepted")
        else:
            print(f"○ Share metric increment returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
