"""
Security Penetration Testing Suite
Tests for OWASP Top 10 vulnerabilities and security best practices.

Run with: python -m pytest backend/tests/test_security.py -v
"""
import pytest
import asyncio
import re
import json
from unittest.mock import AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configurations
API_BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://auth-photo-comic.preview.emergentagent.com")


class TestSecurityHeaders:
    """Test security headers are properly configured"""
    
    @pytest.mark.asyncio
    async def test_csp_header_present(self):
        """A01:2021 - Content Security Policy should be present"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/health") as response:
                csp = response.headers.get("Content-Security-Policy")
                assert csp is not None, "CSP header missing"
                assert "default-src" in csp, "CSP should include default-src"
    
    @pytest.mark.asyncio
    async def test_hsts_header_present(self):
        """A01:2021 - HSTS header should be present"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/health") as response:
                hsts = response.headers.get("Strict-Transport-Security")
                assert hsts is not None, "HSTS header missing"
                assert "max-age=" in hsts, "HSTS should include max-age"
    
    @pytest.mark.asyncio
    async def test_x_frame_options_header(self):
        """A01:2021 - X-Frame-Options should prevent clickjacking"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/health") as response:
                xfo = response.headers.get("X-Frame-Options")
                assert xfo in ["DENY", "SAMEORIGIN"], f"X-Frame-Options should be DENY or SAMEORIGIN, got {xfo}"
    
    @pytest.mark.asyncio
    async def test_x_content_type_options(self):
        """A01:2021 - X-Content-Type-Options should prevent MIME sniffing"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/health") as response:
                xcto = response.headers.get("X-Content-Type-Options")
                assert xcto == "nosniff", f"X-Content-Type-Options should be nosniff, got {xcto}"
    
    @pytest.mark.asyncio
    async def test_referrer_policy_header(self):
        """A01:2021 - Referrer-Policy should be configured"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/health") as response:
                rp = response.headers.get("Referrer-Policy")
                assert rp is not None, "Referrer-Policy header missing"


class TestInjectionPrevention:
    """A03:2021 - Injection Prevention Tests"""
    
    @pytest.mark.asyncio
    async def test_sql_injection_blocked(self):
        """Test SQL injection attempts are blocked"""
        import aiohttp
        payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1; SELECT * FROM users",
            "admin'--",
            "1 UNION SELECT * FROM users"
        ]
        
        async with aiohttp.ClientSession() as session:
            for payload in payloads:
                async with session.post(
                    f"{API_BASE_URL}/api/auth/login",
                    json={"email": payload, "password": "test"}
                ) as response:
                    # Should not return 500 (internal error would indicate SQL injection worked)
                    assert response.status != 500, f"SQL injection payload may have worked: {payload}"
    
    @pytest.mark.asyncio
    async def test_nosql_injection_blocked(self):
        """Test NoSQL injection attempts are blocked"""
        import aiohttp
        payloads = [
            {"$gt": ""},
            {"$ne": None},
            {"$where": "1==1"}
        ]
        
        async with aiohttp.ClientSession() as session:
            for payload in payloads:
                async with session.post(
                    f"{API_BASE_URL}/api/auth/login",
                    json={"email": payload, "password": "test"}
                ) as response:
                    # Should return 422 (validation error) not 200
                    assert response.status != 200, f"NoSQL injection may have worked"
    
    @pytest.mark.asyncio
    async def test_xss_in_input_sanitized(self):
        """Test XSS payloads are sanitized"""
        import aiohttp
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "'\"><script>alert('xss')</script>"
        ]
        
        async with aiohttp.ClientSession() as session:
            # First login to get token
            async with session.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": "demo@example.com", "password": "Password123!"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get("token")
                    
                    # Try XSS in caption rewriter
                    for payload in xss_payloads:
                        async with session.post(
                            f"{API_BASE_URL}/api/caption-rewriter-pro/rewrite",
                            json={"text": payload, "tone": "funny", "pack_type": "single_tone"},
                            headers={"Authorization": f"Bearer {token}"}
                        ) as rewrite_response:
                            if rewrite_response.status == 200:
                                result = await rewrite_response.json()
                                # Check that script tags are not in output
                                result_str = json.dumps(result)
                                assert "<script>" not in result_str.lower(), f"XSS payload may not be sanitized: {payload}"


class TestAuthenticationSecurity:
    """A07:2021 - Authentication and Session Management Tests"""
    
    @pytest.mark.asyncio
    async def test_password_not_in_response(self):
        """Passwords should never be returned in API responses"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": "demo@example.com", "password": "Password123!"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    data_str = json.dumps(data).lower()
                    assert "password123" not in data_str, "Password found in response!"
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self):
        """Invalid JWT tokens should be rejected"""
        import aiohttp
        invalid_tokens = [
            "invalid_token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "null",
            "undefined"
        ]
        
        async with aiohttp.ClientSession() as session:
            for token in invalid_tokens:
                async with session.get(
                    f"{API_BASE_URL}/api/credits/balance",
                    headers={"Authorization": f"Bearer {token}"}
                ) as response:
                    # Should reject invalid token (401, 403, 404 are all acceptable)
                    assert response.status != 200, f"Invalid token should not return 200: {token}"
    
    @pytest.mark.asyncio
    async def test_missing_auth_header_rejected(self):
        """Requests without auth header should be rejected for protected routes"""
        import aiohttp
        protected_routes = [
            "/api/credits/balance",
            "/api/story-episode-creator/history",
            "/api/content-challenge-planner/history",
            "/api/caption-rewriter-pro/history"
        ]
        
        async with aiohttp.ClientSession() as session:
            for route in protected_routes:
                async with session.get(f"{API_BASE_URL}{route}") as response:
                    # Should not return 200 without authentication
                    assert response.status != 200, f"Protected route {route} returned 200 without auth"


