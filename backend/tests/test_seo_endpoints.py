"""
SEO & Google Indexing Readiness Tests
Tests for sitemap.xml, robots.txt, and meta tag implementation
"""
import pytest
import requests
import os
import xml.etree.ElementTree as ET

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')
PRODUCTION_DOMAIN = "https://www.visionary-suite.com"


class TestRobotsTxt:
    """Tests for /api/public/robots.txt endpoint"""
    
    def test_robots_txt_returns_200(self):
        """Verify robots.txt endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/public/robots.txt")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: robots.txt returns 200 OK")
    
    def test_robots_txt_content_type(self):
        """Verify robots.txt returns text/plain content type"""
        response = requests.get(f"{BASE_URL}/api/public/robots.txt")
        content_type = response.headers.get('content-type', '')
        assert 'text/plain' in content_type, f"Expected text/plain, got {content_type}"
        print("PASS: robots.txt content-type is text/plain")
    
    def test_robots_txt_has_user_agent(self):
        """Verify robots.txt contains User-agent directive"""
        response = requests.get(f"{BASE_URL}/api/public/robots.txt")
        content = response.text
        assert "User-agent: *" in content, "Missing User-agent: * directive"
        print("PASS: robots.txt contains User-agent: *")
    
    def test_robots_txt_allow_rules(self):
        """Verify robots.txt has correct Allow rules"""
        response = requests.get(f"{BASE_URL}/api/public/robots.txt")
        content = response.text
        
        expected_allows = [
            "Allow: /",
            "Allow: /explore",
            "Allow: /pricing",
            "Allow: /blog",
            "Allow: /about",
            "Allow: /contact",
            "Allow: /reviews",
            "Allow: /gallery",
            "Allow: /v/",
            "Allow: /creator/",
            "Allow: /series/",
            "Allow: /character/",
            "Allow: /experience",
        ]
        
        for allow in expected_allows:
            assert allow in content, f"Missing: {allow}"
        print(f"PASS: robots.txt contains all {len(expected_allows)} Allow rules")
    
    def test_robots_txt_disallow_rules(self):
        """Verify robots.txt has correct Disallow rules"""
        response = requests.get(f"{BASE_URL}/api/public/robots.txt")
        content = response.text
        
        expected_disallows = [
            "Disallow: /app/",
            "Disallow: /api/",
            "Disallow: /login",
            "Disallow: /signup",
        ]
        
        for disallow in expected_disallows:
            assert disallow in content, f"Missing: {disallow}"
        print(f"PASS: robots.txt contains all {len(expected_disallows)} Disallow rules")
    
    def test_robots_txt_sitemap_directive(self):
        """Verify robots.txt contains Sitemap directive with production URL"""
        response = requests.get(f"{BASE_URL}/api/public/robots.txt")
        content = response.text
        
        expected_sitemap = f"Sitemap: {PRODUCTION_DOMAIN}/api/public/sitemap.xml"
        assert expected_sitemap in content, f"Missing or incorrect Sitemap directive. Expected: {expected_sitemap}"
        print(f"PASS: robots.txt contains correct Sitemap directive: {expected_sitemap}")
    
    def test_robots_txt_no_preview_url(self):
        """Verify robots.txt does not contain preview.emergentagent.com URLs"""
        response = requests.get(f"{BASE_URL}/api/public/robots.txt")
        content = response.text
        
        assert "preview.emergentagent.com" not in content, "Found preview URL in robots.txt"
        print("PASS: robots.txt contains no preview.emergentagent.com URLs")


class TestSitemapXml:
    """Tests for /api/public/sitemap.xml endpoint"""
    
    def test_sitemap_returns_200(self):
        """Verify sitemap.xml endpoint returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: sitemap.xml returns 200 OK")
    
    def test_sitemap_content_type(self):
        """Verify sitemap.xml returns application/xml content type"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        content_type = response.headers.get('content-type', '')
        assert 'application/xml' in content_type, f"Expected application/xml, got {content_type}"
        print("PASS: sitemap.xml content-type is application/xml")
    
    def test_sitemap_is_valid_xml(self):
        """Verify sitemap.xml is valid XML"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        try:
            ET.fromstring(response.content)
            print("PASS: sitemap.xml is valid XML")
        except ET.ParseError as e:
            pytest.fail(f"Invalid XML: {e}")
    
    def test_sitemap_has_urlset_root(self):
        """Verify sitemap.xml has urlset root element"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        root = ET.fromstring(response.content)
        
        # Handle namespace
        assert 'urlset' in root.tag, f"Expected urlset root, got {root.tag}"
        print("PASS: sitemap.xml has urlset root element")
    
    def test_sitemap_has_100_plus_urls(self):
        """Verify sitemap.xml contains 100+ URLs"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        root = ET.fromstring(response.content)
        
        # Count url elements (handle namespace)
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = root.findall('.//sm:url', ns)
        
        url_count = len(urls)
        assert url_count >= 100, f"Expected 100+ URLs, got {url_count}"
        print(f"PASS: sitemap.xml contains {url_count} URLs (>= 100)")
    
    def test_sitemap_static_pages(self):
        """Verify sitemap.xml contains all required static pages"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        content = response.text
        
        static_pages = [
            f"{PRODUCTION_DOMAIN}",  # Homepage
            f"{PRODUCTION_DOMAIN}/explore",
            f"{PRODUCTION_DOMAIN}/gallery",
            f"{PRODUCTION_DOMAIN}/pricing",
            f"{PRODUCTION_DOMAIN}/blog",
            f"{PRODUCTION_DOMAIN}/about",
            f"{PRODUCTION_DOMAIN}/contact",
            f"{PRODUCTION_DOMAIN}/reviews",
            f"{PRODUCTION_DOMAIN}/experience",
            f"{PRODUCTION_DOMAIN}/user-manual",
            f"{PRODUCTION_DOMAIN}/privacy-policy",
            f"{PRODUCTION_DOMAIN}/terms-of-service",
            f"{PRODUCTION_DOMAIN}/cookie-policy",
        ]
        
        for page in static_pages:
            assert page in content, f"Missing static page: {page}"
        print(f"PASS: sitemap.xml contains all {len(static_pages)} static pages")
    
    def test_sitemap_blog_posts(self):
        """Verify sitemap.xml contains blog post URLs"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        content = response.text
        
        # Check for at least one blog post URL pattern
        assert f"{PRODUCTION_DOMAIN}/blog/ai-story-video-creator-guide-2026" in content, \
            "Missing blog post: ai-story-video-creator-guide-2026"
        print("PASS: sitemap.xml contains blog post URLs")
    
    def test_sitemap_dynamic_content_urls(self):
        """Verify sitemap.xml contains dynamic content URLs (/v/ pipeline jobs)"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        content = response.text
        
        # Check for /v/ URLs (pipeline jobs)
        assert f"{PRODUCTION_DOMAIN}/v/" in content, "Missing /v/ (pipeline job) URLs"
        print("PASS: sitemap.xml contains /v/ (pipeline job) URLs")
    
    def test_sitemap_no_preview_urls(self):
        """Verify sitemap.xml does not contain preview.emergentagent.com URLs"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        content = response.text
        
        assert "preview.emergentagent.com" not in content, "Found preview URL in sitemap.xml"
        print("PASS: sitemap.xml contains no preview.emergentagent.com URLs")
    
    def test_sitemap_all_urls_use_production_domain(self):
        """Verify all URLs in sitemap use production domain"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        root = ET.fromstring(response.content)
        
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = root.findall('.//sm:loc', ns)
        
        for url_elem in urls:
            url = url_elem.text
            assert url.startswith(PRODUCTION_DOMAIN), f"URL does not use production domain: {url}"
        
        print(f"PASS: All {len(urls)} URLs use production domain {PRODUCTION_DOMAIN}")
    
    def test_sitemap_url_structure(self):
        """Verify sitemap URLs have required elements (loc, lastmod, changefreq, priority)"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        root = ET.fromstring(response.content)
        
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = root.findall('.//sm:url', ns)
        
        # Check first 5 URLs for structure
        for url in urls[:5]:
            loc = url.find('sm:loc', ns)
            lastmod = url.find('sm:lastmod', ns)
            changefreq = url.find('sm:changefreq', ns)
            priority = url.find('sm:priority', ns)
            
            assert loc is not None, "Missing <loc> element"
            assert lastmod is not None, "Missing <lastmod> element"
            assert changefreq is not None, "Missing <changefreq> element"
            assert priority is not None, "Missing <priority> element"
        
        print("PASS: sitemap URLs have proper structure (loc, lastmod, changefreq, priority)")


