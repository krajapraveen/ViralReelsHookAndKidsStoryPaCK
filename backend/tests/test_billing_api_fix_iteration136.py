"""
Iteration 136 - Billing Page API Fix Verification
Tests the fix for paymentAPI endpoints changed from /api/payments/* to /api/cashfree/*
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCashfreeProductsEndpoint:
    """Test /api/cashfree/products endpoint - the correct endpoint for billing page"""
    
    def test_cashfree_products_returns_200(self):
        """Verify /api/cashfree/products returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("SUCCESS: /api/cashfree/products returns 200")
    
    def test_cashfree_products_returns_7_products(self):
        """Verify endpoint returns all 7 products (4 subscriptions + 3 credit packs)"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        data = response.json()
        
        products = data.get("products", {})
        assert len(products) == 7, f"Expected 7 products, got {len(products)}"
        print(f"SUCCESS: Found {len(products)} products")
    
    def test_cashfree_products_has_subscriptions(self):
        """Verify all 4 subscription plans exist"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        data = response.json()
        products = data.get("products", {})
        
        expected_subscriptions = ["weekly", "monthly", "quarterly", "yearly"]
        for sub in expected_subscriptions:
            assert sub in products, f"Missing subscription: {sub}"
            assert "period" in products[sub], f"{sub} should have period field"
            assert "savings" in products[sub], f"{sub} should have savings field"
        print(f"SUCCESS: All 4 subscriptions found: {expected_subscriptions}")
    
    def test_cashfree_products_has_credit_packs(self):
        """Verify all 3 credit packs exist"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        data = response.json()
        products = data.get("products", {})
        
        expected_packs = ["starter", "creator", "pro"]
        for pack in expected_packs:
            assert pack in products, f"Missing credit pack: {pack}"
            assert "period" not in products[pack], f"{pack} should NOT have period field"
        print(f"SUCCESS: All 3 credit packs found: {expected_packs}")
    
    def test_cashfree_products_price_structure(self):
        """Verify each product has required fields: name, credits, price"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        data = response.json()
        products = data.get("products", {})
        
        required_fields = ["name", "credits", "price"]
        for product_id, product in products.items():
            for field in required_fields:
                assert field in product, f"{product_id} missing field: {field}"
                
        print("SUCCESS: All products have required fields (name, credits, price)")
    
    def test_cashfree_products_gateway_info(self):
        """Verify response includes gateway info"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        data = response.json()
        
        assert "gateway" in data, "Response should include gateway field"
        assert data["gateway"] == "cashfree", f"Gateway should be 'cashfree', got {data['gateway']}"
        assert "configured" in data, "Response should include configured field"
        print(f"SUCCESS: Gateway info present - gateway: {data['gateway']}, configured: {data['configured']}")


class TestOldPaymentsEndpointDoesNotExist:
    """Verify the old /api/payments/* endpoints don't exist (were never created)"""
    
    def test_old_payments_products_returns_404(self):
        """Verify /api/payments/products returns 404 (endpoint doesn't exist)"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        # Should return 404 since this endpoint never existed
        assert response.status_code == 404, f"Old endpoint should return 404, got {response.status_code}"
        print("SUCCESS: /api/payments/products correctly returns 404 (doesn't exist)")


class TestCashfreeHealthEndpoint:
    """Test /api/cashfree/health endpoint"""
    
    def test_cashfree_health_returns_200(self):
        """Verify health check returns 200"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("SUCCESS: /api/cashfree/health returns 200")
    
    def test_cashfree_health_configured(self):
        """Verify cashfree is configured"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        data = response.json()
        
        assert data.get("status") == "healthy", f"Expected healthy status, got {data.get('status')}"
        assert data.get("configured") == True, "Cashfree should be configured"
        print(f"SUCCESS: Cashfree health - status: {data.get('status')}, configured: {data.get('configured')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
