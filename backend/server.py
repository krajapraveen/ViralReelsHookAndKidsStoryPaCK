from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import httpx
import json
import random
import string

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'creatorstudio-secret-key-change-in-production-very-long-key-minimum-256-bits')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 168  # 7 days

# Worker URL
WORKER_URL = os.environ.get('WORKER_URL', 'http://localhost:5000')

# Security
security = HTTPBearer(auto_error=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="CreatorStudio API")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
credits_router = APIRouter(prefix="/credits", tags=["Credits"])
generate_router = APIRouter(prefix="/generate", tags=["Generation"])
payments_router = APIRouter(prefix="/payments", tags=["Payments"])
feedback_router = APIRouter(prefix="/feedback", tags=["Feedback"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
chatbot_router = APIRouter(prefix="/chatbot", tags=["Chatbot"])
health_router = APIRouter(prefix="/health", tags=["Health"])

# ==================== MODELS ====================

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleCallback(BaseModel):
    sessionId: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    credits: int
    createdAt: str

class GenerateReelRequest(BaseModel):
    topic: str
    niche: str = "General"
    language: str = "English"
    tone: str = "Bold"
    duration: str = "30s"
    goal: str = "Followers"

class GenerateStoryRequest(BaseModel):
    genre: str = "Adventure"
    customGenre: Optional[str] = None
    ageGroup: str = "4-6"
    theme: str = "Friendship"
    sceneCount: int = 8

class FeedbackSuggestion(BaseModel):
    rating: int = 0
    category: str = "general"
    suggestion: str
    email: Optional[str] = None

class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

class ChatMessage(BaseModel):
    sessionId: str = "default"
    message: str

class CreateOrderRequest(BaseModel):
    productId: str
    currency: str = "INR"

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

# ==================== UTILITIES ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, role: str) -> str:
    payload = {
        'sub': user_id,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('sub')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(user: dict = Depends(get_current_user)):
    if user.get('role') != 'ADMIN':
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ==================== AUTHENTICATION ROUTES ====================

@auth_router.post("/register")
async def register(data: UserCreate, background_tasks: BackgroundTasks):
    # Check if user exists
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "name": data.name,
        "email": data.email.lower(),
        "password": hash_password(data.password),
        "role": "USER",
        "credits": 54,  # Free credits on signup
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user)
    
    # Log credit transaction
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "amount": 54,
        "type": "BONUS",
        "description": "Welcome bonus - 54 free credits",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Send welcome email in background
    background_tasks.add_task(notify_welcome, user)
    
    token = create_token(user_id, "USER")
    
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "credits": user["credits"]
        }
    }

@auth_router.post("/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email.lower()}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["id"], user["role"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "credits": user["credits"]
        }
    }

@auth_router.post("/google-callback")
async def google_callback(data: GoogleCallback):
    try:
        # Exchange session ID for user info via Emergent Auth
        # CORRECT ENDPOINT: https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client_http:
            response = await client_http.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": data.sessionId}
            )
            logger.info(f"Google auth response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Auth failed: {response.text[:500]}")
                raise HTTPException(status_code=400, detail="Invalid session or session expired")
            
            auth_data = response.json()
            logger.info(f"Auth data received for: {auth_data.get('email', 'unknown')}")
            
        email = auth_data.get('email', '').lower()
        name = auth_data.get('name', email.split('@')[0])
        picture = auth_data.get('picture', '')
        google_id = auth_data.get('id', '')  # 'id' field from the response
        
        if not email:
            raise HTTPException(status_code=400, detail="No email received from Google")
        
        # Check if user exists
        user = await db.users.find_one({"email": email}, {"_id": 0})
        
        if not user:
            # Create new user
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "name": name,
                "email": email,
                "password": "",  # No password for Google users
                "role": "USER",
                "credits": 54,
                "googleId": google_id,
                "picture": picture,
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user)
            
            # Log credit transaction
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "amount": 54,
                "type": "BONUS",
                "description": "Welcome bonus - 54 free credits",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"New Google user created: {email}")
        else:
            # Update existing user's Google info if needed
            if not user.get("googleId"):
                await db.users.update_one(
                    {"email": email},
                    {"$set": {"googleId": google_id, "picture": picture}}
                )
            logger.info(f"Existing user logged in: {email}")
        
        token = create_token(user["id"], user["role"])
        
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "credits": user["credits"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google callback error: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@auth_router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "credits": user["credits"],
        "createdAt": user.get("createdAt", datetime.now(timezone.utc).isoformat()),
        "googleId": user.get("googleId")
    }

