"""
Iteration 76 - Real-Time Analytics Full Feature Tests
Testing 6 new features:
1. Production monitoring (/monitoring/health)
2. Email alerts for unusual activity (/alerts/*)
3. WebSocket-based updates (ws endpoint)
4. Export to CSV/PDF (/export/csv, /export/pdf)
5. Custom date range filters (snapshot with date params)
6. Granular revenue breakdowns (/revenue-breakdown)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


class TestRealtimeAnalyticsExportFeatures:
    """Test CSV and PDF Export functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup API session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Authenticate as admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_demo_token(self):
        """Authenticate as demo (non-admin) user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    # ===== CSV EXPORT TESTS =====
    
    def test_01_export_csv_overview(self):
        """Test: CSV export for overview data works"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/export/csv?data_type=overview&days=7",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "text/csv" in response.headers.get("Content-Type", ""), "Response should be CSV"
        
        # Verify CSV content has headers
        content = response.text
        assert "Date" in content, "CSV should have Date column"
        assert "Generations" in content, "CSV should have Generations column"
        assert "Logins" in content, "CSV should have Logins column"
        
        print(f"✓ CSV overview export successful, size: {len(content)} bytes")
    
    def test_02_export_csv_generations(self):
        """Test: CSV export for generations data works"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/export/csv?data_type=generations&days=30",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        content = response.text
        assert "Type" in content, "CSV should have Type column"
        assert "User ID" in content, "CSV should have User ID column"
        
        print(f"✓ CSV generations export successful")
    
    def test_03_export_csv_revenue(self):
        """Test: CSV export for revenue data works"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/export/csv?data_type=revenue&days=30",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        content = response.text
        assert "Amount" in content, "CSV should have Amount column"
        assert "Plan Type" in content, "CSV should have Plan Type column"
        
        print(f"✓ CSV revenue export successful")
    
    def test_04_export_csv_users(self):
        """Test: CSV export for users data works"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/export/csv?data_type=users&days=30",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        content = response.text
        assert "Email" in content, "CSV should have Email column"
        assert "Role" in content, "CSV should have Role column"
        
        print(f"✓ CSV users export successful")
    
    def test_05_export_csv_non_admin_denied(self):
        """Test: Non-admin cannot export CSV"""
        token = self.get_demo_token()
        assert token is not None, "Demo login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/export/csv?data_type=overview",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-admin correctly denied CSV export (403)")
    
    # ===== PDF EXPORT TESTS =====
    
    def test_06_export_pdf_report(self):
        """Test: PDF export for analytics report works"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/export/pdf?days=7",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/pdf" in response.headers.get("Content-Type", ""), "Response should be PDF"
        
        # Verify PDF header (PDF files start with %PDF)
        assert response.content[:4] == b'%PDF', "Response should be valid PDF"
        
        print(f"✓ PDF export successful, size: {len(response.content)} bytes")
    
    def test_07_export_pdf_non_admin_denied(self):
        """Test: Non-admin cannot export PDF"""
        token = self.get_demo_token()
        assert token is not None, "Demo login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/export/pdf",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-admin correctly denied PDF export (403)")


