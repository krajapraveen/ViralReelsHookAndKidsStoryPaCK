"""Authentication routes"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone
import uuid
import os
import httpx
from ..utils.auth import hash_password, verify_password, create_token, get_current_user
from ..utils.database import db
from ..models.schemas import UserCreate, UserLogin, GoogleCallback, ProfileUpdate, PasswordChange

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')


@router.post("/register")
async def register(data: UserCreate, background_tasks: BackgroundTasks):
    """Register a new user"""
    # Check if user exists
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = {
        "id": str(uuid.uuid4()),
        "email": data.email.lower(),
        "name": data.name,
        "password": hash_password(data.password),
        "role": "user",
        "credits": 100,  # Starting credits for new users
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "lastLogin": datetime.now(timezone.utc).isoformat()
    }
    
    # Check if first user - make admin
    user_count = await db.users.count_documents({})
    if user_count == 0:
        user["role"] = "admin"
        user["credits"] = 1000
    
    await db.users.insert_one(user)
    
    # Log initial credit grant
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "amount": user["credits"],
        "type": "SIGNUP_BONUS",
        "description": "Welcome bonus credits",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    token = create_token(user["id"], user["role"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "credits": user["credits"]
        }
    }


@router.post("/login")
async def login(data: UserLogin):
    """Login with email and password"""
    user = await db.users.find_one({"email": data.email.lower()})
    
    if not user or not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"lastLogin": datetime.now(timezone.utc).isoformat()}}
    )
    
    token = create_token(user["id"], user["role"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "credits": user["credits"]
        }
    }


@router.post("/google-callback")
async def google_callback(data: GoogleCallback):
    """Handle Google OAuth callback"""
    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": data.code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": os.environ.get('GOOGLE_REDIRECT_URI', ''),
                    "grant_type": "authorization_code"
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            # Get user info
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
            user_info = user_response.json()
            email = user_info.get("email", "").lower()
            name = user_info.get("name", "")
            
            # Check if user exists
            existing = await db.users.find_one({"email": email})
            
            if existing:
                # Update last login
                await db.users.update_one(
                    {"id": existing["id"]},
                    {"$set": {"lastLogin": datetime.now(timezone.utc).isoformat()}}
                )
                token = create_token(existing["id"], existing["role"])
                return {
                    "token": token,
                    "user": {
                        "id": existing["id"],
                        "email": existing["email"],
                        "name": existing["name"],
                        "role": existing["role"],
                        "credits": existing["credits"]
                    }
                }
            else:
                # Create new user
                user = {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "name": name,
                    "password": "",  # No password for OAuth users
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
                    "userId": user["id"],
                    "amount": 100,
                    "type": "SIGNUP_BONUS",
                    "description": "Welcome bonus credits (Google Sign-In)",
                    "createdAt": datetime.now(timezone.utc).isoformat()
                })
                
                token = create_token(user["id"], user["role"])
                return {
                    "token": token,
                    "user": {
                        "id": user["id"],
                        "email": user["email"],
                        "name": user["name"],
                        "role": user["role"],
                        "credits": user["credits"]
                    }
                }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    return {
        "id": user_data["id"],
        "email": user_data["email"],
        "name": user_data["name"],
        "role": user_data["role"],
        "credits": user_data["credits"]
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
    user_data = await db.users.find_one({"id": user["id"]})
    
    if not verify_password(data.currentPassword, user_data.get("password", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
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
    
    return {
        "user": user_data,
        "generations": generations,
        "creditHistory": ledger,
        "paymentHistory": orders
    }


@router.delete("/account")
async def delete_account(user: dict = Depends(get_current_user)):
    """Delete user account and all associated data"""
    user_id = user["id"]
    
    # Delete all user data
    await db.users.delete_one({"id": user_id})
    await db.generations.delete_many({"userId": user_id})
    await db.credit_ledger.delete_many({"userId": user_id})
    await db.orders.delete_many({"userId": user_id})
    
    return {"message": "Account deleted successfully"}
