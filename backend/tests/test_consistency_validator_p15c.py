"""
Test Suite for Photo to Comic P1.5-C: Character Consistency Validator
Tests OpenCV FaceRecognizerSF (SFace) integration for face embedding extraction and comparison.

Features tested:
- extract_face_embedding detects faces in real photos
- extract_face_embedding returns no face for non-face images
- compute_similarity returns 1.0 for self-comparison
- validate_panel_consistency returns correct verdicts
- run_consistency_validation logs to consistency_logs collection
"""

import pytest
import os
import sys
import base64
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestConsistencyValidatorUnit:
    """Unit tests for consistency_validator.py functions"""
    
    def test_models_exist(self):
        """Verify ONNX models are present"""
        from services.consistency_validator import YUNET_PATH, SFACE_PATH
        
        assert os.path.exists(YUNET_PATH), f"YuNet model not found at {YUNET_PATH}"
        assert os.path.exists(SFACE_PATH), f"SFace model not found at {SFACE_PATH}"
        
        # Check file sizes are reasonable
        yunet_size = os.path.getsize(YUNET_PATH)
        sface_size = os.path.getsize(SFACE_PATH)
        
        assert yunet_size > 100000, f"YuNet model too small: {yunet_size} bytes"
        assert sface_size > 30000000, f"SFace model too small: {sface_size} bytes"
        print(f"PASS: YuNet model: {yunet_size/1024:.1f}KB, SFace model: {sface_size/1024/1024:.1f}MB")
    
    def test_extract_face_embedding_real_face(self):
        """Test face embedding extraction from real face photo"""
        from services.consistency_validator import extract_face_embedding
        
        # Load real face image
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            image_bytes = f.read()
        
        embedding, face_detected, face_score = extract_face_embedding(image_bytes)
        
        assert face_detected is True, "Face should be detected in real face photo"
        assert embedding is not None, "Embedding should not be None"
        assert face_score > 0.5, f"Face score should be > 0.5, got {face_score}"
        
        # Check embedding shape (SFace produces 128-dim embeddings)
        assert embedding.shape == (1, 128), f"Expected (1, 128) embedding, got {embedding.shape}"
        print(f"PASS: Face detected with score {face_score:.3f}, embedding shape {embedding.shape}")
    
    def test_extract_face_embedding_no_face(self):
        """Test face embedding extraction returns no face for non-face images"""
        from services.consistency_validator import extract_face_embedding
        
        # Load no-face image (solid color)
        with open('/tmp/test_no_face.jpg', 'rb') as f:
            image_bytes = f.read()
        
        embedding, face_detected, face_score = extract_face_embedding(image_bytes)
        
        assert face_detected is False, "No face should be detected in solid color image"
        assert embedding is None, "Embedding should be None when no face detected"
        assert face_score == 0, f"Face score should be 0, got {face_score}"
        print("PASS: No face detected in non-face image")
    
    def test_extract_face_embedding_base64_input(self):
        """Test face embedding extraction from base64 encoded image"""
        from services.consistency_validator import extract_face_embedding
        
        # Load and encode real face image
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            image_bytes = f.read()
        
        b64_data = base64.b64encode(image_bytes).decode('utf-8')
        
        embedding, face_detected, face_score = extract_face_embedding(b64_data)
        
        assert face_detected is True, "Face should be detected from base64 input"
        assert embedding is not None, "Embedding should not be None"
        print(f"PASS: Face detected from base64 input, score {face_score:.3f}")
    
    def test_extract_face_embedding_data_uri_input(self):
        """Test face embedding extraction from data URI format"""
        from services.consistency_validator import extract_face_embedding
        
        # Load and encode real face image as data URI
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            image_bytes = f.read()
        
        b64_data = base64.b64encode(image_bytes).decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_data}"
        
        embedding, face_detected, face_score = extract_face_embedding(data_uri)
        
        assert face_detected is True, "Face should be detected from data URI input"
        assert embedding is not None, "Embedding should not be None"
        print(f"PASS: Face detected from data URI input, score {face_score:.3f}")
    
    def test_compute_similarity_self_comparison(self):
        """Test compute_similarity returns ~1.0 for self-comparison"""
        from services.consistency_validator import extract_face_embedding, compute_similarity
        
        # Load real face image
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            image_bytes = f.read()
        
        embedding, face_detected, _ = extract_face_embedding(image_bytes)
        assert face_detected, "Need face for self-comparison test"
        
        # Self-comparison should return ~1.0 (floating point precision)
        similarity = compute_similarity(embedding, embedding)
        
        assert similarity > 0.999, f"Self-comparison should return ~1.0, got {similarity}"
        print(f"PASS: Self-comparison similarity = {similarity}")
    
    def test_compute_similarity_none_inputs(self):
        """Test compute_similarity handles None inputs gracefully"""
        from services.consistency_validator import compute_similarity
        
        # None inputs should return 0.0
        assert compute_similarity(None, None) == 0.0
        assert compute_similarity(None, np.zeros((1, 128))) == 0.0
        assert compute_similarity(np.zeros((1, 128)), None) == 0.0
        print("PASS: compute_similarity handles None inputs correctly")
    
    def test_validate_panel_consistency_accept(self):
        """Test validate_panel_consistency returns 'accept' for high-similarity panels"""
        from services.consistency_validator import extract_face_embedding, validate_panel_consistency
        
        # Load real face image
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            image_bytes = f.read()
        
        embedding, face_detected, _ = extract_face_embedding(image_bytes)
        assert face_detected, "Need face for consistency test"
        
        # Same embedding should give 'accept' verdict
        result = validate_panel_consistency(
            source_embedding=embedding,
            panel_embedding=embedding,
            panel1_embedding=embedding,
            panel_number=1,
            source_face_detected=True,
            panel_face_detected=True
        )
        
        assert result["verdict"] == "accept", f"Expected 'accept', got {result['verdict']}"
        assert result["source_similarity"] == 1.0, f"Expected 1.0 similarity, got {result['source_similarity']}"
        assert result["face_detected"] is True
        print(f"PASS: validate_panel_consistency returns 'accept' for identical embeddings")
    
    def test_validate_panel_consistency_no_face_in_panel(self):
        """Test validate_panel_consistency returns 'no_face' for panels without faces"""
        from services.consistency_validator import extract_face_embedding, validate_panel_consistency
        
        # Load real face image for source
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            image_bytes = f.read()
        
        source_emb, source_detected, _ = extract_face_embedding(image_bytes)
        assert source_detected, "Need face in source for test"
        
        # Panel has no face
        result = validate_panel_consistency(
            source_embedding=source_emb,
            panel_embedding=None,
            panel1_embedding=source_emb,
            panel_number=2,
            source_face_detected=True,
            panel_face_detected=False
        )
        
        assert result["verdict"] == "no_face", f"Expected 'no_face', got {result['verdict']}"
        assert result["face_detected"] is False
        assert result["reason"] == "panel_no_face"
        print("PASS: validate_panel_consistency returns 'no_face' for panels without faces")
    
    def test_validate_panel_consistency_skip_when_source_no_face(self):
        """Test validate_panel_consistency returns 'skip' when source has no face"""
        from services.consistency_validator import validate_panel_consistency
        
        result = validate_panel_consistency(
            source_embedding=None,
            panel_embedding=None,
            panel1_embedding=None,
            panel_number=1,
            source_face_detected=False,
            panel_face_detected=True
        )
        
        assert result["verdict"] == "skip", f"Expected 'skip', got {result['verdict']}"
        assert result["reason"] == "source_no_face"
        print("PASS: validate_panel_consistency returns 'skip' when source has no face")
    
    def test_validate_panel_consistency_panel1_similarity(self):
        """Test validate_panel_consistency computes panel1 similarity for panels > 1"""
        from services.consistency_validator import extract_face_embedding, validate_panel_consistency
        
        # Load real face image
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            image_bytes = f.read()
        
        embedding, face_detected, _ = extract_face_embedding(image_bytes)
        assert face_detected, "Need face for test"
        
        # Panel 1 should have panel1_similarity = 0 (no comparison to self)
        result1 = validate_panel_consistency(
            source_embedding=embedding,
            panel_embedding=embedding,
            panel1_embedding=embedding,
            panel_number=1,
            source_face_detected=True,
            panel_face_detected=True
        )
        assert result1["panel1_similarity"] == 0.0, "Panel 1 should not compare to itself"
        
        # Panel 2+ should have panel1_similarity computed
        result2 = validate_panel_consistency(
            source_embedding=embedding,
            panel_embedding=embedding,
            panel1_embedding=embedding,
            panel_number=2,
            source_face_detected=True,
            panel_face_detected=True
        )
        assert result2["panel1_similarity"] == 1.0, f"Panel 2 should have panel1_similarity=1.0, got {result2['panel1_similarity']}"
        print("PASS: panel1_similarity computed correctly for panels > 1")


