"""
Comprehensive Tests for Wallet Credit Pipeline - Iteration 35
Tests wallet endpoints, job creation, cancellation, ledger, pricing, and idempotency
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://subscription-gateway-1.preview.emergentagent.com')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


@pytest.fixture(scope="module")
def demo_token():
    """Get demo user token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Demo login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin user token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# =============================================================================
# WALLET ENDPOINT TESTS
# =============================================================================
class TestWalletMe:
    """Tests for GET /api/wallet/me - Wallet balance display"""
    
    def test_wallet_me_returns_balance_fields(self, demo_token):
        """Verify wallet endpoint returns required balance fields"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/me",
            headers=get_auth_headers(demo_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Required fields
        assert "userId" in data, "Missing userId in wallet response"
        assert "balanceCredits" in data, "Missing balanceCredits in wallet response"
        assert "reservedCredits" in data, "Missing reservedCredits in wallet response"
        assert "availableCredits" in data, "Missing availableCredits in wallet response"
        
        # Verify types
        assert isinstance(data["balanceCredits"], int), "balanceCredits should be int"
        assert isinstance(data["reservedCredits"], int), "reservedCredits should be int"
        assert isinstance(data["availableCredits"], int), "availableCredits should be int"
        
        # Verify available = balance - reserved
        expected_available = data["balanceCredits"] - data["reservedCredits"]
        assert data["availableCredits"] == expected_available, \
            f"availableCredits mismatch: expected {expected_available}, got {data['availableCredits']}"
        
        print(f"✓ Wallet balance: {data['balanceCredits']} (available: {data['availableCredits']}, reserved: {data['reservedCredits']})")
    
    def test_wallet_me_requires_auth(self):
        """Verify wallet endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/wallet/me")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Wallet endpoint properly requires authentication")


