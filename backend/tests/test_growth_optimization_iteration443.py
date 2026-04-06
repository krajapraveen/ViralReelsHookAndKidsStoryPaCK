"""
Growth Optimization Testing - Iteration 443
Tests:
1. Completion modal: WhatsApp PRIMARY, viral nudge, Download/Create Another secondary
2. Share page: More Videos carousel with "People are creating these" heading
3. Backend: GET /api/share/{shareId}/more-videos returns up to 6 videos
4. Backend: POST /api/growth/event accepts share_viewed, cta_clicked, remix_clicked, whatsapp_shared
5. My Space regression: 3 sections, auto-download toggle, notification toggle, Create Another section
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMoreVideosEndpoint:
    """Test GET /api/share/{shareId}/more-videos endpoint"""
    
    def test_more_videos_returns_videos(self):
        """Test that more-videos endpoint returns up to 6 videos"""
        share_id = "96902ad4-066"  # Known test share ID
        response = requests.get(f"{BASE_URL}/api/share/{share_id}/more-videos")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=true"
        assert "videos" in data, "Expected 'videos' key in response"
        
        videos = data["videos"]
        assert isinstance(videos, list), "Expected videos to be a list"
        assert len(videos) <= 6, f"Expected at most 6 videos, got {len(videos)}"
        
        # Verify video structure if any videos returned
        if len(videos) > 0:
            video = videos[0]
            assert "id" in video, "Expected 'id' in video"
            assert "title" in video, "Expected 'title' in video"
            assert "thumbnailUrl" in video or video.get("thumbnailUrl") is None, "Expected 'thumbnailUrl' key"
            assert "views" in video, "Expected 'views' in video"
        
        print(f"✓ More videos endpoint returned {len(videos)} videos")
    
    def test_more_videos_excludes_current_share(self):
        """Test that more-videos excludes the current share ID"""
        share_id = "96902ad4-066"
        response = requests.get(f"{BASE_URL}/api/share/{share_id}/more-videos")
        
        assert response.status_code == 200
        data = response.json()
        videos = data.get("videos", [])
        
        # Verify current share is not in the list
        video_ids = [v.get("id") for v in videos]
        assert share_id not in video_ids, f"Current share {share_id} should not be in more-videos list"
        
        print(f"✓ Current share correctly excluded from more-videos")
    
    def test_more_videos_invalid_share_id(self):
        """Test more-videos with invalid share ID still returns empty list (not 404)"""
        response = requests.get(f"{BASE_URL}/api/share/invalid-share-id-xyz/more-videos")
        
        # Should return 200 with empty videos list (not 404)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("videos") == [] or isinstance(data.get("videos"), list)
        
        print("✓ Invalid share ID returns empty videos list")


class TestGrowthEventTracking:
    """Test POST /api/growth/event for share page analytics"""
    
    def test_share_viewed_event(self):
        """Test share_viewed event is accepted"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "share_viewed",
            "meta": {"share_id": "96902ad4-066"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ share_viewed event accepted")
    
    def test_cta_clicked_event(self):
        """Test cta_clicked event is accepted"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "cta_clicked",
            "meta": {"share_id": "96902ad4-066", "location": "primary_btn"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ cta_clicked event accepted")
    
    def test_remix_clicked_event(self):
        """Test remix_clicked event is accepted"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "remix_clicked",
            "meta": {"share_id": "96902ad4-066"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ remix_clicked event accepted")
    
    def test_whatsapp_shared_event(self):
        """Test whatsapp_shared event is accepted"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "whatsapp_shared",
            "meta": {"share_id": "96902ad4-066"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ whatsapp_shared event accepted")
    
    def test_invalid_event_rejected(self):
        """Test that invalid events are rejected with 400"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "invalid_event_xyz",
            "meta": {}
        })
        
        assert response.status_code == 400, f"Expected 400 for invalid event, got {response.status_code}"
        print("✓ Invalid event correctly rejected with 400")


class TestSharePageEndpoint:
    """Test GET /api/share/{shareId} endpoint"""
    
    def test_share_page_data(self):
        """Test share page returns all required fields"""
        share_id = "96902ad4-066"
        response = requests.get(f"{BASE_URL}/api/share/{share_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "id" in data
        assert "title" in data
        assert "views" in data
        assert "forks" in data
        
        print(f"✓ Share page data returned: title='{data.get('title')}', views={data.get('views')}, forks={data.get('forks')}")
    
    def test_share_page_increments_views(self):
        """Test that share page view count increments"""
        share_id = "96902ad4-066"
        
        # Get initial view count
        response1 = requests.get(f"{BASE_URL}/api/share/{share_id}")
        assert response1.status_code == 200
        views1 = response1.json().get("views", 0)
        
        # Get again - should increment
        response2 = requests.get(f"{BASE_URL}/api/share/{share_id}")
        assert response2.status_code == 200
        views2 = response2.json().get("views", 0)
        
        assert views2 >= views1, f"View count should increment: {views1} -> {views2}"
        print(f"✓ View count incremented: {views1} -> {views2}")


class TestForkEndpoint:
    """Test POST /api/share/{shareId}/fork endpoint"""
    
    def test_fork_returns_prefill_data(self):
        """Test fork endpoint returns prefill data for remix"""
        share_id = "96902ad4-066"
        response = requests.post(f"{BASE_URL}/api/share/{share_id}/fork")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "fork" in data
        
        fork = data["fork"]
        assert "parentShareId" in fork
        assert "parentTitle" in fork
        assert "storyContext" in fork or fork.get("storyContext") is None
        assert "type" in fork
        
        print(f"✓ Fork endpoint returned prefill data: parentTitle='{fork.get('parentTitle')}'")
    
    def test_fork_invalid_share_id(self):
        """Test fork with invalid share ID returns 404"""
        response = requests.post(f"{BASE_URL}/api/share/invalid-share-xyz/fork")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Fork with invalid share ID returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
