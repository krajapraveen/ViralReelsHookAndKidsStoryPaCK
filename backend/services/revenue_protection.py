"""
Revenue Protection Service
CreatorStudio AI - Protects credits, prevents abuse, ensures revenue safety

Key Features:
1. Credit Protection - Deduct BEFORE generation, validate server-side
2. Replay Attack Prevention - Idempotency keys for generation requests
3. Role Protection - Admin-only credit modification
4. Prompt Safety - Copyright/celebrity blocking
5. Download Protection - Signed URLs with expiry
"""
import os
import hashlib
import hmac
import uuid
import secrets
import time
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict
from functools import wraps
import logging
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
SIGNED_URL_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-me')
SIGNED_URL_EXPIRY_SECONDS = 300  # 5 minutes
REPLAY_WINDOW_SECONDS = 60  # Reject duplicate requests within 60 seconds

# Copyright and celebrity protection keywords
COPYRIGHT_KEYWORDS = [
    # Famous Characters
    "mickey mouse", "donald duck", "spiderman", "spider-man", "batman", "superman",
    "iron man", "captain america", "thor", "hulk", "black widow", "harry potter",
    "pikachu", "pokemon", "mario", "luigi", "sonic", "spongebob", "peppa pig",
    "frozen elsa", "elsa frozen", "anna frozen", "moana", "simba", "nemo",
    "buzz lightyear", "woody toy story", "shrek", "minions",
    
    # Famous Brands
    "disney", "pixar", "marvel", "dc comics", "warner bros", "dreamworks",
    "nintendo", "nickelodeon", "cartoon network", "sesame street",
    
    # Generic copyright terms
    "copyrighted", "trademark", "registered trademark", "all rights reserved"
]

CELEBRITY_KEYWORDS = [
    # Actors
    "tom cruise", "brad pitt", "leonardo dicaprio", "johnny depp", "will smith",
    "angelina jolie", "jennifer aniston", "scarlett johansson", "margot robbie",
    "dwayne johnson", "the rock", "ryan reynolds", "chris hemsworth", "chris evans",
    "robert downey", "keanu reeves", "denzel washington", "morgan freeman",
    
    # Musicians
    "taylor swift", "beyonce", "rihanna", "drake", "kanye west", "jay z",
    "justin bieber", "ariana grande", "selena gomez", "ed sheeran", "billie eilish",
    "lady gaga", "katy perry", "bruno mars", "post malone", "the weeknd",
    
    # Athletes
    "lionel messi", "cristiano ronaldo", "lebron james", "michael jordan",
    "serena williams", "roger federer", "usain bolt", "tom brady",
    
    # Politicians & Public Figures
    "donald trump", "joe biden", "barack obama", "elon musk", "jeff bezos",
    "mark zuckerberg", "bill gates", "warren buffett",
    
    # Generic terms
    "celebrity", "famous person", "real person", "public figure",
    "deepfake", "face swap", "face replace"
]

# Universal negative prompts for AI image generation
UNIVERSAL_NEGATIVE_PROMPTS = [
    "realistic human face",
    "celebrity likeness", 
    "real person",
    "photorealistic portrait",
    "branded logo",
    "copyrighted character",
    "trademarked design",
    "watermark",
    "signature",
    "nsfw",
    "violence",
    "gore"
]