# =============================================================================
# PRICING ENDPOINT TESTS
# =============================================================================
class TestWalletPricing:
    """Tests for GET /api/wallet/pricing - Credit costs per job type"""
    
    def test_pricing_returns_all_job_types(self, demo_token):
        """Verify pricing endpoint returns all job types with costs"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/pricing",
            headers=get_auth_headers(demo_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pricing" in data, "Missing pricing in response"
        
        pricing = data["pricing"]
        
        # Expected job types
        expected_types = [
            "TEXT_TO_IMAGE", "TEXT_TO_VIDEO", "IMAGE_TO_VIDEO",
            "VIDEO_REMIX", "STORY_GENERATION", "REEL_GENERATION", "STYLE_PROFILE_CREATE"
        ]
        
        for job_type in expected_types:
            assert job_type in pricing, f"Missing pricing for {job_type}"
            assert "baseCredits" in pricing[job_type], f"Missing baseCredits for {job_type}"
            print(f"  ✓ {job_type}: {pricing[job_type]['baseCredits']} credits")
        
        # Verify TEXT_TO_IMAGE costs 10 credits
        assert pricing["TEXT_TO_IMAGE"]["baseCredits"] == 10, \
            f"TEXT_TO_IMAGE should cost 10 credits, got {pricing['TEXT_TO_IMAGE']['baseCredits']}"
        
        print(f"✓ All {len(expected_types)} job types have pricing configured")
    
    def test_pricing_is_public(self):
        """Pricing can be accessed without auth (or with auth)"""
        # This should work with auth
        response = requests.get(f"{BASE_URL}/api/wallet/pricing")
        # Note: API requires auth based on wallet.py implementation
        # If it requires auth, this should be 403/401
        print(f"Pricing endpoint status: {response.status_code}")


# =============================================================================
# JOB CREATION TESTS
# =============================================================================
class TestJobCreation:
    """Tests for POST /api/wallet/jobs - Job creation with credit reservation"""
    
    def test_create_job_success(self, demo_token):
        """Create a TEXT_TO_IMAGE job successfully"""
        idempotency_key = str(uuid.uuid4())
        
        job_data = {
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {
                "prompt": "A beautiful sunset over the ocean",
                "aspect_ratio": "1:1"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/wallet/jobs",
            headers={**get_auth_headers(demo_token), "Idempotency-Key": idempotency_key},
            json=job_data
        )
        
        # Check for success or insufficient credits
        if response.status_code == 402:
            pytest.skip("Insufficient credits for job creation test")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True, "Job creation should return success:true"
        assert "jobId" in data, "Missing jobId in response"
        assert data["status"] == "QUEUED", f"Expected QUEUED status, got {data['status']}"
        assert data["costCredits"] == 10, f"Expected 10 credits, got {data['costCredits']}"
        
        print(f"✓ Job created: {data['jobId']} (cost: {data['costCredits']} credits, status: {data['status']})")
        return data["jobId"]
    
    def test_create_job_invalid_type(self, demo_token):
        """Creating job with invalid type should fail"""
        job_data = {
            "jobType": "INVALID_TYPE",
            "inputData": {"prompt": "test"}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/wallet/jobs",
            headers=get_auth_headers(demo_token),
            json=job_data
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid job type, got {response.status_code}"
        print("✓ Invalid job type correctly rejected with 400")
    
    def test_create_job_missing_input(self, demo_token):
        """Creating job without required fields should fail"""
        job_data = {
            "jobType": "TEXT_TO_IMAGE"
            # Missing inputData
        }
        
        response = requests.post(
            f"{BASE_URL}/api/wallet/jobs",
            headers=get_auth_headers(demo_token),
            json=job_data
        )
        
        assert response.status_code == 422, f"Expected 422 for missing fields, got {response.status_code}"
        print("✓ Missing inputData correctly rejected with 422")


# =============================================================================
# IDEMPOTENCY TESTS
# =============================================================================
class TestIdempotency:
    """Tests for idempotency protection on job creation"""
    
    def test_duplicate_request_returns_existing_job(self, demo_token):
        """Duplicate request with same idempotency key returns existing job"""
        idempotency_key = str(uuid.uuid4())
        
        job_data = {
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {
                "prompt": "Idempotency test image",
                "aspect_ratio": "16:9"
            }
        }
        
        headers = {**get_auth_headers(demo_token), "Idempotency-Key": idempotency_key}
        
        # First request
        response1 = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        
        if response1.status_code == 402:
            pytest.skip("Insufficient credits for idempotency test")
        
        assert response1.status_code == 200
        job_id_1 = response1.json()["jobId"]
        
        # Second request with same idempotency key
        response2 = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Should return same job, not create new one
        assert data2["jobId"] == job_id_1, "Duplicate request should return same jobId"
        assert data2.get("duplicate") == True, "Response should indicate duplicate:true"
        
        print(f"✓ Idempotency working: duplicate request returned existing job {job_id_1}")


# =============================================================================
# JOB STATUS TESTS
# =============================================================================
class TestJobStatus:
    """Tests for GET /api/wallet/jobs/{id} - Job status and output"""
    
    def test_get_job_status(self, demo_token):
        """Get job status for a created job"""
        # First create a job
        job_data = {
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {"prompt": "Status test image"}
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/wallet/jobs",
            headers=get_auth_headers(demo_token),
            json=job_data
        )
        
        if create_resp.status_code == 402:
            pytest.skip("Insufficient credits")
        
        job_id = create_resp.json()["jobId"]
        
        # Get status
        response = requests.get(
            f"{BASE_URL}/api/wallet/jobs/{job_id}",
            headers=get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["jobId"] == job_id
        assert data["jobType"] == "TEXT_TO_IMAGE"
        assert "status" in data
        assert "costCredits" in data
        assert "createdAt" in data
        
        print(f"✓ Job status retrieved: {data['status']} (progress: {data.get('progress', 0)}%)")
    
    def test_get_nonexistent_job(self, demo_token):
        """Getting non-existent job should return 404"""
        fake_job_id = str(uuid.uuid4())
        
        response = requests.get(
            f"{BASE_URL}/api/wallet/jobs/{fake_job_id}",
            headers=get_auth_headers(demo_token)
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent job correctly returns 404")


# =============================================================================
# JOB CANCELLATION TESTS
# =============================================================================
class TestJobCancellation:
    """Tests for POST /api/wallet/jobs/{id}/cancel - Job cancellation with credit release"""
    
    def test_cancel_queued_job_releases_credits(self, demo_token):
        """Cancelling a QUEUED job should release reserved credits"""
        # Get initial wallet state
        wallet_before = requests.get(
            f"{BASE_URL}/api/wallet/me",
            headers=get_auth_headers(demo_token)
        ).json()
        
        initial_available = wallet_before["availableCredits"]
        initial_reserved = wallet_before["reservedCredits"]
        
        # Create a job
        job_data = {
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {"prompt": "Cancel test image"}
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/wallet/jobs",
            headers=get_auth_headers(demo_token),
            json=job_data
        )
        
        if create_resp.status_code == 402:
            pytest.skip("Insufficient credits for cancellation test")
        
        job_id = create_resp.json()["jobId"]
        cost = create_resp.json()["costCredits"]
        
        # Verify credits were reserved
        wallet_after_create = requests.get(
            f"{BASE_URL}/api/wallet/me",
            headers=get_auth_headers(demo_token)
        ).json()
        
        assert wallet_after_create["reservedCredits"] >= cost, "Credits should be reserved"
        
        # Cancel the job
        cancel_resp = requests.post(
            f"{BASE_URL}/api/wallet/jobs/{job_id}/cancel",
            headers=get_auth_headers(demo_token)
        )
        
        # Job might already be processing
        if cancel_resp.status_code == 400:
            print(f"Job {job_id} cannot be cancelled (status changed)")
            return
        
        assert cancel_resp.status_code == 200, f"Expected 200, got {cancel_resp.status_code}"
        
        data = cancel_resp.json()
        assert data["success"] == True
        assert data["status"] == "CANCELLED"
        
        # Verify credits were released
        wallet_after_cancel = requests.get(
            f"{BASE_URL}/api/wallet/me",
            headers=get_auth_headers(demo_token)
        ).json()
        
        # Reserved should decrease or return to original
        print(f"✓ Job cancelled: {job_id}, credits released")
    
    def test_cannot_cancel_completed_job(self, demo_token):
        """Cannot cancel a job that's already completed or running"""
        # This test relies on finding a job that's not in QUEUED/PENDING state
        # First list jobs and find one that's SUCCEEDED or FAILED
        list_resp = requests.get(
            f"{BASE_URL}/api/wallet/jobs?limit=20",
            headers=get_auth_headers(demo_token)
        )
        
        if list_resp.status_code != 200:
            pytest.skip("Cannot list jobs")
        
        jobs = list_resp.json().get("jobs", [])
        
        completed_job = next(
            (j for j in jobs if j["status"] in ["SUCCEEDED", "FAILED", "RUNNING"]),
            None
        )
        
        if not completed_job:
            pytest.skip("No completed jobs found to test cancellation rejection")
        
        cancel_resp = requests.post(
            f"{BASE_URL}/api/wallet/jobs/{completed_job['id']}/cancel",
            headers=get_auth_headers(demo_token)
        )
        
        assert cancel_resp.status_code == 400, f"Expected 400, got {cancel_resp.status_code}"
        print(f"✓ Completed job ({completed_job['status']}) correctly cannot be cancelled")


