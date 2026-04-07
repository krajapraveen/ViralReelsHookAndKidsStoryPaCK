"""
Admin Payment Verification Dashboard API Tests - Iteration 453
Tests for /api/admin/payments/* endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
NON_ADMIN_EMAIL = "newuser@test.com"
NON_ADMIN_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert "token" in data
    assert data["user"]["role"] == "ADMIN"
    return data["token"]


@pytest.fixture(scope="module")
def non_admin_token():
    """Get non-admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": NON_ADMIN_EMAIL,
        "password": NON_ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Non-admin user not available for testing")
    data = response.json()
    return data.get("token")


class TestAdminPaymentsStats:
    """Tests for GET /api/admin/payments/stats"""
    
    def test_stats_returns_environment_and_counts(self, admin_token):
        """Stats endpoint returns environment badge and all required metrics"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify environment badge
        assert "environment" in data
        assert data["environment"] in ["PRODUCTION", "SANDBOX"]
        
        # Verify all 8 stat cards are present
        required_fields = [
            "orders_today",
            "succeeded_today", 
            "failed_today",
            "webhook_events_today",
            "webhook_failures_today",
            "unreconciled_orders",
            "settlements_pending",
            "revenue_today"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], (int, float)), f"{field} should be numeric"
        
        # Verify cashfree_configured flag
        assert "cashfree_configured" in data
        assert isinstance(data["cashfree_configured"], bool)
    
    def test_stats_requires_admin(self, non_admin_token):
        """Stats endpoint requires ADMIN role"""
        if not non_admin_token:
            pytest.skip("Non-admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/stats",
            headers={"Authorization": f"Bearer {non_admin_token}"}
        )
        assert response.status_code == 403
        assert "Admin access required" in response.json().get("detail", "")


class TestAdminPaymentsOrders:
    """Tests for GET /api/admin/payments/orders"""
    
    def test_orders_returns_list_with_enrichment(self, admin_token):
        """Orders endpoint returns orders with webhook enrichment"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "orders" in data
        assert "environment" in data
        assert isinstance(data["orders"], list)
        
        if data["orders"]:
            order = data["orders"][0]
            # Verify required columns
            required_fields = [
                "order_id", "userEmail", "productName", "displayAmount",
                "status", "webhook_received", "entitlementApplied"
            ]
            for field in required_fields:
                assert field in order, f"Missing field in order: {field}"
    
    def test_orders_filter_by_email(self, admin_token):
        """Orders can be filtered by email"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders?email=test@visionary-suite.com&limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for order in data["orders"]:
            assert "visionary-suite" in order["userEmail"].lower()
    
    def test_orders_filter_by_status(self, admin_token):
        """Orders can be filtered by status"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders?status=CREATED&limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for order in data["orders"]:
            assert order["status"] == "CREATED"
    
    def test_orders_unreconciled_filter(self, admin_token):
        """Unreconciled only filter works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders?unreconciled_only=true&limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Unreconciled orders should have status SUCCESS/PAID but entitlementApplied=False
        for order in data["orders"]:
            assert order["status"] in ["SUCCESS", "PAID"]
            assert order["entitlementApplied"] is not True
    
    def test_orders_requires_admin(self, non_admin_token):
        """Orders endpoint requires ADMIN role"""
        if not non_admin_token:
            pytest.skip("Non-admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders",
            headers={"Authorization": f"Bearer {non_admin_token}"}
        )
        assert response.status_code == 403


class TestAdminPaymentsOrderDrilldown:
    """Tests for GET /api/admin/payments/orders/{order_id}"""
    
    @pytest.fixture
    def sample_order_id(self, admin_token):
        """Get a sample order ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200 and response.json()["orders"]:
            return response.json()["orders"][0]["order_id"]
        pytest.skip("No orders available for drilldown testing")
    
    def test_drilldown_returns_4_panels(self, admin_token, sample_order_id):
        """Drilldown returns all 4 panels: order, user, cashfree, webhooks"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders/{sample_order_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify environment badge
        assert "environment" in data
        
        # Panel 1: Business View (order + user)
        assert "order" in data
        assert "user" in data
        
        # Panel 2: Cashfree Truth
        assert "cashfree" in data
        assert "order" in data["cashfree"]
        assert "payments" in data["cashfree"]
        assert "settlements" in data["cashfree"]
        
        # Panel 3: Webhook Trace
        assert "webhooks" in data
        assert isinstance(data["webhooks"], list)
        
        # Panel 4: Credit Transactions
        assert "credit_transactions" in data
        
        # Mismatch detection
        assert "mismatches" in data
        assert "mismatch_count" in data
        assert isinstance(data["mismatches"], list)
    
    def test_drilldown_business_view_fields(self, admin_token, sample_order_id):
        """Business View panel has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders/{sample_order_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        order = data["order"]
        required_order_fields = [
            "userEmail", "productName", "displayAmount", "status", "entitlementApplied"
        ]
        for field in required_order_fields:
            assert field in order, f"Missing order field: {field}"
    
    def test_drilldown_not_found(self, admin_token):
        """Drilldown returns 404 for non-existent order"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders/nonexistent_order_12345",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    def test_drilldown_requires_admin(self, non_admin_token, sample_order_id):
        """Drilldown requires ADMIN role"""
        if not non_admin_token:
            pytest.skip("Non-admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders/{sample_order_id}",
            headers={"Authorization": f"Bearer {non_admin_token}"}
        )
        assert response.status_code == 403


class TestAdminPaymentsWebhooks:
    """Tests for GET /api/admin/payments/webhooks"""
    
    def test_webhooks_returns_list(self, admin_token):
        """Webhooks endpoint returns list with required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/webhooks?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "webhooks" in data
        assert isinstance(data["webhooks"], list)
        
        if data["webhooks"]:
            webhook = data["webhooks"][0]
            required_fields = ["eventType", "orderId", "status", "receivedAt"]
            for field in required_fields:
                assert field in webhook, f"Missing webhook field: {field}"
    
    def test_webhooks_filter_by_order_id(self, admin_token):
        """Webhooks can be filtered by order ID"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/webhooks?order_id=cf_order&limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for webhook in data["webhooks"]:
            assert "cf_order" in webhook["orderId"]
    
    def test_webhooks_requires_admin(self, non_admin_token):
        """Webhooks endpoint requires ADMIN role"""
        if not non_admin_token:
            pytest.skip("Non-admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/webhooks",
            headers={"Authorization": f"Bearer {non_admin_token}"}
        )
        assert response.status_code == 403


class TestAdminPaymentsSettlements:
    """Tests for GET /api/admin/payments/settlements"""
    
    def test_settlements_returns_list(self, admin_token):
        """Settlements endpoint returns list with required fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/settlements?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "settlements" in data
        assert isinstance(data["settlements"], list)
        
        if data["settlements"]:
            settlement = data["settlements"][0]
            required_fields = ["order_id", "userEmail", "productName", "displayAmount", "status"]
            for field in required_fields:
                assert field in settlement, f"Missing settlement field: {field}"
    
    def test_settlements_requires_admin(self, non_admin_token):
        """Settlements endpoint requires ADMIN role"""
        if not non_admin_token:
            pytest.skip("Non-admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/settlements",
            headers={"Authorization": f"Bearer {non_admin_token}"}
        )
        assert response.status_code == 403


class TestAdminPaymentsReconcile:
    """Tests for POST /api/admin/payments/reconcile/{order_id}"""
    
    @pytest.fixture
    def sample_order_id(self, admin_token):
        """Get a sample order ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200 and response.json()["orders"]:
            return response.json()["orders"][0]["order_id"]
        pytest.skip("No orders available for reconcile testing")
    
    def test_reconcile_returns_actions_taken(self, admin_token, sample_order_id):
        """Reconcile endpoint returns actions_taken log"""
        response = requests.post(
            f"{BASE_URL}/api/admin/payments/reconcile/{sample_order_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "order_id" in data
        assert "request_id" in data
        assert "cf_order_status" in data
        assert "internal_status_before" in data
        assert "actions_taken" in data
        assert isinstance(data["actions_taken"], list)
    
    def test_reconcile_not_found(self, admin_token):
        """Reconcile returns 404 for non-existent order"""
        response = requests.post(
            f"{BASE_URL}/api/admin/payments/reconcile/nonexistent_order_12345",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    def test_reconcile_requires_admin(self, non_admin_token, sample_order_id):
        """Reconcile requires ADMIN role"""
        if not non_admin_token:
            pytest.skip("Non-admin token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/payments/reconcile/{sample_order_id}",
            headers={"Authorization": f"Bearer {non_admin_token}"}
        )
        assert response.status_code == 403


class TestAdminPaymentsFetchCashfree:
    """Tests for POST /api/admin/payments/fetch-cashfree/{order_id}"""
    
    @pytest.fixture
    def sample_order_id(self, admin_token):
        """Get a sample order ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/orders?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200 and response.json()["orders"]:
            return response.json()["orders"][0]["order_id"]
        pytest.skip("No orders available for fetch-cashfree testing")
    
    def test_fetch_cashfree_returns_data(self, admin_token, sample_order_id):
        """Fetch Cashfree endpoint returns order data without modifying DB"""
        response = requests.post(
            f"{BASE_URL}/api/admin/payments/fetch-cashfree/{sample_order_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "order" in data
        assert "payments" in data
        assert "settlements" in data
        assert "request_id" in data
        assert "environment" in data
    
    def test_fetch_cashfree_requires_admin(self, non_admin_token, sample_order_id):
        """Fetch Cashfree requires ADMIN role"""
        if not non_admin_token:
            pytest.skip("Non-admin token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/payments/fetch-cashfree/{sample_order_id}",
            headers={"Authorization": f"Bearer {non_admin_token}"}
        )
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
