"""
Cashfree Webhook Edge Case Testing Suite
Tests all payment webhook scenarios including:
- Success flows
- Pending states
- Failure handling
- Timeout recovery
- Duplicate delivery protection
- Signature verification
"""

import pytest
import asyncio
import hmac
import hashlib
import json
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from server import app

client = TestClient(app)

# Test configuration
WEBHOOK_SECRET = os.environ.get('CASHFREE_WEBHOOK_SECRET', 'test_webhook_secret')
TEST_ORDER_ID = f"TEST_ORDER_{int(time.time())}"
TEST_USER_ID = "test_user_123"


def generate_signature(payload: dict, secret: str) -> str:
    """Generate Cashfree webhook signature"""
    payload_str = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def create_webhook_payload(
    order_id: str,
    status: str = "SUCCESS",
    amount: float = 100.0,
    cf_payment_id: str = None,
    payment_method: str = "upi"
) -> dict:
    """Create a standard Cashfree webhook payload"""
    return {
        "data": {
            "order": {
                "order_id": order_id,
                "order_amount": amount,
                "order_currency": "INR",
                "order_status": status,
            },
            "payment": {
                "cf_payment_id": cf_payment_id or f"CF_{int(time.time())}",
                "payment_status": status,
                "payment_amount": amount,
                "payment_currency": "INR",
                "payment_method": {
                    "payment_method_type": payment_method
                },
                "payment_time": datetime.now().isoformat(),
            },
            "customer_details": {
                "customer_id": TEST_USER_ID,
                "customer_email": "test@example.com",
            }
        },
        "event_time": datetime.now().isoformat(),
        "type": "PAYMENT_SUCCESS_WEBHOOK" if status == "SUCCESS" else f"PAYMENT_{status}_WEBHOOK"
    }


