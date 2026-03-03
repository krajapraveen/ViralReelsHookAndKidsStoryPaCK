"""
Admin Routes - Dashboard, Analytics, Payment Monitoring, Exception Tracking
CreatorStudio AI Admin Panel
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_admin_user, get_current_user,
    SENDGRID_API_KEY, SENDGRID_AVAILABLE, ADMIN_ALERT_EMAIL, SENDER_EMAIL,
    hash_password
)
from security import limiter

router = APIRouter(prefix="/admin", tags=["Admin"])


# =============================================================================
# REQUEST MODELS
# =============================================================================
class ResetCreditsRequest(BaseModel):
    user_id: str
    credits: int = Field(ge=0, le=999999999)
    reason: str = Field(min_length=5, max_length=500)


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str
    password: str = Field(min_length=8)
    credits: int = Field(default=100, ge=0, le=999999999)
    role: str = Field(default="user")


class BulkResetCreditsRequest(BaseModel):
    user_ids: List[str]
    credits: int = Field(ge=0, le=999999999)
    reason: str = Field(min_length=5, max_length=500)


# =============================================================================
# USER MANAGEMENT - RESET VERIFICATION STATUS
# =============================================================================
class ResetVerificationRequest(BaseModel):
    user_id: str
    reason: str = Field(min_length=5, max_length=500, default="Admin reset for re-verification")


async def send_verification_email_for_reset(email: str, token: str, name: str):
    """Send verification email via SendGrid for admin-reset users"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email
        
        api_key = os.environ.get("SENDGRID_API_KEY")
        if not api_key:
            logger.warning("SendGrid API key not configured - cannot send verification email")
            return False
        
        frontend_url = os.environ.get("FRONTEND_URL", "https://visionary-suite.com")
        verify_url = f"{frontend_url}/verify-email?token={token}"
        
        # Use verified sender identity
        from_email = Email(
            email=os.environ.get("SENDGRID_FROM_EMAIL", "krajapraveen@visionary-suite.com"),
            name="CreatorStudio AI"
        )
        
        message = Mail(
            from_email=from_email,
            to_emails=email,
            subject="Action Required: Verify Your Email - CreatorStudio AI",
            html_content=f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; padding: 40px; border-radius: 16px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #818cf8; margin: 0;">CreatorStudio AI</h1>
                </div>
                <div style="background: #1e293b; padding: 30px; border-radius: 12px;">
                    <h2 style="color: #f1f5f9; margin-top: 0;">Hi {name}!</h2>
                    <p style="color: #94a3b8; font-size: 16px; line-height: 1.6;">
                        Your account requires email verification to unlock your <strong style="color: #fbbf24;">20 free credits</strong>.
                    </p>
                    <p style="color: #94a3b8; font-size: 16px; line-height: 1.6;">
                        Please click the button below to verify your email address and start creating amazing content!
                    </p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verify_url}" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">
                            Verify Email & Unlock Credits
                        </a>
                    </div>
                    <p style="color: #64748b; font-size: 14px;">
                        This link will expire in 24 hours. After verification, you'll receive 20 credits immediately and 80 more over the next 7 days!
                    </p>
                </div>
                <p style="color: #475569; font-size: 12px; text-align: center; margin-top: 30px;">
                    © 2026 Visionary Suite. All rights reserved.
                </p>
            </div>
            """
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info(f"Verification email sent to {email} - Status: {response.status_code}")
        return response.status_code in [200, 201, 202]
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        return False


@router.post("/users/reset-verification")
@limiter.limit("30/minute")
async def reset_user_verification(
    request: Request,
    data: ResetVerificationRequest,
    admin: dict = Depends(get_admin_user)
):
    """
    Reset a user's email verification status and credits.
    This is used to fix legacy accounts that were created before the email verification feature.
    The user will need to verify their email again to unlock credits.
    """
    try:
        # Find user
        user = await db.users.find_one({"id": data.user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        old_credits = user.get("credits", 0)
        old_verified = user.get("emailVerified", False)
        user_email = user.get("email", "")
        user_name = user.get("name", "User")
        
        # Generate new verification token
        import secrets
        verification_token = secrets.token_urlsafe(32)
        token_expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        
        # Reset user to pending verification state
        await db.users.update_one(
            {"id": data.user_id},
            {
                "$set": {
                    "emailVerified": False,
                    "credits": 0,
                    "pending_credits": 20,
                    "credits_locked": True,
                    "credits_lock_reason": "email_verification_required",
                    "verificationToken": verification_token,
                    "verificationTokenExpiry": token_expiry,
                    "verification_reset_at": datetime.now(timezone.utc).isoformat(),
                    "verification_reset_by": admin["id"]
                }
            }
        )
        
        # SEND VERIFICATION EMAIL
        email_sent = await send_verification_email_for_reset(user_email, verification_token, user_name)
        
        # Log the reset
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": data.user_id,
            "amount": -old_credits,
            "type": "ADMIN_VERIFICATION_RESET",
            "description": f"Verification reset by admin: {data.reason}. Credits will be restored after email verification.",
            "adminId": admin["id"],
            "adminEmail": admin.get("email", ""),
            "oldCredits": old_credits,
            "newCredits": 0,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Audit log
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "RESET_USER_VERIFICATION",
            "details": {
                "user_id": data.user_id,
                "user_email": user_email,
                "old_credits": old_credits,
                "old_verified": old_verified,
                "reason": data.reason,
                "email_sent": email_sent
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Admin {admin.get('email')} reset verification for {user_email}: credits {old_credits} -> 0, verified: {old_verified} -> False, email_sent: {email_sent}")
        
        return {
            "success": True,
            "message": f"User verification status reset. {'Verification email sent!' if email_sent else 'Email could not be sent - check SendGrid config.'}",
            "user_email": user_email,
            "old_credits": old_credits,
            "old_verified": old_verified,
            "email_sent": email_sent,
            "new_state": {
                "emailVerified": False,
                "credits": 0,
                "pending_credits": 20,
                "credits_locked": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting verification: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset verification status")


# =============================================================================
# USER MANAGEMENT - MANUAL VERIFY (Skip Email Verification)
# =============================================================================
class ManualVerifyRequest(BaseModel):
    user_id: str
    credits_to_grant: int = Field(default=100, ge=0, le=1000000)
    reason: str = Field(min_length=5, max_length=500, default="Admin manual verification")


@router.post("/users/manual-verify")
@limiter.limit("30/minute")
async def manual_verify_user(
    request: Request,
    data: ManualVerifyRequest,
    admin: dict = Depends(get_admin_user)
):
    """
    Manually verify a user's email without requiring them to click a verification link.
    This bypasses the email verification process entirely.
    Use when: SendGrid limits exceeded, user can't receive emails, or for testing.
    """
    try:
        # Find user
        user = await db.users.find_one({"id": data.user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_email = user.get("email", "")
        old_credits = user.get("credits", 0)
        old_verified = user.get("emailVerified", False)
        
        # If already verified, just update credits if needed
        if old_verified:
            if data.credits_to_grant > 0 and old_credits != data.credits_to_grant:
                await db.users.update_one(
                    {"id": data.user_id},
                    {"$set": {"credits": data.credits_to_grant}}
                )
                return {
                    "success": True,
                    "message": f"User already verified. Credits updated to {data.credits_to_grant}.",
                    "user_email": user_email,
                    "was_already_verified": True,
                    "credits_granted": data.credits_to_grant
                }
            return {
                "success": True,
                "message": "User is already verified.",
                "user_email": user_email,
                "was_already_verified": True,
                "credits_granted": old_credits
            }
        
        # Manually verify the user
        await db.users.update_one(
            {"id": data.user_id},
            {
                "$set": {
                    "emailVerified": True,
                    "credits": data.credits_to_grant,
                    "credits_locked": False,
                    "manual_verification_at": datetime.now(timezone.utc).isoformat(),
                    "manual_verification_by": admin["id"],
                    "manual_verification_reason": data.reason
                },
                "$unset": {
                    "pending_credits": "",
                    "credits_lock_reason": "",
                    "verificationToken": "",
                    "verificationTokenExpiry": ""
                }
            }
        )
        
        # Log the manual verification
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": data.user_id,
            "amount": data.credits_to_grant,
            "type": "ADMIN_MANUAL_VERIFY",
            "description": f"Manual verification by admin: {data.reason}. Granted {data.credits_to_grant} credits.",
            "adminId": admin["id"],
            "adminEmail": admin.get("email", ""),
            "oldCredits": old_credits,
            "newCredits": data.credits_to_grant,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Audit log
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "MANUAL_VERIFY_USER",
            "details": {
                "user_id": data.user_id,
                "user_email": user_email,
                "old_credits": old_credits,
                "credits_granted": data.credits_to_grant,
                "reason": data.reason
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Admin {admin.get('email')} manually verified {user_email}: granted {data.credits_to_grant} credits")
        
        return {
            "success": True,
            "message": f"User manually verified! Granted {data.credits_to_grant} credits.",
            "user_email": user_email,
            "was_already_verified": False,
            "credits_granted": data.credits_to_grant
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual verification: {e}")
        raise HTTPException(status_code=500, detail="Failed to manually verify user")


# =============================================================================
# USER MANAGEMENT - RESET CREDITS
# =============================================================================
@router.post("/users/reset-credits")
@limiter.limit("30/minute")
async def reset_user_credits(
    request: Request,
    data: ResetCreditsRequest,
    admin: dict = Depends(get_admin_user)
):
    """Reset credits for a specific user"""
    try:
        # Find user
        user = await db.users.find_one({"id": data.user_id}, {"_id": 0, "email": 1, "name": 1, "credits": 1})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        old_credits = user.get("credits", 0)
        
        # Update credits
        await db.users.update_one(
            {"id": data.user_id},
            {"$set": {"credits": data.credits, "credits_updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Log the credit change
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": data.user_id,
            "amount": data.credits - old_credits,
            "type": "ADMIN_RESET",
            "description": f"Admin reset: {data.reason}",
            "adminId": admin["id"],
            "adminEmail": admin.get("email", ""),
            "oldCredits": old_credits,
            "newCredits": data.credits,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Audit log
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "RESET_USER_CREDITS",
            "details": {
                "user_id": data.user_id,
                "user_email": user.get("email"),
                "old_credits": old_credits,
                "new_credits": data.credits,
                "reason": data.reason
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Admin {admin.get('email')} reset credits for {user.get('email')}: {old_credits} -> {data.credits}")
        
        return {
            "success": True,
            "message": "Credits reset successfully",
            "user_email": user.get("email"),
            "old_credits": old_credits,
            "new_credits": data.credits
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting credits: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset credits")


@router.post("/users/bulk-reset-credits")
@limiter.limit("10/minute")
async def bulk_reset_credits(
    request: Request,
    data: BulkResetCreditsRequest,
    admin: dict = Depends(get_admin_user)
):
    """Reset credits for multiple users at once"""
    try:
        results = []
        
        for user_id in data.user_ids:
            user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "credits": 1})
            if not user:
                results.append({"user_id": user_id, "success": False, "error": "Not found"})
                continue
            
            old_credits = user.get("credits", 0)
            
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"credits": data.credits}}
            )
            
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "amount": data.credits - old_credits,
                "type": "ADMIN_BULK_RESET",
                "description": f"Bulk reset: {data.reason}",
                "adminId": admin["id"],
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
            
            results.append({
                "user_id": user_id,
                "user_email": user.get("email"),
                "success": True,
                "old_credits": old_credits,
                "new_credits": data.credits
            })
        
        # Audit log
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "BULK_RESET_CREDITS",
            "details": {"user_count": len(data.user_ids), "credits": data.credits, "reason": data.reason},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "results": results,
            "total_updated": len([r for r in results if r.get("success")])
        }
        
    except Exception as e:
        logger.error(f"Error in bulk reset: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk reset credits")


@router.post("/users/create")
@limiter.limit("10/minute")
async def admin_create_user(
    request: Request,
    data: CreateUserRequest,
    admin: dict = Depends(get_admin_user)
):
    """Admin create new user with specified credits"""
    try:
        # Check if email exists
        existing = await db.users.find_one({"email": data.email.lower()})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": data.email.lower(),
            "name": data.name,
            "password": hash_password(data.password),
            "role": data.role,
            "credits": data.credits,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "createdBy": admin["id"],
            "createdByAdmin": True
        }
        
        await db.users.insert_one(user)
        
        # Log initial credits
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "amount": data.credits,
            "type": "ADMIN_GRANT",
            "description": "Initial credits granted by admin",
            "adminId": admin["id"],
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Audit log
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "CREATE_USER",
            "details": {"user_id": user_id, "email": data.email, "credits": data.credits, "role": data.role},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Admin {admin.get('email')} created user {data.email} with {data.credits} credits")
        
        return {
            "success": True,
            "user": {
                "id": user_id,
                "email": data.email.lower(),
                "name": data.name,
                "role": data.role,
                "credits": data.credits
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.get("/users/list")
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    page: int = 1,
    size: int = 50,
    search: Optional[str] = None,
    role: Optional[str] = None,
    admin: dict = Depends(get_admin_user)
):
    """List all users with pagination and filters"""
    try:
        query = {}
        
        if search:
            query["$or"] = [
                {"email": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}}
            ]
        
        if role:
            query["role"] = role
        
        skip = (page - 1) * size
        total = await db.users.count_documents(query)
        
        users = await db.users.find(
            query,
            {"_id": 0, "password": 0}
        ).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
        
        return {
            "users": users,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/users/{user_id}")
@limiter.limit("60/minute")
async def get_user_details(
    request: Request,
    user_id: str,
    admin: dict = Depends(get_admin_user)
):
    """Get detailed user information"""
    try:
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get credit history
        credit_history = await db.credit_ledger.find(
            {"userId": user_id},
            {"_id": 0}
        ).sort("createdAt", -1).limit(20).to_list(20)
        
        # Get generation stats
        generation_count = await db.generations.count_documents({"userId": user_id})
        genstudio_count = await db.genstudio_jobs.count_documents({"userId": user_id})
        
        # Get login activity
        login_count = await db.login_activity.count_documents({"user_id": user_id})
        last_login = await db.login_activity.find_one(
            {"user_id": user_id, "status": "SUCCESS"},
            {"_id": 0, "timestamp": 1, "ip_address": 1, "country": 1}
        )
        
        return {
            "user": user,
            "stats": {
                "generations": generation_count,
                "genstudio_jobs": genstudio_count,
                "login_count": login_count,
                "last_login": last_login
            },
            "credit_history": credit_history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user details")


# =============================================================================
# DASHBOARD ANALYTICS
# =============================================================================
@router.get("/analytics/dashboard")
@limiter.limit("60/minute")
async def get_admin_analytics(request: Request, days: int = 30, user: dict = Depends(get_admin_user)):
    """Get comprehensive admin dashboard analytics"""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    start_iso = start_date.isoformat()
    
    # User stats
    total_users = await db.users.count_documents({})
    new_users = await db.users.count_documents({"createdAt": {"$gte": start_iso}})
    active_users = await db.users.count_documents({"lastLogin": {"$gte": start_iso}})
    
    # Generation stats
    total_generations = await db.generations.count_documents({})
    reel_generations = await db.generations.count_documents({"type": "REEL"})
    story_generations = await db.generations.count_documents({"type": "STORY"})
    recent_generations = await db.generations.count_documents({"createdAt": {"$gte": start_iso}})
    
    # GenStudio stats
    genstudio_jobs = await db.genstudio_jobs.count_documents({})
    genstudio_recent = await db.genstudio_jobs.count_documents({"createdAt": {"$gte": start_iso}})
    
    # Revenue stats  
    pipeline = [
        {"$match": {"status": "PAID", "createdAt": {"$gte": start_iso}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
    ]
    revenue_result = await db.orders.aggregate(pipeline).to_list(length=1)
    revenue = revenue_result[0] if revenue_result else {"total": 0, "count": 0}
    
    # Credit usage
    credit_pipeline = [
        {"$match": {"type": "USAGE", "createdAt": {"$gte": start_iso}}},
        {"$group": {"_id": None, "total": {"$sum": {"$abs": "$amount"}}}}
    ]
    credit_result = await db.credit_ledger.aggregate(credit_pipeline).to_list(length=1)
    credits_used = credit_result[0].get("total", 0) if credit_result else 0
    
    # Recent activity
    recent_users_list = await db.users.find(
        {},
        {"_id": 0, "password": 0}
    ).sort("createdAt", -1).limit(10).to_list(length=10)
    
    recent_gens = await db.generations.find(
        {},
        {"_id": 0}
    ).sort("createdAt", -1).limit(10).to_list(length=10)
    
    # Exception summary
    total_exceptions = await db.exception_logs.count_documents({})
    unresolved_exceptions = await db.exception_logs.count_documents({"resolved": False})
    critical_exceptions = await db.exception_logs.count_documents({"severity": "CRITICAL", "resolved": False})
    
    # Payment summary
    successful_payments = await db.payment_logs.count_documents({"status": "SUCCESS"})
    failed_payments = await db.payment_logs.count_documents({"status": "FAILED"})
    refunded_payments = await db.payment_logs.count_documents({"status": "REFUNDED"})
    
    # Calculate satisfaction from feedback
    feedback_count = await db.feedback.count_documents({})
    feedback_with_rating = await db.feedback.find(
        {"rating": {"$exists": True}}, 
        {"_id": 0, "rating": 1, "message": 1, "createdAt": 1}
    ).limit(100).to_list(100)
    avg_rating = sum([f.get("rating", 0) for f in feedback_with_rating]) / len(feedback_with_rating) if feedback_with_rating else 0
    satisfaction_percentage = int((avg_rating / 5) * 100) if avg_rating > 0 else 0
    
    # Calculate rating distribution
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for f in feedback_with_rating:
        rating = f.get("rating", 0)
        if 1 <= rating <= 5:
            rating_distribution[rating] += 1
    
    # Get recent reviews (feedback with comments)
    recent_reviews = await db.feedback.find(
        {"rating": {"$exists": True}},
        {"_id": 0, "rating": 1, "message": 1, "createdAt": 1}
    ).sort("createdAt", -1).limit(10).to_list(length=10)
    
    # Format reviews for frontend
    formatted_reviews = [
        {"rating": r.get("rating", 0), "comment": r.get("message", ""), "createdAt": r.get("createdAt", "")}
        for r in recent_reviews
    ]
    
    # Calculate NPS score (promoters - detractors)
    promoters = rating_distribution.get(5, 0) + rating_distribution.get(4, 0)
    detractors = rating_distribution.get(1, 0) + rating_distribution.get(2, 0)
    total_responses = len(feedback_with_rating) or 1
    nps_score = int(((promoters - detractors) / total_responses) * 100)
    
    # Generate daily trend data for visitors
    daily_trend = []
    for i in range(7):
        day = end_date - timedelta(days=6-i)
        day_start = day.replace(hour=0, minute=0, second=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        day_visitors = await db.users.count_documents({
            "lastLogin": {"$gte": day_start.isoformat(), "$lte": day_end.isoformat()}
        })
        daily_trend.append({
            "date": day.strftime("%m/%d"),
            "visitors": day_visitors or (total_users // 7)  # Fallback to average
        })
    
    # Recent payments
    recent_payments = await db.orders.find(
        {},
        {"_id": 0}
    ).sort("createdAt", -1).limit(5).to_list(length=5)
    
    # =========================================================================
    # FEATURE USAGE ANALYTICS (for FeaturesTab)
    # =========================================================================
    # Get feature usage from generations collection
    feature_pipeline = [
        {"$match": {"createdAt": {"$gte": start_iso}}},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    feature_counts = await db.generations.aggregate(feature_pipeline).to_list(20)
    
    # Also get GenStudio job types
    genstudio_feature_pipeline = [
        {"$match": {"createdAt": {"$gte": start_iso}}},
        {"$group": {"_id": "$jobType", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    genstudio_counts = await db.genstudio_jobs.aggregate(genstudio_feature_pipeline).to_list(20)
    
    # Combine all feature usage
    all_features = []
    for f in feature_counts:
        if f.get("_id"):
            all_features.append({"feature": f["_id"], "count": f["count"]})
    for f in genstudio_counts:
        if f.get("_id"):
            all_features.append({"feature": f["_id"], "count": f["count"]})
    
    # Sort by count
    all_features.sort(key=lambda x: x["count"], reverse=True)
    
    # Calculate percentages
    total_feature_count = sum(f["count"] for f in all_features) or 1
    feature_percentages = [
        {"feature": f["feature"], "percentage": round((f["count"] / total_feature_count) * 100, 1)}
        for f in all_features
    ]
    
    # Get unique users per feature
    unique_users_pipeline = [
        {"$match": {"createdAt": {"$gte": start_iso}}},
        {"$group": {"_id": "$type", "uniqueUsers": {"$addToSet": "$userId"}}},
        {"$project": {"feature": "$_id", "uniqueUsers": {"$size": "$uniqueUsers"}}}
    ]
    unique_users_by_feature = await db.generations.aggregate(unique_users_pipeline).to_list(20)
    
    # =========================================================================
    # PAYMENT ANALYTICS (for PaymentsTab)
    # =========================================================================
    # Transaction summary
    total_transactions = await db.orders.count_documents({"createdAt": {"$gte": start_iso}})
    successful_transactions = await db.orders.count_documents({"status": "PAID", "createdAt": {"$gte": start_iso}})
    failed_transactions = await db.orders.count_documents({"status": {"$in": ["FAILED", "CANCELLED"]}, "createdAt": {"$gte": start_iso}})
    pending_transactions = await db.orders.count_documents({"status": "PENDING", "createdAt": {"$gte": start_iso}})
    
    success_rate = round((successful_transactions / total_transactions * 100), 1) if total_transactions > 0 else 0
    
    # Plan breakdown
    plan_pipeline = [
        {"$match": {"status": "PAID", "createdAt": {"$gte": start_iso}}},
        {"$group": {
            "_id": "$product",
            "count": {"$sum": 1},
            "revenue": {"$sum": "$amount"}
        }},
        {"$sort": {"revenue": -1}}
    ]
    plan_breakdown = await db.orders.aggregate(plan_pipeline).to_list(10)
    formatted_plan_breakdown = [
        {"productName": p["_id"] or "Unknown", "count": p["count"], "revenue": p["revenue"]}
        for p in plan_breakdown if p.get("_id")
    ]
    
    # Failure reasons
    failure_pipeline = [
        {"$match": {"status": {"$in": ["FAILED", "CANCELLED"]}, "createdAt": {"$gte": start_iso}}},
        {"$group": {"_id": "$failureReason", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    failure_reasons = await db.orders.aggregate(failure_pipeline).to_list(10)
    formatted_failures = [
        {"reason": f["_id"] or "Unknown", "count": f["count"]}
        for f in failure_reasons
    ]
    
    # Daily revenue trend
    daily_revenue_trend = []
    for i in range(10):
        day = end_date - timedelta(days=9-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        day_pipeline = [
            {"$match": {"status": "PAID", "createdAt": {"$gte": day_start.isoformat(), "$lte": day_end.isoformat()}}},
            {"$group": {"_id": None, "revenue": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        day_result = await db.orders.aggregate(day_pipeline).to_list(1)
        daily_revenue_trend.append({
            "date": day.strftime("%m/%d"),
            "revenue": day_result[0]["revenue"] if day_result else 0,
            "count": day_result[0]["count"] if day_result else 0
        })
    
    return {
        "success": True,
        "data": {
            "overview": {
                "totalUsers": total_users,
                "newUsers": new_users,
                "activeUsers": active_users,
                "activeSessions": active_users,
                "totalGenerations": total_generations,
                "totalRevenue": revenue.get("total", 0),
                "periodRevenue": revenue.get("total", 0)
            },
            "users": {
                "total": total_users,
                "new": new_users,
                "active": active_users,
                "recentUsers": recent_users_list
            },
            "generations": {
                "total": total_generations,
                "reels": reel_generations,
                "stories": story_generations,
                "reelGenerations": reel_generations,
                "storyGenerations": story_generations,
                "recent": recent_generations,
                "genstudioTotal": genstudio_jobs,
                "genstudioRecent": genstudio_recent,
                "recentGenerations": recent_gens,
                "successRate": 100,
                "creditsUsed": credits_used
            },
            "revenue": {
                "total": revenue.get("total", 0),
                "orders": revenue.get("count", 0),
                "currency": "INR"
            },
            "credits": {
                "used": credits_used
            },
            "exceptions": {
                "total": total_exceptions,
                "unresolved": unresolved_exceptions,
                "critical": critical_exceptions
            },
            "payments": {
                "successful": successful_payments,
                "failed": failed_payments,
                "refunded": refunded_payments,
                "totalTransactions": total_transactions,
                "successfulTransactions": successful_transactions,
                "failedTransactions": failed_transactions,
                "pendingTransactions": pending_transactions,
                "successRate": success_rate,
                "planBreakdown": formatted_plan_breakdown,
                "failureReasons": formatted_failures,
                "dailyRevenueTrend": daily_revenue_trend
            },
            "visitors": {
                "uniqueVisitors": total_users,
                "totalPageViews": total_generations + total_users * 3,
                "today": active_users,
                "dailyTrend": daily_trend
            },
            "satisfaction": {
                "satisfactionPercentage": satisfaction_percentage,
                "averageRating": round(avg_rating, 1),
                "totalFeedback": feedback_count,
                "totalReviews": len(feedback_with_rating),
                "npsScore": nps_score,
                "ratingDistribution": rating_distribution,
                "recentReviews": formatted_reviews
            },
            "featureUsage": {
                "topFeatures": all_features[:10],
                "featurePercentages": feature_percentages[:10],
                "uniqueUsersPerFeature": unique_users_by_feature
            },
            "recentActivity": {
                "recentUsers": recent_users_list[:5],
                "recentPayments": recent_payments
            },
            "period": {
                "days": days,
                "start": start_iso,
                "end": end_date.isoformat()
            }
        }
    }


# =============================================================================
# PAYMENT MONITORING
# =============================================================================
@router.get("/payments/successful")
async def get_successful_payments(
    page: int = 0,
    size: int = 50,
    days: int = 30,
    user: dict = Depends(get_admin_user)
):
    """Get all successful payment transactions"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    skip = page * size
    
    query = {"status": {"$in": ["SUCCESS", "PAID"]}}
    if days:
        query["created_at"] = {"$gte": start_date}
    
    payments = await db.payment_logs.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(size).to_list(length=size)
    
    # Also get from orders collection for legacy data
    orders = await db.orders.find(
        {"status": "PAID", "createdAt": {"$gte": start_date}},
        {"_id": 0}
    ).sort("createdAt", -1).limit(size).to_list(length=size)
    
    total = await db.payment_logs.count_documents(query)
    
    # Calculate totals
    pipeline = [
        {"$match": query},
        {"$group": {"_id": None, "total_amount": {"$sum": "$amount"}, "total_credits": {"$sum": "$credits"}}}
    ]
    totals = await db.payment_logs.aggregate(pipeline).to_list(length=1)
    
    return {
        "payments": payments,
        "legacyOrders": orders,
        "total": total,
        "page": page,
        "size": size,
        "summary": totals[0] if totals else {"total_amount": 0, "total_credits": 0}
    }


