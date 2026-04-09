"""
Test Suite for Iteration 476:
1. Traffic Source Segmentation Dashboard for A/B tests
2. Character-Driven Auto-Share Prompts (SharePromptModal)

Tests cover:
- GET /api/ab/segmentation endpoint
- Segmentation response structure (source, total_impressions, variants, sufficient_data, confidence, winner)
- Sources sorted by total_impressions descending
- sufficient_data is false when impressions < 100 per variant per source
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed - skipping admin tests")


@pytest.fixture(scope="module")
def authenticated_admin_client(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestABSegmentationEndpoint:
    """Tests for GET /api/ab/segmentation endpoint"""
    
    def test_segmentation_endpoint_returns_200(self, api_client):
        """Test that segmentation endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/ab/segmentation?experiment_id=hero_headline")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Segmentation endpoint returns 200 OK")
    
    def test_segmentation_response_structure(self, api_client):
        """Test that segmentation response has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/ab/segmentation?experiment_id=hero_headline")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level fields
        assert "success" in data, "Response missing 'success' field"
        assert data["success"] == True, "success should be True"
        assert "experiment_id" in data, "Response missing 'experiment_id' field"
        assert data["experiment_id"] == "hero_headline", f"Expected experiment_id 'hero_headline', got {data['experiment_id']}"
        assert "min_source_sample" in data, "Response missing 'min_source_sample' field"
        assert data["min_source_sample"] == 100, f"Expected min_source_sample 100, got {data['min_source_sample']}"
        assert "sources" in data, "Response missing 'sources' field"
        assert isinstance(data["sources"], list), "sources should be a list"
        
        print(f"✓ Segmentation response has correct structure with {len(data['sources'])} sources")
    
    def test_segmentation_source_structure(self, api_client):
        """Test that each source in segmentation has correct fields"""
        response = api_client.get(f"{BASE_URL}/api/ab/segmentation?experiment_id=hero_headline")
        assert response.status_code == 200
        
        data = response.json()
        sources = data.get("sources", [])
        
        if len(sources) == 0:
            print("⚠ No sources found - this is expected if no traffic has been recorded yet")
            return
        
        for source in sources:
            # Check required fields for each source
            assert "source" in source, "Source missing 'source' field"
            assert "total_impressions" in source, "Source missing 'total_impressions' field"
            assert "variants" in source, "Source missing 'variants' field"
            assert "sufficient_data" in source, "Source missing 'sufficient_data' field"
            assert "confidence" in source, "Source missing 'confidence' field"
            assert "winner" in source, "Source missing 'winner' field"
            
            # Check variants structure
            assert isinstance(source["variants"], list), "variants should be a list"
            for variant in source["variants"]:
                assert "variant_id" in variant, "Variant missing 'variant_id' field"
                assert "label" in variant, "Variant missing 'label' field"
                assert "impressions" in variant, "Variant missing 'impressions' field"
                assert "clicks" in variant, "Variant missing 'clicks' field"
                assert "ctr" in variant, "Variant missing 'ctr' field"
        
        print(f"✓ All {len(sources)} sources have correct structure with variants")
    
    def test_segmentation_sources_sorted_by_impressions(self, api_client):
        """Test that sources are sorted by total_impressions descending"""
        response = api_client.get(f"{BASE_URL}/api/ab/segmentation?experiment_id=hero_headline")
        assert response.status_code == 200
        
        data = response.json()
        sources = data.get("sources", [])
        
        if len(sources) < 2:
            print("⚠ Less than 2 sources - cannot verify sorting")
            return
        
        # Verify descending order
        for i in range(len(sources) - 1):
            current_impressions = sources[i]["total_impressions"]
            next_impressions = sources[i + 1]["total_impressions"]
            assert current_impressions >= next_impressions, \
                f"Sources not sorted: {current_impressions} should be >= {next_impressions}"
        
        print(f"✓ Sources are correctly sorted by total_impressions descending")
    
    def test_segmentation_sufficient_data_threshold(self, api_client):
        """Test that sufficient_data is false when impressions < 100 per variant"""
        response = api_client.get(f"{BASE_URL}/api/ab/segmentation?experiment_id=hero_headline")
        assert response.status_code == 200
        
        data = response.json()
        sources = data.get("sources", [])
        min_sample = data.get("min_source_sample", 100)
        
        for source in sources:
            # Check if all variants have >= min_sample impressions
            all_sufficient = all(v["impressions"] >= min_sample for v in source["variants"])
            
            if all_sufficient:
                assert source["sufficient_data"] == True, \
                    f"Source {source['source']} should have sufficient_data=True (all variants >= {min_sample})"
            else:
                assert source["sufficient_data"] == False, \
                    f"Source {source['source']} should have sufficient_data=False (some variants < {min_sample})"
        
        print(f"✓ sufficient_data correctly reflects {min_sample} impressions threshold")
    
    def test_segmentation_winner_only_with_sufficient_data(self, api_client):
        """Test that winner is only set when sufficient_data is True and confidence >= 95"""
        response = api_client.get(f"{BASE_URL}/api/ab/segmentation?experiment_id=hero_headline")
        assert response.status_code == 200
        
        data = response.json()
        sources = data.get("sources", [])
        
        for source in sources:
            if not source["sufficient_data"]:
                assert source["winner"] is None, \
                    f"Source {source['source']} should not have winner when sufficient_data=False"
            elif source["confidence"] < 95:
                assert source["winner"] is None, \
                    f"Source {source['source']} should not have winner when confidence < 95%"
        
        print("✓ Winner logic correctly respects sufficient_data and confidence thresholds")
    
    def test_segmentation_invalid_experiment(self, api_client):
        """Test segmentation with invalid experiment_id"""
        response = api_client.get(f"{BASE_URL}/api/ab/segmentation?experiment_id=nonexistent_experiment")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert len(data.get("sources", [])) == 0, "Should return empty sources for invalid experiment"
        
        print("✓ Invalid experiment returns empty sources gracefully")


class TestABEventsTracking:
    """Tests for ab_events tracking that feeds segmentation"""
    
    def test_public_ab_impression_with_traffic_source(self, api_client):
        """Test that public ab-impression endpoint accepts traffic_source"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/public/ab-impression", json={
            "session_id": session_id,
            "experiment_id": "hero_headline",
            "variant": "headline_a",
            "action": "impression",
            "traffic_source": "direct"
        })
        
        # Should return 200 or 201
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        print("✓ Public ab-impression accepts traffic_source field")
    
    def test_public_ab_impression_cta_click(self, api_client):
        """Test that cta_click action is tracked"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/public/ab-impression", json={
            "session_id": session_id,
            "experiment_id": "hero_headline",
            "variant": "headline_b",
            "action": "cta_click",
            "traffic_source": "instagram"
        })
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        print("✓ Public ab-impression tracks cta_click action")


class TestABResultsEndpoint:
    """Tests for GET /api/ab/results endpoint (existing functionality)"""
    
    def test_ab_results_hero_headline(self, api_client):
        """Test that hero_headline experiment is returned in results"""
        response = api_client.get(f"{BASE_URL}/api/ab/results?experiment_id=hero_headline")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "experiments" in data
        assert len(data["experiments"]) > 0, "Should have at least one experiment"
        
        exp = data["experiments"][0]
        assert exp["experiment_id"] == "hero_headline"
        assert "variants" in exp
        assert len(exp["variants"]) == 2, "hero_headline should have 2 variants"
        
        print(f"✓ hero_headline experiment found with {len(exp['variants'])} variants")


class TestLandingPageLoads:
    """Test that landing page still loads correctly"""
    
    def test_landing_page_accessible(self, api_client):
        """Test that landing page is accessible"""
        response = api_client.get(f"{BASE_URL}/")
        # Landing page should return 200 or redirect
        assert response.status_code in [200, 301, 302, 304], f"Landing page returned {response.status_code}"
        print("✓ Landing page is accessible")
    
    def test_health_endpoint(self, api_client):
        """Test health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("✓ Health endpoint returns 200")


