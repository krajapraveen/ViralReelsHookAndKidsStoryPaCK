"""
Production Metrics Dashboard - Backend API Tests
Tests for the validation phase dashboard tracking Brand Kit Generator and Photo to Comic jobs.
All endpoints require admin authentication.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


class TestProductionMetricsAuth:
    """Test authentication requirements for production metrics endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get non-admin test user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")
    
    def test_overview_requires_auth(self):
        """Test that /overview endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/production-metrics/overview")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: /overview requires authentication")
    
    def test_brand_kit_requires_auth(self):
        """Test that /brand-kit endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/production-metrics/brand-kit")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: /brand-kit requires authentication")
    
    def test_photo_to_comic_requires_auth(self):
        """Test that /photo-to-comic endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/production-metrics/photo-to-comic")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: /photo-to-comic requires authentication")
    
    def test_jobs_requires_auth(self):
        """Test that /jobs endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/production-metrics/jobs")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: /jobs requires authentication")
    
    def test_overview_rejects_non_admin(self, test_user_token):
        """Test that /overview rejects non-admin users with 403"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/overview", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("PASS: /overview rejects non-admin users with 403")
    
    def test_brand_kit_rejects_non_admin(self, test_user_token):
        """Test that /brand-kit rejects non-admin users with 403"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/brand-kit", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("PASS: /brand-kit rejects non-admin users with 403")
    
    def test_photo_to_comic_rejects_non_admin(self, test_user_token):
        """Test that /photo-to-comic rejects non-admin users with 403"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/photo-to-comic", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("PASS: /photo-to-comic rejects non-admin users with 403")
    
    def test_jobs_rejects_non_admin(self, test_user_token):
        """Test that /jobs rejects non-admin users with 403"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/jobs", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("PASS: /jobs rejects non-admin users with 403")


