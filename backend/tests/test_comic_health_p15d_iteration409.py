"""
Photo to Comic P1.5-D: Observability Dashboard Tests
Tests for GET /api/admin/metrics/comic-health endpoint and related features.

Features tested:
- Comic health endpoint returns all metric categories
- Critical alert when success rate < 80%
- Admin authentication required
- Days parameter support
- Regression tests for quality check, events, PDF endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestComicHealthEndpoint:
    """Tests for /api/admin/metrics/comic-health endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get regular user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"User login failed: {response.status_code}")
    
    def test_comic_health_returns_all_categories(self, admin_token):
        """Comic health endpoint returns all metric categories"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required categories exist
        assert "jobs" in data, "Missing 'jobs' category"
        assert "performance" in data, "Missing 'performance' category"
        assert "consistency" in data, "Missing 'consistency' category"
        assert "quality_check" in data, "Missing 'quality_check' category"
        assert "downloads" in data, "Missing 'downloads' category"
        assert "conversion" in data, "Missing 'conversion' category"
        assert "alerts" in data, "Missing 'alerts' category"
        
        # Verify jobs structure
        jobs = data["jobs"]
        assert "total" in jobs, "Missing jobs.total"
        assert "completed" in jobs, "Missing jobs.completed"
        assert "partial" in jobs, "Missing jobs.partial"
        assert "failed" in jobs, "Missing jobs.failed"
        assert "success_rate" in jobs, "Missing jobs.success_rate"
        
        # Verify performance structure
        perf = data["performance"]
        assert "avg_generation_time_seconds" in perf, "Missing performance.avg_generation_time_seconds"
        assert "retry_rate" in perf, "Missing performance.retry_rate"
        assert "retried_jobs" in perf, "Missing performance.retried_jobs"
        
        # Verify consistency structure
        cons = data["consistency"]
        assert "avg_similarity" in cons, "Missing consistency.avg_similarity"
        assert "consistency_retry_rate" in cons, "Missing consistency.consistency_retry_rate"
        assert "no_face_panel_rate" in cons, "Missing consistency.no_face_panel_rate"
        assert "drift_by_style" in cons, "Missing consistency.drift_by_style"
        
        # Verify quality_check structure
        qc = data["quality_check"]
        assert "total_checks" in qc, "Missing quality_check.total_checks"
        assert "breakdown" in qc, "Missing quality_check.breakdown"
        
        # Verify downloads structure
        dl = data["downloads"]
        assert "pdf_attempts" in dl, "Missing downloads.pdf_attempts"
        assert "pdf_success" in dl, "Missing downloads.pdf_success"
        assert "pdf_fail" in dl, "Missing downloads.pdf_fail"
        assert "pdf_success_rate" in dl, "Missing downloads.pdf_success_rate"
        assert "png_downloads" in dl, "Missing downloads.png_downloads"
        assert "script_downloads" in dl, "Missing downloads.script_downloads"
        
        # Verify conversion structure
        conv = data["conversion"]
        assert "style_clicks" in conv, "Missing conversion.style_clicks"
        assert "generate_after_preview" in conv, "Missing conversion.generate_after_preview"
        assert "result_views" in conv, "Missing conversion.result_views"
        
        print(f"✓ Comic health returns all categories: jobs={jobs['total']}, success_rate={jobs['success_rate']}%")
    
    def test_comic_health_critical_alert_low_success_rate(self, admin_token):
        """Comic health returns critical alert when success rate < 80%"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        success_rate = data["jobs"]["success_rate"]
        alerts = data["alerts"]
        
        if success_rate is not None and success_rate < 80:
            # Should have critical alert
            critical_alerts = [a for a in alerts if a.get("level") == "critical"]
            assert len(critical_alerts) > 0, f"Expected critical alert for success_rate={success_rate}%"
            assert any("success rate" in a.get("message", "").lower() for a in critical_alerts), \
                "Critical alert should mention success rate"
            print(f"✓ Critical alert present for success_rate={success_rate}%")
        else:
            print(f"✓ Success rate is {success_rate}% (>= 80%), no critical alert expected")
    
    def test_comic_health_requires_admin_auth(self, user_token):
        """Comic health endpoint requires admin authentication"""
        # Test with regular user token
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code in [401, 403], \
            f"Expected 401/403 for non-admin, got {response.status_code}"
        print("✓ Comic health endpoint rejects non-admin users")
    
    def test_comic_health_no_auth_rejected(self):
        """Comic health endpoint rejects unauthenticated requests"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/comic-health")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 for no auth, got {response.status_code}"
        print("✓ Comic health endpoint rejects unauthenticated requests")
    
    def test_comic_health_accepts_days_parameter(self, admin_token):
        """Comic health endpoint accepts days parameter"""
        for days in [7, 30, 90]:
            response = requests.get(
                f"{BASE_URL}/api/admin/metrics/comic-health?days={days}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Failed for days={days}: {response.status_code}"
            
            data = response.json()
            assert data.get("period_days") == days, f"Expected period_days={days}, got {data.get('period_days')}"
        
        print("✓ Comic health accepts days parameter (7, 30, 90)")
    
    def test_comic_health_empty_state_handling(self, admin_token):
        """Comic health handles empty state gracefully"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health?days=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should have empty_state field
        assert "empty_state" in data, "Missing empty_state field"
        
        if data["empty_state"]:
            assert "empty_message" in data, "Missing empty_message when empty_state=true"
            print(f"✓ Empty state handled: {data['empty_message']}")
        else:
            print(f"✓ Data present: {data['jobs']['total']} jobs")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"User login failed: {response.status_code}")
    
    def test_quality_check_endpoint_works(self, user_token):
        """Quality check endpoint still works (regression)"""
        # Create a simple test image (1x1 red pixel PNG)
        import base64
        # Minimal valid PNG (1x1 red pixel)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        
        files = {"photo": ("test.png", png_data, "image/png")}
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/quality-check",
            files=files,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # Should return 200 with quality result
        assert response.status_code == 200, f"Quality check failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "overall" in data or "result" in data or "quality" in data, \
            f"Quality check response missing expected fields: {data}"
        
        print(f"✓ Quality check endpoint works: {data.get('overall', data.get('result', 'OK'))}")
    
    def test_events_endpoint_works(self, user_token):
        """Events endpoint still works (regression)"""
        # Test posting a valid event type
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/events",
            json={
                "event_type": "preview_strip_style_click",
                "job_id": "test-job-123",
                "metadata": {"style": "cartoon_fun", "test": True}
            },
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # Should accept the event (200 or 201)
        assert response.status_code in [200, 201], \
            f"Events endpoint failed: {response.status_code} - {response.text}"
        
        print("✓ Events endpoint works")
    
    def test_job_status_endpoint_works(self, user_token):
        """Job status endpoint still works (regression)"""
        # Test with a non-existent job ID (should return 404 or empty)
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/nonexistent-job-id",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # Should return 404 for non-existent job or 200 with error
        assert response.status_code in [200, 404], \
            f"Job status endpoint failed: {response.status_code} - {response.text}"
        
        print("✓ Job status endpoint works")
    
    def test_pdf_endpoint_exists(self, user_token):
        """PDF endpoint exists (regression)"""
        # Test with a non-existent job ID
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/pdf/nonexistent-job-id",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # Should return 404 for non-existent job (not 500)
        assert response.status_code in [200, 404], \
            f"PDF endpoint failed: {response.status_code} - {response.text}"
        
        print("✓ PDF endpoint exists and handles missing jobs")


