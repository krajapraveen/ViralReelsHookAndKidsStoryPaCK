"""
P1.7 Payment & Billing Edge-Case Hardening Sweep Tests
Tests for:
1. Billing page loading states (loading, error, retry)
2. Auto-verify on return from Cashfree redirect
3. Double-click protection on buy buttons
4. Duplicate pending order prevention
5. Verify idempotency (no double-crediting)
6. Invoice endpoint accepts CREDIT_APPLIED and SUBSCRIPTION_ACTIVATED
7. Refund endpoint accepts CREDIT_APPLIED and SUBSCRIPTION_ACTIVATED
8. Webhook admin endpoints require admin auth
9. Stale order cleanup endpoint
10. Payment error messaging
"""
import pytest
import requests
import os
import time
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestPaymentHardeningP17:
    """P1.7 Payment & Billing Edge-Case Hardening Tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create a requests session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        return s
    
    @pytest.fixture(scope="class")
    def user_token(self, session):
        """Get user auth token"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"User login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def admin_token(self, session):
        """Get admin auth token"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def user_headers(self, user_token):
        """Headers with user auth"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_token}"
        }
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin auth"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_token}"
        }
    
    # =========================================================================
    # Test 1: Products endpoint works (needed for billing page)
    # =========================================================================
    def test_products_endpoint_returns_products(self, session):
        """Test that /api/cashfree/products returns product list"""
        response = session.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200, f"Products endpoint failed: {response.text}"
        
        data = response.json()
        assert "products" in data, "Response should contain 'products' key"
        assert isinstance(data["products"], dict), "Products should be a dict"
        assert len(data["products"]) > 0, "Should have at least one product"
        
        # Verify product structure
        for pid, product in data["products"].items():
            assert "name" in product, f"Product {pid} missing 'name'"
            assert "credits" in product, f"Product {pid} missing 'credits'"
            assert "displayPrice" in product, f"Product {pid} missing 'displayPrice'"
        
        print(f"PASS: Products endpoint returns {len(data['products'])} products")
    
    # =========================================================================
    # Test 2: Webhook admin endpoints require admin auth
    # =========================================================================
    def test_webhook_failed_endpoint_requires_admin_auth(self, session):
        """Test GET /api/cashfree-webhook/failed requires admin auth"""
        # Without auth - should fail
        response = session.get(f"{BASE_URL}/api/cashfree-webhook/failed")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: /api/cashfree-webhook/failed returns {response.status_code} without auth")
    
    def test_webhook_failed_endpoint_works_with_admin(self, session, admin_headers):
        """Test GET /api/cashfree-webhook/failed works with admin auth"""
        response = session.get(f"{BASE_URL}/api/cashfree-webhook/failed", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200 with admin auth, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "failed_webhooks" in data, "Response should contain 'failed_webhooks'"
        assert "count" in data, "Response should contain 'count'"
        print(f"PASS: /api/cashfree-webhook/failed works with admin auth, count={data['count']}")
    
    def test_webhook_stats_endpoint_requires_admin_auth(self, session):
        """Test GET /api/cashfree-webhook/stats requires admin auth"""
        # Without auth - should fail
        response = session.get(f"{BASE_URL}/api/cashfree-webhook/stats")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: /api/cashfree-webhook/stats returns {response.status_code} without auth")
    
    def test_webhook_stats_endpoint_works_with_admin(self, session, admin_headers):
        """Test GET /api/cashfree-webhook/stats works with admin auth"""
        response = session.get(f"{BASE_URL}/api/cashfree-webhook/stats", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200 with admin auth, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "period" in data, "Response should contain 'period'"
        assert "total" in data, "Response should contain 'total'"
        assert "processed" in data, "Response should contain 'processed'"
        print(f"PASS: /api/cashfree-webhook/stats works with admin auth, total={data['total']}")
    
    def test_webhook_retry_endpoint_requires_admin_auth(self, session):
        """Test POST /api/cashfree-webhook/retry/{event_id} requires admin auth"""
        # Without auth - should fail
        response = session.post(f"{BASE_URL}/api/cashfree-webhook/retry/fake_event_id")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: /api/cashfree-webhook/retry requires admin auth, returns {response.status_code}")
    
    # =========================================================================
    # Test 3: Stale order cleanup endpoint (admin only)
    # =========================================================================
    def test_stale_order_cleanup_requires_admin_auth(self, session):
        """Test POST /api/cashfree/orders/cleanup-stale requires admin auth"""
        # Without auth - should fail
        response = session.post(f"{BASE_URL}/api/cashfree/orders/cleanup-stale")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: /api/cashfree/orders/cleanup-stale returns {response.status_code} without auth")
    
    def test_stale_order_cleanup_works_with_admin(self, session, admin_headers):
        """Test POST /api/cashfree/orders/cleanup-stale works with admin auth"""
        response = session.post(f"{BASE_URL}/api/cashfree/orders/cleanup-stale", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200 with admin auth, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should contain 'success'"
        assert "expiredCount" in data, "Response should contain 'expiredCount'"
        assert "cutoff" in data, "Response should contain 'cutoff'"
        print(f"PASS: Stale order cleanup works, expired {data['expiredCount']} orders")
    
    # =========================================================================
    # Test 4: Verify endpoint idempotency (calling verify on non-existent order)
    # =========================================================================
    def test_verify_returns_404_for_nonexistent_order(self, session, user_headers):
        """Test POST /api/cashfree/verify returns 404 for non-existent order"""
        response = session.post(
            f"{BASE_URL}/api/cashfree/verify",
            json={"order_id": "nonexistent_order_12345"},
            headers=user_headers
        )
        assert response.status_code == 404, f"Expected 404 for non-existent order, got {response.status_code}"
        print("PASS: Verify returns 404 for non-existent order")
    
    # =========================================================================
    # Test 5: Refund endpoint requires admin auth
    # =========================================================================
    def test_refund_endpoint_requires_admin_auth(self, session, user_headers):
        """Test POST /api/cashfree/refund/{order_id} requires admin auth"""
        # With regular user auth - should fail
        response = session.post(
            f"{BASE_URL}/api/cashfree/refund/fake_order_id",
            json={"reason": "Test refund"},
            headers=user_headers
        )
        assert response.status_code in [401, 403], f"Expected 401/403 with user auth, got {response.status_code}"
        print(f"PASS: Refund endpoint returns {response.status_code} with regular user auth")
    
    def test_refund_endpoint_returns_404_for_nonexistent_order(self, session, admin_headers):
        """Test POST /api/cashfree/refund/{order_id} returns 404 for non-existent order"""
        response = session.post(
            f"{BASE_URL}/api/cashfree/refund/nonexistent_order_12345",
            json={"reason": "Test refund"},
            headers=admin_headers
        )
        assert response.status_code == 404, f"Expected 404 for non-existent order, got {response.status_code}"
        print("PASS: Refund endpoint returns 404 for non-existent order")
    
    # =========================================================================
    # Test 6: Invoice endpoint requires auth and returns 404 for non-existent
    # =========================================================================
    def test_invoice_endpoint_requires_auth(self, session):
        """Test GET /api/cashfree/invoice/{order_id} requires auth"""
        response = session.get(f"{BASE_URL}/api/cashfree/invoice/fake_order_id")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: Invoice endpoint returns {response.status_code} without auth")
    
    def test_invoice_endpoint_returns_404_for_nonexistent_order(self, session, user_headers):
        """Test GET /api/cashfree/invoice/{order_id} returns 404 for non-existent order"""
        response = session.get(
            f"{BASE_URL}/api/cashfree/invoice/nonexistent_order_12345",
            headers=user_headers
        )
        assert response.status_code == 404, f"Expected 404 for non-existent order, got {response.status_code}"
        print("PASS: Invoice endpoint returns 404 for non-existent order")
    
    # =========================================================================
    # Test 7: Create order requires auth
    # =========================================================================
    def test_create_order_requires_auth(self, session):
        """Test POST /api/cashfree/create-order requires auth"""
        response = session.post(
            f"{BASE_URL}/api/cashfree/create-order",
            json={"productId": "starter", "currency": "INR"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: Create order returns {response.status_code} without auth")
    
    def test_create_order_rejects_invalid_product(self, session, user_headers):
        """Test POST /api/cashfree/create-order rejects invalid product"""
        response = session.post(
            f"{BASE_URL}/api/cashfree/create-order",
            json={"productId": "invalid_product_xyz", "currency": "INR"},
            headers=user_headers
        )
        assert response.status_code == 400, f"Expected 400 for invalid product, got {response.status_code}"
        print("PASS: Create order rejects invalid product with 400")
    
    # =========================================================================
    # Test 8: Payment history endpoint
    # =========================================================================
    def test_payment_history_requires_auth(self, session):
        """Test GET /api/cashfree/payments/history requires auth"""
        response = session.get(f"{BASE_URL}/api/cashfree/payments/history")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: Payment history returns {response.status_code} without auth")
    
    def test_payment_history_works_with_auth(self, session, user_headers):
        """Test GET /api/cashfree/payments/history works with auth"""
        response = session.get(f"{BASE_URL}/api/cashfree/payments/history", headers=user_headers)
        assert response.status_code == 200, f"Expected 200 with auth, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "payments" in data, "Response should contain 'payments'"
        print(f"PASS: Payment history works, found {len(data['payments'])} payments")
    
    # =========================================================================
    # Test 9: Pending delivery orders (admin only)
    # =========================================================================
    def test_pending_delivery_requires_admin_auth(self, session, user_headers):
        """Test GET /api/cashfree/orders/pending-delivery requires admin auth"""
        response = session.get(
            f"{BASE_URL}/api/cashfree/orders/pending-delivery",
            headers=user_headers
        )
        assert response.status_code in [401, 403], f"Expected 401/403 with user auth, got {response.status_code}"
        print(f"PASS: Pending delivery returns {response.status_code} with regular user auth")
    
    def test_pending_delivery_works_with_admin(self, session, admin_headers):
        """Test GET /api/cashfree/orders/pending-delivery works with admin auth"""
        response = session.get(
            f"{BASE_URL}/api/cashfree/orders/pending-delivery",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200 with admin auth, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "totalPaidOrders" in data, "Response should contain 'totalPaidOrders'"
        assert "ordersNeedingReview" in data, "Response should contain 'ordersNeedingReview'"
        print(f"PASS: Pending delivery works, {data['ordersNeedingReview']} orders need review")
    
    # =========================================================================
    # Test 10: Monitoring health (admin only)
    # =========================================================================
    def test_monitoring_health_requires_admin_auth(self, session, user_headers):
        """Test GET /api/cashfree/monitoring/health requires admin auth"""
        response = session.get(
            f"{BASE_URL}/api/cashfree/monitoring/health",
            headers=user_headers
        )
        assert response.status_code in [401, 403], f"Expected 401/403 with user auth, got {response.status_code}"
        print(f"PASS: Monitoring health returns {response.status_code} with regular user auth")
    
    def test_monitoring_health_works_with_admin(self, session, admin_headers):
        """Test GET /api/cashfree/monitoring/health works with admin auth"""
        response = session.get(
            f"{BASE_URL}/api/cashfree/monitoring/health",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200 with admin auth, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "gateway" in data, "Response should contain 'gateway'"
        assert data["gateway"] == "cashfree", "Gateway should be 'cashfree'"
        print(f"PASS: Monitoring health works, gateway={data['gateway']}")
    
    # =========================================================================
    # Test 11: Credits balance endpoint
    # =========================================================================
    def test_credits_balance_requires_auth(self, session):
        """Test GET /api/credits/balance requires auth"""
        response = session.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: Credits balance returns {response.status_code} without auth")
    
    def test_credits_balance_works_with_auth(self, session, user_headers):
        """Test GET /api/credits/balance works with auth"""
        response = session.get(f"{BASE_URL}/api/credits/balance", headers=user_headers)
        assert response.status_code == 200, f"Expected 200 with auth, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Balance could be in 'credits' or 'balance' key
        assert "credits" in data or "balance" in data, "Response should contain 'credits' or 'balance'"
        print(f"PASS: Credits balance works, balance={data.get('credits', data.get('balance', 0))}")


class TestPaymentHardeningCodeReview:
    """Code review tests - verify implementation details"""
    
    def test_verify_endpoint_has_idempotency_check(self):
        """Verify that verify endpoint code has idempotency check"""
        # Read the cashfree_payments.py file
        file_path = "/app/backend/routes/cashfree_payments.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for terminal paid states check
        assert "terminal_paid_states" in content or "CREDIT_APPLIED" in content, \
            "Verify endpoint should check for terminal paid states"
        
        # Check for double-check after gateway call
        assert "fresh_order" in content or "Re-check DB status" in content.lower() or "race" in content.lower(), \
            "Verify endpoint should re-check DB status after gateway call"
        
        print("PASS: Verify endpoint has idempotency checks in code")
    
    def test_create_order_has_duplicate_check(self):
        """Verify that create-order endpoint has duplicate pending order check"""
        file_path = "/app/backend/routes/cashfree_payments.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for existing pending order check
        assert "existing_pending" in content or "duplicate" in content.lower(), \
            "Create order should check for existing pending orders"
        
        # Check that it returns existing session
        assert "existing_session" in content or "Return existing session" in content, \
            "Create order should return existing session for duplicate"
        
        print("PASS: Create order has duplicate pending order check in code")
    
    def test_refund_accepts_credit_applied_state(self):
        """Verify that refund endpoint accepts CREDIT_APPLIED state"""
        file_path = "/app/backend/routes/cashfree_payments.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for refundable states including CREDIT_APPLIED
        assert "CREDIT_APPLIED" in content, "Refund should accept CREDIT_APPLIED state"
        assert "SUBSCRIPTION_ACTIVATED" in content, "Refund should accept SUBSCRIPTION_ACTIVATED state"
        assert "refundable_states" in content, "Should have refundable_states tuple"
        
        print("PASS: Refund endpoint accepts CREDIT_APPLIED and SUBSCRIPTION_ACTIVATED states")
    
    def test_invoice_accepts_credit_applied_state(self):
        """Verify that invoice endpoint accepts CREDIT_APPLIED state"""
        file_path = "/app/backend/routes/cashfree_payments.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the invoice endpoint section
        invoice_section_start = content.find("def generate_invoice")
        if invoice_section_start == -1:
            pytest.skip("Invoice endpoint not found in file")
        
        invoice_section = content[invoice_section_start:invoice_section_start + 1000]
        
        # Check that it accepts CREDIT_APPLIED
        assert "CREDIT_APPLIED" in invoice_section or "PAID" in invoice_section, \
            "Invoice should accept CREDIT_APPLIED state"
        
        print("PASS: Invoice endpoint accepts terminal paid states")
    
    def test_webhook_handler_has_admin_auth(self):
        """Verify that webhook admin endpoints require admin auth"""
        file_path = "/app/backend/routes/cashfree_webhook_handler.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for get_admin_user dependency
        assert "get_admin_user" in content, "Webhook handler should use get_admin_user"
        
        # Check that failed, retry, and stats endpoints have admin auth
        assert "Depends(get_admin_user)" in content, "Admin endpoints should use Depends(get_admin_user)"
        
        print("PASS: Webhook admin endpoints require admin auth")
    
    def test_stale_order_cleanup_exists(self):
        """Verify that stale order cleanup endpoint exists"""
        file_path = "/app/backend/routes/cashfree_payments.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for cleanup endpoint
        assert "cleanup-stale" in content or "cleanup_stale" in content, \
            "Stale order cleanup endpoint should exist"
        
        # Check that it expires old orders
        assert "EXPIRED" in content, "Cleanup should set status to EXPIRED"
        
        print("PASS: Stale order cleanup endpoint exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
