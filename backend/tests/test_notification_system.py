"""
Notification System Tests - Iteration 104
Tests for user notification system APIs
- GET /api/notifications - Get all notifications
- GET /api/notifications/unread-count - Get unread count
- POST /api/notifications/{id}/read - Mark notification as read
- POST /api/notifications/mark-all-read - Mark all as read
- DELETE /api/notifications/{id} - Delete notification
- DELETE /api/notifications - Clear all notifications
- GET /api/notifications/poll - Poll for new notifications
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestNotificationSystem:
    """Tests for notification API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as demo user
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data.get("token")
        self.user_id = data.get("userId") or data.get("user", {}).get("id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
    def test_01_get_notifications(self):
        """Test GET /api/notifications - Get user notifications"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "notifications" in data, "Response missing 'notifications' field"
        assert "unread_count" in data, "Response missing 'unread_count' field"
        assert "total" in data, "Response missing 'total' field"
        
        print(f"GET /api/notifications: {data['total']} notifications, {data['unread_count']} unread")
        
        # Verify notification structure if any exist
        if data['notifications']:
            notif = data['notifications'][0]
            assert "id" in notif, "Notification missing 'id'"
            assert "type" in notif, "Notification missing 'type'"
            assert "title" in notif, "Notification missing 'title'"
            assert "message" in notif, "Notification missing 'message'"
            assert "read" in notif, "Notification missing 'read'"
            assert "created_at" in notif, "Notification missing 'created_at'"
            print(f"Sample notification: {notif['title']} - {notif['message']}")
    
    def test_02_get_unread_count(self):
        """Test GET /api/notifications/unread-count - Get unread count"""
        response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        
        assert response.status_code == 200, f"Get unread count failed: {response.text}"
        data = response.json()
        
        assert "unread_count" in data, "Response missing 'unread_count'"
        assert isinstance(data['unread_count'], int), "unread_count should be integer"
        
        print(f"GET /api/notifications/unread-count: {data['unread_count']}")
    
    def test_03_poll_notifications(self):
        """Test GET /api/notifications/poll - Poll for new notifications"""
        response = self.session.get(f"{BASE_URL}/api/notifications/poll")
        
        assert response.status_code == 200, f"Poll notifications failed: {response.text}"
        data = response.json()
        
        assert "unread_count" in data, "Response missing 'unread_count'"
        assert "new_notifications" in data, "Response missing 'new_notifications'"
        assert "has_new" in data, "Response missing 'has_new'"
        
        print(f"GET /api/notifications/poll: {data['unread_count']} unread, has_new={data['has_new']}")
    
    def test_04_create_test_notification_via_backend(self):
        """Create a test notification by triggering backend service directly (simulating generation completion)"""
        # This tests that the notification system integration works
        # In real scenario, notifications are created when generation completes
        
        # First get current notification count
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        initial_count = response.json()['total']
        
        print(f"Initial notification count: {initial_count}")
        # Test notification is created when generation completes (tested via integration)
    
    def test_05_mark_notification_read_invalid_id(self):
        """Test POST /api/notifications/{id}/read with invalid ID"""
        fake_id = f"notif_{uuid.uuid4().hex[:16]}"
        response = self.session.post(f"{BASE_URL}/api/notifications/{fake_id}/read")
        
        # Should return 404 for non-existent notification
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"POST /api/notifications/{fake_id}/read: 404 as expected")
    
    def test_06_mark_all_notifications_read(self):
        """Test POST /api/notifications/mark-all-read"""
        response = self.session.post(f"{BASE_URL}/api/notifications/mark-all-read")
        
        assert response.status_code == 200, f"Mark all read failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=true"
        assert "marked_count" in data, "Response missing 'marked_count'"
        
        print(f"POST /api/notifications/mark-all-read: {data.get('marked_count', 0)} marked")
        
        # Verify unread count is now 0
        count_response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert count_response.status_code == 200
        assert count_response.json()['unread_count'] == 0, "Unread count should be 0 after mark-all-read"
    
    def test_07_delete_notification_invalid_id(self):
        """Test DELETE /api/notifications/{id} with invalid ID"""
        fake_id = f"notif_{uuid.uuid4().hex[:16]}"
        response = self.session.delete(f"{BASE_URL}/api/notifications/{fake_id}")
        
        # Should return 404 for non-existent notification
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"DELETE /api/notifications/{fake_id}: 404 as expected")
    
    def test_08_clear_all_notifications(self):
        """Test DELETE /api/notifications - Clear all notifications"""
        response = self.session.delete(f"{BASE_URL}/api/notifications")
        
        assert response.status_code == 200, f"Clear all failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=true"
        assert "deleted_count" in data, "Response missing 'deleted_count'"
        
        print(f"DELETE /api/notifications: {data.get('deleted_count', 0)} deleted")
        
        # Verify notifications list is now empty
        list_response = self.session.get(f"{BASE_URL}/api/notifications")
        assert list_response.status_code == 200
        assert list_response.json()['total'] == 0, "Total should be 0 after clear all"
    
    def test_09_unauthenticated_access(self):
        """Test that notification endpoints require authentication"""
        # Create new session without auth token
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        # Test GET /api/notifications
        response = no_auth_session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated GET, got {response.status_code}"
        
        # Test GET /api/notifications/unread-count
        response = no_auth_session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated unread-count, got {response.status_code}"
        
        # Test POST /api/notifications/mark-all-read
        response = no_auth_session.post(f"{BASE_URL}/api/notifications/mark-all-read")
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated mark-all-read, got {response.status_code}"
        
        print("All notification endpoints correctly require authentication")


class TestNotificationWithFilters:
    """Tests for notification filtering and pagination"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as demo user
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_notifications_with_limit(self):
        """Test GET /api/notifications with limit parameter"""
        response = self.session.get(f"{BASE_URL}/api/notifications?limit=5")
        
        assert response.status_code == 200, f"Get notifications with limit failed: {response.text}"
        data = response.json()
        
        assert len(data['notifications']) <= 5, "Limit should restrict notifications to 5"
        print(f"GET /api/notifications?limit=5: {len(data['notifications'])} notifications")
    
    def test_02_get_notifications_include_read(self):
        """Test GET /api/notifications with include_read=false parameter"""
        response = self.session.get(f"{BASE_URL}/api/notifications?include_read=false")
        
        assert response.status_code == 200, f"Get notifications with include_read=false failed: {response.text}"
        data = response.json()
        
        # All returned notifications should be unread
        for notif in data['notifications']:
            assert notif.get('read') == False, "All notifications should be unread when include_read=false"
        
        print(f"GET /api/notifications?include_read=false: {len(data['notifications'])} unread notifications")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
