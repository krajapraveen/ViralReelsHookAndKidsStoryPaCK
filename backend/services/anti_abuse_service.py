"""
Anti-Abuse Service for Free Credits Protection
Implements: Device Fingerprinting, IP Tracking, Disposable Email Blocking,
Phone Verification, and Delayed Credit Release
"""
import os
import hashlib
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("anti_abuse")

# Disposable email domains to block (comprehensive list)
DISPOSABLE_EMAIL_DOMAINS = {
    # Popular disposable email services
    "mailinator.com", "guerrillamail.com", "guerrillamail.org", "sharklasers.com",
    "grr.la", "guerrillamail.biz", "guerrillamail.de", "guerrillamail.net",
    "10minutemail.com", "10minutemail.net", "10minmail.com", "10mail.org",
    "tempmail.com", "temp-mail.org", "tempail.com", "tempr.email",
    "throwaway.email", "throwawaymail.com", "trash-mail.com", "trashmail.com",
    "trashmail.net", "trashmail.org", "fakeinbox.com", "fakemailgenerator.com",
    "getnada.com", "nada.email", "dispostable.com", "mailnesia.com",
    "maildrop.cc", "mailsac.com", "mohmal.com", "tempinbox.com",
    "yopmail.com", "yopmail.fr", "yopmail.net", "cool.fr.nf",
    "jetable.fr.nf", "nospam.ze.tc", "nomail.xl.cx", "mega.zik.dj",
    "speed.1s.fr", "courriel.fr.nf", "moncourrier.fr.nf", "monemail.fr.nf",
    "monmail.fr.nf", "hide.biz.st", "mytrashmail.com", "mt2009.com",
    "thankyou2010.com", "trash2009.com", "mt2014.com", "tempsky.com",
    "mailcatch.com", "mailexpire.com", "mailmoat.com", "mailnull.com",
    "meltmail.com", "mintemail.com", "mt2015.com", "mytempemail.com",
    "nobulk.com", "noclickemail.com", "nogmailspam.info", "nomail.pw",
    "nomail.xl.cx", "no-spam.ws", "notmailinator.com", "nowmymail.com",
    "ownmail.net", "pookmail.com", "proxymail.eu", "rcpt.at",
    "rejectmail.com", "rtrtr.com", "s0ny.net", "safe-mail.net",
    "safetymail.info", "safetypost.de", "sandelf.de", "saynotospams.com",
    "selfdestructingmail.com", "sendspamhere.com", "shitmail.me",
    "sinnlos-mail.de", "siteposter.net", "smellfear.com", "snakemail.com",
    "sneakemail.com", "sofort-mail.de", "sogetthis.com", "soodonims.com",
    "spam4.me", "spamavert.com", "spambob.com", "spambob.net",
    "spambob.org", "spambog.com", "spambog.de", "spambog.ru",
    "spambox.info", "spambox.irishspringrealty.com", "spambox.us",
    "spamcannon.com", "spamcannon.net", "spamcero.com", "spamcon.org",
    "spamcorptastic.com", "spamcowboy.com", "spamcowboy.net", "spamcowboy.org",
    "spamday.com", "spameater.com", "spameater.org", "spamex.com",
    "spamfree24.com", "spamfree24.de", "spamfree24.eu", "spamfree24.info",
    "spamfree24.net", "spamfree24.org", "spamgoes.in", "spamgourmet.com",
    "spamgourmet.net", "spamgourmet.org", "spamherelots.com", "spamhereplease.com",
    "spamhole.com", "spamify.com", "spaminator.de", "spamkill.info",
    "spaml.com", "spaml.de", "spamlot.net", "spammotel.com",
    "spamobox.com", "spamoff.de", "spamsalad.in", "spamslicer.com",
    "spamspot.com", "spamthis.co.uk", "spamtroll.net", "supergreatmail.com",
    "supermailer.jp", "suremail.info", "teleworm.com", "teleworm.us",
    "tempalias.com", "tempe-mail.com", "tempemail.biz", "tempemail.co.za",
    "tempemail.com", "tempemail.net", "tempinbox.co.uk", "tempinbox.com",
    "tempmail.co", "tempmail.de", "tempmail.eu", "tempmail.it",
    "tempmail.net", "tempmail2.com", "tempmaildemo.com", "tempmailer.com",
    "tempmailaddress.com", "tempthe.net", "thankdog.net", "thisisnotmyrealemail.com",
    "throam.com", "throwam.com", "tilien.com", "tmailinator.com",
    "tradermail.info", "trbvm.com", "trickmail.net", "tyldd.com",
    "uggsrock.com", "upliftnow.com", "uplipht.com", "venompen.com",
    "veryrealemail.com", "viditag.com", "viralplays.com", "vkcode.ru",
    "whatiaas.com", "whatpaas.com", "wh4f.org", "whopy.com",
    "wilemail.com", "willselfdestruct.com", "winemaven.info", "wronghead.com",
    "wuzup.net", "wuzupmail.net", "wwwnew.eu", "xagloo.com",
    "xemaps.com", "xents.com", "xmaily.com", "xoxy.net",
    "yapped.net", "yeah.net", "yep.it", "yogamaven.com",
    "yuurok.com", "zehnminutenmail.de", "zippymail.info", "zoaxe.com",
    "zoemail.com", "zoemail.net", "zoemail.org", "zomg.info",
    # Additional common ones
    "getairmail.com", "discard.email", "discardmail.com", "emailondeck.com",
    "mailforspam.com", "mytemp.email", "tempail.com", "tempmailaddress.com"
}