class TestFrontendSEO:
    """Tests for frontend SEO implementation"""
    
    def test_frontend_loads(self):
        """Verify frontend loads successfully"""
        response = requests.get(BASE_URL, timeout=10)
        assert response.status_code == 200, f"Frontend failed to load: {response.status_code}"
        print("PASS: Frontend loads successfully")
    
    def test_index_html_has_json_ld(self):
        """Verify index.html contains JSON-LD structured data"""
        response = requests.get(BASE_URL, timeout=10)
        content = response.text
        
        # Check for JSON-LD script tags
        assert 'application/ld+json' in content, "Missing JSON-LD script tags"
        print("PASS: index.html contains JSON-LD structured data")
    
    def test_index_html_has_website_schema(self):
        """Verify index.html contains WebSite schema"""
        response = requests.get(BASE_URL, timeout=10)
        content = response.text
        
        assert '"@type": "WebSite"' in content or '"@type":"WebSite"' in content, \
            "Missing WebSite schema"
        print("PASS: index.html contains WebSite schema")
    
    def test_index_html_has_organization_schema(self):
        """Verify index.html contains Organization schema"""
        response = requests.get(BASE_URL, timeout=10)
        content = response.text
        
        assert '"@type": "Organization"' in content or '"@type":"Organization"' in content, \
            "Missing Organization schema"
        print("PASS: index.html contains Organization schema")
    
    def test_index_html_has_software_application_schema(self):
        """Verify index.html contains SoftwareApplication schema"""
        response = requests.get(BASE_URL, timeout=10)
        content = response.text
        
        assert '"@type": "SoftwareApplication"' in content or '"@type":"SoftwareApplication"' in content, \
            "Missing SoftwareApplication schema"
        print("PASS: index.html contains SoftwareApplication schema")
    
    def test_index_html_has_canonical_url(self):
        """Verify index.html contains canonical URL"""
        response = requests.get(BASE_URL, timeout=10)
        content = response.text
        
        assert 'rel="canonical"' in content, "Missing canonical link tag"
        assert PRODUCTION_DOMAIN in content, f"Canonical URL should use {PRODUCTION_DOMAIN}"
        print("PASS: index.html contains canonical URL")
    
    def test_index_html_has_og_tags(self):
        """Verify index.html contains Open Graph meta tags"""
        response = requests.get(BASE_URL, timeout=10)
        content = response.text
        
        og_tags = [
            'property="og:type"',
            'property="og:url"',
            'property="og:title"',
            'property="og:description"',
            'property="og:image"',
        ]
        
        for tag in og_tags:
            assert tag in content, f"Missing OG tag: {tag}"
        print(f"PASS: index.html contains all {len(og_tags)} Open Graph tags")
    
    def test_index_html_has_twitter_tags(self):
        """Verify index.html contains Twitter Card meta tags"""
        response = requests.get(BASE_URL, timeout=10)
        content = response.text
        
        twitter_tags = [
            'property="twitter:card"',
            'property="twitter:title"',
            'property="twitter:description"',
            'property="twitter:image"',
        ]
        
        for tag in twitter_tags:
            assert tag in content, f"Missing Twitter tag: {tag}"
        print(f"PASS: index.html contains all {len(twitter_tags)} Twitter Card tags")


class TestStaticRobotsTxt:
    """Tests for static robots.txt in frontend/public/"""
    
    def test_static_robots_txt_exists(self):
        """Verify static robots.txt exists as backup"""
        # This tests the static file served by frontend
        response = requests.get(f"{BASE_URL}/robots.txt", timeout=10)
        # May return 200 or redirect to API endpoint
        assert response.status_code in [200, 301, 302], f"Static robots.txt issue: {response.status_code}"
        print("PASS: Static robots.txt accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
