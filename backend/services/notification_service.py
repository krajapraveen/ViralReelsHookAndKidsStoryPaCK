"""
Notification Service
Handles user notifications for completed generations, downloads, and system events
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Notification types
NOTIFICATION_TYPES = {
    "GENERATION_COMPLETE": "generation_complete",
    "GENERATION_FAILED": "generation_failed",
    "DOWNLOAD_READY": "download_ready",
    "DOWNLOAD_EXPIRING": "download_expiring",
    "CREDIT_LOW": "credit_low",
    "REFUND_ISSUED": "refund_issued",
    "SYSTEM": "system"
}

# Feature display names
FEATURE_NAMES = {
    "comic_avatar": "Comic Avatar",
    "comic_strip": "Comic Strip",
    "comic_storybook": "Comic Storybook",
    "gif_maker": "GIF Maker",
    "reaction_gif": "Reaction GIF",
    "reel_generator": "Reel Generator",
    "story_generator": "Story Generator",
    "coloring_book": "Coloring Book",
    "bedtime_story": "Bedtime Story",
    "thumbnail_generator": "Thumbnail Generator",
    "brand_story": "Brand Story",
    "offer_generator": "Offer Generator",
    "story_hook": "Story Hook",
    "caption_rewriter": "Caption Rewriter"
}


class NotificationService:
    """Service for managing user notifications"""
    
    def __init__(self, db):
        self.db = db
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        feature: Optional[str] = None,
        job_id: Optional[str] = None,
        download_url: Optional[str] = None,
        download_id: Optional[str] = None,
        action_url: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Create a new notification for a user"""
        import uuid
        
        notification_id = f"notif_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        
        notification = {
            "id": notification_id,
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "feature": feature,
            "job_id": job_id,
            "download_url": download_url,
            "download_id": download_id,
            "action_url": action_url,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "read": False,
            "created_at": now.isoformat(),
            "metadata": metadata or {}
        }
        
        await self.db.notifications.insert_one(notification)
        logger.info(f"Created notification {notification_id} for user {user_id}: {title}")
        
        return {
            "id": notification_id,
            "type": notification_type,
            "title": title,
            "message": message
        }
    
    async def notify_generation_complete(
        self,
        user_id: str,
        feature: str,
        job_id: str,
        download_url: Optional[str] = None,
        download_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Dict:
        """Send notification when a generation job completes"""
        feature_name = FEATURE_NAMES.get(feature, feature.replace("_", " ").title())
        
        return await self.create_notification(
            user_id=user_id,
            notification_type=NOTIFICATION_TYPES["GENERATION_COMPLETE"],
            title=f"{feature_name} Ready!",
            message=f"Your {feature_name.lower()} is ready for download.",
            feature=feature,
            job_id=job_id,
            download_url=download_url,
            download_id=download_id,
            action_url=f"/app/{feature.replace('_', '-')}" if feature else None,
            expires_at=expires_at
        )
    
    async def notify_generation_failed(
        self,
        user_id: str,
        feature: str,
        job_id: str,
        error_message: Optional[str] = None,
        refund_issued: bool = False
    ) -> Dict:
        """Send notification when a generation job fails"""
        feature_name = FEATURE_NAMES.get(feature, feature.replace("_", " ").title())
        
        message = f"Your {feature_name.lower()} generation failed."
        if refund_issued:
            message += " Credits have been refunded to your account."
        elif error_message:
            message += f" Error: {error_message}"
        
        return await self.create_notification(
            user_id=user_id,
            notification_type=NOTIFICATION_TYPES["GENERATION_FAILED"],
            title=f"{feature_name} Failed",
            message=message,
            feature=feature,
            job_id=job_id,
            metadata={"refund_issued": refund_issued, "error": error_message}
        )
    
    async def notify_download_ready(
        self,
        user_id: str,
        download_id: str,
        filename: str,
        download_url: str,
        expires_at: datetime,
        feature: Optional[str] = None
    ) -> Dict:
        """Send notification when a download is ready"""
        remaining_minutes = int((expires_at - datetime.now(timezone.utc)).total_seconds() / 60)
        
        return await self.create_notification(
            user_id=user_id,
            notification_type=NOTIFICATION_TYPES["DOWNLOAD_READY"],
            title="Download Ready",
            message=f"Your file '{filename}' is ready. Available for {remaining_minutes} minutes.",
            feature=feature,
            download_id=download_id,
            download_url=download_url,
            expires_at=expires_at
        )
    
    async def notify_refund_issued(
        self,
        user_id: str,
        amount: int,
        reason: str,
        feature: Optional[str] = None
    ) -> Dict:
        """Send notification when a refund is issued"""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NOTIFICATION_TYPES["REFUND_ISSUED"],
            title="Refund Issued",
            message=f"{amount} credits have been refunded to your account. Reason: {reason}",
            feature=feature,
            metadata={"refund_amount": amount, "reason": reason}
        )
    
    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50,
        include_read: bool = True
    ) -> List[Dict]:
        """Get all notifications for a user"""
        query = {"user_id": user_id}
        if not include_read:
            query["read"] = False
        
        notifications = await self.db.notifications.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return notifications
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user"""
        return await self.db.notifications.count_documents({
            "user_id": user_id,
            "read": False
        })
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        result = await self.db.notifications.update_one(
            {"id": notification_id, "user_id": user_id},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
        )
        return result.modified_count > 0
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        result = await self.db.notifications.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
        )
        return result.modified_count
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        result = await self.db.notifications.delete_one({
            "id": notification_id,
            "user_id": user_id
        })
        return result.deleted_count > 0
    
    async def delete_all_notifications(self, user_id: str) -> int:
        """Delete all notifications for a user"""
        result = await self.db.notifications.delete_many({"user_id": user_id})
        return result.deleted_count
    
    async def cleanup_old_notifications(self, days: int = 7) -> int:
        """Remove notifications older than specified days"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.notifications.delete_many({
            "created_at": {"$lt": cutoff.isoformat()}
        })
        if result.deleted_count > 0:
            logger.info(f"Cleaned up {result.deleted_count} old notifications")
        return result.deleted_count


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service(db) -> NotificationService:
    """Get or create notification service singleton"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService(db)
    return _notification_service
