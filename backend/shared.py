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
    """
    Atomically deduct credits from user — delegates to CreditsService.
    Raises HTTPException on failure.
    """
    from services.credits_service import get_credits_service, InsufficientCreditsError
    svc = get_credits_service(db)
    try:
        result = await svc.deduct_credits(user_id, amount, reason=description)
        return result["new_balance"]
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

async def add_credits(user_id: str, amount: int, description: str, tx_type: str = "PURCHASE", order_id: str = None) -> int:
    """Add credits to user — delegates to CreditsService."""
    from services.credits_service import get_credits_service
    svc = get_credits_service(db)
    result = await svc.award_credits(user_id, amount, reason=description, reference_id=order_id)
    return result["new_balance"]

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
REEL_SYSTEM_PROMPT = """You are an elite social media content strategist and scriptwriter who specializes in creating viral, high-retention short-form video content. You optimize for real outcomes: engagement, followers, conversions, and watch time. Output must be structured JSON only."""

REEL_USER_PROMPT_TEMPLATE = """Generate a UNIQUE, outcome-driven short-form video content pack optimized for real performance.

**Creator Brief:**
- Platform: {platform}
- Topic: {topic}
- Niche: {niche}
- Hook Style: {hookStyle}
- Reel Format: {reelFormat}
- Tone: {tone}
- Duration: {duration}
- Content Objective: {goal}
- CTA Type: {ctaType}
- Target Audience: {audience}
- Language: {language}
- Output Scope: {outputType}
- Unique Request ID: {uniqueId}

**PERFORMANCE REQUIREMENTS:**
- Hooks must stop the scroll in under 1.5 seconds
- Script must maintain retention throughout with pattern interrupts
- CTA must feel natural, not forced
- Content must be platform-native (not generic across platforms)
- Each hook variant should use a different psychological trigger

Output ONLY this JSON format:
{{
  "hooks": ["5 unique scroll-stopping hooks using different psychological triggers, under 12 words each"],
  "best_hook": "The highest-performing hook from above",
  "script": {{
    "scenes": [
      {{
        "time": "0-3s",
        "on_screen_text": "Bold text overlay for this segment",
        "voiceover": "Spoken narration for this segment",
        "visual_direction": "Camera angle, movement, and visual style direction",
        "broll": ["specific visual/footage suggestions"],
        "retention_note": "Why this segment keeps viewers watching"
      }}
    ],
    "cta": "Natural, compelling call to action matching the CTA type"
  }},
  "voiceover_full": "Complete voiceover script as a single flowing text, optimized for {duration} at natural speaking pace",
  "caption_short": "Short engaging caption optimized for {platform}",
  "caption_long": "Detailed value-driven caption with hooks and line breaks",
  "hashtags": ["20 relevant trending hashtags for {platform}"],
  "shot_list": [
    {{
      "shot_number": 1,
      "description": "What to film/show",
      "type": "close-up / wide / medium / overhead / POV",
      "duration": "Xs",
      "notes": "Lighting, props, or movement notes"
    }}
  ],
  "visual_prompts": [
    "Detailed AI image/video generation prompt for scene 1 - include style, mood, colors, composition",
    "Detailed AI image/video generation prompt for scene 2"
  ],
  "posting_tips": ["5 specific tips for maximizing performance on {platform}"],
  "ai_recommendations": {{
    "best_hook_type": "Why this hook style works best for this topic",
    "recommended_duration": "Optimal duration with reasoning",
    "suggested_posting_time": "Best time to post on {platform}",
    "emotional_trigger": "Primary emotion this content should evoke",
    "retention_strategy": "Key strategy for maintaining watch time"
  }}
}}

Rules:
- Hooks MUST use the specified hook style ({hookStyle}) as the primary approach
- Script format MUST match the reel format ({reelFormat})
- CTA MUST align with the specified CTA type ({ctaType})
- Content MUST be optimized for {platform} specifically
- Visual prompts must be detailed enough for AI image generation
- Shot list must be practical and actionable
- Voiceover must match the specified tone ({tone})
- No unsafe/illegal content

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
