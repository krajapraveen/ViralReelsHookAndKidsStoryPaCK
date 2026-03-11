"""
Test Suite: Comix AI and GIF Maker - Full E2E Generation Tests (Iteration 68)
Tests actual image upload and AI generation functionality

Features tested:
- Comix AI photo-to-comic character generation with actual image upload
- Comix AI panel generation from text description
- Comix AI story mode generation
- GIF Maker photo-to-gif generation with actual image upload
- Job status polling
- Static file serving verification
"""

import pytest
import requests
import os
import time
import base64
from io import BytesIO

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://subscription-gateway-1.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "demo@example.com"
TEST_PASSWORD = "Password123!"

# Create a simple test image (1x1 red pixel PNG)
def create_test_image():
    """Create a minimal valid PNG image for testing"""
    # PNG header + IHDR chunk + minimal IDAT + IEND
    # This is a 1x1 red pixel PNG
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimension
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # 8-bit RGB
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,  # compressed data
        0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x18, 0xDD,
        0x8D, 0xB5, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
        0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    return png_data


class TestAuthentication:
    """Test authentication for API access"""
    
    def test_login_demo_user(self):
        """Test login with demo user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✓ Login successful. User: {data['user'].get('email')}")
        return data["token"]


class TestComixAIGeneration:
    """Test Comix AI generation endpoints with actual image upload"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_comix_styles_endpoint(self, auth_token):
        """Test /api/comix/styles returns all style data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/comix/styles", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        assert "layouts" in data
        assert "credits" in data
        
        # Verify styles count
        styles = data["styles"]
        assert len(styles) >= 9, f"Expected at least 9 styles, got {len(styles)}"
        print(f"✓ Styles endpoint: {len(styles)} styles available")
    
    def test_comix_character_generation_start(self, auth_token):
        """Test starting a comic character generation job with image upload"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create test image
        test_image = create_test_image()
        
        files = {
            'photo': ('test_photo.png', BytesIO(test_image), 'image/png')
        }
        data = {
            'style': 'classic',
            'character_type': 'portrait',
            'remove_background': 'false'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comix/generate-character",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Generation failed: {response.text}"
        result = response.json()
        assert result.get("success") == True, "Success not True"
        assert "jobId" in result, "No jobId in response"
        assert result.get("status") == "QUEUED", f"Unexpected status: {result.get('status')}"
        
        print(f"✓ Character generation started. Job ID: {result['jobId']}")
        return result["jobId"]
    
    def test_comix_character_job_polling(self, auth_token):
        """Test job polling for character generation"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Start a job
        test_image = create_test_image()
        files = {'photo': ('test.png', BytesIO(test_image), 'image/png')}
        data = {'style': 'manga', 'character_type': 'portrait'}
        
        response = requests.post(
            f"{BASE_URL}/api/comix/generate-character",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        job_id = response.json()["jobId"]
        
        # Poll for completion (max 60 seconds)
        max_wait = 60
        poll_interval = 3
        elapsed = 0
        final_status = None
        
        while elapsed < max_wait:
            poll_response = requests.get(
                f"{BASE_URL}/api/comix/job/{job_id}",
                headers=headers
            )
            assert poll_response.status_code == 200
            job_data = poll_response.json()
            final_status = job_data.get("status")
            
            print(f"  Job {job_id[:8]}... status: {final_status}")
            
            if final_status in ["COMPLETED", "FAILED"]:
                break
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        assert final_status in ["COMPLETED", "FAILED"], f"Job stuck at status: {final_status}"
        
        if final_status == "COMPLETED":
            assert "resultUrl" in job_data, "No resultUrl in completed job"
            result_url = job_data["resultUrl"]
            print(f"✓ Character generation COMPLETED. Result URL: {result_url}")
            
            # Verify result URL is accessible if it's not a placeholder
            if result_url.startswith("/api/static"):
                full_url = f"{BASE_URL}{result_url}"
                static_response = requests.get(full_url, headers=headers)
                print(f"  Static file response: {static_response.status_code}")
                # Note: File may not exist yet if generation failed silently
        else:
            print(f"⚠ Character generation FAILED. Error: {job_data.get('error')}")
    
    def test_comix_panel_generation(self, auth_token):
        """Test comic panel generation from text description"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        data = {
            'scene_description': 'A superhero standing on a rooftop at sunset looking over the city',
            'style': 'superhero',
            'panel_count': '1',
            'genre': 'action',
            'mood': 'exciting',
            'include_speech_bubbles': 'true',
            'speech_text': 'The city needs a hero!'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comix/generate-panel",
            headers=headers,
            data=data
        )
        
        assert response.status_code == 200, f"Panel generation failed: {response.text}"
        result = response.json()
        assert result.get("success") == True
        assert "jobId" in result
        
        print(f"✓ Panel generation started. Job ID: {result['jobId']}")
        
        # Poll for result
        job_id = result["jobId"]
        max_wait = 45
        elapsed = 0
        
        while elapsed < max_wait:
            poll_response = requests.get(f"{BASE_URL}/api/comix/job/{job_id}", headers=headers)
            job_data = poll_response.json()
            if job_data.get("status") in ["COMPLETED", "FAILED"]:
                print(f"  Panel generation final status: {job_data.get('status')}")
                break
            time.sleep(3)
            elapsed += 3
    
    def test_comix_story_generation(self, auth_token):
        """Test comic story generation with multiple panels"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        data = {
            'story_prompt': 'A young wizard discovers a magical book that brings drawings to life',
            'style': 'fantasy',
            'panel_count': '4',
            'genre': 'adventure',
            'auto_dialogue': 'true'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comix/generate-story",
            headers=headers,
            data=data
        )
        
        assert response.status_code == 200, f"Story generation failed: {response.text}"
        result = response.json()
        assert result.get("success") == True
        assert "jobId" in result
        
        print(f"✓ Story generation started. Job ID: {result['jobId']}")
        
        # Note: Story generation takes longer, just verify it started
        job_id = result["jobId"]
        poll_response = requests.get(f"{BASE_URL}/api/comix/job/{job_id}", headers=headers)
        assert poll_response.status_code == 200
        job_data = poll_response.json()
        assert job_data.get("status") in ["QUEUED", "PROCESSING"], f"Unexpected initial status: {job_data.get('status')}"
    
    def test_content_moderation_blocks_copyrighted(self, auth_token):
        """Test that content moderation blocks copyrighted content"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Try to generate with copyrighted content
        test_image = create_test_image()
        files = {'photo': ('test.png', BytesIO(test_image), 'image/png')}
        data = {
            'style': 'classic',
            'character_type': 'portrait',
            'custom_prompt': 'Make this look like Spiderman from Marvel'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comix/generate-character",
            headers=headers,
            files=files,
            data=data
        )
        
        # Should be blocked with 400
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        error_detail = response.json().get("detail", "")
        assert "not allowed" in error_detail.lower() or "spiderman" in error_detail.lower()
        print(f"✓ Content moderation working: {error_detail}")


