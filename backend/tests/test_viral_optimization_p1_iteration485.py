"""
P1 Viral Optimization Sprint - Backend API Tests
Tests for:
1. GET /api/viral/story-momentum/{job_id} - Public momentum API
2. Response structure validation
3. Momentum level calculation logic
4. Badge generation logic
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestViralMomentumAPI:
    """Tests for the public story momentum API endpoint"""

    def test_momentum_api_returns_200_for_any_job_id(self):
        """Momentum API should return 200 for any job_id (public, no auth)"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/test-job-123")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Momentum API returns 200 for any job_id")

    def test_momentum_api_response_structure(self):
        """Verify response contains all required fields"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/test-job-456")
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            'success', 'job_id', 'momentum_level', 'momentum_label',
            'total_remixes', 'chain_depth', 'badges'
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify types
        assert isinstance(data['success'], bool), "success should be boolean"
        assert isinstance(data['momentum_level'], str), "momentum_level should be string"
        assert isinstance(data['momentum_label'], str), "momentum_label should be string"
        assert isinstance(data['total_remixes'], int), "total_remixes should be int"
        assert isinstance(data['chain_depth'], int), "chain_depth should be int"
        assert isinstance(data['badges'], list), "badges should be list"
        
        print("PASS: Response structure is correct")

    def test_momentum_api_returns_success_true(self):
        """API should always return success: true"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/any-job-id")
        data = response.json()
        assert data['success'] is True, "Expected success: true"
        print("PASS: API returns success: true")

    def test_momentum_api_returns_job_id_in_response(self):
        """API should echo back the job_id in response"""
        test_job_id = "my-unique-job-id-789"
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/{test_job_id}")
        data = response.json()
        assert data['job_id'] == test_job_id, f"Expected job_id {test_job_id}, got {data['job_id']}"
        print("PASS: API echoes back job_id correctly")

    def test_momentum_level_new_for_no_traction(self):
        """New stories with no traction should have momentum_level='new'"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/brand-new-story-no-traction")
        data = response.json()
        assert data['momentum_level'] == 'new', f"Expected 'new', got {data['momentum_level']}"
        assert data['momentum_label'] == 'New', f"Expected 'New', got {data['momentum_label']}"
        print("PASS: New stories have momentum_level='new'")

    def test_momentum_api_badges_array_structure(self):
        """Badges array should have correct structure when present"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/test-badges-structure")
        data = response.json()
        
        # For new stories, badges should be empty
        assert isinstance(data['badges'], list), "badges should be a list"
        
        # If badges exist, verify structure
        if len(data['badges']) > 0:
            badge = data['badges'][0]
            assert 'id' in badge, "Badge should have 'id'"
            assert 'label' in badge, "Badge should have 'label'"
            assert 'tier' in badge, "Badge should have 'tier'"
        
        print("PASS: Badges array structure is correct")

    def test_momentum_api_no_auth_required(self):
        """Momentum API should work without authentication"""
        # No auth headers
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/public-test")
        assert response.status_code == 200, "API should work without auth"
        assert response.json()['success'] is True
        print("PASS: No authentication required for momentum API")

    def test_momentum_api_handles_special_characters_in_job_id(self):
        """API should handle special characters in job_id"""
        # Test with URL-safe characters
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/job-with-dashes-123")
        assert response.status_code == 200
        print("PASS: API handles special characters in job_id")

    def test_momentum_api_returns_additional_stats(self):
        """API should return additional stats like remixes_24h, remixes_7d, total_shares, total_views"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/stats-test")
        data = response.json()
        
        # Check for additional stats fields
        assert 'remixes_24h' in data, "Should have remixes_24h"
        assert 'remixes_7d' in data, "Should have remixes_7d"
        assert 'total_shares' in data, "Should have total_shares"
        assert 'total_views' in data, "Should have total_views"
        
        # All should be integers
        assert isinstance(data['remixes_24h'], int)
        assert isinstance(data['remixes_7d'], int)
        assert isinstance(data['total_shares'], int)
        assert isinstance(data['total_views'], int)
        
        print("PASS: API returns all additional stats")


class TestMomentumLevelLogic:
    """Tests for momentum level calculation logic"""

    def test_valid_momentum_levels(self):
        """Momentum level should be one of the valid values"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/level-test")
        data = response.json()
        
        valid_levels = ['viral_surge', 'spreading_widely', 'trending', 'rising_fast', 'warming_up', 'new']
        assert data['momentum_level'] in valid_levels, f"Invalid momentum level: {data['momentum_level']}"
        print("PASS: Momentum level is valid")

    def test_momentum_label_matches_level(self):
        """Momentum label should match the level"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/label-test")
        data = response.json()
        
        level_to_label = {
            'viral_surge': 'Viral Surge',
            'spreading_widely': 'Spreading Widely',
            'trending': 'Trending Now',
            'rising_fast': 'Rising Fast',
            'warming_up': 'Warming Up',
            'new': 'New'
        }
        
        expected_label = level_to_label.get(data['momentum_level'])
        assert data['momentum_label'] == expected_label, f"Label mismatch: expected {expected_label}, got {data['momentum_label']}"
        print("PASS: Momentum label matches level")


class TestBadgeLogic:
    """Tests for badge generation logic"""

    def test_badges_empty_for_new_stories(self):
        """New stories with no remixes should have empty badges"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/no-badges-test")
        data = response.json()
        
        if data['total_remixes'] == 0 and data['chain_depth'] == 0:
            assert len(data['badges']) == 0, "New stories should have no badges"
        print("PASS: New stories have empty badges")

    def test_badge_tier_values(self):
        """Badge tiers should be bronze, silver, or gold"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/tier-test")
        data = response.json()
        
        valid_tiers = ['bronze', 'silver', 'gold']
        for badge in data['badges']:
            assert badge['tier'] in valid_tiers, f"Invalid tier: {badge['tier']}"
        print("PASS: Badge tiers are valid")


class TestHealthAndBasics:
    """Basic health and connectivity tests"""

    def test_backend_health(self):
        """Backend should be healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        print("PASS: Backend is healthy")

    def test_viral_flywheel_router_mounted(self):
        """Viral flywheel router should be mounted"""
        response = requests.get(f"{BASE_URL}/api/viral/story-momentum/router-test")
        assert response.status_code == 200, "Viral flywheel router should be mounted"
        print("PASS: Viral flywheel router is mounted")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
