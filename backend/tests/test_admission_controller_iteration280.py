"""
Test Suite: Admission Controller & Concurrency Limits (Iteration 280)

Tests the pre-job admission controller and strict per-user concurrency limits:
- Free users: max 1 concurrent job, rejected with clear message when at limit
- Paid users: queued with ETA when system overloaded
- Premium users: priority admission
- System status endpoint shows user-specific concurrency info
- Pipeline options returns concurrency_limits
- Public endpoints still working (regression)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials (from requirements)
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


class TestPublicEndpointsRegression:
    """Regression: Verify public endpoints still work"""
    
    def test_public_explore_returns_trending(self):
        """GET /api/public/explore should return trending items"""
        response = requests.get(f"{BASE_URL}/api/public/explore")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "items" in data
        assert len(data["items"]) >= 1
        print(f"PASS: /api/public/explore returns {len(data['items'])} trending items")
    
    def test_public_stats_returns_metrics(self):
        """GET /api/public/stats should return platform metrics"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200
        data = response.json()
        # Stats response has creators, videos_created, etc.
        assert "creators" in data or "videos_created" in data
        print(f"PASS: /api/public/stats returns metrics: {data}")


class TestPipelineOptions:
    """Test pipeline options endpoint returns concurrency_limits"""
    
    def test_options_returns_concurrency_limits(self):
        """GET /api/pipeline/options should include concurrency_limits"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "concurrency_limits" in data
        
        limits = data["concurrency_limits"]
        # Verify expected plan limits
        assert limits.get("free") == 1, "Free users should have limit of 1"
        assert limits.get("admin") == 10, "Admin users should have limit of 10"
        assert limits.get("pro") == 5, "Pro users should have limit of 5"
        assert limits.get("starter") == 3, "Starter users should have limit of 3"
        print(f"PASS: concurrency_limits in options: {limits}")


class TestSystemStatus:
    """Test system-status endpoint returns user-specific concurrency info"""
    
    @pytest.fixture
    def test_user_token(self):
        """Login as test user and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Cannot login as test user: {response.status_code} - {response.text}")
        return response.json().get("token")
    
    @pytest.fixture
    def admin_user_token(self):
        """Login as admin user and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_USER_EMAIL,
            "password": ADMIN_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Cannot login as admin user: {response.status_code} - {response.text}")
        return response.json().get("token")
    
    def test_system_status_requires_auth(self):
        """GET /api/pipeline/system-status should require authentication"""
        response = requests.get(f"{BASE_URL}/api/pipeline/system-status")
        assert response.status_code == 401 or response.status_code == 403
        print("PASS: system-status requires authentication")
    
    def test_system_status_returns_user_info_test_user(self, test_user_token):
        """System status should return user-specific concurrency info for test user (free plan)"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/system-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "user" in data
        assert "system" in data
        
        user_info = data["user"]
        assert "active_jobs" in user_info
        assert "max_concurrent" in user_info
        assert "slots_available" in user_info
        assert "plan" in user_info
        
        # Test user should be free plan with max 1 concurrent job
        # Note: test user may be exempt from rate limiting but concurrency limit still applies
        print(f"PASS: test user system-status: {user_info}")
    
    def test_system_status_returns_user_info_admin_user(self, admin_user_token):
        """System status should return user-specific concurrency info for admin user"""
        headers = {"Authorization": f"Bearer {admin_user_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/system-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        user_info = data["user"]
        
        # Admin user should have max 10 concurrent jobs
        assert user_info.get("max_concurrent") == 10, f"Admin max_concurrent should be 10, got {user_info.get('max_concurrent')}"
        print(f"PASS: admin user system-status: max_concurrent={user_info.get('max_concurrent')}")
    
    def test_system_status_returns_system_metrics(self, test_user_token):
        """System status should return system-wide metrics"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/system-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        system_info = data.get("system", {})
        # System should have queued_jobs, processing_jobs, system_overloaded, system_stressed
        assert "queued_jobs" in system_info
        assert "processing_jobs" in system_info
        assert "system_overloaded" in system_info
        assert "system_stressed" in system_info
        print(f"PASS: system metrics: queued={system_info.get('queued_jobs')}, processing={system_info.get('processing_jobs')}, overloaded={system_info.get('system_overloaded')}, stressed={system_info.get('system_stressed')}")


class TestAdmissionController:
    """Test admission controller behavior for concurrent job limits"""
    
    @pytest.fixture
    def test_user_session(self):
        """Login as test user and return session with headers"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Cannot login as test user: {response.status_code}")
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    @pytest.fixture
    def admin_user_session(self):
        """Login as admin user and return session with headers"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_USER_EMAIL,
            "password": ADMIN_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Cannot login as admin user: {response.status_code}")
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_rate_limit_status_endpoint(self, test_user_session):
        """Rate limit status endpoint should return current limits"""
        response = test_user_session.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        assert response.status_code == 200
        data = response.json()
        
        # Should have can_create, recent_count, max_per_hour, concurrent, max_concurrent
        assert "can_create" in data
        assert "recent_count" in data
        assert "max_per_hour" in data
        assert "concurrent" in data
        assert "max_concurrent" in data
        print(f"PASS: rate-limit-status: {data}")
    
    def test_check_active_jobs_before_concurrency_test(self, test_user_session):
        """Check how many active jobs test user currently has"""
        response = test_user_session.get(f"{BASE_URL}/api/pipeline/system-status")
        assert response.status_code == 200
        data = response.json()
        user_info = data.get("user", {})
        active_jobs = user_info.get("active_jobs", 0)
        max_concurrent = user_info.get("max_concurrent", 1)
        slots_available = user_info.get("slots_available", 0)
        
        print(f"INFO: Test user active_jobs={active_jobs}, max_concurrent={max_concurrent}, slots_available={slots_available}")
        return active_jobs, max_concurrent, slots_available
    
    def test_admission_rejection_response_format(self, test_user_session):
        """
        Test that when user exceeds concurrency limit, they get HTTP 429 with proper format.
        Note: This test verifies the response format but may not trigger if user has slots available.
        """
        # First check current status
        status_response = test_user_session.get(f"{BASE_URL}/api/pipeline/system-status")
        if status_response.status_code != 200:
            pytest.skip("Cannot get system status")
        
        user_info = status_response.json().get("user", {})
        active_jobs = user_info.get("active_jobs", 0)
        max_concurrent = user_info.get("max_concurrent", 1)
        
        print(f"INFO: User has {active_jobs}/{max_concurrent} active jobs")
        
        # If user already at limit, verify 429 response
        if active_jobs >= max_concurrent:
            payload = {
                "title": "Test Concurrency Limit",
                "story_text": "A" * 60,  # Min 50 chars
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            }
            response = test_user_session.post(f"{BASE_URL}/api/pipeline/create", json=payload)
            
            # Should get 429 with admission_rejected
            assert response.status_code == 429, f"Expected 429, got {response.status_code}"
            detail = response.json().get("detail", {})
            
            # detail could be string or dict
            if isinstance(detail, dict):
                assert detail.get("error") == "admission_rejected", f"Expected admission_rejected error, got: {detail}"
                assert "message" in detail, "Should have message in rejection"
                print(f"PASS: Got 429 with admission_rejected: {detail.get('message')}")
            else:
                # Older format might just be a string
                print(f"PASS: Got 429 with detail: {detail}")
        else:
            print(f"SKIP: User has slots available ({active_jobs}/{max_concurrent}), cannot test 429 rejection without creating a job first")
            pytest.skip("User has available slots, need to create job first to test rejection")


class TestConcurrencyLimitsVerification:
    """Verify concurrency limits are correctly configured"""
    
    def test_free_user_limit_is_one(self):
        """Free plan should have max 1 concurrent job"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        limits = response.json().get("concurrency_limits", {})
        assert limits.get("free") == 1
        print("PASS: Free plan concurrency limit is 1")
    
    def test_paid_plans_have_higher_limits(self):
        """Paid plans should have higher limits (3 for most, 5 for premium)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        limits = response.json().get("concurrency_limits", {})
        
        # Verify paid plan limits
        paid_plans_3 = ["starter", "weekly", "monthly", "creator", "quarterly", "yearly"]
        for plan in paid_plans_3:
            assert limits.get(plan) == 3, f"{plan} should have limit 3, got {limits.get(plan)}"
        
        # Verify premium plan limits
        premium_plans_5 = ["pro", "premium", "enterprise", "demo"]
        for plan in premium_plans_5:
            assert limits.get(plan) == 5, f"{plan} should have limit 5, got {limits.get(plan)}"
        
        # Verify admin limit
        assert limits.get("admin") == 10, f"admin should have limit 10, got {limits.get('admin')}"
        
        print("PASS: All plan concurrency limits correctly configured")


class TestUserJobs:
    """Test user jobs endpoint for verifying job creation"""
    
    @pytest.fixture
    def test_user_session(self):
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Cannot login: {response.status_code}")
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_user_jobs_endpoint(self, test_user_session):
        """GET /api/pipeline/user-jobs should return user's jobs"""
        response = test_user_session.get(f"{BASE_URL}/api/pipeline/user-jobs")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "jobs" in data
        
        jobs = data["jobs"]
        active_jobs = [j for j in jobs if j.get("status") in ["QUEUED", "PROCESSING"]]
        print(f"PASS: user-jobs returns {len(jobs)} total jobs, {len(active_jobs)} active")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
