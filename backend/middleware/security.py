"""
Security Middleware & Headers
CreatorStudio AI - OWASP Compliance
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import re
import time


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    Implements OWASP security best practices
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Content Security Policy (CSP)
        # Allows resources from self, inline styles/scripts, and specific CDNs
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: blob: https: http:",
            "media-src 'self' blob: https:",
            "connect-src 'self' https: wss:",
            "frame-ancestors 'self'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # HTTP Strict Transport Security (HSTS)
        # Force HTTPS for 1 year, include subdomains
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # X-Content-Type-Options
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        # Prevent clickjacking (legacy, CSP frame-ancestors is preferred)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # X-XSS-Protection
        # Enable browser XSS filtering (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy)
        # Restrict browser features
        permissions = [
            "accelerometer=()",
            "camera=()",
            "geolocation=()",
            "gyroscope=()",
            "magnetometer=()",
            "microphone=()",
            "payment=()",
            "usb=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)
        
        # Cache-Control for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic rate limiting middleware
    Tracks requests per IP and blocks if exceeded
    """
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # IP -> [(timestamp, count)]
        self.cleanup_interval = 60  # Clean old entries every 60 seconds
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        current_time = time.time()
        
        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
            self.last_cleanup = current_time
        
        # Check rate limit
        if client_ip in self.request_counts:
            entries = self.request_counts[client_ip]
            # Remove entries older than 1 minute
            entries = [(t, c) for t, c in entries if current_time - t < 60]
            total_requests = sum(c for _, c in entries)
            
            if total_requests >= self.requests_per_minute:
                return Response(
                    content='{"detail": "Rate limit exceeded. Please try again later."}',
                    status_code=429,
                    media_type="application/json",
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0"
                    }
                )
            
            entries.append((current_time, 1))
            self.request_counts[client_ip] = entries
        else:
            self.request_counts[client_ip] = [(current_time, 1)]
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - self._get_request_count(client_ip))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _get_request_count(self, client_ip: str) -> int:
        if client_ip not in self.request_counts:
            return 0
        current_time = time.time()
        entries = self.request_counts[client_ip]
        return sum(c for t, c in entries if current_time - t < 60)
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove entries older than 1 minute"""
        for ip in list(self.request_counts.keys()):
            entries = self.request_counts[ip]
            entries = [(t, c) for t, c in entries if current_time - t < 60]
            if entries:
                self.request_counts[ip] = entries
            else:
                del self.request_counts[ip]


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Sanitize potentially dangerous input patterns
    Helps prevent XSS and injection attacks
    """
    
    # Patterns that might indicate XSS or injection attempts
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'document\.cookie',
        r'document\.write',
        r'eval\s*\(',
        r'expression\s*\(',
    ]
    
    def __init__(self, app):
        super().__init__(app)
        self.compiled_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.DANGEROUS_PATTERNS]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check query parameters
        for key, value in request.query_params.items():
            if self._is_dangerous(value):
                return Response(
                    content='{"detail": "Invalid input detected"}',
                    status_code=400,
                    media_type="application/json"
                )
        
        return await call_next(request)
    
    def _is_dangerous(self, value: str) -> bool:
        """Check if value contains dangerous patterns"""
        if not value:
            return False
        for pattern in self.compiled_patterns:
            if pattern.search(value):
                return True
        return False


# Security utility functions
def sanitize_html(text: str) -> str:
    """Remove potentially dangerous HTML tags and attributes"""
    if not text:
        return text
    
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove event handlers
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    # Remove javascript: URLs
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    return text


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?://[^\s<>"{}|\\^`\[\]]+$'
    return bool(re.match(pattern, url))


# CORS configuration helper
def get_cors_config():
    """Get CORS configuration for the application"""
    return {
        "allow_origins": [
            "https://creatorstudio.ai",
            "https://www.creatorstudio.ai",
            "https://progressive-pipeline.preview.emergentagent.com",
            "http://localhost:3000",
            "http://localhost:8001"
        ],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "Accept",
            "Origin",
            "Cache-Control"
        ],
        "max_age": 600
    }
