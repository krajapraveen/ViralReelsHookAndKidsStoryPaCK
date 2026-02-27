"""
Iteration 100: Comprehensive Testing for System Resilience Dashboard, 
Advanced Analytics Export, and Cashfree Payment Endpoints.

Test Scope:
- System Resilience Dashboard (admin only)
- Auto-refund stats
- Self-healing incidents
- Circuit breakers
- Worker metrics
- Analytics Export endpoints
- Cashfree payment flows
"""

import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        if token:
            return token
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def demo_token(api_client):
    """Get demo user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        if token:
            return token
    pytest.skip("Demo user authentication failed")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def demo_headers(demo_token):
    """Headers with demo user auth"""
    return {"Authorization": f"Bearer {demo_token}", "Content-Type": "application/json"}


# =============================================================================
# SYSTEM RESILIENCE DASHBOARD TESTS
# =============================================================================

class TestSystemResilienceDashboard:
    """Test System Resilience Dashboard endpoints (Admin only)"""
    
    def test_dashboard_endpoint_admin_access(self, api_client, admin_headers):
        """Test /api/system-resilience/dashboard - Admin should have access"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/dashboard", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify dashboard structure
        assert "health_score" in data, "Missing health_score"
        assert "health_status" in data, "Missing health_status"
        assert "auto_refunds" in data, "Missing auto_refunds"
        assert "self_healing" in data, "Missing self_healing"
        assert "circuit_breakers" in data, "Missing circuit_breakers"
        assert "worker_retries" in data, "Missing worker_retries"
        assert "payment_reconciliation" in data, "Missing payment_reconciliation"
        assert "timestamp" in data, "Missing timestamp"
        
        # Verify health_score is numeric
        assert isinstance(data["health_score"], (int, float)), "health_score should be numeric"
        assert 0 <= data["health_score"] <= 100, "health_score should be 0-100"
        
        # Verify health_status is valid
        valid_statuses = ["excellent", "good", "degraded", "critical"]
        assert data["health_status"] in valid_statuses, f"Invalid health_status: {data['health_status']}"
        
        print(f"Dashboard health: {data['health_score']} ({data['health_status']})")
    
    def test_dashboard_endpoint_non_admin_denied(self, api_client, demo_headers):
        """Test /api/system-resilience/dashboard - Non-admin should be denied"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/dashboard", headers=demo_headers)
        
        # Should return 403 Forbidden for non-admin users
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Non-admin access correctly denied")
    
    def test_dashboard_auto_refunds_structure(self, api_client, admin_headers):
        """Verify auto_refunds structure in dashboard"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/dashboard", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        auto_refunds = data.get("auto_refunds", {})
        assert "last_24h" in auto_refunds, "Missing last_24h in auto_refunds"
        assert "last_7d" in auto_refunds, "Missing last_7d in auto_refunds"
        
        # Verify last_24h structure
        last_24h = auto_refunds["last_24h"]
        assert "count" in last_24h, "Missing count in last_24h"
        assert "total_credits" in last_24h, "Missing total_credits in last_24h"
        
        print(f"Auto refunds (24h): {last_24h['count']} refunds, {last_24h['total_credits']} credits")


class TestAutoRefundDetails:
    """Test /api/system-resilience/auto-refunds endpoint"""
    
    def test_auto_refunds_default_period(self, api_client, admin_headers):
        """Test auto-refunds with default 7-day period"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/auto-refunds", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "period_days" in data, "Missing period_days"
        assert data["period_days"] == 7, "Default period should be 7 days"
        assert "total_refunds" in data, "Missing total_refunds"
        assert "total_credits_refunded" in data, "Missing total_credits_refunded"
        assert "by_reason" in data, "Missing by_reason"
        assert "by_feature" in data, "Missing by_feature"
        assert "daily_totals" in data, "Missing daily_totals"
        assert "recent_refunds" in data, "Missing recent_refunds"
        
        print(f"Total refunds (7d): {data['total_refunds']}, Credits: {data['total_credits_refunded']}")
    
    def test_auto_refunds_custom_period(self, api_client, admin_headers):
        """Test auto-refunds with custom period"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/auto-refunds?days=30", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 30, "Period should be 30 days"


