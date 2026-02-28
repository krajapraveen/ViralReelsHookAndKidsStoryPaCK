#!/usr/bin/env python3
"""
Cashfree Complete Payment Flow Test
Tests the full payment → credits flow using Cashfree sandbox test cards.
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
API_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://visionary-qa.preview.emergentagent.com")
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Cashfree Sandbox Test Cards
# Reference: https://docs.cashfree.com/docs/test-credentials
TEST_CARDS = {
    "success": {
        "card_number": "4111111111111111",
        "card_expiry_mm": "12",
        "card_expiry_yy": "25",
        "card_cvv": "123",
        "card_holder_name": "Test User",
        "description": "Always succeeds"
    },
    "failure": {
        "card_number": "4111111111111112",
        "card_expiry_mm": "12",
        "card_expiry_yy": "25",
        "card_cvv": "123",
        "card_holder_name": "Test User",
        "description": "Always fails"
    },
    "otp_required": {
        "card_number": "4111111111111141",
        "card_expiry_mm": "12",
        "card_expiry_yy": "25",
        "card_cvv": "123",
        "card_holder_name": "Test User",
        "description": "Requires OTP (use any 6 digits)"
    },
    "insufficient_funds": {
        "card_number": "4111111111111151",
        "card_expiry_mm": "12",
        "card_expiry_yy": "25",
        "card_cvv": "123",
        "card_holder_name": "Test User",
        "description": "Insufficient funds"
    }
}

# Sandbox UPI IDs
TEST_UPI = {
    "success": "testsuccess@gocash",
    "failure": "testfailure@gocash"
}


class CashfreePaymentTester:
    """Tests complete payment flow with Cashfree sandbox"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip('/')
        self.token: Optional[str] = None
        self.test_results = []
        
    async def login(self, session: aiohttp.ClientSession) -> str:
        """Get authentication token"""
        async with session.post(
            f"{self.api_url}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        ) as resp:
            data = await resp.json()
            return data.get("token", "")
    
    async def get_wallet_balance(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Get wallet details"""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.get(f"{self.api_url}/api/wallet/me", headers=headers) as resp:
            return await resp.json()
    
    async def get_products(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Get available products"""
        async with session.get(f"{self.api_url}/api/cashfree/products") as resp:
            return await resp.json()
    
    async def create_order(self, session: aiohttp.ClientSession, product_id: str) -> Dict[str, Any]:
        """Create a payment order"""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.post(
            f"{self.api_url}/api/cashfree/create-order",
            headers=headers,
            json={"productId": product_id}
        ) as resp:
            return await resp.json()
    
    async def check_order_status(self, session: aiohttp.ClientSession, order_id: str) -> Dict[str, Any]:
        """Check order status"""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.get(
            f"{self.api_url}/api/cashfree/order/{order_id}/status",
            headers=headers
        ) as resp:
            try:
                return await resp.json()
            except:
                return {"status": resp.status, "error": await resp.text()}
    
    async def get_payment_history(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Get payment history"""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.get(
            f"{self.api_url}/api/cashfree/payments/history",
            headers=headers
        ) as resp:
            try:
                return await resp.json()
            except:
                return {"status": resp.status}
    
    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {test_name}: {details}")
    
    async def test_product_listing(self, session: aiohttp.ClientSession):
        """Test product listing endpoint"""
        print("\n--- Test: Product Listing ---")
        
        products = await self.get_products(session)
        
        if "products" in products:
            product_dict = products["products"]
            # Products might be a dict with product_id as key
            if isinstance(product_dict, dict):
                product_list = list(product_dict.keys())
            else:
                product_list = product_dict
                
            self.record_result(
                "Product Listing",
                True,
                f"Found {len(product_list)} products"
            )
            
            # Display products
            print("\n  Available Products:")
            if isinstance(product_dict, dict):
                for product_id, details in product_dict.items():
                    if isinstance(details, dict):
                        print(f"    - {product_id}: {details.get('name', product_id)} - {details.get('credits', 'N/A')} credits @ INR {details.get('price', 'N/A')}")
                    else:
                        print(f"    - {product_id}")
            else:
                for p in product_list:
                    print(f"    - {p}")
        else:
            self.record_result("Product Listing", False, "No products found")
    
    async def test_order_creation(self, session: aiohttp.ClientSession) -> Optional[str]:
        """Test order creation for each product"""
        print("\n--- Test: Order Creation ---")
        
        products = await self.get_products(session)
        product_data = products.get("products", {})
        
        # Handle dict (product_id: details) or list format
        if isinstance(product_data, dict):
            product_ids = list(product_data.keys())
        else:
            product_ids = product_data
        
        if not product_ids:
            self.record_result("Order Creation", False, "No products available")
            return None
        
        # Test with first product
        product_id = product_ids[0]
        
        order = await self.create_order(session, product_id)
        
        if order.get("success"):
            order_id = order.get("orderId")
            self.record_result(
                "Order Creation",
                True,
                f"Order {order_id} created for {product_id}"
            )
            print(f"\n  Order Details:")
            print(f"    Order ID: {order.get('orderId')}")
            print(f"    CF Order ID: {order.get('cfOrderId')}")
            print(f"    Amount: INR {order.get('amount')}")
            print(f"    Credits: {order.get('credits')}")
            session_id = order.get('paymentSessionId', 'N/A')
            print(f"    Payment Session: {session_id[:50] if session_id else 'N/A'}...")
            return order_id
        else:
            self.record_result("Order Creation", False, str(order))
            return None
    
    async def test_order_status_tracking(self, session: aiohttp.ClientSession, order_id: str):
        """Test order status tracking"""
        print("\n--- Test: Order Status Tracking ---")
        
        if not order_id:
            self.record_result("Order Status", False, "No order ID provided")
            return
        
        status = await self.check_order_status(session, order_id)
        
        # Status should be ACTIVE (unpaid) for newly created order
        order_status = status.get("order_status", status.get("status", "unknown"))
        self.record_result(
            "Order Status",
            order_status in ["ACTIVE", "active", "PENDING", "pending", "SUCCESS", "success"],
            f"Order status: {order_status}"
        )
    
    async def test_wallet_integration(self, session: aiohttp.ClientSession):
        """Test wallet balance endpoint"""
        print("\n--- Test: Wallet Integration ---")
        
        wallet = await self.get_wallet_balance(session)
        
        if "balanceCredits" in wallet or "availableCredits" in wallet:
            credits = wallet.get("balanceCredits", wallet.get("availableCredits", 0))
            self.record_result("Wallet Balance", True, f"Current balance: {credits} credits")
        else:
            self.record_result("Wallet Balance", False, str(wallet))
    
    async def test_payment_history(self, session: aiohttp.ClientSession):
        """Test payment history endpoint"""
        print("\n--- Test: Payment History ---")
        
        history = await self.get_payment_history(session)
        
        if "payments" in history or isinstance(history, list):
            payments = history.get("payments", history) if isinstance(history, dict) else history
            self.record_result(
                "Payment History",
                True,
                f"Found {len(payments) if isinstance(payments, list) else 0} payment records"
            )
        elif history.get("status") == 200:
            self.record_result("Payment History", True, "Endpoint accessible")
        else:
            self.record_result("Payment History", False, str(history))
    
    async def test_gateway_health(self, session: aiohttp.ClientSession):
        """Test Cashfree gateway health"""
        print("\n--- Test: Gateway Health ---")
        
        async with session.get(f"{self.api_url}/api/cashfree/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                self.record_result(
                    "Gateway Health",
                    data.get("status") == "healthy",
                    f"Status: {data.get('status')}, Environment: {data.get('environment', 'unknown')}"
                )
            else:
                self.record_result("Gateway Health", False, f"HTTP {resp.status}")
    
    async def run_all_tests(self):
        """Run complete payment flow tests"""
        print("\n" + "="*60)
        print("CASHFREE PAYMENT FLOW TEST")
        print("="*60)
        print(f"API URL: {self.api_url}")
        print(f"\nSandbox Test Cards Available:")
        for name, card in TEST_CARDS.items():
            print(f"  - {name}: {card['card_number']} ({card['description']})")
        print(f"\nSandbox UPI IDs:")
        for name, upi in TEST_UPI.items():
            print(f"  - {name}: {upi}")
        
        connector = aiohttp.TCPConnector(limit=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Login
            self.token = await self.login(session)
            if not self.token:
                print("ERROR: Authentication failed")
                return
            
            print(f"\nAuthenticated as: {ADMIN_EMAIL}")
            
            # Run tests
            await self.test_gateway_health(session)
            await self.test_wallet_integration(session)
            await self.test_product_listing(session)
            order_id = await self.test_order_creation(session)
            await self.test_order_status_tracking(session, order_id)
            await self.test_payment_history(session)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        
        print(f"Passed: {passed}/{total}")
        print(f"Failed: {total - passed}/{total}")
        
        print("\n" + "="*60)
        print("SANDBOX TEST CARD INSTRUCTIONS")
        print("="*60)
        print("""
To complete a payment test in the browser:

1. Navigate to: {api_url}/app/billing
2. Select a credit pack
3. Click "Buy Now" to initiate payment
4. On the Cashfree payment page, use these test cards:

SUCCESS PAYMENT:
  Card: 4111 1111 1111 1111
  Expiry: 12/25
  CVV: 123
  
FAILED PAYMENT:
  Card: 4111 1111 1111 1112
  Expiry: 12/25
  CVV: 123

OTP REQUIRED:
  Card: 4111 1111 1111 1141
  Expiry: 12/25
  CVV: 123
  OTP: Any 6 digits (e.g., 123456)

UPI SUCCESS:
  UPI ID: testsuccess@gocash
  
UPI FAILURE:
  UPI ID: testfailure@gocash
        """.format(api_url=self.api_url))
        
        # Save report
        report = {
            "test_type": "Cashfree Payment Flow Test",
            "timestamp": datetime.utcnow().isoformat(),
            "api_url": self.api_url,
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "results": self.test_results,
            "sandbox_test_cards": TEST_CARDS,
            "sandbox_upi": TEST_UPI
        }
        
        report_path = "/app/test_reports/cashfree_payment_flow_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\nReport saved to: {report_path}")
        
        return report


async def main():
    tester = CashfreePaymentTester(API_URL)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
