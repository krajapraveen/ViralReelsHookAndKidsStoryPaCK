"""
Test iteration 101: Background colors, WaitingWithGames, Admin Worker Routes
Tests the new features:
1. Admin worker routes (/api/admin/workers/metrics, /api/admin/workers/load-balancer/status)
2. WaitingWithGames component existence verification
3. Dark slate/indigo gradient background on pages
"""
import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminWorkerRoutes:
    """Test admin worker management routes"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Admin auth failed")
    
    @pytest.fixture
    def user_token(self):
        """Get regular user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("User auth failed")
    
    def test_worker_metrics_endpoint_requires_admin(self, user_token):
        """Test /api/admin/workers/metrics requires admin role"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/metrics",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        # Should be 403 for non-admin
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("PASS: Worker metrics endpoint correctly requires admin role")
    
    def test_worker_metrics_endpoint_admin_access(self, admin_token):
        """Test /api/admin/workers/metrics returns data for admin"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}"
        data = response.json()
        assert "pools" in data, "Response should contain 'pools' key"
        assert "timestamp" in data, "Response should contain 'timestamp' key"
        print(f"PASS: Worker metrics returned {len(data.get('pools', []))} pools")
    
    def test_load_balancer_status_requires_admin(self, user_token):
        """Test /api/admin/workers/load-balancer/status requires admin role"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/load-balancer/status",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        # Should be 403 for non-admin
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("PASS: Load balancer status correctly requires admin role")
    
    def test_load_balancer_status_admin_access(self, admin_token):
        """Test /api/admin/workers/load-balancer/status returns data for admin"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/load-balancer/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}"
        data = response.json()
        
        # Verify required fields
        expected_fields = ["status", "total_workers", "busy_workers", "overall_utilization", 
                          "total_queue_size", "pools", "auto_scaling", "timestamp"]
        for field in expected_fields:
            assert field in data, f"Response missing required field: {field}"
        
        # Verify auto_scaling structure
        auto_scaling = data.get("auto_scaling", {})
        assert "enabled" in auto_scaling, "auto_scaling should have 'enabled' field"
        assert "scale_up_threshold" in auto_scaling, "auto_scaling should have 'scale_up_threshold' field"
        assert "scale_down_threshold" in auto_scaling, "auto_scaling should have 'scale_down_threshold' field"
        
        print(f"PASS: Load balancer status returned - status: {data.get('status')}, utilization: {data.get('overall_utilization')}%")


class TestHealthAndBasicEndpoints:
    """Test basic health and API endpoints"""
    
    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data.get("status") in ["ok", "healthy"], f"Unexpected health status: {data}"
        print(f"PASS: Health endpoint returned status: {data.get('status')}")
    
    def test_comics_config_endpoint(self):
        """Test comics configuration endpoint"""
        response = requests.get(f"{BASE_URL}/api/comics/config")
        assert response.status_code == 200, f"Comics config failed: {response.status_code}"
        data = response.json()
        assert "emotions" in data or "styles" in data, "Expected comics config data"
        print("PASS: Comics config endpoint working")


class TestPageBackgrounds:
    """Verify page background classes in frontend files (code verification)"""
    
    def test_comic_storybook_background(self):
        """Verify ComicStorybookBuilder has dark gradient background"""
        file_path = "/app/frontend/src/pages/ComicStorybookBuilder.js"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for dark gradient background
        assert "min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950" in content, \
            "ComicStorybookBuilder missing dark gradient background"
        print("PASS: ComicStorybookBuilder has correct dark gradient background")
    
    def test_gif_maker_background(self):
        """Verify GifMaker has dark gradient background"""
        file_path = "/app/frontend/src/pages/GifMaker.js"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for dark gradient background
        assert "min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950" in content, \
            "GifMaker missing dark gradient background"
        print("PASS: GifMaker has correct dark gradient background")
    
    def test_photo_to_comic_background(self):
        """Verify PhotoToComic has dark gradient background"""
        file_path = "/app/frontend/src/pages/PhotoToComic.js"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for dark gradient background
        assert "min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950" in content, \
            "PhotoToComic missing dark gradient background"
        print("PASS: PhotoToComic has correct dark gradient background")


