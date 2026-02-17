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

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ.get('DB_NAME', 'creatorstudio')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Security configurations
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# File expiry (security)
FILE_EXPIRY_MINUTES = 3

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')

# Check LLM availability
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    LLM_AVAILABLE = bool(EMERGENT_LLM_KEY)
except ImportError:
    LLM_AVAILABLE = False

# Security bearer
security = HTTPBearer()

# =============================================================================
# PASSWORD UTILITIES
# =============================================================================
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
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
# AUTHENTICATION DEPENDENCY
# =============================================================================
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user"""
    payload = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
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

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require admin role"""
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# =============================================================================
# CREDIT UTILITIES
# =============================================================================
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

async def add_credits(user_id: str, amount: int, description: str, tx_type: str = "PURCHASE") -> int:
    """Add credits to user and log transaction"""
    result = await db.users.find_one_and_update(
        {"id": user_id},
        {"$inc": {"credits": amount}},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "amount": amount,
        "type": tx_type,
        "description": description,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return result.get("credits", 0)

# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    'db', 'logger', 'security',
    'hash_password', 'verify_password',
    'create_token', 'decode_token',
    'get_current_user', 'get_optional_user', 'require_admin',
    'deduct_credits', 'add_credits',
    'FILE_EXPIRY_MINUTES', 'LLM_AVAILABLE',
    'EMERGENT_LLM_KEY', 'RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET',
    'SENDGRID_API_KEY', 'ELEVENLABS_API_KEY'
]
