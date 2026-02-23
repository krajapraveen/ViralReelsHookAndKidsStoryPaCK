"""
Login Activity Admin Panel API Tests
Tests for admin login activity tracking, IP blocking, and force logout functionality

Endpoints tested:
- GET /api/admin/login-activity - List login activities with filters
- GET /api/admin/login-activity/{id} - Get single activity detail
- GET /api/admin/login-activity/stats/summary - Get login statistics
- GET /api/admin/login-activity/export/csv - Export to CSV
- GET /api/admin/login-activity/blocked-ips/list - List blocked IPs
- POST /api/admin/login-activity/block-ip - Block an IP
- DELETE /api/admin/login-activity/block-ip/{ip} - Unblock an IP
- POST /api/admin/login-activity/force-logout - Force logout a user
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    token = response.json()["token"]
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Return headers with admin auth token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestLoginActivityList:
    """Test GET /api/admin/login-activity - List login activities"""
    
    def test_get_login_activity_list(self, admin_headers):
        """Test getting paginated login activity list"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity?page=1&size=10",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "activities" in data, "activities key missing"
        assert "pagination" in data, "pagination key missing"
        assert "page" in data["pagination"]
        assert "size" in data["pagination"]
        assert "total" in data["pagination"]
        assert "pages" in data["pagination"]
        
        # Check activity record structure if activities exist
        if len(data["activities"]) > 0:
            activity = data["activities"][0]
            required_fields = ["id", "identifier", "timestamp", "status", "ip_address", 
                             "device_type", "browser", "os", "auth_method", "location"]
            for field in required_fields:
                assert field in activity, f"Field {field} missing from activity"
        
        print(f"✓ Login activity list returned {len(data['activities'])} activities")
    
    def test_filter_by_user_email(self, admin_headers):
        """Test filtering activities by user email"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity?user=admin&page=1&size=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned activities should contain 'admin' in identifier
        for activity in data["activities"]:
            assert "admin" in activity.get("identifier", "").lower() or \
                   "admin" in activity.get("user_email", "").lower(), \
                   f"Activity doesn't match filter: {activity.get('identifier')}"
        
        print(f"✓ User filter working - returned {len(data['activities'])} matching activities")
    
    def test_filter_by_status(self, admin_headers):
        """Test filtering activities by status"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity?status=SUCCESS&page=1&size=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned activities should have SUCCESS status
        for activity in data["activities"]:
            assert activity["status"] == "SUCCESS", f"Activity status is {activity['status']}, expected SUCCESS"
        
        print(f"✓ Status filter working - {len(data['activities'])} SUCCESS activities")
    
    def test_filter_by_country(self, admin_headers):
        """Test filtering activities by country"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity?country=United&page=1&size=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned activities should have matching country
        for activity in data["activities"]:
            assert "united" in activity.get("country", "").lower(), \
                f"Country doesn't match: {activity.get('country')}"
        
        print(f"✓ Country filter working - {len(data['activities'])} matching activities")
    
    def test_filter_by_risk_flags(self, admin_headers):
        """Test filtering activities with risk flags"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity?has_risk=true&page=1&size=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned activities should have risk flags
        for activity in data["activities"]:
            assert len(activity.get("risk_flags", [])) > 0, \
                "Activity should have risk flags"
        
        print(f"✓ Risk flag filter working - {len(data['activities'])} risky activities")


class TestLoginActivityDetail:
    """Test GET /api/admin/login-activity/{id} - Get activity detail"""
    
    def test_get_activity_detail(self, admin_headers):
        """Test getting single activity detail"""
        # First get an activity ID
        list_response = requests.get(
            f"{BASE_URL}/api/admin/login-activity?page=1&size=1",
            headers=admin_headers
        )
        assert list_response.status_code == 200
        activities = list_response.json()["activities"]
        
        if len(activities) == 0:
            pytest.skip("No activities available to test")
        
        activity_id = activities[0]["id"]
        
        # Get detail
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity/{activity_id}",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check detail fields
        assert data["id"] == activity_id
        assert "user_info" in data or data.get("user_id") is None
        assert "session_id_masked" in data
        assert "related_activity" in data or data.get("user_id") is None
        
        print(f"✓ Activity detail retrieved for {activity_id[:8]}...")
    
    def test_get_nonexistent_activity(self, admin_headers):
        """Test getting non-existent activity returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity/nonexistent-id-12345",
            headers=admin_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent activity returns 404")


class TestLoginActivityStats:
    """Test GET /api/admin/login-activity/stats/summary"""
    
    def test_get_stats_summary(self, admin_headers):
        """Test getting login statistics summary"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity/stats/summary?days=7",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check stats structure
        required_fields = ["period_days", "total_logins", "successful_logins", 
                         "failed_logins", "success_rate", "unique_users",
                         "risky_logins", "top_countries", "auth_methods", 
                         "device_types", "daily_trend"]
        
        for field in required_fields:
            assert field in data, f"Field {field} missing from stats"
        
        assert data["period_days"] == 7
        assert isinstance(data["success_rate"], (int, float))
        assert isinstance(data["top_countries"], list)
        assert isinstance(data["auth_methods"], list)
        assert isinstance(data["daily_trend"], list)
        
        print(f"✓ Stats: {data['total_logins']} logins, {data['success_rate']}% success rate")


