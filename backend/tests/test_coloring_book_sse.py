"""
Test Suite for Coloring Book and SSE Features
Tests the new Kids Coloring Book module and SSE job updates
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://create-share-remix.preview.emergentagent.com')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}


class TestColoringBookPricing:
    """Tests for Coloring Book pricing endpoint (public)"""
    
    def test_pricing_endpoint_returns_200(self):
        """Pricing endpoint should be publicly accessible"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/pricing")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Pricing endpoint returns 200")
    
    def test_pricing_has_correct_structure(self):
        """Pricing response should have credit pricing, regional pricing, and free preview"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/pricing")
        assert response.status_code == 200
        
        data = response.json()
        # Check creditPricing structure
        assert "creditPricing" in data, "Missing creditPricing key"
        credit_pricing = data["creditPricing"]
        assert "BASE_EXPORT" in credit_pricing, "Missing BASE_EXPORT"
        assert "ACTIVITY_PAGES" in credit_pricing, "Missing ACTIVITY_PAGES"
        assert "PERSONALIZED_COVER" in credit_pricing, "Missing PERSONALIZED_COVER"
        assert "PER_EXTRA_PAGE" in credit_pricing, "Missing PER_EXTRA_PAGE"
        
        # Verify values match expected pricing
        assert credit_pricing["BASE_EXPORT"] == 5, f"BASE_EXPORT should be 5, got {credit_pricing['BASE_EXPORT']}"
        assert credit_pricing["ACTIVITY_PAGES"] == 2, f"ACTIVITY_PAGES should be 2"
        assert credit_pricing["PERSONALIZED_COVER"] == 1, f"PERSONALIZED_COVER should be 1"
        
        print("PASS: Pricing has correct credit pricing structure")
    
    def test_pricing_has_regional_pricing(self):
        """Pricing should include regional pricing for INR and USD"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/pricing")
        data = response.json()
        
        assert "regionalPricing" in data, "Missing regionalPricing"
        regional = data["regionalPricing"]
        
        assert "INR" in regional, "Missing INR pricing"
        assert "USD" in regional, "Missing USD pricing"
        
        # Check INR pricing structure
        inr = regional["INR"]
        assert "weekly" in inr, "Missing weekly plan"
        assert "monthly" in inr, "Missing monthly plan"
        assert inr["monthly"].get("recommended") == True, "Monthly should be recommended"
        
        print("PASS: Regional pricing structure correct")
    
    def test_pricing_has_free_preview(self):
        """Pricing should include free preview info"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/pricing")
        data = response.json()
        
        assert "freePreview" in data, "Missing freePreview"
        preview = data["freePreview"]
        assert "pages" in preview, "Missing pages in freePreview"
        assert "hasWatermark" in preview, "Missing hasWatermark in freePreview"
        
        print("PASS: Free preview info present")


class TestColoringBookTemplates:
    """Tests for activity templates endpoint (public)"""
    
    def test_templates_endpoint_returns_200(self):
        """Templates endpoint should be publicly accessible"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/templates")
        assert response.status_code == 200
        print("PASS: Templates endpoint returns 200")
    
    def test_templates_returns_expected_templates(self):
        """Should return all 6 activity templates"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/templates")
        data = response.json()
        
        assert "templates" in data, "Missing templates key"
        templates = data["templates"]
        assert len(templates) == 6, f"Expected 6 templates, got {len(templates)}"
        
        # Check template IDs
        template_ids = [t["id"] for t in templates]
        expected_ids = ["match_characters", "find_hidden", "vocabulary", "maze", "word_search", "certificate"]
        for tid in expected_ids:
            assert tid in template_ids, f"Missing template: {tid}"
        
        print("PASS: All 6 activity templates present")
    
    def test_template_structure(self):
        """Each template should have id, name, description, type"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/templates")
        templates = response.json()["templates"]
        
        for t in templates:
            assert "id" in t, f"Template missing id"
            assert "name" in t, f"Template missing name"
            assert "description" in t, f"Template missing description"
            assert "type" in t, f"Template missing type"
        
        print("PASS: All templates have correct structure")


