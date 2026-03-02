"""
Shared Dependencies for CreatorStudio AI Backend
Contains database connections, authentication, and common utilities
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import bcrypt
import jwt
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import razorpay

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("creatorstudio")

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ.get('DB_NAME', 'creatorstudio')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Security configurations
JWT_SECRET = os.environ.get('JWT_SECRET', 'creatorstudio-dev-secret-change-in-prod')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 720  # 30 days (extended for better UX)

# File expiry (security) - 3 minutes as per security requirements
FILE_EXPIRY_MINUTES = 3

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ADMIN_ALERT_EMAIL = os.environ.get('ADMIN_ALERT_EMAIL', 'admin@creatorstudio.ai')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'alerts@creatorstudio.ai')
WORKER_URL = os.environ.get('WORKER_URL', 'http://localhost:5000')

# Check LLM availability
LLM_AVAILABLE = False
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    LLM_AVAILABLE = bool(EMERGENT_LLM_KEY)
except ImportError:
    pass

# Check ElevenLabs availability
ELEVENLABS_AVAILABLE = False
eleven_client = None
try:
    from elevenlabs import ElevenLabs
    from elevenlabs.core import ApiError as ElevenLabsError
    ELEVENLABS_AVAILABLE = True
    if ELEVENLABS_API_KEY:
        eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
except ImportError:
    pass

# SendGrid availability
SENDGRID_AVAILABLE = False
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = bool(SENDGRID_API_KEY)
except ImportError:
    pass

# Initialize Razorpay Client
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Security bearer
security = HTTPBearer()

# Video storage directory
VIDEO_STORAGE_DIR = Path("/tmp/creatorstudio_videos")
VIDEO_STORAGE_DIR.mkdir(exist_ok=True)

# =============================================================================
# PASSWORD UTILITIES
# =============================================================================
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# =============================================================================
# JWT TOKEN UTILITIES
# =============================================================================
def create_token(user_id: str, role: str) -> str:
    """Create JWT token"""
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode JWT token"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# =============================================================================
# AUTHENTICATION DEPENDENCIES
# =============================================================================
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_optional_user(request: Request) -> Optional[dict]:
    """Get user if authenticated, None otherwise"""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    try:
        token = auth.split(" ")[1]
        payload = decode_token(token)
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        return user
    except:
        return None

async def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    """Require admin role"""
    role = user.get("role", "").upper()
    if role not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# =============================================================================
# CREDIT UTILITIES
# =============================================================================
async def check_credits(user: dict, amount: int, feature_name: str = "this feature") -> None:
    """Check if user has enough credits, raise exception if not"""
    current = user.get("credits", 0)
    if current < amount:
        subscription = user.get("subscription")
        if not subscription:
            raise HTTPException(
                status_code=402,
                detail=f"You've used all your free credits! Please subscribe to continue using {feature_name}."
            )
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient credits. Need {amount} credits, have {current}."
        )

async def deduct_credits(user_id: str, amount: int, description: str) -> int:
    """Deduct credits from user and log transaction"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_credits = user.get("credits", 0)
    if current_credits < amount:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {amount}, have {current_credits}")
    
    new_balance = current_credits - amount
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"credits": new_balance}}
    )
    
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "amount": -amount,
        "type": "USAGE",
        "description": description,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return new_balance

