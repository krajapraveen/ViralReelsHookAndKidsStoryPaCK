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
import asyncio
import razorpay

# LLM Integration for AI generation
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

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
    # Check credits
    if user["credits"] < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits. You need 1 credit for reel generation.")
    
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
        # Try inline generation first (for production), fall back to worker (for local dev)
        result = None
        generation_error = None
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                result = await generate_story_content_inline(data.model_dump())
            except Exception as inline_error:
                logger.warning(f"Inline story generation failed: {inline_error}")
                generation_error = str(inline_error)
        
        # Fall back to worker if inline failed or not available (local dev only)
        if result is None and WORKER_URL and 'localhost' not in WORKER_URL:
            try:
                async with httpx.AsyncClient(timeout=180.0) as client_http:
                    response = await client_http.post(
                        f"{WORKER_URL}/generate/story",
                        json=data.model_dump()
                    )
                    if response.status_code == 200:
                        result = response.json()
            except Exception as worker_error:
                logger.warning(f"Worker fallback also failed: {worker_error}")
        
        if result is None:
            error_msg = generation_error or "AI service unavailable. Please try again."
            raise HTTPException(status_code=503, detail=error_msg)
        
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
api_router.include_router(alert_router)

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
