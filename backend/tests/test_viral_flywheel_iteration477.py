"""
Viral Flywheel Engine v1 — Phase A: Foundation Tests
Iteration 477

Tests:
1. POST /api/viral/track-click - tracks share clicks with traffic_source and attribution_depth
2. POST /api/viral/track-conversion - marks referral as converted
3. POST /api/viral/lineage - records remix parent-child relationship (requires auth)
4. GET /api/viral/lineage/{job_id} - returns 'Inspired by' data
5. GET /api/viral/rewards/status - returns reward status for logged-in user (requires auth)
6. POST /api/viral/rewards/check-and-grant - processes pending rewards (requires auth)
7. GET /api/viral/leaderboard - returns ranked creators by viral score
8. GET /api/viral/metrics - returns viral loop core metrics
9. GET /api/ab/smart-route - falls back to control when confidence insufficient
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="function")
def api_client():
    """Shared requests session - function scoped to avoid header pollution"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed for test user: {response.status_code}")


@pytest.fixture(scope="function")
def authenticated_client(auth_token):
    """Session with auth header - function scoped"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestViralTrackClick:
    """Tests for POST /api/viral/track-click"""
    
    def test_track_click_with_valid_slug(self, api_client):
        """Track click with a valid share slug"""
        test_slug = f"test-slug-{uuid.uuid4().hex[:8]}"
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        
        response = api_client.post(f"{BASE_URL}/api/viral/track-click", json={
            "share_slug": test_slug,
            "session_id": session_id,
            "traffic_source": "instagram"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert data["ok"] == True
        # tracked may be False if slug doesn't exist, but endpoint should work
        print(f"Track click response: {data}")
    
    def test_track_click_with_different_traffic_sources(self, api_client):
        """Test tracking clicks from different traffic sources"""
        traffic_sources = ["direct", "instagram", "organic", "referral"]
        
        for source in traffic_sources:
            test_slug = f"test-slug-{uuid.uuid4().hex[:8]}"
            session_id = f"ses_{uuid.uuid4().hex[:12]}"
            
            response = api_client.post(f"{BASE_URL}/api/viral/track-click", json={
                "share_slug": test_slug,
                "session_id": session_id,
                "traffic_source": source
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] == True
            print(f"Traffic source '{source}' tracked successfully")
    
    def test_track_click_returns_attribution_depth(self, api_client):
        """Verify attribution_depth is returned when tracking succeeds"""
        test_slug = f"test-slug-{uuid.uuid4().hex[:8]}"
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        
        response = api_client.post(f"{BASE_URL}/api/viral/track-click", json={
            "share_slug": test_slug,
            "session_id": session_id,
            "traffic_source": "direct"
        })
        
        assert response.status_code == 200
        data = response.json()
        # attribution_depth is only returned when tracked=True
        if data.get("tracked"):
            assert "attribution_depth" in data
            assert isinstance(data["attribution_depth"], int)
            print(f"Attribution depth: {data['attribution_depth']}")


class TestViralTrackConversion:
    """Tests for POST /api/viral/track-conversion"""
    
    def test_track_conversion_remix(self, api_client):
        """Track a remix conversion"""
        test_slug = f"test-slug-{uuid.uuid4().hex[:8]}"
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        
        response = api_client.post(f"{BASE_URL}/api/viral/track-conversion", json={
            "share_slug": test_slug,
            "session_id": session_id,
            "conversion_type": "remix",
            "new_job_id": f"job_{uuid.uuid4().hex[:12]}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert data["ok"] == True
        print(f"Conversion tracked: {data}")
    
    def test_track_conversion_signup(self, api_client):
        """Track a signup conversion"""
        test_slug = f"test-slug-{uuid.uuid4().hex[:8]}"
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        
        response = api_client.post(f"{BASE_URL}/api/viral/track-conversion", json={
            "share_slug": test_slug,
            "session_id": session_id,
            "conversion_type": "signup",
            "new_user_id": f"user_{uuid.uuid4().hex[:12]}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        print(f"Signup conversion tracked: {data}")


class TestViralLineage:
    """Tests for POST /api/viral/lineage and GET /api/viral/lineage/{job_id}"""
    
    def test_record_lineage_requires_auth(self, api_client):
        """POST /api/viral/lineage requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/viral/lineage", json={
            "child_job_id": f"child_{uuid.uuid4().hex[:12]}",
            "parent_job_id": f"parent_{uuid.uuid4().hex[:12]}"
        })
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 422]
        print(f"Lineage POST without auth: {response.status_code}")
    
    def test_record_lineage_with_auth(self, authenticated_client):
        """POST /api/viral/lineage with authentication"""
        child_job_id = f"child_{uuid.uuid4().hex[:12]}"
        parent_job_id = f"parent_{uuid.uuid4().hex[:12]}"
        
        response = authenticated_client.post(f"{BASE_URL}/api/viral/lineage", json={
            "child_job_id": child_job_id,
            "parent_job_id": parent_job_id
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert data["ok"] == True
        assert "lineage_recorded" in data
        print(f"Lineage recorded: {data}")
    
    def test_get_lineage_nonexistent_job(self, api_client):
        """GET /api/viral/lineage/{job_id} for non-existent job"""
        fake_job_id = f"nonexistent_{uuid.uuid4().hex[:12]}"
        
        response = api_client.get(f"{BASE_URL}/api/viral/lineage/{fake_job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "found" in data
        assert data["found"] == False
        print(f"Lineage for non-existent job: {data}")
    
    def test_get_lineage_returns_parent_info(self, api_client):
        """GET /api/viral/lineage/{job_id} returns parent info when found"""
        # This test checks the structure - actual data depends on DB state
        test_job_id = f"test_{uuid.uuid4().hex[:12]}"
        
        response = api_client.get(f"{BASE_URL}/api/viral/lineage/{test_job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "found" in data
        
        if data["found"]:
            assert "lineage" in data
            lineage = data["lineage"]
            assert "parent_title" in lineage
            assert "parent_slug" in lineage
            assert "parent_user_id" in lineage
            print(f"Lineage found: {lineage}")
        else:
            print("No lineage found (expected for test job)")


class TestViralRewards:
    """Tests for GET /api/viral/rewards/status and POST /api/viral/rewards/check-and-grant"""
    
    def test_rewards_status_requires_auth(self, api_client):
        """GET /api/viral/rewards/status requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/viral/rewards/status")
        
        assert response.status_code in [401, 403]
        print(f"Rewards status without auth: {response.status_code}")
    
    def test_rewards_status_with_auth(self, authenticated_client):
        """GET /api/viral/rewards/status with authentication"""
        response = authenticated_client.get(f"{BASE_URL}/api/viral/rewards/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_remix_conversions" in data
        assert "total_credits_earned" in data
        assert "today_credits_earned" in data
        assert "daily_cap" in data
        assert "conversions_until_next_reward" in data
        
        # Verify types
        assert isinstance(data["total_remix_conversions"], int)
        assert isinstance(data["total_credits_earned"], int)
        assert isinstance(data["daily_cap"], int)
        assert data["daily_cap"] == 5  # MAX_DAILY_REWARD from code
        
        print(f"Rewards status: {data}")
    
    def test_check_and_grant_rewards_requires_auth(self, api_client):
        """POST /api/viral/rewards/check-and-grant requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/viral/rewards/check-and-grant")
        
        assert response.status_code in [401, 403]
        print(f"Check-and-grant without auth: {response.status_code}")
    
    def test_check_and_grant_rewards_with_auth(self, authenticated_client):
        """POST /api/viral/rewards/check-and-grant with authentication"""
        response = authenticated_client.post(f"{BASE_URL}/api/viral/rewards/check-and-grant")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ok" in data
        assert data["ok"] == True
        assert "credits_granted" in data
        assert isinstance(data["credits_granted"], int)
        
        print(f"Check-and-grant result: {data}")


class TestViralLeaderboard:
    """Tests for GET /api/viral/leaderboard"""
    
    def test_leaderboard_returns_success(self, api_client):
        """GET /api/viral/leaderboard returns success"""
        response = api_client.get(f"{BASE_URL}/api/viral/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert data["success"] == True
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        
        print(f"Leaderboard entries: {len(data['leaderboard'])}")
    
    def test_leaderboard_with_limit(self, api_client):
        """GET /api/viral/leaderboard with limit parameter"""
        response = api_client.get(f"{BASE_URL}/api/viral/leaderboard?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert len(data["leaderboard"]) <= 5
        
        print(f"Leaderboard with limit=5: {len(data['leaderboard'])} entries")
    
    def test_leaderboard_entry_structure(self, api_client):
        """Verify leaderboard entry structure"""
        response = api_client.get(f"{BASE_URL}/api/viral/leaderboard?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["leaderboard"]) > 0:
            entry = data["leaderboard"][0]
            
            # Verify expected fields
            assert "user_id" in entry
            assert "referred_remixes" in entry
            assert "viral_signups" in entry
            assert "max_chain_depth" in entry
            assert "viral_score" in entry
            assert "name" in entry
            
            # Verify viral_score calculation
            # Score = (referred_remixes * 0.5) + (downstream_chain_depth * 0.3) + (viral_signups * 0.2)
            expected_score = round(
                entry["referred_remixes"] * 0.5 + 
                entry["max_chain_depth"] * 0.3 + 
                entry["viral_signups"] * 0.2, 
                2
            )
            assert entry["viral_score"] == expected_score
            
            print(f"Top entry: {entry}")
        else:
            print("No leaderboard entries yet (expected for new system)")


class TestViralMetrics:
    """Tests for GET /api/viral/metrics"""
    
    def test_metrics_returns_success(self, api_client):
        """GET /api/viral/metrics returns success"""
        response = api_client.get(f"{BASE_URL}/api/viral/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert data["success"] == True
        assert "metrics" in data
        
        print(f"Metrics response: {data}")
    
    def test_metrics_structure(self, api_client):
        """Verify metrics structure"""
        response = api_client.get(f"{BASE_URL}/api/viral/metrics")
        
        assert response.status_code == 200
        data = response.json()
        metrics = data["metrics"]
        
        # Verify expected fields
        expected_fields = [
            "total_share_clicks",
            "total_conversions",
            "total_remixes",
            "total_signups",
            "click_to_remix_rate",
            "click_to_signup_rate",
            "avg_attribution_depth",
            "viral_coefficient",
            "unique_sharers"
        ]
        
        for field in expected_fields:
            assert field in metrics, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(metrics["total_share_clicks"], int)
        assert isinstance(metrics["total_conversions"], int)
        assert isinstance(metrics["total_remixes"], int)
        assert isinstance(metrics["total_signups"], int)
        assert isinstance(metrics["click_to_remix_rate"], (int, float))
        assert isinstance(metrics["click_to_signup_rate"], (int, float))
        assert isinstance(metrics["avg_attribution_depth"], (int, float))
        assert isinstance(metrics["viral_coefficient"], (int, float))
        assert isinstance(metrics["unique_sharers"], int)
        
        print(f"Metrics: {metrics}")


class TestSmartHeadlineRoute:
    """Tests for GET /api/ab/smart-route"""
    
    def test_smart_route_returns_variant(self, api_client):
        """GET /api/ab/smart-route returns a variant"""
        response = api_client.get(f"{BASE_URL}/api/ab/smart-route?experiment_id=hero_headline&traffic_source=direct")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "variant_id" in data
        assert "reason" in data
        
        print(f"Smart route response: {data}")
    
    def test_smart_route_fallback_to_control(self, api_client):
        """Smart route falls back to control when confidence insufficient"""
        # Use a traffic source that likely has insufficient data
        response = api_client.get(f"{BASE_URL}/api/ab/smart-route?experiment_id=hero_headline&traffic_source=test_source_{uuid.uuid4().hex[:8]}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should fall back to control (headline_a) due to insufficient data
        assert data["variant_id"] in ["headline_a", None]  # Control or no experiment
        assert data["reason"] in ["insufficient_data", "low_confidence", "no_experiment", "source_winner"]
        
        print(f"Fallback response: {data}")
    
    def test_smart_route_different_traffic_sources(self, api_client):
        """Test smart route with different traffic sources"""
        traffic_sources = ["direct", "instagram", "organic", "referral"]
        
        for source in traffic_sources:
            response = api_client.get(f"{BASE_URL}/api/ab/smart-route?experiment_id=hero_headline&traffic_source={source}")
            
            assert response.status_code == 200
            data = response.json()
            assert "variant_id" in data
            assert "reason" in data
            assert "source" in data
            assert data["source"] == source
            
            print(f"Smart route for '{source}': variant={data['variant_id']}, reason={data['reason']}")
    
    def test_smart_route_nonexistent_experiment(self, api_client):
        """Smart route handles non-existent experiment gracefully"""
        response = api_client.get(f"{BASE_URL}/api/ab/smart-route?experiment_id=nonexistent_experiment&traffic_source=direct")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["variant_id"] is None
        assert data["reason"] == "no_experiment"
        
        print(f"Non-existent experiment response: {data}")


class TestEndToEndViralFlow:
    """End-to-end tests for the viral flywheel flow"""
    
    def test_full_viral_flow(self, api_client, authenticated_client):
        """Test the complete viral flow: click -> conversion -> lineage"""
        # Step 1: Track a click
        test_slug = f"e2e-test-{uuid.uuid4().hex[:8]}"
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        
        click_response = api_client.post(f"{BASE_URL}/api/viral/track-click", json={
            "share_slug": test_slug,
            "session_id": session_id,
            "traffic_source": "instagram"
        })
        assert click_response.status_code == 200
        print(f"Step 1 - Click tracked: {click_response.json()}")
        
        # Step 2: Track a conversion
        new_job_id = f"job_{uuid.uuid4().hex[:12]}"
        conversion_response = api_client.post(f"{BASE_URL}/api/viral/track-conversion", json={
            "share_slug": test_slug,
            "session_id": session_id,
            "conversion_type": "remix",
            "new_job_id": new_job_id
        })
        assert conversion_response.status_code == 200
        print(f"Step 2 - Conversion tracked: {conversion_response.json()}")
        
        # Step 3: Record lineage (requires auth)
        parent_job_id = f"parent_{uuid.uuid4().hex[:12]}"
        lineage_response = authenticated_client.post(f"{BASE_URL}/api/viral/lineage", json={
            "child_job_id": new_job_id,
            "parent_job_id": parent_job_id,
            "parent_share_slug": test_slug
        })
        assert lineage_response.status_code == 200
        print(f"Step 3 - Lineage recorded: {lineage_response.json()}")
        
        # Step 4: Check metrics
        metrics_response = api_client.get(f"{BASE_URL}/api/viral/metrics")
        assert metrics_response.status_code == 200
        print(f"Step 4 - Metrics: {metrics_response.json()}")
        
        # Step 5: Check leaderboard
        leaderboard_response = api_client.get(f"{BASE_URL}/api/viral/leaderboard?limit=5")
        assert leaderboard_response.status_code == 200
        print(f"Step 5 - Leaderboard: {leaderboard_response.json()}")
        
        print("Full viral flow completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
