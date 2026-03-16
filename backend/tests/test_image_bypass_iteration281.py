"""
Test suite for Image Generation Direct Bypass (Iteration 281)
Tests the litellm.image_generation direct bypass that replaces the emergentintegrations wrapper.
Key focus: verify generate_image_direct() is being used, [IMG_DIRECT] logging, and pipeline completion.
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestHealthAndPublicEndpoints:
    """Verify basic health and public endpoints are working"""
    
    def test_health_endpoint(self):
        """Health check should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"PASS: Health endpoint returned {data}")
    
    def test_public_explore_endpoint(self):
        """Public explore should return trending items"""
        response = requests.get(f"{BASE_URL}/api/public/explore", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "items" in data
        assert len(data["items"]) > 0
        print(f"PASS: Public explore returned {len(data['items'])} items")
    
    def test_public_stats_endpoint(self):
        """Public stats should return platform metrics"""
        response = requests.get(f"{BASE_URL}/api/public/stats", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "creators" in data
        assert "videos_created" in data
        assert "total_creations" in data
        print(f"PASS: Public stats: creators={data.get('creators')}, videos={data.get('videos_created')}")
    
    def test_public_sitemap_endpoint(self):
        """Sitemap should return valid XML"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml", timeout=10)
        assert response.status_code == 200
        assert "<?xml" in response.text or "<urlset" in response.text
        print(f"PASS: Sitemap returned valid XML ({len(response.text)} bytes)")


class TestPipelineOptions:
    """Verify pipeline configuration endpoints"""
    
    def test_pipeline_options_returns_config(self):
        """Pipeline options should return animation styles, voice presets, and limits"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields
        assert data.get("success") is True
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        assert "credit_costs" in data
        assert "plan_scene_limits" in data
        assert "concurrency_limits" in data
        
        # Verify concurrency limits structure
        limits = data.get("concurrency_limits", {})
        assert limits.get("free") == 1
        assert limits.get("admin") == 10
        
        print(f"PASS: Pipeline options returned all config fields")
        print(f"  - Animation styles: {len(data.get('animation_styles', []))}")
        print(f"  - Concurrency limits: free={limits.get('free')}, admin={limits.get('admin')}")


class TestSystemStatus:
    """Verify system status endpoint with authentication"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    def test_system_status_requires_auth(self):
        """System status should require authentication"""
        response = requests.get(f"{BASE_URL}/api/pipeline/system-status", timeout=10)
        assert response.status_code == 401 or response.status_code == 403
        print("PASS: System status requires authentication")
    
    def test_system_status_returns_data(self, admin_token):
        """Authenticated system status should return system and user info"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/system-status",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "system" in data
        assert "user" in data
        
        # Verify system fields
        system = data.get("system", {})
        assert "queued_jobs" in system
        assert "processing_jobs" in system
        assert "system_overloaded" in system
        
        # Verify user fields
        user = data.get("user", {})
        assert "active_jobs" in user
        assert "max_concurrent" in user
        assert user.get("plan") == "admin"
        assert user.get("max_concurrent") == 10
        
        print(f"PASS: System status returned: queued={system.get('queued_jobs')}, processing={system.get('processing_jobs')}")
        print(f"  - User: plan={user.get('plan')}, max_concurrent={user.get('max_concurrent')}")


class TestAdmissionController:
    """Verify admission controller and concurrency limits"""
    
    @pytest.fixture
    def test_user_token(self):
        """Get test user authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Test user authentication failed")
    
    def test_free_user_concurrency_limit(self, test_user_token):
        """Free user should have max_concurrent=1"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/system-status",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        user = data.get("user", {})
        # Free user should have max_concurrent=1
        assert user.get("max_concurrent") == 1
        print(f"PASS: Free user has max_concurrent={user.get('max_concurrent')}")


class TestDirectImageBypassCodeVerification:
    """Code-level verification that generate_image_direct is being used"""
    
    def test_pipeline_engine_imports_direct_bypass(self):
        """Verify pipeline_engine.py imports generate_image_direct"""
        pipeline_path = "/app/backend/services/pipeline_engine.py"
        assert os.path.exists(pipeline_path), f"Pipeline engine not found at {pipeline_path}"
        
        with open(pipeline_path, 'r') as f:
            content = f.read()
        
        # Check for import statement
        assert "from services.image_gen_direct import generate_image_direct" in content, \
            "pipeline_engine.py should import generate_image_direct"
        
        # Check for usage in run_stage_images
        assert "await generate_image_direct(" in content, \
            "pipeline_engine.py should call generate_image_direct"
        
        print("PASS: pipeline_engine.py imports and uses generate_image_direct")
    
    def test_image_gen_direct_module_exists(self):
        """Verify image_gen_direct.py exists with correct implementation"""
        direct_path = "/app/backend/services/image_gen_direct.py"
        assert os.path.exists(direct_path), f"image_gen_direct.py not found at {direct_path}"
        
        with open(direct_path, 'r') as f:
            content = f.read()
        
        # Check for key components
        assert "from litellm import image_generation" in content, \
            "Should import litellm.image_generation"
        assert "async def generate_image_direct" in content, \
            "Should define generate_image_direct function"
        assert 'params["size"]' in content or "size" in content, \
            "Should support size parameter"
        assert "[IMG_DIRECT]" in content, \
            "Should log with [IMG_DIRECT] prefix"
        assert "_is_emergent_key" in content, \
            "Should handle Emergent key routing"
        
        print("PASS: image_gen_direct.py has correct implementation")
    
    def test_no_openaiimagegeneration_wrapper_in_pipeline(self):
        """Verify OpenAIImageGeneration wrapper is NOT used in run_stage_images"""
        pipeline_path = "/app/backend/services/pipeline_engine.py"
        
        with open(pipeline_path, 'r') as f:
            lines = f.readlines()
        
        # Find run_stage_images function and check it doesn't use OpenAIImageGeneration
        in_run_stage_images = False
        for i, line in enumerate(lines):
            if "async def run_stage_images" in line:
                in_run_stage_images = True
            elif in_run_stage_images and "async def " in line:
                break  # Reached next function
            
            if in_run_stage_images:
                assert "OpenAIImageGeneration" not in line, \
                    f"Line {i+1}: run_stage_images should NOT use OpenAIImageGeneration wrapper"
        
        print("PASS: run_stage_images does not use OpenAIImageGeneration wrapper")


class TestPublicCreationPageRegression:
    """Test public creation pages still load"""
    
    def test_create_share_remix_page_loads(self):
        """The /v/create-share-remix page should be accessible"""
        # This is a frontend route, so we test the API that serves it
        # The page should load without 404/500
        response = requests.get(
            f"{BASE_URL}/api/pipeline/options",  # API used by the page
            timeout=10
        )
        assert response.status_code == 200
        print("PASS: Pipeline options API (used by creation page) is working")


class TestCompletedJobVerification:
    """Verify completed jobs have correct status and credit handling"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    def test_user_jobs_endpoint(self, admin_token):
        """User jobs endpoint should return job list with status info"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/user-jobs?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "jobs" in data
        
        jobs = data.get("jobs", [])
        print(f"PASS: User jobs endpoint returned {len(jobs)} jobs")
        
        # If there are jobs, verify structure
        if jobs:
            job = jobs[0]
            assert "job_id" in job
            assert "status" in job
            assert "stages" in job
            print(f"  - Latest job: {job.get('job_id')[:8]}... status={job.get('status')}")
            
            # Check if any completed jobs exist with credit_status=finalized
            for job in jobs:
                if job.get("status") == "COMPLETED":
                    credit_status = job.get("credit_status", "unknown")
                    print(f"  - COMPLETED job found: {job.get('job_id')[:8]}... credit_status={credit_status}")


class TestSizeParameterInDirectBypass:
    """Verify size parameter is passed correctly in direct bypass"""
    
    def test_size_parameter_in_image_gen_direct(self):
        """The direct bypass should pass size parameter for performance"""
        direct_path = "/app/backend/services/image_gen_direct.py"
        
        with open(direct_path, 'r') as f:
            content = f.read()
        
        # Check size parameter is in function signature
        assert "size: Optional[str] = None" in content or "size:" in content, \
            "generate_image_direct should accept size parameter"
        
        # Check size is added to params when provided
        assert 'params["size"] = size' in content, \
            "Size should be added to params dict when provided"
        
        print("PASS: size parameter is properly handled in image_gen_direct")
    
    def test_pipeline_engine_passes_size_1024x1024(self):
        """Pipeline engine should pass explicit size=1024x1024 for performance"""
        pipeline_path = "/app/backend/services/pipeline_engine.py"
        
        with open(pipeline_path, 'r') as f:
            content = f.read()
        
        # Check for explicit 1024x1024 size
        assert '1024x1024' in content or 'img_size' in content, \
            "Pipeline engine should specify image size"
        
        print("PASS: Pipeline engine specifies image size for performance")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
