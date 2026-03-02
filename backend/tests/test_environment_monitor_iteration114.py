"""
Environment Monitor Feature Testing - Iteration 114
Tests for Database Environment Monitoring and Auto-Reconnection system
Endpoints:
- GET /api/environment-monitor/status - returns current environment status
- GET /api/environment-monitor/health-check - public endpoint returns health status
- POST /api/environment-monitor/check-production - simulates production check
- POST /api/environment-monitor/reconnect-production - triggers manual reconnection
- POST /api/environment-monitor/toggle-auto-fix - enables/disables auto-fix
- GET /api/environment-monitor/alerts - returns alert history
- GET /api/environment-monitor/fix-history - returns fix attempt history
- POST /api/environment-monitor/test-alert - sends test email
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test admin credentials
ADMIN_EMAIL = "krajapraveen.katta@creatorstudio.ai"
ADMIN_PASSWORD = "Onemanarmy@1979#"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestEnvironmentMonitorPublicEndpoints:
    """Test public endpoints that don't require authentication"""
    
    def test_health_check_endpoint(self, api_client):
        """GET /api/environment-monitor/health-check - Public health check"""
        response = api_client.get(f"{BASE_URL}/api/environment-monitor/health-check")
        
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "status" in data, "Missing 'status' field"
        assert "database" in data, "Missing 'database' field"
        assert "environment" in data, "Missing 'environment' field"
        assert "is_production" in data, "Missing 'is_production' field"
        assert "auto_fix_enabled" in data, "Missing 'auto_fix_enabled' field"
        assert "timestamp" in data, "Missing 'timestamp' field"
        assert "version" in data, "Missing 'version' field"
        
        # Verify expected values based on context (localhost MongoDB = PRODUCTION_USING_LOCALHOST_DATABASE)
        assert data["version"] == "2.0.0", f"Unexpected version: {data['version']}"
        print(f"Health check: status={data['status']}, db={data['database']}, env={data['environment']}")


