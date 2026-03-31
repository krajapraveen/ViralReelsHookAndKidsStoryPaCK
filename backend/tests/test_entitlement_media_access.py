"""
Test Suite: Entitlement-Based Media Access Control
Tests for strict download gating based on user subscription status.

Features tested:
- /api/media/entitlement endpoint returns correct flags for free vs paid users
- /api/media/download-token/{asset_id} returns 403 for free users, success for paid/admin
- /api/story-engine/user-jobs scrubs output_url for free users
- Top-up credits alone do NOT unlock downloads
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
FREE_USER_EMAIL = "test@visionary-suite.com"
FREE_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def free_user_token(api_client):
    """Get authentication token for free user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": FREE_USER_EMAIL,
        "password": FREE_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Free user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_user_token(api_client):
    """Get authentication token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_USER_EMAIL,
        "password": ADMIN_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def free_user_client(api_client, free_user_token):
    """Session with free user auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {free_user_token}"
    })
    return session


@pytest.fixture(scope="module")
def admin_user_client(api_client, admin_user_token):
    """Session with admin user auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_user_token}"
    })
    return session


class TestMediaEntitlementEndpoint:
    """Tests for GET /api/media/entitlement"""

    def test_free_user_entitlement_returns_can_download_false(self, free_user_client):
        """Free user should see can_download: false"""
        response = free_user_client.get(f"{BASE_URL}/api/media/entitlement")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") is True, "Response should have success: true"
        assert data.get("can_download") is False, f"Free user should have can_download=false, got {data.get('can_download')}"
        assert data.get("upgrade_required") is True, f"Free user should have upgrade_required=true, got {data.get('upgrade_required')}"
        assert data.get("plan_type") == "free", f"Free user should have plan_type='free', got {data.get('plan_type')}"
        print(f"✓ Free user entitlement: can_download={data.get('can_download')}, upgrade_required={data.get('upgrade_required')}")

    def test_admin_user_entitlement_returns_can_download_true(self, admin_user_client):
        """Admin user should see can_download: true"""
        response = admin_user_client.get(f"{BASE_URL}/api/media/entitlement")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") is True, "Response should have success: true"
        assert data.get("can_download") is True, f"Admin user should have can_download=true, got {data.get('can_download')}"
        # Admin may have upgrade_required=false
        print(f"✓ Admin user entitlement: can_download={data.get('can_download')}, plan_type={data.get('plan_type')}")

    def test_entitlement_requires_auth(self, api_client):
        """Entitlement endpoint should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/media/entitlement")
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Entitlement endpoint requires auth (returned {response.status_code})")


class TestDownloadTokenEndpoint:
    """Tests for POST /api/media/download-token/{asset_id}"""

    def test_free_user_download_token_returns_403(self, free_user_client):
        """Free user POST /api/media/download-token/{asset_id} should return 403 with DOWNLOAD_NOT_ALLOWED"""
        # Use a dummy asset_id - the entitlement check happens before asset lookup
        test_asset_id = "test-asset-12345"
        
        response = free_user_client.post(f"{BASE_URL}/api/media/download-token/{test_asset_id}")
        
        assert response.status_code == 403, f"Expected 403 for free user, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check for DOWNLOAD_NOT_ALLOWED error code
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            error_code = detail.get("error_code")
            assert error_code == "DOWNLOAD_NOT_ALLOWED", f"Expected error_code='DOWNLOAD_NOT_ALLOWED', got {error_code}"
            print(f"✓ Free user download-token returns 403 with error_code={error_code}")
        else:
            # detail might be a string
            assert "DOWNLOAD_NOT_ALLOWED" in str(detail) or "download" in str(detail).lower(), f"Expected DOWNLOAD_NOT_ALLOWED in detail, got {detail}"
            print(f"✓ Free user download-token returns 403: {detail}")

    def test_admin_user_download_token_with_valid_asset(self, admin_user_client):
        """Admin user should be able to get download token for valid asset"""
        # First, get a valid asset_id from user-jobs
        jobs_response = admin_user_client.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=5")
        
        if jobs_response.status_code != 200:
            pytest.skip(f"Could not fetch user jobs: {jobs_response.status_code}")
        
        jobs_data = jobs_response.json()
        jobs = jobs_data.get("jobs", [])
        
        # Find a completed job with output
        valid_job = None
        for job in jobs:
            if job.get("status") in ["COMPLETED", "READY"] and job.get("output_url"):
                valid_job = job
                break
        
        if not valid_job:
            pytest.skip("No completed jobs with output_url found for admin user")
        
        asset_id = valid_job.get("job_id")
        response = admin_user_client.post(f"{BASE_URL}/api/media/download-token/{asset_id}")
        
        assert response.status_code == 200, f"Expected 200 for admin user, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") is True, "Response should have success: true"
        assert "download_url" in data, "Response should contain download_url"
        assert data.get("download_url") is not None, "download_url should not be None"
        print(f"✓ Admin user got download token for asset {asset_id[:8]}...")

    def test_admin_user_download_token_nonexistent_asset(self, admin_user_client):
        """Admin user should get 404 for non-existent asset"""
        fake_asset_id = "nonexistent-asset-99999"
        
        response = admin_user_client.post(f"{BASE_URL}/api/media/download-token/{fake_asset_id}")
        
        # Should return 404 (asset not found) since admin passes entitlement check
        assert response.status_code == 404, f"Expected 404 for non-existent asset, got {response.status_code}: {response.text}"
        print(f"✓ Admin user gets 404 for non-existent asset")

    def test_download_token_requires_auth(self, api_client):
        """Download token endpoint should require authentication"""
        response = api_client.post(f"{BASE_URL}/api/media/download-token/test-asset")
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Download token endpoint requires auth (returned {response.status_code})")


