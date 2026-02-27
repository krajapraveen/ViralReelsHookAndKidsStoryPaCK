"""
Two-Factor Authentication (2FA) Service
CreatorStudio AI - Email-based OTP verification

Features:
- Generate 6-digit OTP codes
- Email delivery via configured provider
- Time-limited codes (5 minutes)
- Rate limiting on OTP requests
- Secure code storage with hashing
"""
import os
import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3
OTP_COOLDOWN_SECONDS = 60  # Minimum time between OTP requests


class TwoFactorAuthService:
    """
    Email-based Two-Factor Authentication service.
    """
    
    def __init__(self, db):
        self.db = db
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', 'noreply@creatorstudio.ai')
    
    def _generate_otp(self) -> str:
        """Generate a secure 6-digit OTP"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])
    
    def _hash_otp(self, otp: str, user_id: str) -> str:
        """Hash OTP for secure storage"""
        data = f"{otp}:{user_id}:{os.environ.get('JWT_SECRET', 'secret')}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def is_2fa_enabled(self, user_id: str) -> bool:
        """Check if user has 2FA enabled"""
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "two_factor_enabled": 1})
        return user.get("two_factor_enabled", False) if user else False
    
    async def enable_2fa(self, user_id: str) -> Tuple[bool, str]:
        """Enable 2FA for a user"""
        result = await self.db.users.update_one(
            {"id": user_id},
            {"$set": {"two_factor_enabled": True, "two_factor_enabled_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.modified_count > 0:
            logger.info(f"2FA enabled for user {user_id}")
            return True, "Two-factor authentication enabled successfully"
        return False, "Failed to enable 2FA"
    
    async def disable_2fa(self, user_id: str) -> Tuple[bool, str]:
        """Disable 2FA for a user"""
        result = await self.db.users.update_one(
            {"id": user_id},
            {"$set": {"two_factor_enabled": False}, "$unset": {"two_factor_enabled_at": ""}}
        )
        
        if result.modified_count > 0:
            logger.info(f"2FA disabled for user {user_id}")
            return True, "Two-factor authentication disabled"
        return False, "Failed to disable 2FA"
    
    async def generate_and_send_otp(self, user_id: str, email: str, purpose: str = "login") -> Tuple[bool, str]:
        """
        Generate OTP and send to user's email.
        
        Args:
            user_id: User's ID
            email: User's email address
            purpose: Purpose of OTP (login, enable_2fa, sensitive_action)
            
        Returns: (success, message)
        """
        # Check cooldown
        recent_otp = await self.db.otp_codes.find_one({
            "user_id": user_id,
            "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(seconds=OTP_COOLDOWN_SECONDS)).isoformat()}
        })
        
        if recent_otp:
            wait_time = OTP_COOLDOWN_SECONDS - (datetime.now(timezone.utc) - datetime.fromisoformat(recent_otp["created_at"])).seconds
            return False, f"Please wait {wait_time} seconds before requesting a new code"
        
        # Generate OTP
        otp = self._generate_otp()
        otp_hash = self._hash_otp(otp, user_id)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
        
        # Store OTP (invalidate previous ones)
        await self.db.otp_codes.update_many(
            {"user_id": user_id, "purpose": purpose, "used": False},
            {"$set": {"used": True, "invalidated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        await self.db.otp_codes.insert_one({
            "user_id": user_id,
            "email": email,
            "otp_hash": otp_hash,
            "purpose": purpose,
            "attempts": 0,
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat()
        })
        
        # Send email
        try:
            await self._send_otp_email(email, otp, purpose)
            logger.info(f"OTP sent to {email} for user {user_id} ({purpose})")
            return True, f"Verification code sent to {self._mask_email(email)}"
        except Exception as e:
            logger.error(f"Failed to send OTP email: {e}")
            return False, "Failed to send verification code. Please try again."
    
    async def verify_otp(self, user_id: str, otp: str, purpose: str = "login") -> Tuple[bool, str]:
        """
        Verify an OTP code.
        
        Returns: (is_valid, message)
        """
        otp_hash = self._hash_otp(otp, user_id)
        
        # Find the OTP record
        otp_record = await self.db.otp_codes.find_one({
            "user_id": user_id,
            "purpose": purpose,
            "used": False,
            "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
        })
        
        if not otp_record:
            return False, "Invalid or expired verification code"
        
        # Check attempts
        if otp_record["attempts"] >= MAX_OTP_ATTEMPTS:
            await self.db.otp_codes.update_one(
                {"_id": otp_record["_id"]},
                {"$set": {"used": True, "invalidated_at": datetime.now(timezone.utc).isoformat()}}
            )
            return False, "Too many failed attempts. Please request a new code."
        
        # Verify hash
        if otp_record["otp_hash"] != otp_hash:
            await self.db.otp_codes.update_one(
                {"_id": otp_record["_id"]},
                {"$inc": {"attempts": 1}}
            )
            remaining = MAX_OTP_ATTEMPTS - otp_record["attempts"] - 1
            return False, f"Invalid code. {remaining} attempts remaining."
        
        # Mark as used
        await self.db.otp_codes.update_one(
            {"_id": otp_record["_id"]},
            {"$set": {"used": True, "verified_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        logger.info(f"OTP verified for user {user_id} ({purpose})")
        return True, "Verification successful"
    
    async def _send_otp_email(self, email: str, otp: str, purpose: str):
        """Send OTP via email"""
        purpose_text = {
            "login": "log in to your account",
            "enable_2fa": "enable two-factor authentication",
            "disable_2fa": "disable two-factor authentication",
            "sensitive_action": "complete this action"
        }.get(purpose, "verify your identity")
        
        subject = f"Your CreatorStudio AI Verification Code: {otp}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #0f172a; color: #e2e8f0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #1e293b; padding: 40px; border-radius: 12px; }}
                .logo {{ text-align: center; margin-bottom: 30px; }}
                .otp-code {{ font-size: 36px; font-weight: bold; text-align: center; color: #8b5cf6; letter-spacing: 8px; padding: 20px; background-color: #0f172a; border-radius: 8px; margin: 20px 0; }}
                .message {{ text-align: center; color: #94a3b8; margin-bottom: 20px; }}
                .warning {{ font-size: 12px; color: #ef4444; text-align: center; margin-top: 20px; }}
                .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <h1 style="color: #8b5cf6;">CreatorStudio AI</h1>
                </div>
                <p class="message">Use this verification code to {purpose_text}:</p>
                <div class="otp-code">{otp}</div>
                <p class="message">This code expires in {OTP_EXPIRY_MINUTES} minutes.</p>
                <p class="warning">If you didn't request this code, please ignore this email and ensure your account is secure.</p>
                <div class="footer">
                    <p>&copy; 2026 CreatorStudio AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        CreatorStudio AI Verification Code
        
        Use this code to {purpose_text}: {otp}
        
        This code expires in {OTP_EXPIRY_MINUTES} minutes.
        
        If you didn't request this code, please ignore this email.
        """
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = email
        
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email (if SMTP configured)
        if self.smtp_user and self.smtp_password:
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            except Exception as e:
                logger.error(f"SMTP send failed: {e}")
                # Fall back to logging the OTP (for development)
                logger.info(f"[DEV] OTP for {email}: {otp}")
        else:
            # Development mode - log OTP
            logger.info(f"[DEV MODE] OTP for {email}: {otp}")
    
    def _mask_email(self, email: str) -> str:
        """Mask email for display (e.g., j***@gmail.com)"""
        if '@' not in email:
            return email
        local, domain = email.split('@')
        if len(local) <= 2:
            masked_local = local[0] + '***'
        else:
            masked_local = local[0] + '***' + local[-1]
        return f"{masked_local}@{domain}"


# Singleton
_two_factor_service = None


def get_two_factor_service(db) -> TwoFactorAuthService:
    """Get or create the 2FA service singleton"""
    global _two_factor_service
    if _two_factor_service is None:
        _two_factor_service = TwoFactorAuthService(db)
    return _two_factor_service


__all__ = [
    'TwoFactorAuthService',
    'get_two_factor_service',
    'OTP_EXPIRY_MINUTES'
]
