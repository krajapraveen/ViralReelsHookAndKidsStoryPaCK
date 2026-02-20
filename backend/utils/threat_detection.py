"""
Production Threat Detection Module
Implements real security measures: rate limiting, abuse detection, IP reputation, monitoring
"""
import asyncio
import hashlib
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# =============================================================================
# THREAT DETECTION CONFIGURATION
# =============================================================================

# Rate limit windows (seconds)
RATE_WINDOWS = {
    "auth": {"window": 60, "max_requests": 10},          # Auth endpoints
    "generation": {"window": 60, "max_requests": 5},      # AI generation
    "export": {"window": 60, "max_requests": 10},         # Export endpoints
    "payment": {"window": 60, "max_requests": 5},         # Payment endpoints
    "api": {"window": 60, "max_requests": 100},           # General API
}

# Abuse patterns
ABUSE_PATTERNS = {
    "rapid_auth_failure": {"threshold": 5, "window": 300, "action": "block_temp"},
    "rapid_generation": {"threshold": 20, "window": 3600, "action": "throttle"},
    "suspicious_headers": {"threshold": 3, "window": 60, "action": "block_temp"},
    "payload_size_abuse": {"threshold": 5, "window": 300, "action": "block_temp"},
}

# Suspicious user-agents
SUSPICIOUS_USER_AGENTS = [
    "python-requests",  # Could be bot
    "curl",
    "wget",
    "scrapy",
    "bot",
    "spider",
    "crawler",
]

# Allowed origins (for CORS-like checks)
ALLOWED_ORIGINS = [
    "localhost",
    "127.0.0.1",
    ".preview.emergentagent.com",
    ".emergentagent.com",
]

# =============================================================================
# IN-MEMORY STORES (Production should use Redis)
# =============================================================================

class ThreatStore:
    """In-memory threat detection store"""
    
    def __init__(self):
        self.request_counts: Dict[str, List[float]] = defaultdict(list)
        self.auth_failures: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}  # IP -> block_until timestamp
        self.throttled_ips: Dict[str, float] = {}  # IP -> throttle_until timestamp
        self.suspicious_activity: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        self.ip_scores: Dict[str, int] = defaultdict(int)  # Reputation scores
        
    def cleanup_old_entries(self):
        """Remove entries older than 1 hour"""
        cutoff = time.time() - 3600
        
        for key in list(self.request_counts.keys()):
            self.request_counts[key] = [t for t in self.request_counts[key] if t > cutoff]
            if not self.request_counts[key]:
                del self.request_counts[key]
        
        for key in list(self.auth_failures.keys()):
            self.auth_failures[key] = [t for t in self.auth_failures[key] if t > cutoff]
            if not self.auth_failures[key]:
                del self.auth_failures[key]
        
        # Clear expired blocks
        now = time.time()
        self.blocked_ips = {k: v for k, v in self.blocked_ips.items() if v > now}
        self.throttled_ips = {k: v for k, v in self.throttled_ips.items() if v > now}

threat_store = ThreatStore()

# =============================================================================
# RATE LIMITING
# =============================================================================

def check_rate_limit(ip: str, endpoint_type: str) -> Tuple[bool, Optional[str]]:
    """
    Check if request should be rate limited
    Returns: (is_allowed, error_message)
    """
    config = RATE_WINDOWS.get(endpoint_type, RATE_WINDOWS["api"])
    window = config["window"]
    max_requests = config["max_requests"]
    
    key = f"{ip}:{endpoint_type}"
    now = time.time()
    cutoff = now - window
    
    # Clean old entries
    threat_store.request_counts[key] = [
        t for t in threat_store.request_counts[key] if t > cutoff
    ]
    
    # Check limit
    if len(threat_store.request_counts[key]) >= max_requests:
        return False, f"Rate limit exceeded. Max {max_requests} requests per {window}s"
    
    # Record request
    threat_store.request_counts[key].append(now)
    return True, None

# =============================================================================
# ABUSE DETECTION
# =============================================================================

def record_auth_failure(ip: str, user_email: str = None):
    """Record failed authentication attempt"""
    now = time.time()
    threat_store.auth_failures[ip].append(now)
    
    # Check for rapid failures
    window = ABUSE_PATTERNS["rapid_auth_failure"]["window"]
    threshold = ABUSE_PATTERNS["rapid_auth_failure"]["threshold"]
    cutoff = now - window
    
    recent_failures = [t for t in threat_store.auth_failures[ip] if t > cutoff]
    
    if len(recent_failures) >= threshold:
        # Temporary block
        block_duration = 900  # 15 minutes
        threat_store.blocked_ips[ip] = now + block_duration
        threat_store.ip_scores[ip] += 10
        
        logger.warning(f"IP {ip} temporarily blocked due to rapid auth failures")
        
        # Log security event
        log_threat_event("RAPID_AUTH_FAILURE", ip, {
            "failures_count": len(recent_failures),
            "user_email": user_email,
            "block_duration": block_duration
        })

