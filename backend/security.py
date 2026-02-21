"""
Security Module for CreatorStudio AI
Implements comprehensive security measures against common vulnerabilities
"""
import re
import html
import hashlib
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, List
from functools import wraps

import bleach
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# =============================================================================
# RATE LIMITING
# =============================================================================
# Use in-memory storage for rate limiting
from limits.storage import MemoryStorage

# Create memory storage instance
memory_storage = MemoryStorage()

# Initialize limiter with explicit storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per day", "100 per hour"]
)

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors"""
    logger.warning(f"Rate limit exceeded for IP: {get_remote_address(request)}")
    return JSONResponse(
        status_code=429,
        content={
            "error": "Too many requests",
            "detail": "You have exceeded the rate limit. Please try again later.",
            "retry_after": "60 seconds"
        }
    )

# =============================================================================
# INPUT SANITIZATION
# =============================================================================
# Dangerous patterns to detect
DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # Script tags
    r'javascript:',  # JavaScript protocol
    r'on\w+\s*=',  # Event handlers (onclick, onerror, etc.)
    r'eval\s*\(',  # Eval function
    r'document\.',  # DOM manipulation
    r'window\.',  # Window object access
    r'\.\./\.\.',  # Path traversal
    r';\s*(rm|cat|wget|curl|bash|sh)\s',  # Command injection
    r'\$\{.*\}',  # Template injection
    r'{{.*}}',  # Template injection
    r'<iframe',  # Iframe injection
    r'<embed',  # Embed injection
    r'<object',  # Object injection
    r'data:text/html',  # Data URL XSS
    r'vbscript:',  # VBScript
]

# Prohibited content for AI generation
PROHIBITED_CONTENT = [
    "celebrity", "famous person", "real person", "deepfake", "face swap",
    "nude", "naked", "porn", "sexual", "explicit", "nsfw",
    "child", "minor", "underage", "kid abuse",
    "violence", "gore", "murder", "terrorist", "bomb",
    "drug", "cocaine", "heroin", "meth",
    "weapon", "gun", "knife attack",
    "hate speech", "racist", "discrimination",
    "phishing", "scam", "fraud"
]

def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks
    """
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Use bleach to clean HTML
    text = bleach.clean(
        text,
        tags=[],  # No HTML tags allowed
        attributes={},
        strip=True
    )
    
    # HTML escape any remaining special characters
    text = html.escape(text, quote=True)
    
    return text.strip()

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    if not filename:
        return "unnamed"
    
    # Remove path components
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # Remove special characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
    
    # Limit length
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    name = name[:100]
    ext = ext[:10]
    
    return f"{name}.{ext}" if ext else name

def detect_dangerous_content(text: str) -> Optional[str]:
    """
    Detect dangerous patterns in user input
    Returns the pattern name if found, None otherwise
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning(f"Dangerous pattern detected: {pattern[:30]}...")
            return "malicious_content"
    
    return None

def detect_prohibited_content(text: str) -> Optional[str]:
    """
    Detect prohibited content for AI generation
    Returns the prohibited term if found
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    for term in PROHIBITED_CONTENT:
        if term in text_lower:
            return term
    
    return None

def validate_prompt(prompt: str) -> tuple[bool, str]:
    """
    Validate AI generation prompt
    Returns (is_valid, error_message)
    """
    if not prompt or not prompt.strip():
        return False, "Prompt cannot be empty"
    
    if len(prompt) > 2000:
        return False, "Prompt too long (max 2000 characters)"
    
    # Check for dangerous content
    dangerous = detect_dangerous_content(prompt)
    if dangerous:
        return False, "Prompt contains potentially malicious content"
    
    # Check for prohibited content
    prohibited = detect_prohibited_content(prompt)
    if prohibited:
        return False, f"Prohibited content detected: {prohibited}. This violates our content policy."
    
    return True, ""

# =============================================================================
# SECURITY HEADERS
# =============================================================================
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:;",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache"
}

async def add_security_headers(request: Request, call_next):
    """Middleware to add security headers to all responses"""
    response = await call_next(request)
    
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    
    return response

# =============================================================================
# IP BLOCKING & THREAT DETECTION
# =============================================================================
blocked_ips = set()
suspicious_ips = {}  # IP -> (count, last_attempt)
MAX_SUSPICIOUS_ATTEMPTS = 10
BLOCK_DURATION_MINUTES = 60

def check_ip_blocked(ip: str) -> bool:
    """Check if IP is blocked"""
    return ip in blocked_ips

