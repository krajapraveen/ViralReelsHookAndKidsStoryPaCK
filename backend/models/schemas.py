"""Pydantic models for API request/response schemas"""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleCallback(BaseModel):
    code: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    credits: int


class GenerateReelRequest(BaseModel):
    language: str = "English"
    niche: str = "Business"
    tone: str = "Professional"
    duration: str = "30s"
    goal: str = "Engagement"
    topic: str = ""


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


class ProfileUpdate(BaseModel):
    name: Optional[str] = None


class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str