@router.get("/payments/failed")
async def get_failed_payments(
    page: int = 0,
    size: int = 50,
    days: int = 30,
    user: dict = Depends(get_admin_user)
):
    """Get all failed payment transactions with failure reasons"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    skip = page * size
    
    query = {"status": "FAILED"}
    if days:
        query["created_at"] = {"$gte": start_date}
    
    payments = await db.payment_logs.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.payment_logs.count_documents(query)
    
    # Group by failure reason
    reason_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$failure_reason", "count": {"$sum": 1}}}
    ]
    reasons = await db.payment_logs.aggregate(reason_pipeline).to_list(length=100)
    
    return {
        "payments": payments,
        "total": total,
        "page": page,
        "size": size,
        "failureReasons": {r["_id"] or "Unknown": r["count"] for r in reasons}
    }


@router.get("/payments/refunded")
async def get_refunded_payments(
    page: int = 0,
    size: int = 50,
    days: int = 30,
    user: dict = Depends(get_admin_user)
):
    """Get all refunded payment transactions"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    skip = page * size
    
    query = {"status": "REFUNDED"}
    if days:
        query["created_at"] = {"$gte": start_date}
    
    payments = await db.payment_logs.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(size).to_list(length=size)
    
    # Also check orders
    orders = await db.orders.find(
        {"status": "REFUNDED"},
        {"_id": 0}
    ).sort("refunded_at", -1).limit(size).to_list(length=size)
    
    total = await db.payment_logs.count_documents(query)
    
    return {
        "payments": payments,
        "refundedOrders": orders,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/payments/by-functionality")
async def get_payments_by_functionality(
    days: int = 30,
    user: dict = Depends(get_admin_user)
):
    """Get payment breakdown by functionality/product"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    pipeline = [
        {"$match": {"status": {"$in": ["SUCCESS", "PAID"]}, "created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$product_id",
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$amount"},
            "total_credits": {"$sum": "$credits"}
        }},
        {"$sort": {"total_amount": -1}}
    ]
    
    breakdown = await db.payment_logs.aggregate(pipeline).to_list(length=100)
    
    return {
        "breakdown": [
            {
                "product": b["_id"] or "Unknown",
                "transactions": b["count"],
                "totalAmount": b["total_amount"],
                "totalCredits": b["total_credits"]
            }
            for b in breakdown
        ],
        "period": f"Last {days} days"
    }


# =============================================================================
# EXCEPTION MONITORING
# =============================================================================
@router.get("/exceptions/all")
async def get_all_exceptions(
    page: int = 0,
    size: int = 50,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    user: dict = Depends(get_admin_user)
):
    """Get all logged exceptions from user actions and system"""
    skip = page * size
    
    query = {}
    if severity:
        query["severity"] = severity.upper()
    if resolved is not None:
        query["resolved"] = resolved
    
    exceptions = await db.exception_logs.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.exception_logs.count_documents(query)
    
    return {
        "exceptions": exceptions,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/exceptions/by-functionality")
async def get_exceptions_by_functionality(
    days: int = 30,
    user: dict = Depends(get_admin_user)
):
    """Get exception breakdown by functionality"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$functionality",
            "count": {"$sum": 1},
            "unresolved": {"$sum": {"$cond": [{"$eq": ["$resolved", False]}, 1, 0]}},
            "critical": {"$sum": {"$cond": [{"$eq": ["$severity", "CRITICAL"]}, 1, 0]}}
        }},
        {"$sort": {"count": -1}}
    ]
    
    breakdown = await db.exception_logs.aggregate(pipeline).to_list(length=100)
    
    return {
        "breakdown": [
            {
                "functionality": b["_id"] or "Unknown",
                "totalCount": b["count"],
                "unresolvedCount": b["unresolved"],
                "criticalCount": b["critical"]
            }
            for b in breakdown
        ],
        "period": f"Last {days} days"
    }