# ============================================================================
# CREDIT PROTECTION
# ============================================================================
class CreditProtectionService:
    """
    Ensures credits are:
    1. Validated on server-side (never trust client)
    2. Deducted BEFORE generation starts
    3. Protected from replay attacks
    """
    
    def __init__(self, db):
        self.db = db
        self._request_hashes = {}  # In-memory cache for replay detection
    
    async def validate_and_reserve_credits(
        self,
        user_id: str,
        required_credits: int,
        feature_name: str,
        request_hash: Optional[str] = None
    ) -> Tuple[bool, str, int]:
        """
        Validate user has enough credits and reserve them atomically.
        
        Returns: (success, message, new_balance)
        """
        # Check for replay attack
        if request_hash and self._is_replay_attack(user_id, request_hash):
            return False, "Duplicate request detected. Please wait before retrying.", 0
        
        # Get current user with fresh data
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            return False, "User not found", 0
        
        current_credits = user.get("credits", 0)
        
        # Server-side validation - NEVER trust client-provided credit values
        if current_credits < required_credits:
            subscription = user.get("subscription")
            if not subscription:
                return False, f"Insufficient credits for {feature_name}. You need {required_credits} credits but have {current_credits}. Please purchase more credits.", current_credits
            return False, f"Insufficient credits. Need {required_credits}, have {current_credits}.", current_credits
        
        # Atomic deduction using MongoDB's findOneAndUpdate
        result = await self.db.users.find_one_and_update(
            {
                "id": user_id,
                "credits": {"$gte": required_credits}  # Double-check in query
            },
            {"$inc": {"credits": -required_credits}},
            return_document=True
        )
        
        if not result:
            # Race condition - credits were deducted by another request
            return False, "Credits changed during request. Please try again.", current_credits
        
        new_balance = result.get("credits", 0)
        
        # Log the credit deduction
        await self.db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "amount": -required_credits,
            "type": "USAGE",
            "description": f"Reserved for: {feature_name}",
            "status": "RESERVED",  # Will be updated to COMPLETED or REFUNDED
            "requestHash": request_hash,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Record request hash to prevent replay
        if request_hash:
            self._record_request(user_id, request_hash)
        
        logger.info(f"Credits reserved: user={user_id}, amount={required_credits}, feature={feature_name}, new_balance={new_balance}")
        
        return True, "Credits reserved successfully", new_balance
    
    async def refund_credits(
        self,
        user_id: str,
        credits: int,
        reason: str,
        request_hash: Optional[str] = None
    ) -> Tuple[bool, int]:
        """
        Refund credits if generation fails after deduction.
        
        Returns: (success, new_balance)
        """
        result = await self.db.users.find_one_and_update(
            {"id": user_id},
            {"$inc": {"credits": credits}},
            return_document=True
        )
        
        if not result:
            logger.error(f"Failed to refund credits: user={user_id}, amount={credits}")
            return False, 0
        
        new_balance = result.get("credits", 0)
        
        # Log the refund
        await self.db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "amount": credits,
            "type": "REFUND",
            "description": f"Generation failed: {reason}",
            "requestHash": request_hash,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Credits refunded: user={user_id}, amount={credits}, reason={reason}")
        
        return True, new_balance
    
    def _is_replay_attack(self, user_id: str, request_hash: str) -> bool:
        """Check if this request is a replay of a recent request"""
        key = f"{user_id}:{request_hash}"
        now = time.time()
        
        # Clean old entries
        self._cleanup_old_requests()
        
        if key in self._request_hashes:
            timestamp = self._request_hashes[key]
            if now - timestamp < REPLAY_WINDOW_SECONDS:
                logger.warning(f"Replay attack detected: user={user_id}, hash={request_hash[:16]}...")
                return True
        
        return False
    
    def _record_request(self, user_id: str, request_hash: str):
        """Record a request to prevent replay"""
        key = f"{user_id}:{request_hash}"
        self._request_hashes[key] = time.time()
    
    def _cleanup_old_requests(self):
        """Remove request hashes older than the replay window"""
        now = time.time()
        cutoff = now - REPLAY_WINDOW_SECONDS * 2
        keys_to_remove = [k for k, v in self._request_hashes.items() if v < cutoff]
        for k in keys_to_remove:
            del self._request_hashes[k]
    
    @staticmethod
    def generate_request_hash(user_id: str, endpoint: str, params: dict) -> str:
        """Generate a unique hash for a request to detect replays"""
        # Sort params for consistent hashing
        sorted_params = sorted(params.items())
        data = f"{user_id}:{endpoint}:{sorted_params}"
        return hashlib.sha256(data.encode()).hexdigest()


