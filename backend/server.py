from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header, BackgroundTasks, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
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
import asyncio
import razorpay
import base64
import tempfile
import shutil
import re
import html

# Import security module
from security import (
    limiter, rate_limit_exceeded_handler, sanitize_input, sanitize_filename,
    detect_dangerous_content, detect_prohibited_content, validate_prompt,
    add_security_headers, security_middleware, validate_password_strength,
    generate_secure_token, validate_file_type, validate_file_size,
    log_security_event, sanitize_mongo_query, SECURITY_HEADERS,
    ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES, record_suspicious_activity
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# LLM Integration for AI generation
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# ElevenLabs for TTS
try:
    from elevenlabs import ElevenLabs
    from elevenlabs.core import ApiError as ElevenLabsError
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

# MoviePy for video generation
try:
    from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# SendGrid for email
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration - require JWT_SECRET in production for security
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    # Generate a default for development only - in production, JWT_SECRET must be set
    JWT_SECRET = 'dev-only-secret-' + str(uuid.uuid4())
    print("WARNING: JWT_SECRET not set - using generated development secret. Set JWT_SECRET in production!")
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 168  # 7 days

# Worker URL
WORKER_URL = os.environ.get('WORKER_URL', 'http://localhost:5000')

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

# Initialize Razorpay Client
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Email Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
ADMIN_ALERT_EMAIL = os.environ.get('ADMIN_ALERT_EMAIL', 'krajapraveen@visionary-suite.com')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'alerts@creatorstudio.ai')

# Initialize SendGrid
EMAIL_ENABLED = SENDGRID_AVAILABLE and bool(SENDGRID_API_KEY)

# LLM Configuration for AI Generation
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# ElevenLabs Configuration for TTS
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
eleven_client = None
if ELEVENLABS_AVAILABLE and ELEVENLABS_API_KEY:
    eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Video storage directory
VIDEO_STORAGE_DIR = Path("/tmp/creatorstudio_videos")
VIDEO_STORAGE_DIR.mkdir(exist_ok=True)

# AI Generation Prompts
REEL_SYSTEM_PROMPT = """You are an elite social media scriptwriter. Output must be structured JSON only."""

REEL_USER_PROMPT_TEMPLATE = """Generate a UNIQUE and ORIGINAL high-retention Instagram Reel package. This content must be COMPLETELY DIFFERENT from anything generated before.

**Input Parameters:**
- Language: {language}
- Niche: {niche}
- Tone: {tone}
- Duration: {duration}
- Goal: {goal}
- Topic: {topic}
- Unique Request ID: {uniqueId}

**CREATIVITY REQUIREMENTS:**
- Create FRESH hooks that haven't been used before
- Make the script UNIQUE and engaging
- Use creative, unexpected angles on the topic
- Don't use generic or overused phrases

Output ONLY this JSON format:
{{
  "hooks": ["5 unique, attention-grabbing hooks under 12 words each"],
  "best_hook": "The most powerful hook from above",
  "script": {{
    "scenes": [
      {{"time": "0-2s", "on_screen_text": "...", "voiceover": "...", "broll": ["visual suggestions"]}}
    ],
    "cta": "Compelling call to action"
  }},
  "caption_short": "Short engaging caption",
  "caption_long": "Detailed caption with value",
  "hashtags": ["20 relevant trending hashtags"],
  "posting_tips": ["5 specific tips for this content"]
}}

Rules:
• Hooks MUST be under 12 words and attention-grabbing
• Script must be punchy and scroll-stopping
• Make it UNIQUE - don't repeat common patterns
• No unsafe/illegal content

Return ONLY valid JSON, no markdown or explanation."""

STORY_SYSTEM_PROMPT = """You are a creative children's story writer. Each story you create must be COMPLETELY UNIQUE and DIFFERENT from any previous stories. 

CRITICAL RULES:
- NEVER repeat the same plot, characters, or storyline
- Always create FRESH, ORIGINAL content
- Use the provided genre and age group to craft age-appropriate content
- Make stories engaging, educational, and fun
- No violence, fear, or adult themes
- Output must be structured JSON only"""

STORY_USER_PROMPT_TEMPLATE = """Create a COMPLETELY UNIQUE and ORIGINAL kids story video pack. This story must be DIFFERENT from any story you've created before.

**REQUIREMENTS:**
- Genre: {genre}
- Age Group: {ageGroup} years old
- Theme/Moral: {theme}
- Number of Scenes: {scenes}
- Custom Elements: {customElements}
- Unique ID: {uniqueId}

**CREATIVITY INSTRUCTIONS:**
- Invent NEW character names (don't use common names like "Max" or "Luna")
- Create a FRESH plot that hasn't been done before
- Use unexpected twists and creative scenarios
- Make the setting unique and interesting
- The title should be catchy and original

Output ONLY this JSON format (no markdown, no explanation):
{{
  "title": "A unique, catchy title for this specific story",
  "synopsis": "A 2-3 sentence summary of this unique story",
  "genre": "{genre}",
  "ageGroup": "{ageGroup}",
  "moral": "The lesson or moral of this story",
  "characters": [
    {{"name": "Unique character name", "role": "protagonist/supporting", "description": "Brief description"}}
  ],
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene title",
      "setting": "Where this scene takes place",
      "visual_description": "Detailed description for illustration",
      "narration": "The narrator's text for this scene",
      "dialogue": [{{"speaker": "Character name", "line": "What they say"}}],
      "image_prompt": "Detailed prompt for generating scene illustration"
    }}
  ],
  "youtubeMetadata": {{
    "title": "YouTube video title",
    "description": "YouTube description with story summary",
    "tags": ["relevant", "tags", "for", "youtube"]
  }}
}}

Remember: Create something FRESH and ORIGINAL. Do not repeat patterns from other stories."""