class TestMonitoringHealth:
    """Test Production Monitoring Health endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup API session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Authenticate as admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_demo_token(self):
        """Authenticate as demo user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_01_monitoring_health_returns_status(self):
        """Test: /monitoring/health returns system health status"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/monitoring/health",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "status" in data, "Missing status field"
        assert data["status"] in ["healthy", "degraded"], f"Unknown status: {data['status']}"
        assert "timestamp" in data, "Missing timestamp"
        assert "components" in data, "Missing components"
        assert "metrics" in data, "Missing metrics"
        assert "system" in data, "Missing system resources"
        
        # Validate components
        components = data["components"]
        assert "database" in components, "Missing database component"
        assert "api" in components, "Missing api component"
        assert "websocket" in components, "Missing websocket component"
        
        # Validate metrics
        metrics = data["metrics"]
        assert "errorRate1h" in metrics, "Missing errorRate1h"
        assert "totalJobs1h" in metrics, "Missing totalJobs1h"
        assert "failedJobs1h" in metrics, "Missing failedJobs1h"
        
        # Validate system resources
        system = data["system"]
        assert "cpuPercent" in system, "Missing cpuPercent"
        assert "memoryPercent" in system, "Missing memoryPercent"
        
        print(f"✓ System health: {data['status']}, DB: {components['database']}, CPU: {system['cpuPercent']}")
    
    def test_02_monitoring_health_non_admin_denied(self):
        """Test: Non-admin cannot access monitoring health"""
        token = self.get_demo_token()
        assert token is not None, "Demo login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/monitoring/health",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-admin correctly denied monitoring health access (403)")


class TestAlertFeatures:
    """Test Email Alerts functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup API session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Authenticate as admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_demo_token(self):
        """Authenticate as demo user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_01_get_alert_config(self):
        """Test: /alerts/config returns alert configuration"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/alerts/config",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "thresholds" in data, "Missing thresholds"
        assert "cooldownMinutes" in data, "Missing cooldownMinutes"
        assert "emailConfigured" in data, "Missing emailConfigured flag"
        
        # Validate thresholds
        thresholds = data["thresholds"]
        assert "failed_jobs_rate" in thresholds, "Missing failed_jobs_rate threshold"
        assert "failed_logins_count" in thresholds, "Missing failed_logins_count threshold"
        
        print(f"✓ Alert config: {len(thresholds)} thresholds, email configured: {data['emailConfigured']}")
    
    def test_02_get_alert_history(self):
        """Test: /alerts/history returns alert history"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/alerts/history?days=7",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "alerts" in data, "Missing alerts array"
        assert "period" in data, "Missing period"
        assert isinstance(data["alerts"], list), "alerts should be a list"
        
        print(f"✓ Alert history: {len(data['alerts'])} alerts in {data['period']}")
    
    def test_03_send_test_alert(self):
        """Test: /alerts/test sends a test alert"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.post(
            f"{BASE_URL}/api/realtime-analytics/alerts/test",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "success" in data, "Missing success field"
        assert "message" in data, "Missing message field"
        
        print(f"✓ Test alert sent: {data['message']}")
    
    def test_04_alerts_non_admin_denied(self):
        """Test: Non-admin cannot access alerts"""
        token = self.get_demo_token()
        assert token is not None, "Demo login failed"
        
        # Test config access
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/alerts/config",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for config, got {response.status_code}"
        
        # Test history access
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/alerts/history",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for history, got {response.status_code}"
        
        # Test send alert
        response = self.session.post(
            f"{BASE_URL}/api/realtime-analytics/alerts/test",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for test alert, got {response.status_code}"
        
        print(f"✓ Non-admin correctly denied all alert endpoints (403)")


class TestDateRangeFilters:
    """Test Custom Date Range Filters"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup API session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Authenticate as admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_01_snapshot_with_date_range(self):
        """Test: Snapshot endpoint accepts custom date range"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        from datetime import datetime, timedelta
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/snapshot?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify period is set based on provided dates
        assert "period" in data, "Missing period in response"
        period = data["period"]
        assert "start" in period, "Missing period start"
        assert "end" in period, "Missing period end"
        
        print(f"✓ Snapshot with custom date range successful")
    
    def test_02_generation_trends_custom_days(self):
        """Test: Generation trends accepts custom days parameter"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        for days in [7, 14, 30]:
            response = self.session.get(
                f"{BASE_URL}/api/realtime-analytics/generation-trends?days={days}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200, f"Expected 200 for {days} days, got {response.status_code}"
            data = response.json()
            assert len(data["trends"]) == days, f"Expected {days} trend entries, got {len(data['trends'])}"
        
        print(f"✓ Generation trends with 7/14/30 days successful")


class TestRevenueBreakdown:
    """Test Granular Revenue Breakdown"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup API session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Authenticate as admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_01_revenue_breakdown_full_structure(self):
        """Test: Revenue breakdown returns all required data"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/revenue-breakdown?days=30",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate full structure
        assert "period" in data, "Missing period"
        assert "startDate" in data, "Missing startDate"
        assert "endDate" in data, "Missing endDate"
        assert "byPlan" in data, "Missing byPlan breakdown"
        assert "dailyTrend" in data, "Missing dailyTrend"
        assert "byPaymentMethod" in data, "Missing byPaymentMethod"
        assert "topUsers" in data, "Missing topUsers"
        assert "summary" in data, "Missing summary"
        
        # Validate summary
        summary = data["summary"]
        assert "totalRevenue" in summary, "Missing totalRevenue in summary"
        assert "totalTransactions" in summary, "Missing totalTransactions in summary"
        assert "avgTransactionValue" in summary, "Missing avgTransactionValue in summary"
        assert "currency" in summary, "Missing currency in summary"
        
        # Validate byPlan structure
        for plan in data["byPlan"]:
            assert "plan" in plan, "Missing plan name"
            assert "revenue" in plan, "Missing revenue"
            assert "transactions" in plan, "Missing transactions"
            assert "avgTransaction" in plan, "Missing avgTransaction"
        
        print(f"✓ Revenue breakdown: {summary['totalRevenue']} INR total, {len(data['byPlan'])} plans")
    
    def test_02_revenue_breakdown_daily_trend(self):
        """Test: Revenue breakdown includes daily trend data"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/revenue-breakdown?days=7",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate daily trend structure
        assert "dailyTrend" in data
        daily_trend = data["dailyTrend"]
        
        # Should have up to 7 days (or fewer based on data)
        assert len(daily_trend) <= 7, f"Expected max 7 days, got {len(daily_trend)}"
        
        for day in daily_trend:
            assert "date" in day, "Missing date in daily trend"
            assert "day" in day, "Missing day name"
            assert "revenue" in day, "Missing revenue"
            assert "transactions" in day, "Missing transactions"
        
        print(f"✓ Daily revenue trend: {len(daily_trend)} days of data")
    
    def test_03_revenue_breakdown_top_users(self):
        """Test: Revenue breakdown includes top spending users"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/revenue-breakdown?days=30",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate top users structure
        assert "topUsers" in data
        top_users = data["topUsers"]
        
        for user in top_users:
            assert "userId" in user, "Missing userId"
            assert "email" in user, "Missing email"
            assert "totalSpent" in user, "Missing totalSpent"
            assert "transactions" in user, "Missing transactions"
        
        print(f"✓ Top users: {len(top_users)} users in breakdown")


class TestLiveStatsAndSnapshot:
    """Test core snapshot and live-stats endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup API session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Authenticate as admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_01_snapshot_complete_structure(self):
        """Test: Snapshot returns complete analytics data"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/snapshot",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate all required fields
        required_fields = [
            "timestamp", "period", "liveMetrics", "performance",
            "revenue", "generationsByType", "hourlyActivity", "recentActivity"
        ]
        for field in required_fields:
            assert field in data, f"Missing {field}"
        
        # Validate liveMetrics
        live = data["liveMetrics"]
        live_fields = ["activeUsers", "totalUsers", "newUsersToday", 
                      "todayLogins", "todayGenerations", "creditsUsedToday"]
        for field in live_fields:
            assert field in live, f"Missing {field} in liveMetrics"
        
        # Validate performance
        perf = data["performance"]
        assert "successRate" in perf
        assert "totalJobs24h" in perf
        assert "successfulJobs24h" in perf
        
        # Validate revenue
        rev = data["revenue"]
        assert "today" in rev
        assert "last7Days" in rev
        assert "currency" in rev
        
        print(f"✓ Snapshot complete: {live['totalUsers']} total users, {perf['successRate']}% success rate")
    
    def test_02_live_stats_endpoint(self):
        """Test: Live stats returns quick metrics"""
        token = self.get_admin_token()
        assert token is not None, "Admin login failed"
        
        response = self.session.get(
            f"{BASE_URL}/api/realtime-analytics/live-stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "activeSessions" in data
        assert "recentGenerations" in data
        assert "serverTime" in data
        assert "status" in data
        assert data["status"] == "healthy"
        
        print(f"✓ Live stats: {data['activeSessions']} active, status: {data['status']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