class TestEnvironmentMonitorAuthRequired:
    """Test authenticated endpoints - admin access required"""
    
    def test_get_environment_status(self, authenticated_client):
        """GET /api/environment-monitor/status - Get current environment status"""
        response = authenticated_client.get(f"{BASE_URL}/api/environment-monitor/status")
        
        assert response.status_code == 200, f"Status endpoint failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "data" in data, "Missing 'data' field"
        
        status_data = data["data"]
        # Verify structure
        assert "status" in status_data, "Missing 'status' in data"
        assert "current_environment" in status_data, "Missing 'current_environment'"
        assert "expected_production_db" in status_data, "Missing 'expected_production_db'"
        assert "monitoring_active" in status_data, "Missing 'monitoring_active'"
        assert "auto_fix_enabled" in status_data, "Missing 'auto_fix_enabled'"
        assert "alert_recipients" in status_data, "Missing 'alert_recipients'"
        
        # Verify current environment details
        env = status_data["current_environment"]
        assert "database_name" in env, "Missing 'database_name'"
        assert "detected_environment" in env, "Missing 'detected_environment'"
        assert "is_production_db" in env, "Missing 'is_production_db'"
        assert "is_localhost" in env, "Missing 'is_localhost'"
        
        print(f"Environment status: {status_data['status']}, db={env['database_name']}, env={env['detected_environment']}")
    
    def test_get_alerts(self, authenticated_client):
        """GET /api/environment-monitor/alerts - Get alert history"""
        response = authenticated_client.get(f"{BASE_URL}/api/environment-monitor/alerts?days=30")
        
        assert response.status_code == 200, f"Alerts endpoint failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "period_days" in data, "Missing 'period_days'"
        assert "total_alerts" in data, "Missing 'total_alerts'"
        assert "alerts" in data, "Missing 'alerts' list"
        assert isinstance(data["alerts"], list), "'alerts' should be a list"
        
        print(f"Alerts: total={data['total_alerts']} in last {data['period_days']} days")
    
    def test_get_fix_history(self, authenticated_client):
        """GET /api/environment-monitor/fix-history - Get fix attempt history"""
        response = authenticated_client.get(f"{BASE_URL}/api/environment-monitor/fix-history?days=30")
        
        assert response.status_code == 200, f"Fix history endpoint failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "period_days" in data, "Missing 'period_days'"
        assert "total_fixes" in data, "Missing 'total_fixes'"
        assert "fixes" in data, "Missing 'fixes' list"
        assert isinstance(data["fixes"], list), "'fixes' should be a list"
        
        print(f"Fix history: total={data['total_fixes']} in last {data['period_days']} days")
    
    def test_get_database_info(self, authenticated_client):
        """GET /api/environment-monitor/database-info - Get database information"""
        response = authenticated_client.get(f"{BASE_URL}/api/environment-monitor/database-info")
        
        assert response.status_code == 200, f"Database info endpoint failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "database" in data, "Missing 'database'"
        assert "stats" in data, "Missing 'stats'"
        
        db_info = data["database"]
        assert "name" in db_info, "Missing database 'name'"
        assert "environment" in db_info, "Missing database 'environment'"
        assert "is_production" in db_info, "Missing 'is_production'"
        
        print(f"Database info: name={db_info['name']}, env={db_info['environment']}, prod={db_info['is_production']}")
    
    def test_check_production_environment(self, authenticated_client):
        """POST /api/environment-monitor/check-production - Simulate production check"""
        response = authenticated_client.post(f"{BASE_URL}/api/environment-monitor/check-production")
        
        assert response.status_code == 200, f"Check production endpoint failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "production_check" in data, "Missing 'production_check'"
        assert "message" in data, "Missing 'message'"
        
        check = data["production_check"]
        assert "mismatch_detected" in check, "Missing 'mismatch_detected'"
        assert "environment_info" in check, "Missing 'environment_info'"
        
        # Log result based on mismatch status
        if check["mismatch_detected"]:
            print(f"Mismatch detected: {check.get('mismatch_type')}, severity={check.get('severity')}")
        else:
            print("No mismatch detected - production environment OK")
    
    def test_toggle_auto_fix_enable(self, authenticated_client):
        """POST /api/environment-monitor/toggle-auto-fix - Enable auto-fix"""
        response = authenticated_client.post(f"{BASE_URL}/api/environment-monitor/toggle-auto-fix?enabled=true")
        
        assert response.status_code == 200, f"Toggle auto-fix failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "auto_fix_enabled" in data, "Missing 'auto_fix_enabled'"
        assert data["auto_fix_enabled"] == True, "Auto-fix should be enabled"
        
        print(f"Auto-fix toggled: enabled={data['auto_fix_enabled']}")
    
    def test_toggle_auto_fix_disable_and_enable(self, authenticated_client):
        """POST /api/environment-monitor/toggle-auto-fix - Toggle auto-fix off then on"""
        # Disable
        response = authenticated_client.post(f"{BASE_URL}/api/environment-monitor/toggle-auto-fix?enabled=false")
        assert response.status_code == 200, f"Toggle auto-fix (disable) failed: {response.text}"
        
        data = response.json()
        assert data.get("auto_fix_enabled") == False, "Auto-fix should be disabled"
        print("Auto-fix disabled")
        
        # Re-enable
        response = authenticated_client.post(f"{BASE_URL}/api/environment-monitor/toggle-auto-fix?enabled=true")
        assert response.status_code == 200, f"Toggle auto-fix (enable) failed: {response.text}"
        
        data = response.json()
        assert data.get("auto_fix_enabled") == True, "Auto-fix should be enabled"
        print("Auto-fix re-enabled")


class TestEnvironmentMonitorUnauthenticated:
    """Test that authenticated endpoints reject unauthenticated requests"""
    
    def test_status_requires_auth(self, api_client):
        """GET /api/environment-monitor/status without auth should fail"""
        # Remove auth header if present
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.get(f"{BASE_URL}/api/environment-monitor/status")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403 but got {response.status_code}"
        print(f"Status without auth: {response.status_code} - correctly rejected")
    
    def test_alerts_requires_auth(self, api_client):
        """GET /api/environment-monitor/alerts without auth should fail"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/environment-monitor/alerts")
        
        assert response.status_code in [401, 403], f"Expected 401/403 but got {response.status_code}"
        print(f"Alerts without auth: {response.status_code} - correctly rejected")


class TestEnvironmentMonitorEdgeCases:
    """Test edge cases and validation"""
    
    def test_alerts_with_custom_days(self, authenticated_client):
        """GET /api/environment-monitor/alerts with different days parameter"""
        for days in [7, 14, 30, 60]:
            response = authenticated_client.get(f"{BASE_URL}/api/environment-monitor/alerts?days={days}")
            assert response.status_code == 200, f"Alerts with days={days} failed"
            data = response.json()
            assert data["period_days"] == days, f"Expected period_days={days}"
        print("Alerts with custom days parameters: OK")
    
    def test_fix_history_with_custom_days(self, authenticated_client):
        """GET /api/environment-monitor/fix-history with different days parameter"""
        for days in [7, 14, 30]:
            response = authenticated_client.get(f"{BASE_URL}/api/environment-monitor/fix-history?days={days}")
            assert response.status_code == 200, f"Fix history with days={days} failed"
            data = response.json()
            assert data["period_days"] == days, f"Expected period_days={days}"
        print("Fix history with custom days parameters: OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
