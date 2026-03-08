"""
Iteration 120 - Revenue Analytics Dashboard & Watermark Service Tests
Tests for:
1. Revenue Analytics API endpoints (admin-only)
2. Watermark should-apply check endpoint
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_EMAIL = "krajapraveen.katta@creatorstudio.ai"
ADMIN_PASSWORD = "Onemanarmy@1979#"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


class TestAuthSetup:
    """Helper class for authentication setup"""
    
    @staticmethod
    def get_admin_token():
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        return None
    
    @staticmethod
    def get_user_token():
        """Get regular user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        return None


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token for tests"""
    token = TestAuthSetup.get_admin_token()
    if not token:
        pytest.skip("Admin authentication failed - cannot test admin endpoints")
    return token


@pytest.fixture(scope="module")
def user_token():
    """Get user token for tests"""
    token = TestAuthSetup.get_user_token()
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin authentication"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def user_headers(user_token):
    """Headers with user authentication"""
    if user_token:
        return {"Authorization": f"Bearer {user_token}"}
    return {}


# ==========================================
# REVENUE ANALYTICS SUMMARY TESTS
# ==========================================

class TestRevenueAnalyticsSummary:
    """Revenue Analytics Summary Endpoint Tests"""
    
    def test_summary_requires_auth(self):
        """Test that summary endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/summary")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Summary endpoint requires authentication")
    
    def test_summary_returns_data(self, admin_headers):
        """Test that summary endpoint returns valid data structure"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/summary", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should have success=True"
        assert "summary" in data, "Response should contain summary"
        
        summary = data["summary"]
        # Verify required fields exist
        required_fields = [
            "totalRevenueAllTime", "totalOrdersAllTime", "periodRevenue", 
            "subscriptionRevenue", "subscriptionCount", "topupRevenue", 
            "topupCount", "netRevenue", "pendingPayments", "failedPayments",
            "refundedPayments", "activeSubscribers"
        ]
        for field in required_fields:
            assert field in summary, f"Summary missing required field: {field}"
        
        # Verify numeric types
        assert isinstance(summary.get("totalRevenueAllTime"), (int, float))
        assert isinstance(summary.get("totalOrdersAllTime"), int)
        
        print(f"PASS: Summary returns valid data - Total Revenue: {summary.get('totalRevenueAllTime')}")
    
    def test_summary_with_date_filter(self, admin_headers):
        """Test summary endpoint with date range filter"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/summary",
            params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "period" in data, "Response should contain period info"
        print("PASS: Summary works with date filters")


# ==========================================
# SUBSCRIPTION BREAKDOWN TESTS
# ==========================================

class TestSubscriptionBreakdown:
    """Subscription Breakdown Endpoint Tests"""
    
    def test_subscriptions_requires_auth(self):
        """Test that subscriptions endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/subscriptions")
        assert response.status_code in [401, 403]
        print("PASS: Subscriptions endpoint requires authentication")
    
    def test_subscriptions_returns_breakdown(self, admin_headers):
        """Test that subscriptions endpoint returns breakdown by type"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/subscriptions",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "subscriptions" in data
        
        subscriptions = data["subscriptions"]
        assert isinstance(subscriptions, list), "Subscriptions should be a list"
        
        # Verify subscription types
        sub_types = [s.get("type") for s in subscriptions]
        expected_types = ["weekly", "monthly", "quarterly", "yearly"]
        for expected in expected_types:
            assert expected in sub_types, f"Missing subscription type: {expected}"
        
        # Verify each subscription has required fields
        for sub in subscriptions:
            assert "type" in sub
            assert "revenue" in sub
            assert "count" in sub
            assert "uniqueUsers" in sub
        
        print(f"PASS: Subscriptions breakdown - {len(subscriptions)} types returned")


# ==========================================
# TOP-UP BREAKDOWN TESTS
# ==========================================

class TestTopupBreakdown:
    """Top-up Breakdown Endpoint Tests"""
    
    def test_topups_requires_auth(self):
        """Test that topups endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/topups")
        assert response.status_code in [401, 403]
        print("PASS: Topups endpoint requires authentication")
    
    def test_topups_returns_breakdown(self, admin_headers):
        """Test that topups endpoint returns breakdown by type"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/topups",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "topups" in data
        
        topups = data["topups"]
        assert isinstance(topups, list)
        
        # Verify topup types
        topup_types = [t.get("type") for t in topups]
        expected_types = ["starter", "creator", "pro"]
        for expected in expected_types:
            assert expected in topup_types, f"Missing topup type: {expected}"
        
        print(f"PASS: Topups breakdown - {len(topups)} types returned")