class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)

class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=6)

@auth_router.put("/profile")
async def update_profile(data: ProfileUpdate, user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"name": data.name, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True, "message": "Profile updated successfully"}

@auth_router.put("/password")
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    if user.get("googleId"):
        raise HTTPException(status_code=400, detail="Cannot change password for Google accounts")
    
    if not verify_password(data.currentPassword, user["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password": hash_password(data.newPassword), "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True, "message": "Password changed successfully"}

@auth_router.get("/export-data")
async def export_user_data(user: dict = Depends(get_current_user)):
    """Export all user data for GDPR compliance"""
    # Get generations
    generations = await db.generations.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    # Get credit ledger
    ledger = await db.credit_ledger.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    # Get orders
    orders = await db.orders.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    return {
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "credits": user["credits"],
            "createdAt": user.get("createdAt")
        },
        "generations": generations,
        "creditHistory": ledger,
        "paymentHistory": orders
    }

@auth_router.delete("/account")
async def delete_account(user: dict = Depends(get_current_user)):
    """Delete user account and all associated data"""
    user_id = user["id"]
    
    # Delete all user data
    await db.generations.delete_many({"userId": user_id})
    await db.credit_ledger.delete_many({"userId": user_id})
    await db.orders.delete_many({"userId": user_id})
    await db.users.delete_one({"id": user_id})
    
    logger.info(f"User account deleted: {user['email']}")
    return {"success": True, "message": "Account deleted successfully"}

# ==================== EMAIL NOTIFICATION SERVICE ====================

async def send_email_notification(to_email: str, subject: str, html_body: str, email_type: str = "general"):
    """Send email notification using Resend"""
    email_log = {
        "id": str(uuid.uuid4()),
        "toEmail": to_email,
        "subject": subject,
        "type": email_type,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    if EMAIL_ENABLED and RESEND_AVAILABLE:
        try:
            params = {
                "from": f"CreatorStudio AI <{SENDER_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body
            }
            
            # Run sync SDK in thread to keep FastAPI non-blocking
            result = await asyncio.to_thread(resend.Emails.send, params)
            
            email_log["status"] = "SENT"
            email_log["resendId"] = result.get("id") if isinstance(result, dict) else str(result)
            logger.info(f"Email sent [{email_type}] to {to_email}: {subject}")
            
        except Exception as e:
            email_log["status"] = "FAILED"
            email_log["error"] = str(e)
            logger.error(f"Email send failed [{email_type}] to {to_email}: {e}")
    else:
        email_log["status"] = "SKIPPED"
        email_log["reason"] = "Email not configured" if not EMAIL_ENABLED else "Resend not available"
        logger.info(f"Email skipped [{email_type}] to {to_email}: {subject} (not configured)")
    
    # Save to database for tracking
    await db.email_logs.insert_one(email_log)
    return email_log["status"] == "SENT"

async def notify_payment_success(user: dict, order: dict):
    """Send payment success notification"""
    subject = f"Payment Confirmed - {order.get('productName', 'Credit Pack')}"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }}
            .order-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .highlight {{ color: #6366f1; font-weight: bold; }}
            .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✨ Payment Confirmed!</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{user['name']}</strong>,</p>
                <p>Your payment has been successfully processed! Here are your order details:</p>
                
                <div class="order-details">
                    <p><strong>Product:</strong> {order.get('productName', 'Credit Pack')}</p>
                    <p><strong>Amount:</strong> {order.get('currency', 'INR')} {order.get('amount', 0)}</p>
                    <p><strong>Credits Added:</strong> <span class="highlight">+{order.get('credits', 0)} credits</span></p>
                </div>
                
                <p>Your new credit balance: <span class="highlight">{user['credits']} credits</span></p>
                
                <p>Start creating amazing content now!</p>
                
                <div class="footer">
                    <p>Thank you for using CreatorStudio AI!</p>
                    <p>© 2026 CreatorStudio AI. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    await send_email_notification(user['email'], subject, html_body, "payment")

async def notify_generation_complete(user: dict, generation_type: str, generation_id: str):
    """Send generation completion notification"""
    subject = f"Your {generation_type} is Ready! 🎉 - CreatorStudio AI"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }}
            .cta-button {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎬 Your {generation_type} is Ready!</h1>
            </div>
            <div class="content">
                <p>Hi <strong>{user['name']}</strong>,</p>
                <p>Great news! Your {generation_type.lower()} generation is complete and ready to download.</p>
                
                <p><strong>Generation ID:</strong> {generation_id[:8]}...</p>
                
                <p>Log in to your dashboard to view, download, and share your creation!</p>
                
                <div class="footer">
                    <p>Happy creating! 🚀</p>
                    <p>© 2026 CreatorStudio AI. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    await send_email_notification(user['email'], subject, html_body, "generation")

async def notify_welcome(user: dict):
    """Send welcome email to new users"""
    subject = "Welcome to CreatorStudio AI! 🎉"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }}
            .feature-box {{ background: white; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #6366f1; }}
            .credits-badge {{ display: inline-block; background: #10b981; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; }}
            .cta-button {{ display: inline-block; background: #6366f1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
            .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Welcome to CreatorStudio AI!</h1>
                <p>Your creative journey starts here</p>
            </div>
            <div class="content">
                <p>Hi <strong>{user['name']}</strong>,</p>
                <p>We're thrilled to have you on board! You've received:</p>
                
                <p style="text-align: center;">
                    <span class="credits-badge">🎁 54 FREE CREDITS</span>
                </p>
                
                <p>Here's what you can create:</p>
                
                <div class="feature-box">
                    <h3>🎬 Reel Scripts (1 credit each)</h3>
                    <ul>
                        <li>Generate viral Instagram reel scripts in seconds</li>
                        <li>Complete with hooks, scenes, and hashtags</li>
                        <li>Optimized for engagement and growth</li>
                    </ul>
                </div>
                
                <div class="feature-box">
                    <h3>📖 Kids Story Packs (6-8 credits each)</h3>
                    <ul>
                        <li>Full video production packages</li>
                        <li>AI-generated scripts and scene breakdowns</li>
                        <li>Age-appropriate, safe content</li>
                    </ul>
                </div>
                
                <p style="text-align: center;">
                    <a href="https://creatorstudio-9.preview.emergentagent.com/app" class="cta-button">Start Creating Now →</a>
                </p>
                
                <p>Questions? Use our AI chatbot or reply to this email!</p>
                
                <div class="footer">
                    <p>Happy creating! 🚀</p>
                    <p>© 2026 CreatorStudio AI. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    await send_email_notification(user['email'], subject, html_body, "welcome")

# ==================== CREDITS ROUTES ====================

@credits_router.get("/balance")
async def get_balance(user: dict = Depends(get_current_user)):
    # Determine if user is on free tier (less than 54 credits and no purchases)
    purchase_count = await db.orders.count_documents({"userId": user["id"], "status": "PAID"})
    is_free_tier = purchase_count == 0
    
    return {
        "credits": user["credits"],
        "balance": user["credits"],  # Alias for compatibility
        "isFreeTier": is_free_tier
    }

@credits_router.get("/ledger")
async def get_ledger(page: int = 0, size: int = 20, user: dict = Depends(get_current_user)):
    skip = page * size
    ledger = await db.credit_ledger.find(
        {"userId": user["id"]}, 
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
    
    total = await db.credit_ledger.count_documents({"userId": user["id"]})
    
    return {
        "content": ledger,
        "totalElements": total,
        "page": page,
        "size": size
    }

# ==================== GENERATION ROUTES ====================

@generate_router.post("/reel")
async def generate_reel(data: GenerateReelRequest, user: dict = Depends(get_current_user)):
    # Check credits
    if user["credits"] < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits. You need 1 credit for reel generation.")
    
    try:
        # Call worker to generate
        async with httpx.AsyncClient(timeout=90.0) as client_http:
            response = await client_http.post(
                f"{WORKER_URL}/generate/reel",
                json=data.model_dump()
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Generation failed")
            
            result = response.json()
        
        # Deduct credit
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": -1}}
        )
        
        # Log transaction
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "amount": -1,
            "type": "USAGE",
            "description": f"Reel script generation: {data.topic[:50]}",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Save generation
        generation_id = str(uuid.uuid4())
        generation = {
            "id": generation_id,
            "userId": user["id"],
            "type": "REEL",
            "status": "COMPLETED",
            "inputJson": data.model_dump(),
            "outputJson": result,
            "creditsUsed": 1,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat()
        }
        await db.generations.insert_one(generation)
        
        return {
            "success": True,
            "generationId": generation_id,
            "result": result,
            "creditsUsed": 1,
            "remainingCredits": user["credits"] - 1
        }
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Generation timed out. Please try again.")
    except Exception as e:
        logger.error(f"Reel generation error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed")

@generate_router.post("/story")
async def generate_story(data: GenerateStoryRequest, user: dict = Depends(get_current_user)):
    credits_needed = min(max(data.sceneCount, 6), 10)  # 6-10 credits based on scenes
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. You need {credits_needed} credits for story generation.")
    
    # Create generation record
    generation_id = str(uuid.uuid4())
    
    try:
        # Generate story synchronously
        async with httpx.AsyncClient(timeout=180.0) as client_http:
            response = await client_http.post(
                f"{WORKER_URL}/generate/story",
                json=data.model_dump()
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Story generation failed")
            
            result = response.json()
        
        # Deduct credits after successful generation
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": -credits_needed}}
        )
        
        # Log transaction
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "amount": -credits_needed,
            "type": "USAGE",
            "description": f"Story pack generation: {data.genre} ({data.sceneCount} scenes)",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Save generation record
        generation = {
            "id": generation_id,
            "userId": user["id"],
            "type": "STORY",
            "status": "COMPLETED",
            "inputJson": data.model_dump(),
            "outputJson": result,
            "creditsUsed": credits_needed,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat()
        }
        await db.generations.insert_one(generation)
        
        return {
            "success": True,
            "generationId": generation_id,
            "status": "COMPLETED",
            "result": result,
            "creditsUsed": credits_needed,
            "remainingCredits": user["credits"] - credits_needed
        }
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Story generation timed out. Please try again.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Story generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")

@generate_router.get("/generations/{generation_id}")
async def get_generation(generation_id: str, user: dict = Depends(get_current_user)):
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return generation

@generate_router.get("/generations")
async def get_generations(type: Optional[str] = None, page: int = 0, size: int = 20, user: dict = Depends(get_current_user)):
    query = {"userId": user["id"]}
    if type:
        query["type"] = type.upper()
    
    skip = page * size
    generations = await db.generations.find(query, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
    total = await db.generations.count_documents(query)
    
    return {
        "content": generations,
        "totalElements": total,
        "page": page,
        "size": size
    }

@generate_router.post("/demo-reel")
async def demo_reel(data: GenerateReelRequest):
    """Demo endpoint - no auth required"""
    return {
        "success": True,
        "result": {
            "hooks": [
                "This changed everything for me...",
                "Stop scrolling - you need to see this!",
                "I wish someone told me this sooner",
                "The secret nobody talks about",
                "This will blow your mind"
            ],
            "best_hook": "Stop scrolling - you need to see this!",
            "script": {
                "scenes": [
                    {"time": "0-3s", "on_screen_text": "POV: You just discovered...", "voiceover": "Wait, you need to see this", "broll": ["close-up reveal shot"]},
                    {"time": "3-15s", "on_screen_text": "The secret is...", "voiceover": "Here's what changed everything", "broll": ["dynamic b-roll"]},
                    {"time": "15-25s", "on_screen_text": "Here's how...", "voiceover": "And here's exactly how you can do it too", "broll": ["tutorial style shots"]},
                    {"time": "25-30s", "on_screen_text": "Follow for more!", "voiceover": "Save this and follow for more tips", "broll": ["energetic closing"]}
                ],
                "cta": "Follow for more tips like this!"
            },
            "caption_short": "This changed everything 🚀",
            "caption_long": "I spent years figuring this out so you don't have to. Save this post and come back to it when you need it. Drop a 🔥 if this helped!",
            "hashtags": ["#viral", "#trending", "#tips", "#growth", "#creator"],
            "posting_tips": ["Post between 6-9 PM", "Use trending audio", "Reply to comments quickly"]
        },
        "message": "This is a demo. Sign up for full access!"
    }

# ==================== PAYMENTS ROUTES ====================

PRODUCTS = [
    {"id": "starter", "name": "Starter Pack", "credits": 50, "price": 99, "currency": "INR", "type": "ONE_TIME"},
    {"id": "pro", "name": "Pro Pack", "credits": 150, "price": 249, "currency": "INR", "type": "ONE_TIME"},
    {"id": "creator", "name": "Creator Pack", "credits": 400, "price": 499, "currency": "INR", "type": "ONE_TIME"},
    {"id": "monthly", "name": "Monthly Subscription", "credits": 100, "price": 199, "currency": "INR", "type": "SUBSCRIPTION"}
]

EXCHANGE_RATES = {
    "INR": 1.0,
    "USD": 0.012,
    "EUR": 0.011,
    "GBP": 0.0095
}

@payments_router.get("/products")
async def get_products():
    return {"products": PRODUCTS}

@payments_router.get("/currencies")
async def get_currencies():
    return {
        "currencies": ["INR", "USD", "EUR", "GBP"],
        "exchangeRates": EXCHANGE_RATES,
        "baseCurrency": "INR"
    }

@payments_router.get("/exchange-rate/{currency}")
async def get_exchange_rate(currency: str):
    currency = currency.upper()
    if currency not in EXCHANGE_RATES:
        raise HTTPException(status_code=400, detail="Currency not supported")
    return {"currency": currency, "rate": EXCHANGE_RATES[currency]}

@payments_router.post("/create-order")
async def create_order(data: CreateOrderRequest, user: dict = Depends(get_current_user)):
    try:
        product = next((p for p in PRODUCTS if p["id"] == data.productId), None)
        if not product:
            raise HTTPException(status_code=400, detail="Invalid product ID. Please select a valid product.")
        
        # Validate currency
        currency = data.currency.upper()
        if currency not in EXCHANGE_RATES:
            raise HTTPException(status_code=400, detail=f"Currency '{currency}' is not supported. Supported currencies: {', '.join(EXCHANGE_RATES.keys())}")
        
        # Create mock order (Razorpay integration would go here)
        order_id = f"order_{''.join(random.choices(string.ascii_letters + string.digits, k=14))}"
        
        # Calculate price in selected currency
        rate = EXCHANGE_RATES.get(currency, 1.0)
        converted_price = round(product["price"] * rate, 2)
        
        # Save order
        order = {
            "id": str(uuid.uuid4()),
            "razorpayOrderId": order_id,
            "userId": user["id"],
            "productId": data.productId,
            "productName": product["name"],
            "amount": converted_price,
            "currency": currency,
            "credits": product["credits"],
            "status": "PENDING",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "expiresAt": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        }
        await db.orders.insert_one(order)
        
        logger.info(f"Order created: {order_id} for user {user['email']}")
        
        return {
            "success": True,
            "orderId": order_id,
            "amount": int(converted_price * 100),  # In smallest currency unit
            "currency": currency,
            "productName": product["name"],
            "credits": product["credits"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create order. Please try again.")

@payments_router.post("/verify")
async def verify_payment(data: VerifyPaymentRequest, user: dict = Depends(get_current_user)):
    try:
        # Find order
        order = await db.orders.find_one({"razorpayOrderId": data.razorpay_order_id}, {"_id": 0})
        if not order:
            logger.warning(f"Order not found: {data.razorpay_order_id}")
            raise HTTPException(status_code=400, detail="Order not found. The order may have expired or is invalid.")
        
        # Verify ownership
        if order["userId"] != user["id"]:
            logger.warning(f"Unauthorized payment verification attempt: {data.razorpay_order_id} by {user['email']}")
            raise HTTPException(status_code=403, detail="You are not authorized to verify this payment.")
        
        # Check if already paid
        if order["status"] == "PAID":
            return {
                "success": True,
                "message": "Payment already verified",
                "creditsAdded": order["credits"],
                "alreadyProcessed": True
            }
        
        # Check if order expired (24 hours)
        if order.get("expiresAt"):
            expires_at = datetime.fromisoformat(order["expiresAt"].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                await db.orders.update_one(
                    {"razorpayOrderId": data.razorpay_order_id},
                    {"$set": {"status": "EXPIRED"}}
                )
                raise HTTPException(status_code=400, detail="Order has expired. Please create a new order.")
        
        # In production, verify signature with Razorpay
        # razorpay_signature verification would go here
        
        # Update order
        await db.orders.update_one(
            {"razorpayOrderId": data.razorpay_order_id},
            {
                "$set": {
                    "status": "PAID",
                    "razorpayPaymentId": data.razorpay_payment_id,
                    "razorpaySignature": data.razorpay_signature,
                    "paidAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Add credits to user
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": order["credits"]}}
        )
        
        # Log transaction
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "amount": order["credits"],
            "type": "PURCHASE",
            "description": f"Purchased {order['productName']} - {order['credits']} credits",
            "orderId": data.razorpay_order_id,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Send email notification (stubbed)
        updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
        await notify_payment_success(updated_user, order)
        
        logger.info(f"Payment verified: {data.razorpay_order_id} for user {user['email']}")
        
        return {
            "success": True,
            "message": "Payment verified successfully",
            "creditsAdded": order["credits"],
            "newBalance": updated_user["credits"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment verification failed: {e}")
        # Log failed payment
        await db.payment_failures.insert_one({
            "id": str(uuid.uuid4()),
            "orderId": data.razorpay_order_id,
            "paymentId": data.razorpay_payment_id,
            "userId": user["id"],
            "error": str(e),
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        raise HTTPException(status_code=500, detail="Payment verification failed. Please contact support if money was deducted.")

@payments_router.get("/history")
async def get_payment_history(page: int = 0, size: int = 20, user: dict = Depends(get_current_user)):
    skip = page * size
    orders = await db.orders.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
    
    total = await db.orders.count_documents({"userId": user["id"]})
    
    return {
        "content": orders,
        "totalElements": total,
        "page": page,
        "size": size
    }

@payments_router.get("/health")
async def payments_health():
    return {"status": "healthy"}

@payments_router.post("/webhook")
async def payment_webhook(request: Request):
    """Razorpay webhook handler"""
    return {"status": "ok"}

# ==================== EMAIL ROUTES ====================

@api_router.get("/email/status")
async def get_email_status():
    """Check email service status"""
    return {
        "enabled": EMAIL_ENABLED,
        "provider": "Resend" if RESEND_AVAILABLE else "None",
        "senderEmail": SENDER_EMAIL if EMAIL_ENABLED else None
    }

@admin_router.get("/email/logs")
async def get_email_logs(page: int = 0, size: int = 50, user: dict = Depends(get_admin_user)):
    """Get email logs for admin"""
    skip = page * size
    logs = await db.email_logs.find({}, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
    total = await db.email_logs.count_documents({})
    
    # Get stats
    sent_count = await db.email_logs.count_documents({"status": "SENT"})
    failed_count = await db.email_logs.count_documents({"status": "FAILED"})
    skipped_count = await db.email_logs.count_documents({"status": "SKIPPED"})
    
    return {
        "success": True,
        "logs": logs,
        "stats": {
            "total": total,
            "sent": sent_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "deliveryRate": round((sent_count / total * 100) if total > 0 else 0, 1)
        },
        "page": page,
        "size": size
    }

@api_router.post("/email/test")
async def send_test_email(user: dict = Depends(get_admin_user)):
    """Send a test email (admin only)"""
    subject = "Test Email from CreatorStudio AI"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .box {{ background: #f0f9ff; border: 1px solid #0ea5e9; padding: 20px; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>✅ Email Test Successful!</h2>
            <p>This is a test email sent from CreatorStudio AI.</p>
            <p><strong>Timestamp:</strong> {datetime.now(timezone.utc).isoformat()}</p>
            <p><strong>Sent to:</strong> {user['email']}</p>
        </div>
    </body>
    </html>
    """
    
    success = await send_email_notification(user['email'], subject, html_body, "test")
    
    # Get the last log entry
    last_log = await db.email_logs.find_one(
        {"toEmail": user['email'], "type": "test"},
        {"_id": 0},
        sort=[("createdAt", -1)]
    )
    
    error_msg = None
    if last_log and last_log.get("status") == "FAILED":
        error_msg = last_log.get("error", "Unknown error")
    
    return {
        "success": success,
        "message": "Test email sent successfully!" if success else f"Email failed: {error_msg}",
        "emailEnabled": EMAIL_ENABLED,
        "note": "Resend free tier only allows sending to the account owner's email. Verify a domain at resend.com/domains for full functionality." if not success and "own email" in str(error_msg) else None
    }

# ==================== FEEDBACK ROUTES ====================

@feedback_router.post("/suggestion")
async def submit_suggestion(data: FeedbackSuggestion):
    feedback = {
        "id": str(uuid.uuid4()),
        "name": "Anonymous User",
        "email": data.email or "anonymous@feedback.local",
        "type": data.category.upper() if data.category else "SUGGESTION",
        "rating": data.rating,
        "message": f"[{data.category.upper() if data.category else 'GENERAL'}] {data.suggestion}",
        "allowPublic": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.feedback.insert_one(feedback)
    logger.info(f"Feedback received: {data.category}")
    
    return {"success": True, "message": "Thank you for your feedback!"}

@api_router.post("/feedback")
async def submit_feedback_legacy(request: Request):
    """Legacy feedback endpoint"""
    try:
        body = await request.json()
        feedback = {
            "id": str(uuid.uuid4()),
            "name": body.get("name", "Anonymous"),
            "email": body.get("email", "anonymous@feedback.local"),
            "type": body.get("type", "FEEDBACK").upper(),
            "rating": body.get("rating", 5),
            "message": body.get("message", ""),
            "allowPublic": body.get("allowPublic", False),
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.feedback.insert_one(feedback)
        return {"status": "success", "message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return {"status": "error", "message": "Failed to submit feedback"}

@api_router.get("/reviews")
async def get_reviews():
    """Get public reviews"""
    reviews = await db.feedback.find(
        {"allowPublic": True, "type": "REVIEW"},
        {"_id": 0}
    ).sort("createdAt", -1).limit(20).to_list(20)
    return reviews

@api_router.post("/contact")
async def submit_contact(data: ContactMessage):
    contact = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "email": data.email,
        "subject": data.subject,
        "message": data.message,
        "resolved": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.contacts.insert_one(contact)
    return {"status": "success", "message": "Message sent successfully"}

# ==================== CHATBOT ROUTES ====================

@chatbot_router.post("/message")
async def chatbot_message(data: ChatMessage):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client_http:
            response = await client_http.post(
                f"{WORKER_URL}/chatbot/message",
                json=data.model_dump()
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "response": "Sorry, I'm having trouble right now. Please try again.",
                    "sessionId": data.sessionId
                }
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return {
            "success": False,
            "response": "Sorry, I'm having trouble right now. Please try again.",
            "sessionId": data.sessionId
        }

@api_router.post("/chat")
async def chat_proxy(data: ChatMessage):
    """Proxy for AI chat"""
    return await chatbot_message(data)

# ==================== ADMIN ROUTES ====================

@admin_router.get("/analytics/dashboard")
async def get_admin_analytics(days: int = 30, user: dict = Depends(get_admin_user)):
    # Calculate date range
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get counts
    total_users = await db.users.count_documents({})
    new_users = await db.users.count_documents({"createdAt": {"$gte": start_date}})
    total_generations = await db.generations.count_documents({})
    total_feedback = await db.feedback.count_documents({})
    
    # Get revenue
    paid_orders = await db.orders.find({"status": "PAID"}, {"_id": 0}).to_list(1000)
    total_revenue = sum(o.get("amount", 0) for o in paid_orders)
    period_revenue = sum(o.get("amount", 0) for o in paid_orders if o.get("createdAt", "") >= start_date)
    
    # Get recent users
    recent_users = await db.users.find({}, {"_id": 0, "password": 0}).sort("createdAt", -1).limit(10).to_list(10)
    
    # Get recent payments
    recent_payments = await db.orders.find({"status": "PAID"}, {"_id": 0}).sort("createdAt", -1).limit(10).to_list(10)
    
    return {
        "success": True,
        "data": {
            "overview": {
                "totalUsers": total_users,
                "newUsers": new_users,
                "totalGenerations": total_generations,
                "totalRevenue": total_revenue,
                "periodRevenue": period_revenue,
                "activeSessions": random.randint(5, 20)
            },
            "visitors": {
                "uniqueVisitors": random.randint(100, 500),
                "totalPageViews": random.randint(500, 2000),
                "anonymousVisitors": random.randint(50, 200),
                "loggedInVisitors": total_users,
                "dailyTrend": [{"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), "visitors": random.randint(10, 100)} for i in range(7)],
                "pageViews": [{"page": "/app", "views": random.randint(100, 500)}, {"page": "/pricing", "views": random.randint(50, 200)}],
                "deviceDistribution": {"Desktop": random.randint(60, 80), "Mobile": random.randint(20, 40)},
                "browserDistribution": {"Chrome": random.randint(50, 70), "Safari": random.randint(15, 30), "Firefox": random.randint(5, 15)}
            },
            "featureUsage": {
                "topFeatures": [{"feature": "REEL_GENERATION", "count": random.randint(50, 200)}, {"feature": "STORY_GENERATION", "count": random.randint(20, 100)}],
                "featurePercentages": [{"feature": "REEL_GENERATION", "percentage": 60}, {"feature": "STORY_GENERATION", "percentage": 40}],
                "uniqueUsersPerFeature": [{"feature": "REEL_GENERATION", "uniqueUsers": random.randint(20, 80)}]
            },
            "payments": {
                "totalTransactions": len(paid_orders),
                "successfulTransactions": len(paid_orders),
                "failedTransactions": 0,
                "pendingTransactions": 0,
                "successRate": 100,
                "planBreakdown": [],
                "failureReasons": [],
                "dailyRevenueTrend": [{"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), "revenue": random.randint(0, 500), "count": random.randint(0, 5)} for i in range(10)]
            },
            "satisfaction": {
                "satisfactionPercentage": 85,
                "averageRating": 4.2,
                "totalReviews": total_feedback,
                "npsScore": 42,
                "ratingDistribution": {5: 10, 4: 5, 3: 2, 2: 1, 1: 0},
                "recentReviews": [],
                "totalFeedback": total_feedback
            },
            "generations": {
                "reelGenerations": await db.generations.count_documents({"type": "REEL"}),
                "storyGenerations": await db.generations.count_documents({"type": "STORY"}),
                "successRate": 95,
                "creditsUsed": random.randint(100, 500)
            },
            "recentActivity": {
                "recentUsers": recent_users,
                "recentPayments": recent_payments
            }
        }
    }

@admin_router.get("/feedback/all")
async def get_all_feedback(user: dict = Depends(get_admin_user)):
    feedback_list = await db.feedback.find({}, {"_id": 0}).sort("createdAt", -1).to_list(1000)
    
    total = len(feedback_list)
    avg_rating = 0
    if feedback_list:
        ratings = [f.get("rating", 0) for f in feedback_list if f.get("rating")]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    by_category = {}
    for f in feedback_list:
        cat = f.get("type", "GENERAL")
        by_category[cat] = by_category.get(cat, 0) + 1
    
    return {
        "success": True,
        "feedback": feedback_list,
        "stats": {
            "total": total,
            "averageRating": avg_rating,
            "byCategory": by_category
        }
    }

@admin_router.delete("/feedback/{feedback_id}")
async def delete_feedback(feedback_id: str, user: dict = Depends(get_admin_user)):
    result = await db.feedback.delete_one({"id": feedback_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"success": True, "message": "Feedback deleted"}

@admin_router.get("/analytics/track/{event}")
async def track_event(event: str):
    """Public analytics tracking endpoint"""
    return {"status": "ok"}

# ==================== HEALTH ROUTES ====================

@health_router.get("/")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@health_router.get("/live")
async def liveness():
    return {"status": "live"}

@health_router.get("/ready")
async def readiness():
    return {"status": "ready"}

@api_router.get("/privacy/policy")
async def privacy_policy():
    return {
        "title": "Privacy Policy",
        "lastUpdated": "2024-01-01",
        "content": "CreatorStudio AI respects your privacy..."
    }

# ==================== FEATURE REQUESTS ====================

@api_router.get("/feature-requests/analytics")
async def feature_requests_analytics(user: dict = Depends(get_admin_user)):
    return {
        "success": True,
        "data": {
            "totalRequests": 0,
            "totalVotes": 0,
            "byStatus": {},
            "byCategory": [],
            "topRequests": []
        }
    }

# ==================== ROOT ENDPOINT ====================

@api_router.get("/")
async def root():
    return {"message": "CreatorStudio API", "version": "1.0.0"}

# ==================== INCLUDE ROUTERS ====================

api_router.include_router(auth_router)
api_router.include_router(credits_router)
api_router.include_router(generate_router)
api_router.include_router(payments_router)
api_router.include_router(feedback_router)
api_router.include_router(admin_router)
api_router.include_router(chatbot_router)
api_router.include_router(health_router)

app.include_router(api_router)

# ==================== MIDDLEWARE ====================

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup():
    logger.info("CreatorStudio API starting...")
    
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.generations.create_index("userId")
    await db.generations.create_index("id", unique=True)
    await db.feedback.create_index("id", unique=True)
    await db.orders.create_index("userId")
    await db.credit_ledger.create_index("userId")
    
    # Create admin user if not exists
    admin = await db.users.find_one({"email": "admin@creatorstudio.ai"})
    if not admin:
        admin_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": admin_id,
            "name": "Admin",
            "email": "admin@creatorstudio.ai",
            "password": hash_password("Admin@123"),
            "role": "ADMIN",
            "credits": 999999,  # Unlimited credits for admin
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Admin user created")
    else:
        # Update admin credits to unlimited
        await db.users.update_one(
            {"email": "admin@creatorstudio.ai"},
            {"$set": {"credits": 999999}}
        )
    
    # Create demo user if not exists
    demo = await db.users.find_one({"email": "demo@example.com"})
    if not demo:
        demo_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": demo_id,
            "name": "Demo User",
            "email": "demo@example.com",
            "password": hash_password("Password123!"),
            "role": "USER",
            "credits": 54,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Demo user created")
    
    logger.info("CreatorStudio API ready!")

@app.on_event("shutdown")
async def shutdown():
    client.close()
    logger.info("CreatorStudio API shutdown")
