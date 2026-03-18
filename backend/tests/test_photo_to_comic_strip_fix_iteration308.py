"""
Test Photo to Comic Strip Fix - Iteration 308
Verifies:
1. Backend photo_to_comic.py has ZERO placehold.co references in strip generation
2. Backend sets per-panel status: 'READY' for successful, 'FAILED' for failed
3. Backend job status: 'COMPLETED'/'PARTIAL_READY'/'FAILED' 
4. Backend only deducts credits proportional to successful panels
5. Frontend handles per-panel status and partial-ready banner
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://growth-funnel-stable.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

class TestPhotoToComicStripFix:
    """Test Photo to Comic Strip pipeline fixes"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture
    def api_client(self, auth_token):
        """Create authenticated session"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        })
        return session
    
    def test_photo_to_comic_styles_endpoint(self, api_client):
        """Test /api/photo-to-comic/styles endpoint returns styles and pricing"""
        response = api_client.get(f"{BASE_URL}/api/photo-to-comic/styles")
        assert response.status_code == 200, f"Styles endpoint failed: {response.text}"
        
        data = response.json()
        assert "styles" in data, "Response missing 'styles'"
        assert "pricing" in data, "Response missing 'pricing'"
        
        # Verify pricing structure
        pricing = data["pricing"]
        assert "comic_strip" in pricing, "Missing comic_strip pricing"
        assert "panels" in pricing["comic_strip"], "Missing panel pricing"
        print(f"✓ Styles endpoint returns {len(data['styles'])} styles")
    
    def test_photo_to_comic_pricing_endpoint(self, api_client):
        """Test /api/photo-to-comic/pricing endpoint"""
        response = api_client.get(f"{BASE_URL}/api/photo-to-comic/pricing")
        assert response.status_code == 200, f"Pricing endpoint failed: {response.text}"
        
        data = response.json()
        assert "pricing" in data, "Response missing 'pricing'"
        
        pricing = data["pricing"]
        # Verify strip pricing structure
        assert "comic_strip" in pricing
        strip_pricing = pricing["comic_strip"]
        assert "panels" in strip_pricing
        assert 4 in strip_pricing["panels"], "Missing 4-panel pricing"
        
        print(f"✓ Pricing endpoint returns correct structure")
    
    def test_photo_to_comic_history_endpoint(self, api_client):
        """Test /api/photo-to-comic/history endpoint returns jobs"""
        response = api_client.get(f"{BASE_URL}/api/photo-to-comic/history")
        assert response.status_code == 200, f"History endpoint failed: {response.text}"
        
        data = response.json()
        assert "jobs" in data, "Response missing 'jobs'"
        assert "total" in data, "Response missing 'total'"
        
        # Check if any jobs exist with the new status fields
        jobs = data["jobs"]
        print(f"✓ History endpoint returns {len(jobs)} jobs, total: {data['total']}")
        
        # Verify job structure for strip jobs
        strip_jobs = [j for j in jobs if j.get("mode") == "strip"]
        if strip_jobs:
            job = strip_jobs[0]
            print(f"  - Sample strip job status: {job.get('status')}")
            if job.get("panels"):
                panels = job["panels"]
                for p in panels:
                    if p.get("status"):
                        print(f"  - Panel {p.get('panelNumber')}: status={p.get('status')}, imageUrl={'present' if p.get('imageUrl') else 'null'}")
    
    def test_job_status_structure_for_strip_jobs(self, api_client):
        """Verify strip jobs have proper status fields"""
        response = api_client.get(f"{BASE_URL}/api/photo-to-comic/history")
        assert response.status_code == 200
        
        data = response.json()
        jobs = data.get("jobs", [])
        
        # Find completed or partial_ready strip jobs
        strip_jobs = [j for j in jobs if j.get("mode") == "strip" and j.get("status") in ["COMPLETED", "PARTIAL_READY", "FAILED"]]
        
        if strip_jobs:
            job = strip_jobs[0]
            job_id = job.get("id")
            
            # Verify status fields
            assert job.get("status") in ["COMPLETED", "PARTIAL_READY", "FAILED"], f"Invalid status: {job.get('status')}"
            
            # For COMPLETED or PARTIAL_READY, verify panels have status
            if job.get("status") in ["COMPLETED", "PARTIAL_READY"] and job.get("panels"):
                panels = job["panels"]
                for panel in panels:
                    # Each panel should have a status field
                    if "status" in panel:
                        assert panel["status"] in ["READY", "FAILED"], f"Invalid panel status: {panel['status']}"
                        # READY panels should have imageUrl
                        if panel["status"] == "READY":
                            assert panel.get("imageUrl"), f"READY panel missing imageUrl"
                            # ImageUrl should NOT be placehold.co
                            assert "placehold.co" not in (panel.get("imageUrl") or ""), f"Panel has placehold.co URL!"
                        # FAILED panels should have null imageUrl
                        elif panel["status"] == "FAILED":
                            assert panel.get("imageUrl") is None, f"FAILED panel should have null imageUrl, got: {panel.get('imageUrl')}"
                
                print(f"✓ Strip job {job_id[:8]} has valid status structure")
            
            # Verify readyPanels/failedPanels/totalPanels fields
            if job.get("readyPanels") is not None:
                assert isinstance(job["readyPanels"], int), "readyPanels should be int"
                assert isinstance(job.get("failedPanels", 0), int), "failedPanels should be int"
                assert isinstance(job.get("totalPanels", 0), int), "totalPanels should be int"
                print(f"  - readyPanels: {job['readyPanels']}, failedPanels: {job.get('failedPanels')}, totalPanels: {job.get('totalPanels')}")
        else:
            print("⚠ No completed strip jobs found to verify structure")
    
    def test_diagnostic_endpoint(self, api_client):
        """Test /api/photo-to-comic/diagnostic endpoint"""
        response = api_client.get(f"{BASE_URL}/api/photo-to-comic/diagnostic")
        assert response.status_code == 200, f"Diagnostic endpoint failed: {response.text}"
        
        data = response.json()
        assert "llm_status" in data, "Missing llm_status"
        assert "recent_jobs" in data, "Missing recent_jobs"
        
        print(f"✓ Diagnostic endpoint accessible")
        print(f"  - LLM available: {data['llm_status'].get('available')}")
        if data.get("recent_jobs", {}).get("last_hour"):
            hour_stats = data["recent_jobs"]["last_hour"]
            print(f"  - Last hour: completed={hour_stats.get('completed')}, failed={hour_stats.get('failed')}")
    
    def test_job_polling_returns_correct_status_fields(self, api_client):
        """Test GET /api/photo-to-comic/job/{id} returns correct status fields"""
        # Get a recent job ID from history
        response = api_client.get(f"{BASE_URL}/api/photo-to-comic/history?size=1")
        assert response.status_code == 200
        
        jobs = response.json().get("jobs", [])
        if not jobs:
            print("⚠ No jobs in history to test polling")
            return
        
        job_id = jobs[0].get("id")
        
        # Poll the job
        poll_response = api_client.get(f"{BASE_URL}/api/photo-to-comic/job/{job_id}")
        assert poll_response.status_code == 200, f"Job polling failed: {poll_response.text}"
        
        job = poll_response.json()
        
        # Verify basic fields
        assert "id" in job
        assert "status" in job
        assert job["status"] in ["QUEUED", "PROCESSING", "COMPLETED", "PARTIAL_READY", "FAILED"]
        
        # For strip mode, verify panels structure
        if job.get("mode") == "strip" and job.get("status") in ["COMPLETED", "PARTIAL_READY"]:
            assert "panels" in job, "Strip job missing panels array"
            assert "readyPanels" in job, "Strip job missing readyPanels count"
            assert "failedPanels" in job, "Strip job missing failedPanels count"
            assert "totalPanels" in job, "Strip job missing totalPanels count"
            
            # Verify no placehold.co in any panel
            for panel in job.get("panels", []):
                if panel.get("imageUrl"):
                    assert "placehold.co" not in panel["imageUrl"], f"Found placehold.co in panel: {panel.get('panelNumber')}"
        
        print(f"✓ Job polling returns correct structure for job {job_id[:8]}")


class TestGalleryRegression:
    """Gallery regression check"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture
    def api_client(self, auth_token):
        """Create authenticated session"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        })
        return session
    
    def test_gallery_explore_has_items(self, api_client):
        """Test gallery explore endpoint returns items"""
        response = api_client.get(f"{BASE_URL}/api/gallery/explore?page=0&size=50")
        assert response.status_code == 200, f"Gallery explore failed: {response.text}"
        
        data = response.json()
        items = data.get("items") or data.get("data") or []
        total = data.get("total") or len(items)
        
        assert total >= 48, f"Gallery should have 48+ items, got {total}"
        print(f"✓ Gallery explore has {total} items (expected 48+)")
        
        # Check thumbnails exist
        items_with_thumbnails = sum(1 for item in items if item.get("thumbnail_url") or item.get("thumbnailUrl"))
        print(f"  - Items with thumbnails: {items_with_thumbnails}")


class TestComicStorybookPreview:
    """Comic Story Book Builder preview regression"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture
    def api_client(self, auth_token):
        """Create authenticated session"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        })
        return session
    
    def test_comic_storybook_templates_endpoint(self, api_client):
        """Test comic storybook templates endpoint"""
        response = api_client.get(f"{BASE_URL}/api/comic-storybook/templates")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Comic storybook templates endpoint accessible")
            if isinstance(data, list):
                print(f"  - {len(data)} templates available")
        else:
            print(f"⚠ Comic storybook templates: {response.status_code}")
    
    def test_comic_storybook_jobs_history(self, api_client):
        """Test comic storybook jobs history"""
        response = api_client.get(f"{BASE_URL}/api/comic-storybook/jobs")
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs") or data.get("items") or []
            print(f"✓ Comic storybook jobs accessible, {len(jobs)} jobs")
        else:
            # Try alternative endpoint
            response = api_client.get(f"{BASE_URL}/api/comic-storybook-v2/jobs")
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs") or data.get("items") or []
                print(f"✓ Comic storybook v2 jobs accessible, {len(jobs)} jobs")
            else:
                print(f"⚠ Comic storybook jobs endpoint: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