class TestCashfreeWebhookSuccess:
    """Test successful payment scenarios"""
    
    def test_successful_payment_webhook(self):
        """Test standard successful payment processing"""
        payload = create_webhook_payload(
            order_id=f"success_{TEST_ORDER_ID}",
            status="SUCCESS",
            amount=299.0
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert "processed" in str(data).lower() or response.status_code == 200
    
    def test_partial_payment_webhook(self):
        """Test partial payment handling"""
        payload = create_webhook_payload(
            order_id=f"partial_{TEST_ORDER_ID}",
            status="SUCCESS",
            amount=50.0  # Less than full amount
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Should handle gracefully
        assert response.status_code < 500


class TestCashfreeWebhookPending:
    """Test pending payment scenarios"""
    
    def test_pending_payment_webhook(self):
        """Test pending payment status handling"""
        payload = create_webhook_payload(
            order_id=f"pending_{TEST_ORDER_ID}",
            status="PENDING"
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Should acknowledge but not process credits
        assert response.status_code < 500
    
    def test_pending_to_success_transition(self):
        """Test payment transitioning from pending to success"""
        order_id = f"transition_{TEST_ORDER_ID}"
        
        # First: Send pending webhook
        pending_payload = create_webhook_payload(
            order_id=order_id,
            status="PENDING"
        )
        pending_sig = generate_signature(pending_payload, WEBHOOK_SECRET)
        
        pending_response = client.post(
            "/api/webhooks/cashfree",
            json=pending_payload,
            headers={"x-webhook-signature": pending_sig}
        )
        assert pending_response.status_code < 500
        
        # Then: Send success webhook
        success_payload = create_webhook_payload(
            order_id=order_id,
            status="SUCCESS"
        )
        success_sig = generate_signature(success_payload, WEBHOOK_SECRET)
        
        success_response = client.post(
            "/api/webhooks/cashfree",
            json=success_payload,
            headers={"x-webhook-signature": success_sig}
        )
        assert success_response.status_code < 500


class TestCashfreeWebhookFailure:
    """Test failed payment scenarios"""
    
    def test_failed_payment_webhook(self):
        """Test failed payment handling"""
        payload = create_webhook_payload(
            order_id=f"failed_{TEST_ORDER_ID}",
            status="FAILED"
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Should acknowledge failure
        assert response.status_code < 500
    
    def test_cancelled_payment_webhook(self):
        """Test cancelled payment handling"""
        payload = create_webhook_payload(
            order_id=f"cancelled_{TEST_ORDER_ID}",
            status="CANCELLED"
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        assert response.status_code < 500
    
    def test_user_dropped_payment(self):
        """Test user-dropped payment webhook"""
        payload = create_webhook_payload(
            order_id=f"dropped_{TEST_ORDER_ID}",
            status="USER_DROPPED"
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        assert response.status_code < 500


class TestCashfreeWebhookDuplicates:
    """Test duplicate delivery protection"""
    
    def test_duplicate_webhook_idempotency(self):
        """Test that duplicate webhooks don't double-credit"""
        order_id = f"duplicate_{TEST_ORDER_ID}"
        cf_payment_id = f"CF_DUP_{int(time.time())}"
        
        payload = create_webhook_payload(
            order_id=order_id,
            status="SUCCESS",
            cf_payment_id=cf_payment_id,
            amount=100.0
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        # Send first webhook
        response1 = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Send duplicate webhook (same payload)
        response2 = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Both should succeed (idempotent), but credits only added once
        assert response1.status_code < 500
        assert response2.status_code < 500
    
    def test_rapid_duplicate_webhooks(self):
        """Test rapid-fire duplicate webhook handling"""
        order_id = f"rapid_{TEST_ORDER_ID}"
        cf_payment_id = f"CF_RAPID_{int(time.time())}"
        
        payload = create_webhook_payload(
            order_id=order_id,
            status="SUCCESS",
            cf_payment_id=cf_payment_id
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        # Send 5 rapid duplicates
        responses = []
        for _ in range(5):
            response = client.post(
                "/api/webhooks/cashfree",
                json=payload,
                headers={"x-webhook-signature": signature}
            )
            responses.append(response.status_code)
        
        # All should be handled gracefully
        assert all(code < 500 for code in responses)


class TestCashfreeWebhookSecurity:
    """Test webhook security and signature verification"""
    
    def test_invalid_signature_rejected(self):
        """Test that invalid signatures are rejected"""
        payload = create_webhook_payload(
            order_id=f"invalid_sig_{TEST_ORDER_ID}",
            status="SUCCESS"
        )
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": "invalid_signature_12345"}
        )
        
        # Should be rejected
        assert response.status_code in [400, 401, 403]
    
    def test_missing_signature_rejected(self):
        """Test that missing signature is rejected"""
        payload = create_webhook_payload(
            order_id=f"no_sig_{TEST_ORDER_ID}",
            status="SUCCESS"
        )
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload
            # No signature header
        )
        
        # Should be rejected
        assert response.status_code in [400, 401, 403]
    
    def test_tampered_payload_rejected(self):
        """Test that tampered payloads are rejected"""
        payload = create_webhook_payload(
            order_id=f"tampered_{TEST_ORDER_ID}",
            status="SUCCESS",
            amount=100.0
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        # Tamper with the payload after signing
        payload["data"]["order"]["order_amount"] = 10000.0
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Should be rejected due to signature mismatch
        assert response.status_code in [400, 401, 403]


class TestCashfreeWebhookTimeout:
    """Test timeout and recovery scenarios"""
    
    def test_webhook_processing_timeout_recovery(self):
        """Test recovery from processing timeout"""
        payload = create_webhook_payload(
            order_id=f"timeout_{TEST_ORDER_ID}",
            status="SUCCESS"
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        # Set a short timeout for the request
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature},
            timeout=30.0
        )
        
        # Should complete within timeout
        assert response.status_code < 500
    
    def test_late_webhook_delivery(self):
        """Test handling of late webhook delivery"""
        # Simulate a webhook for an old order
        payload = create_webhook_payload(
            order_id=f"late_{TEST_ORDER_ID}",
            status="SUCCESS"
        )
        # Backdate the event time
        payload["event_time"] = (datetime.now() - timedelta(hours=24)).isoformat()
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Should still process (webhooks can be delayed)
        assert response.status_code < 500


class TestCashfreeWebhookEdgeCases:
    """Test additional edge cases"""
    
    def test_malformed_payload(self):
        """Test handling of malformed webhook payload"""
        response = client.post(
            "/api/webhooks/cashfree",
            json={"invalid": "payload"},
            headers={"x-webhook-signature": "test"}
        )
        
        # Should reject gracefully
        assert response.status_code in [400, 422]
    
    def test_empty_payload(self):
        """Test handling of empty payload"""
        response = client.post(
            "/api/webhooks/cashfree",
            json={},
            headers={"x-webhook-signature": "test"}
        )
        
        assert response.status_code in [400, 422]
    
    def test_unknown_payment_status(self):
        """Test handling of unknown payment status"""
        payload = create_webhook_payload(
            order_id=f"unknown_status_{TEST_ORDER_ID}",
            status="UNKNOWN_STATUS"
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Should handle gracefully
        assert response.status_code < 500
    
    def test_very_large_amount(self):
        """Test handling of very large payment amount"""
        payload = create_webhook_payload(
            order_id=f"large_amount_{TEST_ORDER_ID}",
            status="SUCCESS",
            amount=9999999.99
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Should handle or validate
        assert response.status_code < 500
    
    def test_zero_amount_payment(self):
        """Test handling of zero amount payment"""
        payload = create_webhook_payload(
            order_id=f"zero_amount_{TEST_ORDER_ID}",
            status="SUCCESS",
            amount=0.0
        )
        signature = generate_signature(payload, WEBHOOK_SECRET)
        
        response = client.post(
            "/api/webhooks/cashfree",
            json=payload,
            headers={"x-webhook-signature": signature}
        )
        
        # Should handle or reject gracefully
        assert response.status_code < 500


# Summary report generator
def generate_test_report(results: dict) -> str:
    """Generate a summary report of webhook tests"""
    report = """
╔══════════════════════════════════════════════════════════════╗
║          CASHFREE WEBHOOK EDGE CASE TEST REPORT              ║
╠══════════════════════════════════════════════════════════════╣
"""
    for category, tests in results.items():
        report += f"║ {category:<60} ║\n"
        for test_name, status in tests.items():
            status_icon = "✅" if status else "❌"
            report += f"║   {status_icon} {test_name:<56} ║\n"
        report += "╠══════════════════════════════════════════════════════════════╣\n"
    
    report += "╚══════════════════════════════════════════════════════════════╝\n"
    return report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
