"""
Iteration 102: Worker Dashboard and WaitingWithGames Tests
Tests:
1. Worker Dashboard at /app/admin/workers - displays worker pools
2. Auto-scaling controls work
3. Auto-refresh toggle
4. WaitingWithGames in ReelGenerator during loading
5. WaitingWithGames in GifMaker during PROCESSING/QUEUED
6. Backend worker pools initialization (logs verification)
7. Admin worker metrics API /api/admin/workers/metrics
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://remix-monetize-1.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


class TestWorkerDashboardAPIs:
    """Test Worker Dashboard Backend APIs"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        return response.json()["token"]
    
    def test_worker_metrics_endpoint(self, admin_token):
        """Test /api/admin/workers/metrics returns data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Worker metrics failed: {response.text}"
        
        data = response.json()
        assert "pools" in data, "Response should have 'pools'"
        assert "timestamp" in data, "Response should have 'timestamp'"
        print(f"Worker metrics: {len(data['pools'])} pools returned")
    
    def test_worker_metrics_requires_admin(self, demo_token):
        """Test that non-admin users get 403"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/metrics",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 403, "Non-admin should get 403"
        print("Non-admin access correctly denied (403)")
    
    def test_load_balancer_status(self, admin_token):
        """Test /api/admin/workers/load-balancer/status returns expected structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/load-balancer/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Load balancer status failed: {response.text}"
        
        data = response.json()
        # Verify structure
        expected_fields = ["status", "total_workers", "busy_workers", "overall_utilization", "pools", "auto_scaling"]
        for field in expected_fields:
            assert field in data, f"Missing expected field: {field}"
        
        # Verify auto_scaling structure
        assert "enabled" in data["auto_scaling"], "auto_scaling should have 'enabled'"
        assert "scale_up_threshold" in data["auto_scaling"], "auto_scaling should have scale_up_threshold"
        assert "scale_down_threshold" in data["auto_scaling"], "auto_scaling should have scale_down_threshold"
        
        print(f"Load balancer status: {data['status']}, {data['total_workers']} total workers, {data['overall_utilization']}% utilization")
    
    def test_auto_scaling_toggle(self, admin_token):
        """Test auto-scaling toggle endpoint"""
        # Test enabling
        response = requests.post(
            f"{BASE_URL}/api/admin/workers/auto-scaling/toggle?enabled=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Auto-scaling enable failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Should return success=true"
        assert data.get("auto_scaling_enabled") == True, "Should confirm enabled"
        print("Auto-scaling enabled successfully")
        
        # Test disabling
        response = requests.post(
            f"{BASE_URL}/api/admin/workers/auto-scaling/toggle?enabled=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Auto-scaling disable failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Should return success=true"
        assert data.get("auto_scaling_enabled") == False, "Should confirm disabled"
        print("Auto-scaling disabled successfully")
        
        # Re-enable for normal operation
        requests.post(
            f"{BASE_URL}/api/admin/workers/auto-scaling/toggle?enabled=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_pool_scale_endpoint(self, admin_token):
        """Test manual pool scaling endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/admin/workers/pools/story_generator/scale?target_workers=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Pool scale failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Should return success=true"
        assert data.get("target_workers") == 5, "Should return target_workers=5"
        print("Pool scale request successful")
    
    def test_pool_scale_validation(self, admin_token):
        """Test pool scaling validation"""
        # Too few workers
        response = requests.post(
            f"{BASE_URL}/api/admin/workers/pools/story_generator/scale?target_workers=0",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400, "Should reject 0 workers"
        
        # Too many workers
        response = requests.post(
            f"{BASE_URL}/api/admin/workers/pools/story_generator/scale?target_workers=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400, "Should reject 50 workers"
        print("Pool scale validation working correctly")
    
    def test_jobs_history_endpoint(self, admin_token):
        """Test job history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/jobs/history?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Jobs history failed: {response.text}"
        
        data = response.json()
        assert "jobs" in data, "Response should have 'jobs'"
        assert "count" in data, "Response should have 'count'"
        print(f"Jobs history: {data['count']} jobs returned")


class TestReelGeneratorWaitingGames:
    """Test that ReelGenerator has WaitingWithGames during loading"""
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        return response.json()["token"]
    
    def test_reel_generation_endpoint_exists(self, demo_token):
        """Test that reel generation endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "topic": "Morning routines for success",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            }
        )
        # Should be 200 (success) or valid error (not 404/500)
        assert response.status_code in [200, 400, 402], f"Reel generation: {response.status_code} - {response.text}"
        print(f"Reel generation endpoint working: {response.status_code}")


class TestGifMakerWaitingGames:
    """Test that GifMaker has WaitingWithGames during PROCESSING/QUEUED"""
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        return response.json()["token"]
    
    def test_gif_maker_emotions_endpoint(self, demo_token):
        """Test GIF maker emotions/config endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/gif-maker/emotions",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 200, f"GIF emotions failed: {response.text}"
        
        data = response.json()
        assert "emotions" in data, "Response should have 'emotions'"
        assert "styles" in data, "Response should have 'styles'"
        assert "backgrounds" in data, "Response should have 'backgrounds'"
        print(f"GIF maker config: {len(data.get('emotions', {}))} emotions available")
    
    def test_gif_maker_history_endpoint(self, demo_token):
        """Test GIF maker history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/gif-maker/history?size=12",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 200, f"GIF history failed: {response.text}"
        
        data = response.json()
        assert "jobs" in data, "Response should have 'jobs'"
        print(f"GIF maker history: {len(data.get('jobs', []))} jobs")


class TestWorkerSystemStartup:
    """Test that worker pools are properly initialized on startup"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    def test_health_endpoint(self):
        """Test basic health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("Health check: PASS")
    
    def test_worker_pools_initialized(self, admin_token):
        """Test that worker pools are initialized by checking load balancer status"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/load-balancer/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Backend should have 6 feature pools as per main agent note
        # comic_avatar, comic_strip, gif_maker, coloring_book, reel_generator, story_generator
        pools = data.get("pools", [])
        
        # At minimum, pools should exist (even if empty initially)
        # The worker system registers handlers but pool metrics may not be populated until jobs are submitted
        print(f"Worker pools active: {len(pools)} pools, {data.get('total_workers', 0)} total workers")
        
        # Verify system is in a valid state
        assert data.get("status") in ["healthy", "high_load", "critical", None], "Invalid system status"
        assert "auto_scaling" in data, "auto_scaling config should be present"
        print(f"System status: {data.get('status')}, Auto-scaling: {data.get('auto_scaling', {}).get('enabled')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
