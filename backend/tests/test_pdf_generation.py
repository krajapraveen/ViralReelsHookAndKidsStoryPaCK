"""
PDF Generation Flow Tests
Tests the complete flow: Generate Story -> Create Printable Book -> Download PDF
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@example.com"
TEST_PASSWORD = "Password123!"


class TestPDFGenerationFlow:
    """Test the complete PDF generation flow"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            allow_redirects=True
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_01_login_success(self, auth_token):
        """Test login works and returns token"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Login successful, token length: {len(auth_token)}")
    
    def test_02_generate_story(self, auth_headers):
        """Test story generation endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/generate/story",
            headers=auth_headers,
            json={
                "genre": "Adventure",
                "ageGroup": "4-6",
                "theme": "Friendship",
                "sceneCount": 6
            },
            allow_redirects=True
        )
        
        # Check response
        assert response.status_code == 200, f"Story generation failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Validate response structure
        assert data.get("success") == True, "Story generation not successful"
        assert "generationId" in data, "No generationId in response"
        assert "result" in data, "No result in response"
        
        # Validate story structure
        result = data["result"]
        assert "title" in result, "No title in story"
        assert "scenes" in result, "No scenes in story"
        assert len(result["scenes"]) > 0, "No scenes in story"
        
        # Store generation ID for next tests
        TestPDFGenerationFlow.generation_id = data["generationId"]
        print(f"✓ Story generated: {result.get('title')}")
        print(f"  Generation ID: {data['generationId']}")
        print(f"  Scenes: {len(result['scenes'])}")
    
    def test_03_create_printable_book(self, auth_headers):
        """Test printable book creation endpoint"""
        generation_id = getattr(TestPDFGenerationFlow, 'generation_id', None)
        assert generation_id is not None, "No generation_id from previous test"
        
        response = requests.post(
            f"{BASE_URL}/api/story-tools/printable-book/generate",
            headers=auth_headers,
            params={"generation_id": generation_id},
            allow_redirects=True
        )
        
        # Check response
        assert response.status_code == 200, f"Printable book creation failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Validate response structure
        assert data.get("success") == True, "Printable book creation not successful"
        assert "bookId" in data, "No bookId in response"
        assert "downloadUrl" in data, "No downloadUrl in response"
        assert "pages" in data, "No pages count in response"
        
        # Store book ID for next tests
        TestPDFGenerationFlow.book_id = data["bookId"]
        TestPDFGenerationFlow.download_url = data["downloadUrl"]
        
        print(f"✓ Printable book created: {data['bookId']}")
        print(f"  Title: {data.get('title')}")
        print(f"  Pages: {data.get('pages')}")
        print(f"  Download URL: {data.get('downloadUrl')}")
    
    def test_04_download_pdf(self, auth_headers):
        """Test PDF download endpoint"""
        book_id = getattr(TestPDFGenerationFlow, 'book_id', None)
        assert book_id is not None, "No book_id from previous test"
        
        # Wait a moment for PDF generation
        time.sleep(2)
        
        response = requests.get(
            f"{BASE_URL}/api/story-tools/printable-book/{book_id}/pdf",
            headers=auth_headers,
            allow_redirects=True
        )
        
        # Check response
        assert response.status_code == 200, f"PDF download failed: {response.status_code} - {response.text}"
        
        # Validate PDF content
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Wrong content type: {content_type}"
        
        # Check PDF size (should be > 500KB for proper rendering)
        pdf_size = len(response.content)
        print(f"✓ PDF downloaded successfully")
        print(f"  Size: {pdf_size / 1024:.2f} KB")
        print(f"  Content-Type: {content_type}")
        
        # Validate PDF header (PDF files start with %PDF)
        assert response.content[:4] == b'%PDF', "Invalid PDF header"
        
        # Check minimum size (should be > 50KB at least)
        assert pdf_size > 50 * 1024, f"PDF too small: {pdf_size} bytes"
        
        # Store PDF for analysis
        TestPDFGenerationFlow.pdf_content = response.content
        TestPDFGenerationFlow.pdf_size = pdf_size
    
    def test_05_pdf_structure_validation(self):
        """Validate PDF has proper structure"""
        pdf_content = getattr(TestPDFGenerationFlow, 'pdf_content', None)
        assert pdf_content is not None, "No PDF content from previous test"
        
        # Check PDF contains expected markers
        pdf_text = pdf_content.decode('latin-1', errors='ignore')
        
        # Check for page count (should have multiple pages)
        page_count = pdf_text.count('/Type /Page')
        print(f"✓ PDF structure validation")
        print(f"  Detected pages: {page_count}")
        
        # Should have at least 4 pages (cover + scenes + moral + ending)
        assert page_count >= 4, f"Too few pages in PDF: {page_count}"


