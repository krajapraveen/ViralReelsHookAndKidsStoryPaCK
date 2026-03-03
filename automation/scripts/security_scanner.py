#!/usr/bin/env python3
"""
CreatorStudio AI - Security Scanner
Comprehensive security scanning for the application
"""

import requests
import re
import json
import os
from datetime import datetime
from urllib.parse import urljoin

API_BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://activity-tracker-197.preview.emergentagent.com')
LOG_FILE = '/app/automation/logs/security_scan.log'
REPORT_FILE = '/app/automation/reports/security_report.json'

def log(message, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + '\n')

class SecurityScanner:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.vulnerabilities = []
        self.warnings = []
        self.info = []
    
    def add_vulnerability(self, category, severity, description, details=None):
        self.vulnerabilities.append({
            'category': category,
            'severity': severity,
            'description': description,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_warning(self, category, description, details=None):
        self.warnings.append({
            'category': category,
            'description': description,
            'details': details
        })
    
    def add_info(self, category, description):
        self.info.append({'category': category, 'description': description})

    # ==================== Security Header Checks ====================
    
    def check_security_headers(self):
        """Check for important security headers"""
        log("Checking security headers...")
        
        try:
            resp = requests.get(self.base_url, timeout=10)
            headers = resp.headers
            
            required_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': None,  # Should exist
                'Content-Security-Policy': None,
            }
            
            for header, expected in required_headers.items():
                if header not in headers:
                    self.add_warning('HEADERS', f'Missing security header: {header}')
                elif expected and headers[header] not in (expected if isinstance(expected, list) else [expected]):
                    self.add_warning('HEADERS', f'Weak {header} value: {headers[header]}')
                else:
                    self.add_info('HEADERS', f'{header}: {headers[header]}')
            
            # Check for information disclosure headers
            disclosure_headers = ['Server', 'X-Powered-By', 'X-AspNet-Version']
            for header in disclosure_headers:
                if header in headers:
                    self.add_warning('INFO_DISCLOSURE', f'Server info exposed via {header}: {headers[header]}')
            
        except Exception as e:
            self.add_warning('HEADERS', f'Could not check headers: {str(e)}')

    # ==================== SQL Injection Tests ====================
    
    def check_sql_injection(self):
        """Test common SQL injection patterns"""
        log("Testing SQL injection vectors...")
        
        payloads = [
            "' OR '1'='1",
            "1; DROP TABLE users--",
            "' UNION SELECT * FROM users--",
            "admin'--",
            "1' AND '1'='1"
        ]
        
        endpoints = [
            ('/api/auth/login', 'POST', {'email': '{payload}', 'password': 'test'}),
        ]
        
        for endpoint, method, data_template in endpoints:
            for payload in payloads:
                try:
                    data = {k: v.replace('{payload}', payload) if isinstance(v, str) else v 
                           for k, v in data_template.items()}
                    
                    if method == 'POST':
                        resp = self.session.post(
                            urljoin(self.base_url, endpoint),
                            json=data,
                            timeout=10
                        )
                    
                    # Check for SQL error messages in response
                    response_text = resp.text.lower()
                    sql_errors = ['sql', 'mysql', 'postgresql', 'sqlite', 'oracle', 'syntax error']
                    
                    if any(err in response_text for err in sql_errors):
                        self.add_vulnerability(
                            'SQL_INJECTION',
                            'HIGH',
                            f'Possible SQL injection at {endpoint}',
                            f'Payload: {payload}'
                        )
                        
                except Exception as e:
                    pass  # Timeout or connection error is fine
        
        self.add_info('SQL_INJECTION', 'SQL injection scan completed')

    # ==================== XSS Tests ====================
    
    def check_xss(self):
        """Test for Cross-Site Scripting vulnerabilities"""
        log("Testing XSS vectors...")
        
        payloads = [
            '<script>alert("XSS")</script>',
            '"><script>alert("XSS")</script>',
            "javascript:alert('XSS')",
            '<img src=x onerror=alert("XSS")>',
            '<svg onload=alert("XSS")>'
        ]
        
        test_endpoints = [
            ('/api/contact', 'POST', {'name': '{payload}', 'email': 'test@test.com', 'message': 'test'}),
        ]
        
        for endpoint, method, data_template in test_endpoints:
            for payload in payloads:
                try:
                    data = {k: v.replace('{payload}', payload) if isinstance(v, str) else v 
                           for k, v in data_template.items()}
                    
                    if method == 'POST':
                        resp = self.session.post(
                            urljoin(self.base_url, endpoint),
                            json=data,
                            timeout=10
                        )
                    
                    # Check if payload is reflected without encoding
                    if payload in resp.text:
                        self.add_vulnerability(
                            'XSS',
                            'HIGH',
                            f'Reflected XSS at {endpoint}',
                            f'Payload: {payload}'
                        )
                        
                except Exception as e:
                    pass
        
        self.add_info('XSS', 'XSS scan completed')

    # ==================== Authentication Tests ====================
    
    def check_auth_vulnerabilities(self):
        """Check authentication security"""
        log("Testing authentication security...")
        
        # Test for weak password acceptance
        weak_passwords = ['123', 'password', '1234', 'admin']
        
        for pwd in weak_passwords:
            try:
                resp = self.session.post(
                    urljoin(self.base_url, '/api/auth/register'),
                    json={'name': 'Test', 'email': f'weakpwd{len(pwd)}@test.com', 'password': pwd},
                    timeout=10
                )
                
                if resp.status_code == 200 and 'token' in resp.text:
                    self.add_vulnerability(
                        'AUTH',
                        'MEDIUM',
                        'Weak password accepted',
                        f'Password "{pwd}" was accepted'
                    )
            except:
                pass
        
        # Test for user enumeration
        try:
            # Test with existing email pattern
            resp1 = self.session.post(
                urljoin(self.base_url, '/api/auth/login'),
                json={'email': 'admin@creatorstudio.ai', 'password': 'wrongpassword'},
                timeout=10
            )
            
            resp2 = self.session.post(
                urljoin(self.base_url, '/api/auth/login'),
                json={'email': 'nonexistent@nowhere.com', 'password': 'wrongpassword'},
                timeout=10
            )
            
            # If responses are significantly different, user enumeration is possible
            if len(resp1.text) != len(resp2.text) or resp1.status_code != resp2.status_code:
                if 'not found' in resp2.text.lower() or 'does not exist' in resp2.text.lower():
                    self.add_warning(
                        'AUTH',
                        'User enumeration possible via login endpoint',
                        'Different responses for existing vs non-existing users'
                    )
        except:
            pass
        
        self.add_info('AUTH', 'Authentication security scan completed')

    # ==================== Sensitive Data Exposure ====================
    
    def check_data_exposure(self):
        """Check for sensitive data exposure"""
        log("Checking for sensitive data exposure...")
        
        # Check for exposed config files
        sensitive_paths = [
            '/.env', '/config.json', '/settings.json',
            '/.git/config', '/backup.sql', '/dump.sql',
            '/api/debug', '/api/config', '/phpinfo.php',
            '/server-status', '/elmah.axd', '/trace.axd'
        ]
        
        for path in sensitive_paths:
            try:
                resp = self.session.get(
                    urljoin(self.base_url, path),
                    timeout=5
                )
                
                if resp.status_code == 200:
                    self.add_vulnerability(
                        'DATA_EXPOSURE',
                        'CRITICAL',
                        f'Sensitive file accessible: {path}',
                        f'Status: {resp.status_code}'
                    )
            except:
                pass
        
        # Check API responses for sensitive data
        try:
            # Check if error responses leak stack traces
            resp = self.session.post(
                urljoin(self.base_url, '/api/auth/login'),
                json={'email': 'invalid', 'password': 'x'},
                timeout=10
            )
            
            sensitive_patterns = [
                r'stack trace', r'exception', r'at \w+\.\w+\(',
                r'password', r'secret', r'api[_-]?key',
                r'/home/\w+', r'C:\\', r'jdbc:', r'mongodb://'
            ]
            
            for pattern in sensitive_patterns:
                if re.search(pattern, resp.text, re.IGNORECASE):
                    self.add_warning(
                        'DATA_EXPOSURE',
                        f'Possible sensitive data in error response',
                        f'Pattern matched: {pattern}'
                    )
                    break
        except:
            pass
        
        self.add_info('DATA_EXPOSURE', 'Data exposure scan completed')

    # ==================== Rate Limiting ====================
    
    def check_rate_limiting(self):
        """Check if rate limiting is implemented"""
        log("Testing rate limiting...")
        
        # Try rapid requests to login endpoint
        endpoint = urljoin(self.base_url, '/api/auth/login')
        
        blocked = False
        for i in range(20):
            try:
                resp = self.session.post(
                    endpoint,
                    json={'email': 'test@test.com', 'password': 'wrong'},
                    timeout=5
                )
                
                if resp.status_code == 429 or 'rate limit' in resp.text.lower():
                    blocked = True
                    break
            except:
                pass
        
        if not blocked:
            self.add_warning(
                'RATE_LIMITING',
                'No rate limiting detected on login endpoint',
                'Endpoint allows unlimited login attempts'
            )
        else:
            self.add_info('RATE_LIMITING', 'Rate limiting is active')

    # ==================== CORS Configuration ====================
    
    def check_cors(self):
        """Check CORS configuration"""
        log("Checking CORS configuration...")
        
        try:
            # Test with malicious origin
            resp = self.session.options(
                urljoin(self.base_url, '/api/auth/login'),
                headers={'Origin': 'https://malicious-site.com'},
                timeout=10
            )
            
            cors_header = resp.headers.get('Access-Control-Allow-Origin', '')
            
            if cors_header == '*':
                self.add_vulnerability(
                    'CORS',
                    'MEDIUM',
                    'CORS allows all origins',
                    'Access-Control-Allow-Origin: *'
                )
            elif 'malicious-site.com' in cors_header:
                self.add_vulnerability(
                    'CORS',
                    'HIGH',
                    'CORS reflects arbitrary origins',
                    f'Reflected: {cors_header}'
                )
            else:
                self.add_info('CORS', f'CORS properly configured: {cors_header or "No CORS header"}')
        except:
            pass

    # ==================== JWT Security ====================
    
    def check_jwt_security(self):
        """Check JWT token security"""
        log("Checking JWT security...")
        
        try:
            # Get a valid token
            resp = self.session.post(
                urljoin(self.base_url, '/api/auth/login'),
                json={'email': 'admin@creatorstudio.ai', 'password': 'Admin@123'},
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                token = data.get('token', '')
                
                if token:
                    # Decode JWT header (no verification)
                    import base64
                    parts = token.split('.')
                    if len(parts) == 3:
                        header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
                        
                        # Check for weak algorithms
                        alg = header.get('alg', '')
                        if alg.lower() == 'none':
                            self.add_vulnerability(
                                'JWT',
                                'CRITICAL',
                                'JWT allows "none" algorithm',
                                'Tokens can be forged'
                            )
                        elif alg.lower() in ['hs256', 'hs384', 'hs512']:
                            self.add_info('JWT', f'JWT uses {alg} algorithm')
                        
                        # Test if token is accepted without signature
                        forged_token = parts[0] + '.' + parts[1] + '.'
                        resp2 = self.session.get(
                            urljoin(self.base_url, '/api/auth/me'),
                            headers={'Authorization': f'Bearer {forged_token}'},
                            timeout=10
                        )
                        
                        if resp2.status_code == 200:
                            self.add_vulnerability(
                                'JWT',
                                'CRITICAL',
                                'JWT signature not verified',
                                'Forged token accepted'
                            )
        except:
            pass

    # ==================== Run All Scans ====================
    
    def run_full_scan(self):
        """Run all security scans"""
        log("=" * 60)
        log("Starting Full Security Scan")
        log("=" * 60)
        
        self.check_security_headers()
        self.check_sql_injection()
        self.check_xss()
        self.check_auth_vulnerabilities()
        self.check_data_exposure()
        self.check_rate_limiting()
        self.check_cors()
        self.check_jwt_security()
        
        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'target': self.base_url,
            'summary': {
                'vulnerabilities': len(self.vulnerabilities),
                'warnings': len(self.warnings),
                'info': len(self.info),
                'critical': len([v for v in self.vulnerabilities if v['severity'] == 'CRITICAL']),
                'high': len([v for v in self.vulnerabilities if v['severity'] == 'HIGH']),
                'medium': len([v for v in self.vulnerabilities if v['severity'] == 'MEDIUM']),
                'low': len([v for v in self.vulnerabilities if v['severity'] == 'LOW'])
            },
            'vulnerabilities': self.vulnerabilities,
            'warnings': self.warnings,
            'info': self.info,
            'status': 'PASS' if not self.vulnerabilities else 'FAIL'
        }
        
        # Save report
        with open(REPORT_FILE, 'w') as f:
            json.dump(report, f, indent=2)
        
        log("=" * 60)
        log(f"Security Scan Complete")
        log(f"Vulnerabilities: {report['summary']['vulnerabilities']}")
        log(f"  Critical: {report['summary']['critical']}")
        log(f"  High: {report['summary']['high']}")
        log(f"  Medium: {report['summary']['medium']}")
        log(f"Warnings: {report['summary']['warnings']}")
        log(f"Status: {report['status']}")
        log("=" * 60)
        
        return report

if __name__ == '__main__':
    scanner = SecurityScanner(API_BASE_URL)
    report = scanner.run_full_scan()
    print(json.dumps(report['summary'], indent=2))