# ============================================================================
# PROMPT SAFETY SERVICE
# ============================================================================
class PromptSafetyService:
    """
    Protects against copyright infringement and celebrity likeness in AI generation.
    """
    
    @staticmethod
    def check_copyright_violation(text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains copyrighted content references.
        
        Returns: (is_safe, violation_term)
        """
        if not text:
            return True, None
        
        text_lower = text.lower()
        
        for keyword in COPYRIGHT_KEYWORDS:
            if keyword in text_lower:
                return False, keyword
        
        return True, None
    
    @staticmethod
    def check_celebrity_reference(text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains celebrity name references.
        
        Returns: (is_safe, violation_term)
        """
        if not text:
            return True, None
        
        text_lower = text.lower()
        
        for keyword in CELEBRITY_KEYWORDS:
            if keyword in text_lower:
                return False, keyword
        
        return True, None
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """
        Sanitize a prompt by removing/replacing dangerous content.
        """
        if not prompt:
            return ""
        
        sanitized = prompt
        
        # Remove copyright keywords
        for keyword in COPYRIGHT_KEYWORDS:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            sanitized = pattern.sub("[character]", sanitized)
        
        # Remove celebrity keywords
        for keyword in CELEBRITY_KEYWORDS:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            sanitized = pattern.sub("[person]", sanitized)
        
        return sanitized.strip()
    
    @staticmethod
    def get_negative_prompt() -> str:
        """Get the universal negative prompt to inject into all image generation"""
        return ", ".join(UNIVERSAL_NEGATIVE_PROMPTS)
    
    @staticmethod
    def validate_generation_prompt(prompt: str) -> Tuple[bool, str]:
        """
        Full validation of a generation prompt.
        
        Returns: (is_valid, error_message)
        """
        if not prompt or not prompt.strip():
            return False, "Prompt cannot be empty"
        
        if len(prompt) > 2000:
            return False, "Prompt too long (max 2000 characters)"
        
        # Check copyright
        is_safe, violation = PromptSafetyService.check_copyright_violation(prompt)
        if not is_safe:
            return False, f"Copyrighted content detected: '{violation}'. Please use original content."
        
        # Check celebrity
        is_safe, violation = PromptSafetyService.check_celebrity_reference(prompt)
        if not is_safe:
            return False, f"Celebrity reference detected: '{violation}'. We cannot generate content featuring real people."
        
        return True, ""


# ============================================================================
# DOWNLOAD PROTECTION SERVICE
# ============================================================================
class DownloadProtectionService:
    """
    Protects generated content with signed URLs that expire.
    Prevents direct file URL access and sharing of premium content.
    """
    
    @staticmethod
    def generate_signed_url(
        file_path: str,
        user_id: str,
        expiry_seconds: int = SIGNED_URL_EXPIRY_SECONDS
    ) -> str:
        """
        Generate a signed URL for secure file access.
        
        The URL contains:
        - File path
        - User ID (for audit)
        - Expiry timestamp
        - HMAC signature
        """
        expires_at = int(time.time()) + expiry_seconds
        
        # Create signature data
        data = f"{file_path}:{user_id}:{expires_at}"
        signature = hmac.new(
            SIGNED_URL_SECRET.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        # Encode the token
        token = f"{expires_at}.{signature}"
        
        return token
    
    @staticmethod
    def verify_signed_url(
        file_path: str,
        user_id: str,
        token: str
    ) -> Tuple[bool, str]:
        """
        Verify a signed URL token.
        
        Returns: (is_valid, error_message)
        """
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return False, "Invalid token format"
            
            expires_at = int(parts[0])
            provided_signature = parts[1]
            
            # Check expiry
            if time.time() > expires_at:
                return False, "Download link has expired. Please generate a new one."
            
            # Verify signature
            data = f"{file_path}:{user_id}:{expires_at}"
            expected_signature = hmac.new(
                SIGNED_URL_SECRET.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()[:32]
            
            if not hmac.compare_digest(provided_signature, expected_signature):
                return False, "Invalid download signature"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Signed URL verification failed: {e}")
            return False, "Invalid download token"
    
    @staticmethod
    def create_download_response(
        file_path: str,
        user_id: str,
        filename: str,
        user_plan: str = "free"
    ) -> dict:
        """
        Create a secure download response with signed URL.
        """
        token = DownloadProtectionService.generate_signed_url(file_path, user_id)
        expires_in = SIGNED_URL_EXPIRY_SECONDS
        
        return {
            "download_token": token,
            "filename": filename,
            "expires_in_seconds": expires_in,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            "is_watermarked": user_plan == "free"
        }


# ============================================================================
# ROLE PROTECTION SERVICE
# ============================================================================
class RoleProtectionService:
    """
    Protects admin-only operations and prevents privilege escalation.
    """
    
    PROTECTED_OPERATIONS = [
        "modify_credits",
        "modify_pricing",
        "modify_user_role",
        "access_admin_panel",
        "view_all_users",
        "export_user_data",
        "modify_system_settings"
    ]
    
    @staticmethod
    def check_admin_permission(user: dict, operation: str) -> Tuple[bool, str]:
        """
        Check if user has permission for an admin operation.
        
        Returns: (has_permission, error_message)
        """
        role = user.get("role", "").upper()
        
        if role not in ["ADMIN", "SUPERADMIN"]:
            return False, f"Admin access required for: {operation}"
        
        # SuperAdmin can do everything
        if role == "SUPERADMIN":
            return True, ""
        
        # Regular Admin restrictions (if needed)
        # Currently all admins have full access, but this can be extended
        
        return True, ""
    
    @staticmethod
    def validate_credit_modification(
        admin_user: dict,
        target_user_id: str,
        amount: int
    ) -> Tuple[bool, str]:
        """
        Validate an admin credit modification request.
        """
        # Prevent self-modification for security
        if admin_user.get("id") == target_user_id:
            role = admin_user.get("role", "").upper()
            if role != "SUPERADMIN":
                return False, "Cannot modify your own credits"
        
        # Validate amount
        if amount < 0 or amount > 999999999:
            return False, "Invalid credit amount"
        
        return True, ""


# ============================================================================
# AUDIT LOGGING
# ============================================================================
async def log_security_event(
    db,
    event_type: str,
    user_id: Optional[str],
    details: dict,
    severity: str = "INFO",
    ip_address: Optional[str] = None
):
    """
    Log a security-related event for audit purposes.
    """
    await db.security_audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "user_id": user_id,
        "details": details,
        "severity": severity,
        "ip_address": ip_address,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    if severity in ["WARNING", "ERROR", "CRITICAL"]:
        logger.warning(f"SECURITY: {event_type} - user={user_id} - {details}")


# ============================================================================
# EXPORTS
# ============================================================================
__all__ = [
    'CreditProtectionService',
    'PromptSafetyService', 
    'DownloadProtectionService',
    'RoleProtectionService',
    'log_security_event',
    'UNIVERSAL_NEGATIVE_PROMPTS',
    'COPYRIGHT_KEYWORDS',
    'CELEBRITY_KEYWORDS'
]
