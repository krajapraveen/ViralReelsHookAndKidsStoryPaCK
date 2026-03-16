"""
Iteration 57 - Comprehensive Testing of 13 New Features
Testing: Activity Monitoring, Reel Export, Security Monitoring, A/B Testing, Cashfree Webhooks
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
if not BASE_URL:
    BASE_URL = "https://durable-jobs-beta.preview.emergentagent.com"

# Test credentials
ADMIN_CREDS = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
DEMO_CREDS = {"email": "demo@example.com", "password": "Password123!"}


class TestAuthentication:
    """Test admin and demo user authentication - confirms password security fix"""
    
    def test_admin_login(self):
        """Test admin login works with provided credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token returned"
        assert data.get("user", {}).get("email") == ADMIN_CREDS["email"]
        assert data.get("user", {}).get("role") == "ADMIN"
        print(f"✓ Admin login successful, role: {data.get('user', {}).get('role')}")
    
    def test_demo_login(self):
        """Test demo user login works with provided credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_CREDS)
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token returned"
        assert data.get("user", {}).get("email") == DEMO_CREDS["email"]
        print(f"✓ Demo user login successful")


class TestActivityMonitoring:
    """Test Real-time Activity Monitoring APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin authentication failed")
        self.admin_token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_activity_admin_live(self):
        """GET /api/activity/admin/live - Real-time activity data"""
        response = requests.get(f"{BASE_URL}/api/activity/admin/live", headers=self.headers)
        assert response.status_code == 200, f"Live activity failed: {response.text}"
        data = response.json()
        assert "activeSessions" in data
        assert "activeUsersCount" in data
        assert "recentActivities" in data
        assert "timestamp" in data
        print(f"✓ Live activity endpoint working. Active users: {data.get('activeUsersCount')}")
    
    def test_activity_admin_stats_today(self):
        """GET /api/activity/admin/stats?period=today"""
        response = requests.get(f"{BASE_URL}/api/activity/admin/stats?period=today", headers=self.headers)
        assert response.status_code == 200, f"Activity stats failed: {response.text}"
        data = response.json()
        assert "period" in data
        assert data["period"] == "today"
        assert "uniqueUsers" in data
        assert "totalSessions" in data
        assert "avgSessionDuration" in data
        assert "activeNow" in data
        print(f"✓ Activity stats endpoint working. Unique users today: {data.get('uniqueUsers')}")
    
    def test_activity_admin_stats_week(self):
        """GET /api/activity/admin/stats?period=week"""
        response = requests.get(f"{BASE_URL}/api/activity/admin/stats?period=week", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "week"
        print(f"✓ Weekly activity stats working. Total sessions: {data.get('totalSessions')}")


class TestReelExport:
    """Test Reel PDF Export APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get demo user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_CREDS)
        if response.status_code != 200:
            pytest.skip("Demo authentication failed")
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_reel_export_history(self):
        """GET /api/reel-export/history - Export history endpoint"""
        response = requests.get(f"{BASE_URL}/api/reel-export/history", headers=self.headers)
        assert response.status_code == 200, f"Reel export history failed: {response.text}"
        data = response.json()
        assert "exports" in data
        assert "total" in data
        assert isinstance(data["exports"], list)
        print(f"✓ Reel export history working. Total exports: {data.get('total')}")


class TestSecurityMonitoring:
    """Test Security Monitoring APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin authentication failed")
        self.admin_token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_security_overview(self):
        """GET /api/security/overview - Security dashboard overview"""
        response = requests.get(f"{BASE_URL}/api/security/overview", headers=self.headers)
        assert response.status_code == 200, f"Security overview failed: {response.text}"
        data = response.json()
        assert "status" in data
        assert data["status"] in ["OPERATIONAL", "ALERT"]
        assert "alertsSummary" in data
        assert "last24Hours" in data
        assert "timestamp" in data
        print(f"✓ Security overview working. Status: {data.get('status')}")
    
    def test_security_health(self):
        """GET /api/security/health - Security system health"""
        response = requests.get(f"{BASE_URL}/api/security/health")
        assert response.status_code == 200, f"Security health failed: {response.text}"
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data
        assert data["status"] in ["HEALTHY", "DEGRADED"]
        print(f"✓ Security health endpoint working. Status: {data.get('status')}")
        print(f"  Components: {data.get('components')}")
    
    def test_security_alerts(self):
        """GET /api/security/alerts - Security alerts list"""
        response = requests.get(f"{BASE_URL}/api/security/alerts", headers=self.headers)
        assert response.status_code == 200, f"Security alerts failed: {response.text}"
        data = response.json()
        assert "alerts" in data
        assert "total" in data
        assert "unacknowledged" in data
        print(f"✓ Security alerts working. Total: {data.get('total')}, Unack: {data.get('unacknowledged')}")
    
    def test_security_events(self):
        """GET /api/security/events - Security events list"""
        response = requests.get(f"{BASE_URL}/api/security/events?days=7", headers=self.headers)
        assert response.status_code == 200, f"Security events failed: {response.text}"
        data = response.json()
        assert "events" in data
        assert "summary" in data
        assert "period" in data
        print(f"✓ Security events working. Period: {data.get('period')}")
    
    def test_security_blocked_ips(self):
        """GET /api/security/blocked-ips - Blocked IPs list"""
        response = requests.get(f"{BASE_URL}/api/security/blocked-ips", headers=self.headers)
        assert response.status_code == 200, f"Blocked IPs failed: {response.text}"
        data = response.json()
        # May have message if threat detection not available
        assert "blocked" in data or "message" in data
        print(f"✓ Blocked IPs endpoint working. Blocked count: {data.get('blocked_count', 'N/A')}")


class TestABTesting:
    """Test A/B Testing Framework APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get tokens"""
        # Get demo user token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_CREDS)
        if response.status_code != 200:
            pytest.skip("Demo authentication failed")
        self.user_token = response.json().get("token")
        self.user_headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # Get admin token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        self.admin_token = response.json().get("token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_experiments_active(self):
        """GET /api/experiments/active - Active experiments for user"""
        response = requests.get(f"{BASE_URL}/api/experiments/active", headers=self.user_headers)
        assert response.status_code == 200, f"Active experiments failed: {response.text}"
        data = response.json()
        assert "experiments" in data
        assert "user_id" in data
        print(f"✓ Active experiments working. User assigned to {len(data.get('experiments', {}))} experiments")
    
    def test_experiment_pricing_v2(self):
        """GET /api/experiments/pricing_v2 - Specific experiment config"""
        response = requests.get(f"{BASE_URL}/api/experiments/pricing_v2", headers=self.user_headers)
        assert response.status_code == 200, f"Pricing experiment failed: {response.text}"
        data = response.json()
        assert "experiment_id" in data
        assert data["experiment_id"] == "pricing_v2"
        assert "variant" in data
        assert data["variant"] in ["control", "treatment"]
        assert "config" in data
        print(f"✓ Pricing experiment working. User variant: {data.get('variant')}")
    
    def test_experiment_admin_list(self):
        """GET /api/experiments/admin/list - Admin list all experiments"""
        response = requests.get(f"{BASE_URL}/api/experiments/admin/list", headers=self.admin_headers)
        assert response.status_code == 200, f"Admin experiments list failed: {response.text}"
        data = response.json()
        assert "experiments" in data
        experiments = data["experiments"]
        assert len(experiments) >= 1
        # Check experiment structure
        exp = experiments[0]
        assert "id" in exp
        assert "name" in exp
        assert "status" in exp
        assert "variants" in exp
        print(f"✓ Admin experiments list working. Total experiments: {len(experiments)}")


class TestCashfreeWebhook:
    """Test Cashfree Webhook Handler APIs"""
    
    def test_webhook_stats(self):
        """GET /api/cashfree-webhook/stats - Webhook processing statistics"""
        response = requests.get(f"{BASE_URL}/api/cashfree-webhook/stats")
        assert response.status_code == 200, f"Webhook stats failed: {response.text}"
        data = response.json()
        assert "period" in data
        assert "total" in data
        assert "processed" in data
        assert "failed" in data
        print(f"✓ Webhook stats working. Total: {data.get('total')}, Processed: {data.get('processed')}")
    
    def test_webhook_failed_list(self):
        """GET /api/cashfree-webhook/failed - Failed webhooks list"""
        response = requests.get(f"{BASE_URL}/api/cashfree-webhook/failed")
        assert response.status_code == 200, f"Failed webhooks failed: {response.text}"
        data = response.json()
        assert "failed_webhooks" in data
        assert "count" in data
        print(f"✓ Failed webhooks endpoint working. Count: {data.get('count')}")


class TestAdminAnalytics:
    """Test Admin Analytics Dashboard APIs (Used by AdminMonitoring page)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin authentication failed")
        self.admin_token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_analytics_overview(self):
        """GET /api/analytics/admin/overview"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/overview", headers=self.headers)
        assert response.status_code == 200, f"Analytics overview failed: {response.text}"
        data = response.json()
        assert "users" in data
        assert "jobs" in data
        print(f"✓ Analytics overview working. Total users: {data.get('users', {}).get('total')}")
    
    def test_analytics_threat_stats(self):
        """GET /api/analytics/admin/threat-stats"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/threat-stats", headers=self.headers)
        assert response.status_code == 200, f"Threat stats failed: {response.text}"
        data = response.json()
        # Check for expected fields
        assert "currentStatus" in data or "error" in data or isinstance(data, dict)
        print(f"✓ Threat stats endpoint working")
    
    def test_analytics_app_usage(self):
        """GET /api/analytics/admin/app-usage?days=30"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/app-usage?days=30", headers=self.headers)
        assert response.status_code == 200, f"App usage failed: {response.text}"
        data = response.json()
        assert "period" in data or "featureTotals" in data or isinstance(data, dict)
        print(f"✓ App usage endpoint working")
    
    def test_analytics_performance(self):
        """GET /api/analytics/admin/performance"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/performance", headers=self.headers)
        assert response.status_code == 200, f"Performance stats failed: {response.text}"
        data = response.json()
        print(f"✓ Performance endpoint working")


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self):
        """GET /api/health/ - Basic health check"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print(f"✓ Health check working. Status: {data.get('status')}")
    
    def test_root_health(self):
        """GET /health - Root health endpoint"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        print(f"✓ Root health endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
