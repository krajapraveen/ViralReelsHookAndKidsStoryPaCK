"""
Notification Routes
API endpoints for user notifications
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from services.notification_service import get_notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class MarkReadRequest(BaseModel):
    notification_ids: Optional[List[str]] = None  # If None, mark all as read


@router.get("")
async def get_notifications(
    limit: int = 50,
    include_read: bool = True,
    user: dict = Depends(get_current_user)
):
    """Get all notifications for the current user"""
    service = get_notification_service(db)
    
    notifications = await service.get_user_notifications(
        user_id=user["id"],
        limit=limit,
        include_read=include_read
    )
    
    unread_count = await service.get_unread_count(user["id"])
    
    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "total": len(notifications)
    }


@router.get("/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    """Get count of unread notifications"""
    service = get_notification_service(db)
    count = await service.get_unread_count(user["id"])
    
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: dict = Depends(get_current_user)
):
    """Mark a specific notification as read"""
    service = get_notification_service(db)
    
    success = await service.mark_as_read(notification_id, user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True, "message": "Notification marked as read"}


@router.post("/mark-all-read")
async def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    service = get_notification_service(db)
    
    count = await service.mark_all_as_read(user["id"])
    
    return {"success": True, "marked_count": count}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a specific notification"""
    service = get_notification_service(db)
    
    success = await service.delete_notification(notification_id, user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True, "message": "Notification deleted"}


@router.delete("")
async def delete_all_notifications(user: dict = Depends(get_current_user)):
    """Delete all notifications for the current user"""
    service = get_notification_service(db)
    
    count = await service.delete_all_notifications(user["id"])
    
    return {"success": True, "deleted_count": count}


# Poll endpoint for real-time updates (client-side polling)
@router.get("/poll")
async def poll_notifications(
    last_check: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Poll for new notifications since last check"""
    service = get_notification_service(db)
    
    # Get unread count
    unread_count = await service.get_unread_count(user["id"])
    
    # Get recent notifications (last 5 unread)
    notifications = await service.get_user_notifications(
        user_id=user["id"],
        limit=5,
        include_read=False
    )
    
    return {
        "unread_count": unread_count,
        "new_notifications": notifications,
        "has_new": len(notifications) > 0
    }