async def add_credits(user_id: str, amount: int, description: str, tx_type: str = "PURCHASE", order_id: str = None) -> int:
    """Add credits to user and log transaction"""
    result = await db.users.find_one_and_update(
        {"id": user_id},
        {"$inc": {"credits": amount}},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    ledger_entry = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "amount": amount,
        "type": tx_type,
        "description": description,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    if order_id:
        ledger_entry["orderId"] = order_id
    
    await db.credit_ledger.insert_one(ledger_entry)
    
    return result.get("credits", 0)

# =============================================================================
# EXCEPTION LOGGING
# =============================================================================
async def log_exception(
    functionality: str,
    error_type: str,
    error_message: str,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    stack_trace: Optional[str] = None,
    severity: str = "ERROR"
):
    """Log an exception to the database for admin monitoring"""
    try:
        await db.exception_logs.insert_one({
            "id": str(uuid.uuid4()),
            "functionality": functionality,
            "error_type": error_type,
            "error_message": error_message,
            "user_id": user_id,
            "user_email": user_email,
            "stack_trace": stack_trace,
            "severity": severity,
            "resolved": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to log exception: {e}")

# =============================================================================
# PAYMENT LOGGING
# =============================================================================
async def log_payment(
    user_id: str,
    user_email: str,
    order_id: str,
    amount: int,
    currency: str,
    status: str,
    product_id: str,
    credits: int,
    failure_reason: Optional[str] = None,
    refund_id: Optional[str] = None
):
    """Log a payment transaction to the database"""
    try:
        await db.payment_logs.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "user_email": user_email,
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "status": status,
            "product_id": product_id,
            "credits": credits,
            "failure_reason": failure_reason,
            "refund_id": refund_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to log payment: {e}")

# =============================================================================
# REFUND PROCESSING
# =============================================================================
async def process_refund(order_id: str, payment_id: str, reason: str) -> dict:
    """Process a refund for a failed delivery after successful payment"""
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment gateway not configured")
    
    try:
        # Get order details
        order = await db.orders.find_one({"razorpay_order_id": order_id})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Process refund via Razorpay
        refund = razorpay_client.payment.refund(payment_id, {
            "amount": order["amount"],
            "speed": "normal",
            "notes": {
                "reason": reason,
                "order_id": order_id
            }
        })
        
        # Update order status
        await db.orders.update_one(
            {"razorpay_order_id": order_id},
            {
                "$set": {
                    "status": "REFUNDED",
                    "refund_id": refund["id"],
                    "refund_reason": reason,
                    "refunded_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Log the refund
        await log_payment(
            user_id=order["userId"],
            user_email="",
            order_id=order_id,
            amount=order["amount"],
            currency=order.get("currency", "INR"),
            status="REFUNDED",
            product_id=order.get("productId", ""),
            credits=order.get("credits", 0),
            failure_reason=reason,
            refund_id=refund["id"]
        )
        
        logger.info(f"Refund processed: {refund['id']} for order {order_id}")
        return {"success": True, "refund_id": refund["id"]}
        
    except Exception as e:
        logger.error(f"Refund failed: {e}")
        await log_exception(
            functionality="payment_refund",
            error_type="REFUND_FAILED",
            error_message=str(e),
            severity="CRITICAL"
        )
        raise HTTPException(status_code=500, detail=f"Refund failed: {str(e)}")

# =============================================================================
# AI GENERATION PROMPTS
# =============================================================================
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
  "moral": "The lesson this story teaches",
  "scenes": [
    {{
      "sceneNumber": 1,
      "sceneTitle": "Scene title",
      "narration": "Full narration text for voiceover (2-3 sentences)",
      "visualDescription": "Detailed visual prompt for image generation",
      "characterDialogue": "Any character dialogue in this scene"
    }}
  ],
  "characters": [
    {{
      "name": "Character name",
      "description": "Brief description for visual consistency"
    }}
  ],
  "readingLevel": "Easy/Medium/Advanced based on age",
  "keywords": ["5-8 relevant keywords"],
  "parentNotes": "Brief note for parents about the story's message"
}}

Create exactly {scenes} unique scenes. Make each scene visually distinct and story-advancing."""

# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    # Database & Logging
    'db', 'logger', 'security', 'client',
    # Password utilities
    'hash_password', 'verify_password',
    # Token utilities
    'create_token', 'decode_token',
    # Auth dependencies
    'get_current_user', 'get_optional_user', 'get_admin_user',
    # Credit utilities
    'check_credits', 'deduct_credits', 'add_credits',
    # Exception & Payment logging
    'log_exception', 'log_payment', 'process_refund',
    # Configuration
    'FILE_EXPIRY_MINUTES', 'LLM_AVAILABLE', 'JWT_SECRET', 'JWT_ALGORITHM',
    # API Keys
    'EMERGENT_LLM_KEY', 'RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET',
    'SENDGRID_API_KEY', 'ELEVENLABS_API_KEY', 'WORKER_URL',
    'ADMIN_ALERT_EMAIL', 'SENDER_EMAIL',
    # Clients
    'razorpay_client', 'eleven_client',
    # Availability flags
    'SENDGRID_AVAILABLE', 'ELEVENLABS_AVAILABLE',
    # Storage
    'VIDEO_STORAGE_DIR',
    # Prompts
    'REEL_SYSTEM_PROMPT', 'REEL_USER_PROMPT_TEMPLATE',
    'STORY_SYSTEM_PROMPT', 'STORY_USER_PROMPT_TEMPLATE',
]