# ==========================================
# REVENUE TRENDS TESTS
# ==========================================

class TestRevenueTrends:
    """Revenue Trends Endpoint Tests"""
    
    def test_trends_requires_auth(self):
        """Test that trends endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/trends")
        assert response.status_code in [401, 403]
        print("PASS: Trends endpoint requires authentication")
    
    def test_trends_by_day(self, admin_headers):
        """Test trends by day period"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/trends",
            params={"period": "day", "limit": 7},
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("period") == "day"
        assert "trends" in data
        assert isinstance(data["trends"], list)
        
        # Verify trend data structure
        if data["trends"]:
            trend = data["trends"][0]
            assert "period" in trend
            assert "revenue" in trend
            assert "orders" in trend
            assert "subscriptions" in trend
            assert "topups" in trend
        
        print(f"PASS: Daily trends - {len(data['trends'])} data points")
    
    def test_trends_by_month(self, admin_headers):
        """Test trends by month period"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/trends",
            params={"period": "month", "limit": 6},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("period") == "month"
        print("PASS: Monthly trends working")
    
    def test_trends_invalid_period(self, admin_headers):
        """Test trends with invalid period parameter"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/trends",
            params={"period": "invalid"},
            headers=admin_headers
        )
        assert response.status_code == 422, "Should reject invalid period"
        print("PASS: Invalid period properly rejected")


# ==========================================
# TRANSACTIONS LIST TESTS
# ==========================================

class TestTransactionsList:
    """Transactions List Endpoint Tests"""
    
    def test_transactions_requires_auth(self):
        """Test that transactions endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/transactions")
        assert response.status_code in [401, 403]
        print("PASS: Transactions endpoint requires authentication")
    
    def test_transactions_returns_paginated_list(self, admin_headers):
        """Test that transactions returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/transactions",
            params={"page": 1, "limit": 10},
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "transactions" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert "totalPages" in pagination
        
        print(f"PASS: Transactions list - {len(data['transactions'])} items, total: {pagination['total']}")
    
    def test_transactions_with_status_filter(self, admin_headers):
        """Test transactions filtering by status"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/transactions",
            params={"status": "PAID", "limit": 5},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all transactions have PAID status (if any returned)
        for tx in data.get("transactions", []):
            assert tx.get("status") == "PAID", "Filter should return only PAID transactions"
        
        print("PASS: Transactions status filter working")
    
    def test_transactions_with_product_type_filter(self, admin_headers):
        """Test transactions filtering by product type"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/transactions",
            params={"product_type": "subscription", "limit": 5},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all transactions are subscriptions (if any returned)
        for tx in data.get("transactions", []):
            assert tx.get("transactionType") == "subscription"
        
        print("PASS: Transactions product type filter working")


# ==========================================
# TOP USERS TESTS
# ==========================================

class TestTopUsers:
    """Top Paying Users Endpoint Tests"""
    
    def test_top_users_requires_auth(self):
        """Test that top-users endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/top-users")
        assert response.status_code in [401, 403]
        print("PASS: Top users endpoint requires authentication")
    
    def test_top_users_returns_list(self, admin_headers):
        """Test that top-users endpoint returns list of top paying users"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/top-users",
            params={"limit": 10},
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "topUsers" in data
        
        top_users = data["topUsers"]
        assert isinstance(top_users, list)
        
        # Verify user data structure
        for user in top_users:
            assert "userId" in user
            assert "totalSpent" in user
            assert "orderCount" in user
        
        # Verify sorted by total spent (descending)
        for i in range(len(top_users) - 1):
            assert top_users[i]["totalSpent"] >= top_users[i+1]["totalSpent"]
        
        print(f"PASS: Top users - {len(top_users)} users returned")


# ==========================================
# LOCATION BREAKDOWN TESTS
# ==========================================

