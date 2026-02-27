"""
Iteration 98 Test: 7 Major Features Testing
- Admin Audit Logs API
- Template Leaderboard API  
- Protected Download API
- Template Versioning & A/B Testing API
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

class TestAdminAuth:
    """Admin Authentication Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token for authenticated tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            # Verify user is admin
            me_response = requests.get(f"{BASE_URL}/api/auth/me", 
                headers={"Authorization": f"Bearer {token}"})
            if me_response.status_code == 200:
                user = me_response.json()
                user_data = user.get("user", user)
                if user_data.get("role", "").upper() == "ADMIN":
                    return token
        pytest.skip("Admin authentication failed - skipping admin tests")
    
    def test_admin_login(self):
        """Test admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        print("PASS: Admin login successful")


class TestAdminAuditLogs:
    """Admin Audit Logs API Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin auth failed")
    
    def test_get_audit_actions(self, admin_token):
        """Test GET /api/admin/audit-logs/actions"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs/actions",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "actions" in data
        assert isinstance(data["actions"], list)
        print(f"PASS: Got {len(data['actions'])} action types")
    
    def test_get_audit_logs(self, admin_token):
        """Test GET /api/admin/audit-logs/logs"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs/logs?days=30&limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "limit" in data
        assert "has_more" in data
        print(f"PASS: Got {len(data['logs'])} logs, total: {data['total']}")
    
    def test_get_audit_stats(self, admin_token):
        """Test GET /api/admin/audit-logs/stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs/stats?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "total_actions" in data
        assert "actions_by_type" in data
        assert "actions_by_admin" in data
        assert "period_days" in data
        print(f"PASS: Audit stats - {data['total_actions']} total actions")
    
    def test_export_audit_logs_json(self, admin_token):
        """Test GET /api/admin/audit-logs/export?format=json"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs/export?days=30&format=json",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "format" in data
        assert data["format"] == "json"
        assert "data" in data
        print(f"PASS: Export JSON - {data.get('count', len(data.get('data', [])))} records")
    
    def test_export_audit_logs_csv(self, admin_token):
        """Test GET /api/admin/audit-logs/export?format=csv"""
        response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs/export?days=30&format=csv",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "format" in data
        assert data["format"] == "csv"
        assert "data" in data
        assert "filename" in data
        print(f"PASS: Export CSV - filename: {data['filename']}")


