"""
Iteration 290 Tests: Server-Side Upload Proxy + Story Chain Model

FEATURES TESTED:
1. POST /api/storage/upload — server-side proxy upload (no CORS issues)
2. POST /api/storage/upload — rejects non-image files
3. POST /api/storage/upload — rejects files over 15MB
4. GET /api/photo-to-comic/my-chains — returns user's story chains
5. GET /api/photo-to-comic/chain/{chain_id} — returns full chain tree
6. Story chain data model validation
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def test_user_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Could not authenticate test user: {response.status_code}")


@pytest.fixture(scope="module")
def admin_user_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_USER_EMAIL, "password": ADMIN_USER_PASSWORD},
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Could not authenticate admin user: {response.status_code}")


@pytest.fixture
def auth_headers(test_user_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def admin_headers(admin_user_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_user_token}"}


# ─── Server-Side Upload Proxy Tests ─────────────────────────────────────────


class TestServerSideUploadProxy:
    """Tests for POST /api/storage/upload — server-side proxy upload"""

    def test_upload_valid_image_file(self, auth_headers):
        """Test uploading a valid image file via server-side proxy"""
        # Create a small valid PNG image
        from io import BytesIO
        
        # PNG header
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 pixel
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0x0F, 0x00, 0x00,
            0x01, 0x01, 0x01, 0x00, 0x18, 0xDD, 0x8D, 0xB4,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,  # IEND chunk
            0xAE, 0x42, 0x60, 0x82
        ])
        
        files = {"file": ("test_image.png", BytesIO(png_data), "image/png")}
        
        response = requests.post(
            f"{BASE_URL}/api/storage/upload",
            headers=auth_headers,
            files=files,
        )
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.text[:500] if response.text else 'empty'}")
        
        # Should succeed with 200 and return storage_key + public_url
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        assert "storage_key" in data
        assert "public_url" in data
        print(f"✓ Upload returned storage_key: {data['storage_key'][:30]}...")

    def test_upload_rejects_non_image_files(self, auth_headers):
        """Test that non-image files are rejected with 400"""
        # Create a text file
        text_content = b"This is not an image file"
        files = {"file": ("test.txt", io.BytesIO(text_content), "text/plain")}
        
        response = requests.post(
            f"{BASE_URL}/api/storage/upload",
            headers=auth_headers,
            files=files,
        )
        
        print(f"Non-image upload response: {response.status_code}")
        
        # Should reject with 400
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Non-image file correctly rejected")

    def test_upload_rejects_files_over_15mb(self, auth_headers):
        """Test that files over 15MB are rejected with 400"""
        # Create a large file (16MB of zeros with PNG header to pass type check)
        large_content = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A  # PNG signature only
        ]) + b"\x00" * (16 * 1024 * 1024)
        
        files = {"file": ("large_image.png", io.BytesIO(large_content), "image/png")}
        
        response = requests.post(
            f"{BASE_URL}/api/storage/upload",
            headers=auth_headers,
            files=files,
        )
        
        print(f"Large file upload response: {response.status_code}")
        
        # Should reject with 400 (file too large)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "large" in response.text.lower() or "15" in response.text
        print("✓ Large file correctly rejected")

    def test_upload_requires_authentication(self):
        """Test that upload requires authentication"""
        text_content = b"test content"
        files = {"file": ("test.png", io.BytesIO(text_content), "image/png")}
        
        response = requests.post(
            f"{BASE_URL}/api/storage/upload",
            files=files,
        )
        
        print(f"No auth upload response: {response.status_code}")
        
        # Should reject with 401 or 403
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
        print("✓ Upload requires authentication")


# ─── Story Chain Endpoints Tests ────────────────────────────────────────────


class TestStoryChainEndpoints:
    """Tests for Story Chain API endpoints"""

    def test_my_chains_endpoint_returns_chains_list(self, auth_headers):
        """Test GET /my-chains returns user's story chains"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/my-chains",
            headers=auth_headers,
        )
        
        print(f"My chains response: {response.status_code}")
        print(f"My chains data: {response.text[:500] if response.text else 'empty'}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "chains" in data
        assert isinstance(data["chains"], list)
        assert "total" in data
        
        # If there are chains, verify structure
        if len(data["chains"]) > 0:
            chain = data["chains"][0]
            # Should have chain metadata
            assert "chain_id" in chain
            assert "total_episodes" in chain
            assert "continuations" in chain or chain.get("continuations") == 0
            assert "remixes" in chain or chain.get("remixes") == 0
            print(f"✓ My chains returned {len(data['chains'])} chains with proper structure")
        else:
            print("✓ My chains returned empty list (no chains yet)")

    def test_my_chains_includes_episode_counts(self, auth_headers):
        """Test that my-chains response includes episode counts and branch info"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/my-chains",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Even empty response should have proper structure
        for chain in data.get("chains", []):
            assert "total_episodes" in chain
            # Continuations and remixes should be numeric
            assert isinstance(chain.get("continuations", 0), int)
            assert isinstance(chain.get("remixes", 0), int)
            
        print(f"✓ Chain metadata includes episode counts")

    def test_chain_detail_returns_404_for_nonexistent(self, auth_headers):
        """Test GET /chain/{chain_id} returns 404 for nonexistent chain"""
        fake_chain_id = "nonexistent-chain-id-12345"
        
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/chain/{fake_chain_id}",
            headers=auth_headers,
        )
        
        print(f"Nonexistent chain response: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Chain endpoint returns 404 for nonexistent chain")

    def test_chain_detail_requires_authentication(self):
        """Test that chain endpoints require authentication"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/chain/test-chain-id",
        )
        
        assert response.status_code in [401, 403, 422]
        print("✓ Chain endpoint requires authentication")

    def test_my_chains_requires_authentication(self):
        """Test that my-chains requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/my-chains",
        )
        
        assert response.status_code in [401, 403, 422]
        print("✓ My-chains endpoint requires authentication")


# ─── Story Chain Data Model Tests ───────────────────────────────────────────


class TestStoryChainDataModel:
    """Tests for story chain data model fields in jobs"""

    def test_job_status_includes_chain_fields_after_generation(self, auth_headers):
        """Test that job status includes chain fields if job exists"""
        # First get history to find an existing job
        history_response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history",
            headers=auth_headers,
        )
        
        if history_response.status_code != 200:
            pytest.skip("No history available")
            
        data = history_response.json()
        jobs = data.get("jobs", [])
        
        if not jobs:
            pytest.skip("No existing jobs to check chain fields")
        
        # Get first completed job
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        if not completed_jobs:
            pytest.skip("No completed jobs to check")
            
        job = completed_jobs[0]
        job_id = job.get("id")
        
        # Get job detail
        job_response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/{job_id}",
            headers=auth_headers,
        )
        
        assert job_response.status_code == 200
        job_data = job_response.json()
        
        # Chain fields should be present (after backfill or creation)
        # Note: Old jobs may not have chain fields until backfill runs
        print(f"Job data keys: {list(job_data.keys())}")
        
        # If chain fields exist, validate them
        if "story_chain_id" in job_data:
            assert job_data["story_chain_id"]  # Should not be empty
            print(f"✓ Job has story_chain_id: {job_data['story_chain_id'][:20]}...")
            
            if "branch_type" in job_data:
                assert job_data["branch_type"] in ["original", "continuation", "remix"]
                print(f"✓ Job has valid branch_type: {job_data['branch_type']}")
        else:
            print("ℹ Job doesn't have chain fields yet (may need backfill)")

    def test_chain_backfill_on_my_chains_call(self, auth_headers):
        """Test that calling my-chains triggers backfill for old jobs"""
        # First call my-chains
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/my-chains",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Backfill should have run
        # Check history to see if jobs have chain fields
        history_response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history?size=5",
            headers=auth_headers,
        )
        
        if history_response.status_code == 200:
            jobs = history_response.json().get("jobs", [])
            for job in jobs:
                # After backfill, jobs should have chain IDs
                if job.get("story_chain_id"):
                    print(f"✓ Job {job.get('id', '')[:8]} has chain_id after my-chains call")
                    return
        
        print("ℹ No jobs with chain fields found (may be new user)")


# ─── Continue Story Chain Tests ─────────────────────────────────────────────


class TestContinueStoryAssignsChainFields:
    """Tests for continue-story endpoint chain field assignment"""

    def test_continue_story_validates_parent_exists(self, auth_headers):
        """Test continue-story returns 404 for nonexistent parent"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/continue-story",
            headers=auth_headers,
            json={
                "parentJobId": "nonexistent-job-id-12345",
                "prompt": "Continue the story",
                "panelCount": 4,
                "keepStyle": True,
            },
        )
        
        print(f"Continue story response: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Continue-story returns 404 for nonexistent parent")

    def test_continue_story_requires_strip_mode(self, auth_headers):
        """Test continue-story only works with strip mode jobs"""
        # Get history to find an avatar job
        history_response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history",
            headers=auth_headers,
        )
        
        if history_response.status_code != 200:
            pytest.skip("No history available")
            
        jobs = history_response.json().get("jobs", [])
        avatar_jobs = [j for j in jobs if j.get("mode") == "avatar" and j.get("status") == "COMPLETED"]
        
        if not avatar_jobs:
            pytest.skip("No avatar jobs to test with")
            
        avatar_job = avatar_jobs[0]
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/continue-story",
            headers=auth_headers,
            json={
                "parentJobId": avatar_job["id"],
                "prompt": "Continue",
                "panelCount": 4,
            },
        )
        
        print(f"Continue avatar job response: {response.status_code}")
        
        # Should fail with 400 (avatar mode doesn't support continuation)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Continue-story rejects avatar mode jobs")