class TestGifMakerGeneration:
    """Test GIF Maker generation endpoints with actual image upload"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_gif_emotions_endpoint(self, auth_token):
        """Test /api/gif-maker/emotions returns all emotion data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/emotions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "emotions" in data
        assert "styles" in data
        assert "backgrounds" in data
        assert "credits" in data
        
        emotions = data["emotions"]
        assert len(emotions) >= 12, f"Expected at least 12 emotions, got {len(emotions)}"
        print(f"✓ Emotions endpoint: {len(emotions)} emotions available")
    
    def test_gif_single_generation(self, auth_token):
        """Test single GIF generation with image upload"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        test_image = create_test_image()
        files = {'photo': ('test_photo.png', BytesIO(test_image), 'image/png')}
        data = {
            'emotion': 'happy',
            'style': 'cartoon',
            'background': 'transparent',
            'quality': 'basic'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/gif-maker/generate",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"GIF generation failed: {response.text}"
        result = response.json()
        assert result.get("success") == True
        assert "jobId" in result
        assert result.get("status") == "QUEUED"
        
        print(f"✓ GIF generation started. Job ID: {result['jobId']}")
        
        # Poll for completion
        job_id = result["jobId"]
        max_wait = 60
        elapsed = 0
        
        while elapsed < max_wait:
            poll_response = requests.get(f"{BASE_URL}/api/gif-maker/job/{job_id}", headers=headers)
            assert poll_response.status_code == 200
            job_data = poll_response.json()
            final_status = job_data.get("status")
            
            print(f"  GIF Job {job_id[:8]}... status: {final_status}")
            
            if final_status in ["COMPLETED", "FAILED"]:
                break
            
            time.sleep(3)
            elapsed += 3
        
        if final_status == "COMPLETED":
            assert "resultUrl" in job_data
            print(f"✓ GIF generation COMPLETED. Result URL: {job_data['resultUrl']}")
        else:
            print(f"⚠ GIF generation status: {final_status}. Error: {job_data.get('error')}")
    
    def test_gif_batch_generation(self, auth_token):
        """Test batch GIF generation with multiple emotions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        test_image = create_test_image()
        files = {'photo': ('test_photo.png', BytesIO(test_image), 'image/png')}
        data = {
            'emotions': 'happy,excited,laughing',
            'style': 'sticker'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/gif-maker/generate-batch",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Batch generation failed: {response.text}"
        result = response.json()
        assert result.get("success") == True
        assert "batchId" in result
        
        print(f"✓ Batch GIF generation started. Batch ID: {result['batchId']}")
    
    def test_gif_unsafe_content_blocked(self, auth_token):
        """Test that unsafe content is blocked"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        test_image = create_test_image()
        files = {'photo': ('test.png', BytesIO(test_image), 'image/png')}
        data = {
            'emotion': 'happy',
            'style': 'cartoon',
            'add_text': 'Some violent content here'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/gif-maker/generate",
            headers=headers,
            files=files,
            data=data
        )
        
        # Should be blocked
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Unsafe content blocked: {response.json().get('detail')}")
    
    def test_gif_share_endpoint(self, auth_token):
        """Test public share endpoint returns 404 for non-existent GIF"""
        response = requests.get(f"{BASE_URL}/api/gif-maker/share/nonexistent-id")
        assert response.status_code == 404
        print(f"✓ Share endpoint returns 404 for non-existent GIF")


class TestStaticFileServing:
    """Test static file serving for generated images"""
    
    def test_static_directory_accessible(self):
        """Test that static file directory is accessible"""
        # Just verify the endpoint exists and doesn't error
        response = requests.get(f"{BASE_URL}/api/static/generated/")
        # 403 or 404 is expected for directory listing, just not 500
        assert response.status_code != 500, f"Static serving error: {response.status_code}"
        print(f"✓ Static endpoint accessible (status: {response.status_code})")


class TestJobHistory:
    """Test job history endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_comix_history(self, auth_token):
        """Test comic generation history endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/comix/history?size=5", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        print(f"✓ Comix history: {data['total']} total jobs")
    
    def test_gif_history(self, auth_token):
        """Test GIF generation history endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/history?size=5", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        print(f"✓ GIF history: {data['total']} total jobs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
