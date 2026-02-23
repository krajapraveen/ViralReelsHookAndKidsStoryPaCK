"""
Login Activity Routes - Admin Panel for User Login Tracking
CreatorStudio AI

Features:
- Track all login attempts (success/failure)
- IP geolocation via ip-api.com (free)
- Risk flag detection (New Country, New Device, Multiple Failed Attempts)
- Export CSV functionality
- Block IP and Force Logout capabilities
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
import os
import sys
import httpx
import csv
import io
import json
from user_agents import parse as parse_user_agent

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user
from security import limiter

router = APIRouter(prefix="/admin/login-activity", tags=["Admin - Login Activity"])

# Constants
DATA_RETENTION_DAYS = 30
IP_CACHE_HOURS = 72
MAX_FAILED_ATTEMPTS_FOR_RISK = 3


# =============================================================================
# MODELS
# =============================================================================
class LoginActivityRecord(BaseModel):
    user_id: Optional[str] = None
    identifier: str  # email/phone used
    timestamp: str
    status: str  # SUCCESS, FAILED, LOGOUT, EXPIRED
    failure_reason: Optional[str] = None
    ip_address: str
    ip_forwarded_raw: Optional[str] = None
    user_agent: str
    device_type: str  # Desktop, Mobile, Tablet
    browser: str
    os: str
    auth_method: str  # google, email_password, otp
    session_id: str
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    risk_flags: List[str] = []
    request_id: Optional[str] = None


class BlockIPRequest(BaseModel):
    ip_address: str
    reason: str = Field(min_length=5, max_length=500)
    duration_hours: int = Field(default=24, ge=1, le=8760)  # Max 1 year


class ForceLogoutRequest(BaseModel):
    user_id: str
    reason: str = Field(min_length=5, max_length=500)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def extract_client_ip(request: Request) -> tuple:
    """Extract client IP from request, handling proxies"""
    # Check Cloudflare header first
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip, request.headers.get("X-Forwarded-For", "")
    
    # Check X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        # Take the first IP (client IP)
        client_ip = forwarded.split(",")[0].strip()
        return client_ip, forwarded
    
    # Check X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip, ""
    
    # Fallback to direct connection
    return request.client.host if request.client else "unknown", ""


def parse_device_info(user_agent_string: str) -> dict:
    """Parse user agent to extract device info"""
    try:
        ua = parse_user_agent(user_agent_string)
        
        # Determine device type
        if ua.is_mobile:
            device_type = "Mobile"
        elif ua.is_tablet:
            device_type = "Tablet"
        elif ua.is_pc:
            device_type = "Desktop"
        else:
            device_type = "Unknown"
        
        return {
            "device_type": device_type,
            "browser": f"{ua.browser.family} {ua.browser.version_string}".strip(),
            "os": f"{ua.os.family} {ua.os.version_string}".strip()
        }
    except Exception as e:
        logger.warning(f"Failed to parse user agent: {e}")
        return {
            "device_type": "Unknown",
            "browser": "Unknown",
            "os": "Unknown"
        }


def mask_session_id(session_id: str) -> str:
    """Mask session ID for privacy - show first 6 and last 4"""
    if not session_id or len(session_id) < 12:
        return "****"
    return f"{session_id[:6]}...{session_id[-4:]}"


async def get_geo_from_ip(ip_address: str) -> dict:
    """Get geolocation from IP using ip-api.com (free, 45 req/min)"""
    # Skip for localhost/private IPs
    if ip_address in ["127.0.0.1", "localhost", "unknown"] or ip_address.startswith("192.168.") or ip_address.startswith("10."):
        return {"country": "Local", "region": "", "city": "", "isp": "Local Network"}
    
    # Check cache first
    cached = await db.ip_geo_cache.find_one({"ip": ip_address}, {"_id": 0})
    if cached:
        cache_time = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
        if datetime.now(timezone.utc) - cache_time < timedelta(hours=IP_CACHE_HOURS):
            return {
                "country": cached.get("country", ""),
                "region": cached.get("region", ""),
                "city": cached.get("city", ""),
                "isp": cached.get("isp", "")
            }
    
    # Call ip-api.com
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://ip-api.com/json/{ip_address}",
                params={"fields": "status,country,regionName,city,isp,org"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    geo_data = {
                        "country": data.get("country", ""),
                        "region": data.get("regionName", ""),
                        "city": data.get("city", ""),
                        "isp": data.get("isp") or data.get("org", "")
                    }
                    
                    # Cache the result
                    await db.ip_geo_cache.update_one(
                        {"ip": ip_address},
                        {"$set": {
                            "ip": ip_address,
                            **geo_data,
                            "cached_at": datetime.now(timezone.utc).isoformat()
                        }},
                        upsert=True
                    )
                    
                    return geo_data
    except Exception as e:
        logger.warning(f"IP geolocation lookup failed for {ip_address}: {e}")
    
    return {"country": "", "region": "", "city": "", "isp": ""}


async def detect_risk_flags(user_id: Optional[str], ip_address: str, country: str, device_fingerprint: str) -> List[str]:
    """Detect risk flags for the login attempt"""
    risk_flags = []
    
    if not user_id:
        return risk_flags
    
    # Check for multiple failed attempts in last hour
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    failed_count = await db.login_activity.count_documents({
        "user_id": user_id,
        "status": "FAILED",
        "timestamp": {"$gte": one_hour_ago}
    })
    if failed_count >= MAX_FAILED_ATTEMPTS_FOR_RISK:
        risk_flags.append("Multiple failed attempts")
    
    # Check for new country
    if country:
        previous_countries = await db.login_activity.distinct(
            "country",
            {"user_id": user_id, "status": "SUCCESS", "country": {"$nin": [None, ""]}}
        )
        if previous_countries and country not in previous_countries:
            risk_flags.append("New Country")
    
    # Check for new device
    if device_fingerprint:
        previous_devices = await db.login_activity.distinct(
            "device_fingerprint",
            {"user_id": user_id, "status": "SUCCESS"}
        )
        if previous_devices and device_fingerprint not in previous_devices:
            risk_flags.append("New Device")
    
    return risk_flags


async def log_login_activity(
    request: Request,
    user_id: Optional[str],
    identifier: str,
    status: str,
    auth_method: str,
    failure_reason: Optional[str] = None,
    background_tasks: Optional[BackgroundTasks] = None
):
    """Log a login activity event"""
    try:
        # Extract IP
        ip_address, ip_forwarded = extract_client_ip(request)
        
        # Parse user agent
        user_agent = request.headers.get("User-Agent", "")
        device_info = parse_device_info(user_agent)
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create device fingerprint for risk detection
        device_fingerprint = f"{device_info['browser']}_{device_info['os']}_{device_info['device_type']}"
        
        # Get geo data (async in background if possible)
        geo_data = await get_geo_from_ip(ip_address)
        
        # Detect risk flags
        risk_flags = await detect_risk_flags(
            user_id, ip_address, 
            geo_data.get("country", ""), 
            device_fingerprint
        )
        
        # Create activity record
        activity = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "identifier": identifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "failure_reason": failure_reason,
            "ip_address": ip_address,
            "ip_forwarded_raw": ip_forwarded,
            "user_agent": user_agent,
            "device_type": device_info["device_type"],
            "browser": device_info["browser"],
            "os": device_info["os"],
            "auth_method": auth_method,
            "session_id": session_id,
            "country": geo_data.get("country", ""),
            "region": geo_data.get("region", ""),
            "city": geo_data.get("city", ""),
            "isp": geo_data.get("isp", ""),
            "risk_flags": risk_flags,
            "device_fingerprint": device_fingerprint,
            "request_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.login_activity.insert_one(activity)
        
        # Log admin alert for high-risk logins
        if risk_flags and status == "SUCCESS":
            logger.warning(f"High-risk login detected for {identifier}: {risk_flags}")
        
        return session_id
        
    except Exception as e:
        logger.error(f"Failed to log login activity: {e}")
        return None


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================
@router.get("")
@limiter.limit("60/minute")
async def get_login_activity(
    request: Request,
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    user: Optional[str] = Query(None, description="Search by email or name"),
    status: Optional[str] = Query(None, description="Filter by status: SUCCESS, FAILED, LOGOUT, EXPIRED"),
    country: Optional[str] = Query(None, description="Filter by country"),
    city: Optional[str] = Query(None, description="Filter by city"),
    ip: Optional[str] = Query(None, description="Filter by IP address"),
    auth_method: Optional[str] = Query(None, description="Filter by auth method: google, email_password"),
    has_risk: Optional[bool] = Query(None, description="Filter entries with risk flags"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_admin_user)
):
    """Get paginated login activity with filters"""
    try:
        # Build query
        query = {}
        
        # Date range filter
        if from_date:
            query["timestamp"] = {"$gte": from_date}
        if to_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = to_date
            else:
                query["timestamp"] = {"$lte": to_date}
        
        # User search (email or name via user lookup)
        if user:
            # Find matching users
            user_query = {
                "$or": [
                    {"email": {"$regex": user, "$options": "i"}},
                    {"name": {"$regex": user, "$options": "i"}}
                ]
            }
            matching_users = await db.users.find(user_query, {"id": 1, "_id": 0}).to_list(100)
            user_ids = [u["id"] for u in matching_users]
            
            # Also search by identifier directly
            query["$or"] = [
                {"user_id": {"$in": user_ids}},
                {"identifier": {"$regex": user, "$options": "i"}}
            ]
        
        # Status filter
        if status:
            query["status"] = status.upper()
        
        # Location filters
        if country:
            query["country"] = {"$regex": country, "$options": "i"}
        if city:
            query["city"] = {"$regex": city, "$options": "i"}
        
        # IP filter
        if ip:
            query["ip_address"] = {"$regex": ip, "$options": "i"}
        
        # Auth method filter
        if auth_method:
            query["auth_method"] = auth_method.lower()
        
        # Risk flag filter
        if has_risk is True:
            query["risk_flags"] = {"$ne": []}
        elif has_risk is False:
            query["risk_flags"] = []
        
        # Execute query with pagination
        skip = (page - 1) * size
        total = await db.login_activity.count_documents(query)
        
        activities = await db.login_activity.find(
            query,
            {"_id": 0, "device_fingerprint": 0}
        ).sort("timestamp", -1).skip(skip).limit(size).to_list(size)
        
        # Enrich with user names
        user_ids = list(set([a.get("user_id") for a in activities if a.get("user_id")]))
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"id": {"$in": user_ids}},
                {"_id": 0, "id": 1, "name": 1, "email": 1}
            ).to_list(len(user_ids))
            users_map = {u["id"]: u for u in users}
        
        # Process activities
        for activity in activities:
            # Add user info
            if activity.get("user_id") and activity["user_id"] in users_map:
                user_info = users_map[activity["user_id"]]
                activity["user_name"] = user_info.get("name", "")
                activity["user_email"] = user_info.get("email", "")
            else:
                activity["user_name"] = ""
                activity["user_email"] = activity.get("identifier", "")
            
            # Mask session ID
            activity["session_id_masked"] = mask_session_id(activity.get("session_id", ""))
            
            # Format location
            location_parts = [
                activity.get("city", ""),
                activity.get("region", ""),
                activity.get("country", "")
            ]
            activity["location"] = ", ".join([p for p in location_parts if p])
        
        # Log admin access
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "VIEW_LOGIN_ACTIVITY",
            "details": {"filters": {"user": user, "status": status, "country": country}},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "activities": activities,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching login activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch login activity")


@router.get("/{activity_id}")
@limiter.limit("60/minute")
async def get_login_activity_detail(
    request: Request,
    activity_id: str,
    admin: dict = Depends(get_admin_user)
):
    """Get detailed login activity record"""
    try:
        activity = await db.login_activity.find_one(
            {"id": activity_id},
            {"_id": 0, "device_fingerprint": 0}
        )
        
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        # Get user info
        if activity.get("user_id"):
            user_data = await db.users.find_one(
                {"id": activity["user_id"]},
                {"_id": 0, "id": 1, "name": 1, "email": 1, "createdAt": 1}
            )
            if user_data:
                activity["user_info"] = user_data
        
        # Mask session ID
        activity["session_id_masked"] = mask_session_id(activity.get("session_id", ""))
        
        # Get related activity (same user, last 10)
        if activity.get("user_id"):
            related = await db.login_activity.find(
                {"user_id": activity["user_id"], "id": {"$ne": activity_id}},
                {"_id": 0, "id": 1, "timestamp": 1, "status": 1, "ip_address": 1, "country": 1}
            ).sort("timestamp", -1).limit(10).to_list(10)
            activity["related_activity"] = related
        
        # Log admin access
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "VIEW_LOGIN_ACTIVITY_DETAIL",
            "details": {"activity_id": activity_id},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return activity
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching login activity detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch activity detail")


@router.get("/export/csv")
@limiter.limit("10/minute")
async def export_login_activity_csv(
    request: Request,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    admin: dict = Depends(get_admin_user)
):
    """Export filtered login activity to CSV"""
    try:
        # Build query (same as list endpoint)
        query = {}
        if from_date:
            query["timestamp"] = {"$gte": from_date}
        if to_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = to_date
            else:
                query["timestamp"] = {"$lte": to_date}
        if status:
            query["status"] = status.upper()
        if country:
            query["country"] = {"$regex": country, "$options": "i"}
        if user:
            query["identifier"] = {"$regex": user, "$options": "i"}
        
        # Fetch all matching records (limit 10000)
        activities = await db.login_activity.find(
            query,
            {"_id": 0, "device_fingerprint": 0, "user_agent": 0}
        ).sort("timestamp", -1).limit(10000).to_list(10000)
        
        # Get user names
        user_ids = list(set([a.get("user_id") for a in activities if a.get("user_id")]))
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"id": {"$in": user_ids}},
                {"_id": 0, "id": 1, "name": 1, "email": 1}
            ).to_list(len(user_ids))
            users_map = {u["id"]: u for u in users}
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Timestamp (UTC)", "User Name", "Email", "Status", "Auth Method",
            "IP Address", "Country", "Region", "City", "ISP",
            "Device Type", "Browser", "OS", "Risk Flags", "Failure Reason"
        ])
        
        # Data rows
        for activity in activities:
            user_info = users_map.get(activity.get("user_id"), {})
            writer.writerow([
                activity.get("timestamp", ""),
                user_info.get("name", ""),
                activity.get("identifier", ""),
                activity.get("status", ""),
                activity.get("auth_method", ""),
                activity.get("ip_address", ""),
                activity.get("country", ""),
                activity.get("region", ""),
                activity.get("city", ""),
                activity.get("isp", ""),
                activity.get("device_type", ""),
                activity.get("browser", ""),
                activity.get("os", ""),
                ", ".join(activity.get("risk_flags", [])),
                activity.get("failure_reason", "")
            ])
        
        # Log export
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "EXPORT_LOGIN_ACTIVITY",
            "details": {"record_count": len(activities), "filters": {"status": status, "country": country}},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Return CSV response
        output.seek(0)
        filename = f"login_activity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting login activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


@router.post("/block-ip")
@limiter.limit("10/minute")
async def block_ip_address(
    request: Request,
    data: BlockIPRequest,
    admin: dict = Depends(get_admin_user)
):
    """Block an IP address from logging in"""
    try:
        # Check if already blocked
        existing = await db.blocked_ips.find_one({"ip_address": data.ip_address, "active": True})
        if existing:
            raise HTTPException(status_code=400, detail="IP address is already blocked")
        
        # Calculate expiry
        expires_at = datetime.now(timezone.utc) + timedelta(hours=data.duration_hours)
        
        # Create block record
        block = {
            "id": str(uuid.uuid4()),
            "ip_address": data.ip_address,
            "reason": data.reason,
            "blocked_by": admin["id"],
            "blocked_by_email": admin.get("email", ""),
            "blocked_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
            "duration_hours": data.duration_hours,
            "active": True
        }
        
        await db.blocked_ips.insert_one(block)
        
        # Log action
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "BLOCK_IP",
            "details": {"ip_address": data.ip_address, "reason": data.reason, "duration_hours": data.duration_hours},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.warning(f"IP blocked by admin {admin.get('email')}: {data.ip_address} - {data.reason}")
        
        return {
            "success": True,
            "message": f"IP {data.ip_address} blocked for {data.duration_hours} hours",
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to block IP")


@router.delete("/block-ip/{ip_address}")
@limiter.limit("10/minute")
async def unblock_ip_address(
    request: Request,
    ip_address: str,
    admin: dict = Depends(get_admin_user)
):
    """Unblock an IP address"""
    try:
        result = await db.blocked_ips.update_one(
            {"ip_address": ip_address, "active": True},
            {"$set": {
                "active": False,
                "unblocked_by": admin["id"],
                "unblocked_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="IP not found in block list")
        
        # Log action
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "UNBLOCK_IP",
            "details": {"ip_address": ip_address},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {"success": True, "message": f"IP {ip_address} unblocked"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to unblock IP")


@router.get("/blocked-ips/list")
@limiter.limit("30/minute")
async def get_blocked_ips(
    request: Request,
    admin: dict = Depends(get_admin_user)
):
    """Get list of currently blocked IPs"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        blocked = await db.blocked_ips.find(
            {"active": True, "expires_at": {"$gt": now}},
            {"_id": 0}
        ).sort("blocked_at", -1).to_list(100)
        
        return {"blocked_ips": blocked}
        
    except Exception as e:
        logger.error(f"Error fetching blocked IPs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch blocked IPs")