# ─── Existing Endpoints Regression Tests ────────────────────────────────────


class TestExistingEndpointsRegression:
    """Ensure existing endpoints still work after changes"""

    def test_styles_endpoint(self, auth_headers):
        """Test GET /styles still works"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/styles",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        assert "pricing" in data
        print(f"✓ Styles endpoint returns {len(data['styles'])} styles")

    def test_pricing_endpoint(self, auth_headers):
        """Test GET /pricing still works"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/pricing",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        pricing = data["pricing"]
        assert "comic_avatar" in pricing
        assert "comic_strip" in pricing
        print("✓ Pricing endpoint returns correct structure")

    def test_history_endpoint(self, auth_headers):
        """Test GET /history still works"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        print(f"✓ History endpoint returns {data['total']} total jobs")

    def test_diagnostic_endpoint(self, auth_headers):
        """Test GET /diagnostic still works"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/diagnostic",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "llm_status" in data
        print("✓ Diagnostic endpoint returns system health info")

    def test_job_not_found(self, auth_headers):
        """Test GET /job/{id} returns 404 for invalid ID"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/invalid-job-id-12345",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        print("✓ Job endpoint returns 404 for invalid ID")


# ─── Credits and Auth Tests ─────────────────────────────────────────────────


class TestCreditsAndAuth:
    """Basic credits and auth tests"""

    def test_credits_balance(self, auth_headers):
        """Test GET /credits/balance returns numeric credits"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert isinstance(data["credits"], (int, float))
        print(f"✓ Credits balance: {data['credits']}")

    def test_auth_me(self, auth_headers):
        """Test GET /auth/me returns user info"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data or "id" in data or "email" in data
        print("✓ Auth me endpoint returns user info")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