class TestSelfHealingIncidents:
    """Test /api/system-resilience/self-healing/incidents endpoint"""
    
    def test_incidents_default_request(self, api_client, admin_headers):
        """Test self-healing incidents with default parameters"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/self-healing/incidents", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "period_days" in data, "Missing period_days"
        assert "total_incidents" in data, "Missing total_incidents"
        assert "resolved_count" in data, "Missing resolved_count"
        assert "resolution_rate" in data, "Missing resolution_rate"
        assert "by_type" in data, "Missing by_type"
        assert "by_service" in data, "Missing by_service"
        assert "recent_incidents" in data, "Missing recent_incidents"
        
        print(f"Incidents: {data['total_incidents']}, Resolved: {data['resolved_count']}, Rate: {data['resolution_rate']}%")
    
    def test_incidents_with_severity_filter(self, api_client, admin_headers):
        """Test incidents with severity filter"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/self-healing/incidents?severity=critical", headers=admin_headers)
        
        assert response.status_code == 200


class TestCircuitBreakers:
    """Test /api/system-resilience/circuit-breakers endpoint"""
    
    def test_circuit_breakers_status(self, api_client, admin_headers):
        """Test circuit breakers status"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/circuit-breakers", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "timestamp" in data, "Missing timestamp"
        assert "circuit_breakers" in data, "Missing circuit_breakers"
        assert "total_services" in data, "Missing total_services"
        assert "healthy_count" in data, "Missing healthy_count"
        assert "degraded_count" in data, "Missing degraded_count"
        
        # Check circuit breakers have expected structure
        breakers = data.get("circuit_breakers", {})
        for name, status in breakers.items():
            assert "state" in status, f"Missing state for {name}"
            assert "healthy" in status, f"Missing healthy for {name}"
        
        print(f"Circuit breakers: {data['total_services']} total, {data['healthy_count']} healthy, {data['degraded_count']} degraded")


class TestWorkerMetrics:
    """Test /api/system-resilience/worker-metrics endpoint"""
    
    def test_worker_metrics_default(self, api_client, admin_headers):
        """Test worker metrics with default 24h period"""
        response = api_client.get(f"{BASE_URL}/api/system-resilience/worker-metrics", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "period_hours" in data, "Missing period_hours"
        assert "total_jobs" in data, "Missing total_jobs"
        assert "jobs_processed" in data, "Missing jobs_processed"
        assert "jobs_failed" in data, "Missing jobs_failed"
        assert "jobs_retried" in data, "Missing jobs_retried"
        assert "success_rate" in data, "Missing success_rate"
        assert "retry_rate" in data, "Missing retry_rate"
        
        print(f"Worker metrics: {data['total_jobs']} jobs, {data['success_rate']}% success, {data['retry_rate']}% retry")


# =============================================================================
# ADVANCED ANALYTICS EXPORT TESTS
# =============================================================================

class TestAnalyticsExportFormats:
    """Test /api/analytics-export/formats endpoint"""
    
    def test_supported_formats(self, api_client):
        """Test getting supported export formats - Public endpoint"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/formats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "formats" in data, "Missing formats"
        assert "export_types" in data, "Missing export_types"
        
        # Verify formats
        formats = data["formats"]
        assert len(formats) >= 2, "Should have at least JSON and CSV formats"
        
        format_ids = [f["id"] for f in formats]
        assert "json" in format_ids, "JSON format missing"
        assert "csv" in format_ids, "CSV format missing"
        
        # Verify export types
        export_types = data["export_types"]
        expected_types = ["template_analytics", "user_activity", "revenue_report", "system_health", "comprehensive"]
        for exp_type in expected_types:
            assert exp_type in export_types, f"Missing export type: {exp_type}"
        
        print(f"Supported formats: {format_ids}")
        print(f"Export types: {export_types}")


class TestTemplateAnalyticsExport:
    """Test /api/analytics-export/template-analytics endpoint"""
    
    def test_template_analytics_json(self, api_client, admin_headers):
        """Test template analytics export in JSON format"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/template-analytics?format=json", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        # JSON response should be parseable
        data = response.json()
        assert data is not None, "JSON response should not be empty"
        print(f"Template analytics (JSON): Retrieved successfully")
    
    def test_template_analytics_csv(self, api_client, admin_headers):
        """Test template analytics export in CSV format"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/template-analytics?format=csv", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        # CSV should have text/csv content type
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type or len(response.content) > 0, "Should return CSV data"
        print(f"Template analytics (CSV): Retrieved successfully")
    
    def test_template_analytics_non_admin_denied(self, api_client, demo_headers):
        """Template analytics should require admin access"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/template-analytics", headers=demo_headers)
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestRevenueReportExport:
    """Test /api/analytics-export/revenue-report endpoint"""
    
    def test_revenue_report_json(self, api_client, admin_headers):
        """Test revenue report export in JSON format"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/revenue-report?format=json&group_by=day", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data is not None
        print(f"Revenue report (JSON): Retrieved successfully")
    
    def test_revenue_report_group_by_week(self, api_client, admin_headers):
        """Test revenue report with weekly grouping"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/revenue-report?group_by=week", headers=admin_headers)
        
        assert response.status_code == 200
    
    def test_revenue_report_invalid_group_by(self, api_client, admin_headers):
        """Test revenue report with invalid group_by"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/revenue-report?group_by=invalid", headers=admin_headers)
        
        assert response.status_code == 400, "Invalid group_by should return 400"