class TestSharePromptAnalyticsEvents:
    """Tests for share prompt analytics events (backend tracking via /api/growth/event)
    
    Note: SharePromptModal uses trackEvent() from analytics.js for GA4 tracking (client-side).
    The backend /api/growth/event endpoint tracks share_click events.
    """
    
    def test_growth_event_share_click(self, api_client):
        """Test that share_click event can be tracked via /api/growth/event"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/growth/event", json={
            "event": "share_click",
            "session_id": session_id,
            "meta": {
                "job_id": "test_job_123",
                "platform": "instagram",
                "source": "auto_share_prompt"
            }
        })
        
        # Should accept the event
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        print("✓ share_click event can be tracked via /api/growth/event")
    
    def test_growth_event_share_viewed(self, api_client):
        """Test that share_viewed event can be tracked"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/growth/event", json={
            "event": "share_viewed",
            "session_id": session_id,
            "meta": {
                "job_id": "test_job_123"
            }
        })
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        print("✓ share_viewed event can be tracked")
    
    def test_growth_event_share(self, api_client):
        """Test that share event can be tracked"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/growth/event", json={
            "event": "share",
            "session_id": session_id,
            "meta": {
                "job_id": "test_job_123",
                "platform": "whatsapp"
            }
        })
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        print("✓ share event can be tracked")
    
    def test_growth_event_invalid_event_rejected(self, api_client):
        """Test that invalid events are rejected"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/growth/event", json={
            "event": "invalid_event_name_xyz",
            "session_id": session_id
        })
        
        assert response.status_code == 400, f"Expected 400 for invalid event, got {response.status_code}"
        print("✓ Invalid events are correctly rejected with 400")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
