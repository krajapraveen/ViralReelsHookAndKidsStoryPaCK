"""
SRE Endpoints Testing - Iteration 85
Tests: Circuit Breakers, Auto-Scaling, Self-Healing, CDN Status
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://avatar-comic-builder.preview.emergentagent.com').rstrip('/')

class TestSREPublicEndpoints:
    """Public SRE endpoints (no auth required)"""
    
    def test_health_endpoint(self):
        """Test /api/sre/health - public endpoint"""
        response = requests.get(f"{BASE_URL}/api/sre/health", timeout=10)
        assert response.status_code == 200, f"Health endpoint failed: {response.status_code}"
        
        data = response.json()
        assert "overall" in data, "Missing 'overall' field"
        assert data["overall"] in ["healthy", "unhealthy"], f"Invalid health status: {data['overall']}"
        assert "checks" in data, "Missing 'checks' field"
        assert "timestamp" in data, "Missing timestamp"
        
        # Verify health check structure
        checks = data["checks"]
        assert "database" in checks, "Missing database check"
        assert "jobs" in checks, "Missing jobs check"
        
        print(f"Health status: {data['overall']}")
        print(f"Database status: {checks['database']['status']}")
        print(f"Jobs status: {checks['jobs']['status']}")


class TestSREAuthenticatedEndpoints:
    """SRE endpoints requiring admin auth"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "admin@creatorstudio.ai",
                "password": "Cr3@t0rStud!o#2026"
            },
            timeout=10
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Admin login failed: {login_response.status_code}")
        
        token_data = login_response.json()
        self.admin_token = token_data.get("token")
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
        
    def test_circuits_endpoint(self):
        """Test /api/sre/circuits - all 6 circuit breakers"""
        response = requests.get(
            f"{BASE_URL}/api/sre/circuits",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Circuits endpoint failed: {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True, "Response not successful"
        assert "circuits" in data, "Missing 'circuits' field"
        
        circuits = data["circuits"]
        expected_circuits = ["gemini", "openai", "sora", "elevenlabs", "storage", "payment"]
        
        for circuit_name in expected_circuits:
            assert circuit_name in circuits, f"Missing circuit: {circuit_name}"
            circuit = circuits[circuit_name]
            assert "name" in circuit, f"Circuit {circuit_name} missing 'name'"
            assert "state" in circuit, f"Circuit {circuit_name} missing 'state'"
            assert circuit["state"] in ["closed", "open", "half_open"], f"Invalid state: {circuit['state']}"
            assert "failure_count" in circuit, f"Circuit {circuit_name} missing 'failure_count'"
            assert "can_execute" in circuit, f"Circuit {circuit_name} missing 'can_execute'"
            
        print(f"Circuits found: {len(circuits)}")
        for name, info in circuits.items():
            print(f"  {name}: state={info['state']}, failures={info['failure_count']}, can_execute={info['can_execute']}")
    
    def test_scaling_endpoint(self):
        """Test /api/sre/scaling - worker count and queue metrics"""
        response = requests.get(
            f"{BASE_URL}/api/sre/scaling",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Scaling endpoint failed: {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True, "Response not successful"
        assert "status" in data, "Missing 'status' field"
        assert "current_metrics" in data, "Missing 'current_metrics' field"
        
        status = data["status"]
        assert "current_workers" in status, "Missing current_workers"
        assert "min_workers" in status, "Missing min_workers"
        assert "max_workers" in status, "Missing max_workers"
        
        metrics = data["current_metrics"]
        assert "queue_depth" in metrics, "Missing queue_depth"
        assert "processing" in metrics, "Missing processing count"
        
        print(f"Current workers: {status['current_workers']}")
        print(f"Worker range: {status['min_workers']} - {status['max_workers']}")
        print(f"Queue depth: {metrics['queue_depth']}, Processing: {metrics['processing']}")
    
    def test_healing_status_endpoint(self):
        """Test /api/sre/healing/status - issues_detected object"""
        response = requests.get(
            f"{BASE_URL}/api/sre/healing/status",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Healing status endpoint failed: {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True, "Response not successful"
        assert "issues_detected" in data, "Missing 'issues_detected' field"
        
        issues = data["issues_detected"]
        assert "stuck_jobs" in issues, "Missing stuck_jobs count"
        assert "unreconciled_payments" in issues, "Missing unreconciled_payments count"
        assert isinstance(issues["stuck_jobs"], int), "stuck_jobs should be int"
        assert isinstance(issues["unreconciled_payments"], int), "unreconciled_payments should be int"
        
        print(f"Stuck jobs: {issues['stuck_jobs']}")
        print(f"Unreconciled payments: {issues['unreconciled_payments']}")
    
    def test_cdn_status_endpoint(self):
        """Test /api/sre/cdn/status - asset_status object"""
        response = requests.get(
            f"{BASE_URL}/api/sre/cdn/status",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"CDN status endpoint failed: {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True, "Response not successful"
        assert "asset_status" in data, "Missing 'asset_status' field"
        assert "cache_config" in data, "Missing 'cache_config' field"
        
        asset_status = data["asset_status"]
        assert "expired_links" in asset_status, "Missing expired_links"
        assert "missing_assets" in asset_status, "Missing missing_assets"
        
        cache_config = data["cache_config"]
        assert "static" in cache_config, "Missing static cache config"
        assert "images" in cache_config, "Missing images cache config"
        assert "videos" in cache_config, "Missing videos cache config"
        
        print(f"Expired links: {asset_status['expired_links']}")
        print(f"Missing assets: {asset_status['missing_assets']}")
        print(f"Cache configs: {list(cache_config.keys())}")
    
    def test_sre_status_comprehensive(self):
        """Test /api/sre/status - comprehensive SRE status"""
        response = requests.get(
            f"{BASE_URL}/api/sre/status",
            headers=self.headers,
            timeout=15
        )
        assert response.status_code == 200, f"SRE status endpoint failed: {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True, "Response not successful"
        assert "performance" in data, "Missing performance"
        assert "cache" in data, "Missing cache stats"
        assert "database" in data, "Missing database info"
        assert "queues" in data, "Missing queues info"
        
        print(f"Performance uptime: {data['performance'].get('uptime_seconds', 0)} seconds")
        print(f"Total requests: {data['performance'].get('total_requests', 0)}")


class TestSREUnauthorizedAccess:
    """Test that admin endpoints require authentication"""
    
    def test_circuits_requires_auth(self):
        """Circuits endpoint should require admin auth"""
        response = requests.get(f"{BASE_URL}/api/sre/circuits", timeout=10)
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
    
    def test_scaling_requires_auth(self):
        """Scaling endpoint should require admin auth"""
        response = requests.get(f"{BASE_URL}/api/sre/scaling", timeout=10)
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
    
    def test_healing_status_requires_auth(self):
        """Healing status endpoint should require admin auth"""
        response = requests.get(f"{BASE_URL}/api/sre/healing/status", timeout=10)
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
    
    def test_cdn_status_requires_auth(self):
        """CDN status endpoint should require admin auth"""
        response = requests.get(f"{BASE_URL}/api/sre/cdn/status", timeout=10)
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"


class TestDemoUserAccess:
    """Test demo user can access user dashboard"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get demo user token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "demo@example.com",
                "password": "Password123!"
            },
            timeout=10
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Demo login failed: {login_response.status_code}")
        
        token_data = login_response.json()
        self.demo_token = token_data.get("token")
        self.headers = {"Authorization": f"Bearer {self.demo_token}"}
    
    def test_demo_user_profile(self):
        """Demo user can access their profile"""
        response = requests.get(
            f"{BASE_URL}/api/user/profile",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code == 200, f"Profile access failed: {response.status_code}"
        
        data = response.json()
        if data.get("success"):
            user = data.get("user", data)
            print(f"Demo user email: {user.get('email')}")
    
    def test_demo_user_cannot_access_sre_endpoints(self):
        """Demo user should NOT access admin SRE endpoints"""
        response = requests.get(
            f"{BASE_URL}/api/sre/circuits",
            headers=self.headers,
            timeout=10
        )
        assert response.status_code in [401, 403], f"Demo should not access circuits: {response.status_code}"


class TestBillingEndpoints:
    """Test billing page data"""
    
    def test_public_subscription_plans(self):
        """Test subscription plans are accessible"""
        response = requests.get(f"{BASE_URL}/api/billing/plans", timeout=10)
        # Plans may require auth or be public
        if response.status_code == 200:
            data = response.json()
            print(f"Plans response: {data}")
        else:
            print(f"Plans endpoint status: {response.status_code}")
    
    def test_public_credit_packs(self):
        """Test credit packs are accessible"""
        response = requests.get(f"{BASE_URL}/api/billing/credit-packs", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"Credit packs response: {data}")
        else:
            print(f"Credit packs endpoint status: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