def detect_suspicious_request(request: Request) -> Tuple[bool, Optional[str]]:
    """
    Analyze request for suspicious patterns
    Returns: (is_suspicious, reason)
    """
    ip = get_client_ip(request)
    
    # Check user-agent
    user_agent = request.headers.get("user-agent", "").lower()
    for sus_agent in SUSPICIOUS_USER_AGENTS:
        if sus_agent in user_agent:
            threat_store.ip_scores[ip] += 1
            return True, f"Suspicious user-agent: {sus_agent}"
    
    # Check for missing headers
    if not request.headers.get("user-agent"):
        threat_store.ip_scores[ip] += 2
        return True, "Missing user-agent header"
    
    # Check content-length for POST requests
    if request.method == "POST":
        content_length = request.headers.get("content-length", "0")
        try:
            if int(content_length) > 10 * 1024 * 1024:  # 10MB
                threat_store.ip_scores[ip] += 5
                return True, "Excessive payload size"
        except ValueError:
            pass
    
    return False, None

def is_ip_blocked(ip: str) -> bool:
    """Check if IP is currently blocked"""
    if ip in threat_store.blocked_ips:
        if time.time() < threat_store.blocked_ips[ip]:
            return True
        else:
            del threat_store.blocked_ips[ip]
    return False

def is_ip_throttled(ip: str) -> bool:
    """Check if IP is currently throttled"""
    if ip in threat_store.throttled_ips:
        if time.time() < threat_store.throttled_ips[ip]:
            return True
        else:
            del threat_store.throttled_ips[ip]
    return False

# =============================================================================
# IP UTILITIES
# =============================================================================

def get_client_ip(request: Request) -> str:
    """Get client IP, handling proxies"""
    # Check X-Forwarded-For header
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Get first IP in chain (original client)
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection
    return request.client.host if request.client else "unknown"

def hash_ip(ip: str) -> str:
    """Hash IP for privacy-safe logging"""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

# =============================================================================
# LOGGING & MONITORING
# =============================================================================

def log_threat_event(event_type: str, ip: str, details: dict, severity: str = "WARNING"):
    """Log threat event for monitoring"""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "ip_hash": hash_ip(ip),
        "severity": severity,
        "details": {k: v for k, v in details.items() if k != "ip"}  # Don't log raw IP
    }
    
    if severity == "CRITICAL":
        logger.critical(f"THREAT: {event}")
    elif severity == "ERROR":
        logger.error(f"THREAT: {event}")
    elif severity == "WARNING":
        logger.warning(f"THREAT: {event}")
    else:
        logger.info(f"THREAT: {event}")
    
    # Record suspicious activity
    threat_store.suspicious_activity[ip].append((time.time(), event_type))

def get_threat_stats() -> dict:
    """Get current threat detection statistics"""
    threat_store.cleanup_old_entries()
    
    return {
        "blocked_ips_count": len(threat_store.blocked_ips),
        "throttled_ips_count": len(threat_store.throttled_ips),
        "active_sessions": len(threat_store.request_counts),
        "high_risk_ips": len([s for s in threat_store.ip_scores.values() if s >= 10]),
        "recent_events": len([
            e for events in threat_store.suspicious_activity.values()
            for e in events if e[0] > time.time() - 3600
        ])
    }

# =============================================================================
# MIDDLEWARE
# =============================================================================

async def threat_detection_middleware(request: Request, call_next):
    """Main threat detection middleware"""
    ip = get_client_ip(request)
    path = request.url.path.lower()
    
    # Check if IP is blocked
    if is_ip_blocked(ip):
        log_threat_event("BLOCKED_ACCESS_ATTEMPT", ip, {"path": path})
        return JSONResponse(
            status_code=403,
            content={"error": "Access denied", "detail": "Your access has been temporarily restricted"}
        )
    
    # Check for suspicious patterns
    is_suspicious, reason = detect_suspicious_request(request)
    if is_suspicious and threat_store.ip_scores[ip] >= 10:
        log_threat_event("SUSPICIOUS_REQUEST_BLOCKED", ip, {"reason": reason, "path": path})
        return JSONResponse(
            status_code=403,
            content={"error": "Request blocked", "detail": "Suspicious activity detected"}
        )
    
    # Determine endpoint type for rate limiting
    endpoint_type = "api"
    if "/auth/" in path:
        endpoint_type = "auth"
    elif "/generate" in path or "/genstudio" in path or "/wallet/jobs" in path:
        endpoint_type = "generation"
    elif "/export" in path or "/download" in path:
        endpoint_type = "export"
    elif "/payment" in path or "/cashfree" in path:
        endpoint_type = "payment"
    
    # Check rate limit
    is_allowed, error_msg = check_rate_limit(ip, endpoint_type)
    if not is_allowed:
        log_threat_event("RATE_LIMIT_EXCEEDED", ip, {"endpoint_type": endpoint_type, "path": path})
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "detail": error_msg, "retry_after": 60}
        )
    
    # Apply throttling if IP is throttled (slower response)
    if is_ip_throttled(ip):
        await asyncio.sleep(2)  # Add 2 second delay
    
    # Process request
    response = await call_next(request)
    
    return response

# =============================================================================
# CLEANUP TASK
# =============================================================================

async def periodic_cleanup():
    """Periodic cleanup of old threat data"""
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        threat_store.cleanup_old_entries()
        logger.info(f"Threat store cleanup complete. Stats: {get_threat_stats()}")

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'threat_detection_middleware',
    'record_auth_failure',
    'detect_suspicious_request',
    'is_ip_blocked',
    'is_ip_throttled',
    'get_client_ip',
    'log_threat_event',
    'get_threat_stats',
    'check_rate_limit',
    'periodic_cleanup',
    'threat_store'
]