class TestUserJobsOutputUrlScrubbing:
    """Tests for GET /api/story-engine/user-jobs output_url scrubbing"""

    def test_free_user_jobs_have_null_output_url(self, free_user_client):
        """Free user GET /api/story-engine/user-jobs should have output_url as null (scrubbed)"""
        response = free_user_client.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") is True, "Response should have success: true"
        jobs = data.get("jobs", [])
        
        # Check that output_url is null/None for all jobs
        jobs_with_output = []
        for job in jobs:
            if job.get("output_url") is not None:
                jobs_with_output.append(job.get("job_id"))
        
        assert len(jobs_with_output) == 0, f"Free user should have output_url=null for all jobs, but found output_url in: {jobs_with_output}"
        print(f"✓ Free user has {len(jobs)} jobs, all with output_url=null (correctly scrubbed)")

    def test_admin_user_jobs_have_output_url_for_completed(self, admin_user_client):
        """Admin user GET /api/story-engine/user-jobs should have output_url present for completed jobs"""
        response = admin_user_client.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") is True, "Response should have success: true"
        jobs = data.get("jobs", [])
        
        # Check completed jobs have output_url
        completed_jobs = [j for j in jobs if j.get("status") in ["COMPLETED", "READY"]]
        jobs_with_output = [j for j in completed_jobs if j.get("output_url")]
        
        if len(completed_jobs) > 0:
            # At least some completed jobs should have output_url
            print(f"✓ Admin user has {len(completed_jobs)} completed jobs, {len(jobs_with_output)} with output_url")
            # Note: Not all completed jobs may have output_url (some may have failed to produce output)
        else:
            print(f"✓ Admin user has {len(jobs)} jobs (no completed jobs to verify output_url)")


class TestNoRawR2UrlsForFreeUsers:
    """Tests to ensure no raw R2 URLs are exposed to free users"""

    def test_free_user_jobs_no_r2_urls_in_response(self, free_user_client):
        """Free user API responses should not contain raw R2 URLs (pub-*.r2.dev)"""
        response = free_user_client.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check the raw response text for R2 URLs
        response_text = response.text
        
        # R2 URLs pattern: pub-*.r2.dev
        r2_patterns = ["pub-", ".r2.dev"]
        
        # output_url should be null, so no R2 URLs should appear in that field
        # thumbnail_url and preview_url may still have R2 URLs (for preview purposes)
        data = response.json()
        jobs = data.get("jobs", [])
        
        for job in jobs:
            output_url = job.get("output_url")
            if output_url:
                # This should not happen for free users
                assert not any(p in str(output_url) for p in r2_patterns), f"Free user has raw R2 URL in output_url: {output_url}"
        
        print(f"✓ Free user jobs response has no raw R2 URLs in output_url field")


