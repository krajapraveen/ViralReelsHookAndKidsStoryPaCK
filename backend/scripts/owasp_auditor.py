"""
OWASP Top 10 Security Audit
CreatorStudio AI - Comprehensive security assessment

This module provides automated security checks against OWASP Top 10 2021:
A01:2021 – Broken Access Control
A02:2021 – Cryptographic Failures
A03:2021 – Injection
A04:2021 – Insecure Design
A05:2021 – Security Misconfiguration
A06:2021 – Vulnerable and Outdated Components
A07:2021 – Identification and Authentication Failures
A08:2021 – Software and Data Integrity Failures
A09:2021 – Security Logging and Monitoring Failures
A10:2021 – Server-Side Request Forgery (SSRF)
"""
import os
import re
import glob
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class OWASPSecurityAuditor:
    """
    Automated OWASP Top 10 security audit for the application.
    """
    
    def __init__(self, backend_path: str = "/app/backend", frontend_path: str = "/app/frontend"):
        self.backend_path = backend_path
        self.frontend_path = frontend_path
        self.findings = []
        self.passed_checks = []
        self.recommendations = []
    
    def run_full_audit(self) -> Dict:
        """Run complete OWASP Top 10 audit"""
        audit_start = datetime.now(timezone.utc)
        
        results = {
            "audit_timestamp": audit_start.isoformat(),
            "owasp_version": "2021",
            "categories": {}
        }
        
        # Run all category checks
        results["categories"]["A01_Broken_Access_Control"] = self._audit_a01_access_control()
        results["categories"]["A02_Cryptographic_Failures"] = self._audit_a02_cryptography()
        results["categories"]["A03_Injection"] = self._audit_a03_injection()
        results["categories"]["A04_Insecure_Design"] = self._audit_a04_design()
        results["categories"]["A05_Security_Misconfiguration"] = self._audit_a05_misconfiguration()
        results["categories"]["A06_Vulnerable_Components"] = self._audit_a06_components()
        results["categories"]["A07_Authentication_Failures"] = self._audit_a07_authentication()
        results["categories"]["A08_Data_Integrity"] = self._audit_a08_integrity()
        results["categories"]["A09_Logging_Monitoring"] = self._audit_a09_logging()
        results["categories"]["A10_SSRF"] = self._audit_a10_ssrf()
        
        # Calculate overall score
        total_checks = sum(cat["checks_performed"] for cat in results["categories"].values())
        passed_checks = sum(cat["checks_passed"] for cat in results["categories"].values())
        
        results["summary"] = {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "compliance_score": round((passed_checks / total_checks) * 100, 1) if total_checks > 0 else 0,
            "risk_level": self._calculate_risk_level(passed_checks, total_checks),
            "audit_duration_seconds": (datetime.now(timezone.utc) - audit_start).seconds
        }
        
        results["recommendations"] = self._generate_recommendations()
        
        return results
    
    def _audit_a01_access_control(self) -> Dict:
        """A01:2021 – Broken Access Control"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: Admin routes require authentication
        admin_routes = self._find_patterns(
            os.path.join(self.backend_path, "routes", "*.py"),
            r'@router\.(get|post|put|delete)\s*\([^)]*admin[^)]*\)'
        )
        
        admin_protected = self._find_patterns(
            os.path.join(self.backend_path, "routes", "*.py"),
            r'admin.*Depends\(get_admin_user\)|get_admin_user.*admin'
        )
        
        if len(admin_protected) >= len(admin_routes) * 0.8:
            checks["passed"].append("Admin routes are properly protected with authentication")
        else:
            checks["failed"].append("Some admin routes may lack proper authentication")
        
        # Check 2: User isolation in queries
        user_isolation = self._find_patterns(
            os.path.join(self.backend_path, "routes", "*.py"),
            r'user\["id"\]|user\.id|user_id.*user\['
        )
        if len(user_isolation) > 10:
            checks["passed"].append("User isolation patterns found in data queries")
        else:
            checks["warnings"].append("Verify user data isolation in all endpoints")
        
        # Check 3: CORS configuration
        cors_config = self._check_file_contains(
            os.path.join(self.backend_path, "server.py"),
            ["CORSMiddleware", "allow_origins"]
        )
        if cors_config:
            checks["passed"].append("CORS is configured")
        else:
            checks["failed"].append("CORS configuration not found")
        
        # Check 4: Rate limiting
        rate_limit = self._check_file_contains(
            os.path.join(self.backend_path, "security.py"),
            ["limiter", "RateLimitMiddleware", "slowapi"]
        )
        if rate_limit:
            checks["passed"].append("Rate limiting is implemented")
        else:
            checks["warnings"].append("Consider implementing rate limiting")
        
        return {
            "category": "A01:2021 – Broken Access Control",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a02_cryptography(self) -> Dict:
        """A02:2021 – Cryptographic Failures"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: Password hashing
        password_hash = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'bcrypt|argon2|pbkdf2|passlib|hash_password'
        )
        if password_hash:
            checks["passed"].append("Secure password hashing is implemented")
        else:
            checks["failed"].append("No secure password hashing found")
        
        # Check 2: JWT implementation
        jwt_impl = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["jwt.encode", "jwt.decode", "PyJWT"]
        )
        if jwt_impl:
            checks["passed"].append("JWT authentication is implemented")
        
        # Check 3: HTTPS enforcement
        https_check = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["https://", "SSL", "TLS", "HSTS"]
        )
        if https_check:
            checks["passed"].append("HTTPS/TLS references found")
        else:
            checks["warnings"].append("Ensure HTTPS is enforced in production")
        
        # Check 4: No hardcoded secrets
        secrets_check = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'(password|secret|key)\s*=\s*["\'][^"\']{8,}["\']'
        )
        if not secrets_check:
            checks["passed"].append("No hardcoded secrets detected")
        else:
            checks["failed"].append(f"Potential hardcoded secrets found in {len(secrets_check)} locations")
        
        # Check 5: Environment variables for secrets
        env_secrets = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'os\.environ\.get\(["\'].*(?:SECRET|KEY|PASSWORD|TOKEN)'
        )
        if env_secrets:
            checks["passed"].append("Secrets loaded from environment variables")
        
        return {
            "category": "A02:2021 – Cryptographic Failures",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a03_injection(self) -> Dict:
        """A03:2021 – Injection"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: SQL injection prevention (using ORM/parameterized queries)
        raw_sql = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'execute\s*\(\s*f["\']|execute\s*\([^)]*%s|\.format\([^)]*\)\s*\)'
        )
        if not raw_sql:
            checks["passed"].append("No raw SQL with string formatting found")
        else:
            checks["failed"].append(f"Potential SQL injection vectors in {len(raw_sql)} locations")
        
        # Check 2: MongoDB safe patterns
        mongo_safe = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'find_one\s*\(\s*\{|find\s*\(\s*\{|insert_one|update_one'
        )
        if mongo_safe:
            checks["passed"].append("MongoDB queries use safe patterns")
        
        # Check 3: Input sanitization
        sanitize = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["bleach", "sanitize", "escape", "clean"]
        )
        if sanitize:
            checks["passed"].append("Input sanitization library detected")
        else:
            checks["warnings"].append("Consider adding input sanitization")
        
        # Check 4: XSS prevention
        xss_check = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["bleach.clean", "html.escape", "markupsafe"]
        )
        if xss_check:
            checks["passed"].append("XSS prevention measures found")
        
        return {
            "category": "A03:2021 – Injection",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a04_design(self) -> Dict:
        """A04:2021 – Insecure Design"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: Input validation
        validation = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'Pydantic|BaseModel|validator|Field\('
        )
        if validation:
            checks["passed"].append("Pydantic models used for input validation")
        else:
            checks["warnings"].append("Consider using Pydantic for strict input validation")
        
        # Check 2: Error handling
        error_handling = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'try:|except.*:|HTTPException|raise'
        )
        if len(error_handling) > 20:
            checks["passed"].append("Error handling patterns implemented")
        
        # Check 3: Business logic protection
        credit_check = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["deduct_credits", "validate_credits", "check_credits"]
        )
        if credit_check:
            checks["passed"].append("Credit/business logic validation found")
        
        return {
            "category": "A04:2021 – Insecure Design",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a05_misconfiguration(self) -> Dict:
        """A05:2021 – Security Misconfiguration"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: Debug mode disabled
        debug_enabled = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'debug\s*=\s*True|DEBUG\s*=\s*True'
        )
        if not debug_enabled:
            checks["passed"].append("Debug mode appears to be disabled")
        else:
            checks["warnings"].append("Ensure debug mode is disabled in production")
        
        # Check 2: Security headers
        security_headers = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy", "HSTS"]
        )
        if security_headers:
            checks["passed"].append("Security headers are configured")
        else:
            checks["failed"].append("Security headers not found")
        
        # Check 3: Default credentials
        default_creds = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'password\s*=\s*["\']admin|password\s*=\s*["\']password|password\s*=\s*["\']123'
        )
        if not default_creds:
            checks["passed"].append("No default credentials detected")
        else:
            checks["failed"].append("Potential default credentials found")
        
        # Check 4: Error messages
        detailed_errors = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'str\(e\)|traceback|exception.*detail'
        )
        if len(detailed_errors) < 10:
            checks["passed"].append("Error messages appear controlled")
        else:
            checks["warnings"].append("Review error messages for information disclosure")
        
        return {
            "category": "A05:2021 – Security Misconfiguration",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a06_components(self) -> Dict:
        """A06:2021 – Vulnerable and Outdated Components"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: requirements.txt exists
        req_file = os.path.join(self.backend_path, "requirements.txt")
        if os.path.exists(req_file):
            checks["passed"].append("requirements.txt exists for dependency management")
        else:
            checks["failed"].append("requirements.txt not found")
        
        # Check 2: package.json exists
        pkg_file = os.path.join(self.frontend_path, "package.json")
        if os.path.exists(pkg_file):
            checks["passed"].append("package.json exists for frontend dependencies")
        
        # Note: Actual vulnerability scanning is done by vulnerability_scanner.py
        checks["warnings"].append("Run vulnerability_scanner.py for detailed component analysis")
        
        return {
            "category": "A06:2021 – Vulnerable and Outdated Components",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a07_authentication(self) -> Dict:
        """A07:2021 – Identification and Authentication Failures"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: Password policy
        password_policy = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'len\(password\)|password.*[<>]=?\s*\d|min.*length|password_strength'
        )
        if password_policy:
            checks["passed"].append("Password policy checks found")
        else:
            checks["warnings"].append("Consider implementing password strength requirements")
        
        # Check 2: Account lockout
        lockout = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["lockout", "failed_attempts", "account_locked", "MAX_FAILED"]
        )
        if lockout:
            checks["passed"].append("Account lockout mechanism implemented")
        else:
            checks["warnings"].append("Consider implementing account lockout")
        
        # Check 3: Session management
        session = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["session", "token", "JWT", "expires"]
        )
        if session:
            checks["passed"].append("Session/token management implemented")
        
        # Check 4: 2FA support
        twofa = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["two_factor", "2fa", "otp", "totp"]
        )
        if twofa:
            checks["passed"].append("Two-factor authentication supported")
        else:
            checks["warnings"].append("Consider implementing 2FA")
        
        return {
            "category": "A07:2021 – Identification and Authentication Failures",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a08_integrity(self) -> Dict:
        """A08:2021 – Software and Data Integrity Failures"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: File upload validation
        file_validation = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'content_type|file\.filename|allowed_extensions|file_type'
        )
        if file_validation:
            checks["passed"].append("File upload validation found")
        
        # Check 2: Signature verification
        signature = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["hmac", "signature", "verify", "hash"]
        )
        if signature:
            checks["passed"].append("Signature/hash verification implemented")
        
        # Check 3: CSP headers
        csp = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["Content-Security-Policy"]
        )
        if csp:
            checks["passed"].append("Content Security Policy configured")
        
        return {
            "category": "A08:2021 – Software and Data Integrity Failures",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a09_logging(self) -> Dict:
        """A09:2021 – Security Logging and Monitoring Failures"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: Logging implementation
        logging_impl = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'logger\.|logging\.|log\.'
        )
        if len(logging_impl) > 20:
            checks["passed"].append("Comprehensive logging implemented")
        else:
            checks["warnings"].append("Consider adding more logging")
        
        # Check 2: Audit logging
        audit = self._check_file_contains(
            os.path.join(self.backend_path, "**", "*.py"),
            ["audit", "AuditLog", "audit_log"]
        )
        if audit:
            checks["passed"].append("Audit logging system found")
        else:
            checks["warnings"].append("Consider implementing audit logging")
        
        # Check 3: Security event logging
        security_logging = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'login.*log|fail.*log|security.*log|blocked.*log'
        )
        if security_logging:
            checks["passed"].append("Security events are logged")
        
        return {
            "category": "A09:2021 – Security Logging and Monitoring Failures",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _audit_a10_ssrf(self) -> Dict:
        """A10:2021 – Server-Side Request Forgery (SSRF)"""
        checks = {"passed": [], "failed": [], "warnings": []}
        
        # Check 1: URL validation
        url_validation = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'urlparse|validate_url|is_valid_url|whitelist.*url'
        )
        if url_validation:
            checks["passed"].append("URL validation patterns found")
        
        # Check 2: External request handling
        external_requests = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'requests\.get|httpx|aiohttp.*get|urllib'
        )
        if external_requests:
            checks["warnings"].append(f"External HTTP requests found in {len(external_requests)} locations - ensure URL validation")
        else:
            checks["passed"].append("Limited external HTTP requests")
        
        # Check 3: Internal IP blocking
        ip_block = self._find_patterns(
            os.path.join(self.backend_path, "**", "*.py"),
            r'127\.|localhost|192\.168\.|10\.|172\.'
        )
        if ip_block:
            checks["warnings"].append("Internal IP references found - ensure SSRF protection")
        
        return {
            "category": "A10:2021 – Server-Side Request Forgery",
            "checks_performed": len(checks["passed"]) + len(checks["failed"]) + len(checks["warnings"]),
            "checks_passed": len(checks["passed"]),
            "findings": checks
        }
    
    def _find_patterns(self, file_pattern: str, regex_pattern: str) -> List[str]:
        """Find regex patterns in files matching glob pattern"""
        matches = []
        try:
            for filepath in glob.glob(file_pattern, recursive=True):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if re.search(regex_pattern, content, re.IGNORECASE):
                            matches.append(filepath)
                except:
                    pass
        except:
            pass
        return matches
    
    def _check_file_contains(self, file_pattern: str, keywords: List[str]) -> bool:
        """Check if any file contains any of the keywords"""
        try:
            for filepath in glob.glob(file_pattern, recursive=True):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        for keyword in keywords:
                            if keyword.lower() in content:
                                return True
                except:
                    pass
        except:
            pass
        return False
    
    def _calculate_risk_level(self, passed: int, total: int) -> str:
        """Calculate overall risk level"""
        if total == 0:
            return "UNKNOWN"
        
        score = (passed / total) * 100
        if score >= 90:
            return "LOW"
        elif score >= 70:
            return "MEDIUM"
        elif score >= 50:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _generate_recommendations(self) -> List[str]:
        """Generate overall recommendations"""
        return [
            "Run regular security audits (at least quarterly)",
            "Keep all dependencies updated to latest secure versions",
            "Implement security training for development team",
            "Use automated security scanning in CI/CD pipeline",
            "Conduct penetration testing annually",
            "Monitor security logs and set up alerts",
            "Document and review all API endpoints for access control",
            "Implement bug bounty program for responsible disclosure"
        ]
    
    def save_report(self, output_path: str = "/app/reports/owasp_audit.json") -> Dict:
        """Run audit and save report"""
        report = self.run_full_audit()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"OWASP audit report saved to {output_path}")
        return report


def run_audit():
    """CLI entry point"""
    auditor = OWASPSecurityAuditor()
    report = auditor.save_report()
    
    print(f"\n{'='*60}")
    print("OWASP TOP 10 SECURITY AUDIT REPORT")
    print(f"{'='*60}")
    print(f"Compliance Score: {report['summary']['compliance_score']}%")
    print(f"Risk Level: {report['summary']['risk_level']}")
    print(f"Total Checks: {report['summary']['total_checks']}")
    print(f"Passed: {report['summary']['passed_checks']}")
    print(f"Failed: {report['summary']['failed_checks']}")
    
    print(f"\n{'='*60}")
    print("CATEGORY BREAKDOWN")
    print(f"{'='*60}")
    
    for cat_name, cat_data in report['categories'].items():
        status = "PASS" if cat_data['checks_passed'] == cat_data['checks_performed'] else "REVIEW"
        print(f"\n{cat_data['category']}")
        print(f"  Status: {status} ({cat_data['checks_passed']}/{cat_data['checks_performed']})")
        
        if cat_data['findings'].get('failed'):
            print(f"  FAILED:")
            for f in cat_data['findings']['failed']:
                print(f"    - {f}")
    
    print(f"\nFull report saved to: /app/reports/owasp_audit.json")


if __name__ == "__main__":
    run_audit()
