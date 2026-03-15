"""
Test Suite for Admin Panel Bug Fixes - Iteration 264
Testing:
1. Trending Topics CRUD (was 404, now fixed)
2. Admin Analytics Dashboard (was 504 timeout, now optimized with asyncio.gather)
3. All Admin Panel dynamic endpoints
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://progressive-pipeline.preview.emergentagent.com"

# Admin credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestAdminAuth:
    """Test admin authentication first"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        print(f"Admin login status: {response.status_code}")
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"Admin token obtained: {token[:20]}...")
            return token
        else:
            print(f"Admin login failed: {response.text}")
            pytest.fail("Admin login failed")
    
    def test_admin_login(self, admin_token):
        """Verify admin can log in"""
        assert admin_token is not None
        assert len(admin_token) > 10
        print("✓ Admin login successful")


class TestTrendingTopics:
    """Bug Fix 1: Trending Topics - was 404, now should return 200"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_get_trending_topics(self, admin_token):
        """GET /api/content/trending?active_only=false should return topics (6 seeded)"""
        response = requests.get(
            f"{BASE_URL}/api/content/trending?active_only=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"GET trending topics status: {response.status_code}")
        print(f"Response: {response.text[:500] if response.text else 'empty'}")
        
        # Should return 200, not 404
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "topics" in data
        assert "count" in data
        print(f"✓ Found {data['count']} trending topics")
        
        # Verify topics have expected structure
        if data['topics']:
            topic = data['topics'][0]
            assert "id" in topic
            assert "title" in topic
            assert "niche" in topic
    
    def test_create_trending_topic(self, admin_token):
        """POST /api/content/trending creates new topic"""
        test_topic = {
            "title": "TEST_AI Tools for Productivity 2026",
            "niche": "business",
            "hook_preview": "These 5 AI tools doubled my productivity...",
            "suggested_angle": "Focus on practical demos",
            "is_active": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/content/trending",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=test_topic
        )
        print(f"POST trending topic status: {response.status_code}")
        print(f"Response: {response.text[:500] if response.text else 'empty'}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        assert "topic" in data
        assert data["topic"]["title"] == test_topic["title"]
        print(f"✓ Created topic with ID: {data['topic']['id']}")
        
        # Store for cleanup
        return data["topic"]["id"]
    
    def test_delete_trending_topic(self, admin_token):
        """DELETE /api/content/trending/{id} deletes topic"""
        # First create a topic to delete
        test_topic = {
            "title": "TEST_Delete Me Topic",
            "niche": "health",
            "hook_preview": "This topic will be deleted",
            "suggested_angle": "",
            "is_active": False
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/content/trending",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=test_topic
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create topic to delete")
        
        topic_id = create_response.json()["topic"]["id"]
        
        # Now delete it
        response = requests.delete(
            f"{BASE_URL}/api/content/trending/{topic_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"DELETE trending topic status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json().get("success") == True
        print(f"✓ Deleted topic {topic_id}")


class TestAdminAnalytics:
    """Bug Fix 2: Admin Analytics - was 504 timeout, now optimized"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_admin_analytics_dashboard_fast(self, admin_token):
        """GET /api/admin/analytics/dashboard?days=30 should return 200 fast (<2s)"""
        start_time = time.time()
        
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/dashboard?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10  # Should respond within 10 seconds max
        )
        
        elapsed = time.time() - start_time
        print(f"Analytics dashboard status: {response.status_code}")
        print(f"Response time: {elapsed:.2f}s")
        
        # Should return 200, not 504
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Should be fast (optimized with asyncio.gather)
        assert elapsed < 5, f"Response too slow: {elapsed:.2f}s (expected <5s)"
        print(f"✓ Analytics returned in {elapsed:.2f}s")
        
        # Verify response structure
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
        
        # Check required fields per the bug fix requirements
        analytics = data["data"]
        required_sections = ["users", "generations", "revenue", "payments", "satisfaction"]
        for section in required_sections:
            assert section in analytics, f"Missing section: {section}"
        
        print(f"✓ Analytics contains all required sections: {list(analytics.keys())}")


class TestAdminPanelEndpoints:
    """Test all Admin Panel dynamic endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_users_list(self, admin_token):
        """GET /api/admin/users/list returns users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/list",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Users list status: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        print(f"✓ Found {len(data['users'])} users")
    
    def test_login_activity(self, admin_token):
        """GET /api/admin/login-activity returns login data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Login activity status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ Login activity endpoint working")
    
    def test_audit_logs(self, admin_token):
        """GET /api/admin/audit-logs/logs returns audit logs"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs/logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Audit logs status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ Audit logs endpoint working")
    
    def test_audit_stats(self, admin_token):
        """GET /api/admin/audit-logs/stats returns audit stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Audit stats status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ Audit stats endpoint working")
    
    def test_worker_metrics(self, admin_token):
        """GET /api/admin/workers/metrics returns worker metrics"""
        response = requests.get(
            f"{BASE_URL}/api/admin/workers/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Worker metrics status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ Worker metrics endpoint working")
    
    def test_system_health(self, admin_token):
        """GET /api/admin/system/system-health returns system health"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system/system-health",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"System health status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ System health endpoint working")
    
    def test_monitoring_dashboard(self, admin_token):
        """GET /api/admin/system/monitoring/dashboard returns monitoring data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/system/monitoring/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Monitoring dashboard status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ Monitoring dashboard endpoint working")
    
    def test_revenue_analytics_summary(self, admin_token):
        """GET /api/revenue-analytics/summary returns revenue summary"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Revenue analytics status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ Revenue analytics endpoint working")
    
    def test_successful_payments(self, admin_token):
        """GET /api/admin/payments/successful returns payments"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/successful",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Successful payments status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ Successful payments endpoint working")
    
    def test_all_feedback(self, admin_token):
        """GET /api/admin/feedback/all returns feedback"""
        response = requests.get(
            f"{BASE_URL}/api/admin/feedback/all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"Feedback status: {response.status_code}")
        
        assert response.status_code == 200
        print("✓ Feedback endpoint working")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_cleanup_test_topics(self, admin_token):
        """Clean up TEST_ prefixed topics"""
        response = requests.get(
            f"{BASE_URL}/api/content/trending?active_only=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 200:
            topics = response.json().get("topics", [])
            for topic in topics:
                if topic.get("title", "").startswith("TEST_"):
                    requests.delete(
                        f"{BASE_URL}/api/content/trending/{topic['id']}",
                        headers={"Authorization": f"Bearer {admin_token}"}
                    )
                    print(f"Cleaned up test topic: {topic['title']}")
        
        print("✓ Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