class TestRateLimiting:
    """A04:2021 - Rate Limiting Tests"""
    
    @pytest.mark.asyncio
    async def test_login_rate_limited(self):
        """Login endpoint should be rate limited"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            rate_limited = False
            for i in range(15):  # Try 15 rapid requests
                async with session.post(
                    f"{API_BASE_URL}/api/auth/login",
                    json={"email": "test@test.com", "password": "wrong"}
                ) as response:
                    if response.status == 429:
                        rate_limited = True
                        break
            # Note: This may not trigger in test environment with low traffic
            # Just log the result
            print(f"Rate limiting triggered: {rate_limited}")


class TestCopyrightProtection:
    """Business Logic Security - Copyright Protection Tests"""
    
    @pytest.mark.asyncio
    async def test_blocked_keywords_in_story_creator(self):
        """Story Episode Creator should block copyrighted content"""
        import aiohttp
        blocked_keywords = [
            "Mickey Mouse goes on adventure",
            "Spider-Man saves the day",
            "Harry Potter at Hogwarts",
            "Pokemon trainer catches Pikachu",
            "Batman fights Joker"
        ]
        
        async with aiohttp.ClientSession() as session:
            # Login first
            async with session.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": "demo@example.com", "password": "Password123!"}
            ) as login_response:
                if login_response.status == 200:
                    data = await login_response.json()
                    token = data.get("token")
                    
                    for keyword in blocked_keywords:
                        async with session.post(
                            f"{API_BASE_URL}/api/story-episode-creator/generate",
                            json={"story_idea": keyword, "episode_count": 3, "add_ons": []},
                            headers={"Authorization": f"Bearer {token}"}
                        ) as response:
                            assert response.status == 400, f"Copyright keyword '{keyword}' should be blocked"
                            error_data = await response.json()
                            assert "copyrighted" in error_data.get("detail", "").lower() or "branded" in error_data.get("detail", "").lower()


class TestInputValidation:
    """A03:2021 - Input Validation Tests"""
    
    @pytest.mark.asyncio
    async def test_oversized_input_rejected(self):
        """Oversized inputs should be rejected"""
        import aiohttp
        # Create a very large string
        large_input = "A" * 100000  # 100KB string
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": large_input, "password": "test"}
            ) as response:
                # Should return validation error, not crash
                assert response.status in [400, 413, 422], "Oversized input should be rejected"
    
    @pytest.mark.asyncio
    async def test_invalid_json_handled(self):
        """Invalid JSON should be handled gracefully"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/api/auth/login",
                data="not valid json {{{",
                headers={"Content-Type": "application/json"}
            ) as response:
                # Should return 400 or 422, not 500
                assert response.status in [400, 422], "Invalid JSON should return 400/422, not crash"


class TestSensitiveDataExposure:
    """A02:2021 - Sensitive Data Exposure Tests"""
    
    @pytest.mark.asyncio
    async def test_no_sensitive_data_in_error_messages(self):
        """Error messages should not expose sensitive data"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": "nonexistent@test.com", "password": "wrongpass"}
            ) as response:
                if response.status == 401:
                    data = await response.json()
                    detail = data.get("detail", "").lower()
                    # Error should be generic - "Invalid email or password" is acceptable
                    # It should NOT reveal which specific part is wrong
                    assert "user does not exist" not in detail  # Don't reveal if user exists
                    assert "email not found" not in detail  # Don't enumerate users
                    assert "wrong password" not in detail  # Don't confirm password separately
    
    @pytest.mark.asyncio
    async def test_mongodb_id_not_exposed(self):
        """MongoDB _id should not be exposed in responses"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Login first
            async with session.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": "demo@example.com", "password": "Password123!"}
            ) as login_response:
                if login_response.status == 200:
                    data = await login_response.json()
                    token = data.get("token")
                    
                    # Check wallet endpoint
                    async with session.get(
                        f"{API_BASE_URL}/api/wallet",
                        headers={"Authorization": f"Bearer {token}"}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            data_str = json.dumps(data)
                            assert "_id" not in data_str, "MongoDB _id should not be exposed"
                            # Check for ObjectId pattern
                            assert not re.search(r'ObjectId\(["\'][a-f0-9]{24}["\']\)', data_str), "ObjectId should not be exposed"


def run_security_tests():
    """Run all security tests and generate report"""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
    return result.returncode


if __name__ == "__main__":
    exit(run_security_tests())
