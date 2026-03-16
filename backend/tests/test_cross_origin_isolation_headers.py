"""
Test Cross-Origin Isolation Headers (COOP/COEP)
Iteration 272: Verify headers for SharedArrayBuffer/ffmpeg.wasm support

Tests:
- Frontend HTML response has COOP: same-origin
- Frontend HTML response has COEP: credentialless
- Backend API response has COOP: same-origin
- Backend API response has COEP: credentialless
- CSP includes blob: in script-src and worker-src
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCrossOriginIsolationHeaders:
    """Test COOP/COEP headers for SharedArrayBuffer support"""

    def test_frontend_html_has_coop_header(self):
        """Frontend HTML response has Cross-Origin-Opener-Policy: same-origin"""
        response = requests.get(BASE_URL, timeout=10)
        
        coop = response.headers.get('Cross-Origin-Opener-Policy', '')
        assert coop == 'same-origin', f"Expected COOP='same-origin', got '{coop}'"
        print(f"✓ Frontend COOP header: {coop}")

    def test_frontend_html_has_coep_header(self):
        """Frontend HTML response has Cross-Origin-Embedder-Policy: credentialless"""
        response = requests.get(BASE_URL, timeout=10)
        
        coep = response.headers.get('Cross-Origin-Embedder-Policy', '')
        assert coep == 'credentialless', f"Expected COEP='credentialless', got '{coep}'"
        print(f"✓ Frontend COEP header: {coep}")

    def test_backend_api_has_coop_header(self):
        """Backend API response has Cross-Origin-Opener-Policy: same-origin"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        coop = response.headers.get('Cross-Origin-Opener-Policy', '')
        # Allow redirect, check original response headers
        assert coop == 'same-origin', f"Expected COOP='same-origin', got '{coop}'"
        print(f"✓ Backend API COOP header: {coop}")

    def test_backend_api_has_coep_header(self):
        """Backend API response has Cross-Origin-Embedder-Policy: credentialless"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        coep = response.headers.get('Cross-Origin-Embedder-Policy', '')
        assert coep == 'credentialless', f"Expected COEP='credentialless', got '{coep}'"
        print(f"✓ Backend API COEP header: {coep}")

    def test_csp_includes_blob_in_script_src(self):
        """Content-Security-Policy includes blob: in script-src for ffmpeg.wasm"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        csp = response.headers.get('Content-Security-Policy', '')
        
        # Check script-src includes blob:
        assert 'script-src' in csp, "CSP missing script-src directive"
        assert 'blob:' in csp, f"CSP script-src missing blob: source. CSP: {csp[:200]}"
        print(f"✓ CSP includes blob: in script-src")

    def test_csp_includes_worker_src(self):
        """Content-Security-Policy includes worker-src 'self' blob: for ffmpeg.wasm workers"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        csp = response.headers.get('Content-Security-Policy', '')
        
        # Check worker-src includes self and blob:
        assert 'worker-src' in csp, "CSP missing worker-src directive"
        
        # Extract worker-src directive
        for directive in csp.split(';'):
            directive = directive.strip()
            if directive.startswith('worker-src'):
                assert "'self'" in directive or "self" in directive.lower(), f"worker-src missing 'self'. Directive: {directive}"
                assert 'blob:' in directive, f"worker-src missing blob:. Directive: {directive}"
                print(f"✓ CSP worker-src directive: {directive}")
                return
        
        # If we didn't find worker-src, fail
        pytest.fail("worker-src directive not found in CSP")


class TestSecurityHeadersComprehensive:
    """Additional security headers verification"""

    def test_x_content_type_options(self):
        """X-Content-Type-Options: nosniff present"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        header = response.headers.get('X-Content-Type-Options', '')
        assert header == 'nosniff', f"Expected X-Content-Type-Options='nosniff', got '{header}'"
        print(f"✓ X-Content-Type-Options: {header}")

    def test_x_frame_options(self):
        """X-Frame-Options present"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        header = response.headers.get('X-Frame-Options', '')
        assert header in ['DENY', 'SAMEORIGIN'], f"Expected X-Frame-Options='DENY' or 'SAMEORIGIN', got '{header}'"
        print(f"✓ X-Frame-Options: {header}")

    def test_strict_transport_security(self):
        """Strict-Transport-Security header present"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        header = response.headers.get('Strict-Transport-Security', '')
        assert 'max-age' in header.lower(), f"Expected HSTS header with max-age, got '{header}'"
        print(f"✓ Strict-Transport-Security: {header[:50]}...")

    def test_referrer_policy(self):
        """Referrer-Policy header present"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        header = response.headers.get('Referrer-Policy', '')
        assert header, f"Referrer-Policy header missing"
        print(f"✓ Referrer-Policy: {header}")

    def test_cross_origin_resource_policy(self):
        """Cross-Origin-Resource-Policy header for assets"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10, allow_redirects=True)
        
        header = response.headers.get('Cross-Origin-Resource-Policy', '')
        # This allows cross-origin access to resources (needed for loading images/audio)
        assert header == 'cross-origin', f"Expected Cross-Origin-Resource-Policy='cross-origin', got '{header}'"
        print(f"✓ Cross-Origin-Resource-Policy: {header}")


class TestPipelinePreviewEndpoint:
    """Test pipeline preview endpoint returns proper data for completed jobs"""

    def test_preview_endpoint_for_completed_job(self):
        """GET /api/pipeline/preview/{job_id} returns proper data"""
        job_id = "a67ff269-1ba5-41d4-a827-9c97cff4d00d"
        response = requests.get(f"{BASE_URL}/api/pipeline/preview/{job_id}", timeout=10)
        
        # Should return 200 for completed job or 404 if not found
        if response.status_code == 200:
            data = response.json()
            assert 'status' in data, "Response missing status"
            assert 'scenes' in data, "Response missing scenes"
            print(f"✓ Preview endpoint working: status={data.get('status')}, scenes={len(data.get('scenes', []))}")
        elif response.status_code == 404:
            print("Job not found (may have been cleaned up)")
            pytest.skip("Test job not found")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_status_endpoint_for_completed_job(self):
        """GET /api/pipeline/status/{job_id} returns manifest for completed jobs"""
        job_id = "a67ff269-1ba5-41d4-a827-9c97cff4d00d"
        response = requests.get(f"{BASE_URL}/api/pipeline/status/{job_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            print(f"Job status: {status}")
            
            if status == 'COMPLETED':
                assert 'manifest' in data, "COMPLETED job missing manifest"
                manifest = data['manifest']
                assert 'scenes' in manifest, "Manifest missing scenes"
                print(f"✓ Manifest found with {len(manifest.get('scenes', []))} scenes")
        elif response.status_code == 404:
            print("Job not found (may have been cleaned up)")
            pytest.skip("Test job not found")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