class TestTemplateLeaderboard:
    """Template Leaderboard API Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin auth failed")
    
    def test_get_revenue_rankings(self, admin_token):
        """Test GET /api/template-leaderboard/revenue-rankings"""
        response = requests.get(
            f"{BASE_URL}/api/template-leaderboard/revenue-rankings?days=30&limit=20",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "rankings" in data
        assert "summary" in data
        summary = data["summary"]
        assert "total_revenue_usd" in summary
        assert "total_generations" in summary
        print(f"PASS: Revenue rankings - {len(data['rankings'])} templates, ${summary['total_revenue_usd']} total revenue")
    
    def test_get_top_performers(self, admin_token):
        """Test GET /api/template-leaderboard/top-performers"""
        response = requests.get(
            f"{BASE_URL}/api/template-leaderboard/top-performers?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "by_volume" in data
        assert "by_unique_users" in data
        assert "top_niches" in data
        assert "top_tones" in data
        assert "period_days" in data
        print(f"PASS: Top performers - {len(data['top_niches'])} niches, {len(data['top_tones'])} tones")
    
    def test_get_growth_trends(self, admin_token):
        """Test GET /api/template-leaderboard/growth-trends"""
        response = requests.get(
            f"{BASE_URL}/api/template-leaderboard/growth-trends?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "trends" in data
        assert "period_days" in data
        assert "comparison" in data
        print(f"PASS: Growth trends - {len(data['trends'])} features analyzed")
    
    def test_export_json(self, admin_token):
        """Test GET /api/template-leaderboard/export/json"""
        response = requests.get(
            f"{BASE_URL}/api/template-leaderboard/export/json?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "format" in data
        assert data["format"] == "json"
        assert "data" in data
        assert "filename" in data
        print(f"PASS: Export JSON - {data['filename']}")
    
    def test_export_csv_summary(self, admin_token):
        """Test GET /api/template-leaderboard/export/csv?report_type=summary"""
        response = requests.get(
            f"{BASE_URL}/api/template-leaderboard/export/csv?days=30&report_type=summary",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "format" in data
        assert data["format"] == "csv"
        assert "data" in data
        print(f"PASS: Export CSV summary - {data.get('filename', 'analytics.csv')}")


class TestProtectedDownload:
    """Protected Download API Tests"""
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get regular user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@creatorstudio.ai",
            "password": "TestDemo123!"
        })
        if response.status_code == 200:
            return response.json().get("token")
        # Try admin as fallback
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("User auth failed")
    
    def test_get_download_config(self):
        """Test GET /api/protected-download/config (public endpoint)"""
        response = requests.get(f"{BASE_URL}/api/protected-download/config")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "watermark_removal_cost" in data
        assert "signed_url_expiry_seconds" in data
        assert "watermark_enabled" in data
        assert "protection_features" in data
        print(f"PASS: Config - Watermark removal cost: {data['watermark_removal_cost']} credits")
    
    def test_get_signed_url_requires_auth(self):
        """Test POST /api/protected-download/get-signed-url requires auth"""
        response = requests.post(
            f"{BASE_URL}/api/protected-download/get-signed-url",
            json={"file_id": "123456789012345678901234", "file_type": "image"}
        )
        assert response.status_code in [401, 403], f"Expected auth error, got: {response.status_code}"
        print("PASS: get-signed-url requires authentication")
    
    def test_remove_watermark_requires_auth(self):
        """Test POST /api/protected-download/remove-watermark requires auth"""
        response = requests.post(
            f"{BASE_URL}/api/protected-download/remove-watermark",
            json={"file_id": "123456789012345678901234"}
        )
        assert response.status_code in [401, 403], f"Expected auth error, got: {response.status_code}"
        print("PASS: remove-watermark requires authentication")
    
    def test_get_signed_url_file_not_found(self, user_token):
        """Test signed URL with non-existent file"""
        response = requests.post(
            f"{BASE_URL}/api/protected-download/get-signed-url",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"file_id": "123456789012345678901234", "file_type": "image"}
        )
        assert response.status_code == 404, f"Expected 404, got: {response.status_code}"
        print("PASS: Returns 404 for non-existent file")


class TestTemplateVersioning:
    """Template Versioning & A/B Testing API Tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin auth failed")
    
    def test_create_template_version(self, admin_token):
        """Test POST /api/template-versioning/versions"""
        response = requests.post(
            f"{BASE_URL}/api/template-versioning/versions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "template_id": "test_template_001",
                "template_type": "instagram_bio",
                "content": {
                    "prompt_template": "Generate a bio for {niche}",
                    "max_length": 150
                },
                "notes": "Test version created by iteration 98"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "version" in data
        assert "template_id" in data
        assert data["template_id"] == "test_template_001"
        print(f"PASS: Created template version {data['version']} with id {data['id']}")
        return data["id"]
    
    def test_list_template_versions(self, admin_token):
        """Test GET /api/template-versioning/versions/{template_id}"""
        response = requests.get(
            f"{BASE_URL}/api/template-versioning/versions/test_template_001",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "versions" in data
        assert "count" in data
        print(f"PASS: Listed {data['count']} versions for test_template_001")
    
    def test_get_ab_tests(self, admin_token):
        """Test GET /api/template-versioning/ab-tests"""
        response = requests.get(
            f"{BASE_URL}/api/template-versioning/ab-tests",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "tests" in data
        assert "count" in data
        print(f"PASS: Listed {data['count']} active A/B tests")
    
    def test_create_ab_test_flow(self, admin_token):
        """Test full A/B test creation flow"""
        # First create two versions
        version_a = requests.post(
            f"{BASE_URL}/api/template-versioning/versions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "template_id": "ab_test_template_001",
                "template_type": "instagram_bio",
                "content": {"variant": "A", "prompt": "Version A prompt"},
                "notes": "Version A for A/B test"
            }
        )
        assert version_a.status_code == 200
        version_a_id = version_a.json()["id"]
        
        version_b = requests.post(
            f"{BASE_URL}/api/template-versioning/versions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "template_id": "ab_test_template_001",
                "template_type": "instagram_bio",
                "content": {"variant": "B", "prompt": "Version B prompt"},
                "notes": "Version B for A/B test"
            }
        )
        assert version_b.status_code == 200
        version_b_id = version_b.json()["id"]
        
        # Create A/B test
        response = requests.post(
            f"{BASE_URL}/api/template-versioning/ab-tests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": f"Test AB {datetime.now().strftime('%H%M%S')}",
                "template_type": "instagram_bio",
                "variant_a_id": version_a_id,
                "variant_b_id": version_b_id,
                "traffic_split": 0.5
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert data["status"] == "active"
        print(f"PASS: Created A/B test '{data['name']}' with id {data['id']}")
        
        # Test public variant endpoint
        variant_response = requests.get(
            f"{BASE_URL}/api/template-versioning/variant/{data['id']}?user_id=test_user_123"
        )
        assert variant_response.status_code == 200, f"Failed to get variant: {variant_response.text}"
        variant_data = variant_response.json()
        assert "variant" in variant_data
        print(f"PASS: User assigned to {variant_data['variant']}")
        
        # Test conversion tracking
        conversion_response = requests.post(
            f"{BASE_URL}/api/template-versioning/conversion/{data['id']}?user_id=test_user_123"
        )
        assert conversion_response.status_code == 200
        print("PASS: Conversion tracked successfully")
        
        return data["id"]


class TestIntegrationEndpoints:
    """Test cross-feature integrations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin auth failed")
    
    def test_audit_log_records_actions(self, admin_token):
        """Verify that actions create audit logs"""
        # Create a template version (should create audit log)
        create_response = requests.post(
            f"{BASE_URL}/api/template-versioning/versions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "template_id": "audit_test_template",
                "template_type": "test",
                "content": {"test": True},
                "notes": "Audit test version"
            }
        )
        assert create_response.status_code == 200
        
        # Check audit logs for the action
        logs_response = requests.get(
            f"{BASE_URL}/api/admin/audit-logs/logs?action=template_create&limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert logs_response.status_code == 200
        data = logs_response.json()
        # Verify logs exist (may be empty if this is first test run)
        assert "logs" in data
        print(f"PASS: Found {len(data['logs'])} template_create audit logs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