def record_suspicious_activity(ip: str, reason: str):
    """Record suspicious activity from an IP"""
    now = datetime.now(timezone.utc)
    
    if ip in suspicious_ips:
        count, last_attempt = suspicious_ips[ip]
        # Reset if more than 1 hour since last attempt
        if (now - last_attempt).total_seconds() > 3600:
            count = 0
        count += 1
        suspicious_ips[ip] = (count, now)
        
        if count >= MAX_SUSPICIOUS_ATTEMPTS:
            blocked_ips.add(ip)
            logger.error(f"IP {ip} blocked due to suspicious activity: {reason}")
    else:
        suspicious_ips[ip] = (1, now)
    
    logger.warning(f"Suspicious activity from {ip}: {reason}")

async def security_middleware(request: Request, call_next):
    """Main security middleware"""
    ip = get_remote_address(request)
    
    # Check if IP is blocked
    if check_ip_blocked(ip):
        logger.warning(f"Blocked IP attempted access: {ip}")
        return JSONResponse(
            status_code=403,
            content={"error": "Access denied", "detail": "Your IP has been blocked due to suspicious activity"}
        )
    
    # Check for common attack patterns in URL
    path = request.url.path.lower()
    suspicious_paths = [
        '/wp-admin', '/wp-login', '/.env', '/.git', '/phpinfo',
        '/admin.php', '/shell', '/cmd', '/eval', '/../',
        '/etc/passwd', '/proc/self', 'select%20', 'union%20',
        '<script', 'javascript:', 'onerror='
    ]
    
    for sus_path in suspicious_paths:
        if sus_path in path:
            record_suspicious_activity(ip, f"Suspicious path access: {path}")
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden", "detail": "Access denied"}
            )
    
    # Continue with request
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled error from {ip}: {str(e)}")
        raise

# =============================================================================
# PASSWORD SECURITY
# =============================================================================
def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password too long (max 128 characters)"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    # Check for common weak passwords
    weak_passwords = ['password', '12345678', 'qwerty', 'admin', 'letmein']
    if password.lower() in weak_passwords:
        return False, "Password is too common. Please choose a stronger password."
    
    return True, ""

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)

# =============================================================================
# FILE SECURITY
# =============================================================================
ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif']
ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']
ALLOWED_AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/ogg']
MAX_FILE_SIZE_MB = 50

def validate_file_type(content_type: str, allowed_types: List[str]) -> bool:
    """Validate file type against allowed types"""
    return content_type.lower() in allowed_types

def validate_file_size(size_bytes: int, max_size_mb: int = MAX_FILE_SIZE_MB) -> bool:
    """Validate file size"""
    return size_bytes <= max_size_mb * 1024 * 1024

def get_file_hash(content: bytes) -> str:
    """Get SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

# =============================================================================
# AUDIT LOGGING
# =============================================================================
def log_security_event(event_type: str, details: dict, severity: str = "INFO"):
    """Log security-related events"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": severity,
        **details
    }
    
    if severity == "ERROR":
        logger.error(f"SECURITY EVENT: {log_entry}")
    elif severity == "WARNING":
        logger.warning(f"SECURITY EVENT: {log_entry}")
    else:
        logger.info(f"SECURITY EVENT: {log_entry}")

# =============================================================================
# SQL/NOSQL INJECTION PREVENTION
# =============================================================================
def sanitize_mongo_query(query_value: str) -> str:
    """Sanitize values used in MongoDB queries to prevent NoSQL injection"""
    if not isinstance(query_value, str):
        return query_value
    
    # Remove MongoDB operators
    dangerous_operators = ['$where', '$gt', '$lt', '$ne', '$in', '$nin', '$or', '$and', '$not', '$regex']
    result = query_value
    
    for op in dangerous_operators:
        result = result.replace(op, '')
    
    return result

# =============================================================================
# EXPORT
# =============================================================================
__all__ = [
    'limiter',
    'rate_limit_exceeded_handler',
    'sanitize_input',
    'sanitize_filename',
    'detect_dangerous_content',
    'detect_prohibited_content',
    'validate_prompt',
    'add_security_headers',
    'security_middleware',
    'validate_password_strength',
    'generate_secure_token',
    'validate_file_type',
    'validate_file_size',
    'get_file_hash',
    'log_security_event',
    'sanitize_mongo_query',
    'SECURITY_HEADERS',
    'ALLOWED_IMAGE_TYPES',
    'ALLOWED_VIDEO_TYPES',
    'ALLOWED_AUDIO_TYPES',
    'record_suspicious_activity'
]
