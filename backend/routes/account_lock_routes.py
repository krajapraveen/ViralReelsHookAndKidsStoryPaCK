"""
Account Lock Management Routes
API endpoints for locking/unlocking user accounts
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/account-management", tags=["Account Management"])


class LockAccountRequest(BaseModel):
    user_id: str
    reason: str
    duration_hours: Optional[int] = None  # None = permanent until manual unlock


class UnlockAccountRequest(BaseModel):
    user_id: str
    reason: Optional[str] = "Manual unlock by admin"


class BulkLockRequest(BaseModel):
    user_ids: List[str]
    reason: str
    duration_hours: Optional[int] = None


class AutoLockConfigRequest(BaseModel):
    enabled: bool
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    suspicious_ip_threshold: int = 10


def require_admin(user: dict):
    """Check if user is admin"""
    user_role = user.get("role", "").upper()
    if user_role not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/users")
async def get_all_users_with_lock_status(
    page: int = 1,
    limit: int = 50,
    filter_locked: Optional[bool] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all users with their lock status"""
    require_admin(user)
    
    query = {}
    
    if filter_locked is not None:
        query["isLocked"] = filter_locked
    
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    
    users = await db.users.find(
        query,
        {"_id": 0, "password": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.users.count_documents(query)
    
    # Get lockout info for each user
    for u in users:
        lockout = await db.account_lockouts.find_one(
            {"email": u.get("email")},
            {"_id": 0}
        )
        u["lockout_info"] = lockout
        
        # Check if lock has expired
        if lockout and lockout.get("lockUntil"):
            lock_until = datetime.fromisoformat(lockout["lockUntil"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > lock_until:
                u["isLocked"] = False
                u["lockExpired"] = True
    
    return {
        "success": True,
        "users": users,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


@router.post("/lock")
async def lock_user_account(
    request: LockAccountRequest,
    user: dict = Depends(get_current_user)
):
    """Lock a user account"""
    require_admin(user)
    
    # Get the target user
    target_user = await db.users.find_one({"id": request.user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate lock expiry
    lock_until = None
    if request.duration_hours:
        lock_until = datetime.now(timezone.utc) + timedelta(hours=request.duration_hours)
    
    # Update user record
    await db.users.update_one(
        {"id": request.user_id},
        {
            "$set": {
                "isLocked": True,
                "lockedAt": datetime.now(timezone.utc).isoformat(),
                "lockedBy": user.get("email"),
                "lockReason": request.reason,
                "lockUntil": lock_until.isoformat() if lock_until else None
            }
        }
    )
    
    # Create/update lockout record
    await db.account_lockouts.update_one(
        {"email": target_user.get("email")},
        {
            "$set": {
                "email": target_user.get("email"),
                "userId": request.user_id,
                "isLocked": True,
                "lockedAt": datetime.now(timezone.utc).isoformat(),
                "lockedBy": user.get("email"),
                "reason": request.reason,
                "lockUntil": lock_until.isoformat() if lock_until else None,
                "type": "MANUAL"
            }
        },
        upsert=True
    )
    
    # Log the action
    await db.audit_logs.insert_one({
        "action": "ACCOUNT_LOCKED",
        "admin_id": user.get("id"),
        "admin_email": user.get("email"),
        "target_user_id": request.user_id,
        "target_user_email": target_user.get("email"),
        "reason": request.reason,
        "duration_hours": request.duration_hours,
        "lock_until": lock_until.isoformat() if lock_until else "PERMANENT",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "message": f"Account {target_user.get('email')} has been locked",
        "lock_until": lock_until.isoformat() if lock_until else "PERMANENT"
    }


@router.post("/unlock")
async def unlock_user_account(
    request: UnlockAccountRequest,
    user: dict = Depends(get_current_user)
):
    """Unlock a user account"""
    require_admin(user)
    
    # Get the target user
    target_user = await db.users.find_one({"id": request.user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user record
    await db.users.update_one(
        {"id": request.user_id},
        {
            "$set": {
                "isLocked": False,
                "unlockedAt": datetime.now(timezone.utc).isoformat(),
                "unlockedBy": user.get("email")
            },
            "$unset": {
                "lockedAt": "",
                "lockReason": "",
                "lockUntil": ""
            }
        }
    )
    
    # Remove lockout record
    await db.account_lockouts.delete_one({"email": target_user.get("email")})
    
    # Clear failed attempts
    await db.failed_login_attempts.delete_many({"email": target_user.get("email")})
    
    # Log the action
    await db.audit_logs.insert_one({
        "action": "ACCOUNT_UNLOCKED",
        "admin_id": user.get("id"),
        "admin_email": user.get("email"),
        "target_user_id": request.user_id,
        "target_user_email": target_user.get("email"),
        "reason": request.reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "message": f"Account {target_user.get('email')} has been unlocked"
    }


@router.post("/bulk-lock")
async def bulk_lock_accounts(
    request: BulkLockRequest,
    user: dict = Depends(get_current_user)
):
    """Lock multiple user accounts at once"""
    require_admin(user)
    
    results = []
    lock_until = None
    if request.duration_hours:
        lock_until = datetime.now(timezone.utc) + timedelta(hours=request.duration_hours)
    
    for user_id in request.user_ids:
        target_user = await db.users.find_one({"id": user_id})
        if not target_user:
            results.append({"user_id": user_id, "success": False, "error": "User not found"})
            continue
        
        # Don't lock admin accounts in bulk
        if target_user.get("role", "").upper() == "ADMIN":
            results.append({"user_id": user_id, "success": False, "error": "Cannot bulk-lock admin accounts"})
            continue
        
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "isLocked": True,
                    "lockedAt": datetime.now(timezone.utc).isoformat(),
                    "lockedBy": user.get("email"),
                    "lockReason": request.reason,
                    "lockUntil": lock_until.isoformat() if lock_until else None
                }
            }
        )
        
        await db.account_lockouts.update_one(
            {"email": target_user.get("email")},
            {
                "$set": {
                    "email": target_user.get("email"),
                    "userId": user_id,
                    "isLocked": True,
                    "lockedAt": datetime.now(timezone.utc).isoformat(),
                    "lockedBy": user.get("email"),
                    "reason": request.reason,
                    "lockUntil": lock_until.isoformat() if lock_until else None,
                    "type": "BULK_MANUAL"
                }
            },
            upsert=True
        )
        
        results.append({"user_id": user_id, "email": target_user.get("email"), "success": True})
    
    # Log the bulk action
    await db.audit_logs.insert_one({
        "action": "BULK_ACCOUNT_LOCK",
        "admin_id": user.get("id"),
        "admin_email": user.get("email"),
        "user_count": len(request.user_ids),
        "successful": len([r for r in results if r.get("success")]),
        "reason": request.reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "message": f"Bulk lock completed: {len([r for r in results if r.get('success')])} of {len(request.user_ids)} accounts locked",
        "results": results
    }


@router.post("/bulk-unlock")
async def bulk_unlock_accounts(
    user_ids: List[str],
    user: dict = Depends(get_current_user)
):
    """Unlock multiple user accounts at once"""
    require_admin(user)
    
    results = []
    
    for user_id in user_ids:
        target_user = await db.users.find_one({"id": user_id})
        if not target_user:
            results.append({"user_id": user_id, "success": False, "error": "User not found"})
            continue
        
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "isLocked": False,
                    "unlockedAt": datetime.now(timezone.utc).isoformat(),
                    "unlockedBy": user.get("email")
                },
                "$unset": {
                    "lockedAt": "",
                    "lockReason": "",
                    "lockUntil": ""
                }
            }
        )
        
        await db.account_lockouts.delete_one({"email": target_user.get("email")})
        await db.failed_login_attempts.delete_many({"email": target_user.get("email")})
        
        results.append({"user_id": user_id, "email": target_user.get("email"), "success": True})
    
    # Log the bulk action
    await db.audit_logs.insert_one({
        "action": "BULK_ACCOUNT_UNLOCK",
        "admin_id": user.get("id"),
        "admin_email": user.get("email"),
        "user_count": len(user_ids),
        "successful": len([r for r in results if r.get("success")]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "message": f"Bulk unlock completed: {len([r for r in results if r.get('success')])} of {len(user_ids)} accounts unlocked",
        "results": results
    }


@router.get("/auto-lock/config")
async def get_auto_lock_config(user: dict = Depends(get_current_user)):
    """Get auto-lock configuration"""
    require_admin(user)
    
    config = await db.system_config.find_one({"type": "auto_lock"}, {"_id": 0})
    
    if not config:
        config = {
            "type": "auto_lock",
            "enabled": True,
            "max_failed_attempts": 5,
            "lockout_duration_minutes": 30,
            "suspicious_ip_threshold": 10
        }
    
    return {"success": True, "config": config}


@router.post("/auto-lock/config")
async def update_auto_lock_config(
    request: AutoLockConfigRequest,
    user: dict = Depends(get_current_user)
):
    """Update auto-lock configuration"""
    require_admin(user)
    
    await db.system_config.update_one(
        {"type": "auto_lock"},
        {
            "$set": {
                "type": "auto_lock",
                "enabled": request.enabled,
                "max_failed_attempts": request.max_failed_attempts,
                "lockout_duration_minutes": request.lockout_duration_minutes,
                "suspicious_ip_threshold": request.suspicious_ip_threshold,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user.get("email")
            }
        },
        upsert=True
    )
    
    await db.audit_logs.insert_one({
        "action": "AUTO_LOCK_CONFIG_UPDATED",
        "admin_id": user.get("id"),
        "admin_email": user.get("email"),
        "config": {
            "enabled": request.enabled,
            "max_failed_attempts": request.max_failed_attempts,
            "lockout_duration_minutes": request.lockout_duration_minutes,
            "suspicious_ip_threshold": request.suspicious_ip_threshold
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "message": "Auto-lock configuration updated"}


@router.get("/lockout-history")
async def get_lockout_history(
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """Get history of account lockouts"""
    require_admin(user)
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    lockouts = await db.audit_logs.find(
        {
            "action": {"$in": ["ACCOUNT_LOCKED", "ACCOUNT_UNLOCKED", "BULK_ACCOUNT_LOCK", "BULK_ACCOUNT_UNLOCK"]},
            "timestamp": {"$gte": start_date.isoformat()}
        },
        {"_id": 0}
    ).sort("timestamp", -1).to_list(500)
    
    return {
        "success": True,
        "period_days": days,
        "total_events": len(lockouts),
        "history": lockouts
    }


@router.get("/currently-locked")
async def get_currently_locked_accounts(user: dict = Depends(get_current_user)):
    """Get list of currently locked accounts"""
    require_admin(user)
    
    locked_accounts = await db.account_lockouts.find(
        {"isLocked": True},
        {"_id": 0}
    ).to_list(1000)
    
    # Check for expired locks
    now = datetime.now(timezone.utc)
    active_locks = []
    expired_locks = []
    
    for lock in locked_accounts:
        if lock.get("lockUntil"):
            try:
                lock_until = datetime.fromisoformat(lock["lockUntil"].replace("Z", "+00:00"))
                if now > lock_until:
                    expired_locks.append(lock)
                    continue
            except:
                pass
        active_locks.append(lock)
    
    return {
        "success": True,
        "total_locked": len(active_locks),
        "expired_locks": len(expired_locks),
        "locked_accounts": active_locks,
        "expired_but_not_cleared": expired_locks
    }
