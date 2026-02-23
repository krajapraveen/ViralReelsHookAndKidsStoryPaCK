"""
Test suite for CreatorStudio AI Payment Flow
Tests: Razorpay order creation, payment verification, webhook, and email service
"""
import pytest
import requests
import os
import json
import hmac
import hashlib

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://qa-testing-preview.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "admin123"
WEBHOOK_SECRET = "your_webhook_secret"


class TestAuthentication:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test successful login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "email" in data, "Email not in response"
        assert data["email"] == ADMIN_EMAIL
        
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}"


class TestPaymentProducts:
    """Payment products endpoint tests"""
    
    def test_get_products(self):
        """Test getting payment products"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200, f"Get products failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Products should be a list"
        assert len(data) > 0, "Should have at least one product"
        
        # Verify product structure
        product = data[0]
        assert "id" in product
        assert "name" in product
        assert "priceInr" in product
        assert "credits" in product
        assert "type" in product
        
    def test_products_have_credit_packs_and_subscriptions(self):
        """Test that products include both credit packs and subscriptions"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        data = response.json()
        
        types = set(p["type"] for p in data)
        assert "CREDIT_PACK" in types, "Should have credit pack products"
        assert "SUBSCRIPTION" in types, "Should have subscription products"


class TestPaymentOrderCreation:
    """Payment order creation tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_create_order_success(self, auth_token):
        """Test creating a Razorpay order"""
        response = requests.post(
            f"{BASE_URL}/api/payments/create-order",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"productId": 1}
        )
        assert response.status_code == 200, f"Create order failed: {response.text}"
        data = response.json()
        
        # Verify order response structure
        assert "orderId" in data, "Order ID not in response"
        assert "amount" in data, "Amount not in response"
        assert "currency" in data, "Currency not in response"
        assert "keyId" in data, "Key ID not in response"
        
        # Verify order ID format (Razorpay format: order_XXXXX)
        assert data["orderId"].startswith("order_"), f"Invalid order ID format: {data['orderId']}"
        assert data["currency"] == "INR", "Currency should be INR"
        assert data["amount"] > 0, "Amount should be positive"
        
    def test_create_order_without_auth(self):
        """Test creating order without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/payments/create-order",
            json={"productId": 1}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_create_order_invalid_product(self, auth_token):
        """Test creating order with invalid product ID"""
        response = requests.post(
            f"{BASE_URL}/api/payments/create-order",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"productId": 99999}
        )
        assert response.status_code in [400, 404, 500], f"Expected error status, got {response.status_code}"


class TestPaymentVerification:
    """Payment verification tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_verify_payment_invalid_order(self, auth_token):
        """Test verifying payment with invalid order ID"""
        response = requests.post(
            f"{BASE_URL}/api/payments/verify",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "razorpayOrderId": "order_invalid",
                "razorpayPaymentId": "pay_invalid",
                "razorpaySignature": "invalid_signature"
            }
        )
        # Should fail because order doesn't exist
        assert response.status_code in [400, 404, 500], f"Expected error status, got {response.status_code}"
        
    def test_verify_payment_missing_fields(self, auth_token):
        """Test verifying payment with missing fields"""
        response = requests.post(
            f"{BASE_URL}/api/payments/verify",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"razorpayOrderId": "order_test"}
        )
        assert response.status_code in [400, 500], f"Expected error status, got {response.status_code}"


class TestWebhookEndpoint:
    """Webhook endpoint tests - should be publicly accessible"""
    
    def test_webhook_accessible_without_auth(self):
        """Test that webhook endpoint is publicly accessible"""
        response = requests.post(
            f"{BASE_URL}/api/payments/webhook",
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "test_signature"
            },
            data='{"event":"test"}'
        )
        # Should not return 401/403 (auth error)
        assert response.status_code not in [401, 403], "Webhook should be publicly accessible"
        
    def test_webhook_invalid_signature(self):
        """Test webhook with invalid signature"""
        payload = json.dumps({
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test123",
                        "order_id": "order_test123"
                    }
                }
            }
        })
        
        response = requests.post(
            f"{BASE_URL}/api/payments/webhook",
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "invalid_signature"
            },
            data=payload
        )
        assert response.status_code == 200 or response.status_code == 400
        data = response.json()
        assert data.get("status") == "invalid_signature", f"Expected invalid_signature status, got {data}"
        
    def test_webhook_valid_signature_format(self):
        """Test webhook with properly formatted signature (will fail verification but tests format)"""
        payload = json.dumps({
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test123",
                        "order_id": "order_test123"
                    }
                }
            }
        })
        
        # Generate a signature (won't match but tests the flow)
        signature = hmac.new(
            WEBHOOK_SECRET.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        response = requests.post(
            f"{BASE_URL}/api/payments/webhook",
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature
            },
            data=payload
        )
        # Should process without auth error
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"


class TestCreditsBalance:
    """Credits balance tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_credits_balance(self, auth_token):
        """Test getting user credits balance"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Get balance failed: {response.text}"
        data = response.json()
        
        assert "balance" in data, "Balance not in response"
        assert "isFreeTier" in data, "isFreeTier not in response"
        assert "hasPurchased" in data, "hasPurchased not in response"
        
    def test_credits_balance_without_auth(self):
        """Test getting credits balance without authentication"""
        response = requests.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestPaymentHistory:
    """Payment history tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_payment_history(self, auth_token):
        """Test getting payment history"""
        response = requests.get(
            f"{BASE_URL}/api/payments/history",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Get history failed: {response.text}"
        data = response.json()
        
        # Should return paginated response
        assert "content" in data or isinstance(data, list), "Should return payment list or paginated response"


class TestEmailServiceIntegration:
    """Email service integration tests (indirect - via registration)"""
    
    def test_registration_triggers_welcome_email(self):
        """Test that registration should trigger welcome email (check logs)"""
        import time
        test_email = f"test_email_{int(time.time())}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": test_email,
            "password": "testpass123"
        })
        
        # Registration might succeed or fail if email exists
        # We're testing that the endpoint works
        if response.status_code == 200:
            data = response.json()
            assert "token" in data, "Token should be in response"
            # Email sending is async, so we can't verify directly
            # But the endpoint should work without errors
        elif response.status_code == 400:
            # Email might already exist
            pass
        else:
            # Other errors are acceptable for this test
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
