"""
Test Multi-Signal First-Time Free Viewing + Abuse Prevention (P0.5 Hardening)
Iteration 462 - Tests for device_token, user_id, IP hash multi-signal detection

Features tested:
1. Backend POST /api/public/quick-generate accepts device_token field
2. Backend returns allow_free_view=true for brand-new device_token
3. Backend returns allow_free_view=true for same session + continue mode
4. Backend returns allow_free_view=false for same session + fresh mode (2nd story = abuse blocked)
5. Backend returns allow_free_view=false for different session (returning user)
6. Backend stores benefit in first_time_benefits collection with device_token, user_id, ip_hash
7. IP secondary signal: new device_token but same IP = blocked if benefit exists for that IP
"""

import pytest
import requests
import os
import time
import random
import string
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

def generate_device_token():
    """Generate a unique device token like frontend does"""
    return f"dt_test_{int(time.time())}_{random.randint(1000, 9999)}"

def generate_session_id():
    """Generate a unique session ID"""
    return f"test_session_{int(time.time())}_{random.randint(1000, 9999)}"


class TestMultiSignalFreeView:
    """Tests for multi-signal first-time free viewing detection"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test - clear test data from MongoDB"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        async def clear_test_data():
            client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
            db = client['creatorstudio_production']
            
            # Clear test entries from first_time_benefits
            await db.first_time_benefits.delete_many({
                '$or': [
                    {'device_token': {'$regex': '^dt_test_'}},
                    {'benefit_session_id': {'$regex': '^test_session_'}}
                ]
            })
            
            # Clear test rate limit entries
            await db.instant_story_requests.delete_many({
                'session_id': {'$regex': '^test_session_'}
            })
        
        asyncio.run(clear_test_data())
        yield
    
    def test_api_accepts_device_token_field(self):
        """Test 1: Backend POST /api/public/quick-generate accepts device_token field"""
        device_token = generate_device_token()
        session_id = generate_session_id()
        
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id,
                "device_token": device_token,
                "theme": "Test story for device token acceptance"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # Should not return 422 (validation error) for device_token field
        assert response.status_code != 422, f"API rejected device_token field: {response.text}"
        # Should return 200 or 429 (rate limit)
        assert response.status_code in [200, 429], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "allow_free_view" in data, "Response missing allow_free_view field"
            print(f"SUCCESS: API accepts device_token, allow_free_view={data['allow_free_view']}")
    
    def test_first_time_device_gets_free_view(self):
        """Test 2: Backend returns allow_free_view=true for brand-new device_token"""
        device_token = generate_device_token()
        session_id = generate_session_id()
        
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id,
                "device_token": device_token,
                "theme": "First time user story"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limit hit - skipping test")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("allow_free_view") == True, f"First-time device should get allow_free_view=true, got {data.get('allow_free_view')}"
        print(f"SUCCESS: First-time device gets allow_free_view=true")
    
    def test_same_session_continue_mode_allowed(self):
        """Test 3: Backend returns allow_free_view=true for same session + continue mode"""
        device_token = generate_device_token()
        session_id = generate_session_id()
        
        # First request - fresh mode
        response1 = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id,
                "device_token": device_token,
                "theme": "Initial story"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response1.status_code == 429:
            pytest.skip("Rate limit hit - skipping test")
        
        assert response1.status_code == 200
        data1 = response1.json()
        story_text = data1.get("story_text", "")[:200]
        
        # Second request - continue mode with same session
        response2 = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "continue",
                "session_id": session_id,
                "device_token": device_token,
                "source_title": "Test Story",
                "source_snippet": story_text
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response2.status_code == 429:
            pytest.skip("Rate limit hit on second request")
        
        assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
        data2 = response2.json()
        
        # Same session + continue mode should still be allowed
        assert data2.get("allow_free_view") == True, f"Same session + continue should get allow_free_view=true, got {data2.get('allow_free_view')}"
        print(f"SUCCESS: Same session + continue mode gets allow_free_view=true")
    
    def test_same_session_fresh_mode_blocked(self):
        """Test 4: Backend returns allow_free_view=false for same session + fresh mode (2nd story = abuse)"""
        device_token = generate_device_token()
        session_id = generate_session_id()
        
        # First request - fresh mode
        response1 = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id,
                "device_token": device_token,
                "theme": "First story"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response1.status_code == 429:
            pytest.skip("Rate limit hit - skipping test")
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1.get("allow_free_view") == True, "First story should be free"
        
        # Second request - fresh mode again (trying to get another free story)
        response2 = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id,
                "device_token": device_token,
                "theme": "Second story attempt"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response2.status_code == 429:
            pytest.skip("Rate limit hit on second request")
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Same session + fresh mode (2nd story) should be blocked
        assert data2.get("allow_free_view") == False, f"Same session + fresh (2nd story) should get allow_free_view=false, got {data2.get('allow_free_view')}"
        print(f"SUCCESS: Same session + fresh mode (2nd story) gets allow_free_view=false (abuse blocked)")
    
    def test_different_session_blocked(self):
        """Test 5: Backend returns allow_free_view=false for different session (returning user)"""
        device_token = generate_device_token()
        session_id_1 = generate_session_id()
        
        # First request with session 1
        response1 = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id_1,
                "device_token": device_token,
                "theme": "First session story"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response1.status_code == 429:
            pytest.skip("Rate limit hit - skipping test")
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1.get("allow_free_view") == True, "First session should be free"
        
        # Second request with different session (simulating returning user)
        session_id_2 = generate_session_id()
        response2 = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id_2,
                "device_token": device_token,
                "theme": "Second session story"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response2.status_code == 429:
            pytest.skip("Rate limit hit on second request")
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Different session with same device_token should be blocked
        assert data2.get("allow_free_view") == False, f"Different session (returning user) should get allow_free_view=false, got {data2.get('allow_free_view')}"
        print(f"SUCCESS: Different session (returning user) gets allow_free_view=false")


class TestBenefitStorage:
    """Tests for first_time_benefits collection storage"""
    
    def test_benefit_stored_with_multi_signal_fields(self):
        """Test 6: Backend stores benefit with device_token, user_id, ip_hash fields"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        device_token = generate_device_token()
        session_id = generate_session_id()
        
        # Make API request
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id,
                "device_token": device_token,
                "theme": "Test benefit storage"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limit hit - skipping test")
        
        assert response.status_code == 200
        
        # Check MongoDB for the benefit record
        async def check_benefit():
            client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
            db = client['creatorstudio_production']
            
            benefit = await db.first_time_benefits.find_one({"device_token": device_token})
            return benefit
        
        benefit = asyncio.run(check_benefit())
        
        assert benefit is not None, f"Benefit record not found for device_token={device_token}"
        assert "device_token" in benefit, "Benefit missing device_token field"
        assert "ip_hash" in benefit, "Benefit missing ip_hash field"
        assert "user_id" in benefit, "Benefit missing user_id field"
        assert "benefit_session_id" in benefit, "Benefit missing benefit_session_id field"
        assert "created_at" in benefit, "Benefit missing created_at field"
        
        assert benefit["device_token"] == device_token, f"device_token mismatch"
        assert benefit["benefit_session_id"] == session_id, f"benefit_session_id mismatch"
        
        print(f"SUCCESS: Benefit stored with all multi-signal fields: device_token={device_token[:20]}..., ip_hash={benefit['ip_hash']}, user_id={benefit['user_id']}")