class TestLocationBreakdown:
    """Revenue by Location Endpoint Tests"""
    
    def test_by_location_requires_auth(self):
        """Test that by-location endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/by-location")
        assert response.status_code in [401, 403]
        print("PASS: By-location endpoint requires authentication")
    
    def test_by_location_returns_breakdown(self, admin_headers):
        """Test that by-location endpoint returns country breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/by-location",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "locationBreakdown" in data
        
        breakdown = data["locationBreakdown"]
        assert isinstance(breakdown, list)
        
        # Verify breakdown structure
        for loc in breakdown:
            assert "country" in loc
            assert "revenue" in loc
            assert "orders" in loc
        
        print(f"PASS: Location breakdown - {len(breakdown)} countries")


# ==========================================
# EXPORT TESTS
# ==========================================

class TestExportFeatures:
    """CSV and Excel Export Tests"""
    
    def test_csv_export_requires_auth(self):
        """Test that CSV export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/export/csv")
        assert response.status_code in [401, 403]
        print("PASS: CSV export requires authentication")
    
    def test_csv_export_returns_file(self, admin_headers):
        """Test that CSV export returns a CSV file"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/export/csv",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers.get("Content-Disposition", "")
        
        # Verify CSV content structure
        content = response.text
        lines = content.strip().split('\n')
        assert len(lines) >= 1, "CSV should have at least header row"
        
        # Verify header columns
        header = lines[0]
        assert "Order ID" in header
        assert "Amount" in header
        assert "Status" in header
        
        print(f"PASS: CSV export - {len(lines)-1} data rows")
    
    def test_excel_export_requires_auth(self):
        """Test that Excel export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/revenue-analytics/export/excel")
        assert response.status_code in [401, 403]
        print("PASS: Excel export requires authentication")
    
    def test_excel_export_returns_file(self, admin_headers):
        """Test that Excel export returns an XLSX file"""
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/export/excel",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheetml" in content_type or "octet-stream" in content_type
        assert "Content-Disposition" in response.headers
        assert ".xlsx" in response.headers.get("Content-Disposition", "")
        
        print("PASS: Excel export returns XLSX file")


# ==========================================
# WATERMARK SERVICE TESTS
# ==========================================

class TestWatermarkShouldApply:
    """Watermark Should-Apply Endpoint Tests"""
    
    def test_should_apply_requires_auth(self):
        """Test that watermark should-apply requires authentication"""
        response = requests.get(f"{BASE_URL}/api/watermark/should-apply")
        assert response.status_code in [401, 403]
        print("PASS: Watermark should-apply requires authentication")
    
    def test_should_apply_for_admin(self, admin_headers):
        """Test that admin users should NOT get watermark"""
        response = requests.get(
            f"{BASE_URL}/api/watermark/should-apply",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "shouldApply" in data
        assert "reason" in data
        
        # Admin should NOT get watermark
        assert data.get("shouldApply") == False, "Admin should not get watermark"
        
        print(f"PASS: Admin watermark check - shouldApply={data.get('shouldApply')}, reason={data.get('reason')}")
    
    def test_should_apply_for_user(self, user_headers):
        """Test watermark check for regular user"""
        if not user_headers:
            pytest.skip("User authentication not available")
        
        response = requests.get(
            f"{BASE_URL}/api/watermark/should-apply",
            headers=user_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "shouldApply" in data
        assert "plan" in data
        
        # Log result - depends on user's payment status
        print(f"PASS: User watermark check - shouldApply={data.get('shouldApply')}, plan={data.get('plan')}, reason={data.get('reason')}")


# ==========================================
# ADMIN ACCESS CONTROL TESTS
# ==========================================

class TestAdminAccessControl:
    """Test that non-admin users cannot access admin endpoints"""
    
    def test_non_admin_cannot_access_summary(self, user_headers):
        """Test that regular user cannot access revenue summary"""
        if not user_headers:
            pytest.skip("User authentication not available")
        
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/summary",
            headers=user_headers
        )
        # Should be 403 Forbidden for non-admin
        assert response.status_code in [401, 403], f"Non-admin should be blocked, got {response.status_code}"
        print("PASS: Non-admin blocked from revenue summary")
    
    def test_non_admin_cannot_access_top_users(self, user_headers):
        """Test that regular user cannot access top users"""
        if not user_headers:
            pytest.skip("User authentication not available")
        
        response = requests.get(
            f"{BASE_URL}/api/revenue-analytics/top-users",
            headers=user_headers
        )
        assert response.status_code in [401, 403]
        print("PASS: Non-admin blocked from top users")


# ==========================================
# MAIN TEST RUNNER
# ==========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
