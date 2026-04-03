"""
Photo to Comic P0 Bug Fix Tests - Iteration 418
Tests for:
1. Import fix verification (emergentintegrations.llm.chat)
2. Model tier mapping (gemini-3.1-flash-image-preview for Tier 3/4)
3. Worker telemetry logging and persistence
4. API endpoints functionality
"""
import pytest
import requests
import os
import json
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestPhotoToComicAPIs:
    """Test Photo to Comic API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Authenticate
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()
    
    def test_styles_endpoint(self):
        """Test GET /api/photo-to-comic/styles returns available styles"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/styles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "styles" in data, "Response should contain 'styles' key"
        assert "pricing" in data, "Response should contain 'pricing' key"
        
        # Verify some expected styles exist
        styles = data["styles"]
        expected_styles = ["bold_superhero", "cartoon_fun", "soft_manga", "noir_comic"]
        for style in expected_styles:
            assert style in styles, f"Expected style '{style}' not found"
    
    def test_presets_endpoint(self):
        """Test GET /api/photo-to-comic/presets returns story presets"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/presets")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "presets" in data, "Response should contain 'presets' key"
        
        # Verify some expected presets exist
        presets = data["presets"]
        expected_presets = ["hero", "comedy", "romance", "mystery"]
        for preset in expected_presets:
            assert preset in presets, f"Expected preset '{preset}' not found"
            assert "name" in presets[preset], f"Preset '{preset}' should have 'name'"
            assert "panel_beats" in presets[preset], f"Preset '{preset}' should have 'panel_beats'"
    
    def test_estimate_endpoint(self):
        """Test GET /api/photo-to-comic/estimate returns time estimates"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/estimate?mode=avatar&panel_count=4")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "estimated_seconds_low" in data, "Response should contain 'estimated_seconds_low'"
        assert "estimated_seconds_high" in data, "Response should contain 'estimated_seconds_high'"
        assert "guarantee" in data, "Response should contain 'guarantee'"
    
    def test_pricing_endpoint(self):
        """Test GET /api/photo-to-comic/pricing returns pricing config"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/pricing")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pricing" in data, "Response should contain 'pricing' key"
        
        pricing = data["pricing"]
        assert "comic_avatar" in pricing, "Pricing should include 'comic_avatar'"
        assert "comic_strip" in pricing, "Pricing should include 'comic_strip'"
    
    def test_existing_job_status(self):
        """Test GET /api/photo-to-comic/job/{job_id} for existing completed job"""
        # Use the known completed job ID from the context
        job_id = "a4a94680-0ef1-4a55-9da7-e4b98f4295ab"
        
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/job/{job_id}")
        
        # Job might exist or not - both are valid outcomes
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Job response should contain 'status'"
            assert "id" in data or "jobId" in data, "Job response should contain job ID"
            print(f"Job {job_id} status: {data.get('status')}")
        elif response.status_code == 404:
            print(f"Job {job_id} not found (expected if DB was reset)")
        else:
            # Other status codes are unexpected
            assert False, f"Unexpected status code {response.status_code}: {response.text}"


class TestImportAndModelConfig:
    """Test that import fix and model config are correct"""
    
    def test_panel_orchestrator_import_line(self):
        """Verify the import fix in panel_orchestrator.py"""
        import subprocess
        result = subprocess.run(
            ["grep", "-n", "from emergentintegrations.llm.chat import", 
             "/app/backend/services/comic_pipeline/panel_orchestrator.py"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "Import line not found in panel_orchestrator.py"
        assert "LlmChat" in result.stdout, "LlmChat should be imported"
        assert "UserMessage" in result.stdout, "UserMessage should be imported"
        assert "ImageContent" in result.stdout, "ImageContent should be imported"
        print(f"Import line found: {result.stdout.strip()}")
    
    def test_model_tier_mapping_tier3(self):
        """Verify Tier 3 model is gemini-3.1-flash-image-preview"""
        import subprocess
        result = subprocess.run(
            ["grep", "-A2", "TIER3_DETERMINISTIC", 
             "/app/backend/enums/pipeline_enums.py"],
            capture_output=True, text=True
        )
        assert "gemini-3.1-flash-image-preview" in result.stdout, \
            f"Tier 3 should use gemini-3.1-flash-image-preview, got: {result.stdout}"
        print(f"Tier 3 config: {result.stdout.strip()}")
    
    def test_model_tier_mapping_tier4(self):
        """Verify Tier 4 model is gemini-3.1-flash-image-preview"""
        import subprocess
        result = subprocess.run(
            ["grep", "-A2", "TIER4_SAFE_DEGRADED", 
             "/app/backend/enums/pipeline_enums.py"],
            capture_output=True, text=True
        )
        assert "gemini-3.1-flash-image-preview" in result.stdout, \
            f"Tier 4 should use gemini-3.1-flash-image-preview, got: {result.stdout}"
        print(f"Tier 4 config: {result.stdout.strip()}")
    
    def test_no_old_model_names(self):
        """Verify old model names are not present"""
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "gemini-2.0-flash-preview-image-generation", 
             "/app/backend/enums/pipeline_enums.py"],
            capture_output=True, text=True
        )
        assert result.returncode != 0, \
            f"Old model name 'gemini-2.0-flash-preview-image-generation' should not exist: {result.stdout}"
        print("Old model names not found - PASS")


class TestWorkerTelemetry:
    """Test worker telemetry implementation"""
    
    def test_worker_telemetry_logging_exists(self):
        """Verify WORKER_TELEMETRY logging is implemented"""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "WORKER_TELEMETRY", 
             "/app/backend/services/comic_pipeline/panel_orchestrator.py"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip())
        assert count >= 2, f"Expected at least 2 WORKER_TELEMETRY log entries, found {count}"
        print(f"WORKER_TELEMETRY log entries found: {count}")
    
    def test_job_telemetry_logging_exists(self):
        """Verify JOB_TELEMETRY logging is implemented"""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "JOB_TELEMETRY", 
             "/app/backend/services/comic_pipeline/job_orchestrator.py"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip())
        assert count >= 1, f"Expected at least 1 JOB_TELEMETRY log entry, found {count}"
        print(f"JOB_TELEMETRY log entries found: {count}")
    
    def test_worker_telemetry_db_persist(self):
        """Verify worker telemetry is persisted to MongoDB"""
        import subprocess
        result = subprocess.run(
            ["grep", "-n", "worker_telemetry.insert_one", 
             "/app/backend/services/comic_pipeline/panel_orchestrator.py"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "worker_telemetry.insert_one not found"
        assert "insert_one" in result.stdout, "DB insert for worker_telemetry not found"
        print(f"DB persist line: {result.stdout.strip()}")
    
    def test_persist_worker_telemetry_method_exists(self):
        """Verify _persist_worker_telemetry method exists"""
        import subprocess
        result = subprocess.run(
            ["grep", "-n", "async def _persist_worker_telemetry", 
             "/app/backend/services/comic_pipeline/panel_orchestrator.py"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "_persist_worker_telemetry method not found"
        print(f"Method definition: {result.stdout.strip()}")


class TestJobStates:
    """Test job state transitions"""
    
    def test_valid_job_states_defined(self):
        """Verify valid job states are defined in enums"""
        import subprocess
        result = subprocess.run(
            ["grep", "-E", "QUEUED|PROCESSING|COMPLETED|READY_WITH_WARNINGS|PARTIAL_READY|FAILED", 
             "/app/backend/enums/pipeline_enums.py"],
            capture_output=True, text=True
        )
        # Check for key states
        assert "QUEUED" in result.stdout or result.returncode == 0, "QUEUED state should be defined"
        print("Job states verification passed")
    
    def test_panel_status_enum(self):
        """Verify PanelStatus enum has required values"""
        import subprocess
        result = subprocess.run(
            ["grep", "-A20", "class PanelStatus", 
             "/app/backend/enums/pipeline_enums.py"],
            capture_output=True, text=True
        )
        assert "PASSED" in result.stdout, "PanelStatus should have PASSED"
        assert "FAILED" in result.stdout, "PanelStatus should have FAILED"
        assert "PASSED_REPAIRED" in result.stdout, "PanelStatus should have PASSED_REPAIRED"
        assert "PASSED_DEGRADED" in result.stdout, "PanelStatus should have PASSED_DEGRADED"
        print("PanelStatus enum verification passed")


class TestFrontendRoute:
    """Test frontend route accessibility"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        yield
        self.session.close()
    
    def test_photo_to_comic_route_accessible(self):
        """Test that /app/photo-to-comic route is accessible"""
        # The frontend is served at the base URL
        response = self.session.get(f"{BASE_URL}/app/photo-to-comic", allow_redirects=True)
        # Should return HTML (React app)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        # Check it's HTML content
        content_type = response.headers.get('content-type', '')
        assert 'text/html' in content_type, f"Expected HTML, got {content_type}"
        print("Frontend route /app/photo-to-comic is accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
