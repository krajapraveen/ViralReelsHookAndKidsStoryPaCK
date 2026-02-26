"""
CreatorStudio AI - User Analytics Models
=========================================
Database models for user behavior tracking, ratings, and analytics.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Types of feature events to track"""
    FEATURE_OPENED = "FEATURE_OPENED"
    GENERATE_CLICKED = "GENERATE_CLICKED"
    GENERATION_SUCCESS = "GENERATION_SUCCESS"
    GENERATION_FAILED = "GENERATION_FAILED"
    DOWNLOAD_CLICKED = "DOWNLOAD_CLICKED"
    DOWNLOAD_SUCCESS = "DOWNLOAD_SUCCESS"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    SHARE_CLICKED = "SHARE_CLICKED"
    PREVIEW_VIEWED = "PREVIEW_VIEWED"
    SETTINGS_CHANGED = "SETTINGS_CHANGED"


class RatingReasonType(str, Enum):
    """Predefined reasons for low ratings"""
    GENERATION_FAILED = "generation_failed"
    POOR_QUALITY = "poor_quality"
    TOO_SLOW = "too_slow"
    CONFUSING_UI = "confusing_ui"
    CREDITS_ISSUE = "credits_issue"
    DOWNLOAD_FAILED = "download_failed"
    OTHER = "other"


class UserPlatform(str, Enum):
    """User platforms"""
    WEB_DESKTOP = "web_desktop"
    WEB_MOBILE = "web_mobile"
    WEB_TABLET = "web_tablet"
    APP_IOS = "app_ios"
    APP_ANDROID = "app_android"


class UserType(str, Enum):
    """User types"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class SessionCreate(BaseModel):
    """Create a new user session"""
    device_type: Optional[str] = None
    platform: Optional[str] = None
    browser: Optional[str] = None
    user_agent: Optional[str] = None


class FeatureEventCreate(BaseModel):
    """Create a feature event"""
    feature_key: str
    event_type: EventType
    status: Optional[str] = "success"
    latency_ms: Optional[int] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RatingCreate(BaseModel):
    """Create a rating with optional required feedback for low ratings"""
    rating: int = Field(..., ge=1, le=5)
    feature_key: Optional[str] = None
    reason_type: Optional[RatingReasonType] = None
    comment: Optional[str] = None
    related_request_id: Optional[str] = None


class RatingWithRequiredFeedback(BaseModel):
    """Rating submission that enforces feedback for 1-2 stars"""
    rating: int = Field(..., ge=1, le=5)
    feature_key: Optional[str] = None
    reason_type: Optional[RatingReasonType] = None  # Required for 1-2 stars
    comment: Optional[str] = None  # Required for 1-2 stars if reason_type is OTHER
    related_request_id: Optional[str] = None


class RatingDrilldownResponse(BaseModel):
    """Detailed drilldown for a low rating"""
    rating_id: str
    user_id: str
    user_email: Optional[str]
    user_name: Optional[str]
    user_type: Optional[str]
    rating: int
    reason_type: Optional[str]
    comment: Optional[str]
    feature_key: Optional[str]
    created_at: str
    
    # User session info
    session_id: Optional[str]
    session_duration_minutes: Optional[int]
    device_type: Optional[str]
    platform: Optional[str]
    browser: Optional[str]
    
    # Location (privacy-safe)
    approx_location: Optional[Dict[str, str]]
    
    # Feature usage context
    feature_events_before_rating: Optional[List[Dict[str, Any]]]
    output_status: Optional[str]
    error_codes: Optional[List[str]]
    
    # Related generation
    related_generation: Optional[Dict[str, Any]]


class RatingSummaryResponse(BaseModel):
    """Summary of ratings for dashboard"""
    period_days: int
    total_ratings: int
    average_rating: float
    distribution: Dict[int, int]
    nps_score: float
    satisfaction_percentage: float
    low_rating_count: int
    low_rating_percentage: float


class FeatureHappinessResponse(BaseModel):
    """Happy vs Unhappy features report"""
    happy_features: List[Dict[str, Any]]
    unhappy_features: List[Dict[str, Any]]
    period_days: int


# ============================================
# DATABASE DOCUMENT SCHEMAS
# ============================================

"""
MongoDB Collections:

1. user_sessions
{
    "session_id": "uuid",
    "user_id": "uuid",
    "login_at": "ISO datetime",
    "logout_at": "ISO datetime or null",
    "device_type": "desktop|mobile|tablet",
    "platform": "web_desktop|web_mobile|app_ios|app_android",
    "browser": "Chrome|Safari|Firefox|etc",
    "user_agent": "full user agent string",
    "approx_location": {
        "country": "India",
        "region": "Maharashtra", 
        "city": "Mumbai"
    },
    "ip_hash": "hashed IP for dedup, not stored raw"
}

2. feature_events
{
    "event_id": "uuid",
    "session_id": "uuid",
    "user_id": "uuid",
    "feature_key": "reel_generator|story_pack|comix_ai|etc",
    "event_type": "FEATURE_OPENED|GENERATE_CLICKED|GENERATION_SUCCESS|GENERATION_FAILED|etc",
    "status": "success|failed|pending",
    "latency_ms": 1234,
    "error_code": "E001|null",
    "created_at": "ISO datetime",
    "metadata": {}
}

3. ratings
{
    "rating_id": "uuid",
    "user_id": "uuid",
    "session_id": "uuid",
    "feature_key": "reel_generator|story_pack|etc|null for general",
    "rating": 1-5,
    "reason_type": "generation_failed|poor_quality|too_slow|confusing_ui|credits_issue|download_failed|other|null",
    "comment": "user provided comment",
    "attachment_url": "optional screenshot url",
    "created_at": "ISO datetime",
    "related_request_id": "job_id or generation_id if applicable"
}

Indexes to create:
- user_sessions: (user_id, login_at), (session_id unique)
- feature_events: (user_id, created_at), (session_id, created_at), (feature_key, event_type), (event_id unique)
- ratings: (user_id, created_at), (rating, created_at), (feature_key, rating), (rating_id unique)
"""