class TestConsistencyValidatorIntegration:
    """Integration tests for consistency validation in the pipeline"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        import requests
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_backend_server_running(self):
        """Test backend server is running with consistency validator integrated"""
        import requests
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("PASS: Backend server running")
    
    def test_quality_check_endpoint_regression(self, auth_token):
        """Regression: Quality check endpoint still works"""
        import requests
        
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            files = {'photo': ('test.jpg', f, 'image/jpeg')}
            headers = {'Authorization': f'Bearer {auth_token}'}
            response = requests.post(
                f"{BASE_URL}/api/photo-to-comic/quality-check",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"Quality check failed: {response.status_code}"
        data = response.json()
        assert 'face_detected' in data
        assert 'can_proceed' in data
        print(f"PASS: Quality check endpoint works, face_detected={data.get('face_detected')}")
    
    def test_events_endpoint_regression(self, auth_token):
        """Regression: Events endpoint still works"""
        import requests
        
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        # Use a valid event type from the allowed list
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/events",
            json={
                "event_type": "result_page_view",
                "metadata": {"test": True}
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Events endpoint failed: {response.status_code}"
        print("PASS: Events endpoint works")
    
    def test_pdf_endpoint_regression(self, auth_token):
        """Regression: PDF endpoint works for completed jobs"""
        import requests
        
        # Use the completed job ID from test credentials
        job_id = "dd41b71f-5711-413b-aac3-dc11349e8e04"
        
        headers = {'Authorization': f'Bearer {auth_token}'}
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/{job_id}/pdf",
            headers=headers
        )
        
        # Should return PDF or 404 if job doesn't exist
        assert response.status_code in [200, 404], f"PDF endpoint failed: {response.status_code}"
        if response.status_code == 200:
            assert 'application/pdf' in response.headers.get('Content-Type', '')
            print("PASS: PDF endpoint returns PDF")
        else:
            print("PASS: PDF endpoint returns 404 for non-existent job (expected)")
    
    def test_job_status_endpoint_regression(self, auth_token):
        """Regression: Job status endpoint works"""
        import requests
        
        job_id = "dd41b71f-5711-413b-aac3-dc11349e8e04"
        
        headers = {'Authorization': f'Bearer {auth_token}'}
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/{job_id}",
            headers=headers
        )
        
        # Should return job data or 404
        assert response.status_code in [200, 404], f"Job status failed: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert 'status' in data or 'id' in data
            print(f"PASS: Job status endpoint works, status={data.get('status')}")
        else:
            print("PASS: Job status returns 404 for non-existent job (expected)")


class TestConsistencyLogging:
    """Test consistency_logs collection logging"""
    
    @pytest.mark.asyncio
    async def test_run_consistency_validation_logs_to_db(self):
        """Test run_consistency_validation logs to consistency_logs collection"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.consistency_validator import run_consistency_validation
        
        # Connect to MongoDB
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'creatorstudio_production')
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Load test image
        with open('/tmp/test_real_face.jpg', 'rb') as f:
            source_bytes = f.read()
        
        # Create mock panels (using same image for simplicity)
        b64_data = base64.b64encode(source_bytes).decode('utf-8')
        panels = [
            {"panelNumber": 1, "status": "READY", "imageUrl": f"data:image/jpeg;base64,{b64_data}"},
            {"panelNumber": 2, "status": "READY", "imageUrl": f"data:image/jpeg;base64,{b64_data}"},
        ]
        
        test_job_id = f"TEST_consistency_validator_{os.urandom(4).hex()}"
        
        try:
            # Run consistency validation
            results = await run_consistency_validation(
                db=db,
                job_id=test_job_id,
                source_photo_bytes=source_bytes,
                panels=panels,
                style="cartoon_fun",
                model_used="test_model"
            )
            
            # Check results
            assert len(results) == 2, f"Expected 2 results, got {len(results)}"
            
            # Check log was created
            log = await db.consistency_logs.find_one({"job_id": test_job_id})
            assert log is not None, "Consistency log should be created"
            assert log["total_panels"] == 2
            assert log["style"] == "cartoon_fun"
            assert log["model_used"] == "test_model"
            assert "panel_details" in log
            assert "created_at" in log
            
            print(f"PASS: Consistency validation logged to DB")
            print(f"  - Total panels: {log['total_panels']}")
            print(f"  - Accepted: {log['accepted']}")
            print(f"  - Avg similarity: {log.get('avg_source_similarity', 0)}")
            
        finally:
            # Cleanup
            await db.consistency_logs.delete_many({"job_id": {"$regex": "^TEST_"}})
            client.close()
    
    @pytest.mark.asyncio
    async def test_run_consistency_validation_no_face_source(self):
        """Test run_consistency_validation handles no-face source correctly"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from services.consistency_validator import run_consistency_validation
        
        # Connect to MongoDB
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'creatorstudio_production')
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Load no-face image
        with open('/tmp/test_no_face.jpg', 'rb') as f:
            source_bytes = f.read()
        
        panels = [
            {"panelNumber": 1, "status": "READY", "imageUrl": "data:image/jpeg;base64,/9j/4AAQ"},
        ]
        
        test_job_id = f"TEST_no_face_{os.urandom(4).hex()}"
        
        try:
            results = await run_consistency_validation(
                db=db,
                job_id=test_job_id,
                source_photo_bytes=source_bytes,
                panels=panels,
                style="cartoon_fun"
            )
            
            # All panels should be 'skip' when source has no face
            assert len(results) == 1
            assert results[0]["verdict"] == "skip"
            assert results[0]["reason"] == "source_no_face"
            
            print("PASS: No-face source correctly skips all panels")
            
        finally:
            await db.consistency_logs.delete_many({"job_id": {"$regex": "^TEST_"}})
            client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
