"""
CreatorStudio AI - Auto-Scaling & Priority Lanes API Tests
==========================================================
Tests for:
1. /api/scaling/status - Get current workers, min/max, running state, active rules
2. /api/scaling/dashboard - Get scaling config, priority lanes, queue by tier
3. /api/scaling/priority/lanes - Get all tier configurations (free, basic, pro, enterprise)
4. /api/scaling/manual - Manual worker scaling (admin only)
5. /api/scaling/rules - Get configured scaling rules
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestScalingAPIs:
    """Test auto-scaling and priority lanes backend APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.admin_token = response.json().get("token")
        assert self.admin_token, "No token returned from login"
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    # ==================================
    # Scaling Status Tests
    # ==================================
    
    def test_scaling_status_returns_200(self):
        """Test /api/scaling/status returns 200 for admin"""
        response = requests.get(f"{BASE_URL}/api/scaling/status", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_scaling_status_has_required_fields(self):
        """Test /api/scaling/status contains current_workers, min_workers, max_workers, running, active_rules"""
        response = requests.get(f"{BASE_URL}/api/scaling/status", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields exist
        assert "current_workers" in data, "Missing current_workers field"
        assert "min_workers" in data, "Missing min_workers field"
        assert "max_workers" in data, "Missing max_workers field"
        assert "running" in data, "Missing running field"
        assert "active_rules" in data, "Missing active_rules field"
        
        # Validate types
        assert isinstance(data["current_workers"], int), "current_workers should be int"
        assert isinstance(data["min_workers"], int), "min_workers should be int"
        assert isinstance(data["max_workers"], int), "max_workers should be int"
        assert isinstance(data["running"], bool), "running should be bool"
        assert isinstance(data["active_rules"], list), "active_rules should be list"
    
    def test_scaling_status_has_queue_stats(self):
        """Test /api/scaling/status includes queue_stats with pending, processing counts"""
        response = requests.get(f"{BASE_URL}/api/scaling/status", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "queue_stats" in data, "Missing queue_stats field"
        queue_stats = data["queue_stats"]
        assert "pending" in queue_stats, "Missing pending in queue_stats"
        assert "processing" in queue_stats, "Missing processing in queue_stats"
        assert "total_active" in queue_stats, "Missing total_active in queue_stats"
    
    def test_scaling_status_requires_auth(self):
        """Test /api/scaling/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scaling/status")
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated, got {response.status_code}"
    
    # ==================================
    # Scaling Dashboard Tests
    # ==================================
    
    def test_scaling_dashboard_returns_200(self):
        """Test /api/scaling/dashboard returns 200 for admin"""
        response = requests.get(f"{BASE_URL}/api/scaling/dashboard", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_scaling_dashboard_has_required_fields(self):
        """Test /api/scaling/dashboard contains scaling, priority_lanes, queue_by_tier"""
        response = requests.get(f"{BASE_URL}/api/scaling/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check required top-level fields
        assert "scaling" in data, "Missing scaling field"
        assert "priority_lanes" in data, "Missing priority_lanes field"
        assert "queue_by_tier" in data, "Missing queue_by_tier field"
        assert "timestamp" in data, "Missing timestamp field"
    
    def test_scaling_dashboard_scaling_config(self):
        """Test /api/scaling/dashboard scaling config contains workers info"""
        response = requests.get(f"{BASE_URL}/api/scaling/dashboard", headers=self.headers)
        assert response.status_code == 200
        scaling = response.json().get("scaling", {})
        
        assert "current_workers" in scaling, "Missing current_workers in scaling"
        assert "min_workers" in scaling, "Missing min_workers in scaling"
        assert "max_workers" in scaling, "Missing max_workers in scaling"
        assert "running" in scaling, "Missing running in scaling"
    
    def test_scaling_dashboard_priority_lanes(self):
        """Test /api/scaling/dashboard has all 4 priority lanes"""
        response = requests.get(f"{BASE_URL}/api/scaling/dashboard", headers=self.headers)
        assert response.status_code == 200
        priority_lanes = response.json().get("priority_lanes", {})
        
        expected_tiers = ["free", "basic", "pro", "enterprise"]
        for tier in expected_tiers:
            assert tier in priority_lanes, f"Missing {tier} tier in priority_lanes"
    
    def test_scaling_dashboard_queue_by_tier(self):
        """Test /api/scaling/dashboard has queue counts for all 4 tiers"""
        response = requests.get(f"{BASE_URL}/api/scaling/dashboard", headers=self.headers)
        assert response.status_code == 200
        queue_by_tier = response.json().get("queue_by_tier", {})
        
        expected_tiers = ["free", "basic", "pro", "enterprise"]
        for tier in expected_tiers:
            assert tier in queue_by_tier, f"Missing {tier} tier in queue_by_tier"
            assert isinstance(queue_by_tier[tier], int), f"Queue count for {tier} should be int"
    
    def test_scaling_dashboard_requires_admin(self):
        """Test /api/scaling/dashboard requires admin role"""
        # Login as regular user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            user_token = response.json().get("token")
            user_headers = {"Authorization": f"Bearer {user_token}"}
            response = requests.get(f"{BASE_URL}/api/scaling/dashboard", headers=user_headers)
            assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    # ==================================
    # Priority Lanes Tests
    # ==================================
    
    def test_priority_lanes_returns_200(self):
        """Test /api/scaling/priority/lanes returns 200 for admin"""
        response = requests.get(f"{BASE_URL}/api/scaling/priority/lanes", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_priority_lanes_has_all_tiers(self):
        """Test /api/scaling/priority/lanes returns all 4 tier configurations"""
        response = requests.get(f"{BASE_URL}/api/scaling/priority/lanes", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "lanes" in data, "Missing lanes field"
        lanes = data["lanes"]
        
        expected_tiers = ["free", "basic", "pro", "enterprise"]
        for tier in expected_tiers:
            assert tier in lanes, f"Missing {tier} tier in lanes"
    
    def test_priority_lanes_tier_config(self):
        """Test priority lanes have correct tier configurations"""
        response = requests.get(f"{BASE_URL}/api/scaling/priority/lanes", headers=self.headers)
        assert response.status_code == 200
        lanes = response.json().get("lanes", {})
        
        # Verify enterprise tier has config
        enterprise = lanes.get("enterprise", {})
        assert "config" in enterprise, "Missing config in enterprise tier"
        config = enterprise["config"]
        
        # Check expected SLAs and configuration
        assert "sla_seconds" in config, "Missing sla_seconds in config"
        assert "priority" in config, "Missing priority in config"
        assert "max_concurrent_jobs" in config, "Missing max_concurrent_jobs in config"
        
        # Verify priorities: Enterprise (1) > Pro (2) > Basic (3) > Free (4)
        assert lanes.get("enterprise", {}).get("config", {}).get("priority") == 1, "Enterprise should have priority 1"
        assert lanes.get("pro", {}).get("config", {}).get("priority") == 2, "Pro should have priority 2"
        assert lanes.get("basic", {}).get("config", {}).get("priority") == 3, "Basic should have priority 3"
        assert lanes.get("free", {}).get("config", {}).get("priority") == 4, "Free should have priority 4"
    
    def test_priority_lanes_sla_values(self):
        """Test priority lanes have correct SLA values"""
        response = requests.get(f"{BASE_URL}/api/scaling/priority/lanes", headers=self.headers)
        assert response.status_code == 200
        lanes = response.json().get("lanes", {})
        
        # Expected SLAs: Enterprise 30s, Pro 60s, Basic 120s, Free 300s
        assert lanes.get("enterprise", {}).get("config", {}).get("sla_seconds") == 30, "Enterprise SLA should be 30s"
        assert lanes.get("pro", {}).get("config", {}).get("sla_seconds") == 60, "Pro SLA should be 60s"
        assert lanes.get("basic", {}).get("config", {}).get("sla_seconds") == 120, "Basic SLA should be 120s"
        assert lanes.get("free", {}).get("config", {}).get("sla_seconds") == 300, "Free SLA should be 300s"
    
    # ==================================
    # Scaling Rules Tests
    # ==================================
    
    def test_scaling_rules_returns_200(self):
        """Test /api/scaling/rules returns 200 for admin"""
        response = requests.get(f"{BASE_URL}/api/scaling/rules", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_scaling_rules_has_required_rules(self):
        """Test /api/scaling/rules contains expected default rules"""
        response = requests.get(f"{BASE_URL}/api/scaling/rules", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "rules" in data, "Missing rules field"
        assert "count" in data, "Missing count field"
        
        rules = data["rules"]
        assert len(rules) >= 1, "Should have at least one rule"
        
        # Get rule names
        rule_names = [r.get("name") for r in rules]
        
        # Should have scale up rules
        expected_up_rules = ["high_queue_depth", "very_high_queue_depth", "high_latency", "premium_queue_growing"]
        for rule in expected_up_rules:
            assert rule in rule_names, f"Missing scale up rule: {rule}"
        
        # Should have scale down rules
        expected_down_rules = ["low_queue_depth", "very_low_queue_depth"]
        for rule in expected_down_rules:
            assert rule in rule_names, f"Missing scale down rule: {rule}"
    
    def test_scaling_rules_rule_structure(self):
        """Test scaling rules have correct structure"""
        response = requests.get(f"{BASE_URL}/api/scaling/rules", headers=self.headers)
        assert response.status_code == 200
        rules = response.json().get("rules", [])
        
        if rules:
            rule = rules[0]
            # Check required fields
            assert "name" in rule, "Rule missing name"
            assert "metric" in rule, "Rule missing metric"
            assert "operator" in rule, "Rule missing operator"
            assert "threshold" in rule, "Rule missing threshold"
            assert "action" in rule, "Rule missing action"
            assert "enabled" in rule, "Rule missing enabled"
    
    # ==================================
    # Manual Scaling Tests
    # ==================================
    
    def test_manual_scale_up(self):
        """Test /api/scaling/manual can scale up workers"""
        # Get current workers
        status_response = requests.get(f"{BASE_URL}/api/scaling/status", headers=self.headers)
        assert status_response.status_code == 200
        current_workers = status_response.json().get("current_workers", 2)
        max_workers = status_response.json().get("max_workers", 20)
        
        # Scale up by 1 (if not at max)
        if current_workers < max_workers:
            target_workers = current_workers + 1
            response = requests.post(
                f"{BASE_URL}/api/scaling/manual",
                headers=self.headers,
                json={
                    "target_workers": target_workers,
                    "reason": "TEST_manual_scale_up"
                }
            )
            assert response.status_code == 200, f"Scale up failed: {response.text}"
            data = response.json()
            assert data.get("success") == True, "Scale up should succeed"
            
            # Verify new worker count
            status_response = requests.get(f"{BASE_URL}/api/scaling/status", headers=self.headers)
            assert status_response.json().get("current_workers") == target_workers
    
    def test_manual_scale_down(self):
        """Test /api/scaling/manual can scale down workers"""
        # Get current workers
        status_response = requests.get(f"{BASE_URL}/api/scaling/status", headers=self.headers)
        assert status_response.status_code == 200
        current_workers = status_response.json().get("current_workers", 2)
        min_workers = status_response.json().get("min_workers", 2)
        
        # Scale down by 1 (if not at min)
        if current_workers > min_workers:
            target_workers = current_workers - 1
            response = requests.post(
                f"{BASE_URL}/api/scaling/manual",
                headers=self.headers,
                json={
                    "target_workers": target_workers,
                    "reason": "TEST_manual_scale_down"
                }
            )
            assert response.status_code == 200, f"Scale down failed: {response.text}"
            data = response.json()
            assert data.get("success") == True, "Scale down should succeed"
    
    def test_manual_scale_enforces_limits(self):
        """Test manual scaling respects min/max limits"""
        # Get limits
        status_response = requests.get(f"{BASE_URL}/api/scaling/status", headers=self.headers)
        assert status_response.status_code == 200
        max_workers = status_response.json().get("max_workers", 20)
        
        # Try to scale beyond max
        response = requests.post(
            f"{BASE_URL}/api/scaling/manual",
            headers=self.headers,
            json={
                "target_workers": max_workers + 10,
                "reason": "TEST_exceed_max"
            }
        )
        # Should either cap at max or reject
        if response.status_code == 200:
            data = response.json()
            new_workers = data.get("new_workers", 0)
            assert new_workers <= max_workers, f"Workers {new_workers} exceeded max {max_workers}"
    
    def test_manual_scale_requires_admin(self):
        """Test /api/scaling/manual requires admin role"""
        # Login as regular user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            user_token = response.json().get("token")
            user_headers = {"Authorization": f"Bearer {user_token}"}
            response = requests.post(
                f"{BASE_URL}/api/scaling/manual",
                headers=user_headers,
                json={"target_workers": 5, "reason": "TEST_non_admin"}
            )
            assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    # ==================================
    # Scaling Metrics Tests
    # ==================================
    
    def test_scaling_metrics_returns_200(self):
        """Test /api/scaling/metrics returns 200 for admin"""
        response = requests.get(f"{BASE_URL}/api/scaling/metrics", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_scaling_metrics_has_data(self):
        """Test /api/scaling/metrics returns metric data"""
        response = requests.get(f"{BASE_URL}/api/scaling/metrics", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "metrics" in data, "Missing metrics field"
    
    # ==================================
    # Scaling History Tests
    # ==================================
    
    def test_scaling_history_returns_200(self):
        """Test /api/scaling/history returns 200 for admin"""
        response = requests.get(f"{BASE_URL}/api/scaling/history", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_scaling_history_structure(self):
        """Test /api/scaling/history returns events list"""
        response = requests.get(f"{BASE_URL}/api/scaling/history", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "events" in data, "Missing events field"
        assert "count" in data, "Missing count field"
        assert isinstance(data["events"], list), "events should be a list"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