class TestColoringBookSvgAssets:
    """Tests for SVG assets endpoint (public)"""
    
    def test_svg_assets_endpoint_returns_200(self):
        """SVG assets endpoint should be publicly accessible"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/svg-assets")
        assert response.status_code == 200
        print("PASS: SVG assets endpoint returns 200")
    
    def test_svg_assets_has_shapes_and_borders(self):
        """Should return shapes and borders"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/svg-assets")
        data = response.json()
        
        assert "shapes" in data, "Missing shapes"
        assert "borders" in data, "Missing borders"
        
        # Check shapes
        shapes = data["shapes"]
        assert len(shapes) >= 8, f"Expected at least 8 shapes, got {len(shapes)}"
        
        # Check borders
        borders = data["borders"]
        assert len(borders) >= 3, f"Expected at least 3 borders, got {len(borders)}"
        
        print("PASS: SVG assets has shapes and borders")
    
    def test_svg_shapes_have_path_data(self):
        """Each shape should have id and path"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/svg-assets")
        shapes = response.json()["shapes"]
        
        for shape in shapes:
            assert "id" in shape, "Shape missing id"
            assert "path" in shape, f"Shape {shape.get('id')} missing path"
            assert len(shape["path"]) > 10, f"Shape {shape.get('id')} path too short"
        
        print("PASS: All shapes have valid SVG path data")


class TestColoringBookAuthenticated:
    """Tests for authenticated coloring book endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Auth failed - skipping authenticated tests")
    
    def test_stories_endpoint_requires_auth(self):
        """Stories endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/stories")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("PASS: Stories endpoint requires auth")
    
    def test_stories_endpoint_returns_list(self):
        """Stories endpoint should return stories list"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/stories", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "stories" in data, "Missing stories key"
        assert "total" in data, "Missing total key"
        assert isinstance(data["stories"], list), "Stories should be a list"
        
        print(f"PASS: Stories endpoint returns list with {data['total']} stories")
    
    def test_calculate_cost_basic(self):
        """Calculate cost for basic export (10 pages, no add-ons)"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/calculate-cost",
            headers=self.headers,
            json={"pageCount": 10, "includeActivityPages": False, "personalizedCover": False, "paperSize": "A4"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "cost" in data, "Missing cost"
        assert "breakdown" in data, "Missing breakdown"
        assert "userBalance" in data, "Missing userBalance"
        assert "canAfford" in data, "Missing canAfford"
        
        # Basic cost should be 5 credits
        assert data["cost"] == 5, f"Basic cost should be 5, got {data['cost']}"
        assert data["breakdown"]["base"] == 5, "Base should be 5"
        assert data["breakdown"]["activityPages"] == 0, "Activity pages should be 0"
        assert data["breakdown"]["personalizedCover"] == 0, "Personalized cover should be 0"
        
        print("PASS: Basic cost calculation correct (5 credits)")
    
    def test_calculate_cost_with_activity_pages(self):
        """Calculate cost with activity pages add-on"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/calculate-cost",
            headers=self.headers,
            json={"pageCount": 10, "includeActivityPages": True, "personalizedCover": False, "paperSize": "A4"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # 5 (base) + 2 (activity) = 7
        assert data["cost"] == 7, f"Cost with activity pages should be 7, got {data['cost']}"
        assert data["breakdown"]["activityPages"] == 2, "Activity pages should be 2"
        
        print("PASS: Cost with activity pages correct (7 credits)")
    
    def test_calculate_cost_with_personalized_cover(self):
        """Calculate cost with personalized cover add-on"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/calculate-cost",
            headers=self.headers,
            json={"pageCount": 10, "includeActivityPages": False, "personalizedCover": True, "childName": "Test Child", "paperSize": "A4"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # 5 (base) + 1 (personalized) = 6
        assert data["cost"] == 6, f"Cost with personalized cover should be 6, got {data['cost']}"
        assert data["breakdown"]["personalizedCover"] == 1, "Personalized cover should be 1"
        
        print("PASS: Cost with personalized cover correct (6 credits)")
    
    def test_calculate_cost_with_all_addons_and_extra_pages(self):
        """Calculate cost with all add-ons and extra pages"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/calculate-cost",
            headers=self.headers,
            json={"pageCount": 12, "includeActivityPages": True, "personalizedCover": True, "childName": "Test", "paperSize": "Letter"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # 5 (base) + 2 (activity) + 1 (personalized) + 1 (2 extra pages * 0.5) = 9
        assert data["cost"] == 9, f"Cost with all add-ons should be 9, got {data['cost']}"
        assert data["breakdown"]["extraPages"] == 1, "Extra pages cost should be 1"
        
        print("PASS: Cost with all add-ons and extra pages correct (9 credits)")
    
    def test_export_history_returns_list(self):
        """Export history should return list of exports"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/export-history", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "exports" in data, "Missing exports key"
        assert "total" in data, "Missing total key"
        
        print(f"PASS: Export history returns list with {data['total']} exports")


class TestSSEEndpoints:
    """Tests for SSE (Server-Sent Events) endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Auth failed - skipping SSE tests")
    
    def test_sse_jobs_requires_auth(self):
        """SSE jobs endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/sse/jobs")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("PASS: SSE jobs requires auth")
    
    def test_sse_wallet_requires_auth(self):
        """SSE wallet endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/sse/wallet")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("PASS: SSE wallet requires auth")


class TestWalletJobsPolling:
    """Tests for wallet/jobs endpoint used by SSE utility as polling fallback"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Auth failed - skipping wallet jobs tests")
    
    def test_wallet_jobs_returns_list(self):
        """Wallet jobs endpoint should return job list"""
        response = requests.get(f"{BASE_URL}/api/wallet/jobs?limit=10", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data, "Missing jobs key"
        assert "total" in data, "Missing total key"
        assert "limit" in data, "Missing limit key"
        
        print(f"PASS: Wallet jobs returns list with {data['total']} jobs")
    
    def test_wallet_jobs_has_correct_structure(self):
        """Each job should have required fields for SSE updates"""
        response = requests.get(f"{BASE_URL}/api/wallet/jobs?limit=5", headers=self.headers)
        data = response.json()
        
        if data["total"] > 0:
            job = data["jobs"][0]
            required_fields = ["id", "userId", "jobType", "status", "costCredits", "createdAt"]
            for field in required_fields:
                assert field in job, f"Job missing field: {field}"
            
            # Check status is valid
            valid_statuses = ["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]
            assert job["status"] in valid_statuses, f"Invalid status: {job['status']}"
            
            print("PASS: Job structure correct for SSE updates")
        else:
            print("PASS: No jobs to verify (empty list)")
    
    def test_wallet_jobs_limit_parameter(self):
        """Should respect limit parameter"""
        response = requests.get(f"{BASE_URL}/api/wallet/jobs?limit=3", headers=self.headers)
        data = response.json()
        
        assert len(data["jobs"]) <= 3, f"Expected max 3 jobs, got {len(data['jobs'])}"
        
        print("PASS: Limit parameter respected")


class TestDashboardColoringBookCard:
    """Tests to verify Dashboard includes coloring book card"""
    
    def test_dashboard_api_accessible(self):
        """Dashboard should be accessible after login"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if login_response.status_code != 200:
            pytest.skip("Auth failed")
        
        token = login_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Dashboard uses multiple endpoints
        # Check user endpoint
        user_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert user_response.status_code == 200
        
        # Check credits endpoint
        credits_response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert credits_response.status_code == 200
        
        print("PASS: Dashboard APIs accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
