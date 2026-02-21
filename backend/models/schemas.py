"""
Pydantic models for API request/response schemas
CreatorStudio AI - Comprehensive Schema Definitions
"""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any


# ==================== AUTH MODELS ====================
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleCallback(BaseModel):
    sessionId: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None


class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    credits: int
    createdAt: Optional[str] = None


# ==================== GENERATION MODELS ====================
class GenerateReelRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=2000, description="Topic for reel generation")
    niche: str = Field(default="General", max_length=100)
    language: str = Field(default="English", max_length=50)
    tone: str = Field(default="Bold", max_length=50)
    duration: str = Field(default="30s", max_length=20)
    goal: str = Field(default="Followers", max_length=50)


class GenerateStoryRequest(BaseModel):
    genre: str = "Adventure"
    customGenre: Optional[str] = None
    ageGroup: str = "4-6"
    theme: str = "Friendship"
    sceneCount: int = 8


# ==================== FEEDBACK MODELS ====================
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


# ==================== PAYMENT MODELS ====================
class CreateOrderRequest(BaseModel):
    productId: str
    currency: str = "INR"


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ==================== GENSTUDIO MODELS ====================
class TextToImageRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    negative_prompt: Optional[str] = None
    aspect_ratio: str = "1:1"
    style_profile_id: Optional[str] = None
    template_id: Optional[str] = None
    add_watermark: bool = True
    consent_confirmed: bool = False


class TextToVideoRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    duration: int = Field(default=4, ge=2, le=12)
    fps: int = Field(default=24, ge=15, le=30)
    aspect_ratio: str = "16:9"
    add_watermark: bool = True
    consent_confirmed: bool = False


class StyleProfileCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    tags: List[str] = []


# ==================== CONTENT VAULT MODELS ====================
class TrendingTopicCreate(BaseModel):
    title: str
    description: str
    niche: str
    hashtags: List[str] = []
    engagement_score: float = 0.0


# ==================== VIDEO EXPORT MODELS ====================
class VideoExportRequest(BaseModel):
    generationId: str
    voiceId: str = "emily"
    backgroundMusic: str = "none"


# ==================== ADMIN MODELS ====================
class AdminExceptionLog(BaseModel):
    id: str
    functionality: str
    error_type: str
    error_message: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: str = "ERROR"
    resolved: bool = False
    created_at: str


class PaymentLog(BaseModel):
    id: str
    user_id: str
    user_email: str
    order_id: str
    amount: int
    currency: str
    status: str  # SUCCESS, FAILED, PENDING, REFUNDED
    product_id: str
    credits: int
    failure_reason: Optional[str] = None
    refund_id: Optional[str] = None
    created_at: str


# ==================== CREATOR PRO MODELS ====================
class HookAnalyzerRequest(BaseModel):
    hook: str = Field(..., min_length=3, max_length=500)
    niche: Optional[str] = None


class SwipeFileRequest(BaseModel):
    niche: str
    content_type: str = "reel"  # reel, story, carousel
    limit: int = 10


class BioGeneratorRequest(BaseModel):
    profession: str
    keywords: List[str] = []
    tone: str = "professional"
    platform: str = "instagram"


class ContentRepurposeRequest(BaseModel):
    content: str = Field(..., min_length=10)
    source_format: str  # blog, tweet, caption
    target_formats: List[str]  # reel_script, carousel, thread


class ConsistencyTrackerRequest(BaseModel):
    content_type: str
    platform: str = "instagram"


# ==================== TWINFINDER MODELS ====================
class TwinFinderUploadRequest(BaseModel):
    consent_confirmed: bool = False


class TwinFinderSearchRequest(BaseModel):
    threshold: float = Field(default=0.7, ge=0.5, le=0.95)
    limit: int = Field(default=10, ge=1, le=50)
