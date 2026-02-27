"""
IP Security & 2FA Routes
CreatorStudio AI - Security management endpoints

Includes:
- IP blocking/unblocking (admin)
- IP security stats
- 2FA enable/disable
- OTP generation and verification
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from typing import Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, get_admin_user
from security import limiter
from services.ip_security_service import get_ip_security_service
from services.two_factor_auth_service import get_two_factor_service

router = APIRouter(prefix="/security", tags=["Security"])


# ============================================================================
# REQUEST MODELS
# ============================================================================
class BlockIPRequest(BaseModel):
    ip_address: str = Field(..., description="IP address to block")
    reason: str = Field(..., description="Reason for blocking")
    duration_hours: int = Field(24, ge=1, le=720, description="Block duration in hours")


class WhitelistIPRequest(BaseModel):
    ip_address: str = Field(..., description="IP address to whitelist")
    reason: str = Field(..., description="Reason for whitelisting")


class Enable2FARequest(BaseModel):
    password: str = Field(..., description="Current password for verification")


class Verify2FARequest(BaseModel):
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    purpose: str = Field("login", description="Purpose: login, enable_2fa, disable_2fa")


# ============================================================================
# IP SECURITY ENDPOINTS (ADMIN)
# ============================================================================
@router.get("/ip/blocked")
@limiter.limit("30/minute")
async def get_blocked_ips(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_admin_user)
):
    """Get list of blocked IP addresses (admin only)"""
    ip_service = await get_ip_security_service(db)
    return await ip_service.get_blocked_ips(page=page, size=size)


@router.post("/ip/block")
@limiter.limit("30/minute")
async def block_ip(
    request: Request,
    data: BlockIPRequest,
    admin: dict = Depends(get_admin_user)
):
    """Block an IP address (admin only)"""
    ip_service = await get_ip_security_service(db)
    await ip_service.block_ip(
        ip_address=data.ip_address,
        reason="ADMIN_BLOCK",
        details=data.reason,
        duration_hours=data.duration_hours,
        admin_id=admin["id"]
    )
    
    logger.info(f"Admin {admin['email']} blocked IP {data.ip_address}")
    return {"success": True, "message": f"IP {data.ip_address} blocked for {data.duration_hours} hours"}


@router.post("/ip/unblock")
@limiter.limit("30/minute")
async def unblock_ip(
    request: Request,
    ip_address: str,
    admin: dict = Depends(get_admin_user)
):
    """Unblock an IP address (admin only)"""
    ip_service = await get_ip_security_service(db)
    await ip_service.unblock_ip(ip_address=ip_address, admin_id=admin["id"])
    
    logger.info(f"Admin {admin['email']} unblocked IP {ip_address}")
    return {"success": True, "message": f"IP {ip_address} unblocked"}


@router.post("/ip/whitelist")
@limiter.limit("30/minute")
async def whitelist_ip(
    request: Request,
    data: WhitelistIPRequest,
    admin: dict = Depends(get_admin_user)
):
    """Add IP to whitelist (admin only)"""
    ip_service = await get_ip_security_service(db)
    await ip_service.add_to_whitelist(
        ip_address=data.ip_address,
        admin_id=admin["id"],
        reason=data.reason
    )
    
    return {"success": True, "message": f"IP {data.ip_address} whitelisted"}


@router.get("/ip/stats")
@limiter.limit("30/minute")
async def get_ip_security_stats(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    admin: dict = Depends(get_admin_user)
):
    """Get IP security statistics (admin only)"""
    ip_service = await get_ip_security_service(db)
    return await ip_service.get_security_stats(days=days)


@router.get("/ip/activity/{ip_address}")
@limiter.limit("30/minute")
async def get_ip_activity(
    request: Request,
    ip_address: str,
    limit: int = Query(100, ge=1, le=500),
    admin: dict = Depends(get_admin_user)
):
    """Get activity history for a specific IP (admin only)"""
    ip_service = await get_ip_security_service(db)
    activities = await ip_service.get_ip_activity(ip_address=ip_address, limit=limit)
    return {"ip_address": ip_address, "activities": activities, "count": len(activities)}


# ============================================================================
# TWO-FACTOR AUTHENTICATION ENDPOINTS
# ============================================================================
@router.get("/2fa/status")
async def get_2fa_status(user: dict = Depends(get_current_user)):
    """Check if 2FA is enabled for the current user"""
    twofa_service = get_two_factor_service(db)
    is_enabled = await twofa_service.is_2fa_enabled(user["id"])
    return {
        "two_factor_enabled": is_enabled,
        "email": user.get("email", "")[:3] + "***" + "@" + user.get("email", "").split("@")[-1] if user.get("email") else ""
    }


@router.post("/2fa/enable/request")
@limiter.limit("5/minute")
async def request_enable_2fa(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Request to enable 2FA - sends OTP to user's email.
    User must verify OTP to complete enabling 2FA.
    """
    twofa_service = get_two_factor_service(db)
    
    # Check if already enabled
    if await twofa_service.is_2fa_enabled(user["id"]):
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    # Send OTP
    success, message = await twofa_service.generate_and_send_otp(
        user_id=user["id"],
        email=user.get("email", ""),
        purpose="enable_2fa"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


@router.post("/2fa/enable/verify")
@limiter.limit("10/minute")
async def verify_enable_2fa(
    request: Request,
    data: Verify2FARequest,
    user: dict = Depends(get_current_user)
):
    """
    Verify OTP to complete enabling 2FA.
    """
    twofa_service = get_two_factor_service(db)
    
    # Verify OTP
    success, message = await twofa_service.verify_otp(
        user_id=user["id"],
        otp=data.otp,
        purpose="enable_2fa"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Enable 2FA
    success, message = await twofa_service.enable_2fa(user["id"])
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return {"success": True, "message": "Two-factor authentication enabled successfully"}


@router.post("/2fa/disable/request")
@limiter.limit("5/minute")
async def request_disable_2fa(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Request to disable 2FA - sends OTP to user's email.
    User must verify OTP to complete disabling 2FA.
    """
    twofa_service = get_two_factor_service(db)
    
    # Check if enabled
    if not await twofa_service.is_2fa_enabled(user["id"]):
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    
    # Send OTP
    success, message = await twofa_service.generate_and_send_otp(
        user_id=user["id"],
        email=user.get("email", ""),
        purpose="disable_2fa"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


@router.post("/2fa/disable/verify")
@limiter.limit("10/minute")
async def verify_disable_2fa(
    request: Request,
    data: Verify2FARequest,
    user: dict = Depends(get_current_user)
):
    """
    Verify OTP to complete disabling 2FA.
    """
    twofa_service = get_two_factor_service(db)
    
    # Verify OTP
    success, message = await twofa_service.verify_otp(
        user_id=user["id"],
        otp=data.otp,
        purpose="disable_2fa"
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Disable 2FA
    success, message = await twofa_service.disable_2fa(user["id"])
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return {"success": True, "message": "Two-factor authentication disabled"}


@router.post("/2fa/verify")
@limiter.limit("10/minute")
async def verify_2fa_login(
    request: Request,
    data: Verify2FARequest
):
    """
    Verify 2FA OTP during login.
    Called after password verification if 2FA is enabled.
    """
    # This endpoint is typically called with a temporary session token
    # For now, we just validate the OTP format
    if not data.otp or len(data.otp) != 6 or not data.otp.isdigit():
        raise HTTPException(status_code=400, detail="Invalid OTP format")
    
    # The actual verification is done by the login flow
    # This endpoint just provides the interface
    return {"success": True, "message": "OTP format valid. Complete verification in login flow."}


@router.post("/2fa/resend")
@limiter.limit("3/minute")
async def resend_2fa_otp(
    request: Request,
    purpose: str = Query("login", description="Purpose of OTP"),
    user: dict = Depends(get_current_user)
):
    """
    Resend OTP code to user's email.
    Rate limited to prevent abuse.
    """
    twofa_service = get_two_factor_service(db)
    
    success, message = await twofa_service.generate_and_send_otp(
        user_id=user["id"],
        email=user.get("email", ""),
        purpose=purpose
    )
    
    if not success:
        raise HTTPException(status_code=429, detail=message)
    
    return {"success": True, "message": message}