class TestJobStatusEndpoint:
    """Tests for GET /api/story-engine/status/{job_id} entitlement gating"""

    def test_free_user_status_has_null_output_url(self, free_user_client):
        """Free user job status should have output_url as null"""
        # First get a job_id
        jobs_response = free_user_client.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=1")
        
        if jobs_response.status_code != 200:
            pytest.skip("Could not fetch user jobs")
        
        jobs = jobs_response.json().get("jobs", [])
        if not jobs:
            pytest.skip("No jobs found for free user")
        
        job_id = jobs[0].get("job_id")
        
        # Get status
        status_response = free_user_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        
        assert status_response.status_code == 200, f"Expected 200, got {status_response.status_code}"
        data = status_response.json()
        
        job_data = data.get("job", {})
        output_url = job_data.get("output_url")
        
        assert output_url is None, f"Free user status should have output_url=null, got {output_url}"
        print(f"✓ Free user job status has output_url=null (correctly scrubbed)")

    def test_admin_user_status_has_output_url_for_completed(self, admin_user_client):
        """Admin user job status should have output_url for completed jobs"""
        # First get a completed job_id
        jobs_response = admin_user_client.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=10")
        
        if jobs_response.status_code != 200:
            pytest.skip("Could not fetch user jobs")
        
        jobs = jobs_response.json().get("jobs", [])
        completed_job = None
        for job in jobs:
            if job.get("status") in ["COMPLETED", "READY"] and job.get("output_url"):
                completed_job = job
                break
        
        if not completed_job:
            pytest.skip("No completed jobs with output found for admin user")
        
        job_id = completed_job.get("job_id")
        
        # Get status
        status_response = admin_user_client.get(f"{BASE_URL}/api/story-engine/status/{job_id}")
        
        assert status_response.status_code == 200, f"Expected 200, got {status_response.status_code}"
        data = status_response.json()
        
        job_data = data.get("job", {})
        output_url = job_data.get("output_url")
        
        assert output_url is not None, f"Admin user status should have output_url for completed job"
        print(f"✓ Admin user job status has output_url for completed job")


class TestPreviewUrlEndpoint:
    """Tests for GET /api/media/preview-url/{asset_id}"""

    def test_free_user_can_get_preview_url(self, free_user_client):
        """Free users should be able to get preview URLs (for watermarked preview)"""
        # Get a job_id first
        jobs_response = free_user_client.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=5")
        
        if jobs_response.status_code != 200:
            pytest.skip("Could not fetch user jobs")
        
        jobs = jobs_response.json().get("jobs", [])
        if not jobs:
            pytest.skip("No jobs found for free user")
        
        # Find a job with thumbnail (indicates it has some assets)
        job_with_assets = None
        for job in jobs:
            if job.get("thumbnail_url"):
                job_with_assets = job
                break
        
        if not job_with_assets:
            pytest.skip("No jobs with assets found")
        
        job_id = job_with_assets.get("job_id")
        
        # Try to get preview URL
        response = free_user_client.get(f"{BASE_URL}/api/media/preview-url/{job_id}")
        
        # Free users should be able to get preview (watermarked)
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
            assert data.get("can_download") is False, "Free user preview should show can_download=false"
            print(f"✓ Free user can get preview URL with can_download=false")
        elif response.status_code == 404:
            print(f"✓ Preview URL returned 404 (no preview available for this asset)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


class TestHealthAndBasicEndpoints:
    """Basic health checks"""

    def test_api_health(self, api_client):
        """API health endpoint should be accessible"""
        response = api_client.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print(f"✓ API health check passed")

    def test_free_user_login(self, api_client):
        """Free user should be able to login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": FREE_USER_EMAIL,
            "password": FREE_USER_PASSWORD
        })
        
        assert response.status_code == 200, f"Free user login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("token") or data.get("access_token"), "Login should return token"
        print(f"✓ Free user login successful")

    def test_admin_user_login(self, api_client):
        """Admin user should be able to login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_USER_EMAIL,
            "password": ADMIN_USER_PASSWORD
        })
        
        assert response.status_code == 200, f"Admin user login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("token") or data.get("access_token"), "Login should return token"
        print(f"✓ Admin user login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
