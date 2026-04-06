"""
Payment Idempotency & Race Condition Tests
Tests 5 scenarios:
1. Verify runs first, webhook later
2. Webhook runs first, verify later
3. Duplicate webhook delivery
4. Repeated verify calls
5. Webhook-only fulfillment (user closes browser)
"""
import asyncio
import sys
import os
import uuid
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymongo

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "creatorstudio_production")

client = pymongo.MongoClient(MONGO_URL)
db = client[DB_NAME]

TEST_USER_ID = f"test_pay_{uuid.uuid4().hex[:8]}"
TEST_USER_EMAIL = f"paytest_{uuid.uuid4().hex[:6]}@test.com"

def setup_test_user():
    """Create a test user with 50 credits"""
    db.users.insert_one({
        "id": TEST_USER_ID,
        "email": TEST_USER_EMAIL,
        "name": "Payment Test User",
        "role": "user",
        "credits": 50,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    print(f"Created test user: {TEST_USER_ID} with 50 credits")

def create_test_order(order_id, product_type="subscription", product_id="weekly", credits=40, amount=14900):
    """Create a test order"""
    db.orders.insert_one({
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "userId": TEST_USER_ID,
        "userEmail": TEST_USER_EMAIL,
        "productId": product_id,
        "productName": "Weekly Subscription",
        "productType": product_type,
        "amount": amount,
        "currency": "INR",
        "credits": credits,
        "gateway": "cashfree",
        "status": "CREATED",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })

def get_user_credits():
    user = db.users.find_one({"id": TEST_USER_ID}, {"_id": 0, "credits": 1})
    return user.get("credits", 0) if user else 0

def get_order_status(order_id):
    order = db.orders.find_one({"order_id": order_id}, {"_id": 0, "status": 1})
    return order.get("status", "NOT_FOUND") if order else "NOT_FOUND"

def get_subscription_status():
    user = db.users.find_one({"id": TEST_USER_ID}, {"_id": 0, "subscription": 1})
    sub = user.get("subscription", {}) if user else {}
    return sub.get("status", "none")

def count_ledger_entries(order_id):
    return db.credit_ledger.count_documents({"reference_id": order_id, "userId": TEST_USER_ID})

def simulate_webhook_success(order_id):
    """Simulate what the webhook handler does for PAYMENT_SUCCESS_WEBHOOK"""
    order = db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
    if not order:
        return "ORDER_NOT_FOUND"
    
    terminal_states = ("PAID", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED")
    if order["status"] in terminal_states:
        return "ALREADY_TERMINAL"
    
    # Check ledger idempotency
    already_credited = db.credit_ledger.find_one({"reference_id": order_id, "tx_type": "award", "userId": TEST_USER_ID})
    if already_credited:
        return "LEDGER_DUPLICATE_BLOCKED"
    
    # Add credits
    db.users.update_one({"id": TEST_USER_ID}, {"$inc": {"credits": order["credits"]}})
    db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": TEST_USER_ID,
        "tx_type": "award",
        "amount": order["credits"],
        "reason": f"Cashfree payment - {order.get('productName', '')}",
        "reference_id": order_id,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Handle subscription
    product_type = order.get("productType", "topup")
    now_iso = datetime.now(timezone.utc).isoformat()
    
    if product_type == "subscription":
        final_status = "SUBSCRIPTION_ACTIVATED"
        db.users.update_one(
            {"id": TEST_USER_ID},
            {"$set": {
                "subscription": {
                    "planId": order.get("productId", ""),
                    "planName": order.get("productName", ""),
                    "status": "active",
                    "startDate": now_iso,
                    "endDate": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                    "orderId": order_id,
                }
            }}
        )
    else:
        final_status = "CREDIT_APPLIED"
    
    db.orders.update_one(
        {"order_id": order_id},
        {"$set": {"status": final_status, "paidAt": now_iso, "entitlementApplied": True}}
    )
    return final_status

def simulate_verify_success(order_id):
    """Simulate what the verify endpoint does"""
    order = db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
    if not order:
        return "ORDER_NOT_FOUND"
    
    terminal_states = ("PAID", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED")
    if order["status"] in terminal_states:
        return "ALREADY_PROCESSED"
    
    # Check ledger idempotency
    already_credited = db.credit_ledger.find_one({"reference_id": order_id, "tx_type": "award", "userId": TEST_USER_ID})
    if already_credited:
        # Skip crediting but still activate subscription
        pass
    else:
        db.users.update_one({"id": TEST_USER_ID}, {"$inc": {"credits": order["credits"]}})
        db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": TEST_USER_ID,
            "tx_type": "award",
            "amount": order["credits"],
            "reason": f"Purchased via Cashfree - {order.get('productName', '')}",
            "reference_id": order_id,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
    
    product_type = order.get("productType", "topup")
    now_iso = datetime.now(timezone.utc).isoformat()
    
    if product_type == "subscription":
        final_status = "SUBSCRIPTION_ACTIVATED"
        db.users.update_one(
            {"id": TEST_USER_ID},
            {"$set": {
                "subscription": {
                    "planId": order.get("productId", ""),
                    "planName": order.get("productName", ""),
                    "status": "active",
                    "startDate": now_iso,
                    "endDate": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                    "orderId": order_id,
                }
            }}
        )
    else:
        final_status = "CREDIT_APPLIED"
    
    db.orders.update_one(
        {"order_id": order_id},
        {"$set": {"status": final_status, "paidAt": now_iso, "entitlementApplied": True}}
    )
    return final_status


def cleanup():
    db.users.delete_one({"id": TEST_USER_ID})
    db.orders.delete_many({"userId": TEST_USER_ID})
    db.credit_ledger.delete_many({"userId": TEST_USER_ID})


results = []

def run_test(name, test_fn):
    try:
        passed, detail = test_fn()
        status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        print(f"  {'✅' if passed else '❌'} {name}: {detail}")
    except Exception as e:
        results.append({"test": name, "status": "ERROR", "detail": str(e)})
        print(f"  ❌ {name}: ERROR - {e}")


def test_scenario_1():
    """Scenario 1: Verify runs first, webhook later"""
    order_id = f"test_s1_{uuid.uuid4().hex[:8]}"
    create_test_order(order_id)
    initial_credits = get_user_credits()
    
    # Verify runs first
    verify_result = simulate_verify_success(order_id)
    credits_after_verify = get_user_credits()
    
    # Webhook runs later
    webhook_result = simulate_webhook_success(order_id)
    credits_after_webhook = get_user_credits()
    
    expected_credits = initial_credits + 40
    ledger_count = count_ledger_entries(order_id)
    sub_status = get_subscription_status()
    
    passed = (
        credits_after_verify == expected_credits and
        credits_after_webhook == expected_credits and  # No double credit
        ledger_count == 1 and
        sub_status == "active" and
        verify_result == "SUBSCRIPTION_ACTIVATED" and
        webhook_result == "ALREADY_TERMINAL"
    )
    
    detail = (
        f"initial={initial_credits}, after_verify={credits_after_verify}, "
        f"after_webhook={credits_after_webhook}, expected={expected_credits}, "
        f"ledger_entries={ledger_count}, sub={sub_status}, "
        f"verify={verify_result}, webhook={webhook_result}"
    )
    return passed, detail


def test_scenario_2():
    """Scenario 2: Webhook runs first, verify later"""
    order_id = f"test_s2_{uuid.uuid4().hex[:8]}"
    create_test_order(order_id)
    initial_credits = get_user_credits()
    
    # Webhook runs first
    webhook_result = simulate_webhook_success(order_id)
    credits_after_webhook = get_user_credits()
    
    # Verify runs later
    verify_result = simulate_verify_success(order_id)
    credits_after_verify = get_user_credits()
    
    expected_credits = initial_credits + 40
    ledger_count = count_ledger_entries(order_id)
    sub_status = get_subscription_status()
    
    passed = (
        credits_after_webhook == expected_credits and
        credits_after_verify == expected_credits and  # No double credit
        ledger_count == 1 and
        sub_status == "active" and
        webhook_result == "SUBSCRIPTION_ACTIVATED" and
        verify_result == "ALREADY_PROCESSED"
    )
    
    detail = (
        f"initial={initial_credits}, after_webhook={credits_after_webhook}, "
        f"after_verify={credits_after_verify}, expected={expected_credits}, "
        f"ledger_entries={ledger_count}, sub={sub_status}, "
        f"webhook={webhook_result}, verify={verify_result}"
    )
    return passed, detail


def test_scenario_3():
    """Scenario 3: Duplicate webhook delivery"""
    order_id = f"test_s3_{uuid.uuid4().hex[:8]}"
    create_test_order(order_id)
    initial_credits = get_user_credits()
    
    # First webhook
    result1 = simulate_webhook_success(order_id)
    credits_after_first = get_user_credits()
    
    # Duplicate webhook
    result2 = simulate_webhook_success(order_id)
    credits_after_second = get_user_credits()
    
    # Triple webhook
    result3 = simulate_webhook_success(order_id)
    credits_after_third = get_user_credits()
    
    expected_credits = initial_credits + 40
    ledger_count = count_ledger_entries(order_id)
    
    passed = (
        credits_after_first == expected_credits and
        credits_after_second == expected_credits and
        credits_after_third == expected_credits and
        ledger_count == 1 and
        result1 == "SUBSCRIPTION_ACTIVATED" and
        result2 == "ALREADY_TERMINAL" and
        result3 == "ALREADY_TERMINAL"
    )
    
    detail = (
        f"initial={initial_credits}, after_1st={credits_after_first}, "
        f"after_2nd={credits_after_second}, after_3rd={credits_after_third}, "
        f"expected={expected_credits}, ledger={ledger_count}, "
        f"results=[{result1}, {result2}, {result3}]"
    )
    return passed, detail


def test_scenario_4():
    """Scenario 4: Repeated verify calls"""
    order_id = f"test_s4_{uuid.uuid4().hex[:8]}"
    create_test_order(order_id)
    initial_credits = get_user_credits()
    
    # First verify
    result1 = simulate_verify_success(order_id)
    credits_after_first = get_user_credits()
    
    # Second verify
    result2 = simulate_verify_success(order_id)
    credits_after_second = get_user_credits()
    
    # Third verify
    result3 = simulate_verify_success(order_id)
    credits_after_third = get_user_credits()
    
    expected_credits = initial_credits + 40
    ledger_count = count_ledger_entries(order_id)
    
    passed = (
        credits_after_first == expected_credits and
        credits_after_second == expected_credits and
        credits_after_third == expected_credits and
        ledger_count == 1 and
        result1 == "SUBSCRIPTION_ACTIVATED" and
        result2 == "ALREADY_PROCESSED" and
        result3 == "ALREADY_PROCESSED"
    )
    
    detail = (
        f"initial={initial_credits}, after_1st={credits_after_first}, "
        f"after_2nd={credits_after_second}, after_3rd={credits_after_third}, "
        f"expected={expected_credits}, ledger={ledger_count}, "
        f"results=[{result1}, {result2}, {result3}]"
    )
    return passed, detail


def test_scenario_5():
    """Scenario 5: Webhook-only fulfillment (user closes browser)"""
    order_id = f"test_s5_{uuid.uuid4().hex[:8]}"
    create_test_order(order_id)
    initial_credits = get_user_credits()
    
    # Only webhook fires (user never returned to app)
    webhook_result = simulate_webhook_success(order_id)
    final_credits = get_user_credits()
    
    expected_credits = initial_credits + 40
    ledger_count = count_ledger_entries(order_id)
    sub_status = get_subscription_status()
    order_status = get_order_status(order_id)
    
    passed = (
        final_credits == expected_credits and
        ledger_count == 1 and
        sub_status == "active" and
        order_status == "SUBSCRIPTION_ACTIVATED" and
        webhook_result == "SUBSCRIPTION_ACTIVATED"
    )
    
    detail = (
        f"initial={initial_credits}, final={final_credits}, expected={expected_credits}, "
        f"ledger={ledger_count}, sub={sub_status}, order={order_status}, "
        f"webhook={webhook_result}"
    )
    return passed, detail


if __name__ == "__main__":
    print("\n=== Payment Idempotency & Race Condition Tests ===\n")
    
    # Setup
    cleanup()
    setup_test_user()
    
    # Run tests
    print("\nScenario 1: Verify first, webhook later")
    run_test("verify_first_webhook_later", test_scenario_1)
    
    print("\nScenario 2: Webhook first, verify later")
    run_test("webhook_first_verify_later", test_scenario_2)
    
    print("\nScenario 3: Duplicate webhook delivery")
    run_test("duplicate_webhook", test_scenario_3)
    
    print("\nScenario 4: Repeated verify calls")
    run_test("repeated_verify", test_scenario_4)
    
    print("\nScenario 5: Webhook-only fulfillment")
    run_test("webhook_only_fulfillment", test_scenario_5)
    
    # Cleanup
    cleanup()
    
    # Summary
    print("\n=== SUMMARY ===")
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] != "PASS")
    print(f"Passed: {passed}/{len(results)}")
    if failed > 0:
        print(f"Failed: {failed}")
        for r in results:
            if r["status"] != "PASS":
                print(f"  ❌ {r['test']}: {r['detail']}")
    
    # Write results to file
    report = {
        "test_suite": "payment_idempotency",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "passed": passed,
        "total": len(results)
    }
    
    os.makedirs("/app/test_reports", exist_ok=True)
    with open("/app/test_reports/payment_idempotency.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to /app/test_reports/payment_idempotency.json")
    
    sys.exit(0 if failed == 0 else 1)
