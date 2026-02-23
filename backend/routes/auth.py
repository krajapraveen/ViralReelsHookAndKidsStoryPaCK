"""
Authentication Routes - Register, Login, Profile Management
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from datetime import datetime, timezone, timedelta
import uuid
import os
import httpx
import sys
import secrets
import re

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, hash_password, verify_password, create_token,
    get_current_user, log_exception
)
from models.schemas import UserCreate, UserLogin, GoogleCallback, ProfileUpdate, PasswordChange
from security import limiter, validate_password_strength
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


# Helper Functions
def validate_name(name: str) -> tuple:
    """Validate full name"""
    if not name or not name.strip():
        return False, "Name is required"
    
    name = name.strip()
    if len(name) < 2:
        return False, "Name must be at least 2 characters"
    if len(name) > 50:
        return False, "Name must be less than 50 characters"
    
    # Allow letters, spaces, hyphens, apostrophes (common in names)
    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        return False, "Name can only contain letters, spaces, hyphens, and apostrophes"
    
    return True, name


def validate_email_format(email: str) -> tuple:
    """Validate email format"""
    if not email or not email.strip():
        return False, "Email is required"
    
    email = email.strip().lower()
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, email


def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)


async def send_verification_email(email: str, token: str, name: str):
    """Send verification email via SendGrid"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email
        
        api_key = os.environ.get("SENDGRID_API_KEY")
        if not api_key:
            logger.warning("SendGrid API key not configured")
            return False
        
        frontend_url = os.environ.get("FRONTEND_URL")
        if not frontend_url:
            logger.error("FRONTEND_URL not configured")
            return False
        verify_url = f"{frontend_url}/verify-email?token={token}"
        
        # Use verified sender identity
        from_email = Email(
            email=os.environ.get("SENDGRID_FROM_EMAIL", "krajapraveen@visionary-suite.com"),
            name="CreatorStudio AI"
        )
        
        message = Mail(
            from_email=from_email,
            to_emails=email,
            subject="Verify Your CreatorStudio AI Account",
            html_content=f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; padding: 40px; border-radius: 16px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #818cf8; margin: 0;">CreatorStudio AI</h1>
                </div>
                <div style="background: #1e293b; padding: 30px; border-radius: 12px;">
                    <h2 style="color: #f1f5f9; margin-top: 0;">Welcome, {name}!</h2>
                    <p style="color: #94a3b8; font-size: 16px; line-height: 1.6;">
                        Thank you for signing up for CreatorStudio AI. Please verify your email address to complete your registration and start creating amazing content.
                    </p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verify_url}" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">
                            Verify Email Address
                        </a>
                    </div>
                    <p style="color: #64748b; font-size: 14px;">
                        This link will expire in 24 hours. If you didn't create an account, you can safely ignore this email.
                    </p>
                </div>
                <p style="color: #475569; font-size: 12px; text-align: center; margin-top: 30px;">
                    © 2026 Visionary Suite. All rights reserved.
                </p>
            </div>
            """
        )
        
        sg = SendGridAPIClient(api_key)
        sg.send(message)
        logger.info(f"Verification email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return False


async def send_password_reset_email(email: str, token: str, name: str):
    """Send password reset email via SendGrid"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email
        
        api_key = os.environ.get("SENDGRID_API_KEY")
        if not api_key:
            logger.warning("SendGrid API key not configured")
            return False
        
        frontend_url = os.environ.get("FRONTEND_URL")
        if not frontend_url:
            logger.error("FRONTEND_URL not configured")
            return False
        reset_url = f"{frontend_url}/reset-password?token={token}"
        
        # Use verified sender identity
        from_email = Email(
            email=os.environ.get("SENDGRID_FROM_EMAIL", "krajapraveen@visionary-suite.com"),
            name="CreatorStudio AI"
        )
        
        message = Mail(
            from_email=from_email,
            to_emails=email,
            subject="Reset Your CreatorStudio AI Password",
            html_content=f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; padding: 40px; border-radius: 16px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #818cf8; margin: 0;">CreatorStudio AI</h1>
                </div>
                <div style="background: #1e293b; padding: 30px; border-radius: 12px;">
                    <h2 style="color: #f1f5f9; margin-top: 0;">Password Reset Request</h2>
                    <p style="color: #94a3b8; font-size: 16px; line-height: 1.6;">
                        Hi {name}, we received a request to reset your password. Click the button below to create a new password.
                    </p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    <p style="color: #64748b; font-size: 14px;">
                        This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email.
                    </p>
                </div>
                <p style="color: #475569; font-size: 12px; text-align: center; margin-top: 30px;">
                    © 2026 Visionary Suite. All rights reserved.
                </p>
            </div>
            """
        )
        
        sg = SendGridAPIClient(api_key)
        sg.send(message)
        logger.info(f"Password reset email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return False


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, data: UserCreate, background_tasks: BackgroundTasks):
    """Register a new user with validation and email verification"""
    try:
        # Validate name
        name_valid, name_result = validate_name(data.name)
        if not name_valid:
            raise HTTPException(status_code=400, detail=name_result)
        clean_name = name_result
        
        # Validate email
        email_valid, email_result = validate_email_format(data.email)
        if not email_valid:
            raise HTTPException(status_code=400, detail=email_result)
        clean_email = email_result
        
        # Validate password strength
        is_valid, error_message = validate_password_strength(data.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Check if user exists (case-insensitive)
        existing = await db.users.find_one({"email": clean_email}, {"_id": 0})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Generate verification token
        verification_token = generate_verification_token()
        token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        
        # Create user
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": clean_email,
            "name": clean_name,
            "password": hash_password(data.password),
            "role": "user",
            "credits": 100,
            "emailVerified": False,
            "verificationToken": verification_token,
            "verificationTokenExpiry": token_expiry.isoformat(),
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "lastLogin": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if first user - make admin
        user_count = await db.users.count_documents({})
        if user_count == 0:
            user["role"] = "ADMIN"
            user["credits"] = 10000
            user["emailVerified"] = True  # Admin auto-verified
        
        await db.users.insert_one(user)
        
        # Log initial credit grant
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "amount": user["credits"],
            "type": "SIGNUP_BONUS",
            "description": "Welcome bonus credits",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Send verification email in background
        background_tasks.add_task(send_verification_email, clean_email, verification_token, clean_name)
        
        token = create_token(user_id, user["role"])
        
        logger.info(f"New user registered: {clean_email}")
        
        return {
            "token": token,
            "user": {
                "id": user_id,
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "credits": user["credits"],
                "emailVerified": user["emailVerified"]
            },
            "message": "Registration successful! Please check your email to verify your account."
        }
    except HTTPException:
        raise
    except Exception as e:
        await log_exception(
            functionality="auth_register",
            error_type="REGISTRATION_ERROR",
            error_message=str(e),
            user_email=data.email,
            severity="ERROR"
        )
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, data: UserLogin):
    """Login with email and password"""
    from routes.login_activity import log_login_activity, is_ip_blocked, extract_client_ip
    
    try:
        # Check if IP is blocked
        client_ip, _ = extract_client_ip(request)
        if await is_ip_blocked(client_ip):
            await log_login_activity(
                request=request,
                user_id=None,
                identifier=data.email.lower(),
                status="FAILED",
                auth_method="email_password",
                failure_reason="IP address blocked"
            )
            raise HTTPException(status_code=403, detail="Access denied. Please contact support.")
        
        user = await db.users.find_one({"email": data.email.lower()}, {"_id": 0})
        
        if not user:
            # Log failed attempt - user not found
            await log_login_activity(
                request=request,
                user_id=None,
                identifier=data.email.lower(),
                status="FAILED",
                auth_method="email_password",
                failure_reason="User not found"
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not verify_password(data.password, user.get("password", "")):
            # Log failed attempt - wrong password
            await log_login_activity(
                request=request,
                user_id=user["id"],
                identifier=data.email.lower(),
                status="FAILED",
                auth_method="email_password",
                failure_reason="Invalid password"
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Update last login
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"lastLogin": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Log successful login
        await log_login_activity(
            request=request,
            user_id=user["id"],
            identifier=data.email.lower(),
            status="SUCCESS",
            auth_method="email_password"
        )
        
        token = create_token(user["id"], user.get("role", "user"))
        
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name", ""),
                "role": user.get("role", "user"),
                "credits": user.get("credits", 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await log_exception(
            functionality="auth_login",
            error_type="LOGIN_ERROR",
            error_message=str(e),
            user_email=data.email,
            severity="WARNING"
        )
        raise HTTPException(status_code=500, detail="Login failed")


@router.options("/google-callback")
async def google_callback_options():
    """Handle CORS preflight for Google callback"""
    return {"status": "ok"}


@router.post("/google-callback")
async def google_callback(request: Request, data: GoogleCallback):
    """Handle Google OAuth callback via Emergent Auth"""
    from routes.login_activity import log_login_activity
    
    try:
        logger.info(f"Google callback received with sessionId: {data.sessionId[:8]}...")
        
        # Verify session with Emergent Auth service - CORRECT ENDPOINT
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                    headers={"X-Session-ID": data.sessionId}
                )
        except httpx.TimeoutException as e:
            logger.error(f"Timeout connecting to Emergent Auth service: {e}")
            raise HTTPException(status_code=503, detail="Authentication service timeout")
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            logger.error(f"Connection error to Emergent Auth: {e}")
            raise HTTPException(status_code=503, detail="Cannot connect to authentication service")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error connecting to Emergent Auth: {type(e).__name__}: {e}")
            raise HTTPException(status_code=503, detail="Authentication service error")
        except Exception as e:
            logger.error(f"Unexpected error connecting to Emergent Auth: {type(e).__name__}: {e}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
        
        logger.info(f"Emergent Auth response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.warning(f"Invalid session response: {response.status_code} - {response.text}")
            raise HTTPException(status_code=400, detail="Invalid session or session expired")
        
        try:
            session_data = response.json()
            logger.info(f"Session data received: {list(session_data.keys())}")
        except Exception as e:
            logger.error(f"Failed to parse session response: {e}")
            raise HTTPException(status_code=500, detail="Invalid response from auth service")
        
        # Extract user info from session data
        email = session_data.get("email", "").lower()
        name = session_data.get("name", email.split("@")[0] if email else "User")
        picture = session_data.get("picture", "")
        session_token = session_data.get("session_token", "")
        
        if not email:
            logger.warning("No email in session data")
            raise HTTPException(status_code=400, detail="Email not provided")
        
        logger.info(f"Processing Google auth for: {email}")
        
        # Check if user exists
        existing = await db.users.find_one({"email": email}, {"_id": 0})
        
        if existing:
            # Update last login and picture
            await db.users.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "lastLogin": datetime.now(timezone.utc).isoformat(),
                    "picture": picture if picture else existing.get("picture", "")
                }}
            )
            token = create_token(existing["id"], existing.get("role", "user"))
            logger.info(f"Existing user logged in: {email}")
            return {
                "token": token,
                "user": {
                    "id": existing["id"],
                    "email": existing["email"],
                    "name": existing.get("name", name),
                    "role": existing.get("role", "user"),
                    "credits": existing.get("credits", 0),
                    "picture": picture if picture else existing.get("picture", "")
                }
            }
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "password": "",
                "role": "user",
                "credits": 100,
                "authProvider": "google",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "lastLogin": datetime.now(timezone.utc).isoformat()
            }
            
            await db.users.insert_one(user)
            
            # Log initial credit grant
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "amount": 100,
                "type": "SIGNUP_BONUS",
                "description": "Welcome bonus credits (Google Sign-In)",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
            
            token = create_token(user_id, "user")
            
            logger.info(f"New Google user registered: {email}")
            
            return {
                "token": token,
                "user": {
                    "id": user_id,
                    "email": email,
                    "name": name,
                    "role": "user",
                    "credits": 100,
                    "picture": picture
                }
            }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google auth error: {type(e).__name__}: {str(e)}")
        try:
            await log_exception(
                functionality="auth_google",
                error_type="GOOGLE_AUTH_ERROR",
                error_message=str(e),
                severity="ERROR"
            )
        except Exception as log_err:
            logger.error(f"Failed to log exception: {log_err}")
        raise HTTPException(status_code=500, detail=f"Google authentication failed: {str(e)}")


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": user["id"],
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "role": user.get("role", "user"),
        "credits": user.get("credits", 0),
        "createdAt": user.get("createdAt"),
        "subscription": user.get("subscription"),
        "plan": user.get("plan", "free"),
        "tourCompleted": user.get("tourCompleted", False)
    }


@router.put("/profile")
async def update_profile(data: ProfileUpdate, user: dict = Depends(get_current_user)):
    """Update user profile"""
    update_data = {}
    if data.name:
        update_data["name"] = data.name
    
    # Handle tour completion status
    if hasattr(data, 'tourCompleted') and data.tourCompleted is not None:
        update_data["tourCompleted"] = data.tourCompleted
    
    if update_data:
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
    
    return {"message": "Profile updated successfully"}


@router.put("/password")
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    """Change user password with advanced validation"""
    try:
        user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user_data.get("authProvider") == "google":
            raise HTTPException(status_code=400, detail="Cannot change password for Google sign-in accounts")
        
        # Verify current password
        if not user_data.get("password"):
            raise HTTPException(status_code=400, detail="No password set for this account")
        
        if not verify_password(data.currentPassword, user_data.get("password", "")):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Validate new password strength
        is_valid, error_message = validate_password_strength(data.newPassword)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Ensure new password is different from current
        if verify_password(data.newPassword, user_data.get("password", "")):
            raise HTTPException(status_code=400, detail="New password must be different from current password")
        
        # Update password
        await db.users.update_one(
            {"id": user["id"]},
            {
                "$set": {
                    "password": hash_password(data.newPassword),
                    "passwordChangedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Password changed for user {user['id']}")
        
        return {"success": True, "message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest):
    """Verify user email with token"""
    try:
        # Find user with this token
        user = await db.users.find_one({
            "verificationToken": data.token
        }, {"_id": 0})
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        # Check if token expired
        expiry = user.get("verificationTokenExpiry")
        if expiry:
            expiry_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expiry_dt:
                raise HTTPException(status_code=400, detail="Verification token has expired. Please request a new one.")
        
        # Check if already verified
        if user.get("emailVerified"):
            return {"success": True, "message": "Email already verified", "alreadyVerified": True}
        
        # Mark email as verified
        await db.users.update_one(
            {"id": user["id"]},
            {
                "$set": {
                    "emailVerified": True,
                    "emailVerifiedAt": datetime.now(timezone.utc).isoformat()
                },
                "$unset": {
                    "verificationToken": "",
                    "verificationTokenExpiry": ""
                }
            }
        )
        
        logger.info(f"Email verified for user {user['id']}")
        
        return {
            "success": True,
            "message": "Email verified successfully! You can now login.",
            "email": user["email"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(status_code=500, detail="Verification failed")


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(request: Request, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Resend email verification"""
    try:
        if user.get("emailVerified"):
            return {"success": True, "message": "Email already verified"}
        
        # Generate new token
        new_token = generate_verification_token()
        token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        
        await db.users.update_one(
            {"id": user["id"]},
            {
                "$set": {
                    "verificationToken": new_token,
                    "verificationTokenExpiry": token_expiry.isoformat()
                }
            }
        )
        
        # Send email
        background_tasks.add_task(
            send_verification_email, 
            user["email"], 
            new_token, 
            user.get("name", "User")
        )
        
        return {"success": True, "message": "Verification email sent"}
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Request password reset"""
    try:
        email = data.email.lower().strip()
        
        # Find user (don't reveal if user exists)
        user = await db.users.find_one({"email": email}, {"_id": 0})
        
        # Always return success to prevent email enumeration
        if not user:
            logger.info(f"Password reset requested for non-existent email: {email}")
            return {"success": True, "message": "If an account exists with this email, you will receive a password reset link."}
        
        # Check if Google user
        if user.get("authProvider") == "google":
            return {"success": True, "message": "This account uses Google Sign-In. Please use the Google login option."}
        
        # Generate reset token
        reset_token = generate_verification_token()
        token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        await db.users.update_one(
            {"id": user["id"]},
            {
                "$set": {
                    "passwordResetToken": reset_token,
                    "passwordResetExpiry": token_expiry.isoformat()
                }
            }
        )
        
        # Send reset email
        background_tasks.add_task(
            send_password_reset_email,
            email,
            reset_token,
            user.get("name", "User")
        )
        
        logger.info(f"Password reset requested for {email}")
        
        return {"success": True, "message": "If an account exists with this email, you will receive a password reset link."}
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        # Don't reveal error details
        return {"success": True, "message": "If an account exists with this email, you will receive a password reset link."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordRequest):
    """Reset password with token"""
    try:
        # Find user with this token
        user = await db.users.find_one({
            "passwordResetToken": data.token
        }, {"_id": 0})
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        # Check if token expired
        expiry = user.get("passwordResetExpiry")
        if expiry:
            expiry_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expiry_dt:
                raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")
        
        # Validate new password
        is_valid, error_message = validate_password_strength(data.newPassword)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Update password and clear token
        await db.users.update_one(
            {"id": user["id"]},
            {
                "$set": {
                    "password": hash_password(data.newPassword),
                    "passwordChangedAt": datetime.now(timezone.utc).isoformat()
                },
                "$unset": {
                    "passwordResetToken": "",
                    "passwordResetExpiry": ""
                }
            }
        )
        
        logger.info(f"Password reset completed for user {user['id']}")
        
        return {"success": True, "message": "Password reset successfully. You can now login with your new password."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail="Password reset failed")


@router.get("/export-data")
async def export_user_data(user: dict = Depends(get_current_user)):
    """Export all user data for GDPR compliance"""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    generations = await db.generations.find({"userId": user["id"]}, {"_id": 0}).to_list(length=1000)
    ledger = await db.credit_ledger.find({"userId": user["id"]}, {"_id": 0}).to_list(length=1000)
    orders = await db.orders.find({"userId": user["id"]}, {"_id": 0}).to_list(length=1000)
    genstudio = await db.genstudio_jobs.find({"userId": user["id"]}, {"_id": 0}).to_list(length=1000)
    
    return {
        "user": user_data,
        "generations": generations,
        "genstudioJobs": genstudio,
        "creditHistory": ledger,
        "paymentHistory": orders,
        "exportedAt": datetime.now(timezone.utc).isoformat()
    }


@router.delete("/account")
async def delete_account(user: dict = Depends(get_current_user)):
    """Delete user account and all associated data"""
    user_id = user["id"]
    
    # Delete all user data
    await db.users.delete_one({"id": user_id})
    await db.generations.delete_many({"userId": user_id})
    await db.genstudio_jobs.delete_many({"userId": user_id})
    await db.credit_ledger.delete_many({"userId": user_id})
    await db.orders.delete_many({"userId": user_id})
    await db.style_profiles.delete_many({"userId": user_id})
    await db.feedback.delete_many({"userId": user_id})
    
    logger.info(f"User account deleted: {user_id}")
    
    return {"message": "Account deleted successfully"}