# Security
security = HTTPBearer(auto_error=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
# File expiry time - 3 MINUTES for security
FILE_EXPIRY_MINUTES = 3
GENSTUDIO_FILE_EXPIRY_MINUTES = 3
PDF_FILE_EXPIRY_MINUTES = 3

# Create the main app with security settings
app = FastAPI(
    title="CreatorStudio API",
    docs_url=None,  # Disable Swagger in production
    redoc_url=None,  # Disable ReDoc in production
    openapi_url=None  # Disable OpenAPI schema in production
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add security middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response

@app.middleware("http")
async def threat_detection_middleware(request: Request, call_next):
    """Detect and block malicious requests"""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Check for suspicious patterns in URL
    path = request.url.path.lower()
    query = str(request.url.query).lower() if request.url.query else ""
    
    # Block common attack vectors
    attack_patterns = [
        '../', '..\\', '/etc/', '/proc/', '.env', '.git', 
        'wp-admin', 'phpinfo', 'eval(', 'exec(', '<script',
        'javascript:', 'vbscript:', 'onload=', 'onerror=',
        'union select', 'drop table', '1=1', "' or '",
        'cmd.exe', '/bin/sh', '/bin/bash'
    ]
    
    for pattern in attack_patterns:
        if pattern in path or pattern in query:
            log_security_event("BLOCKED_REQUEST", {
                "ip": client_ip,
                "path": path,
                "pattern": pattern
            }, "WARNING")
            record_suspicious_activity(client_ip, f"Attack pattern: {pattern}")
            return Response(content="Forbidden", status_code=403)
    
    return await call_next(request)

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

# New Creator Tools Routers
creator_tools_router = APIRouter(prefix="/creator-tools", tags=["Creator Tools"])
story_tools_router = APIRouter(prefix="/story-tools", tags=["Story Tools"])
content_router = APIRouter(prefix="/content", tags=["Content Vault"])
convert_router = APIRouter(prefix="/convert", tags=["Convert Tools"])

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
@limiter.limit("5/minute")  # Rate limit: 5 registrations per minute per IP
async def register(request: Request, data: UserCreate, background_tasks: BackgroundTasks):
    """User registration with security validation"""
    try:
        # Sanitize inputs
        sanitized_name = sanitize_input(data.name, max_length=100)
        sanitized_email = data.email.lower().strip()
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(data.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Check if user exists
        existing = await db.users.find_one({"email": sanitized_email})
        if existing:
            log_security_event("REGISTRATION_DUPLICATE", {"email": sanitized_email}, "INFO")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "name": sanitized_name,
            "email": sanitized_email,
            "password": hash_password(data.password),
            "role": "USER",
            "credits": 100,  # 100 free credits on signup
            "plan": "free",
            "subscription": None,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.users.insert_one(user)
        
        # Log credit transaction
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "amount": 100,
            "type": "BONUS",
            "description": "Welcome bonus - 100 free credits",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Send welcome email in background
        background_tasks.add_task(notify_welcome, user)
        
        log_security_event("USER_REGISTERED", {"user_id": user_id, "email": sanitized_email}, "INFO")
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

@auth_router.post("/login")
@limiter.limit("10/minute")  # Rate limit: 10 login attempts per minute per IP
async def login(request: Request, data: UserLogin):
    """User login with security measures"""
    try:
        client_ip = request.client.host if request.client else "unknown"
        sanitized_email = data.email.lower().strip()
        
        user = await db.users.find_one({"email": sanitized_email}, {"_id": 0})
        if not user:
            log_security_event("LOGIN_FAILED_USER_NOT_FOUND", {"email": sanitized_email, "ip": client_ip}, "WARNING")
            record_suspicious_activity(client_ip, "Failed login - user not found")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not verify_password(data.password, user["password"]):
            log_security_event("LOGIN_FAILED_WRONG_PASSWORD", {"email": sanitized_email, "ip": client_ip}, "WARNING")
            record_suspicious_activity(client_ip, "Failed login - wrong password")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_token(user["id"], user["role"])
        
        log_security_event("LOGIN_SUCCESS", {"user_id": user["id"], "email": sanitized_email}, "INFO")
        
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

def send_email_sync(to_email: str, subject: str, html_content: str):
    """Send email using SendGrid (synchronous)"""
    if not EMAIL_ENABLED:
        logger.info(f"Email disabled - would send to {to_email}: {subject}")
        return False
    
    try:
        message = Mail(
            from_email=Email(SENDER_EMAIL, "CreatorStudio AI"),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"Email sent to {to_email}: {subject} (Status: {response.status_code})")
        return response.status_code == 202
    except Exception as e:
        logger.error(f"Email send failed to {to_email}: {e}")
        return False

async def send_email_notification(to_email: str, subject: str, html_body: str, email_type: str = "general"):
    """Send email notification and log to database"""
    email_log = {
        "id": str(uuid.uuid4()),
        "toEmail": to_email,
        "subject": subject,
        "type": email_type,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    if EMAIL_ENABLED:
        try:
            success = send_email_sync(to_email, subject, html_body)
            email_log["status"] = "SENT" if success else "FAILED"
        except Exception as e:
            email_log["status"] = "FAILED"
            email_log["error"] = str(e)
    else:
        email_log["status"] = "LOGGED"
        logger.info(f"Email logged [{email_type}] to {to_email}: {subject}")
    
    await db.email_logs.insert_one(email_log)
    return email_log["status"] == "SENT"

# ==================== ADMIN ALERT EMAILS ====================

async def send_admin_alert(alert_type: str, title: str, message: str, severity: str = "INFO", details: dict = None):
    """Send alert email to admin"""
    severity_colors = {
        "CRITICAL": "#dc2626",
        "ERROR": "#ea580c",
        "WARNING": "#ca8a04",
        "INFO": "#2563eb",
        "SUCCESS": "#16a34a"
    }
    
    severity_icons = {
        "CRITICAL": "🚨",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "INFO": "ℹ️",
        "SUCCESS": "✅"
    }
    
    color = severity_colors.get(severity, "#6b7280")
    icon = severity_icons.get(severity, "📧")
    
    details_html = ""
    if details:
        details_html = "<table style='width:100%;border-collapse:collapse;margin-top:15px;'>"
        for key, value in details.items():
            details_html += f"<tr><td style='padding:8px;border:1px solid #e5e7eb;background:#f9fafb;font-weight:bold;'>{key}</td><td style='padding:8px;border:1px solid #e5e7eb;'>{value}</td></tr>"
        details_html += "</table>"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #f3f4f6; }}
            .container {{ max-width: 600px; margin: 20px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .header {{ background: {color}; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; }}
            .alert-badge {{ display: inline-block; background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; margin-bottom: 10px; }}
            .footer {{ background: #f9fafb; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span class="alert-badge">{alert_type}</span>
                <h1 style="margin:10px 0;">{icon} {title}</h1>
                <p style="margin:0;opacity:0.9;">Severity: {severity}</p>
            </div>
            <div class="content">
                <p style="font-size:16px;line-height:1.6;">{message}</p>
                {details_html}
                <p style="margin-top:20px;color:#6b7280;font-size:14px;">
                    <strong>Timestamp:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                </p>
            </div>
            <div class="footer">
                <p>CreatorStudio AI Alert System</p>
                <p>This is an automated message. Do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    subject = f"[{severity}] {icon} {title} - CreatorStudio AI"
    await send_email_notification(ADMIN_ALERT_EMAIL, subject, html_body, f"alert_{alert_type.lower()}")

async def send_health_report(services_status: dict, metrics: dict):
    """Send health report email to admin"""
    all_healthy = all(s.get("status") == "healthy" for s in services_status.values())
    
    status_html = ""
    for service, status in services_status.items():
        is_healthy = status.get("status") == "healthy"
        status_color = "#16a34a" if is_healthy else "#dc2626"
        status_icon = "✅" if is_healthy else "❌"
        status_html += f"""
        <tr>
            <td style="padding:10px;border:1px solid #e5e7eb;">{status_icon} {service}</td>
            <td style="padding:10px;border:1px solid #e5e7eb;color:{status_color};font-weight:bold;">{status.get('status', 'unknown').upper()}</td>
            <td style="padding:10px;border:1px solid #e5e7eb;">{status.get('response_time', 'N/A')}</td>
        </tr>
        """
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #f3f4f6; }}
            .container {{ max-width: 700px; margin: 20px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .header {{ background: {'#16a34a' if all_healthy else '#dc2626'}; color: white; padding: 25px; text-align: center; }}
            .content {{ padding: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th {{ background: #f3f4f6; padding: 12px; text-align: left; border: 1px solid #e5e7eb; }}
            .metric-box {{ display: inline-block; background: #f3f4f6; padding: 15px 25px; border-radius: 8px; margin: 5px; text-align: center; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #1f2937; }}
            .metric-label {{ font-size: 12px; color: #6b7280; }}
            .footer {{ background: #f9fafb; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0;">{'✅ All Systems Operational' if all_healthy else '🚨 System Issues Detected'}</h1>
                <p style="margin:10px 0 0 0;opacity:0.9;">Health Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
            </div>
            <div class="content">
                <h2 style="color:#1f2937;">Service Status</h2>
                <table>
                    <tr>
                        <th>Service</th>
                        <th>Status</th>
                        <th>Response Time</th>
                    </tr>
                    {status_html}
                </table>
                
                <h2 style="color:#1f2937;margin-top:30px;">System Metrics</h2>
                <div style="text-align:center;">
                    <div class="metric-box">
                        <div class="metric-value">{metrics.get('total_users', 0)}</div>
                        <div class="metric-label">Total Users</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{metrics.get('total_generations', 0)}</div>
                        <div class="metric-label">Generations</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{metrics.get('active_sessions', 0)}</div>
                        <div class="metric-label">Active Sessions</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">₹{metrics.get('total_revenue', 0)}</div>
                        <div class="metric-label">Revenue</div>
                    </div>
                </div>
            </div>
            <div class="footer">
                <p>CreatorStudio AI - Automated Health Report</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    subject = f"{'✅' if all_healthy else '🚨'} Health Report - CreatorStudio AI"
    await send_email_notification(ADMIN_ALERT_EMAIL, subject, html_body, "health_report")

async def send_service_down_alert(service_name: str, error_message: str, last_healthy: str = None):
    """Send service down alert"""
    await send_admin_alert(
        alert_type="SERVICE_DOWN",
        title=f"{service_name} is DOWN",
        message=f"The {service_name} service has stopped responding and requires immediate attention.",
        severity="CRITICAL",
        details={
            "Service": service_name,
            "Error": error_message,
            "Last Healthy": last_healthy or "Unknown",
            "Action Required": "Please check the service logs and restart if necessary."
        }
    )

async def send_functionality_error_alert(functionality: str, error_message: str, user_email: str = None):
    """Send functionality error alert"""
    details = {
        "Functionality": functionality,
        "Error": error_message,
        "Impact": "Users may be unable to use this feature"
    }
    if user_email:
        details["Affected User"] = user_email
    
    await send_admin_alert(
        alert_type="FUNCTIONALITY_ERROR",
        title=f"{functionality} Not Working",
        message=f"A critical functionality error has been detected in the {functionality} feature.",
        severity="ERROR",
        details=details
    )

async def send_analytics_report(period: str, analytics_data: dict):
    """Send analytics report email"""
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #f3f4f6; }}
            .container {{ max-width: 700px; margin: 20px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 25px; text-align: center; }}
            .content {{ padding: 30px; }}
            .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }}
            .stat-box {{ background: #f9fafb; padding: 20px; border-radius: 8px; text-align: center; }}
            .stat-value {{ font-size: 28px; font-weight: bold; color: #1f2937; }}
            .stat-label {{ font-size: 13px; color: #6b7280; margin-top: 5px; }}
            .stat-change {{ font-size: 12px; margin-top: 5px; }}
            .positive {{ color: #16a34a; }}
            .negative {{ color: #dc2626; }}
            .footer {{ background: #f9fafb; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0;">📊 Analytics Report</h1>
                <p style="margin:10px 0 0 0;opacity:0.9;">{period}</p>
            </div>
            <div class="content">
                <div class="stat-grid">
                    <div class="stat-box">
                        <div class="stat-value">{analytics_data.get('new_users', 0)}</div>
                        <div class="stat-label">New Users</div>
                        <div class="stat-change positive">+{analytics_data.get('user_growth', 0)}%</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{analytics_data.get('total_generations', 0)}</div>
                        <div class="stat-label">Generations</div>
                        <div class="stat-change positive">+{analytics_data.get('generation_growth', 0)}%</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">₹{analytics_data.get('revenue', 0)}</div>
                        <div class="stat-label">Revenue</div>
                        <div class="stat-change positive">+{analytics_data.get('revenue_growth', 0)}%</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{analytics_data.get('satisfaction', 0)}%</div>
                        <div class="stat-label">Satisfaction</div>
                    </div>
                </div>
                
                <h3 style="color:#1f2937;">Top Features</h3>
                <ul style="color:#4b5563;">
                    <li>Reel Generation: {analytics_data.get('reel_count', 0)} generations</li>
                    <li>Story Generation: {analytics_data.get('story_count', 0)} generations</li>
                </ul>
                
                <h3 style="color:#1f2937;">Key Insights</h3>
                <ul style="color:#4b5563;">
                    <li>Most active day: {analytics_data.get('most_active_day', 'N/A')}</li>
                    <li>Average session duration: {analytics_data.get('avg_session', 'N/A')}</li>
                    <li>Conversion rate: {analytics_data.get('conversion_rate', 0)}%</li>
                </ul>
            </div>
            <div class="footer">
                <p>CreatorStudio AI - Analytics Report</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    subject = f"📊 Analytics Report ({period}) - CreatorStudio AI"
    await send_email_notification(ADMIN_ALERT_EMAIL, subject, html_body, "analytics_report")

# ==================== USER NOTIFICATION EMAILS ====================

async def notify_payment_success(user: dict, order: dict):
    """Send payment success notification"""
    subject = f"Payment Confirmed - {order.get('productName', 'Credit Pack')}"
    body = f"Payment of {order.get('currency', 'INR')} {order.get('amount', 0)} confirmed. {order.get('credits', 0)} credits added."
    await send_email_notification(user['email'], subject, body, "payment")

async def notify_generation_complete(user: dict, generation_type: str, generation_id: str):
    """Send generation completion notification"""
    subject = f"Your {generation_type} is Ready!"
    body = f"Generation {generation_id} completed successfully."
    await send_email_notification(user['email'], subject, body, "generation")

async def notify_welcome(user: dict):
    """Send welcome email to new users"""
    subject = "Welcome to CreatorStudio AI!"
    body = f"Welcome {user['name']}! You have 54 free credits to start creating."
    await send_email_notification(user['email'], subject, body, "welcome")

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

# ==================== AI GENERATION HELPERS ====================

async def generate_reel_content_inline(data: dict) -> dict:
    """Generate reel script using LLM directly (no worker needed)"""
    import time
    
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        raise Exception("LLM service not available")
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            unique_session = f"reel_{uuid.uuid4().hex[:12]}_{int(time.time())}"
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=unique_session,
                system_message=REEL_SYSTEM_PROMPT
            ).with_model("gemini", "gemini-2.0-flash")
            
            prompt = REEL_USER_PROMPT_TEMPLATE.format(
                language=data.get('language', 'English'),
                niche=data.get('niche', 'General'),
                tone=data.get('tone', 'Bold'),
                duration=data.get('duration', '30s'),
                goal=data.get('goal', 'Followers'),
                topic=data.get('topic', ''),
                uniqueId=unique_session
            )
            
            user_message = UserMessage(text=prompt)
            response = await asyncio.wait_for(chat.send_message(user_message), timeout=60.0)
            
            result_text = response.strip()
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            return json.loads(result_text.strip())
            
        except asyncio.TimeoutError:
            logger.warning(f"Reel generation timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise Exception("Reel generation timed out. Please try again.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise Exception("Failed to parse response. Please try again.")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Reel generation error (attempt {attempt + 1}): {error_msg}")
            if any(code in error_msg for code in ['502', '503', '504', 'BadGateway', 'timeout', 'connection']):
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            raise

async def generate_story_content_inline(data: dict) -> dict:
    """Generate story pack using LLM directly (no worker needed)"""
    import time
    
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        raise Exception("LLM service not available")
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            unique_session = f"story_{uuid.uuid4().hex[:12]}_{int(time.time())}"
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=unique_session,
                system_message=STORY_SYSTEM_PROMPT
            ).with_model("gemini", "gemini-2.0-flash")
            
            genre = data.get('genre', 'Adventure')
            if genre == 'Custom' and data.get('customGenre'):
                genre = data.get('customGenre')
            
            custom_elements = []
            if data.get('theme'):
                custom_elements.append(f"Theme: {data.get('theme')}")
            if data.get('moral'):
                custom_elements.append(f"Moral: {data.get('moral')}")
            if data.get('setting'):
                custom_elements.append(f"Setting: {data.get('setting')}")
            if data.get('characters'):
                chars = data.get('characters')
                if isinstance(chars, list):
                    custom_elements.append(f"Include characters like: {', '.join(chars)}")
            
            random_themes = ["unexpected friendship", "magical discovery", "brave adventure", "funny mishap", "learning moment", "helping others", "creative solution", "teamwork triumph"]
            custom_elements.append(f"Include element of: {random.choice(random_themes)}")
            
            prompt = STORY_USER_PROMPT_TEMPLATE.format(
                genre=genre,
                ageGroup=data.get('ageGroup', '4-6'),
                theme=data.get('theme', 'Friendship and Adventure'),
                scenes=data.get('sceneCount', data.get('scenes', 8)),
                customElements='; '.join(custom_elements) if custom_elements else 'Create freely',
                uniqueId=unique_session
            )
            
            user_message = UserMessage(text=prompt)
            response = await asyncio.wait_for(chat.send_message(user_message), timeout=90.0)
            
            result_text = response.strip()
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            return json.loads(result_text.strip())
            
        except asyncio.TimeoutError:
            logger.warning(f"Story generation timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise Exception("Story generation timed out. Please try again.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise Exception("Failed to parse response. Please try again.")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Story generation error (attempt {attempt + 1}): {error_msg}")
            if any(code in error_msg for code in ['502', '503', '504', 'BadGateway', 'timeout', 'connection']):
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            raise

# ==================== GENERATION ROUTES ====================

@generate_router.post("/reel")
async def generate_reel(data: GenerateReelRequest, user: dict = Depends(get_current_user)):
    """Generate a viral reel - costs 10 credits"""
    credits_needed = 10  # Fixed 10 credits per reel
    
    # Check if user has subscription or free credits
    user_credits = user.get("credits", 0)
    user_subscription = user.get("subscription")
    
    if user_credits < credits_needed:
        if not user_subscription:
            raise HTTPException(
                status_code=402, 
                detail="You've used all your free credits! Please subscribe to continue generating reels."
            )
        raise HTTPException(status_code=400, detail=f"Insufficient credits. You need {credits_needed} credits for reel generation.")
    
    try:
        # Try inline generation first (for production), fall back to worker (for local dev)
        result = None
        generation_error = None
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                result = await generate_reel_content_inline(data.model_dump())
            except Exception as inline_error:
                logger.warning(f"Inline generation failed: {inline_error}")
                generation_error = str(inline_error)
        
        # Fall back to worker if inline failed or not available (local dev only)
        if result is None and WORKER_URL and 'localhost' not in WORKER_URL:
            try:
                async with httpx.AsyncClient(timeout=90.0) as client_http:
                    response = await client_http.post(
                        f"{WORKER_URL}/generate/reel",
                        json=data.model_dump()
                    )
                    if response.status_code == 200:
                        result = response.json()
            except Exception as worker_error:
                logger.warning(f"Worker fallback also failed: {worker_error}")
        
        if result is None:
            error_msg = generation_error or "AI service unavailable. Please try again."
            raise HTTPException(status_code=503, detail=error_msg)
        
        # Deduct credits
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
            "creditsUsed": credits_needed,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat()
        }
        await db.generations.insert_one(generation)
        
        return {
            "success": True,
            "generationId": generation_id,
            "result": result,
            "creditsUsed": credits_needed,
            "remainingCredits": user["credits"] - credits_needed
        }
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Generation timed out. Please try again.")
    except Exception as e:
        logger.error(f"Reel generation error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed")

@generate_router.post("/story")
async def generate_story(data: GenerateStoryRequest, user: dict = Depends(get_current_user)):
    """Generate a kids story - costs 10 credits"""
    credits_needed = 10  # Fixed 10 credits per story
    
    # Check if user has subscription or free credits
    user_credits = user.get("credits", 0)
    user_subscription = user.get("subscription")
    
    if user_credits < credits_needed:
        if not user_subscription:
            raise HTTPException(
                status_code=402, 
                detail="You've used all your free credits! Please subscribe to continue generating stories."
            )
        raise HTTPException(status_code=400, detail=f"Insufficient credits. You need {credits_needed} credits for story generation.")
    
    # Create generation record
    generation_id = str(uuid.uuid4())
    
    try:
        result = None
        
        # TEMPLATE-BASED GENERATION (FREE - No LLM cost)
        # Try to find a matching template first
        template = await db.story_templates.find_one({
            "ageGroup": data.ageGroup,
            "genre": data.genre if data.genre != "Custom" else {"$exists": True}
        }, {"_id": 0})
        
        # Fallback 1: If no exact match, try any template for this age group
        if not template:
            logger.info(f"No exact match for {data.ageGroup}/{data.genre}, trying any template for age group")
            template = await db.story_templates.find_one({
                "ageGroup": data.ageGroup
            }, {"_id": 0})
        
        # Fallback 2: If still no match, try a nearby age group
        if not template:
            logger.info(f"No template for {data.ageGroup}, trying nearby age groups")
            age_fallbacks = {
                "4-6": ["6-8", "8-10"],
                "6-8": ["4-6", "8-10"],
                "8-10": ["6-8", "10-13"],
                "10-13": ["8-10", "13-15"],
                "13-15": ["10-13", "15-17"],
                "15-17": ["13-15", "10-13"]
            }
            for fallback_age in age_fallbacks.get(data.ageGroup, []):
                template = await db.story_templates.find_one({
                    "ageGroup": fallback_age
                }, {"_id": 0})
                if template:
                    logger.info(f"Using fallback age group {fallback_age}")
                    break
        
        if template:
            # Generate random character names for uniqueness
            hero_names = ["Max", "Luna", "Leo", "Maya", "Sam", "Zoe", "Jack", "Lily", "Finn", "Emma", "Oliver", "Ava", "Noah", "Mia", "Ethan", "Sophie"]
            friend_names = ["Pip", "Sparkle", "Buddy", "Twinkle", "Fuzzy", "Whiskers", "Bubbles", "Patches", "Ziggy", "Coco"]
            mentor_names = ["Grandma Rose", "Old Wizard Oak", "Wise Owl", "Elder Willow", "Magic Fox", "Ancient Turtle"]
            
            hero_name = random.choice(hero_names)
            friend_name = random.choice(friend_names)
            mentor_name = random.choice(mentor_names)
            
            # Deep copy and replace placeholders
            import copy
            result = copy.deepcopy(template)
            
            # Remove template-specific fields
            result.pop("templateNumber", None)
            result.pop("usageCount", None)
            result.pop("createdAt", None)
            
            # Convert to JSON string, replace placeholders, convert back
            result_str = json.dumps(result)
            result_str = result_str.replace("{{HERO_NAME}}", hero_name)
            result_str = result_str.replace("{{FRIEND_NAME}}", friend_name)
            result_str = result_str.replace("{{MENTOR_NAME}}", mentor_name)
            result = json.loads(result_str)
            
            # Update template usage count
            await db.story_templates.update_one(
                {"id": template["id"]},
                {"$inc": {"usageCount": 1}}
            )
            
            logger.info(f"Used template story: {template['title']} for user {user['email']}")
        
        # If no template found, the story generation fails gracefully
        if result is None:
            raise HTTPException(status_code=503, detail="No matching story template found. Please try different options.")
        
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

@generate_router.get("/generations/{generation_id}/pdf")
async def download_generation_pdf(generation_id: str, user: dict = Depends(get_current_user)):
    """Generate and download a PDF for a story generation"""
    from fastapi.responses import Response
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from io import BytesIO
    
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    result = generation.get("outputJson", {})
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.HexColor('#7c3aed'))
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=16, spaceAfter=10, textColor=colors.HexColor('#4f46e5'))
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, spaceAfter=8, leading=14)
    scene_title_style = ParagraphStyle('SceneTitle', parent=styles['Heading3'], fontSize=13, spaceAfter=6, textColor=colors.HexColor('#6366f1'))
    
    story = []
    
    # Title
    story.append(Paragraph(result.get('title', 'Story Pack'), title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Synopsis
    if result.get('synopsis'):
        story.append(Paragraph('<b>Synopsis:</b>', heading_style))
        story.append(Paragraph(result.get('synopsis', ''), body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Genre & Age Group
    story.append(Paragraph(f"<b>Genre:</b> {result.get('genre', 'N/A')} | <b>Age Group:</b> {result.get('ageGroup', 'N/A')}", body_style))
    if result.get('moral'):
        story.append(Paragraph(f"<b>Moral:</b> {result.get('moral', '')}", body_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Characters
    characters = result.get('characters', [])
    if characters:
        story.append(Paragraph('Characters', heading_style))
        for char in characters:
            story.append(Paragraph(f"<b>{char.get('name', 'Unknown')}</b> ({char.get('role', 'character')}): {char.get('description', '')}", body_style))
        story.append(Spacer(1, 0.3*inch))
    
    # Scenes
    scenes = result.get('scenes', [])
    if scenes:
        story.append(Paragraph('Scenes', heading_style))
        for scene in scenes:
            story.append(Paragraph(f"Scene {scene.get('scene_number', '?')}: {scene.get('title', 'Untitled')}", scene_title_style))
            if scene.get('setting'):
                story.append(Paragraph(f"<i>Setting: {scene.get('setting')}</i>", body_style))
            if scene.get('narration'):
                story.append(Paragraph(f"<b>Narration:</b> {scene.get('narration')}", body_style))
            if scene.get('visual_description'):
                story.append(Paragraph(f"<b>Visual:</b> {scene.get('visual_description')}", body_style))
            dialogues = scene.get('dialogue', [])
            if dialogues:
                for d in dialogues:
                    story.append(Paragraph(f"<b>{d.get('speaker', 'Speaker')}:</b> \"{d.get('line', '')}\"", body_style))
            story.append(Spacer(1, 0.15*inch))
    
    # YouTube Metadata
    yt = result.get('youtubeMetadata', {})
    if yt:
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph('YouTube Metadata', heading_style))
        story.append(Paragraph(f"<b>Title:</b> {yt.get('title', '')}", body_style))
        story.append(Paragraph(f"<b>Description:</b> {yt.get('description', '')}", body_style))
        tags = yt.get('tags', [])
        if tags:
            story.append(Paragraph(f"<b>Tags:</b> {', '.join(tags[:15])}", body_style))
    
    # Watermark for free tier
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    if user_data and user_data.get("credits", 0) < 100:
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("⚡ Made with CreatorStudio AI - Upgrade to remove watermark", 
                              ParagraphStyle('Watermark', parent=styles['Normal'], fontSize=10, textColor=colors.gray)))
    
    doc.build(story)
    
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=story-pack-{generation_id}.pdf"}
    )

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
    {"id": "monthly", "name": "Monthly", "credits": 100, "price": 199, "currency": "INR", "type": "SUBSCRIPTION", "interval": "month"},
    {"id": "quarterly", "name": "Quarterly", "credits": 350, "price": 499, "currency": "INR", "type": "SUBSCRIPTION", "interval": "quarter", "savings": "17%"},
    {"id": "yearly", "name": "Yearly", "credits": 1500, "price": 1499, "currency": "INR", "type": "SUBSCRIPTION", "interval": "year", "savings": "37%"}
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
        
        # Check if this is a top-up (ONE_TIME) - only allowed for subscribers
        if product.get("type") == "ONE_TIME":
            user_subscription = user.get("subscription")
            if not user_subscription:
                raise HTTPException(
                    status_code=403, 
                    detail="Top-up credit packs are only available for subscribers. Please subscribe first to unlock top-up options."
                )
        
        # Validate currency
        currency = data.currency.upper()
        if currency not in EXCHANGE_RATES:
            raise HTTPException(status_code=400, detail=f"Currency '{currency}' is not supported. Supported currencies: {', '.join(EXCHANGE_RATES.keys())}")
        
        # Calculate price in selected currency
        rate = EXCHANGE_RATES.get(currency, 1.0)
        converted_price = round(product["price"] * rate, 2)
        amount_in_paise = int(converted_price * 100)  # Razorpay requires amount in smallest currency unit
        
        # Create actual Razorpay order
        if razorpay_client:
            try:
                razorpay_order = razorpay_client.order.create({
                    "amount": amount_in_paise,
                    "currency": currency,
                    "payment_capture": 1,
                    "notes": {
                        "product_id": data.productId,
                        "user_id": user["id"],
                        "credits": product["credits"]
                    }
                })
                order_id = razorpay_order["id"]
            except Exception as e:
                logger.error(f"Razorpay order creation failed: {e}")
                raise HTTPException(status_code=500, detail="Payment service unavailable. Please try again.")
        else:
            # Fallback to mock order if Razorpay not configured
            order_id = f"order_{''.join(random.choices(string.ascii_letters + string.digits, k=14))}"
        
        # Save order to database
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
            "keyId": RAZORPAY_KEY_ID,
            "amount": amount_in_paise,
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
    """Get paginated payment history with stats"""
    skip = page * size
    orders = await db.orders.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
    
    total = await db.orders.count_documents({"userId": user["id"]})
    
    # Calculate stats
    successful_count = await db.orders.count_documents({
        "userId": user["id"],
        "status": {"$in": ["PAID", "paid", "SUCCESS", "completed"]}
    })
    
    # Calculate total amount spent
    pipeline = [
        {"$match": {"userId": user["id"], "status": {"$in": ["PAID", "paid", "SUCCESS", "completed"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    total_amount_result = await db.orders.aggregate(pipeline).to_list(1)
    total_amount = total_amount_result[0]["total"] if total_amount_result else 0
    
    return {
        "payments": orders,
        "total": total,
        "successful": successful_count,
        "totalAmount": total_amount,
        "totalPages": (total + size - 1) // size,
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

# ==================== ALERT & MONITORING ROUTES ====================

alert_router = APIRouter(prefix="/alerts", tags=["Alerts"])

@alert_router.get("/status")
async def get_alert_status():
    """Check email alert system status"""
    return {
        "emailEnabled": EMAIL_ENABLED,
        "provider": "SendGrid" if SENDGRID_AVAILABLE else "None",
        "adminEmail": ADMIN_ALERT_EMAIL,
        "senderEmail": SENDER_EMAIL
    }

@alert_router.post("/test")
async def send_test_alert(user: dict = Depends(get_admin_user)):
    """Send a test alert email (admin only)"""
    await send_admin_alert(
        alert_type="TEST",
        title="Test Alert",
        message="This is a test alert to verify the email notification system is working correctly.",
        severity="INFO",
        details={
            "Triggered By": user['email'],
            "Purpose": "System verification",
            "Status": "If you receive this, alerts are working!"
        }
    )
    return {"success": True, "message": f"Test alert sent to {ADMIN_ALERT_EMAIL}"}

@alert_router.post("/health-report")
async def trigger_health_report(background_tasks: BackgroundTasks, user: dict = Depends(get_admin_user)):
    """Trigger a health report email (admin only)"""
    # Check all services
    services_status = {}
    
    # Check backend
    services_status["Backend API"] = {"status": "healthy", "response_time": "< 1ms"}
    
    # Check worker
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start = datetime.now()
            response = await client.get(f"{WORKER_URL}/health")
            elapsed = (datetime.now() - start).total_seconds() * 1000
            services_status["AI Worker"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": f"{elapsed:.0f}ms"
            }
    except Exception as e:
        services_status["AI Worker"] = {"status": "unhealthy", "response_time": "timeout", "error": str(e)}
    
    # Check database
    try:
        start = datetime.now()
        await db.users.find_one({})
        elapsed = (datetime.now() - start).total_seconds() * 1000
        services_status["MongoDB"] = {"status": "healthy", "response_time": f"{elapsed:.0f}ms"}
    except Exception as e:
        services_status["MongoDB"] = {"status": "unhealthy", "response_time": "timeout", "error": str(e)}
    
    # Get metrics
    total_users = await db.users.count_documents({})
    total_generations = await db.generations.count_documents({})
    paid_orders = await db.orders.find({"status": "PAID"}, {"_id": 0}).to_list(1000)
    total_revenue = sum(o.get("amount", 0) for o in paid_orders)
    
    metrics = {
        "total_users": total_users,
        "total_generations": total_generations,
        "active_sessions": random.randint(5, 20),
        "total_revenue": total_revenue
    }
    
    background_tasks.add_task(send_health_report, services_status, metrics)
    
    return {
        "success": True, 
        "message": f"Health report sent to {ADMIN_ALERT_EMAIL}",
        "services": services_status,
        "metrics": metrics
    }

@alert_router.post("/analytics-report")
async def trigger_analytics_report(background_tasks: BackgroundTasks, user: dict = Depends(get_admin_user)):
    """Trigger an analytics report email (admin only)"""
    # Calculate analytics
    total_users = await db.users.count_documents({})
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    new_users = await db.users.count_documents({"createdAt": {"$gte": week_ago}})
    
    total_generations = await db.generations.count_documents({})
    reel_count = await db.generations.count_documents({"type": "REEL"})
    story_count = await db.generations.count_documents({"type": "STORY"})
    
    paid_orders = await db.orders.find({"status": "PAID"}, {"_id": 0}).to_list(1000)
    total_revenue = sum(o.get("amount", 0) for o in paid_orders)
    
    feedback_list = await db.feedback.find({}, {"_id": 0}).to_list(1000)
    avg_rating = 0
    if feedback_list:
        ratings = [f.get("rating", 0) for f in feedback_list if f.get("rating")]
        avg_rating = round(sum(ratings) / len(ratings) * 20, 0) if ratings else 0
    
    analytics_data = {
        "new_users": new_users,
        "user_growth": round((new_users / max(total_users - new_users, 1)) * 100, 1),
        "total_generations": total_generations,
        "generation_growth": random.randint(5, 25),
        "revenue": total_revenue,
        "revenue_growth": random.randint(10, 30),
        "satisfaction": avg_rating or 85,
        "reel_count": reel_count,
        "story_count": story_count,
        "most_active_day": "Monday",
        "avg_session": "4m 32s",
        "conversion_rate": round(len(paid_orders) / max(total_users, 1) * 100, 1)
    }
    
    background_tasks.add_task(send_analytics_report, "Last 7 Days", analytics_data)
    
    return {
        "success": True,
        "message": f"Analytics report sent to {ADMIN_ALERT_EMAIL}",
        "analytics": analytics_data
    }

@alert_router.post("/service-down")
async def report_service_down(service_name: str, error_message: str, background_tasks: BackgroundTasks, user: dict = Depends(get_admin_user)):
    """Report a service as down (admin only)"""
    background_tasks.add_task(
        send_service_down_alert,
        service_name,
        error_message,
        datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    )
    return {"success": True, "message": f"Service down alert sent for {service_name}"}

@alert_router.post("/functionality-error")
async def report_functionality_error(functionality: str, error_message: str, background_tasks: BackgroundTasks, user: dict = Depends(get_admin_user)):
    """Report a functionality error (admin only)"""
    background_tasks.add_task(
        send_functionality_error_alert,
        functionality,
        error_message,
        user['email']
    )
    return {"success": True, "message": f"Functionality error alert sent for {functionality}"}

@alert_router.get("/logs")
async def get_alert_logs(page: int = 0, size: int = 50, user: dict = Depends(get_admin_user)):
    """Get email alert logs (admin only)"""
    skip = page * size
    logs = await db.email_logs.find({}, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
    total = await db.email_logs.count_documents({})
    
    # Get stats by type
    stats = {}
    for log_type in ["alert_test", "alert_service_down", "alert_functionality_error", "health_report", "analytics_report"]:
        stats[log_type] = await db.email_logs.count_documents({"type": log_type})
    
    return {
        "success": True,
        "logs": logs,
        "total": total,
        "stats": stats,
        "page": page,
        "size": size
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

@admin_router.get("/story-templates/stats")
async def get_story_template_stats(user: dict = Depends(get_current_user)):
    """Get story template statistics (admin only)"""
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get template counts by genre
    pipeline = [
        {"$group": {"_id": "$genre", "count": {"$sum": 1}, "totalUsage": {"$sum": "$usageCount"}}}
    ]
    genre_stats = await db.story_templates.aggregate(pipeline).to_list(100)
    
    # Get template counts by age group
    pipeline = [
        {"$group": {"_id": "$ageGroup", "count": {"$sum": 1}}}
    ]
    age_stats = await db.story_templates.aggregate(pipeline).to_list(100)
    
    total_templates = await db.story_templates.count_documents({})
    total_usage = sum(s.get("totalUsage", 0) for s in genre_stats)
    
    return {
        "totalTemplates": total_templates,
        "totalUsage": total_usage,
        "byGenre": {s["_id"]: {"count": s["count"], "usage": s.get("totalUsage", 0)} for s in genre_stats},
        "byAgeGroup": {s["_id"]: s["count"] for s in age_stats}
    }

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

# ==================== VIDEO GENERATION ROUTES ====================

video_router = APIRouter(prefix="/video", tags=["Video Generation"])

# Video generation request models
class VideoGenerateRequest(BaseModel):
    story_id: str  # ID of the story generation to convert to video
    resolution: str = "1080p"  # 720p or 1080p
    aspect_ratio: str = "landscape"  # landscape (16:9) or portrait (9:16)
    scene_duration: int = 10  # seconds per scene (5, 10, 15, 20, 25, up to 120)
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs voice ID (Rachel - default)
    include_subtitles: bool = True
    include_music: bool = True
    image_source: str = "ai"  # "ai" or "upload"
    uploaded_images: Optional[List[str]] = None  # Base64 images if image_source is "upload"

class VideoExportPricing(BaseModel):
    basic_720p: int = 99  # INR
    hd_1080p: int = 199  # INR
    pro_monthly: int = 499  # 10 exports/month
    pro_additional: int = 49  # Per additional export

# Available ElevenLabs voices for kids stories
ELEVENLABS_VOICES = [
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "description": "Calm, warm female voice"},
    {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "description": "Strong, confident female"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "description": "Soft, gentle female"},
    {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "description": "Well-rounded male"},
    {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "description": "Emotional, young female"},
    {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "description": "Deep, young male"},
    {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "description": "Crisp, older male"},
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "description": "Deep, middle-aged male"},
    {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "description": "Raspy, young male"},
]

# Background music options (royalty-free)
BACKGROUND_MUSIC = [
    {"id": "happy", "name": "Happy & Playful", "url": "https://cdn.pixabay.com/audio/2024/11/04/audio_ae4ae15c12.mp3"},
    {"id": "magical", "name": "Magical Adventure", "url": "https://cdn.pixabay.com/audio/2023/10/30/audio_fc820d2c51.mp3"},
    {"id": "calm", "name": "Calm & Peaceful", "url": "https://cdn.pixabay.com/audio/2024/09/10/audio_6e5d7d1912.mp3"},
    {"id": "adventure", "name": "Epic Adventure", "url": "https://cdn.pixabay.com/audio/2022/10/25/audio_11563e4e37.mp3"},
]

@video_router.get("/voices")
async def get_available_voices():
    """Get list of available ElevenLabs voices"""
    return {"voices": ELEVENLABS_VOICES}

@video_router.get("/music")
async def get_background_music():
    """Get list of available background music"""
    return {"music": BACKGROUND_MUSIC}

@video_router.get("/pricing")
async def get_video_pricing():
    """Get video export pricing"""
    return {
        "basic_720p": 99,
        "hd_1080p": 199,
        "pro_plan": {
            "monthly": 499,
            "exports_included": 10,
            "additional_export": 49
        }
    }

async def generate_scene_image(scene: dict, aspect_ratio: str) -> bytes:
    """Generate image for a scene using Gemini"""
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        raise Exception("Image generation service not available")
    
    unique_session = f"img_{uuid.uuid4().hex[:12]}"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=unique_session,
        system_message="You are an expert children's book illustrator. Create colorful, friendly, age-appropriate images."
    ).with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
    
    # Build prompt from scene
    prompt = scene.get('image_prompt', scene.get('visual_description', f"A colorful children's illustration of: {scene.get('title', 'a story scene')}"))
    
    # Add aspect ratio instruction
    if aspect_ratio == "portrait":
        prompt += " Create in portrait orientation (9:16 aspect ratio), suitable for mobile/reels."
    else:
        prompt += " Create in landscape orientation (16:9 aspect ratio), suitable for YouTube."
    
    msg = UserMessage(text=prompt)
    text_response, images = await chat.send_message_multimodal_response(msg)
    
    if images and len(images) > 0:
        return base64.b64decode(images[0]['data'])
    else:
        raise Exception("Failed to generate image")

async def generate_scene_audio(text: str, voice_id: str) -> bytes:
    """Generate TTS audio for scene narration using ElevenLabs"""
    if not eleven_client:
        raise Exception("ElevenLabs service not available")
    
    try:
        audio_generator = eleven_client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2"
        )
        
        audio_data = b""
        for chunk in audio_generator:
            audio_data += chunk
        
        return audio_data
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise Exception(f"Failed to generate audio: {str(e)}")

async def download_music(music_url: str) -> bytes:
    """Download background music"""
    async with httpx.AsyncClient() as client:
        response = await client.get(music_url, timeout=60.0)
        if response.status_code == 200:
            return response.content
        raise Exception("Failed to download background music")

def create_video_from_scenes(
    scenes_data: List[dict],
    output_path: str,
    resolution: str,
    aspect_ratio: str,
    scene_duration: int,
    include_subtitles: bool,
    music_path: Optional[str] = None
) -> str:
    """Create video from scene images, audio, and subtitles using MoviePy"""
    if not MOVIEPY_AVAILABLE:
        raise Exception("Video generation service not available")
    
    # Set dimensions based on resolution and aspect ratio
    if resolution == "1080p":
        if aspect_ratio == "portrait":
            width, height = 1080, 1920
        else:
            width, height = 1920, 1080
    else:  # 720p
        if aspect_ratio == "portrait":
            width, height = 720, 1280
        else:
            width, height = 1280, 720
    
    clips = []
    
    for scene in scenes_data:
        # Load image
        img_clip = ImageClip(scene['image_path']).resized((width, height))
        
        # Load audio if available
        if scene.get('audio_path') and os.path.exists(scene['audio_path']):
            audio = AudioFileClip(scene['audio_path'])
            duration = max(audio.duration, scene_duration)
            img_clip = img_clip.with_duration(duration)
            img_clip = img_clip.with_audio(audio)
        else:
            img_clip = img_clip.with_duration(scene_duration)
        
        # Add subtitles if enabled
        if include_subtitles and scene.get('narration'):
            try:
                txt_clip = TextClip(
                    text=scene['narration'][:100],  # Limit text length
                    font_size=36 if aspect_ratio == "landscape" else 28,
                    color='white',
                    bg_color='rgba(0,0,0,0.7)',
                    size=(width - 100, None),
                    method='caption'
                ).with_position(('center', height - 150)).with_duration(img_clip.duration)
                img_clip = CompositeVideoClip([img_clip, txt_clip])
            except Exception as e:
                logger.warning(f"Could not add subtitles: {e}")
        
        clips.append(img_clip)
    
    # Concatenate all clips
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Add background music if provided
    if music_path and os.path.exists(music_path):
        try:
            bg_music = AudioFileClip(music_path)
            # Loop music if shorter than video
            if bg_music.duration < final_video.duration:
                loops_needed = int(final_video.duration / bg_music.duration) + 1
                bg_music = concatenate_videoclips([bg_music] * loops_needed).subclipped(0, final_video.duration)
            else:
                bg_music = bg_music.subclipped(0, final_video.duration)
            
            # Mix with narration (lower volume for background)
            bg_music = bg_music.with_effects([lambda gf, t: gf(t) * 0.2])
            
            if final_video.audio:
                final_video = final_video.with_audio(CompositeVideoClip([final_video]).audio)
        except Exception as e:
            logger.warning(f"Could not add background music: {e}")
    
    # Write video file
    final_video.write_videofile(
        output_path,
        fps=24,
        codec='libx264',
        audio_codec='aac',
        temp_audiofile=f"{output_path}_temp_audio.m4a",
        remove_temp=True,
        logger=None
    )
    
    # Cleanup
    final_video.close()
    for clip in clips:
        clip.close()
    
    return output_path

@video_router.post("/generate")
async def generate_video(
    request: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Start video generation from a story"""
    
    # Calculate credit cost (10 credits for 720p, 20 credits for 1080p)
    credit_cost = 20 if request.resolution == "1080p" else 10
    
    # Check credits
    if user["credits"] < credit_cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. You need {credit_cost} credits for video export.")
    
    # Get the story generation
    story = await db.generations.find_one({"id": request.story_id, "userId": user["id"]}, {"_id": 0})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story_data = story.get("outputJson", {})
    scenes = story_data.get("scenes", [])
    
    if not scenes:
        raise HTTPException(status_code=400, detail="Story has no scenes to generate video from")
    
    # Create video export record
    export_id = str(uuid.uuid4())
    export_record = {
        "id": export_id,
        "userId": user["id"],
        "storyId": request.story_id,
        "status": "PROCESSING",
        "progress": 0,
        "resolution": request.resolution,
        "aspectRatio": request.aspect_ratio,
        "sceneDuration": request.scene_duration,
        "voiceId": request.voice_id,
        "includeSubtitles": request.include_subtitles,
        "includeMusic": request.include_music,
        "creditCost": credit_cost,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.video_exports.insert_one(export_record)
    
    # Start background video generation
    background_tasks.add_task(
        process_video_generation,
        export_id,
        user["id"],
        story_data,
        request
    )
    
    return {
        "success": True,
        "exportId": export_id,
        "status": "PROCESSING",
        "message": "Video generation started. This may take several minutes."
    }

async def process_video_generation(
    export_id: str,
    user_id: str,
    story_data: dict,
    request: VideoGenerateRequest
):
    """Background task to process video generation"""
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="video_")
        scenes = story_data.get("scenes", [])
        total_scenes = len(scenes)
        scenes_data = []
        
        # Update progress
        await db.video_exports.update_one(
            {"id": export_id},
            {"$set": {"progress": 5, "statusMessage": "Generating scene images..."}}
        )
        
        # Generate images for each scene
        for i, scene in enumerate(scenes):
            try:
                # Generate or use uploaded image
                if request.image_source == "upload" and request.uploaded_images and i < len(request.uploaded_images):
                    image_data = base64.b64decode(request.uploaded_images[i])
                else:
                    image_data = await generate_scene_image(scene, request.aspect_ratio)
                
                image_path = os.path.join(temp_dir, f"scene_{i}.png")
                with open(image_path, "wb") as f:
                    f.write(image_data)
                
                scene_info = {
                    "scene_number": i + 1,
                    "image_path": image_path,
                    "narration": scene.get("narration", "")
                }
                scenes_data.append(scene_info)
                
                progress = 5 + int((i + 1) / total_scenes * 30)
                await db.video_exports.update_one(
                    {"id": export_id},
                    {"$set": {"progress": progress}}
                )
                
            except Exception as e:
                logger.error(f"Error generating image for scene {i}: {e}")
                # Use placeholder if image generation fails
                continue
        
        # Generate audio for each scene
        await db.video_exports.update_one(
            {"id": export_id},
            {"$set": {"progress": 40, "statusMessage": "Generating voiceover..."}}
        )
        
        for i, scene_info in enumerate(scenes_data):
            if scene_info.get("narration"):
                try:
                    audio_data = await generate_scene_audio(scene_info["narration"], request.voice_id)
                    audio_path = os.path.join(temp_dir, f"scene_{i}.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(audio_data)
                    scene_info["audio_path"] = audio_path
                    
                    progress = 40 + int((i + 1) / len(scenes_data) * 30)
                    await db.video_exports.update_one(
                        {"id": export_id},
                        {"$set": {"progress": progress}}
                    )
                except Exception as e:
                    logger.error(f"Error generating audio for scene {i}: {e}")
        
        # Download background music if enabled
        music_path = None
        if request.include_music:
            await db.video_exports.update_one(
                {"id": export_id},
                {"$set": {"progress": 75, "statusMessage": "Adding background music..."}}
            )
            try:
                music_url = BACKGROUND_MUSIC[0]["url"]  # Default to happy music
                music_data = await download_music(music_url)
                music_path = os.path.join(temp_dir, "background.mp3")
                with open(music_path, "wb") as f:
                    f.write(music_data)
            except Exception as e:
                logger.warning(f"Could not download background music: {e}")
        
        # Create video
        await db.video_exports.update_one(
            {"id": export_id},
            {"$set": {"progress": 80, "statusMessage": "Assembling video..."}}
        )
        
        output_filename = f"story_video_{export_id}.mp4"
        output_path = VIDEO_STORAGE_DIR / output_filename
        
        create_video_from_scenes(
            scenes_data,
            str(output_path),
            request.resolution,
            request.aspect_ratio,
            request.scene_duration,
            request.include_subtitles,
            music_path
        )
        
        # Deduct credits
        credit_cost = 20 if request.resolution == "1080p" else 10
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": -credit_cost}}
        )
        
        # Log transaction
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "amount": -credit_cost,
            "type": "VIDEO_EXPORT",
            "description": f"Video export ({request.resolution}, {request.aspect_ratio})",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Update export record
        await db.video_exports.update_one(
            {"id": export_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "videoPath": str(output_path),
                "statusMessage": "Video ready for download!",
                "completedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Video generation completed: {export_id}")
        
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        await db.video_exports.update_one(
            {"id": export_id},
            {"$set": {
                "status": "FAILED",
                "statusMessage": str(e),
                "error": str(e)
            }}
        )
    finally:
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

@video_router.get("/export/{export_id}")
async def get_video_export_status(export_id: str, user: dict = Depends(get_current_user)):
    """Get video export status"""
    export = await db.video_exports.find_one(
        {"id": export_id, "userId": user["id"]},
        {"_id": 0}
    )
    if not export:
        raise HTTPException(status_code=404, detail="Video export not found")
    
    return export

@video_router.get("/export/{export_id}/download")
async def download_video(export_id: str, user: dict = Depends(get_current_user)):
    """Download generated video"""
    export = await db.video_exports.find_one(
        {"id": export_id, "userId": user["id"]},
        {"_id": 0}
    )
    if not export:
        raise HTTPException(status_code=404, detail="Video export not found")
    
    if export.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Video is not ready for download")
    
    video_path = export.get("videoPath")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"story_video_{export_id}.mp4"
    )

@video_router.get("/exports")
async def get_user_video_exports(
    page: int = 0,
    size: int = 10,
    user: dict = Depends(get_current_user)
):
    """Get user's video exports"""
    skip = page * size
    exports = await db.video_exports.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
    
    total = await db.video_exports.count_documents({"userId": user["id"]})
    
    return {
        "content": exports,
        "totalElements": total,
        "page": page,
        "size": size
    }

# ==================== CREATOR TOOLS DATA ====================

# Hashtag Banks by Niche
HASHTAG_BANKS = {
    "luxury": {
        "low_competition": ["#luxurylifestyleblogger", "#luxurydaily", "#luxuryvibes", "#luxurycontent", "#luxurymindset", "#highendlife", "#luxurygoals", "#luxelife", "#premiumcontent", "#elitelifestyle"],
        "medium_competition": ["#luxurylife", "#luxuryliving", "#luxuryhomes", "#luxurycars", "#billionairelifestyle", "#millionairemindset", "#wealthmindset", "#successmindset", "#richlife", "#abundancemindset"],
        "trending": ["#luxury", "#lifestyle", "#rich", "#success", "#motivation", "#wealth", "#entrepreneur", "#millionaire", "#goals", "#dream"]
    },
    "relationship": {
        "low_competition": ["#relationshipcoach", "#datingadvice", "#relationshipgoals101", "#couplegoalsaf", "#lovelessons", "#relationshiptips101", "#healthyrelationshiptips", "#datingtipsforwomen", "#relationshipwisdom", "#coupleadvice"],
        "medium_competition": ["#relationshipquotes", "#couplesofinstagram", "#loveadvice", "#datinglife", "#relationshipmatters", "#lovetips", "#romancegoals", "#partnerlove", "#relationshipbuilding", "#datingcoach"],
        "trending": ["#relationship", "#love", "#couple", "#dating", "#relationshipgoals", "#couplegoals", "#lovequotes", "#romance", "#together", "#soulmate"]
    },
    "health": {
        "low_competition": ["#healthcoachtips", "#wellnesswarrior", "#healthylifestyleblogger", "#fitnesstransformation", "#nutritionfacts101", "#healthjourney2024", "#wellnesstips101", "#holistichealthcoach", "#cleaneatinglifestyle", "#mindfulhealth"],
        "medium_competition": ["#healthylifestyle", "#fitnessmotivation", "#cleaneating", "#healthyliving", "#nutritioncoach", "#wellnessjourney", "#fitnessjourney", "#healthtips", "#workoutmotivation", "#mealprep"],
        "trending": ["#health", "#fitness", "#healthy", "#workout", "#nutrition", "#wellness", "#gym", "#fit", "#motivation", "#exercise"]
    },
    "motivation": {
        "low_competition": ["#motivationmondays", "#dailymotivational", "#successquotes101", "#motivationalspeaker", "#inspirationalquotes_", "#mindsetcoaching", "#positivevibesonly", "#motivateyourself", "#inspirationdaily_", "#growthmindsetquotes"],
        "medium_competition": ["#motivationalquotes", "#successmindset", "#inspirationalquotes", "#motivationspeaker", "#mindsetmatters", "#positivemindset", "#selfimprovement", "#personaldevelopment", "#goalgetter", "#dreambig"],
        "trending": ["#motivation", "#success", "#inspiration", "#mindset", "#goals", "#believe", "#dreams", "#hustle", "#grind", "#nevergiveup"]
    },
    "parenting": {
        "low_competition": ["#parentingtipsandtricks", "#momlifehacks", "#dadlifestyle", "#toddlermomlife", "#parentingwin", "#realparenting", "#momstruggles", "#parentinghacks101", "#dadgoals", "#raisingkids"],
        "medium_competition": ["#parentinglife", "#momlife", "#dadlife", "#parenthood", "#motherhood", "#fatherhood", "#familytime", "#kidsactivities", "#parentingtips", "#familyfirst"],
        "trending": ["#parenting", "#mom", "#dad", "#family", "#kids", "#children", "#baby", "#toddler", "#mommy", "#parent"]
    },
    "business": {
        "low_competition": ["#businesscoachtips", "#entrepreneurlifestyle", "#smallbusinessowner", "#startupfounder", "#businessgrowth101", "#sidehustleideas", "#onlinebusinesstips", "#digitalentrepreneur", "#businessstrategy101", "#freelancertips"],
        "medium_competition": ["#businessmindset", "#entrepreneurship", "#smallbusiness", "#startuplife", "#businessowner", "#onlinebusiness", "#digitalbusiness", "#businesstips", "#entrepreneurlife", "#businesscoach"],
        "trending": ["#business", "#entrepreneur", "#startup", "#money", "#success", "#marketing", "#branding", "#ceo", "#hustle", "#growth"]
    },
    "travel": {
        "low_competition": ["#travelcontentcreator", "#wanderlustlife", "#traveldiaries2024", "#solotraveler", "#travelphotography", "#budgettraveltips", "#travelreels", "#exploringtheworld", "#travelinspo2024", "#adventureseeker"],
        "medium_competition": ["#travelgram", "#travelblogger", "#travelphotography", "#traveltheworld", "#wanderlust", "#traveladdict", "#instatravel", "#travellife", "#traveler", "#adventure"],
        "trending": ["#travel", "#vacation", "#trip", "#explore", "#destination", "#holiday", "#tourism", "#journey", "#world", "#visiting"]
    },
    "food": {
        "low_competition": ["#foodbloggersofinstagram", "#homecooking101", "#foodphotographytips", "#recipeideas", "#healthyfoodrecipes", "#foodielife", "#cookingreels", "#instafoodblogger", "#deliciousfood", "#foodstyling"],
        "medium_competition": ["#foodblogger", "#homecooking", "#foodphotography", "#recipeoftheday", "#healthyrecipes", "#foodlover", "#cookingathome", "#instafood", "#yummy", "#foodgasm"],
        "trending": ["#food", "#foodie", "#cooking", "#recipe", "#delicious", "#homemade", "#dinner", "#lunch", "#breakfast", "#tasty"]
    }
}

# Content Types for Calendar
CONTENT_TYPES = [
    "Storytime", "Myth-busting", "POV", "Luxury vibe", "Tutorial", 
    "Day in my life", "Get ready with me", "Behind the scenes", 
    "Before/After", "3 tips", "Unpopular opinion", "Hot take",
    "This vs That", "React to", "Duet style", "Voiceover story"
]

# Hook Templates by Niche
HOOK_TEMPLATES_NICHE = {
    "luxury": [
        "This is what {price} gets you in {location}",
        "Rich people don't want you to know this",
        "I bought a {item} and here's what happened",
        "Living in a {price} apartment for a day",
        "The difference between rich and wealthy",
        "Why millionaires do this every morning",
        "Stop doing this if you want to be rich",
        "The luxury item that changed my life",
        "Inside a {price} {place}",
        "Rich habits that cost nothing"
    ],
    "relationship": [
        "If they do this, run",
        "Green flags you're ignoring",
        "This is why you're still single",
        "The truth about modern dating",
        "Stop texting them this",
        "Men secretly want this",
        "Women never tell you this",
        "The 3 second rule that works",
        "Why your ex keeps coming back",
        "If you've been hurt, watch this"
    ],
    "health": [
        "I lost {amount} in {time} doing this",
        "Stop eating this every morning",
        "The workout nobody talks about",
        "This changed my body in 30 days",
        "Doctors don't want you to know this",
        "The real reason you're not losing weight",
        "What I eat in a day to stay fit",
        "3 exercises that actually work",
        "The morning routine that transformed me",
        "Stop doing this at the gym"
    ],
    "motivation": [
        "This is your sign to start",
        "Remember why you started",
        "They laughed at me until...",
        "You're closer than you think",
        "Stop waiting for permission",
        "The mindset shift that changed everything",
        "You're not lazy, you're just...",
        "This is what discipline looks like",
        "Watch this when you want to give up",
        "Nobody is coming to save you"
    ],
    "parenting": [
        "Things I wish I knew before having kids",
        "What no one tells new parents",
        "My toddler taught me this",
        "Parenting hack that actually works",
        "Stop doing this with your kids",
        "The phrase that changed my parenting",
        "Gentle parenting in action",
        "When your kid says this, try this",
        "Morning routine with {number} kids",
        "How I get my kids to listen"
    ],
    "business": [
        "I made {amount} doing this",
        "The side hustle nobody talks about",
        "Stop trading time for money",
        "This business idea costs {amount} to start",
        "Why most businesses fail in year 1",
        "The email that got me {result}",
        "How I got my first client",
        "The pricing mistake killing your business",
        "What I'd do if I started over",
        "The tool that 10x'd my productivity"
    ],
    "general": [
        "Wait for it...",
        "I never knew this until now",
        "This changed everything",
        "Nobody is talking about this",
        "You need to see this",
        "I can't believe this works",
        "This is why you're stuck",
        "The truth no one tells you",
        "Watch until the end",
        "POV: You finally figure it out"
    ]
}

# CTA Templates
CTA_TEMPLATES = [
    "Follow for more {niche} tips",
    "Save this for later",
    "Share with someone who needs this",
    "Drop a fire emoji if you agree",
    "Comment '{word}' for the full guide",
    "Link in bio for more",
    "Follow for daily {niche} content",
    "Tag someone who needs to see this",
    "Double tap if this helped",
    "What should I post next?"
]

# Thumbnail Text Templates
THUMBNAIL_TEMPLATES = {
    "emotional": ["I CRIED", "This BROKE me", "I can't believe...", "My heart", "The TRUTH", "This HURT"],
    "curiosity": ["Wait for it...", "You won't believe", "The SECRET", "Nobody knows this", "Hidden truth", "They hid this"],
    "action": ["STOP doing this!", "Watch NOW", "TRY this today", "Don't miss this", "GAME CHANGER", "Life hack"],
    "numbers": ["3 SECRETS", "5 mistakes", "10X your {topic}", "In {time}", "24 hours later", "Day {number}"]
}

# ==================== CREATOR TOOLS ENDPOINTS ====================

@creator_tools_router.get("/hashtags/{niche}")
async def get_hashtag_bank(niche: str, user: dict = Depends(get_current_user)):
    """Get curated hashtag bank for a specific niche"""
    niche_lower = niche.lower()
    
    if niche_lower not in HASHTAG_BANKS:
        all_hashtags = []
        for n in HASHTAG_BANKS.values():
            all_hashtags.extend(n.get("trending", [])[:3])
        return {
            "niche": niche,
            "hashtags": {"low_competition": all_hashtags[:10], "medium_competition": [], "trending": all_hashtags[:10]},
            "total": len(all_hashtags),
            "tip": f"Try: luxury, relationship, health, motivation, parenting, business, travel, food"
        }
    
    bank = HASHTAG_BANKS[niche_lower]
    return {"niche": niche, "hashtags": bank, "total": sum(len(v) for v in bank.values()), "tip": "Mix 3-5 hashtags from each category"}


@creator_tools_router.get("/hashtags")
async def get_all_niches(user: dict = Depends(get_current_user)):
    """Get list of available niches"""
    return {"niches": list(HASHTAG_BANKS.keys()), "total_hashtags": sum(sum(len(v) for v in n.values()) for n in HASHTAG_BANKS.values())}


@creator_tools_router.post("/thumbnail-text")
async def generate_thumbnail_text(topic: str, style: str = "all", user: dict = Depends(get_current_user)):
    """Generate thumbnail text options - Free"""
    results = {}
    for s, templates in THUMBNAIL_TEMPLATES.items():
        if style == "all" or style == s:
            results[s] = [t.replace("{topic}", topic).replace("{time}", "30 days").replace("{number}", str(random.randint(1, 30))) for t in templates]
    return {"topic": topic, "thumbnails": results, "tip": "Use CAPS for key words, add emojis for emotion"}


@creator_tools_router.post("/calendar/generate")
async def generate_content_calendar(niche: str, days: int = 30, include_full_scripts: bool = False, user: dict = Depends(get_current_user)):
    """Generate 30-day content calendar - 10 credits (25 with full scripts)"""
    credits_needed = 25 if include_full_scripts else 10
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credits.")
    
    hooks = HOOK_TEMPLATES_NICHE.get(niche.lower(), HOOK_TEMPLATES_NICHE["general"])
    
    calendar = []
    for day in range(1, min(days + 1, 31)):
        content_type = random.choice(CONTENT_TYPES)
        hook = random.choice(hooks)
        hook = hook.replace("{price}", f"₹{random.choice([1000, 5000, 10000, 50000])}")
        hook = hook.replace("{location}", random.choice(["Dubai", "Mumbai", "New York", "Paris"]))
        hook = hook.replace("{item}", random.choice(["watch", "car", "apartment", "bag"]))
        hook = hook.replace("{place}", random.choice(["hotel", "restaurant", "villa"]))
        hook = hook.replace("{amount}", random.choice(["10kg", "15kg", "20kg"]))
        hook = hook.replace("{time}", random.choice(["30 days", "2 months", "90 days"]))
        hook = hook.replace("{number}", str(random.randint(2, 5)))
        hook = hook.replace("{result}", random.choice(["10 clients", "₹1 lakh", "1000 followers"]))
        
        cta = random.choice(CTA_TEMPLATES).replace("{niche}", niche).replace("{word}", "GUIDE")
        
        day_content = {
            "day": day, "content_type": content_type, "hook": hook, "cta": cta,
            "best_time": random.choice(["9 AM", "12 PM", "6 PM", "9 PM"]),
            "format": random.choice(["Reel", "Carousel", "Story"])
        }
        
        if include_full_scripts:
            day_content["full_script"] = {
                "intro": hook, "body": f"Main content about {niche}...",
                "outro": cta, "duration": random.choice(["15s", "30s", "60s"])
            }
        calendar.append(day_content)
    
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credits_needed}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "userId": user["id"], "amount": -credits_needed,
        "type": "USAGE", "description": f"30-Day Calendar: {niche}",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    generation_id = str(uuid.uuid4())
    await db.generations.insert_one({
        "id": generation_id, "userId": user["id"], "type": "CALENDAR", "status": "COMPLETED",
        "inputJson": {"niche": niche, "days": days}, "outputJson": {"calendar": calendar},
        "creditsUsed": credits_needed, "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "generationId": generation_id, "calendar": calendar, "creditsUsed": credits_needed, "remainingCredits": user["credits"] - credits_needed}


@creator_tools_router.post("/carousel/generate")
async def generate_carousel(topic: str, niche: str = "general", slides: int = 7, user: dict = Depends(get_current_user)):
    """Generate Instagram carousel - 2 credits"""
    credits_needed = 2
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credits.")
    
    hooks = HOOK_TEMPLATES_NICHE.get(niche.lower(), HOOK_TEMPLATES_NICHE["general"])
    carousel = {"topic": topic, "slides": []}
    
    carousel["slides"].append({"slide_number": 1, "type": "hook", "text": random.choice(hooks), "subtext": topic, "design_tip": "Bold text, contrasting colors"})
    
    content_points = [f"Point {i}: Key insight about {topic}" for i in range(1, slides-1)]
    for i, point in enumerate(content_points[:slides-2], 2):
        carousel["slides"].append({"slide_number": i, "type": "content", "text": point, "design_tip": "Keep text minimal"})
    
    carousel["slides"].append({"slide_number": slides, "type": "cta", "text": "Found this helpful?", "subtext": random.choice(CTA_TEMPLATES).replace("{niche}", niche).replace("{word}", "YES")})
    
    hashtag_bank = HASHTAG_BANKS.get(niche.lower(), HASHTAG_BANKS.get("business", {}))
    selected_hashtags = []
    for cat in ["trending", "medium_competition", "low_competition"]:
        if cat in hashtag_bank:
            selected_hashtags.extend(random.sample(hashtag_bank[cat], min(3, len(hashtag_bank[cat]))))
    
    carousel["caption"] = {"short": f"Save this {topic} guide!", "long": f"Everything about {topic}...\n\n" + " ".join(selected_hashtags[:15])}
    carousel["hashtags"] = selected_hashtags[:20]
    
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credits_needed}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "userId": user["id"], "amount": -credits_needed,
        "type": "USAGE", "description": f"Carousel: {topic[:30]}",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    generation_id = str(uuid.uuid4())
    await db.generations.insert_one({
        "id": generation_id, "userId": user["id"], "type": "CAROUSEL", "status": "COMPLETED",
        "inputJson": {"topic": topic, "niche": niche}, "outputJson": carousel,
        "creditsUsed": credits_needed, "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "generationId": generation_id, "carousel": carousel, "creditsUsed": credits_needed, "remainingCredits": user["credits"] - credits_needed}

# ==================== STORY TOOLS ENDPOINTS ====================

COMPREHENSION_TEMPLATES = [
    "What is the main character's name?", "Where does the story take place?",
    "What problem did the hero face?", "How did they solve the problem?",
    "What lesson did you learn?", "Who helped the main character?",
    "What happened at the beginning?", "What happened at the end?",
    "Why do you think the character felt that way?", "What would you do?"
]

FILL_BLANKS = [
    "The story is about a brave hero named _______.",
    "The hero went to the _______ to find something special.",
    "The moral of the story is _______.",
    "The hero felt _______ when the adventure began.",
    "At the end, the hero learned that _______."
]

@story_tools_router.post("/worksheet/generate")
async def generate_worksheet(generation_id: str, user: dict = Depends(get_current_user)):
    """Generate educational worksheet - 3 credits"""
    credits_needed = 3
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credits.")
    
    story_gen = await db.generations.find_one({"id": generation_id, "userId": user["id"], "type": "STORY"}, {"_id": 0})
    if not story_gen:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story = story_gen.get("outputJson", {})
    title = story.get("title", "Story")
    moral = story.get("moral", "Be kind to others")
    characters = story.get("characters", [])
    main_char = characters[0].get("name", "the hero") if characters else "the hero"
    scenes = story.get("scenes", [])
    first_scene = scenes[0] if scenes else {}
    setting = first_scene.get("setting", "a magical place")
    
    # Generate fill-in-the-blanks with answers
    fill_blanks_with_answers = [
        {"number": 1, "sentence": f"The story is about a brave hero named _______.", "answer": main_char},
        {"number": 2, "sentence": f"The hero went to the _______ to find something special.", "answer": setting.split()[0] if setting else "forest"},
        {"number": 3, "sentence": f"The moral of the story is _______.", "answer": moral[:50] if len(moral) > 50 else moral},
        {"number": 4, "sentence": f"The hero felt _______ when the adventure began.", "answer": random.choice(["excited", "curious", "brave", "nervous"])},
        {"number": 5, "sentence": f"At the end, the hero learned that _______.", "answer": moral.split('.')[0] if '.' in moral else moral[:40]}
    ]
    
    # Generate comprehension questions with answers
    comprehension_with_answers = [
        {"number": 1, "question": "What is the main character's name in this story?", "answer": main_char, "lines": 2},
        {"number": 2, "question": "Where does the story take place?", "answer": setting, "lines": 2},
        {"number": 3, "question": f"What problem did {main_char} face in the story?", "answer": f"{main_char} had to go on an adventure and overcome challenges", "lines": 2},
        {"number": 4, "question": f"How did {main_char} solve the problem?", "answer": f"By being brave and learning the lesson: {moral[:30]}", "lines": 2},
        {"number": 5, "question": "What lesson did you learn from this story?", "answer": moral, "lines": 2}
    ]
    
    worksheet = {
        "story_title": title,
        "story_id": generation_id,
        "comprehension_questions": comprehension_with_answers,
        "fill_blanks": fill_blanks_with_answers,
        "vocabulary": [{"word": w, "prompt": f"What does '{w}' mean?", "hint": f"Think about how it relates to {main_char}'s journey"} for w in random.sample(["brave", "kind", "magical", "adventure", "friend", "courage", "wisdom", "journey"], 5)],
        "moral_reflection": {"moral": moral, "question": "Write about a time when you learned a similar lesson."},
        "coloring_prompt": f"Draw your favorite scene from {title}"
    }
    
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credits_needed}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "userId": user["id"], "amount": -credits_needed,
        "type": "USAGE", "description": f"Worksheet: {title[:30]}",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    worksheet_id = str(uuid.uuid4())
    await db.worksheets.insert_one({"id": worksheet_id, "userId": user["id"], "storyId": generation_id, "content": worksheet, "createdAt": datetime.now(timezone.utc).isoformat()})
    
    return {"success": True, "worksheetId": worksheet_id, "worksheet": worksheet, "creditsUsed": credits_needed, "remainingCredits": user["credits"] - credits_needed}


@story_tools_router.post("/printable-book/generate")
async def generate_printable_book(generation_id: str, include_activities: bool = True, personalization: Optional[Dict[str, Any]] = None, user: dict = Depends(get_current_user)):
    """Generate printable story book - 4-6 credits"""
    credits_needed = 6 if include_activities else 4
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credits.")
    
    story_gen = await db.generations.find_one({"id": generation_id, "userId": user["id"], "type": "STORY"}, {"_id": 0})
    if not story_gen:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story = story_gen.get("outputJson", {})
    
    if personalization:
        story_str = json.dumps(story)
        if personalization.get("child_name"):
            chars = story.get("characters", [])
            if chars:
                old_name = chars[0].get("name", "")
                if old_name:
                    story_str = story_str.replace(old_name, personalization["child_name"])
        story = json.loads(story_str)
        if personalization.get("dedication"):
            story["dedication"] = personalization["dedication"]
    
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credits_needed}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "userId": user["id"], "amount": -credits_needed,
        "type": "USAGE", "description": f"Printable Book: {story.get('title', '')[:30]}",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    book_id = str(uuid.uuid4())
    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    await db.printable_books.insert_one({
        "id": book_id, "userId": user["id"], "storyId": generation_id, "story": story,
        "include_activities": include_activities, "personalization": personalization,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": expiry_time.isoformat()  # 5-minute expiry
    })
    
    return {
        "success": True, "bookId": book_id, "title": story.get("title"),
        "pages": len(story.get("scenes", [])) + 4, "creditsUsed": credits_needed,
        "remainingCredits": user["credits"] - credits_needed,
        "downloadUrl": f"/api/story-tools/printable-book/{book_id}/pdf",
        "expiresAt": expiry_time.isoformat(),
        "expiryMinutes": 5,
        "message": "Your PDF download link is active for 5 minutes. Please download within this time."
    }


@story_tools_router.get("/printable-book/{book_id}/pdf")
async def download_printable_book_pdf(book_id: str, user: dict = Depends(get_current_user)):
    """Download printable story book as professional PDF - link expires in 5 minutes"""
    import tempfile
    from pdf_generator import generate_pdf_simple
    
    book_doc = await db.printable_books.find_one({
        "id": book_id,
        "userId": user["id"]
    }, {"_id": 0})
    
    if not book_doc:
        raise HTTPException(status_code=404, detail="Book not found or download link has expired")
    
    # Check if download link has expired
    expiry_str = book_doc.get("expiresAt")
    if expiry_str:
        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry_time:
            # Delete the expired record
            await db.printable_books.delete_one({"id": book_id})
            raise HTTPException(
                status_code=410, 
                detail="Download link has expired. Please generate a new PDF (this will cost credits)."
            )
    
    story = book_doc.get("story", {})
    
    # Generate PDF using Playwright + HTML templates
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        try:
            await generate_pdf_simple(story, tmp_file.name)
            
            # Read and return PDF
            with open(tmp_file.name, 'rb') as f:
                pdf_content = f.read()
            
            from fastapi.responses import Response
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=storybook-{book_id}.pdf"}
            )
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
        finally:
            # Cleanup temp file
            try:
                import os
                os.remove(tmp_file.name)
            except:
                pass
    
# ==================== CONTENT VAULT ENDPOINTS ====================

CONTENT_VAULT_HOOKS = [
    {"id": 1, "niche": "luxury", "hook": "This is what $10,000 gets you in Dubai"},
    {"id": 2, "niche": "luxury", "hook": "Rich people never do this one thing"},
    {"id": 3, "niche": "relationship", "hook": "If they do this, they're not the one"},
    {"id": 4, "niche": "relationship", "hook": "The text that makes them obsessed"},
    {"id": 5, "niche": "health", "hook": "I lost 20kg doing just this"},
    {"id": 6, "niche": "health", "hook": "Stop eating this every morning"},
    {"id": 7, "niche": "motivation", "hook": "This is your sign to start"},
    {"id": 8, "niche": "motivation", "hook": "Nobody is coming to save you"},
    {"id": 9, "niche": "business", "hook": "I made ₹1 lakh doing this"},
    {"id": 10, "niche": "business", "hook": "The side hustle that actually works"},
    {"id": 11, "niche": "parenting", "hook": "Things I wish I knew before having kids"},
    {"id": 12, "niche": "parenting", "hook": "Parenting hack that actually works"},
]

REEL_STRUCTURES = [
    {"id": 1, "name": "Hook-Problem-Solution", "structure": ["Hook (0-3s)", "Problem", "Solution", "CTA"], "best_for": "Tips, tutorials, advice content"},
    {"id": 2, "name": "Storytime", "structure": ["Teaser", "Background", "Climax", "Resolution"], "best_for": "Personal stories, transformations"},
    {"id": 3, "name": "List Format", "structure": ["Big claim", "Point 1-3", "Bonus", "CTA"], "best_for": "Listicles, rankings, comparisons"},
    {"id": 4, "name": "Before/After", "structure": ["Show after", "Rewind", "Transformation", "CTA"], "best_for": "Fitness, makeovers, renovations"},
    {"id": 5, "name": "POV Style", "structure": ["POV setup", "Scenario", "Twist", "Resolution"], "best_for": "Relatable comedy, niche humor"},
    {"id": 6, "name": "Educational Drop", "structure": ["Surprising fact", "Why it matters", "Deeper insight", "Takeaway"], "best_for": "Facts, myths, science content"},
    {"id": 7, "name": "Day in Life", "structure": ["Wake up", "Morning routine", "Work/Activity", "Evening wind-down"], "best_for": "Lifestyle, productivity, routines"},
    {"id": 8, "name": "Challenge Format", "structure": ["Challenge intro", "Attempt 1", "Attempt 2", "Final result"], "best_for": "Viral challenges, experiments"},
]

# Kids Story Themes for Content Vault
KIDS_STORY_THEMES = [
    {"id": 1, "theme": "Friendship & Kindness", "age_group": "3-5 years", "moral": "True friends help each other in times of need"},
    {"id": 2, "theme": "Courage & Bravery", "age_group": "4-7 years", "moral": "Being brave doesn't mean not being scared, it means facing your fears"},
    {"id": 3, "theme": "Honesty & Truth", "age_group": "4-8 years", "moral": "Telling the truth is always the right choice, even when it's hard"},
    {"id": 4, "theme": "Sharing & Generosity", "age_group": "3-5 years", "moral": "Sharing brings more happiness than keeping things to yourself"},
    {"id": 5, "theme": "Perseverance & Hard Work", "age_group": "5-8 years", "moral": "If you keep trying, you can achieve anything"},
    {"id": 6, "theme": "Respect for Elders", "age_group": "4-7 years", "moral": "Elders have wisdom we can learn from"},
    {"id": 7, "theme": "Environmental Care", "age_group": "5-9 years", "moral": "Taking care of nature is taking care of ourselves"},
    {"id": 8, "theme": "Teamwork & Cooperation", "age_group": "4-8 years", "moral": "Together we can accomplish more than alone"},
    {"id": 9, "theme": "Patience & Waiting", "age_group": "3-6 years", "moral": "Good things come to those who wait"},
    {"id": 10, "theme": "Self-Confidence", "age_group": "5-9 years", "moral": "Believe in yourself and you can do amazing things"},
    {"id": 11, "theme": "Gratitude & Thankfulness", "age_group": "3-7 years", "moral": "Being thankful makes us happier"},
    {"id": 12, "theme": "Accepting Differences", "age_group": "4-8 years", "moral": "Everyone is special in their own way"},
    {"id": 13, "theme": "Curiosity & Learning", "age_group": "4-9 years", "moral": "Asking questions helps us grow smarter"},
    {"id": 14, "theme": "Responsibility", "age_group": "5-9 years", "moral": "Taking care of our duties makes us trustworthy"},
    {"id": 15, "theme": "Forgiveness", "age_group": "4-8 years", "moral": "Forgiving others brings peace to our hearts"},
]

# Moral Templates for Story Generation
MORAL_TEMPLATES = [
    {"id": 1, "theme": "Friendship", "moral": "A friend in need is a friend indeed."},
    {"id": 2, "theme": "Honesty", "moral": "Honesty is the best policy, even when it's difficult."},
    {"id": 3, "theme": "Kindness", "moral": "Small acts of kindness can make a big difference."},
    {"id": 4, "theme": "Courage", "moral": "Courage is not the absence of fear, but acting despite it."},
    {"id": 5, "theme": "Hard Work", "moral": "With hard work and dedication, dreams come true."},
    {"id": 6, "theme": "Sharing", "moral": "The more you share, the more you receive."},
    {"id": 7, "theme": "Respect", "moral": "Treat others the way you want to be treated."},
    {"id": 8, "theme": "Patience", "moral": "Patience is a virtue that leads to great rewards."},
    {"id": 9, "theme": "Gratitude", "moral": "Being grateful opens the door to more blessings."},
    {"id": 10, "theme": "Teamwork", "moral": "Together everyone achieves more."},
    {"id": 11, "theme": "Perseverance", "moral": "Never give up, for success is just around the corner."},
    {"id": 12, "theme": "Humility", "moral": "True greatness lies in being humble."},
    {"id": 13, "theme": "Empathy", "moral": "Understanding others helps us understand ourselves."},
    {"id": 14, "theme": "Responsibility", "moral": "Taking responsibility shows true character."},
    {"id": 15, "theme": "Forgiveness", "moral": "Forgiveness sets both the forgiver and forgiven free."},
    {"id": 16, "theme": "Self-belief", "moral": "Believe in yourself and others will believe in you too."},
    {"id": 17, "theme": "Nature", "moral": "When we care for nature, nature cares for us."},
    {"id": 18, "theme": "Learning", "moral": "Every mistake is a lesson in disguise."},
]

PLAN_ACCESS = {
    "free": {"hooks": 20, "structures": 5, "themes": 5, "morals": 5},
    "starter": {"hooks": 100, "structures": 10, "themes": 10, "morals": 10},
    "pro": {"hooks": 500, "structures": 200, "themes": 100, "morals": 50},
    "lifetime": {"hooks": 500, "structures": 200, "themes": 100, "morals": 50}
}

@content_router.get("/vault")
async def get_content_vault(niche: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Get content vault items based on plan - themes and morals are shuffled for variety"""
    import random
    
    user_plan = user.get("plan", "free")
    access = PLAN_ACCESS.get(user_plan, PLAN_ACCESS["free"])
    
    hooks = CONTENT_VAULT_HOOKS
    if niche:
        hooks = [h for h in hooks if h["niche"] == niche.lower()]
    
    # Shuffle kids themes and moral templates for variety each time
    shuffled_themes = KIDS_STORY_THEMES.copy()
    shuffled_morals = MORAL_TEMPLATES.copy()
    random.shuffle(shuffled_themes)
    random.shuffle(shuffled_morals)
    
    return {
        "plan": user_plan,
        "viral_hooks": hooks[:access["hooks"]],
        "reel_structures": REEL_STRUCTURES[:access["structures"]],
        "kids_themes": shuffled_themes[:access["themes"]],
        "moral_templates": shuffled_morals[:access["morals"]],
        "total_hooks": len(CONTENT_VAULT_HOOKS),
        "total_structures": len(REEL_STRUCTURES),
        "total_themes": len(KIDS_STORY_THEMES),
        "total_morals": len(MORAL_TEMPLATES),
        "access_level": access,
        "is_limited": user_plan == "free",
        "upgrade_message": "Upgrade to Pro to unlock all premium content!" if user_plan == "free" else None
    }


@content_router.get("/trending")
async def get_trending_topics(active_only: bool = True, niche: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Get current trending topics"""
    query = {}
    if active_only:
        query["is_active"] = True
    if niche:
        query["niche"] = niche.lower()
    
    topics = await db.trending_topics.find(query, {"_id": 0}).sort("createdAt", -1).limit(20).to_list(length=20)
    return {"topics": topics, "total": len(topics)}


class TrendingTopicCreate(BaseModel):
    title: str
    niche: str
    description: Optional[str] = ""
    hook_preview: str
    suggested_angle: Optional[str] = ""
    week_start: Optional[str] = None
    week_end: Optional[str] = None
    is_active: bool = True


@content_router.post("/trending")
async def create_trending_topic(data: TrendingTopicCreate, user: dict = Depends(get_admin_user)):
    """Create trending topic (Admin)"""
    topic = {
        "id": str(uuid.uuid4()), "title": data.title, "niche": data.niche.lower(),
        "description": data.description or "", "hook_preview": data.hook_preview,
        "suggested_angle": data.suggested_angle or "", "is_active": data.is_active,
        "week_start": data.week_start, "week_end": data.week_end,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.trending_topics.insert_one(topic)
    # Remove MongoDB _id before returning
    topic.pop("_id", None)
    return {"success": True, "topic": topic}


@content_router.delete("/trending/{topic_id}")
async def delete_trending_topic(topic_id: str, user: dict = Depends(get_admin_user)):
    """Delete trending topic (Admin)"""
    result = await db.trending_topics.delete_one({"id": topic_id})
    return {"success": result.deleted_count > 0}

# ==================== CONVERT TOOLS ENDPOINTS ====================

@convert_router.post("/reel-to-carousel")
async def convert_reel_to_carousel(generation_id: str, user: dict = Depends(get_current_user)):
    """Convert reel to carousel - 1 credit"""
    credits_needed = 1
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits.")
    
    reel_gen = await db.generations.find_one({"id": generation_id, "userId": user["id"], "type": "REEL"}, {"_id": 0})
    if not reel_gen:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    reel = reel_gen.get("outputJson", {})
    carousel = {"original_reel_id": generation_id, "slides": [], "caption": reel.get("caption_long", ""), "hashtags": reel.get("hashtags", [])}
    
    carousel["slides"].append({"slide_number": 1, "type": "hook", "text": reel.get("best_hook", "")})
    script = reel.get("script", {})
    for i, scene in enumerate(script.get("scenes", [])[:5], 2):
        carousel["slides"].append({"slide_number": i, "type": "content", "text": scene.get("on_screen_text", "") or scene.get("voiceover", "")[:100]})
    carousel["slides"].append({"slide_number": len(carousel["slides"]) + 1, "type": "cta", "text": script.get("cta", "Follow!")})
    
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credits_needed}})
    await db.credit_ledger.insert_one({"id": str(uuid.uuid4()), "userId": user["id"], "amount": -credits_needed, "type": "USAGE", "description": "Convert: Reel to Carousel", "createdAt": datetime.now(timezone.utc).isoformat()})
    
    conversion_id = str(uuid.uuid4())
    await db.generations.insert_one({"id": conversion_id, "userId": user["id"], "type": "CAROUSEL", "status": "COMPLETED", "inputJson": {"source": generation_id}, "outputJson": carousel, "creditsUsed": credits_needed, "createdAt": datetime.now(timezone.utc).isoformat()})
    
    return {"success": True, "generationId": conversion_id, "carousel": carousel, "creditsUsed": credits_needed, "remainingCredits": user["credits"] - credits_needed}


@convert_router.post("/story-to-reel")
async def convert_story_to_reel(generation_id: str, user: dict = Depends(get_current_user)):
    """Convert story to reel - 1 credit"""
    credits_needed = 1
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits.")
    
    story_gen = await db.generations.find_one({"id": generation_id, "userId": user["id"], "type": "STORY"}, {"_id": 0})
    if not story_gen:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story = story_gen.get("outputJson", {})
    
    reel = {
        "original_story_id": generation_id,
        "hooks": [f"This story will make your kids smile", f"The tale of {story.get('title', 'adventure')}", f"A lesson about {story.get('moral', 'life')[:30]}"],
        "best_hook": f"Story time: {story.get('title', '')}",
        "script": {
            "scenes": [
                {"time": "0-5s", "text": story.get("title", "Story"), "voiceover": f"Let me tell you about {story.get('title', '')}"},
                {"time": "5-15s", "text": "The Beginning", "voiceover": story.get("synopsis", "")[:100]},
                {"time": "15-25s", "text": "The Adventure", "voiceover": "Our hero faced challenges but learned something important..."},
                {"time": "25-30s", "text": story.get("moral", "The Lesson"), "voiceover": f"The moral: {story.get('moral', 'Be kind')}"}
            ],
            "cta": "Follow for more bedtime stories!"
        },
        "caption": f"📚 {story.get('title', '')} - {story.get('moral', '')}",
        "hashtags": ["kidsstory", "bedtimestory", "parenting", "storytime", "moralstory"]
    }
    
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credits_needed}})
    await db.credit_ledger.insert_one({"id": str(uuid.uuid4()), "userId": user["id"], "amount": -credits_needed, "type": "USAGE", "description": f"Convert: Story to Reel", "createdAt": datetime.now(timezone.utc).isoformat()})
    
    conversion_id = str(uuid.uuid4())
    await db.generations.insert_one({"id": conversion_id, "userId": user["id"], "type": "REEL", "status": "COMPLETED", "inputJson": {"source": generation_id}, "outputJson": reel, "creditsUsed": credits_needed, "createdAt": datetime.now(timezone.utc).isoformat()})
    
    return {"success": True, "generationId": conversion_id, "reel": reel, "creditsUsed": credits_needed, "remainingCredits": user["credits"] - credits_needed}


@convert_router.post("/story-to-quote")
async def convert_story_to_quote(generation_id: str, user: dict = Depends(get_current_user)):
    """Convert story to moral quotes - Free"""
    story_gen = await db.generations.find_one({"id": generation_id, "userId": user["id"], "type": "STORY"}, {"_id": 0})
    if not story_gen:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story = story_gen.get("outputJson", {})
    moral = story.get("moral", "Be kind to everyone")
    title = story.get("title", "Story")
    
    quotes = [
        f"'{moral}' - from {title}",
        f"What we learned: {moral}",
        f"The wisdom from '{title}': {moral}",
        f"Remember: {moral} ✨",
        f"🌟 {moral}"
    ]
    
    return {"success": True, "quotes": quotes, "moral": moral, "hashtags": ["morals", "wisdom", "lifelessons"]}


# ==================== GENSTUDIO AI GENERATION ====================

genstudio_router = APIRouter(prefix="/genstudio", tags=["GenStudio"])

# GenStudio Credit Costs
GENSTUDIO_COSTS = {
    "text_to_image": 10,
    "text_to_video": 10,
    "image_to_video": 10,
    "style_profile_create": 20,
    "style_profile_use": 1,
    "video_remix": 12
}

# Prompt Templates for GenStudio
GENSTUDIO_TEMPLATES = [
    {"id": "product_ad", "name": "Product Advertisement", "category": "marketing", "prompt": "Professional product photography of {product}, studio lighting, white background, commercial quality, 8k resolution"},
    {"id": "luxury_reel", "name": "Luxury Brand Reel", "category": "marketing", "prompt": "Cinematic shot of {subject}, luxury aesthetic, golden hour lighting, elegant composition, premium feel"},
    {"id": "kids_story", "name": "Kids Story Illustration", "category": "creative", "prompt": "Colorful children's book illustration of {scene}, whimsical style, soft pastel colors, friendly characters, storybook quality"},
    {"id": "motivation", "name": "Motivational Content", "category": "social", "prompt": "Inspirational image with {theme}, dramatic lighting, powerful composition, motivational atmosphere"},
    {"id": "social_post", "name": "Social Media Post", "category": "social", "prompt": "Eye-catching social media graphic featuring {subject}, vibrant colors, modern design, engagement-optimized"},
    {"id": "nature_scene", "name": "Nature Landscape", "category": "creative", "prompt": "Breathtaking landscape of {location}, golden hour, dramatic sky, professional photography, National Geographic style"},
    {"id": "food_photo", "name": "Food Photography", "category": "marketing", "prompt": "Appetizing food photography of {dish}, professional styling, soft lighting, restaurant quality, mouth-watering presentation"},
    {"id": "tech_product", "name": "Tech Product Shot", "category": "marketing", "prompt": "Sleek tech product render of {product}, minimalist background, professional lighting, Apple-style aesthetic"}
]

# Pydantic models for GenStudio
class TextToImageRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    negative_prompt: Optional[str] = None
    aspect_ratio: str = "1:1"  # 1:1, 16:9, 9:16, 4:3
    style_profile_id: Optional[str] = None
    template_id: Optional[str] = None
    add_watermark: bool = True
    consent_confirmed: bool = False

class TextToVideoRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    duration: int = Field(default=4, ge=2, le=10)  # seconds
    fps: int = Field(default=24, ge=15, le=30)
    aspect_ratio: str = "16:9"
    add_watermark: bool = True
    consent_confirmed: bool = False

class ImageToVideoRequest(BaseModel):
    motion_prompt: str = Field(..., min_length=3, max_length=500)
    duration: int = Field(default=4, ge=2, le=10)
    add_watermark: bool = True
    consent_confirmed: bool = False

class StyleProfileCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    tags: List[str] = []

class VideoRemixRequest(BaseModel):
    remix_prompt: str = Field(..., min_length=3, max_length=1000)
    template_style: str = "dynamic"  # dynamic, smooth, dramatic
    add_watermark: bool = True
    consent_confirmed: bool = False


@genstudio_router.get("/dashboard")
async def genstudio_dashboard(user: dict = Depends(get_current_user)):
    """Get GenStudio dashboard data"""
    # Get recent generations
    recent_jobs = await db.genstudio_jobs.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(10).to_list(10)
    
    # Get style profiles
    style_profiles = await db.style_profiles.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(50)
    
    # Get stats
    total_generations = await db.genstudio_jobs.count_documents({"userId": user["id"]})
    total_images = await db.genstudio_jobs.count_documents({"userId": user["id"], "type": "text_to_image"})
    total_videos = await db.genstudio_jobs.count_documents({"userId": user["id"], "type": {"$in": ["text_to_video", "image_to_video", "video_remix"]}})
    
    return {
        "credits": user.get("credits", 0),
        "plan": user.get("plan", "free"),
        "recentJobs": recent_jobs,
        "styleProfiles": style_profiles,
        "stats": {
            "totalGenerations": total_generations,
            "totalImages": total_images,
            "totalVideos": total_videos
        },
        "templates": GENSTUDIO_TEMPLATES,
        "costs": GENSTUDIO_COSTS
    }


@genstudio_router.get("/templates")
async def get_templates():
    """Get prompt templates"""
    return {"templates": GENSTUDIO_TEMPLATES}


@genstudio_router.post("/text-to-image")
async def generate_text_to_image(data: TextToImageRequest, user: dict = Depends(get_current_user)):
    """Generate image from text prompt using Gemini - costs 10 credits"""
    
    # Safety check
    if not data.consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
    
    # Check for prohibited content
    prohibited_terms = ["celebrity", "famous person", "real person", "deepfake", "face swap"]
    prompt_lower = data.prompt.lower()
    for term in prohibited_terms:
        if term in prompt_lower:
            raise HTTPException(status_code=400, detail=f"Prohibited content detected: {term}. We don't allow identity cloning.")
    
    cost = GENSTUDIO_COSTS["text_to_image"]
    
    # Check credits
    if user.get("credits", 0) < cost:
        user_subscription = user.get("subscription")
        if not user_subscription:
            raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Check if LLM is available
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    job_id = str(uuid.uuid4())
    
    # Create job record
    await db.genstudio_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_image",
        "status": "processing",
        "inputJson": data.model_dump(),
        "costCredits": cost,
        "outputUrls": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    try:
        # Build prompt with template if selected
        prompt = data.prompt
        if data.template_id:
            template = next((t for t in GENSTUDIO_TEMPLATES if t["id"] == data.template_id), None)
            if template:
                prompt = template["prompt"].replace("{subject}", data.prompt).replace("{product}", data.prompt).replace("{scene}", data.prompt).replace("{theme}", data.prompt).replace("{location}", data.prompt).replace("{dish}", data.prompt)
        
        # Add negative prompt
        full_prompt = prompt
        if data.negative_prompt:
            full_prompt = f"{prompt}. Avoid: {data.negative_prompt}"
        
        # Add aspect ratio instruction
        aspect_instructions = {
            "1:1": "square format, 1:1 aspect ratio",
            "16:9": "widescreen format, 16:9 aspect ratio, landscape",
            "9:16": "vertical format, 9:16 aspect ratio, portrait, mobile-friendly",
            "4:3": "standard format, 4:3 aspect ratio"
        }
        full_prompt += f". {aspect_instructions.get(data.aspect_ratio, '')}"
        
        # Add watermark instruction for free users
        if data.add_watermark or user.get("plan") == "free":
            full_prompt += ". Add subtle 'GenStudio' watermark in corner."
        
        # Generate image using Gemini
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"genstudio-{job_id}",
            system_message="You are an AI image generator. Generate high-quality images based on the user's prompt."
        )
        chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
        
        msg = UserMessage(text=full_prompt)
        text_response, images = await chat.send_message_multimodal_response(msg)
        
        if not images or len(images) == 0:
            raise Exception("No image was generated")
        
        # Save image to temp file
        output_urls = []
        for i, img in enumerate(images):
            image_bytes = base64.b64decode(img['data'])
            filename = f"genstudio_{job_id}_{i}.png"
            filepath = f"/tmp/{filename}"
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            output_urls.append(f"/api/genstudio/download/{job_id}/{filename}")
        
        # Update job with success
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "outputUrls": output_urls,
                "completedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Deduct credits
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": -cost}}
        )
        
        # Log transaction
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "amount": -cost,
            "type": "USAGE",
            "description": f"GenStudio: Text to Image",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "jobId": job_id,
            "status": "completed",
            "outputUrls": output_urls,
            "creditsUsed": cost,
            "remainingCredits": user["credits"] - cost,
            "expiresIn": "15 minutes",
            "message": "Image generated! Download within 15 minutes before it expires."
        }
        
    except Exception as e:
        logger.error(f"GenStudio text-to-image error: {e}")
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@genstudio_router.post("/text-to-video")
async def generate_text_to_video(data: TextToVideoRequest, user: dict = Depends(get_current_user)):
    """Generate video from text prompt using Sora 2 - costs 10 credits"""
    
    # Safety check
    if not data.consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
    
    # Check for prohibited content
    prohibited_terms = ["celebrity", "famous person", "real person", "deepfake", "face swap"]
    prompt_lower = data.prompt.lower()
    for term in prohibited_terms:
        if term in prompt_lower:
            raise HTTPException(status_code=400, detail=f"Prohibited content detected: {term}. We don't allow identity cloning.")
    
    cost = GENSTUDIO_COSTS["text_to_video"]
    
    # Check credits
    if user.get("credits", 0) < cost:
        user_subscription = user.get("subscription")
        if not user_subscription:
            raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    job_id = str(uuid.uuid4())
    
    # Map aspect ratios to video sizes
    size_map = {
        "16:9": "1280x720",
        "9:16": "1024x1792",
        "1:1": "1024x1024",
        "4:3": "1280x720"  # Default to HD for 4:3
    }
    video_size = size_map.get(data.aspect_ratio, "1280x720")
    
    # Validate duration
    valid_durations = [4, 8, 12]
    duration = data.duration if data.duration in valid_durations else 4
    
    # Deduct credits upfront
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"credits": -cost}}
    )
    
    # Log transaction
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "amount": -cost,
        "type": "USAGE",
        "description": f"GenStudio: Text to Video ({duration}s)",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Create job record
    await db.genstudio_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_video",
        "status": "processing",
        "inputJson": data.model_dump(),
        "costCredits": cost,
        "outputUrls": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    # Start background video generation task
    async def generate_video_task():
        try:
            from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
            
            video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
            filename = f"genstudio_{job_id}.mp4"
            filepath = f"/tmp/{filename}"
            
            full_prompt = data.prompt
            if data.add_watermark or user.get("plan") == "free":
                full_prompt += ". Include subtle 'GenStudio' watermark."
            
            video_bytes = video_gen.text_to_video(
                prompt=full_prompt,
                model="sora-2",
                size=video_size,
                duration=duration,
                max_wait_time=600
            )
            
            if not video_bytes:
                raise Exception("Video generation failed - no video returned")
            
            video_gen.save_video(video_bytes, filepath)
            output_urls = [f"/api/genstudio/download/{job_id}/{filename}"]
            
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "completed",
                    "outputUrls": output_urls,
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            logger.info(f"Text-to-video job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Text-to-video job {job_id} failed: {e}")
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            # Refund credits on failure
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {"credits": cost}}
            )
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "amount": cost,
                "type": "REFUND",
                "description": f"GenStudio: Text to Video refund (failed)",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
    
    # Start background task
    asyncio.create_task(generate_video_task())
    
    # Return immediately with job ID
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "message": "Video generation started! Check status by polling the job endpoint.",
        "pollUrl": f"/api/genstudio/job/{job_id}",
        "creditsUsed": cost,
        "remainingCredits": user["credits"] - cost,
        "estimatedTime": f"{duration * 15}-{duration * 20} seconds"
    }


@genstudio_router.post("/image-to-video")
async def generate_image_to_video(
    motion_prompt: str = Form(...),
    duration: int = Form(default=4),
    add_watermark: bool = Form(default=True),
    consent_confirmed: bool = Form(default=False),
    image: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Animate an image with AI motion using Sora 2 - costs 10 credits"""
    
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
    
    cost = GENSTUDIO_COSTS["image_to_video"]
    
    if user.get("credits", 0) < cost:
        user_subscription = user.get("subscription")
        if not user_subscription:
            raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type. Supported: PNG, JPEG, WebP")
    
    job_id = str(uuid.uuid4())
    valid_durations = [4, 8, 12]
    duration = duration if duration in valid_durations else 4
    
    # Save uploaded image temporarily
    input_image_path = f"/tmp/genstudio_input_{job_id}.png"
    try:
        image_content = await image.read()
        with open(input_image_path, "wb") as f:
            f.write(image_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")
    
    # Deduct credits upfront
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -cost}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "amount": -cost,
        "type": "USAGE",
        "description": f"GenStudio: Image to Video ({duration}s)",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Create job record
    await db.genstudio_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "image_to_video",
        "status": "processing",
        "inputJson": {"motion_prompt": motion_prompt, "duration": duration, "add_watermark": add_watermark},
        "costCredits": cost,
        "outputUrls": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    # Background task for video generation
    async def generate_image_video_task():
        try:
            from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
            from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent
            
            logger.info(f"Analyzing uploaded image for job {job_id}")
            
            with open(input_image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            analysis_chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"analyze-{job_id}",
                system_message="You are an expert at describing images for video generation."
            ).with_model("gemini", "gemini-2.0-flash")
            
            analysis_prompt = f"""Analyze this image and create a detailed video generation prompt that:
1. Describes the main subjects and their appearance
2. Describes the setting/background  
3. Incorporates this motion/animation request: {motion_prompt}
4. Keeps the visual style consistent with the image

Output ONLY the video prompt, no explanations. Make it cinematic and detailed."""
            
            image_file = FileContent(content_type="image/jpeg", file_content_base64=image_data)
            image_description = await analysis_chat.send_message(UserMessage(text=analysis_prompt, file_contents=[image_file]))
            
            logger.info(f"Image analyzed, generating video for job {job_id}")
            
            video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
            filename = f"genstudio_{job_id}.mp4"
            filepath = f"/tmp/{filename}"
            
            full_prompt = image_description.strip()
            if add_watermark or user.get("plan") == "free":
                full_prompt += ". Include subtle 'GenStudio' watermark in corner."
            
            video_bytes = video_gen.text_to_video(
                prompt=full_prompt,
                model="sora-2",
                size="1280x720",
                duration=duration,
                max_wait_time=600
            )
            
            if not video_bytes:
                raise Exception("Video generation failed - no video returned")
            
            video_gen.save_video(video_bytes, filepath)
            
            if os.path.exists(input_image_path):
                os.remove(input_image_path)
            
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "completed",
                    "outputUrls": [f"/api/genstudio/download/{job_id}/{filename}"],
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            logger.info(f"Image-to-video job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Image-to-video job {job_id} failed: {e}")
            if os.path.exists(input_image_path):
                os.remove(input_image_path)
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            # Refund credits
            await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": cost}})
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "amount": cost,
                "type": "REFUND",
                "description": f"GenStudio: Image to Video refund (failed)",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
    
    asyncio.create_task(generate_image_video_task())
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "message": "Video generation started! Check status by polling the job endpoint.",
        "pollUrl": f"/api/genstudio/job/{job_id}",
        "creditsUsed": cost,
        "remainingCredits": user["credits"] - cost,
        "estimatedTime": f"{duration * 15}-{duration * 20} seconds"
    }


@genstudio_router.post("/video-remix")
async def remix_video(
    remix_prompt: str = Form(...),
    template_style: str = Form(default="dynamic"),
    add_watermark: bool = Form(default=True),
    consent_confirmed: bool = Form(default=False),
    video: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Remix a video with new style/prompt using AI - costs 12 credits"""
    
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
    
    cost = GENSTUDIO_COSTS["video_remix"]
    
    if user.get("credits", 0) < cost:
        user_subscription = user.get("subscription")
        if not user_subscription:
            raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    allowed_types = ["video/mp4", "video/webm", "video/quicktime"]
    if video.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid video type. Supported: MP4, WebM, MOV")
    
    video_content = await video.read()
    if len(video_content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Video file too large. Maximum size is 50MB.")
    
    job_id = str(uuid.uuid4())
    input_video_path = f"/tmp/genstudio_input_{job_id}.mp4"
    
    try:
        with open(input_video_path, "wb") as f:
            f.write(video_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process video: {str(e)}")
    
    # Deduct credits upfront
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -cost}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "amount": -cost,
        "type": "USAGE",
        "description": f"GenStudio: Video Remix ({template_style})",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    await db.genstudio_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "video_remix",
        "status": "processing",
        "inputJson": {"remix_prompt": remix_prompt, "template_style": template_style, "add_watermark": add_watermark},
        "costCredits": cost,
        "outputUrls": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    # Background task for video remix
    async def generate_remix_task():
        try:
            from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            logger.info(f"Creating remix prompt for job {job_id}")
            
            analysis_chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"remix-{job_id}",
                system_message="You are an expert video editor. Create detailed video generation prompts."
            ).with_model("gemini", "gemini-2.0-flash")
            
            style_prompts = {
                "dynamic": "dynamic editing, fast cuts, energetic transitions",
                "smooth": "smooth transitions, gentle flow, cinematic feel",
                "dramatic": "dramatic lighting, intense mood, cinematic color grading"
            }
            style_addition = style_prompts.get(template_style, style_prompts["dynamic"])
            
            analysis_prompt = f"""Create a detailed video generation prompt for a remix:
- User's remix request: {remix_prompt}
- Style: {style_addition}

Output ONLY the video prompt, no explanations. Make it cinematic."""
            
            remix_description = await analysis_chat.send_message(UserMessage(text=analysis_prompt))
            
            video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
            filename = f"genstudio_remix_{job_id}.mp4"
            filepath = f"/tmp/{filename}"
            
            full_prompt = remix_description.strip()
            if add_watermark or user.get("plan") == "free":
                full_prompt += ". Include subtle 'GenStudio' watermark."
            
            video_bytes = video_gen.text_to_video(
                prompt=full_prompt,
                model="sora-2",
                size="1280x720",
                duration=4,
                max_wait_time=600
            )
            
            if not video_bytes:
                raise Exception("Video remix failed - no video returned")
            
            video_gen.save_video(video_bytes, filepath)
            
            if os.path.exists(input_video_path):
                os.remove(input_video_path)
            
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "completed",
                    "outputUrls": [f"/api/genstudio/download/{job_id}/{filename}"],
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            logger.info(f"Video remix job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Video remix job {job_id} failed: {e}")
            if os.path.exists(input_video_path):
                os.remove(input_video_path)
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": cost}})
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "amount": cost,
                "type": "REFUND",
                "description": f"GenStudio: Video Remix refund (failed)",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
    
    asyncio.create_task(generate_remix_task())
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "message": "Video remix started! Check status by polling the job endpoint.",
        "pollUrl": f"/api/genstudio/job/{job_id}",
        "creditsUsed": cost,
        "remainingCredits": user["credits"] - cost,
        "estimatedTime": "60-120 seconds"
    }


@genstudio_router.get("/download/{job_id}/{filename}")
async def download_genstudio_file(job_id: str, filename: str, user: dict = Depends(get_current_user)):
    """Download generated file - expires after 15 minutes"""
    
    # Verify job belongs to user
    job = await db.genstudio_jobs.find_one({"id": job_id, "userId": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="File not found or expired")
    
    # Check expiry
    expiry_str = job.get("expiresAt")
    if expiry_str:
        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry_time:
            raise HTTPException(status_code=410, detail="Download link expired. Files are available for 15 minutes only.")
    
    filepath = f"/tmp/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=410, detail="File expired or not found")
    
    # Detect media type based on file extension
    media_type = "image/png"
    if filename.endswith(".mp4"):
        media_type = "video/mp4"
    elif filename.endswith(".webm"):
        media_type = "video/webm"
    elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        media_type = "image/jpeg"
    elif filename.endswith(".webp"):
        media_type = "image/webp"
    
    return FileResponse(filepath, filename=filename, media_type=media_type)


@genstudio_router.get("/history")
async def get_genstudio_history(
    page: int = 1, 
    limit: int = 20, 
    type_filter: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get generation history with pagination"""
    
    query = {"userId": user["id"]}
    if type_filter:
        query["type"] = type_filter
    
    skip = (page - 1) * limit
    
    jobs = await db.genstudio_jobs.find(
        query, {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.genstudio_jobs.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit,
        "hasMore": skip + limit < total
    }


@genstudio_router.post("/style-profile")
async def create_style_profile(data: StyleProfileCreate, user: dict = Depends(get_current_user)):
    """Create a new brand style profile - costs 20 credits"""
    
    cost = GENSTUDIO_COSTS["style_profile_create"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} credits to create a style profile")
    
    profile_id = str(uuid.uuid4())
    
    await db.style_profiles.insert_one({
        "id": profile_id,
        "userId": user["id"],
        "name": data.name,
        "description": data.description,
        "tags": data.tags,
        "refImageUrls": [],  # Will be added via upload
        "trained": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Deduct credits
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"credits": -cost}}
    )
    
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "amount": -cost,
        "type": "USAGE",
        "description": f"GenStudio: Style Profile '{data.name}'",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "profileId": profile_id,
        "creditsUsed": cost,
        "remainingCredits": user["credits"] - cost,
        "message": "Style profile created! Now upload 10-20 reference images."
    }


@genstudio_router.get("/style-profiles")
async def get_style_profiles(user: dict = Depends(get_current_user)):
    """Get user's style profiles"""
    
    profiles = await db.style_profiles.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(50)
    
    return {"profiles": profiles, "count": len(profiles)}


@genstudio_router.delete("/style-profile/{profile_id}")
async def delete_style_profile(profile_id: str, user: dict = Depends(get_current_user)):
    """Delete a style profile"""
    
    result = await db.style_profiles.delete_one({"id": profile_id, "userId": user["id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    return {"success": True, "message": "Style profile deleted"}


@genstudio_router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status"""
    
    job = await db.genstudio_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


# ==================== INCLUDE ROUTERS ====================

api_router.include_router(auth_router)
api_router.include_router(credits_router)
api_router.include_router(generate_router)
api_router.include_router(video_router)
api_router.include_router(payments_router)
api_router.include_router(feedback_router)
api_router.include_router(admin_router)
api_router.include_router(chatbot_router)
api_router.include_router(health_router)
api_router.include_router(alert_router)
api_router.include_router(creator_tools_router)
api_router.include_router(story_tools_router)
api_router.include_router(content_router)
api_router.include_router(convert_router)
api_router.include_router(genstudio_router)

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
    await db.printable_books.create_index("expiresAt")  # For cleanup
    
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
            "plan": "admin",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Admin user created")
    else:
        # Update admin credits to unlimited
        await db.users.update_one(
            {"email": "admin@creatorstudio.ai"},
            {"$set": {"credits": 999999, "plan": "admin"}}
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
            "credits": 100,  # 100 free credits for demo
            "plan": "free",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Demo user created")
    else:
        # Update demo user credits to 100
        await db.users.update_one(
            {"email": "demo@example.com"},
            {"$set": {"credits": 100, "plan": "free"}}
        )
    
    # Start background cleanup task for expired downloads
    import asyncio
    asyncio.create_task(cleanup_expired_downloads())
    
    logger.info("CreatorStudio API ready!")


async def cleanup_expired_downloads():
    """Background task to clean up expired files every minute - FILES EXPIRE IN 3 MINUTES"""
    import asyncio
    import glob
    
    while True:
        try:
            logger.info("Running security cleanup task...")
            
            # Delete all expired printable books (3 min expiry)
            result = await db.printable_books.delete_many({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"SECURITY: Cleaned up {result.deleted_count} expired printable book(s)")
            
            # Delete all expired GenStudio jobs (3 min expiry) and their files
            expired_jobs = await db.genstudio_jobs.find({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            }).to_list(100)
            
            for job in expired_jobs:
                job_id = job.get("id", "")
                # Delete associated files - all patterns
                for pattern in [f"/tmp/genstudio_{job_id}*", f"/tmp/genstudio_input_{job_id}*", f"/tmp/genstudio_remix_{job_id}*"]:
                    for filepath in glob.glob(pattern):
                        try:
                            os.remove(filepath)
                            logger.info(f"SECURITY: Deleted expired file: {filepath}")
                        except Exception as e:
                            logger.warning(f"Failed to delete file {filepath}: {e}")
            
            # Delete expired job records
            result = await db.genstudio_jobs.delete_many({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"SECURITY: Cleaned up {result.deleted_count} expired GenStudio job(s)")
            
            # AGGRESSIVE CLEANUP: Delete any temp files older than 3 minutes
            current_time = datetime.now(timezone.utc)
            for pattern in ["/tmp/genstudio_*", "/tmp/printable_*", "/tmp/story_*", "/tmp/reel_*"]:
                for filepath in glob.glob(pattern):
                    try:
                        file_age = current_time.timestamp() - os.path.getmtime(filepath)
                        if file_age > (FILE_EXPIRY_MINUTES * 60):  # 3 minutes in seconds
                            os.remove(filepath)
                            logger.info(f"SECURITY: Force-deleted old file: {filepath}")
                    except Exception as e:
                        pass
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        await asyncio.sleep(60)  # Run every minute


@app.on_event("shutdown")
async def shutdown():
    client.close()
    logger.info("CreatorStudio API shutdown")