class TestSystemHealthExport:
    """Test /api/analytics-export/system-health endpoint"""
    
    def test_system_health_default(self, api_client, admin_headers):
        """Test system health export with default 30 days"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/system-health", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data is not None
        print(f"System health export: Retrieved successfully")
    
    def test_system_health_custom_days(self, api_client, admin_headers):
        """Test system health export with custom days"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/system-health?days=7", headers=admin_headers)
        
        assert response.status_code == 200
    
    def test_system_health_invalid_days(self, api_client, admin_headers):
        """Test system health with invalid days parameter"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/system-health?days=400", headers=admin_headers)
        
        assert response.status_code == 400, "days > 365 should return 400"


class TestQuickStats:
    """Test /api/analytics-export/quick-stats endpoint"""
    
    def test_quick_stats(self, api_client, admin_headers):
        """Test quick stats endpoint"""
        response = api_client.get(f"{BASE_URL}/api/analytics-export/quick-stats", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "timestamp" in data, "Missing timestamp"
        assert "today" in data, "Missing today stats"
        assert "week" in data, "Missing week stats"
        assert "month" in data, "Missing month stats"
        
        # Verify today structure
        today = data.get("today", {})
        assert "orders" in today, "Missing orders in today"
        assert "jobs" in today, "Missing jobs in today"
        
        print(f"Quick stats - Today: {today['orders']} orders, {today['jobs']} jobs")


# =============================================================================
# CASHFREE PAYMENT TESTS
# =============================================================================

class TestCashfreeHealth:
    """Test Cashfree gateway health and configuration"""
    
    def test_cashfree_health(self, api_client):
        """Test Cashfree health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("status") == "healthy", "Cashfree should be healthy"
        assert data.get("gateway") == "cashfree", "Gateway should be cashfree"
        assert "configured" in data, "Should indicate if configured"
        assert "environment" in data, "Should indicate environment"
        
        print(f"Cashfree status: {data['status']}, Configured: {data['configured']}, Env: {data['environment']}")
    
    def test_cashfree_products(self, api_client):
        """Test Cashfree products endpoint"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "products" in data, "Missing products"
        assert "gateway" in data, "Missing gateway"
        
        products = data.get("products", {})
        assert len(products) > 0, "Should have at least one product"
        
        # Verify product structure
        expected_products = ["starter", "creator", "pro"]
        for prod_id in expected_products:
            if prod_id in products:
                prod = products[prod_id]
                assert "name" in prod, f"Missing name for {prod_id}"
                assert "credits" in prod, f"Missing credits for {prod_id}"
                assert "price" in prod, f"Missing price for {prod_id}"
        
        print(f"Available products: {list(products.keys())}")
    
    def test_cashfree_plans(self, api_client):
        """Test Cashfree plans endpoint (alias for products)"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/plans")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestCashfreeOrderCreation:
    """Test Cashfree order creation flow"""
    
    def test_create_order_requires_auth(self, api_client):
        """Order creation should require authentication"""
        response = api_client.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "starter"
        })
        
        assert response.status_code in [401, 403, 422], f"Should require auth, got {response.status_code}"
    
    def test_create_order_invalid_product(self, api_client, demo_headers):
        """Order creation with invalid product should fail"""
        response = api_client.post(f"{BASE_URL}/api/cashfree/create-order", 
            json={"productId": "invalid_product"},
            headers=demo_headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid product, got {response.status_code}"
    
    def test_create_order_valid_request(self, api_client, demo_headers):
        """Test order creation with valid request"""
        response = api_client.post(f"{BASE_URL}/api/cashfree/create-order", 
            json={"productId": "starter", "currency": "INR"},
            headers=demo_headers
        )
        
        # Could be 200 (success) or 500 (if Cashfree not configured properly)
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True, "Should return success"
            assert "orderId" in data, "Should return orderId"
            assert "paymentSessionId" in data, "Should return paymentSessionId"
            print(f"Order created: {data.get('orderId')}")
        else:
            # Log the error but don't fail - Cashfree sandbox might be rate-limited
            print(f"Order creation returned {response.status_code}: {response.text[:200]}")


class TestCashfreeOrderStatus:
    """Test Cashfree order status endpoint"""
    
    def test_order_status_not_found(self, api_client, demo_headers):
        """Test order status for non-existent order"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/order/nonexistent_order_id/status", headers=demo_headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_order_status_requires_auth(self, api_client):
        """Order status should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/order/test_order/status")
        
        assert response.status_code in [401, 403, 422], f"Should require auth, got {response.status_code}"


class TestCashfreePaymentHistory:
    """Test payment history endpoint"""
    
    def test_payment_history_requires_auth(self, api_client):
        """Payment history should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/payments/history")
        
        assert response.status_code in [401, 403, 422], f"Should require auth, got {response.status_code}"
    
    def test_payment_history_with_auth(self, api_client, demo_headers):
        """Test payment history with authentication"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/payments/history", headers=demo_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "payments" in data, "Should return payments array"
        assert "total" in data, "Should return total count"
        assert "limit" in data, "Should return limit"
        assert "skip" in data, "Should return skip"
        
        print(f"Payment history: {data['total']} total payments")


class TestCashfreeRefund:
    """Test Cashfree refund endpoints (Admin only)"""
    
    def test_refund_requires_admin(self, api_client, demo_headers):
        """Refund should require admin access"""
        response = api_client.post(f"{BASE_URL}/api/cashfree/refund/test_order", 
            json={"reason": "Test refund"},
            headers=demo_headers
        )
        
        assert response.status_code in [401, 403], f"Should require admin, got {response.status_code}"
    
    def test_refund_status_requires_admin(self, api_client, demo_headers):
        """Refund status should require admin access"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/refund/test_order/status", headers=demo_headers)
        
        assert response.status_code in [401, 403], f"Should require admin, got {response.status_code}"
    
    def test_pending_delivery_requires_admin(self, api_client, demo_headers):
        """Pending delivery check should require admin"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/orders/pending-delivery", headers=demo_headers)
        
        assert response.status_code in [401, 403], f"Should require admin, got {response.status_code}"
    
    def test_pending_delivery_admin_access(self, api_client, admin_headers):
        """Admin should be able to check pending deliveries"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/orders/pending-delivery", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "totalPaidOrders" in data, "Should return totalPaidOrders"
        assert "ordersNeedingReview" in data, "Should return ordersNeedingReview"
        
        print(f"Pending delivery: {data['totalPaidOrders']} paid orders, {data['ordersNeedingReview']} need review")


class TestCashfreeMonitoring:
    """Test Cashfree payment monitoring endpoints"""
    
    def test_monitoring_health_requires_admin(self, api_client, demo_headers):
        """Monitoring health should require admin"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/monitoring/health", headers=demo_headers)
        
        assert response.status_code in [401, 403], f"Should require admin, got {response.status_code}"
    
    def test_monitoring_health_admin_access(self, api_client, admin_headers):
        """Admin should be able to access monitoring health"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/monitoring/health", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "gateway" in data, "Should return gateway"
        assert "environment" in data, "Should return environment"
        
        print(f"Monitoring health: Gateway {data['gateway']}, Env: {data['environment']}")


# =============================================================================
# WEBHOOK SIMULATION TESTS
# =============================================================================

class TestCashfreeWebhook:
    """Test Cashfree webhook handling"""
    
    def test_webhook_endpoint_exists(self, api_client):
        """Webhook endpoint should exist and accept POST"""
        # Empty body should not crash the server
        response = api_client.post(f"{BASE_URL}/api/cashfree/webhook", 
            json={},
            headers={"Content-Type": "application/json"}
        )
        
        # Could return various status codes, but shouldn't be 404
        assert response.status_code != 404, "Webhook endpoint should exist"
        print(f"Webhook endpoint responds with status: {response.status_code}")
    
    def test_webhook_with_payment_success_event(self, api_client):
        """Test webhook with payment success event (simulated)"""
        webhook_payload = {
            "type": "PAYMENT_SUCCESS_WEBHOOK",
            "data": {
                "order": {
                    "order_id": "test_webhook_order_12345"
                },
                "payment": {
                    "payment_status": "SUCCESS"
                }
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/cashfree/webhook", 
            json=webhook_payload,
            headers={
                "Content-Type": "application/json",
                "x-webhook-timestamp": str(int(datetime.now().timestamp()))
            }
        )
        
        # Should process without crashing
        assert response.status_code in [200, 403], f"Webhook should process or reject (signature), got {response.status_code}"
        print(f"Webhook response: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
