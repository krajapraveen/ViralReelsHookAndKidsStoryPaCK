"""
Authentication Routes - Register, Login, Profile Management
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from datetime import datetime, timezone
import uuid
import os
import httpx
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, hash_password, verify_password, create_token,
    get_current_user, log_exception
)
from models.schemas import UserCreate, UserLogin, GoogleCallback, ProfileUpdate, PasswordChange
from security import limiter, validate_password_strength

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, data: UserCreate, background_tasks: BackgroundTasks):
    """Register a new user with validation"""
    try:
        # Validate password strength
        is_valid, error_message = validate_password_strength(data.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Check if user exists
        existing = await db.users.find_one({"email": data.email.lower()}, {"_id": 0})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": data.email.lower(),
            "name": data.name,
            "password": hash_password(data.password),
            "role": "user",
            "credits": 100,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "lastLogin": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if first user - make admin
        user_count = await db.users.count_documents({})
        if user_count == 0:
            user["role"] = "ADMIN"
            user["credits"] = 10000
        
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
        
        token = create_token(user_id, user["role"])
        
        logger.info(f"New user registered: {data.email}")
        
        return {
            "token": token,
            "user": {
                "id": user_id,
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
                "credits": user["credits"]
            }
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
    try:
        user = await db.users.find_one({"email": data.email.lower()}, {"_id": 0})
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not verify_password(data.password, user.get("password", "")):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Update last login
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"lastLogin": datetime.now(timezone.utc).isoformat()}}
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
async def google_callback(data: GoogleCallback):
    """Handle Google OAuth callback via Emergent Auth"""
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
        "plan": user.get("plan", "free")
    }


@router.put("/profile")
async def update_profile(data: ProfileUpdate, user: dict = Depends(get_current_user)):
    """Update user profile"""
    update_data = {}
    if data.name:
        update_data["name"] = data.name
    
    if update_data:
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
    
    return {"message": "Profile updated successfully"}


@router.put("/password")
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    """Change user password"""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    if user_data.get("authProvider") == "google":
        raise HTTPException(status_code=400, detail="Cannot change password for Google sign-in accounts")
    
    if not verify_password(data.currentPassword, user_data.get("password", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Validate new password
    password_check = validate_password_strength(data.newPassword)
    if not password_check["valid"]:
        raise HTTPException(status_code=400, detail=password_check["message"])
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password": hash_password(data.newPassword)}}
    )
    
    return {"message": "Password changed successfully"}


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