class TestIPSecondarySignal:
    """Tests for IP as secondary signal"""
    
    def test_new_device_same_ip_blocked(self):
        """Test 7: New device_token but same IP = blocked if benefit exists for that IP"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        device_token_1 = generate_device_token()
        session_id_1 = generate_session_id()
        
        # First request - establishes IP hash in benefits
        response1 = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id_1,
                "device_token": device_token_1,
                "theme": "First device story"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response1.status_code == 429:
            pytest.skip("Rate limit hit - skipping test")
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1.get("allow_free_view") == True, "First device should be free"
        
        # Second request with NEW device_token but same IP
        device_token_2 = generate_device_token()
        session_id_2 = generate_session_id()
        
        response2 = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id_2,
                "device_token": device_token_2,
                "theme": "Second device story"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response2.status_code == 429:
            pytest.skip("Rate limit hit on second request")
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # New device_token but same IP should be blocked (IP is secondary signal)
        assert data2.get("allow_free_view") == False, f"New device but same IP should get allow_free_view=false, got {data2.get('allow_free_view')}"
        print(f"SUCCESS: New device_token but same IP gets allow_free_view=false (IP secondary signal working)")


class TestAuthenticatedUser:
    """Tests for authenticated user flow"""
    
    def test_authenticated_user_with_device_token(self):
        """Test: Authenticated user sends both device_token and Authorization header"""
        device_token = generate_device_token()
        session_id = generate_session_id()
        
        # Login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test@visionary-suite.com",
                "password": "Test@2026#"
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if login_response.status_code != 200:
            pytest.skip("Could not login - skipping authenticated test")
        
        auth_token = login_response.json().get("token")
        
        # Make request with both device_token and auth
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id,
                "device_token": device_token,
                "theme": "Authenticated user story"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            },
            timeout=30
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limit hit - skipping test")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should still work with auth header
        assert "allow_free_view" in data, "Response missing allow_free_view"
        print(f"SUCCESS: Authenticated user request works, allow_free_view={data['allow_free_view']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
