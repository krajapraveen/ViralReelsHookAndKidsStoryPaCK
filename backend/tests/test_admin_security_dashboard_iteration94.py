"""
Admin Security Dashboard API Tests - Iteration 94
CreatorStudio AI - Testing IP Security, 2FA, Audit Logs for Security Dashboard

Tests:
- IP Security: stats, blocked list, block IP, unblock IP, IP activity
- Audit Dashboard: logs, suspicious users, real-time activity
- Access Control: Admin-only endpoints, non-admin denied
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    return data["token"]


@pytest.fixture(scope="module")
def demo_token():
    """Get demo user authentication token (non-admin)"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    assert response.status_code == 200, f"Demo login failed: {response.text}"
    data = response.json()
    return data.get("token", "")


class TestIPSecurityEndpoints:
    """Tests for IP Security Management endpoints (admin only)"""
    
    def test_get_ip_stats_admin(self, admin_token):
        """Test GET /api/security/ip/stats with admin token"""
        response = requests.get(
            f"{BASE_URL}/api/security/ip/stats?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "active_blocks" in data
        assert "whitelisted_count" in data
        print(f"IP Stats: active_blocks={data['active_blocks']}, whitelisted={data['whitelisted_count']}")
    
    def test_get_blocked_ips_admin(self, admin_token):
        """Test GET /api/security/ip/blocked with admin token"""
        response = requests.get(
            f"{BASE_URL}/api/security/ip/blocked?page=1&size=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "blocked_ips" in data
        assert "pagination" in data
        assert isinstance(data["blocked_ips"], list)
        print(f"Blocked IPs count: {len(data['blocked_ips'])}")
    
    def test_block_ip_admin(self, admin_token):
        """Test POST /api/security/ip/block with admin token"""
        test_ip = "10.0.0.94"
        response = requests.post(
            f"{BASE_URL}/api/security/ip/block",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json={
                "ip_address": test_ip,
                "reason": "Automated test block iteration 94",
                "duration_hours": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert test_ip in data["message"]
        print(f"Block IP result: {data['message']}")
    
    def test_unblock_ip_admin(self, admin_token):
        """Test POST /api/security/ip/unblock with admin token"""
        test_ip = "10.0.0.94"
        response = requests.post(
            f"{BASE_URL}/api/security/ip/unblock?ip_address={test_ip}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"Unblock IP result: {data['message']}")
    
    def test_get_ip_activity_admin(self, admin_token):
        """Test GET /api/security/ip/activity/{ip} with admin token"""
        test_ip = "10.0.0.94"
        response = requests.get(
            f"{BASE_URL}/api/security/ip/activity/{test_ip}?limit=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "ip_address" in data
        assert "activities" in data
        assert "count" in data
        print(f"IP Activity for {test_ip}: {data['count']} events")


class TestAuditDashboardEndpoints:
    """Tests for Audit Dashboard endpoints (admin only)"""
    
    def test_get_audit_logs_admin(self, admin_token):
        """Test GET /api/admin/audit/logs with admin token"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/logs?page=1&size=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "pagination" in data
        print(f"Audit logs count: {len(data['logs'])}")
    
    def test_get_suspicious_users_admin(self, admin_token):
        """Test GET /api/admin/audit/suspicious-users with admin token"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/suspicious-users?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "suspicious_users" in data
        assert "period_days" in data
        assert "total_flagged" in data
        print(f"Suspicious users flagged: {data['total_flagged']}")
    
    def test_get_realtime_activity_admin(self, admin_token):
        """Test GET /api/admin/audit/real-time-activity with admin token"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/real-time-activity?limit=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "all_events" in data
        assert "security_events" in data
        assert "last_updated" in data
        print(f"Real-time activity events: {len(data['all_events'])}")
    
    def test_get_security_summary_admin(self, admin_token):
        """Test GET /api/admin/audit/security-summary with admin token"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/security-summary?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # The endpoint returns security summary including threat level
        print(f"Security summary: {data}")


class TestNonAdminAccessDenied:
    """Tests to verify non-admin users cannot access security endpoints"""
    
    def test_ip_stats_denied_non_admin(self, demo_token):
        """Non-admin should be denied access to IP stats"""
        response = requests.get(
            f"{BASE_URL}/api/security/ip/stats?days=7",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 403
        assert "Admin access required" in response.text
    
    def test_blocked_ips_denied_non_admin(self, demo_token):
        """Non-admin should be denied access to blocked IPs list"""
        response = requests.get(
            f"{BASE_URL}/api/security/ip/blocked?page=1&size=20",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 403
    
    def test_block_ip_denied_non_admin(self, demo_token):
        """Non-admin should be denied ability to block IPs"""
        response = requests.post(
            f"{BASE_URL}/api/security/ip/block",
            headers={
                "Authorization": f"Bearer {demo_token}",
                "Content-Type": "application/json"
            },
            json={
                "ip_address": "10.0.0.1",
                "reason": "Should fail",
                "duration_hours": 1
            }
        )
        assert response.status_code == 403
    
    def test_audit_logs_denied_non_admin(self, demo_token):
        """Non-admin should be denied access to audit logs"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/logs?page=1&size=10",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 403
    
    def test_suspicious_users_denied_non_admin(self, demo_token):
        """Non-admin should be denied access to suspicious users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/suspicious-users?days=7",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 403
    
    def test_realtime_activity_denied_non_admin(self, demo_token):
        """Non-admin should be denied access to real-time activity"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit/real-time-activity?limit=30",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 403


class TestIPBlockWorkflow:
    """End-to-end tests for IP blocking workflow"""
    
    def test_full_ip_block_unblock_workflow(self, admin_token):
        """Test complete IP block -> verify -> unblock -> verify workflow"""
        unique_ip = f"172.16.0.{int(time.time()) % 255}"
        
        # Step 1: Block the IP
        block_response = requests.post(
            f"{BASE_URL}/api/security/ip/block",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            },
            json={
                "ip_address": unique_ip,
                "reason": "Full workflow test",
                "duration_hours": 1
            }
        )
        assert block_response.status_code == 200
        assert block_response.json()["success"] == True
        
        # Step 2: Verify the IP appears in blocked list
        list_response = requests.get(
            f"{BASE_URL}/api/security/ip/blocked?page=1&size=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert list_response.status_code == 200
        blocked_ips = [ip["ip_address"] for ip in list_response.json()["blocked_ips"]]
        assert unique_ip in blocked_ips, f"Blocked IP {unique_ip} not found in list"
        
        # Step 3: Unblock the IP
        unblock_response = requests.post(
            f"{BASE_URL}/api/security/ip/unblock?ip_address={unique_ip}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert unblock_response.status_code == 200
        assert unblock_response.json()["success"] == True
        
        print(f"Full workflow completed for IP: {unique_ip}")


class Test2FAStatusEndpoints:
    """Tests for 2FA status endpoints (available to authenticated users)"""
    
    def test_get_2fa_status_admin(self, admin_token):
        """Test GET /api/security/2fa/status with admin token"""
        response = requests.get(
            f"{BASE_URL}/api/security/2fa/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "two_factor_enabled" in data
        print(f"Admin 2FA status: enabled={data['two_factor_enabled']}")
    
    def test_get_2fa_status_demo_user(self, demo_token):
        """Test GET /api/security/2fa/status with demo user token"""
        response = requests.get(
            f"{BASE_URL}/api/security/2fa/status",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "two_factor_enabled" in data
        print(f"Demo user 2FA status: enabled={data['two_factor_enabled']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