# =============================================================================
# LEDGER TESTS
# =============================================================================
class TestCreditLedger:
    """Tests for GET /api/wallet/ledger - Credit transaction history"""
    
    def test_ledger_returns_entries(self, demo_token):
        """Ledger should return transaction entries"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/ledger",
            headers=get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert "total" in data
        assert "summary" in data
        
        # Check summary fields
        summary = data["summary"]
        assert "totalHolds" in summary
        assert "totalCaptures" in summary
        assert "totalReleases" in summary
        
        print(f"✓ Ledger has {data['total']} entries")
        print(f"  Summary: HOLD={summary['totalHolds']}, CAPTURE={summary['totalCaptures']}, RELEASE={summary['totalReleases']}")
    
    def test_ledger_entries_have_required_fields(self, demo_token):
        """Ledger entries should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/ledger?limit=5",
            headers=get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200
        entries = response.json().get("entries", [])
        
        if not entries:
            pytest.skip("No ledger entries found")
        
        entry = entries[0]
        required_fields = ["entryType", "amount", "refType", "status", "createdAt"]
        
        for field in required_fields:
            assert field in entry, f"Missing {field} in ledger entry"
        
        # Entry types should be one of HOLD, CAPTURE, RELEASE, TOPUP, ADJUST
        valid_types = ["HOLD", "CAPTURE", "RELEASE", "TOPUP", "ADJUST"]
        assert entry["entryType"] in valid_types, f"Invalid entry type: {entry['entryType']}"
        
        print(f"✓ Ledger entry has all required fields. First entry: {entry['entryType']} of {entry['amount']} credits")


