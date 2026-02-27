"""
IP Security Service
CreatorStudio AI - IP-based suspicious activity detection and blocking

Features:
- Track failed login attempts by IP
- Auto-block IPs with suspicious patterns
- Whitelist/blacklist management
- Rate limiting by IP
- Geo-blocking (optional)
"""
import os
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, List
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Configuration
MAX_FAILED_LOGINS_PER_IP = 10  # Block after 10 failed logins
MAX_REQUESTS_PER_MINUTE = 100  # Rate limit
IP_BLOCK_DURATION_HOURS = 24   # How long to block suspicious IPs
SUSPICIOUS_PATTERNS_THRESHOLD = 5  # Number of patterns to trigger block

# Suspicious activity patterns
SUSPICIOUS_PATTERNS = [
    "sql_injection",      # SQL injection attempts
    "xss_attempt",        # XSS attempts
    "path_traversal",     # Directory traversal
    "brute_force",        # Multiple failed logins
    "rate_limit_abuse",   # Exceeding rate limits
    "invalid_tokens",     # Multiple invalid auth tokens
    "api_abuse",          # Abnormal API usage patterns
    "scanner_detected"    # Automated scanner signatures
]


class IPSecurityService:
    """
    Comprehensive IP-based security service.
    Tracks, analyzes, and blocks suspicious IP addresses.
    """
    
    def __init__(self, db):
        self.db = db
        self._request_counts = defaultdict(list)  # IP -> [timestamps]
        self._failed_logins = defaultdict(int)     # IP -> count
        self._blocked_ips_cache = set()            # In-memory cache
        self._whitelist_cache = set()
    
    async def initialize(self):
        """Initialize the service and load caches"""
        # Load blocked IPs into cache
        blocked = await self.db.blocked_ips.find(
            {"blocked_until": {"$gt": datetime.now(timezone.utc).isoformat()}},
            {"_id": 0, "ip_address": 1}
        ).to_list(1000)
        self._blocked_ips_cache = {b["ip_address"] for b in blocked}
        
        # Load whitelist
        whitelist = await self.db.ip_whitelist.find({}, {"_id": 0, "ip_address": 1}).to_list(100)
        self._whitelist_cache = {w["ip_address"] for w in whitelist}
        
        logger.info(f"IP Security initialized: {len(self._blocked_ips_cache)} blocked, {len(self._whitelist_cache)} whitelisted")
    
    async def check_ip(self, ip_address: str) -> Tuple[bool, str]:
        """
        Check if an IP is allowed to access the system.
        
        Returns: (is_allowed, reason)
        """
        if not ip_address:
            return True, ""
        
        # Check whitelist first
        if ip_address in self._whitelist_cache:
            return True, ""
        
        # Check blocked cache
        if ip_address in self._blocked_ips_cache:
            return False, "IP address is blocked due to suspicious activity"
        
        # Check database for block status
        block_record = await self.db.blocked_ips.find_one({
            "ip_address": ip_address,
            "blocked_until": {"$gt": datetime.now(timezone.utc).isoformat()}
        })
        
        if block_record:
            self._blocked_ips_cache.add(ip_address)
            return False, f"IP blocked until {block_record['blocked_until']}: {block_record.get('reason', 'Suspicious activity')}"
        
        # Check rate limit
        if not self._check_rate_limit(ip_address):
            await self.record_suspicious_activity(ip_address, "rate_limit_abuse", "Exceeded rate limit")
            return False, "Rate limit exceeded. Please slow down."
        
        return True, ""
    
    def _check_rate_limit(self, ip_address: str) -> bool:
        """Check if IP is within rate limits"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old timestamps
        self._request_counts[ip_address] = [
            ts for ts in self._request_counts[ip_address] if ts > minute_ago
        ]
        
        # Check count
        if len(self._request_counts[ip_address]) >= MAX_REQUESTS_PER_MINUTE:
            return False
        
        # Record this request
        self._request_counts[ip_address].append(now)
        return True
    
    async def record_failed_login(self, ip_address: str, email: str = None) -> bool:
        """
        Record a failed login attempt.
        Returns True if IP should be blocked.
        """
        self._failed_logins[ip_address] += 1
        
        # Record in database
        await self.db.ip_activity.insert_one({
            "ip_address": ip_address,
            "activity_type": "failed_login",
            "email_attempted": email,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Check if should block
        if self._failed_logins[ip_address] >= MAX_FAILED_LOGINS_PER_IP:
            await self.block_ip(
                ip_address,
                "brute_force",
                f"Too many failed login attempts ({self._failed_logins[ip_address]})"
            )
            return True
        
        return False
    
    async def record_successful_login(self, ip_address: str):
        """Record successful login - reset failed counter"""
        self._failed_logins[ip_address] = 0
        
        await self.db.ip_activity.insert_one({
            "ip_address": ip_address,
            "activity_type": "successful_login",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def record_suspicious_activity(
        self,
        ip_address: str,
        activity_type: str,
        details: str,
        auto_block: bool = True
    ):
        """
        Record suspicious activity from an IP.
        May trigger automatic blocking.
        """
        await self.db.ip_activity.insert_one({
            "ip_address": ip_address,
            "activity_type": activity_type,
            "details": details,
            "severity": "HIGH" if activity_type in ["sql_injection", "xss_attempt"] else "MEDIUM",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.warning(f"Suspicious activity from {ip_address}: {activity_type} - {details}")
        
        # Count recent suspicious activities
        if auto_block:
            recent_count = await self.db.ip_activity.count_documents({
                "ip_address": ip_address,
                "activity_type": {"$in": SUSPICIOUS_PATTERNS},
                "timestamp": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
            })
            
            if recent_count >= SUSPICIOUS_PATTERNS_THRESHOLD:
                await self.block_ip(ip_address, "multiple_violations", f"Multiple suspicious activities: {recent_count}")
    
    async def block_ip(
        self,
        ip_address: str,
        reason: str,
        details: str,
        duration_hours: int = IP_BLOCK_DURATION_HOURS,
        admin_id: str = None
    ):
        """Block an IP address"""
        blocked_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        
        await self.db.blocked_ips.update_one(
            {"ip_address": ip_address},
            {
                "$set": {
                    "ip_address": ip_address,
                    "reason": reason,
                    "details": details,
                    "blocked_at": datetime.now(timezone.utc).isoformat(),
                    "blocked_until": blocked_until.isoformat(),
                    "blocked_by": admin_id or "SYSTEM",
                    "is_permanent": False
                }
            },
            upsert=True
        )
        
        self._blocked_ips_cache.add(ip_address)
        
        # Log to audit
        await self.db.audit_logs.insert_one({
            "event_type": "SECURITY_IP_BLOCKED",
            "severity": "WARNING",
            "ip_address": ip_address,
            "details": {"reason": reason, "details": details, "duration_hours": duration_hours},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.warning(f"IP BLOCKED: {ip_address} - {reason} - until {blocked_until}")
    
    async def unblock_ip(self, ip_address: str, admin_id: str):
        """Unblock an IP address (admin action)"""
        await self.db.blocked_ips.delete_one({"ip_address": ip_address})
        self._blocked_ips_cache.discard(ip_address)
        
        await self.db.audit_logs.insert_one({
            "event_type": "ADMIN_IP_UNBLOCKED",
            "severity": "INFO",
            "ip_address": ip_address,
            "admin_id": admin_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"IP UNBLOCKED by admin {admin_id}: {ip_address}")
    
    async def add_to_whitelist(self, ip_address: str, admin_id: str, reason: str):
        """Add IP to whitelist (admin action)"""
        await self.db.ip_whitelist.update_one(
            {"ip_address": ip_address},
            {
                "$set": {
                    "ip_address": ip_address,
                    "added_by": admin_id,
                    "reason": reason,
                    "added_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        self._whitelist_cache.add(ip_address)
        logger.info(f"IP WHITELISTED by admin {admin_id}: {ip_address}")
    
    async def remove_from_whitelist(self, ip_address: str, admin_id: str):
        """Remove IP from whitelist"""
        await self.db.ip_whitelist.delete_one({"ip_address": ip_address})
        self._whitelist_cache.discard(ip_address)
    
    async def get_blocked_ips(self, page: int = 1, size: int = 50) -> Dict:
        """Get list of blocked IPs for admin dashboard"""
        skip = (page - 1) * size
        total = await self.db.blocked_ips.count_documents({})
        
        blocked = await self.db.blocked_ips.find(
            {},
            {"_id": 0}
        ).sort("blocked_at", -1).skip(skip).limit(size).to_list(size)
        
        return {
            "blocked_ips": blocked,
            "pagination": {"page": page, "size": size, "total": total}
        }
    
    async def get_ip_activity(self, ip_address: str, limit: int = 100) -> List[Dict]:
        """Get activity history for a specific IP"""
        activities = await self.db.ip_activity.find(
            {"ip_address": ip_address},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        return activities
    
    async def get_security_stats(self, days: int = 7) -> Dict:
        """Get security statistics for dashboard"""
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Count blocked IPs
        active_blocks = await self.db.blocked_ips.count_documents({
            "blocked_until": {"$gt": datetime.now(timezone.utc).isoformat()}
        })
        
        # Count by activity type
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$activity_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        activity_counts = await self.db.ip_activity.aggregate(pipeline).to_list(20)
        
        # Top offending IPs
        top_ips_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}, "activity_type": {"$in": SUSPICIOUS_PATTERNS}}},
            {"$group": {"_id": "$ip_address", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_offenders = await self.db.ip_activity.aggregate(top_ips_pipeline).to_list(10)
        
        return {
            "period_days": days,
            "active_blocks": active_blocks,
            "whitelisted_count": len(self._whitelist_cache),
            "activity_by_type": {a["_id"]: a["count"] for a in activity_counts},
            "top_offending_ips": [{"ip": t["_id"], "incidents": t["count"]} for t in top_offenders],
            "failed_logins_tracked": sum(self._failed_logins.values())
        }
    
    def detect_sql_injection(self, input_string: str) -> bool:
        """Detect potential SQL injection attempts"""
        if not input_string:
            return False
        
        sql_patterns = [
            "' or ", "' and ", "'; drop", "'; delete", "'; update",
            "union select", "1=1", "1 = 1", "--", "/*", "*/",
            "char(", "concat(", "sleep(", "benchmark("
        ]
        
        lower_input = input_string.lower()
        return any(pattern in lower_input for pattern in sql_patterns)
    
    def detect_xss_attempt(self, input_string: str) -> bool:
        """Detect potential XSS attempts"""
        if not input_string:
            return False
        
        xss_patterns = [
            "<script", "</script>", "javascript:", "onerror=", "onload=",
            "onclick=", "onmouseover=", "onfocus=", "onblur=",
            "eval(", "document.cookie", "document.write"
        ]
        
        lower_input = input_string.lower()
        return any(pattern in lower_input for pattern in xss_patterns)
    
    def detect_path_traversal(self, input_string: str) -> bool:
        """Detect directory traversal attempts"""
        if not input_string:
            return False
        
        traversal_patterns = ["../", "..\\", "%2e%2e", "....//", "....\\\\"]
        return any(pattern in input_string.lower() for pattern in traversal_patterns)


# Singleton instance
_ip_security_service = None


async def get_ip_security_service(db) -> IPSecurityService:
    """Get or create the IP security service singleton"""
    global _ip_security_service
    if _ip_security_service is None:
        _ip_security_service = IPSecurityService(db)
        await _ip_security_service.initialize()
    return _ip_security_service


__all__ = [
    'IPSecurityService',
    'get_ip_security_service',
    'SUSPICIOUS_PATTERNS'
]