class TestProductionMetricsOverview:
    """Test the /overview endpoint with admin auth"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_overview_returns_200_for_admin(self, admin_token):
        """Test that /overview returns 200 for admin users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/overview", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /overview returns 200 for admin")
    
    def test_overview_response_structure(self, admin_token):
        """Test that /overview returns correct data structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/overview", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level keys
        assert "period_days" in data, "Missing period_days"
        assert "totals" in data, "Missing totals"
        assert "brand_kit" in data, "Missing brand_kit"
        assert "photo_to_comic" in data, "Missing photo_to_comic"
        assert "daily_trend" in data, "Missing daily_trend"
        assert "target" in data, "Missing target"
        
        # Check totals structure
        totals = data["totals"]
        assert "jobs" in totals, "Missing totals.jobs"
        assert "success" in totals, "Missing totals.success"
        assert "failed" in totals, "Missing totals.failed"
        assert "success_rate" in totals, "Missing totals.success_rate"
        assert "credits_consumed" in totals, "Missing totals.credits_consumed"
        assert "downloads" in totals, "Missing totals.downloads"
        
        # Check target structure (validation target)
        target = data["target"]
        assert "goal" in target, "Missing target.goal"
        assert "current" in target, "Missing target.current"
        assert "progress_pct" in target, "Missing target.progress_pct"
        assert target["goal"] == 200, f"Expected goal=200, got {target['goal']}"
        
        print(f"PASS: /overview response structure valid - {data['totals']['jobs']} total jobs")
    
    def test_overview_period_parameter(self, admin_token):
        """Test that /overview respects days parameter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test 7 days
        response = requests.get(f"{BASE_URL}/api/production-metrics/overview?days=7", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7, f"Expected period_days=7, got {data['period_days']}"
        
        # Test 90 days
        response = requests.get(f"{BASE_URL}/api/production-metrics/overview?days=90", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 90, f"Expected period_days=90, got {data['period_days']}"
        
        print("PASS: /overview respects days parameter")


class TestProductionMetricsBrandKit:
    """Test the /brand-kit endpoint with admin auth"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_brand_kit_returns_200_for_admin(self, admin_token):
        """Test that /brand-kit returns 200 for admin users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/brand-kit", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /brand-kit returns 200 for admin")
    
    def test_brand_kit_response_structure(self, admin_token):
        """Test that /brand-kit returns correct data structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/brand-kit", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert "period_days" in data, "Missing period_days"
        assert "total_jobs" in data, "Missing total_jobs"
        assert "status_breakdown" in data, "Missing status_breakdown"
        assert "success_rate" in data, "Missing success_rate"
        assert "failure_rate" in data, "Missing failure_rate"
        assert "mode_split" in data, "Missing mode_split"
        assert "timing" in data, "Missing timing"
        assert "artifact_metrics" in data, "Missing artifact_metrics"
        assert "downloads" in data, "Missing downloads"
        assert "regenerate" in data, "Missing regenerate"
        assert "industry_distribution" in data, "Missing industry_distribution"
        
        # Check status_breakdown structure
        status = data["status_breakdown"]
        assert "ready" in status, "Missing status_breakdown.ready"
        assert "partial_ready" in status, "Missing status_breakdown.partial_ready"
        assert "failed" in status, "Missing status_breakdown.failed"
        assert "generating" in status, "Missing status_breakdown.generating"
        
        # Check mode_split structure
        mode = data["mode_split"]
        assert "fast" in mode, "Missing mode_split.fast"
        assert "pro" in mode, "Missing mode_split.pro"
        
        # Check timing structure
        timing = data["timing"]
        assert "avg_total_ms" in timing, "Missing timing.avg_total_ms"
        assert "avg_time_to_first_artifact_ms" in timing, "Missing timing.avg_time_to_first_artifact_ms"
        
        # Check downloads structure
        downloads = data["downloads"]
        assert "pdf" in downloads, "Missing downloads.pdf"
        assert "zip" in downloads, "Missing downloads.zip"
        assert "total" in downloads, "Missing downloads.total"
        assert "download_rate" in downloads, "Missing downloads.download_rate"
        
        print(f"PASS: /brand-kit response structure valid - {data['total_jobs']} total jobs")


class TestProductionMetricsPhotoToComic:
    """Test the /photo-to-comic endpoint with admin auth"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_photo_to_comic_returns_200_for_admin(self, admin_token):
        """Test that /photo-to-comic returns 200 for admin users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/photo-to-comic", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /photo-to-comic returns 200 for admin")
    
    def test_photo_to_comic_response_structure(self, admin_token):
        """Test that /photo-to-comic returns correct data structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/photo-to-comic", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert "period_days" in data, "Missing period_days"
        assert "total_jobs" in data, "Missing total_jobs"
        assert "status_breakdown" in data, "Missing status_breakdown"
        assert "success_rate" in data, "Missing success_rate"
        assert "failure_rate" in data, "Missing failure_rate"
        assert "type_split" in data, "Missing type_split"
        assert "timing" in data, "Missing timing"
        assert "downloads" in data, "Missing downloads"
        assert "credits_consumed" in data, "Missing credits_consumed"
        assert "users" in data, "Missing users"
        assert "style_distribution" in data, "Missing style_distribution"
        
        # Check status_breakdown structure
        status = data["status_breakdown"]
        assert "completed" in status, "Missing status_breakdown.completed"
        assert "failed" in status, "Missing status_breakdown.failed"
        assert "processing" in status, "Missing status_breakdown.processing"
        
        # Check type_split structure (avatar vs strip)
        type_split = data["type_split"]
        assert "avatar" in type_split, "Missing type_split.avatar"
        assert "strip" in type_split, "Missing type_split.strip"
        
        # Check timing structure
        timing = data["timing"]
        assert "avg_latency_ms" in timing, "Missing timing.avg_latency_ms"
        assert "avatar_avg_ms" in timing, "Missing timing.avatar_avg_ms"
        assert "strip_avg_ms" in timing, "Missing timing.strip_avg_ms"
        
        # Check users structure
        users = data["users"]
        assert "unique" in users, "Missing users.unique"
        assert "regen_users" in users, "Missing users.regen_users"
        assert "regenerate_rate" in users, "Missing users.regenerate_rate"
        
        print(f"PASS: /photo-to-comic response structure valid - {data['total_jobs']} total jobs")


class TestProductionMetricsJobLog:
    """Test the /jobs endpoint with admin auth"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_jobs_returns_200_for_admin(self, admin_token):
        """Test that /jobs returns 200 for admin users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/jobs", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /jobs returns 200 for admin")
    
    def test_jobs_response_structure(self, admin_token):
        """Test that /jobs returns correct data structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/jobs", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check pagination fields
        assert "jobs" in data, "Missing jobs array"
        assert "total" in data, "Missing total"
        assert "page" in data, "Missing page"
        assert "limit" in data, "Missing limit"
        assert "total_pages" in data, "Missing total_pages"
        
        assert isinstance(data["jobs"], list), "jobs should be a list"
        
        # If there are jobs, check job structure
        if len(data["jobs"]) > 0:
            job = data["jobs"][0]
            assert "job_id" in job, "Missing job.job_id"
            assert "feature" in job, "Missing job.feature"
            assert "status" in job, "Missing job.status"
            assert "created_at" in job, "Missing job.created_at"
            assert job["feature"] in ["brand_kit", "photo_to_comic"], f"Invalid feature: {job['feature']}"
        
        print(f"PASS: /jobs response structure valid - {data['total']} total jobs, page {data['page']}/{data['total_pages']}")
    
    def test_jobs_feature_filter_all(self, admin_token):
        """Test that /jobs feature=all returns both types"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/jobs?feature=all", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: /jobs feature=all returns {data['total']} jobs")
    
    def test_jobs_feature_filter_brand_kit(self, admin_token):
        """Test that /jobs feature=brand_kit filters correctly"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/jobs?feature=brand_kit", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # All returned jobs should be brand_kit
        for job in data["jobs"]:
            assert job["feature"] == "brand_kit", f"Expected brand_kit, got {job['feature']}"
        
        print(f"PASS: /jobs feature=brand_kit returns {data['total']} brand_kit jobs")
    
    def test_jobs_feature_filter_photo_to_comic(self, admin_token):
        """Test that /jobs feature=photo_to_comic filters correctly"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/production-metrics/jobs?feature=photo_to_comic", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # All returned jobs should be photo_to_comic
        for job in data["jobs"]:
            assert job["feature"] == "photo_to_comic", f"Expected photo_to_comic, got {job['feature']}"
        
        print(f"PASS: /jobs feature=photo_to_comic returns {data['total']} photo_to_comic jobs")
    
    def test_jobs_pagination(self, admin_token):
        """Test that /jobs pagination works correctly"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get page 1 with limit 5
        response = requests.get(f"{BASE_URL}/api/production-metrics/jobs?page=1&limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1, f"Expected page=1, got {data['page']}"
        assert data["limit"] == 5, f"Expected limit=5, got {data['limit']}"
        assert len(data["jobs"]) <= 5, f"Expected max 5 jobs, got {len(data['jobs'])}"
        
        print(f"PASS: /jobs pagination works - page 1 with limit 5")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