class TestWaitingWithGamesComponent:
    """Verify WaitingWithGames component integration"""
    
    def test_waiting_with_games_component_exists(self):
        """Verify WaitingWithGames.js file exists and has proper structure"""
        file_path = "/app/frontend/src/components/WaitingWithGames.js"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for key elements
        assert "QUOTES" in content, "WaitingWithGames missing QUOTES array"
        assert "WORD_SCRAMBLES" in content, "WaitingWithGames missing WORD_SCRAMBLES array"
        assert "MATH_PUZZLES" in content, "WaitingWithGames missing MATH_PUZZLES array"
        assert "TRIVIA" in content, "WaitingWithGames missing TRIVIA array"
        assert "MEMORY_PATTERNS" in content, "WaitingWithGames missing MEMORY_PATTERNS array"
        assert "export default function WaitingWithGames" in content, "WaitingWithGames missing default export"
        
        print("PASS: WaitingWithGames component has all required game types (quotes, word scramble, math, trivia, memory)")
    
    def test_waiting_with_games_imported_in_comic_storybook(self):
        """Verify WaitingWithGames is imported in ComicStorybookBuilder"""
        file_path = "/app/frontend/src/pages/ComicStorybookBuilder.js"
        with open(file_path, 'r') as f:
            content = f.read()
        
        assert "import WaitingWithGames from '../components/WaitingWithGames'" in content, \
            "ComicStorybookBuilder missing WaitingWithGames import"
        assert "<WaitingWithGames" in content, "ComicStorybookBuilder not using WaitingWithGames component"
        print("PASS: WaitingWithGames imported and used in ComicStorybookBuilder")
    
    def test_waiting_with_games_imported_in_photo_to_comic(self):
        """Verify WaitingWithGames is imported in PhotoToComic"""
        file_path = "/app/frontend/src/pages/PhotoToComic.js"
        with open(file_path, 'r') as f:
            content = f.read()
        
        assert "import WaitingWithGames from '../components/WaitingWithGames'" in content, \
            "PhotoToComic missing WaitingWithGames import"
        assert "<WaitingWithGames" in content, "PhotoToComic not using WaitingWithGames component"
        print("PASS: WaitingWithGames imported and used in PhotoToComic")


class TestEnhancedWorkerSystemCode:
    """Verify Enhanced Worker System code structure"""
    
    def test_enhanced_worker_system_exists(self):
        """Verify enhanced_worker_system.py has proper structure"""
        file_path = "/app/backend/services/enhanced_worker_system.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for key classes
        assert "class WorkerStatus" in content, "Missing WorkerStatus enum"
        assert "class JobPriority" in content, "Missing JobPriority enum"
        assert "class Job" in content, "Missing Job dataclass"
        assert "class FeatureWorker" in content, "Missing FeatureWorker class"
        assert "class FeatureWorkerPool" in content, "Missing FeatureWorkerPool class"
        assert "class EnhancedWorkerSystem" in content, "Missing EnhancedWorkerSystem class"
        
        # Check for auto-scaling features
        assert "scale_up_threshold" in content, "Missing scale_up_threshold"
        assert "scale_down_threshold" in content, "Missing scale_down_threshold"
        assert "_auto_scale_loop" in content, "Missing auto-scaling loop"
        
        print("PASS: EnhancedWorkerSystem has all required classes and auto-scaling features")
    
    def test_admin_worker_routes_exists(self):
        """Verify admin_worker_routes.py has proper structure"""
        file_path = "/app/backend/routes/admin_worker_routes.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for key routes
        assert '@router.get("/metrics")' in content, "Missing /metrics endpoint"
        assert '@router.get("/load-balancer/status")' in content, "Missing /load-balancer/status endpoint"
        assert '@router.post("/pools/{feature}/scale")' in content, "Missing scale endpoint"
        assert "require_admin" in content, "Missing admin requirement function"
        
        print("PASS: Admin worker routes has all required endpoints")


class TestCSSVariables:
    """Verify CSS variables for unified dark theme"""
    
    def test_css_unified_theme_variables(self):
        """Verify index.css has unified theme CSS variables"""
        file_path = "/app/frontend/src/index.css"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for unified theme variables
        assert "--app-bg-start" in content, "Missing --app-bg-start CSS variable"
        assert "--app-bg-middle" in content, "Missing --app-bg-middle CSS variable"
        assert "--app-bg-end" in content, "Missing --app-bg-end CSS variable"
        assert "--app-bg-gradient" in content, "Missing --app-bg-gradient CSS variable"
        
        # Check for min-h-screen override
        assert ".min-h-screen" in content, "Missing .min-h-screen selector"
        assert "var(--app-bg-gradient)" in content, "Missing gradient variable usage"
        
        print("PASS: CSS has unified theme variables and min-h-screen override")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