# Configuration
MAX_ACCOUNTS_PER_IP_PER_MONTH = 2
MAX_ACCOUNTS_PER_DEVICE = 1
INITIAL_CREDITS = 0  # ZERO credits until email verified
PENDING_CREDITS = 20  # Credits released after email verification
DELAYED_CREDITS = 80  # Remaining 80 released over time
DELAYED_CREDIT_DAYS = 7  # Release over 7 days
EMAIL_VERIFICATION_DEADLINE_HOURS = 24  # Must verify within 24 hours


class AntiAbuseService:
    def __init__(self, db):
        self.db = db
    
    # ==================== DISPOSABLE EMAIL DETECTION ====================
    
    def is_disposable_email(self, email: str) -> Tuple[bool, str]:
        """Check if email is from a disposable email service"""
        if not email or "@" not in email:
            return True, "Invalid email format"
        
        domain = email.lower().split("@")[1]
        
        # Check against known disposable domains
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            return True, f"Disposable email service '{domain}' not allowed"
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r"temp.*mail", r"fake.*mail", r"throw.*away", r"trash.*mail",
            r"spam.*", r"disposable", r"10.*min", r"guerrilla"
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, domain, re.IGNORECASE):
                return True, f"Suspicious email domain pattern detected"
        
        return False, "Email domain acceptable"
    
    # ==================== IP ADDRESS TRACKING ====================
    
    async def check_ip_limit(self, ip_address: str) -> Tuple[bool, str, int]:
        """Check if IP has exceeded signup limit"""
        if not ip_address or ip_address in ["127.0.0.1", "localhost"]:
            return True, "IP check passed (localhost)", 0
        
        # Get signups from this IP in the last 30 days
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        
        signup_count = await self.db.ip_signup_tracking.count_documents({
            "ip_address": ip_address,
            "signup_date": {"$gte": thirty_days_ago}
        })
        
        if signup_count >= MAX_ACCOUNTS_PER_IP_PER_MONTH:
            return False, f"Maximum {MAX_ACCOUNTS_PER_IP_PER_MONTH} accounts per IP per month exceeded", signup_count
        
        return True, "IP limit not exceeded", signup_count
    
    async def record_ip_signup(self, ip_address: str, user_id: str, email: str):
        """Record a signup from an IP address"""
        await self.db.ip_signup_tracking.insert_one({
            "ip_address": ip_address,
            "user_id": user_id,
            "email": email,
            "signup_date": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # ==================== DEVICE FINGERPRINTING ====================
    
    def generate_fingerprint_hash(self, fingerprint_data: Dict[str, Any]) -> str:
        """Generate a hash from device fingerprint data"""
        # Combine key fingerprint components
        components = [
            str(fingerprint_data.get("canvas", "")),
            str(fingerprint_data.get("webgl", "")),
            str(fingerprint_data.get("webgl_vendor", "")),
            str(fingerprint_data.get("webgl_renderer", "")),
            str(fingerprint_data.get("timezone", "")),
            str(fingerprint_data.get("language", "")),
            str(fingerprint_data.get("platform", "")),
            str(fingerprint_data.get("screen_resolution", "")),
            str(fingerprint_data.get("color_depth", "")),
            str(fingerprint_data.get("hardware_concurrency", "")),
            str(fingerprint_data.get("device_memory", "")),
            str(sorted(fingerprint_data.get("fonts", []))),
            str(sorted(fingerprint_data.get("plugins", []))),
        ]
        
        fingerprint_string = "|".join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    async def check_device_fingerprint(self, fingerprint_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Check if device fingerprint already exists"""
        if not fingerprint_data:
            return True, "No fingerprint provided (allowing)", None
        
        fingerprint_hash = self.generate_fingerprint_hash(fingerprint_data)
        
        # Check if this fingerprint exists
        existing = await self.db.device_fingerprints.find_one({
            "fingerprint_hash": fingerprint_hash
        })
        
        if existing:
            # Check how many accounts are associated with this device
            account_count = await self.db.device_fingerprints.count_documents({
                "fingerprint_hash": fingerprint_hash
            })
            
            if account_count >= MAX_ACCOUNTS_PER_DEVICE:
                return False, f"This device already has {account_count} account(s). Maximum {MAX_ACCOUNTS_PER_DEVICE} allowed.", fingerprint_hash
        
        return True, "Device fingerprint acceptable", fingerprint_hash
    
    async def record_device_fingerprint(self, fingerprint_hash: str, user_id: str, email: str, fingerprint_data: Dict[str, Any]):
        """Record a device fingerprint for a new user"""
        await self.db.device_fingerprints.insert_one({
            "fingerprint_hash": fingerprint_hash,
            "user_id": user_id,
            "email": email,
            "fingerprint_data": {
                "platform": fingerprint_data.get("platform"),
                "language": fingerprint_data.get("language"),
                "timezone": fingerprint_data.get("timezone"),
                "screen_resolution": fingerprint_data.get("screen_resolution"),
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # ==================== PHONE VERIFICATION ====================
    
    async def check_phone_number(self, phone_number: str) -> Tuple[bool, str]:
        """Check if phone number is already used"""
        if not phone_number:
            return True, "No phone number provided"
        
        # Normalize phone number (remove spaces, dashes)
        normalized = re.sub(r"[\s\-\(\)]", "", phone_number)
        
        # Check if phone number exists
        existing = await self.db.phone_verifications.find_one({
            "phone_number": normalized,
            "verified": True
        })
        
        if existing:
            return False, "This phone number is already associated with an account"
        
        return True, "Phone number available"
    
    async def record_phone_verification(self, phone_number: str, user_id: str, email: str):
        """Record a verified phone number"""
        normalized = re.sub(r"[\s\-\(\)]", "", phone_number)
        
        await self.db.phone_verifications.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "phone_number": normalized,
                    "user_id": user_id,
                    "email": email,
                    "verified": True,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
    
    # ==================== DELAYED CREDIT RELEASE ====================
    
    def get_initial_credits(self) -> int:
        """Get the number of credits to give on signup (ZERO until email verified)"""
        return INITIAL_CREDITS
    
    def get_pending_credits(self) -> int:
        """Get the number of credits pending email verification"""
        return PENDING_CREDITS
    
    async def setup_delayed_credits(self, user_id: str, email: str):
        """Setup delayed credit release schedule"""
        now = datetime.now(timezone.utc)
        
        # Create release schedule - release credits daily over 7 days
        credits_per_day = DELAYED_CREDITS // DELAYED_CREDIT_DAYS
        remaining = DELAYED_CREDITS % DELAYED_CREDIT_DAYS
        
        schedule = []
        for day in range(1, DELAYED_CREDIT_DAYS + 1):
            release_date = (now + timedelta(days=day)).replace(hour=0, minute=0, second=0, microsecond=0)
            credits_to_release = credits_per_day + (1 if day <= remaining else 0)
            
            schedule.append({
                "day": day,
                "release_date": release_date.isoformat(),
                "credits": credits_to_release,
                "released": False
            })
        
        await self.db.delayed_credits.insert_one({
            "user_id": user_id,
            "email": email,
            "total_delayed_credits": DELAYED_CREDITS,
            "credits_released": 0,
            "schedule": schedule,
            "created_at": now.isoformat()
        })
    
    async def process_delayed_credits(self, user_id: str) -> int:
        """Process and release any due delayed credits"""
        now = datetime.now(timezone.utc)
        
        delayed_record = await self.db.delayed_credits.find_one({"user_id": user_id})
        if not delayed_record:
            return 0
        
        credits_to_release = 0
        updated_schedule = []
        
        for item in delayed_record.get("schedule", []):
            if not item["released"] and item["release_date"] <= now.isoformat():
                credits_to_release += item["credits"]
                item["released"] = True
                item["released_at"] = now.isoformat()
            updated_schedule.append(item)
        
        if credits_to_release > 0:
            # Update the schedule
            await self.db.delayed_credits.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "schedule": updated_schedule,
                        "credits_released": delayed_record.get("credits_released", 0) + credits_to_release
                    }
                }
            )
        
        return credits_to_release
    
    async def get_delayed_credits_status(self, user_id: str) -> Dict[str, Any]:
        """Get status of delayed credits for a user"""
        delayed_record = await self.db.delayed_credits.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if not delayed_record:
            return {"has_delayed_credits": False}
        
        pending_credits = sum(
            item["credits"] for item in delayed_record.get("schedule", [])
            if not item["released"]
        )
        
        next_release = None
        for item in delayed_record.get("schedule", []):
            if not item["released"]:
                next_release = {
                    "date": item["release_date"],
                    "credits": item["credits"]
                }
                break
        
        return {
            "has_delayed_credits": True,
            "total_delayed": delayed_record.get("total_delayed_credits", 0),
            "released": delayed_record.get("credits_released", 0),
            "pending": pending_credits,
            "next_release": next_release
        }
    
    # ==================== COMPREHENSIVE SIGNUP CHECK ====================
    
    async def validate_signup(
        self,
        email: str,
        ip_address: str,
        fingerprint_data: Optional[Dict[str, Any]] = None,
        phone_number: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Comprehensive signup validation combining all anti-abuse checks
        Returns: (is_valid, message, details)
        """
        details = {
            "email_check": None,
            "ip_check": None,
            "device_check": None,
            "phone_check": None,
            "blocked_reason": None
        }
        
        # 1. Check disposable email
        is_valid_email, email_msg = self.is_disposable_email(email)
        details["email_check"] = {"valid": not is_valid_email if "not allowed" in email_msg else is_valid_email, "message": email_msg}
        
        if "not allowed" in email_msg or "Suspicious" in email_msg:
            details["blocked_reason"] = "disposable_email"
            return False, email_msg, details
        
        # 2. Check IP limit
        ip_valid, ip_msg, ip_count = await self.check_ip_limit(ip_address)
        details["ip_check"] = {"valid": ip_valid, "message": ip_msg, "signup_count": ip_count}
        
        if not ip_valid:
            details["blocked_reason"] = "ip_limit_exceeded"
            return False, ip_msg, details
        
        # 3. Check device fingerprint
        if fingerprint_data:
            device_valid, device_msg, fingerprint_hash = await self.check_device_fingerprint(fingerprint_data)
            details["device_check"] = {"valid": device_valid, "message": device_msg, "fingerprint_hash": fingerprint_hash[:16] + "..." if fingerprint_hash else None}
            
            if not device_valid:
                details["blocked_reason"] = "device_limit_exceeded"
                return False, device_msg, details
        
        # 4. Check phone number (if provided)
        if phone_number:
            phone_valid, phone_msg = await self.check_phone_number(phone_number)
            details["phone_check"] = {"valid": phone_valid, "message": phone_msg}
            
            if not phone_valid:
                details["blocked_reason"] = "phone_already_used"
                return False, phone_msg, details
        
        return True, "All anti-abuse checks passed", details
    
    async def record_signup(
        self,
        user_id: str,
        email: str,
        ip_address: str,
        fingerprint_data: Optional[Dict[str, Any]] = None,
        phone_number: Optional[str] = None
    ):
        """Record all signup data for anti-abuse tracking"""
        # Record IP
        await self.record_ip_signup(ip_address, user_id, email)
        
        # Record device fingerprint
        if fingerprint_data:
            fingerprint_hash = self.generate_fingerprint_hash(fingerprint_data)
            await self.record_device_fingerprint(fingerprint_hash, user_id, email, fingerprint_data)
        
        # Record phone
        if phone_number:
            await self.record_phone_verification(phone_number, user_id, email)
        
        # Setup delayed credits
        await self.setup_delayed_credits(user_id, email)
        
        # Log the signup
        await self.db.anti_abuse_logs.insert_one({
            "event": "signup_recorded",
            "user_id": user_id,
            "email": email,
            "ip_address": ip_address,
            "has_fingerprint": fingerprint_data is not None,
            "has_phone": phone_number is not None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# Singleton instance
_anti_abuse_service: Optional[AntiAbuseService] = None

def get_anti_abuse_service(db) -> AntiAbuseService:
    global _anti_abuse_service
    if _anti_abuse_service is None:
        _anti_abuse_service = AntiAbuseService(db)
    return _anti_abuse_service