@router.post("/force-logout")
@limiter.limit("10/minute")
async def force_logout_user(
    request: Request,
    data: ForceLogoutRequest,
    admin: dict = Depends(get_admin_user)
):
    """Force logout a user by invalidating their sessions"""
    try:
        # Verify user exists
        user = await db.users.find_one({"id": data.user_id}, {"_id": 0, "email": 1, "name": 1})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Increment force_logout_count to invalidate existing tokens
        await db.users.update_one(
            {"id": data.user_id},
            {
                "$inc": {"force_logout_count": 1},
                "$set": {
                    "last_force_logout": datetime.now(timezone.utc).isoformat(),
                    "force_logout_reason": data.reason
                }
            }
        )
        
        # Log the logout activity
        await db.login_activity.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": data.user_id,
            "identifier": user.get("email", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "FORCE_LOGOUT",
            "failure_reason": f"Admin force logout: {data.reason}",
            "ip_address": "admin_action",
            "user_agent": "",
            "device_type": "",
            "browser": "",
            "os": "",
            "auth_method": "admin",
            "session_id": "force_logout",
            "risk_flags": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Log admin action
        await db.admin_audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": admin["id"],
            "admin_email": admin.get("email", ""),
            "action": "FORCE_LOGOUT_USER",
            "details": {"user_id": data.user_id, "user_email": user.get("email"), "reason": data.reason},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.warning(f"Force logout by admin {admin.get('email')}: user {user.get('email')} - {data.reason}")
        
        return {
            "success": True,
            "message": f"User {user.get('email')} has been logged out from all devices"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error forcing logout: {e}")
        raise HTTPException(status_code=500, detail="Failed to force logout user")


@router.get("/stats/summary")
@limiter.limit("30/minute")
async def get_login_stats(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    admin: dict = Depends(get_admin_user)
):
    """Get login activity statistics summary"""
    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Total logins
        total_logins = await db.login_activity.count_documents({"timestamp": {"$gte": start_date}})
        successful_logins = await db.login_activity.count_documents({"timestamp": {"$gte": start_date}, "status": "SUCCESS"})
        failed_logins = await db.login_activity.count_documents({"timestamp": {"$gte": start_date}, "status": "FAILED"})
        
        # Unique users
        unique_users = len(await db.login_activity.distinct("user_id", {"timestamp": {"$gte": start_date}, "user_id": {"$ne": None}}))
        
        # Top countries
        country_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}, "country": {"$ne": ""}}},
            {"$group": {"_id": "$country", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_countries = await db.login_activity.aggregate(country_pipeline).to_list(10)
        
        # Auth method breakdown
        auth_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$auth_method", "count": {"$sum": 1}}}
        ]
        auth_breakdown = await db.login_activity.aggregate(auth_pipeline).to_list(10)
        
        # Device type breakdown
        device_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$device_type", "count": {"$sum": 1}}}
        ]
        device_breakdown = await db.login_activity.aggregate(device_pipeline).to_list(10)
        
        # Risk flag count
        risky_logins = await db.login_activity.count_documents({
            "timestamp": {"$gte": start_date},
            "risk_flags": {"$ne": []}
        })
        
        # Daily trend
        daily_pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$addFields": {"date": {"$substr": ["$timestamp", 0, 10]}}},
            {"$group": {
                "_id": "$date",
                "total": {"$sum": 1},
                "success": {"$sum": {"$cond": [{"$eq": ["$status", "SUCCESS"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "FAILED"]}, 1, 0]}}
            }},
            {"$sort": {"_id": 1}}
        ]
        daily_trend = await db.login_activity.aggregate(daily_pipeline).to_list(days)
        
        return {
            "period_days": days,
            "total_logins": total_logins,
            "successful_logins": successful_logins,
            "failed_logins": failed_logins,
            "success_rate": round((successful_logins / total_logins * 100) if total_logins > 0 else 0, 1),
            "unique_users": unique_users,
            "risky_logins": risky_logins,
            "top_countries": [{"country": c["_id"], "count": c["count"]} for c in top_countries],
            "auth_methods": [{"method": a["_id"], "count": a["count"]} for a in auth_breakdown],
            "device_types": [{"type": d["_id"], "count": d["count"]} for d in device_breakdown],
            "daily_trend": daily_trend
        }
        
    except Exception as e:
        logger.error(f"Error fetching login stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


# =============================================================================
# DATA CLEANUP (Background Task)
# =============================================================================
async def cleanup_old_login_activity():
    """Delete login activity older than retention period"""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_DAYS)).isoformat()
        result = await db.login_activity.delete_many({"timestamp": {"$lt": cutoff}})
        if result.deleted_count > 0:
            logger.info(f"Cleaned up {result.deleted_count} old login activity records")
        
        # Also cleanup expired IP blocks
        now = datetime.now(timezone.utc).isoformat()
        await db.blocked_ips.update_many(
            {"expires_at": {"$lt": now}, "active": True},
            {"$set": {"active": False}}
        )
        
        # Cleanup old IP geo cache
        cache_cutoff = (datetime.now(timezone.utc) - timedelta(hours=IP_CACHE_HOURS * 2)).isoformat()
        await db.ip_geo_cache.delete_many({"cached_at": {"$lt": cache_cutoff}})
        
    except Exception as e:
        logger.error(f"Error cleaning up login activity: {e}")


# Helper function to check if IP is blocked
async def is_ip_blocked(ip_address: str) -> bool:
    """Check if an IP address is currently blocked"""
    now = datetime.now(timezone.utc).isoformat()
    blocked = await db.blocked_ips.find_one({
        "ip_address": ip_address,
        "active": True,
        "expires_at": {"$gt": now}
    })
    return blocked is not None
