"""
Iteration 123: Testing Admin Monitoring Dashboard and SmartDownloadButton/Watermark Integration
Features to test:
1. Admin Monitoring Dashboard APIs (queue-status, system-health, load-test, feature-usage)
2. Watermark service (should-apply for free vs paid users)
3. Live Chat Widget human support escalation
"""

import pytest
import requests
import os
import time
import json

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "krajapraveen.katta@creatorstudio.ai"
ADMIN_PASSWORD = "Onemanarmy@1979#"


class TestHealthCheck:
    """Basic health check to ensure API is running"""
    
    def test_health_endpoint(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")


class TestAdminAuthentication:
    """Authentication tests for admin user"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
            
        data = response.json()
        token = data.get("token")
        assert token, "No token in response"
        print(f"✓ Admin login successful")
        return token
    
    def test_admin_login(self, admin_token):
        """Verify admin can login"""
        assert admin_token is not None
        print(f"✓ Admin token obtained: {admin_token[:20]}...")
    
    def test_admin_me_endpoint(self, admin_token):
        """Verify admin user details"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        user = data.get("user", data)
        assert user.get("role", "").upper() == "ADMIN"
        print(f"✓ Admin user verified: {user.get('email')}, role: {user.get('role')}")


class TestMonitoringQueueStatus:
    """Test queue status monitoring API"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_queue_status_endpoint(self, admin_token):
        """Test /api/monitoring/queue-status"""
        response = requests.get(
            f"{BASE_URL}/api/monitoring/queue-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "queueStatus" in data
        
        queue_status = data["queueStatus"]
        assert "pending" in queue_status
        assert "processing" in queue_status
        assert "completedToday" in queue_status
        assert "failedToday" in queue_status
        assert "successRate" in queue_status
        assert "health" in queue_status
        
        print(f"✓ Queue status: pending={queue_status['pending']}, "
              f"processing={queue_status['processing']}, "
              f"health={queue_status['health']}, "
              f"successRate={queue_status['successRate']}%")


class TestMonitoringSystemHealth:
    """Test system health monitoring API"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_system_health_endpoint(self, admin_token):
        """Test /api/monitoring/system-health"""
        response = requests.get(
            f"{BASE_URL}/api/monitoring/system-health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "health" in data
        
        health = data["health"]
        assert "score" in health
        assert "status" in health
        assert "dbConnected" in health
        
        assert "metrics" in data
        metrics = data["metrics"]
        assert "activeUsers" in metrics
        assert "creditsUsedHour" in metrics
        
        print(f"✓ System health: score={health['score']}%, "
              f"status={health['status']}, "
              f"dbConnected={health['dbConnected']}, "
              f"activeUsers={metrics['activeUsers']}")


class TestMonitoringFeatureUsage:
    """Test feature usage analytics API"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_feature_usage_endpoint(self, admin_token):
        """Test /api/monitoring/feature-usage"""
        response = requests.get(
            f"{BASE_URL}/api/monitoring/feature-usage?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "featureUsage" in data
        assert "period" in data
        
        print(f"✓ Feature usage retrieved: period={data['period']}, "
              f"features={len(data['featureUsage'])}")


class TestLoadTestFunctionality:
    """Test load testing APIs"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_load_test_history(self, admin_token):
        """Test /api/monitoring/load-test/history"""
        response = requests.get(
            f"{BASE_URL}/api/monitoring/load-test/history?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "tests" in data
        
        print(f"✓ Load test history: {len(data['tests'])} tests found")
    
    def test_start_load_test(self, admin_token):
        """Test /api/monitoring/load-test/start"""
        response = requests.post(
            f"{BASE_URL}/api/monitoring/load-test/start?test_type=api&num_requests=5&concurrent_users=2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "testId" in data
        
        test_id = data["testId"]
        print(f"✓ Load test started: testId={test_id}")
        
        # Wait for test to complete and check status
        time.sleep(3)
        
        status_response = requests.get(
            f"{BASE_URL}/api/monitoring/load-test/{test_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data.get("success") == True
        assert "test" in status_data
        
        print(f"✓ Load test status: {status_data['test'].get('status')}")


class TestScheduledTests:
    """Test scheduled tests API"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_get_scheduled_tests(self, admin_token):
        """Test /api/monitoring/scheduled-tests"""
        response = requests.get(
            f"{BASE_URL}/api/monitoring/scheduled-tests",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "schedules" in data
        
        print(f"✓ Scheduled tests: {len(data['schedules'])} schedules found")


class TestWatermarkService:
    """Test watermark service for free/paid user differentiation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_should_apply_watermark_for_admin(self, admin_token):
        """Test /api/watermark/should-apply returns shouldApply=false for admin"""
        response = requests.get(
            f"{BASE_URL}/api/watermark/should-apply",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "shouldApply" in data
        
        # Admin/paid users should NOT have watermark
        assert data["shouldApply"] == False, f"Expected shouldApply=False for admin, got {data}"
        
        print(f"✓ Watermark status for admin: shouldApply={data['shouldApply']}, "
              f"reason={data.get('reason')}, plan={data.get('plan')}")
    
    def test_watermark_settings_endpoint(self, admin_token):
        """Test /api/watermark/settings"""
        response = requests.get(
            f"{BASE_URL}/api/watermark/settings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "settings" in data
        
        settings = data["settings"]
        assert "enabled" in settings or "text" in settings
        
        print(f"✓ Watermark settings retrieved: {settings}")


class TestSupportEscalation:
    """Test human support escalation from Live Chat Widget"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_support_escalation_endpoint(self, admin_token):
        """Test /api/monitoring/support/escalate"""
        test_message = "Testing support escalation from automated test"
        test_context = "Test context from LiveChatWidget bot conversation"
        
        response = requests.post(
            f"{BASE_URL}/api/monitoring/support/escalate?message={test_message}&context={test_context}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "ticketId" in data
        assert "estimatedResponseTime" in data
        
        print(f"✓ Support escalation successful: ticketId={data['ticketId']}, "
              f"estimatedResponseTime={data['estimatedResponseTime']}")
    
    def test_get_support_tickets_admin(self, admin_token):
        """Test /api/monitoring/support/tickets (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/monitoring/support/tickets?status=all&limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "tickets" in data
        
        print(f"✓ Support tickets retrieved: {len(data['tickets'])} tickets, total={data.get('total')}")


class TestOutputTracking:
    """Test output tracking API"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_output_tracking_endpoint(self, admin_token):
        """Test /api/monitoring/output-tracking"""
        response = requests.get(
            f"{BASE_URL}/api/monitoring/output-tracking?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "summary" in data
        assert "byType" in data
        
        print(f"✓ Output tracking: totalGenerated={data['summary']['totalGenerated']}, "
              f"totalDownloaded={data['summary']['totalDownloaded']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
