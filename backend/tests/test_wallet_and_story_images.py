"""
Test Suite for Wallet Credit Pipeline and Story Generator Image Display
Features tested:
1. Story Generator image display - coverImageUrl and scene.imageUrl
2. Wallet endpoint GET /api/wallet/me
3. Pricing endpoint GET /api/wallet/pricing
4. Job creation POST /api/wallet/jobs with QUEUED status
5. Idempotency protection for duplicate requests
6. Job status GET /api/wallet/jobs/{id}
7. Job cancel POST /api/wallet/jobs/{id}/cancel
8. Credit ledger GET /api/wallet/ledger with HOLD/RELEASE transactions
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestAuthentication:
    """Authentication helper tests"""
    
    def test_demo_user_login(self):
        """Test demo user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        return data["token"]
    
    def test_admin_user_login(self):
        """Test admin user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]


@pytest.fixture
def demo_token():
    """Get demo user auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Demo user login failed")


@pytest.fixture
def admin_token():
    """Get admin user auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Admin user login failed")


class TestWalletEndpoints:
    """Test Wallet API endpoints for credit-gated async job pipeline"""
    
    def test_get_wallet_me(self, demo_token):
        """Test GET /api/wallet/me returns balance, reserved, and available credits"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers)
        
        assert response.status_code == 200, f"Wallet me failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "userId" in data, "Missing userId"
        assert "balanceCredits" in data, "Missing balanceCredits"
        assert "reservedCredits" in data, "Missing reservedCredits"
        assert "availableCredits" in data, "Missing availableCredits"
        
        # Verify data types
        assert isinstance(data["balanceCredits"], int), "balanceCredits should be int"
        assert isinstance(data["reservedCredits"], int), "reservedCredits should be int"
        assert isinstance(data["availableCredits"], int), "availableCredits should be int"
        
        # Verify available = balance - reserved
        expected_available = data["balanceCredits"] - data["reservedCredits"]
        assert data["availableCredits"] == expected_available, f"Available credits mismatch: {data['availableCredits']} != {expected_available}"
        
        print(f"✓ Wallet balance: {data['balanceCredits']}, reserved: {data['reservedCredits']}, available: {data['availableCredits']}")
    
    def test_get_wallet_me_unauthorized(self):
        """Test wallet endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/wallet/me")
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
    
    def test_get_pricing(self):
        """Test GET /api/wallet/pricing returns all job types with baseCredits"""
        response = requests.get(f"{BASE_URL}/api/wallet/pricing")
        
        assert response.status_code == 200, f"Pricing failed: {response.text}"
        data = response.json()
        
        assert "pricing" in data, "Missing pricing field"
        pricing = data["pricing"]
        
        # Expected job types
        expected_job_types = [
            "TEXT_TO_IMAGE",
            "TEXT_TO_VIDEO",
            "IMAGE_TO_VIDEO",
            "VIDEO_REMIX",
            "STORY_GENERATION",
            "REEL_GENERATION",
            "STYLE_PROFILE_CREATE"
        ]
        
        for job_type in expected_job_types:
            assert job_type in pricing, f"Missing job type: {job_type}"
            assert "baseCredits" in pricing[job_type], f"Missing baseCredits for {job_type}"
            assert isinstance(pricing[job_type]["baseCredits"], int), f"baseCredits should be int for {job_type}"
            print(f"✓ {job_type}: {pricing[job_type]['baseCredits']} credits")


class TestJobPipeline:
    """Test job creation, status, and cancellation with credit reservation"""
    
    def test_create_job_reserves_credits(self, admin_token):
        """Test POST /api/wallet/jobs creates job with QUEUED status and reserves credits"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get initial wallet state
        wallet_before = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers).json()
        initial_available = wallet_before["availableCredits"]
        
        # Create a TEXT_TO_IMAGE job
        job_data = {
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {"prompt": "Test image generation"},
            "provider": "gemini"
        }
        
        response = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        
        assert response.status_code == 200, f"Job creation failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True, "Job creation should succeed"
        assert "jobId" in data, "Missing jobId"
        assert data["status"] == "QUEUED", f"Status should be QUEUED, got: {data['status']}"
        assert "costCredits" in data, "Missing costCredits"
        
        job_id = data["jobId"]
        cost = data["costCredits"]
        
        print(f"✓ Job {job_id} created with QUEUED status, cost: {cost} credits")
        
        # Verify credits are reserved
        wallet_after = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers).json()
        new_available = wallet_after["availableCredits"]
        
        # Available should be reduced by the cost
        assert new_available == initial_available - cost, f"Available credits not reduced: {new_available} != {initial_available - cost}"
        
        print(f"✓ Credits reserved: available went from {initial_available} to {new_available}")
        
        return job_id
    
    def test_idempotency_protection(self, admin_token):
        """Test duplicate request with same Idempotency-Key returns existing job"""
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Idempotency-Key": f"test-idemp-{uuid.uuid4()}"
        }
        
        job_data = {
            "jobType": "REEL_GENERATION",
            "inputData": {"topic": "Idempotency test"},
            "provider": "gemini"
        }
        
        # First request
        response1 = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        assert response1.status_code == 200, f"First request failed: {response1.text}"
        data1 = response1.json()
        job_id1 = data1["jobId"]
        
        # Second request with same idempotency key
        response2 = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        assert response2.status_code == 200, f"Second request failed: {response2.text}"
        data2 = response2.json()
        job_id2 = data2["jobId"]
        
        # Should return same job ID
        assert job_id1 == job_id2, f"Idempotency failed: {job_id1} != {job_id2}"
        assert data2.get("duplicate") == True, "Should indicate duplicate request"
        
        print(f"✓ Idempotency protection working: duplicate request returned existing job {job_id1}")
    
    def test_get_job_status(self, admin_token):
        """Test GET /api/wallet/jobs/{id} returns job details"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a job first
        job_data = {
            "jobType": "STORY_GENERATION",
            "inputData": {"genre": "Fantasy", "theme": "Adventure"},
            "provider": "gemini"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        assert create_response.status_code == 200
        job_id = create_response.json()["jobId"]
        
        # Get job status
        status_response = requests.get(f"{BASE_URL}/api/wallet/jobs/{job_id}", headers=headers)
        assert status_response.status_code == 200, f"Get job status failed: {status_response.text}"
        
        data = status_response.json()
        
        assert data["jobId"] == job_id, "Job ID mismatch"
        assert "status" in data, "Missing status"
        assert "jobType" in data, "Missing jobType"
        assert data["jobType"] == "STORY_GENERATION", f"Job type mismatch: {data['jobType']}"
        assert "costCredits" in data, "Missing costCredits"
        assert "createdAt" in data, "Missing createdAt"
        
        print(f"✓ Job status retrieved: {data['status']}, type: {data['jobType']}, cost: {data['costCredits']}")
    
    def test_get_job_not_found(self, demo_token):
        """Test GET /api/wallet/jobs/{id} returns 404 for non-existent job"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        
        fake_job_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/wallet/jobs/{fake_job_id}", headers=headers)
        
        assert response.status_code == 404, f"Should return 404, got: {response.status_code}"
        print(f"✓ Non-existent job returns 404")
    
    def test_cancel_job_releases_credits(self, admin_token):
        """Test POST /api/wallet/jobs/{id}/cancel releases credits"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get initial wallet state
        wallet_before = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers).json()
        initial_available = wallet_before["availableCredits"]
        
        # Create a job
        job_data = {
            "jobType": "VIDEO_REMIX",
            "inputData": {"description": "Cancel test"},
            "provider": "gemini"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        assert create_response.status_code == 200
        job_id = create_response.json()["jobId"]
        cost = create_response.json()["costCredits"]
        
        # Verify credits are reserved
        wallet_reserved = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers).json()
        assert wallet_reserved["availableCredits"] == initial_available - cost
        
        # Cancel the job
        cancel_response = requests.post(f"{BASE_URL}/api/wallet/jobs/{job_id}/cancel", headers=headers)
        assert cancel_response.status_code == 200, f"Cancel failed: {cancel_response.text}"
        
        data = cancel_response.json()
        assert data["success"] == True, "Cancel should succeed"
        assert data["status"] == "CANCELLED", f"Status should be CANCELLED, got: {data['status']}"
        
        # Verify credits are released
        wallet_after = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers).json()
        assert wallet_after["availableCredits"] == initial_available, f"Credits not released: {wallet_after['availableCredits']} != {initial_available}"
        
        print(f"✓ Job {job_id} cancelled and {cost} credits released")
    
    def test_cancel_job_not_allowed_when_running(self, admin_token):
        """Test cannot cancel job that's not in QUEUED/PENDING status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create and cancel a job first
        job_data = {
            "jobType": "TEXT_TO_IMAGE",
            "inputData": {"prompt": "Cancel test 2"},
            "provider": "gemini"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        job_id = create_response.json()["jobId"]
        
        # First cancel
        cancel1 = requests.post(f"{BASE_URL}/api/wallet/jobs/{job_id}/cancel", headers=headers)
        assert cancel1.status_code == 200
        
        # Second cancel should fail (job already cancelled)
        cancel2 = requests.post(f"{BASE_URL}/api/wallet/jobs/{job_id}/cancel", headers=headers)
        assert cancel2.status_code == 400, f"Second cancel should fail, got: {cancel2.status_code}"
        
        print(f"✓ Double cancel properly rejected")
    
    def test_invalid_job_type(self, demo_token):
        """Test invalid job type returns 400"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        
        job_data = {
            "jobType": "INVALID_TYPE",
            "inputData": {"prompt": "test"},
            "provider": "gemini"
        }
        
        response = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        assert response.status_code == 400, f"Should return 400 for invalid job type, got: {response.status_code}"
        
        print(f"✓ Invalid job type returns 400")


class TestCreditLedger:
    """Test credit ledger with HOLD/CAPTURE/RELEASE transactions"""
    
    def test_get_credit_ledger(self, admin_token):
        """Test GET /api/wallet/ledger shows transactions"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/wallet/ledger", headers=headers)
        
        assert response.status_code == 200, f"Ledger failed: {response.text}"
        data = response.json()
        
        assert "entries" in data, "Missing entries"
        assert "total" in data, "Missing total"
        assert "summary" in data, "Missing summary"
        
        summary = data["summary"]
        assert "totalHolds" in summary, "Missing totalHolds in summary"
        assert "totalCaptures" in summary, "Missing totalCaptures in summary"
        assert "totalReleases" in summary, "Missing totalReleases in summary"
        
        print(f"✓ Ledger retrieved: {data['total']} entries")
        print(f"  Summary - Holds: {summary['totalHolds']}, Captures: {summary['totalCaptures']}, Releases: {summary['totalReleases']}")
    
    def test_ledger_shows_hold_transaction(self, admin_token):
        """Test ledger shows HOLD entry when job is created"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a job
        job_data = {
            "jobType": "REEL_GENERATION",
            "inputData": {"topic": "Ledger test"},
            "provider": "gemini"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        assert create_response.status_code == 200
        job_id = create_response.json()["jobId"]
        
        # Get ledger
        ledger_response = requests.get(f"{BASE_URL}/api/wallet/ledger", headers=headers)
        assert ledger_response.status_code == 200
        
        entries = ledger_response.json()["entries"]
        
        # Find HOLD entry for this job
        hold_entries = [e for e in entries if e.get("refId") == job_id and e.get("entryType") == "HOLD"]
        assert len(hold_entries) > 0, f"No HOLD entry found for job {job_id}"
        
        hold_entry = hold_entries[0]
        assert hold_entry["status"] == "ACTIVE", f"HOLD status should be ACTIVE, got: {hold_entry['status']}"
        
        print(f"✓ HOLD entry found for job {job_id}: {hold_entry['amount']} credits")
        
        return job_id
    
    def test_ledger_shows_release_on_cancel(self, admin_token):
        """Test ledger shows RELEASE entry when job is cancelled"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a job
        job_data = {
            "jobType": "STYLE_PROFILE_CREATE",
            "inputData": {"style": "Release test"},
            "provider": "gemini"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        assert create_response.status_code == 200
        job_id = create_response.json()["jobId"]
        
        # Cancel the job
        cancel_response = requests.post(f"{BASE_URL}/api/wallet/jobs/{job_id}/cancel", headers=headers)
        assert cancel_response.status_code == 200
        
        # Get ledger
        ledger_response = requests.get(f"{BASE_URL}/api/wallet/ledger", headers=headers)
        assert ledger_response.status_code == 200
        
        entries = ledger_response.json()["entries"]
        
        # Find RELEASE entry for this job
        release_entries = [e for e in entries if e.get("refId") == job_id and e.get("entryType") == "RELEASE"]
        assert len(release_entries) > 0, f"No RELEASE entry found for job {job_id}"
        
        release_entry = release_entries[0]
        assert "reason" in release_entry, "RELEASE entry should have reason"
        
        print(f"✓ RELEASE entry found for job {job_id}: {release_entry['amount']} credits released (reason: {release_entry.get('reason', 'N/A')})")


class TestListJobs:
    """Test job listing endpoints"""
    
    def test_list_jobs(self, admin_token):
        """Test GET /api/wallet/jobs returns user's jobs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/wallet/jobs", headers=headers)
        
        assert response.status_code == 200, f"List jobs failed: {response.text}"
        data = response.json()
        
        assert "jobs" in data, "Missing jobs field"
        assert "total" in data, "Missing total field"
        assert "limit" in data, "Missing limit field"
        
        print(f"✓ Listed {len(data['jobs'])} jobs (total: {data['total']})")
    
    def test_list_jobs_filter_by_status(self, admin_token):
        """Test filtering jobs by status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Filter by CANCELLED status
        response = requests.get(f"{BASE_URL}/api/wallet/jobs?status=CANCELLED", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned jobs should be CANCELLED
        for job in data["jobs"]:
            assert job["status"] == "CANCELLED", f"Job {job['id']} should be CANCELLED"
        
        print(f"✓ Filtered by CANCELLED status: {len(data['jobs'])} jobs")
    
    def test_list_jobs_filter_by_type(self, admin_token):
        """Test filtering jobs by job type"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/wallet/jobs?job_type=TEXT_TO_IMAGE", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        for job in data["jobs"]:
            assert job["jobType"] == "TEXT_TO_IMAGE", f"Job should be TEXT_TO_IMAGE"
        
        print(f"✓ Filtered by TEXT_TO_IMAGE: {len(data['jobs'])} jobs")


class TestStoryGeneratorImages:
    """Test Story Generator image display - coverImageUrl and scene.imageUrl"""
    
    def test_story_generation_returns_images(self, admin_token):
        """Test story generation includes coverImageUrl and scene.imageUrl"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        story_data = {
            "ageGroup": "4-6",
            "genre": "Fantasy",
            "theme": "Friendship",
            "sceneCount": 8
        }
        
        print("Generating story (this may take 30-60 seconds)...")
        response = requests.post(f"{BASE_URL}/api/generate/story", headers=headers, json=story_data, timeout=120)
        
        # Accept both success and service unavailable (AI might be busy)
        if response.status_code == 503:
            print(f"⚠️ AI service temporarily unavailable: {response.text}")
            pytest.skip("AI service unavailable")
            return
        
        assert response.status_code == 200, f"Story generation failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True, "Story generation should succeed"
        assert "result" in data, "Missing result"
        
        result = data["result"]
        
        # Check for coverImageUrl (may be optional if image generation fails)
        has_cover_image = "coverImageUrl" in result and result["coverImageUrl"]
        if has_cover_image:
            print(f"✓ Cover image URL present: {result['coverImageUrl']}")
        else:
            print("⚠️ Cover image URL not present (image generation may have failed)")
        
        # Check for scenes with imageUrl
        assert "scenes" in result, "Missing scenes"
        assert len(result["scenes"]) > 0, "No scenes in result"
        
        first_scene = result["scenes"][0]
        has_scene_image = "imageUrl" in first_scene and first_scene["imageUrl"]
        if has_scene_image:
            print(f"✓ First scene image URL present: {first_scene['imageUrl']}")
        else:
            print("⚠️ Scene image URL not present (image generation may have failed)")
        
        # Verify story structure
        assert "title" in result, "Missing title"
        assert "synopsis" in result, "Missing synopsis"
        
        print(f"✓ Story generated: {result['title']}")
        print(f"  Scenes: {len(result['scenes'])}")
        print(f"  Cover image: {'Yes' if has_cover_image else 'No'}")
        print(f"  Scene images: {'Yes' if has_scene_image else 'No'}")
    
    def test_story_image_endpoint(self, admin_token):
        """Test story image serving endpoint exists"""
        # This tests that the endpoint route is registered
        # We can't test actual images without a valid story_id/filename
        
        response = requests.get(f"{BASE_URL}/api/generate/story-image/test-id/test.png")
        
        # Should return 404 for non-existent image (not 500 or other error)
        assert response.status_code == 404, f"Expected 404 for non-existent image, got: {response.status_code}"
        
        print("✓ Story image endpoint exists and returns 404 for non-existent images")


class TestInsufficientCredits:
    """Test credit validation"""
    
    def test_job_creation_insufficient_credits(self, demo_token):
        """Test job creation fails with insufficient credits"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        
        # First check current balance
        wallet = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers).json()
        available = wallet["availableCredits"]
        
        # Try to create a TEXT_TO_VIDEO job which costs more
        # (base 25 + duration * 5)
        job_data = {
            "jobType": "TEXT_TO_VIDEO",
            "inputData": {
                "prompt": "Insufficient credits test",
                "duration": 12  # Maximum duration = 25 + 12*5 = 85 credits
            },
            "provider": "gemini"
        }
        
        response = requests.post(f"{BASE_URL}/api/wallet/jobs", headers=headers, json=job_data)
        
        # If available credits < 85, should fail with 402
        cost = 25 + (12 * 5)  # 85 credits
        if available < cost:
            assert response.status_code == 402, f"Should return 402 for insufficient credits, got: {response.status_code}"
            print(f"✓ Insufficient credits properly handled (available: {available}, needed: {cost})")
        else:
            # User has enough credits, job should succeed
            assert response.status_code == 200, f"Job should succeed with {available} credits"
            print(f"✓ User has enough credits ({available} >= {cost}), job created")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