@router.put("/exceptions/{exception_id}/resolve")
async def resolve_exception(
    exception_id: str,
    user: dict = Depends(get_admin_user)
):
    """Mark an exception as resolved"""
    result = await db.exception_logs.update_one(
        {"id": exception_id},
        {
            "$set": {
                "resolved": True,
                "resolved_by": user["id"],
                "resolved_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    return {"message": "Exception marked as resolved"}


@router.delete("/exceptions/{exception_id}")
async def delete_exception(exception_id: str, user: dict = Depends(get_admin_user)):
    """Delete an exception log entry"""
    result = await db.exception_logs.delete_one({"id": exception_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Exception not found")
    return {"message": "Exception deleted"}


# =============================================================================
# FEEDBACK MANAGEMENT
# =============================================================================
@router.get("/feedback/all")
async def get_all_feedback(user: dict = Depends(get_admin_user)):
    """Get all user feedback"""
    feedback = await db.feedback.find(
        {},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(length=1000)
    
    # Calculate stats
    total = len(feedback)
    ratings = [f.get("rating", 0) for f in feedback if f.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Category breakdown
    categories = {}
    for f in feedback:
        cat = f.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "feedback": feedback,
        "stats": {
            "total": total,
            "averageRating": round(avg_rating, 2),
            "byCategory": categories
        }
    }


@router.delete("/feedback/{feedback_id}")
async def delete_feedback(feedback_id: str, user: dict = Depends(get_admin_user)):
    """Delete a feedback entry"""
    result = await db.feedback.delete_one({"id": feedback_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"message": "Feedback deleted"}


# =============================================================================
# ALERT MANAGEMENT
# =============================================================================
@router.get("/alerts/logs")
async def get_alert_logs(page: int = 0, size: int = 50, user: dict = Depends(get_admin_user)):
    """Get admin alert logs"""
    skip = page * size
    
    alerts = await db.admin_alerts.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.admin_alerts.count_documents({})
    
    return {
        "alerts": alerts,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/alerts/status")
async def get_alert_status():
    """Get alert system status"""
    return {
        "emailEnabled": SENDGRID_AVAILABLE and bool(SENDGRID_API_KEY),
        "adminEmail": ADMIN_ALERT_EMAIL,
        "senderEmail": SENDER_EMAIL
    }


# =============================================================================
# USER MANAGEMENT
# =============================================================================
@router.get("/users")
@router.get("/users/list")
async def get_all_users(
    page: int = 0,
    size: int = 50,
    role: Optional[str] = None,
    user: dict = Depends(get_admin_user)
):
    """Get list of all users"""
    skip = page * size
    query = {}
    if role:
        query["role"] = role.upper()
    
    users = await db.users.find(
        query,
        {"_id": 0, "password": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.users.count_documents(query)
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "size": size
    }


@router.put("/users/{user_id}/credits")
async def adjust_user_credits(
    user_id: str,
    amount: int,
    reason: str,
    user: dict = Depends(get_admin_user)
):
    """Adjust a user's credits (add or subtract)"""
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_balance = target_user.get("credits", 0) + amount
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Cannot set negative credits")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"credits": new_balance}}
    )
    
    # Log the adjustment
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "amount": amount,
        "type": "ADMIN_ADJUSTMENT",
        "description": f"Admin adjustment: {reason}",
        "adjustedBy": user["id"],
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": f"Credits adjusted by {amount}",
        "newBalance": new_balance
    }


# =============================================================================
# ANALYTICS TRACKING
# =============================================================================
@router.get("/analytics/track/{event}")
async def track_event(event: str):
    """Track an analytics event"""
    await db.analytics_events.insert_one({
        "id": str(uuid.uuid4()),
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"status": "tracked", "event": event}


@router.get("/story-templates/stats")
async def get_story_template_stats(user: dict = Depends(get_current_user)):
    """Get story template usage statistics"""
    templates = await db.story_templates.find(
        {},
        {"_id": 0, "id": 1, "title": 1, "genre": 1, "ageGroup": 1, "usageCount": 1}
    ).sort("usageCount", -1).to_list(length=100)
    
    total_templates = len(templates)
    total_usage = sum(t.get("usageCount", 0) for t in templates)
    
    genre_stats = {}
    for t in templates:
        genre = t.get("genre", "Unknown")
        if genre not in genre_stats:
            genre_stats[genre] = {"count": 0, "usage": 0}
        genre_stats[genre]["count"] += 1
        genre_stats[genre]["usage"] += t.get("usageCount", 0)
    
    return {
        "templates": templates[:20],
        "stats": {
            "totalTemplates": total_templates,
            "totalUsage": total_usage,
            "byGenre": genre_stats
        }
    }


@router.get("/feature-requests")
async def feature_requests_analytics(user: dict = Depends(get_admin_user)):
    """Get feature request analytics"""
    feature_requests = await db.feedback.find(
        {"category": "feature_request"},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(length=100)
    
    return {
        "requests": feature_requests,
        "total": len(feature_requests)
    }
