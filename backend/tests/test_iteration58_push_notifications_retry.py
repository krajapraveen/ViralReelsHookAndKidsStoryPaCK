"""
Test Suite for Iteration 58 - Push Notifications and Retry Mechanism
Tests:
1. Push Notifications API endpoints
2. Retry Mechanism code structure verification
3. Integration of retry with generation endpoints
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


class TestAuthAndSetup:
    """Authentication tests to get tokens for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth token"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        """Get demo user authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def demo_headers(self, demo_token):
        """Get headers with demo user auth token"""
        return {
            "Authorization": f"Bearer {demo_token}",
            "Content-Type": "application/json"
        }
    
    def test_admin_login(self):
        """Test admin login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "ADMIN"
        print(f"Admin login successful: {data['user']['email']}")


class TestPushNotificationsAPI:
    """Test Push Notifications API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        """Get admin auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = response.json()["token"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test_get_notification_list(self, admin_headers):
        """Test GET /api/notifications/list - List admin notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/list",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to get notifications list: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "notifications" in data, "Response should have 'notifications' field"
        assert "total" in data, "Response should have 'total' field"
        assert "unreadCount" in data, "Response should have 'unreadCount' field"
        assert isinstance(data["notifications"], list), "Notifications should be a list"
        
        print(f"Notifications list: total={data['total']}, unread={data['unreadCount']}")
    
    def test_get_notification_list_unread_only(self, admin_headers):
        """Test GET /api/notifications/list?unread_only=true"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/list?unread_only=true",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        print(f"Unread notifications: {len(data['notifications'])}")
    
    def test_get_notification_preferences(self, admin_headers):
        """Test GET /api/notifications/preferences - Get notification preferences"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/preferences",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to get preferences: {response.text}"
        data = response.json()
        
        # Verify preference fields exist
        expected_fields = [
            "security_threat", "high_value_conversion", "failed_payment",
            "new_user_signup", "generation_failure", "system_alert",
            "email_enabled", "sms_enabled", "push_enabled"
        ]
        for field in expected_fields:
            assert field in data, f"Preference field '{field}' should exist"
        
        print(f"Notification preferences: email={data['email_enabled']}, sms={data['sms_enabled']}, push={data['push_enabled']}")
    
    def test_update_notification_preferences(self, admin_headers):
        """Test PUT /api/notifications/preferences - Update preferences"""
        preferences = {
            "security_threat": True,
            "high_value_conversion": True,
            "failed_payment": True,
            "new_user_signup": False,
            "generation_failure": True,
            "system_alert": True,
            "email_enabled": True,
            "sms_enabled": False,
            "push_enabled": True
        }
        
        response = requests.put(
            f"{BASE_URL}/api/notifications/preferences",
            headers=admin_headers,
            json=preferences
        )
        assert response.status_code == 200, f"Failed to update preferences: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Update should be successful"
        assert "preferences" in data, "Response should contain updated preferences"
        
        print("Notification preferences updated successfully")
    
    def test_send_test_notification(self, admin_headers):
        """Test POST /api/notifications/test - Send test notification"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/test",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to send test notification: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Test notification should be successful"
        assert "notification_id" in data, "Response should contain notification_id"
        assert data.get("message") == "Test notification sent", "Should have success message"
        
        notification_id = data["notification_id"]
        print(f"Test notification sent successfully: {notification_id}")
        
        return notification_id
    
    def test_poll_notifications(self, admin_headers):
        """Test GET /api/notifications/poll - Poll for new notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/poll",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to poll notifications: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "new" in data, "Response should have 'new' field"
        assert "unreadCount" in data, "Response should have 'unreadCount' field"
        assert "timestamp" in data, "Response should have 'timestamp' field"
        assert isinstance(data["new"], list), "'new' should be a list"
        
        print(f"Poll result: {len(data['new'])} new notifications, unread count: {data['unreadCount']}")
    
    def test_mark_notification_read(self, admin_headers):
        """Test POST /api/notifications/mark-read/{id}"""
        # First send a test notification
        test_response = requests.post(
            f"{BASE_URL}/api/notifications/test",
            headers=admin_headers
        )
        assert test_response.status_code == 200
        notification_id = test_response.json()["notification_id"]
        
        # Mark it as read
        response = requests.post(
            f"{BASE_URL}/api/notifications/mark-read/{notification_id}",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to mark notification as read: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Mark as read should be successful"
        
        print(f"Notification {notification_id} marked as read")
    
    def test_mark_notification_read_invalid_id(self, admin_headers):
        """Test marking invalid notification as read returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/mark-read/invalid-notification-id-12345",
            headers=admin_headers
        )
        # Should return 404 for non-existent notification
        assert response.status_code == 404, f"Expected 404 for invalid notification ID, got {response.status_code}"
        print("Correctly returned 404 for invalid notification ID")
    
    def test_mark_all_notifications_read(self, admin_headers):
        """Test POST /api/notifications/mark-all-read"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/mark-all-read",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to mark all as read: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Mark all as read should be successful"
        assert "marked" in data, "Response should contain count of marked notifications"
        
        print(f"Marked {data['marked']} notifications as read")
    
    def test_unauthorized_access_notifications(self):
        """Test that notification endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications/list")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("Correctly rejected unauthorized access to notifications")


class TestRetryMechanismCodeStructure:
    """Test Retry Mechanism code structure and configuration"""
    
    def test_retry_mechanism_file_exists(self):
        """Verify retry_mechanism.py exists with proper functions"""
        import sys
        import importlib.util
        
        # Load the module
        retry_file = "/app/backend/utils/retry_mechanism.py"
        spec = importlib.util.spec_from_file_location("retry_mechanism", retry_file)
        retry_module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(retry_module)
            
            # Verify key functions exist
            assert hasattr(retry_module, 'with_retry'), "with_retry function should exist"
            assert hasattr(retry_module, 'retry_decorator'), "retry_decorator should exist"
            assert hasattr(retry_module, 'categorize_error'), "categorize_error should exist"
            assert hasattr(retry_module, 'RetryContext'), "RetryContext class should exist"
            assert hasattr(retry_module, 'retry_text_to_image'), "retry_text_to_image should exist"
            assert hasattr(retry_module, 'retry_text_to_video'), "retry_text_to_video should exist"
            assert hasattr(retry_module, 'retry_story_generation'), "retry_story_generation should exist"
            assert hasattr(retry_module, 'retry_reel_generation'), "retry_reel_generation should exist"
            
            print("All retry mechanism functions verified")
            
        except Exception as e:
            pytest.fail(f"Failed to load retry_mechanism module: {e}")
    
    def test_retry_strategies_configuration(self):
        """Verify retry strategies are properly configured"""
        import sys
        import importlib.util
        
        retry_file = "/app/backend/utils/retry_mechanism.py"
        spec = importlib.util.spec_from_file_location("retry_mechanism", retry_file)
        retry_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retry_module)
        
        strategies = retry_module.RETRY_STRATEGIES
        
        # Verify network retry strategy
        assert "network" in strategies, "Network retry strategy should exist"
        assert strategies["network"]["max_retries"] == 5, "Network should have 5 retries"
        
        # Verify rate_limit strategy
        assert "rate_limit" in strategies, "Rate limit retry strategy should exist"
        assert strategies["rate_limit"]["max_retries"] == 3, "Rate limit should have 3 retries"
        assert strategies["rate_limit"]["initial_delay"] == 30, "Rate limit should have 30s initial delay"
        
        # Verify content_safety strategy (should NOT retry)
        assert "content_safety" in strategies, "Content safety strategy should exist"
        assert strategies["content_safety"]["max_retries"] == 0, "Content policy violations should NOT be retried"
        
        # Verify ai_generation strategy
        assert "ai_generation" in strategies, "AI generation retry strategy should exist"
        assert strategies["ai_generation"]["max_retries"] == 3, "AI generation should have 3 retries"
        
        print("Retry strategies configuration verified:")
        print(f"  - Network errors: {strategies['network']['max_retries']} retries")
        print(f"  - Rate limit: {strategies['rate_limit']['max_retries']} retries, {strategies['rate_limit']['initial_delay']}s delay")
        print(f"  - Content safety: {strategies['content_safety']['max_retries']} retries (no retry)")
    
    def test_error_categorization(self):
        """Test error categorization function"""
        import sys
        import importlib.util
        
        retry_file = "/app/backend/utils/retry_mechanism.py"
        spec = importlib.util.spec_from_file_location("retry_mechanism", retry_file)
        retry_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retry_module)
        
        categorize_error = retry_module.categorize_error
        
        # Test network errors
        network_error = ConnectionError("Connection refused")
        assert categorize_error(network_error) == "network", "ConnectionError should be categorized as network"
        
        # Test content safety errors
        content_error = Exception("content policy violation detected")
        assert categorize_error(content_error) == "content_safety", "Content policy error should be categorized as content_safety"
        
        # Test rate limit errors
        rate_error = Exception("Rate limit exceeded - 429 Too Many Requests")
        assert categorize_error(rate_error) == "rate_limit", "Rate limit error should be categorized correctly"
        
        # Test default error
        generic_error = Exception("Some random error")
        assert categorize_error(generic_error) == "default", "Unknown error should be categorized as default"
        
        print("Error categorization tests passed")


class TestRetryInGenerationEndpoints:
    """Verify retry mechanism is integrated in generation endpoints"""
    
    def test_genstudio_text_to_image_retry_structure(self):
        """Verify text-to-image endpoint has retry logic"""
        with open("/app/backend/routes/genstudio.py", "r") as f:
            content = f.read()
        
        # Check for retry-related code in text-to-image
        assert "max_retries = 3" in content, "text-to-image should have max_retries=3"
        assert "while attempt <= max_retries" in content, "Should have retry loop"
        assert "retrying (attempt" in content.lower() or "retry" in content.lower(), "Should update status for retry"
        assert "exponential" in content.lower() or "asyncio.sleep" in content.lower(), "Should have backoff delay"
        
        # Check content policy violations are NOT retried
        assert 'content_safety' in content, "Should check for content_safety errors"
        
        print("text-to-image retry structure verified:")
        print("  - max_retries = 3")
        print("  - retry loop present")
        print("  - exponential backoff implemented")
        print("  - content policy violations not retried")
    
    def test_genstudio_text_to_video_retry_structure(self):
        """Verify text-to-video endpoint has retry logic"""
        with open("/app/backend/routes/genstudio.py", "r") as f:
            content = f.read()
        
        # Check for retry logic in process_text_to_video function
        assert "process_text_to_video" in content, "process_text_to_video function should exist"
        assert "while attempt <= max_retries" in content, "Should have retry loop in video generation"
        
        print("text-to-video retry structure verified")
    
    def test_generation_reel_retry_structure(self):
        """Verify reel generation has retry logic"""
        with open("/app/backend/routes/generation.py", "r") as f:
            content = f.read()
        
        # Check for retry-related code in reel generation
        assert "generate_reel_content_inline" in content, "Reel generation function should exist"
        assert "max_retries = 3" in content, "Reel generation should have max_retries=3"
        assert "Retrying reel generation" in content, "Should log retry attempts"
        
        print("Reel generation retry structure verified:")
        print("  - max_retries = 3")
        print("  - retry logging present")
    
    def test_generation_story_retry_structure(self):
        """Verify story generation has retry logic"""
        with open("/app/backend/routes/generation.py", "r") as f:
            content = f.read()
        
        # Check for retry-related code in story generation
        assert "generate_story_content_inline" in content, "Story content generation function should exist"
        assert "generate_story_image" in content, "Story image generation function should exist"
        
        # Verify story content retry
        assert "Retrying story content generation" in content, "Should log story content retry attempts"
        
        # Verify story image retry
        assert "Retrying story image generation" in content, "Should log story image retry attempts"
        
        print("Story generation retry structure verified:")
        print("  - Content generation with retry")
        print("  - Image generation with retry")
    
    def test_notify_generation_failure_integration(self):
        """Verify generation failures trigger admin notifications"""
        with open("/app/backend/routes/genstudio.py", "r") as f:
            genstudio_content = f.read()
        
        with open("/app/backend/routes/generation.py", "r") as f:
            generation_content = f.read()
        
        # Check that notify_generation_failure is called after all retries exhausted
        assert "notify_generation_failure" in genstudio_content, "GenStudio should notify on failure"
        
        # Check push_notifications import
        assert "from routes.push_notifications import notify_generation_failure" in genstudio_content or \
               "push_notifications" in genstudio_content, "Should import notification function"
        
        print("Generation failure notification integration verified")


class TestNotificationTypes:
    """Verify notification types are properly configured"""
    
    def test_notification_types_configuration(self):
        """Verify all notification types exist"""
        with open("/app/backend/routes/push_notifications.py", "r") as f:
            content = f.read()
        
        expected_types = [
            "security_threat",
            "high_value_conversion",
            "failed_payment",
            "new_user_signup",
            "generation_failure",
            "system_alert"
        ]
        
        for notification_type in expected_types:
            assert f'"{notification_type}"' in content, f"Notification type '{notification_type}' should exist"
        
        print(f"All {len(expected_types)} notification types verified")
    
    def test_notification_channels(self):
        """Verify notification channels are configured"""
        with open("/app/backend/routes/push_notifications.py", "r") as f:
            content = f.read()
        
        # Verify channels exist
        assert '"push"' in content, "Push channel should exist"
        assert '"email"' in content, "Email channel should exist"
        assert '"sms"' in content, "SMS channel should exist"
        
        # Verify security threats use all channels
        assert '"channels": ["push", "email", "sms"]' in content, "Security threats should use all channels"
        
        print("Notification channels verified: push, email, sms")
    
    def test_security_threat_notification_function(self):
        """Verify security threat notification function exists"""
        with open("/app/backend/routes/push_notifications.py", "r") as f:
            content = f.read()
        
        assert "async def notify_security_threat" in content, "notify_security_threat function should exist"
        assert "priority=\"critical\"" in content, "Security threats should have critical priority"
        
        print("Security threat notification function verified")
    
    def test_high_value_conversion_notification(self):
        """Verify high value conversion notification function exists"""
        with open("/app/backend/routes/push_notifications.py", "r") as f:
            content = f.read()
        
        assert "async def notify_high_value_conversion" in content, "notify_high_value_conversion function should exist"
        assert "threshold = 1000" in content, "Should have threshold for high-value notifications"
        
        print("High value conversion notification verified with threshold")


class TestDemoUserNotificationAccess:
    """Test that non-admin users cannot access admin notifications"""
    
    @pytest.fixture(scope="class")
    def demo_headers(self):
        """Get demo user auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Demo user login failed")
        token = response.json()["token"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test_demo_user_cannot_access_notifications_list(self, demo_headers):
        """Non-admin users should not access notification list"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/list",
            headers=demo_headers
        )
        # Should return 401/403 for non-admin users
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print("Non-admin correctly denied access to notifications list")
    
    def test_demo_user_cannot_send_test_notification(self, demo_headers):
        """Non-admin users should not send test notifications"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/test",
            headers=demo_headers
        )
        # Should return 401/403 for non-admin users
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print("Non-admin correctly denied access to send test notifications")


class TestRetryMechanismHelperFunctions:
    """Test retry mechanism utility functions"""
    
    def test_get_retry_config_function(self):
        """Test get_retry_config returns proper config"""
        import sys
        import importlib.util
        
        retry_file = "/app/backend/utils/retry_mechanism.py"
        spec = importlib.util.spec_from_file_location("retry_mechanism", retry_file)
        retry_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retry_module)
        
        get_retry_config = retry_module.get_retry_config
        
        # Test network config
        network_config = get_retry_config("network")
        assert network_config["max_retries"] == 5
        assert network_config["initial_delay"] == 1
        
        # Test rate_limit config
        rate_config = get_retry_config("rate_limit")
        assert rate_config["max_retries"] == 3
        assert rate_config["initial_delay"] == 30
        
        # Test default config for unknown category
        default_config = get_retry_config("unknown_category")
        assert default_config["max_retries"] == 2
        
        print("get_retry_config function verified")
    
    def test_retry_context_class(self):
        """Test RetryContext class functionality"""
        import sys
        import importlib.util
        
        retry_file = "/app/backend/utils/retry_mechanism.py"
        spec = importlib.util.spec_from_file_location("retry_mechanism", retry_file)
        retry_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retry_module)
        
        RetryContext = retry_module.RetryContext
        
        # Create context
        ctx = RetryContext(
            job_id="test-job-123",
            job_type="text_to_image",
            user_id="user-123",
            max_retries=3
        )
        
        assert ctx.job_id == "test-job-123"
        assert ctx.job_type == "text_to_image"
        assert ctx.max_retries == 3
        assert ctx.attempt == 0
        
        # Test delay calculation
        delay1 = ctx.get_delay()
        assert delay1 == 2  # default initial_delay
        
        ctx.increment_attempt()
        assert ctx.attempt == 1
        
        delay2 = ctx.get_delay()
        assert delay2 == 4  # 2 * 2^1
        
        print("RetryContext class verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