class TestContentVault:
    """Test Content Vault endpoints for Kids Story Themes and Moral Templates"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            allow_redirects=True
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_01_content_vault_endpoint(self, auth_headers):
        """Test Content Vault returns all expected data"""
        response = requests.get(
            f"{BASE_URL}/api/content/vault",
            headers=auth_headers,
            allow_redirects=True
        )
        
        assert response.status_code == 200, f"Content vault failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Validate structure
        assert "viral_hooks" in data, "No viral_hooks in response"
        assert "reel_structures" in data, "No reel_structures in response"
        assert "kids_themes" in data, "No kids_themes in response"
        assert "moral_templates" in data, "No moral_templates in response"
        
        print(f"✓ Content Vault endpoint working")
        print(f"  Viral Hooks: {len(data['viral_hooks'])}")
        print(f"  Reel Structures: {len(data['reel_structures'])}")
        print(f"  Kids Themes: {len(data['kids_themes'])}")
        print(f"  Moral Templates: {len(data['moral_templates'])}")
    
    def test_02_kids_themes_structure(self, auth_headers):
        """Test Kids Story Themes have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/content/vault",
            headers=auth_headers,
            allow_redirects=True
        )
        
        data = response.json()
        kids_themes = data.get("kids_themes", [])
        
        assert len(kids_themes) > 0, "No kids themes returned"
        
        # Check first theme structure
        theme = kids_themes[0]
        assert "theme" in theme, "No 'theme' field in kids theme"
        assert "age_group" in theme, "No 'age_group' field in kids theme"
        assert "moral" in theme, "No 'moral' field in kids theme"
        
        print(f"✓ Kids Themes structure valid")
        print(f"  Sample theme: {theme.get('theme')}")
        print(f"  Age group: {theme.get('age_group')}")
    
    def test_03_moral_templates_structure(self, auth_headers):
        """Test Moral Templates have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/content/vault",
            headers=auth_headers,
            allow_redirects=True
        )
        
        data = response.json()
        moral_templates = data.get("moral_templates", [])
        
        assert len(moral_templates) > 0, "No moral templates returned"
        
        # Check first template structure
        template = moral_templates[0]
        assert "theme" in template, "No 'theme' field in moral template"
        assert "moral" in template, "No 'moral' field in moral template"
        
        print(f"✓ Moral Templates structure valid")
        print(f"  Sample theme: {template.get('theme')}")
        print(f"  Sample moral: {template.get('moral')[:50]}...")
    
    def test_04_reel_structures_best_for(self, auth_headers):
        """Test Reel Structures have best_for field"""
        response = requests.get(
            f"{BASE_URL}/api/content/vault",
            headers=auth_headers,
            allow_redirects=True
        )
        
        data = response.json()
        reel_structures = data.get("reel_structures", [])
        
        assert len(reel_structures) > 0, "No reel structures returned"
        
        # Check first structure has best_for
        structure = reel_structures[0]
        assert "name" in structure, "No 'name' field in reel structure"
        assert "structure" in structure, "No 'structure' field in reel structure"
        assert "best_for" in structure, "No 'best_for' field in reel structure"
        
        print(f"✓ Reel Structures have best_for field")
        print(f"  Sample name: {structure.get('name')}")
        print(f"  Best for: {structure.get('best_for')}")


class TestExistingGenerations:
    """Test using existing generations for PDF download"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            allow_redirects=True
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_01_get_existing_generations(self, auth_headers):
        """Test fetching existing story generations"""
        response = requests.get(
            f"{BASE_URL}/api/generate/generations",
            headers=auth_headers,
            params={"type": "STORY"},
            allow_redirects=True
        )
        
        assert response.status_code == 200, f"Get generations failed: {response.status_code}"
        data = response.json()
        
        assert "content" in data, "No content in response"
        generations = data["content"]
        
        print(f"✓ Found {len(generations)} story generations")
        
        if generations:
            gen = generations[0]
            print(f"  Latest: {gen.get('outputJson', {}).get('title', 'Unknown')}")
            TestExistingGenerations.existing_generation_id = gen.get("id")
    
    def test_02_create_book_from_existing(self, auth_headers):
        """Test creating printable book from existing generation"""
        generation_id = getattr(TestExistingGenerations, 'existing_generation_id', None)
        
        if not generation_id:
            pytest.skip("No existing generation found")
        
        response = requests.post(
            f"{BASE_URL}/api/story-tools/printable-book/generate",
            headers=auth_headers,
            params={"generation_id": generation_id},
            allow_redirects=True
        )
        
        # May fail due to insufficient credits - that's OK
        if response.status_code == 400 and "credits" in response.text.lower():
            pytest.skip("Insufficient credits for test")
        
        assert response.status_code == 200, f"Book creation failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "bookId" in data
        
        TestExistingGenerations.book_id = data["bookId"]
        print(f"✓ Book created from existing generation: {data['bookId']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
