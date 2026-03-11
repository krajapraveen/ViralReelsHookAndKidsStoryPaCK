"""
Test Suite for Cashfree Subscription Payment Fix - Iteration 139
Tests the P0 fix for Cashfree payment gateway not opening on Subscription page.

The fix replaced Cashfree Subscriptions API (raw HTTP calls returning 500)
with PGCreateOrder via Cashfree PG SDK (same working approach as Billing page).

Test Coverage:
1. POST /api/subscriptions/recurring/create - creator, pro, studio plans
2. POST /api/subscriptions/recurring/change-plan
3. POST /api/subscriptions/recurring/verify
4. POST /api/cashfree/create-order (existing credit purchase)
5. GET /api/subscriptions/recurring/plans
6. GET /api/subscriptions/recurring/current
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed - status {response.status_code}: {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestSubscriptionPlansEndpoint:
    """Test GET /api/subscriptions/recurring/plans - should return 3 plans"""
    
    def test_get_recurring_plans_returns_success(self, api_client):
        """Test that plans endpoint returns success=true"""
        response = api_client.get(f"{BASE_URL}/api/subscriptions/recurring/plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=true, got {data}"
        print(f"PASS: GET /api/subscriptions/recurring/plans returns success=true")
    
    def test_get_recurring_plans_returns_three_plans(self, api_client):
        """Test that plans endpoint returns exactly 3 plans: creator, pro, studio"""
        response = api_client.get(f"{BASE_URL}/api/subscriptions/recurring/plans")
        assert response.status_code == 200
        data = response.json()
        plans = data.get("plans", [])
        assert len(plans) == 3, f"Expected 3 plans, got {len(plans)}: {plans}"
        print(f"PASS: Returns 3 plans")
    
    def test_plans_have_required_fields(self, api_client):
        """Test that each plan has required fields"""
        response = api_client.get(f"{BASE_URL}/api/subscriptions/recurring/plans")
        data = response.json()
        plans = data.get("plans", [])
        
        plan_keys = [p.get("key") for p in plans]
        assert "creator" in plan_keys, "Missing creator plan"
        assert "pro" in plan_keys, "Missing pro plan"
        assert "studio" in plan_keys, "Missing studio plan"
        
        for plan in plans:
            assert "name" in plan, f"Plan missing name: {plan}"
            assert "price_inr" in plan, f"Plan missing price_inr: {plan}"
            assert "features" in plan, f"Plan missing features: {plan}"
            assert "credits_per_cycle" in plan, f"Plan missing credits_per_cycle: {plan}"
        
        print(f"PASS: All plans have required fields: {plan_keys}")


class TestCurrentSubscriptionEndpoint:
    """Test GET /api/subscriptions/recurring/current"""
    
    def test_get_current_subscription_requires_auth(self, api_client):
        """Test that endpoint requires authentication"""
        # Remove auth header temporarily
        client = requests.Session()
        client.headers.update({"Content-Type": "application/json"})
        response = client.get(f"{BASE_URL}/api/subscriptions/recurring/current")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"PASS: GET /api/subscriptions/recurring/current requires auth")
    
    def test_get_current_subscription_returns_plan_info(self, authenticated_client):
        """Test that endpoint returns current plan info"""
        response = authenticated_client.get(f"{BASE_URL}/api/subscriptions/recurring/current")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=true, got {data}"
        assert "current_plan" in data, f"Missing current_plan: {data}"
        print(f"PASS: Current plan info returned: {data.get('current_plan')}")


class TestCreateRecurringSubscription:
    """
    Test POST /api/subscriptions/recurring/create
    This is the KEY endpoint that was fixed - should return paymentSessionId
    """
    
    def test_create_subscription_requires_auth(self, api_client):
        """Test that endpoint requires authentication"""
        client = requests.Session()
        client.headers.update({"Content-Type": "application/json"})
        response = client.post(f"{BASE_URL}/api/subscriptions/recurring/create", json={
            "plan_key": "creator"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"PASS: POST /api/subscriptions/recurring/create requires auth")
    
    def test_create_subscription_invalid_plan_returns_400(self, authenticated_client):
        """Test that invalid plan_key returns 400"""
        response = authenticated_client.post(f"{BASE_URL}/api/subscriptions/recurring/create", json={
            "plan_key": "invalid_plan"
        })
        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print(f"PASS: Invalid plan returns 400/422")
    
    def test_create_creator_subscription_returns_payment_session(self, authenticated_client):
        """
        CRITICAL TEST: creator plan should return success=true and paymentSessionId
        This is the P0 fix verification - previously returned 500 error
        """
        response = authenticated_client.post(f"{BASE_URL}/api/subscriptions/recurring/create", json={
            "plan_key": "creator"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # KEY assertions - the fix should ensure these pass
        assert data.get("success") == True, f"Expected success=true, got {data}"
        assert "paymentSessionId" in data, f"Missing paymentSessionId - this is the P0 fix: {data}"
        assert "orderId" in data, f"Missing orderId: {data}"
        
        # Additional assertions
        assert data.get("paymentSessionId") is not None, "paymentSessionId is None"
        assert len(data.get("paymentSessionId", "")) > 0, "paymentSessionId is empty"
        
        print(f"PASS: Creator subscription returns paymentSessionId: {data.get('paymentSessionId')[:20]}...")
        print(f"      orderId: {data.get('orderId')}")
        print(f"      environment: {data.get('environment')}")
    
    def test_create_pro_subscription_returns_payment_session(self, authenticated_client):
        """
        CRITICAL TEST: pro plan should return success=true and paymentSessionId
        """
        response = authenticated_client.post(f"{BASE_URL}/api/subscriptions/recurring/create", json={
            "plan_key": "pro"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Expected success=true, got {data}"
        assert "paymentSessionId" in data, f"Missing paymentSessionId: {data}"
        assert "orderId" in data, f"Missing orderId: {data}"
        
        print(f"PASS: Pro subscription returns paymentSessionId: {data.get('paymentSessionId')[:20]}...")
    
    def test_create_studio_subscription_returns_payment_session(self, authenticated_client):
        """
        CRITICAL TEST: studio plan should return success=true and paymentSessionId
        """
        response = authenticated_client.post(f"{BASE_URL}/api/subscriptions/recurring/create", json={
            "plan_key": "studio"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Expected success=true, got {data}"
        assert "paymentSessionId" in data, f"Missing paymentSessionId: {data}"
        assert "orderId" in data, f"Missing orderId: {data}"
        
        print(f"PASS: Studio subscription returns paymentSessionId: {data.get('paymentSessionId')[:20]}...")


class TestChangePlanEndpoint:
    """Test POST /api/subscriptions/recurring/change-plan"""
    
    def test_change_plan_requires_auth(self, api_client):
        """Test that endpoint requires authentication"""
        client = requests.Session()
        client.headers.update({"Content-Type": "application/json"})
        response = client.post(f"{BASE_URL}/api/subscriptions/recurring/change-plan?new_plan_key=pro")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"PASS: POST /api/subscriptions/recurring/change-plan requires auth")
    
    def test_change_plan_invalid_plan_returns_400(self, authenticated_client):
        """Test that invalid plan returns 400"""
        response = authenticated_client.post(f"{BASE_URL}/api/subscriptions/recurring/change-plan?new_plan_key=invalid")
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print(f"PASS: Invalid plan change returns 400/422")
    
    def test_change_plan_to_pro_returns_payment_session(self, authenticated_client):
        """
        Test plan change to pro - should return paymentSessionId like create
        """
        response = authenticated_client.post(f"{BASE_URL}/api/subscriptions/recurring/change-plan?new_plan_key=pro")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Expected success=true, got {data}"
        assert "paymentSessionId" in data, f"Missing paymentSessionId: {data}"
        
        print(f"PASS: Change plan returns paymentSessionId: {data.get('paymentSessionId')[:20] if data.get('paymentSessionId') else 'N/A'}...")


class TestVerifySubscriptionPayment:
    """Test POST /api/subscriptions/recurring/verify"""
    
    def test_verify_requires_auth(self, api_client):
        """Test that endpoint requires authentication"""
        client = requests.Session()
        client.headers.update({"Content-Type": "application/json"})
        response = client.post(f"{BASE_URL}/api/subscriptions/recurring/verify", json={
            "order_id": "test_order"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"PASS: POST /api/subscriptions/recurring/verify requires auth")
    
    def test_verify_invalid_order_returns_404(self, authenticated_client):
        """Test that invalid order_id returns 404"""
        response = authenticated_client.post(f"{BASE_URL}/api/subscriptions/recurring/verify", json={
            "order_id": "nonexistent_order_12345"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"PASS: Invalid order_id returns 404")
    
    def test_verify_requires_order_id(self, authenticated_client):
        """Test that missing order_id returns 400"""
        response = authenticated_client.post(f"{BASE_URL}/api/subscriptions/recurring/verify", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"PASS: Missing order_id returns 400")


class TestExistingCashfreeOrderEndpoint:
    """
    Test POST /api/cashfree/create-order - existing credit purchase
    This endpoint should continue to work after the subscription fix
    """
    
    def test_create_order_requires_auth(self, api_client):
        """Test that endpoint requires authentication"""
        client = requests.Session()
        client.headers.update({"Content-Type": "application/json"})
        response = client.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "starter",
            "currency": "INR"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"PASS: POST /api/cashfree/create-order requires auth")
    
    def test_create_order_starter_pack(self, authenticated_client):
        """Test creating order for starter credit pack"""
        response = authenticated_client.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "starter",
            "currency": "INR"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Expected success=true, got {data}"
        assert "paymentSessionId" in data, f"Missing paymentSessionId: {data}"
        assert "orderId" in data, f"Missing orderId: {data}"
        
        print(f"PASS: Starter pack order created: {data.get('orderId')}")
    
    def test_create_order_creator_pack(self, authenticated_client):
        """Test creating order for creator credit pack"""
        response = authenticated_client.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "creator",
            "currency": "INR"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Expected success=true, got {data}"
        assert "paymentSessionId" in data, f"Missing paymentSessionId: {data}"
        
        print(f"PASS: Creator pack order created: {data.get('orderId')}")
    
    def test_create_order_invalid_product_returns_400(self, authenticated_client):
        """Test that invalid productId returns 400"""
        response = authenticated_client.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "invalid_product",
            "currency": "INR"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"PASS: Invalid product returns 400")


class TestCashfreeHealth:
    """Test Cashfree health endpoint"""
    
    def test_cashfree_health(self, api_client):
        """Test that Cashfree is configured and healthy"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("status") == "healthy", f"Expected healthy status: {data}"
        assert data.get("configured") == True, f"Expected configured=true: {data}"
        
        print(f"PASS: Cashfree health check - status: {data.get('status')}, env: {data.get('environment')}")


class TestCashfreeProducts:
    """Test Cashfree products endpoint"""
    
    def test_get_products(self, api_client):
        """Test getting products list"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "products" in data, f"Missing products: {data}"
        products = data.get("products", {})
        assert len(products) > 0, f"No products returned: {data}"
        
        print(f"PASS: Products endpoint returns {len(products)} products")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