class TestExportCSV:
    """Test GET /api/admin/login-activity/export/csv"""
    
    def test_export_csv(self, admin_headers):
        """Test CSV export functionality"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity/export/csv",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        assert "text/csv" in content_type, f"Expected CSV content type, got {content_type}"
        
        # Check CSV has header row
        csv_content = response.text
        assert "Timestamp" in csv_content
        assert "Email" in csv_content
        assert "Status" in csv_content
        assert "IP Address" in csv_content
        
        print(f"✓ CSV export working - {len(csv_content)} bytes")


class TestBlockIP:
    """Test IP blocking functionality"""
    
    def test_block_ip(self, admin_headers):
        """Test blocking an IP address"""
        test_ip = "10.0.0.99"
        
        response = requests.post(
            f"{BASE_URL}/api/admin/login-activity/block-ip",
            headers=admin_headers,
            json={
                "ip_address": test_ip,
                "reason": "Automated test block",
                "duration_hours": 1
            }
        )
        assert response.status_code == 200, f"Failed to block IP: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert test_ip in data["message"]
        assert "expires_at" in data
        
        print(f"✓ IP {test_ip} blocked successfully")
        
        # Cleanup - unblock the IP
        requests.delete(
            f"{BASE_URL}/api/admin/login-activity/block-ip/{test_ip}",
            headers=admin_headers
        )
    
    def test_block_ip_validation(self, admin_headers):
        """Test IP block validation - reason too short"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login-activity/block-ip",
            headers=admin_headers,
            json={
                "ip_address": "10.0.0.100",
                "reason": "abc",  # Less than 5 chars
                "duration_hours": 1
            }
        )
        assert response.status_code == 422, f"Expected 422 for short reason, got {response.status_code}"
        print("✓ Block IP validates reason length")
    
    def test_get_blocked_ips_list(self, admin_headers):
        """Test getting list of blocked IPs"""
        response = requests.get(
            f"{BASE_URL}/api/admin/login-activity/blocked-ips/list",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "blocked_ips" in data
        assert isinstance(data["blocked_ips"], list)
        
        print(f"✓ Blocked IPs list retrieved - {len(data['blocked_ips'])} IPs")
    
    def test_unblock_ip(self, admin_headers):
        """Test unblocking an IP address"""
        test_ip = "10.0.0.101"
        
        # First block the IP
        requests.post(
            f"{BASE_URL}/api/admin/login-activity/block-ip",
            headers=admin_headers,
            json={
                "ip_address": test_ip,
                "reason": "Test block for unblock test",
                "duration_hours": 1
            }
        )
        
        # Then unblock
        response = requests.delete(
            f"{BASE_URL}/api/admin/login-activity/block-ip/{test_ip}",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to unblock: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        
        print(f"✓ IP {test_ip} unblocked successfully")
    
    def test_unblock_nonexistent_ip(self, admin_headers):
        """Test unblocking IP that isn't blocked returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/login-activity/block-ip/1.2.3.4",
            headers=admin_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Unblock non-existent IP returns 404")


class TestForceLogout:
    """Test force logout functionality"""
    
    def test_force_logout_nonexistent_user(self, admin_headers):
        """Test force logout for non-existent user returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login-activity/force-logout",
            headers=admin_headers,
            json={
                "user_id": "nonexistent-user-id-12345",
                "reason": "Test force logout"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Force logout non-existent user returns 404")
    
    def test_force_logout_validation(self, admin_headers):
        """Test force logout validates reason length"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login-activity/force-logout",
            headers=admin_headers,
            json={
                "user_id": "some-user-id",
                "reason": "abc"  # Less than 5 chars
            }
        )
        assert response.status_code == 422, f"Expected 422 for short reason, got {response.status_code}"
        print("✓ Force logout validates reason length")


class TestAuthorizationRequired:
    """Test that all endpoints require admin authorization"""
    
    def test_list_requires_auth(self):
        """Test login activity list requires auth"""
        response = requests.get(f"{BASE_URL}/api/admin/login-activity")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_stats_requires_auth(self):
        """Test stats endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/admin/login-activity/stats/summary")
        assert response.status_code == 401
    
    def test_export_requires_auth(self):
        """Test export endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/admin/login-activity/export/csv")
        assert response.status_code == 401
    
    def test_block_ip_requires_auth(self):
        """Test block IP endpoint requires auth"""
        response = requests.post(f"{BASE_URL}/api/admin/login-activity/block-ip", json={
            "ip_address": "1.1.1.1",
            "reason": "Test",
            "duration_hours": 1
        })
        assert response.status_code == 401
    
    def test_force_logout_requires_auth(self):
        """Test force logout endpoint requires auth"""
        response = requests.post(f"{BASE_URL}/api/admin/login-activity/force-logout", json={
            "user_id": "test",
            "reason": "Test"
        })
        assert response.status_code == 401
    
    def test_all_auth_checks_passed(self):
        """Summary test"""
        print("✓ All endpoints properly require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