class TestConsistencyValidatorIntegration:
    """Tests for consistency validator integration"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_consistency_logs_in_comic_health(self, admin_token):
        """Consistency logs are reflected in comic health metrics"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        consistency = data["consistency"]
        
        # Consistency section should exist with proper structure
        assert isinstance(consistency.get("avg_similarity"), (int, float, type(None))), \
            "avg_similarity should be numeric or None"
        assert isinstance(consistency.get("consistency_retry_rate"), (int, float, type(None))), \
            "consistency_retry_rate should be numeric or None"
        assert isinstance(consistency.get("no_face_panel_rate"), (int, float, type(None))), \
            "no_face_panel_rate should be numeric or None"
        assert isinstance(consistency.get("drift_by_style"), dict), \
            "drift_by_style should be a dict"
        
        print(f"✓ Consistency metrics structure valid: avg_similarity={consistency.get('avg_similarity')}")


class TestAdminDashboardOtherMetrics:
    """Tests for other admin metrics endpoints (regression)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_summary_endpoint_works(self, admin_token):
        """Summary endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Summary failed: {response.status_code}"
        assert response.json().get("success") == True
        print("✓ Summary endpoint works")
    
    def test_reliability_endpoint_works(self, admin_token):
        """Reliability endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/reliability",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Reliability failed: {response.status_code}"
        assert response.json().get("success") == True
        print("✓ Reliability endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
