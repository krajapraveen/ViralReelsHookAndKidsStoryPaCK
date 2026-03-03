"""
Anti-Abuse API Routes
Endpoints for signup validation, phone verification, and delayed credits
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import os
import sys
import random
import string

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from services.anti_abuse_service import get_anti_abuse_service

router = APIRouter(prefix="/anti-abuse", tags=["Anti-Abuse"])

# In-memory OTP storage (in production, use Redis)
_otp_storage: Dict[str, Dict[str, Any]] = {}


class SignupValidationRequest(BaseModel):
    email: str
    fingerprint: Optional[Dict[str, Any]] = None
    phone_number: Optional[str] = None


class PhoneOTPRequest(BaseModel):
    phone_number: str


class PhoneVerifyRequest(BaseModel):
    phone_number: str
    otp: str


@router.post("/validate-signup")
async def validate_signup(request: Request, data: SignupValidationRequest):
    """
    Validate signup request against anti-abuse rules
    Called before creating a new account
    """
    # Get client IP
    ip_address = request.headers.get("X-Forwarded-For", request.client.host)
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    
    anti_abuse = get_anti_abuse_service(db)
    
    is_valid, message, details = await anti_abuse.validate_signup(
        email=data.email,
        ip_address=ip_address,
        fingerprint_data=data.fingerprint,
        phone_number=data.phone_number
    )
    
    if not is_valid:
        logger.warning(f"Signup blocked: {data.email} - {message} - IP: {ip_address}")
        
        # Log blocked attempt
        await db.blocked_signups.insert_one({
            "email": data.email,
            "ip_address": ip_address,
            "reason": details.get("blocked_reason"),
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "valid": False,
            "message": message,
            "error_code": details.get("blocked_reason", "validation_failed")
        }
    
    return {
        "valid": True,
        "message": "Signup validation passed",
        "initial_credits": anti_abuse.get_initial_credits(),
        "has_delayed_credits": True,
        "delayed_credits_info": "Additional credits will be released over 7 days of activity"
    }


@router.post("/send-otp")
async def send_phone_otp(request: Request, data: PhoneOTPRequest):
    """
    Send OTP to phone number for verification
    """
    phone = data.phone_number.strip()
    
    # Validate phone format
    if not phone or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    
    # Check if phone already used
    anti_abuse = get_anti_abuse_service(db)
    phone_valid, phone_msg = await anti_abuse.check_phone_number(phone)
    
    if not phone_valid:
        raise HTTPException(status_code=400, detail=phone_msg)
    
    # Generate OTP
    otp = ''.join(random.choices(string.digits, k=6))
    
    # Store OTP (expires in 10 minutes)
    _otp_storage[phone] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc).timestamp() + 600,
        "attempts": 0
    }
    
    # In production, send via SMS service (Twilio, MSG91, etc.)
    # For now, we'll log it and return success
    logger.info(f"OTP for {phone}: {otp}")
    
    # Try to send via SMS if configured
    sms_sent = False
    try:
        # Check if Twilio is configured
        twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
        
        if twilio_sid and twilio_token and twilio_phone:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            message = client.messages.create(
                body=f"Your Visionary Suite verification code is: {otp}. Valid for 10 minutes.",
                from_=twilio_phone,
                to=phone
            )
            sms_sent = True
            logger.info(f"SMS sent to {phone}: {message.sid}")
    except Exception as e:
        logger.warning(f"SMS send failed: {e}")
    
    return {
        "success": True,
        "message": "OTP sent successfully" if sms_sent else "OTP generated (SMS service not configured - check logs)",
        "phone_masked": phone[:3] + "****" + phone[-4:] if len(phone) > 7 else "****",
        "expires_in_seconds": 600
    }


@router.post("/verify-otp")
async def verify_phone_otp(data: PhoneVerifyRequest):
    """
    Verify OTP for phone number
    """
    phone = data.phone_number.strip()
    otp = data.otp.strip()
    
    stored = _otp_storage.get(phone)
    
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP found for this phone number. Please request a new one.")
    
    # Check expiry
    if datetime.now(timezone.utc).timestamp() > stored["expires_at"]:
        del _otp_storage[phone]
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    
    # Check attempts
    if stored["attempts"] >= 3:
        del _otp_storage[phone]
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please request a new OTP.")
    
    # Verify OTP
    if stored["otp"] != otp:
        stored["attempts"] += 1
        raise HTTPException(status_code=400, detail=f"Invalid OTP. {3 - stored['attempts']} attempts remaining.")
    
    # Success - clean up
    del _otp_storage[phone]
    
    return {
        "success": True,
        "message": "Phone number verified successfully",
        "phone_verified": True
    }


@router.get("/delayed-credits/status")
async def get_delayed_credits_status(user: dict = Depends(get_current_user)):
    """
    Get status of delayed credits for current user
    """
    anti_abuse = get_anti_abuse_service(db)
    status = await anti_abuse.get_delayed_credits_status(user["id"])
    
    return {
        "success": True,
        **status
    }


@router.post("/delayed-credits/claim")
async def claim_delayed_credits(user: dict = Depends(get_current_user)):
    """
    Claim any available delayed credits
    """
    anti_abuse = get_anti_abuse_service(db)
    
    # Process delayed credits
    credits_released = await anti_abuse.process_delayed_credits(user["id"])
    
    if credits_released > 0:
        # Add credits to user
        from shared import add_credits
        new_balance = await add_credits(
            user_id=user["id"],
            amount=credits_released,
            description=f"Delayed signup bonus credits released",
            tx_type="BONUS"
        )
        
        return {
            "success": True,
            "credits_released": credits_released,
            "new_balance": new_balance,
            "message": f"Congratulations! {credits_released} bonus credits have been added to your account!"
        }
    
    # Get status for more info
    status = await anti_abuse.get_delayed_credits_status(user["id"])
    
    return {
        "success": True,
        "credits_released": 0,
        "message": "No credits available for release yet",
        "next_release": status.get("next_release")
    }


@router.get("/check-email")
async def check_email_validity(email: str):
    """
    Check if an email is from a disposable service
    """
    anti_abuse = get_anti_abuse_service(db)
    is_disposable, message = anti_abuse.is_disposable_email(email)
    
    return {
        "email": email,
        "is_disposable": "not allowed" in message.lower() or "suspicious" in message.lower(),
        "message": message,
        "allowed": "not allowed" not in message.lower() and "suspicious" not in message.lower()
    }


@router.get("/blocked-signups")
async def get_blocked_signups(
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """Get blocked signup attempts (Admin only)"""
    # Check admin
    if user.get("role", "").upper() not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from datetime import timedelta
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    blocked = await db.blocked_signups.find(
        {"timestamp": {"$gte": start_date}},
        {"_id": 0}
    ).sort("timestamp", -1).limit(500).to_list(500)
    
    return {
        "success": True,
        "period_days": days,
        "total": len(blocked),
        "blocked": blocked
    }


@router.get("/stats")
async def get_anti_abuse_stats(user: dict = Depends(get_current_user)):
    """Get anti-abuse statistics (Admin only)"""
    # Check admin
    if user.get("role", "").upper() not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    
    # Count blocked signups
    blocked_30d = await db.blocked_signups.count_documents({
        "timestamp": {"$gte": thirty_days_ago}
    })
    
    blocked_7d = await db.blocked_signups.count_documents({
        "timestamp": {"$gte": seven_days_ago}
    })
    
    # Count by reason
    blocked_by_reason = {}
    reasons = ["disposable_email", "ip_limit_exceeded", "device_limit_exceeded", "phone_already_used"]
    for reason in reasons:
        count = await db.blocked_signups.count_documents({
            "reason": reason,
            "timestamp": {"$gte": thirty_days_ago}
        })
        blocked_by_reason[reason] = count
    
    # Count tracked devices
    device_count = await db.device_fingerprints.count_documents({})
    
    # Count IP records
    ip_count = await db.ip_signup_tracking.count_documents({
        "signup_date": {"$gte": thirty_days_ago}
    })
    
    return {
        "success": True,
        "blocked_signups": {
            "last_30_days": blocked_30d,
            "last_7_days": blocked_7d,
            "by_reason": blocked_by_reason
        },
        "tracking": {
            "devices_tracked": device_count,
            "ip_records_30d": ip_count
        }
    }



class ResetUserVerificationRequest(BaseModel):
    email: str


@router.post("/admin/reset-user-verification")
async def reset_user_verification(
    data: ResetUserVerificationRequest,
    user: dict = Depends(get_current_user)
):
    """
    Admin endpoint to reset a user's email verification status
    This locks their credits until they verify their email
    """
    # Check admin
    if user.get("role", "").upper() not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    email = data.email.lower().strip()
    
    # Find the user
    target_user = await db.users.find_one({"email": email})
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User with email '{email}' not found")
    
    # Don't allow resetting admin accounts
    if target_user.get("role", "").upper() in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=400, detail="Cannot reset verification for admin accounts")
    
    # Store old values for logging
    old_credits = target_user.get("credits", 0)
    old_verified = target_user.get("emailVerified", False)
    
    # Generate new verification token
    import uuid
    from datetime import timedelta
    verification_token = str(uuid.uuid4())
    token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # Reset user verification status
    result = await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "emailVerified": False,
                "credits": 0,
                "pending_credits": 20,
                "credits_locked": True,
                "credits_lock_reason": "email_verification_required",
                "verificationToken": verification_token,
                "verificationTokenExpiry": token_expiry.isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update user")
    
    # Log this action
    await db.admin_audit_log.insert_one({
        "action": "reset_user_verification",
        "admin_id": user["id"],
        "admin_email": user.get("email"),
        "target_email": email,
        "old_values": {
            "credits": old_credits,
            "emailVerified": old_verified
        },
        "new_values": {
            "credits": 0,
            "emailVerified": False,
            "pending_credits": 20,
            "credits_locked": True
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"Admin {user.get('email')} reset verification for {email}")
    
    return {
        "success": True,
        "message": f"User '{email}' verification has been reset",
        "user_email": email,
        "old_credits": old_credits,
        "new_credits": 0,
        "pending_credits": 20,
        "action": "User must now verify email to unlock 20 credits"
    }


@router.get("/admin/user-verification-status")
async def get_user_verification_status(
    email: str,
    user: dict = Depends(get_current_user)
):
    """
    Admin endpoint to check a user's verification status
    """
    # Check admin
    if user.get("role", "").upper() not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    email = email.lower().strip()
    
    # Find the user
    target_user = await db.users.find_one(
        {"email": email},
        {"_id": 0, "password": 0, "verificationToken": 0}
    )
    
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User with email '{email}' not found")
    
    return {
        "success": True,
        "user": {
            "email": target_user.get("email"),
            "name": target_user.get("name"),
            "credits": target_user.get("credits", 0),
            "emailVerified": target_user.get("emailVerified", False),
            "credits_locked": target_user.get("credits_locked", False),
            "pending_credits": target_user.get("pending_credits", 0),
            "createdAt": target_user.get("createdAt")
        }
    }