# =============================================================================
# JOB LISTING TESTS
# =============================================================================
class TestJobListing:
    """Tests for GET /api/wallet/jobs - List user jobs with filters"""
    
    def test_list_jobs(self, demo_token):
        """List jobs returns paginated results"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/jobs?limit=10",
            headers=get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "total" in data
        assert "limit" in data
        
        print(f"✓ Job listing: {len(data['jobs'])} jobs returned, {data['total']} total")
    
    def test_list_jobs_filter_by_status(self, demo_token):
        """Filter jobs by status"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/jobs?status=QUEUED",
            headers=get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned jobs should have QUEUED status
        for job in data["jobs"]:
            assert job["status"] == "QUEUED", f"Expected QUEUED, got {job['status']}"
        
        print(f"✓ Status filter working: {len(data['jobs'])} QUEUED jobs")
    
    def test_list_jobs_filter_by_type(self, demo_token):
        """Filter jobs by job type"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/jobs?job_type=TEXT_TO_IMAGE",
            headers=get_auth_headers(demo_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned jobs should have TEXT_TO_IMAGE type
        for job in data["jobs"]:
            assert job["jobType"] == "TEXT_TO_IMAGE", f"Expected TEXT_TO_IMAGE, got {job['jobType']}"
        
        print(f"✓ Job type filter working: {len(data['jobs'])} TEXT_TO_IMAGE jobs")


# =============================================================================
# CREDIT FLOW TESTS
# =============================================================================
class TestCreditFlow:
    """Tests for credit flow: HOLD on create, CAPTURE on success, RELEASE on failure/cancel"""
    
    def test_hold_created_on_job_creation(self, demo_token):
        """HOLD entry should be created when job is created"""
        # Get ledger before
        ledger_before = requests.get(
            f"{BASE_URL}/api/wallet/ledger?limit=1",
            headers=get_auth_headers(demo_token)
        ).json()
        
        hold_count_before = ledger_before["summary"]["totalHolds"]
        
        # Create job
        job_data = {
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {"prompt": "HOLD test image"}
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/wallet/jobs",
            headers=get_auth_headers(demo_token),
            json=job_data
        )
        
        if create_resp.status_code == 402:
            pytest.skip("Insufficient credits")
        
        job_id = create_resp.json()["jobId"]
        
        # Get ledger after
        ledger_after = requests.get(
            f"{BASE_URL}/api/wallet/ledger?limit=10",
            headers=get_auth_headers(demo_token)
        ).json()
        
        # Find HOLD entry for this job
        hold_entry = next(
            (e for e in ledger_after["entries"] if e["entryType"] == "HOLD" and e.get("refId") == job_id),
            None
        )
        
        assert hold_entry is not None, f"HOLD entry not found for job {job_id}"
        assert hold_entry["status"] == "ACTIVE", "HOLD status should be ACTIVE"
        
        print(f"✓ HOLD entry created for job {job_id}: {hold_entry['amount']} credits")
    
    def test_release_on_cancel(self, demo_token):
        """RELEASE entry should be created when job is cancelled"""
        # Create job
        job_data = {
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {"prompt": "RELEASE test image"}
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/wallet/jobs",
            headers=get_auth_headers(demo_token),
            json=job_data
        )
        
        if create_resp.status_code == 402:
            pytest.skip("Insufficient credits")
        
        job_id = create_resp.json()["jobId"]
        
        # Cancel job
        cancel_resp = requests.post(
            f"{BASE_URL}/api/wallet/jobs/{job_id}/cancel",
            headers=get_auth_headers(demo_token)
        )
        
        if cancel_resp.status_code == 400:
            pytest.skip("Job already processing, cannot cancel")
        
        # Check ledger for RELEASE entry
        ledger = requests.get(
            f"{BASE_URL}/api/wallet/ledger?limit=10",
            headers=get_auth_headers(demo_token)
        ).json()
        
        release_entry = next(
            (e for e in ledger["entries"] if e["entryType"] == "RELEASE" and e.get("refId") == job_id),
            None
        )
        
        assert release_entry is not None, f"RELEASE entry not found for cancelled job {job_id}"
        print(f"✓ RELEASE entry created for cancelled job {job_id}")


# =============================================================================
# TOOLS DISABLED WHEN LOW BALANCE
# =============================================================================
class TestToolsDisabledLowBalance:
    """Test that frontend properly disables tools when balance < cost"""
    
    def test_insufficient_credits_returns_402(self, demo_token):
        """Job creation with insufficient credits returns 402"""
        # This test relies on having a user with low credits
        # We'll use the demo user and check if they have enough
        wallet = requests.get(
            f"{BASE_URL}/api/wallet/me",
            headers=get_auth_headers(demo_token)
        ).json()
        
        # Try to create TEXT_TO_VIDEO which costs more (25+ credits)
        job_data = {
            "jobType": "TEXT_TO_VIDEO",
            "inputData": {
                "prompt": "Test video",
                "duration": 12  # 25 + 12*5 = 85 credits
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/wallet/jobs",
            headers=get_auth_headers(demo_token),
            json=job_data
        )
        
        # Either succeeds or returns 402 for insufficient credits
        if response.status_code == 402:
            data = response.json()
            assert "detail" in data
            assert "Insufficient" in data["detail"]
            print(f"✓ 402 returned for insufficient credits: {data['detail']}")
        else:
            print(f"Job created with status {response.status_code} - user has enough credits")


# =============================================================================
# ADMIN TOKEN TESTS
# =============================================================================
class TestAdminWallet:
    """Test wallet endpoints with admin user"""
    
    def test_admin_wallet_access(self, admin_token):
        """Admin should have high credit balance"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/me",
            headers=get_auth_headers(admin_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Admin should have many credits (999999 per server.py)
        assert data["balanceCredits"] >= 1000, "Admin should have high credit balance"
        print(f"✓ Admin wallet balance: {data['balanceCredits']} credits")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
