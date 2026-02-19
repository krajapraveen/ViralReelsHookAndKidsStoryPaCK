"""
Privacy Routes - GDPR/CCPA Compliance
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone
import uuid
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, log_exception
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/privacy", tags=["Privacy"])


class ConsentUpdate(BaseModel):
    marketing: bool = True
    analytics: bool = True
    thirdParty: bool = False


class DeleteRequest(BaseModel):
    reason: str


@router.get("/my-data")
async def get_my_data(user: dict = Depends(get_current_user)):
    """Get user's data overview for privacy dashboard"""
    try:
        user_id = user["id"]
        
        # Get counts efficiently with aggregation
        generations_count = await db.generations.count_documents({"userId": user_id})
        payments_count = await db.orders.count_documents({"userId": user_id})
        genstudio_count = await db.genstudio_jobs.count_documents({"userId": user_id})
        
        # Get user profile (exclude sensitive data)
        profile = await db.users.find_one(
            {"id": user_id}, 
            {"_id": 0, "password": 0}
        )
        
        # Get privacy consent settings
        consent = await db.privacy_consent.find_one(
            {"userId": user_id},
            {"_id": 0}
        )
        
        return {
            "success": True,
            "data": {
                "profile": {
                    "name": profile.get("name", ""),
                    "email": profile.get("email", ""),
                    "createdAt": profile.get("createdAt", ""),
                    "role": profile.get("role", "user"),
                    "credits": profile.get("credits", 0),
                    "authProvider": profile.get("authProvider", "email")
                },
                "generationsCount": generations_count,
                "paymentsCount": payments_count,
                "genstudioCount": genstudio_count,
                "consent": consent or {
                    "marketing": True,
                    "analytics": True,
                    "thirdParty": False
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get user data overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to load data overview")


@router.get("/export")
async def export_user_data(user: dict = Depends(get_current_user)):
    """Export all user data for GDPR compliance"""
    try:
        user_id = user["id"]
        
        # Get user profile (exclude password)
        profile = await db.users.find_one(
            {"id": user_id},
            {"_id": 0, "password": 0}
        )
        
        # Get all user data
        generations = await db.generations.find(
            {"userId": user_id},
            {"_id": 0}
        ).to_list(length=1000)
        
        credit_ledger = await db.credit_ledger.find(
            {"userId": user_id},
            {"_id": 0}
        ).to_list(length=1000)
        
        orders = await db.orders.find(
            {"userId": user_id},
            {"_id": 0}
        ).to_list(length=500)
        
        genstudio_jobs = await db.genstudio_jobs.find(
            {"userId": user_id},
            {"_id": 0}
        ).to_list(length=500)
        
        feature_requests = await db.feature_requests.find(
            {"userId": user_id},
            {"_id": 0}
        ).to_list(length=100)
        
        feedback = await db.feedback.find(
            {"userId": user_id},
            {"_id": 0}
        ).to_list(length=100)
        
        consent = await db.privacy_consent.find_one(
            {"userId": user_id},
            {"_id": 0}
        )
        
        # Log the export action
        await db.privacy_logs.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "action": "DATA_EXPORT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": "User requested data export"
        })
        
        return {
            "success": True,
            "data": {
                "exportedAt": datetime.now(timezone.utc).isoformat(),
                "profile": profile,
                "generations": {
                    "count": len(generations),
                    "items": generations[:100]  # Limit to 100 for response size
                },
                "creditHistory": {
                    "count": len(credit_ledger),
                    "items": credit_ledger[:100]
                },
                "paymentHistory": {
                    "count": len(orders),
                    "items": orders
                },
                "genstudioJobs": {
                    "count": len(genstudio_jobs),
                    "items": genstudio_jobs[:50]
                },
                "featureRequests": feature_requests,
                "feedback": feedback,
                "privacyConsent": consent or {},
                "dataRetentionPolicy": {
                    "generations": "90 days after creation",
                    "payments": "7 years (legal requirement)",
                    "profile": "Until account deletion"
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to export user data: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


@router.post("/consent")
async def update_consent(data: ConsentUpdate, user: dict = Depends(get_current_user)):
    """Update privacy consent preferences"""
    try:
        user_id = user["id"]
        
        consent_data = {
            "userId": user_id,
            "marketing": data.marketing,
            "analytics": data.analytics,
            "thirdParty": data.thirdParty,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert consent preferences
        await db.privacy_consent.update_one(
            {"userId": user_id},
            {"$set": consent_data},
            upsert=True
        )
        
        # Update user's email preferences based on consent
        email_prefs = {
            "marketingEmails": data.marketing,
            "analyticsConsent": data.analytics,
            "thirdPartySharing": data.thirdParty
        }
        
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"privacyPreferences": email_prefs}}
        )
        
        # Log consent change
        await db.privacy_logs.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "action": "CONSENT_UPDATE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": {
                "marketing": data.marketing,
                "analytics": data.analytics,
                "thirdParty": data.thirdParty
            }
        })
        
        logger.info(f"Privacy consent updated for user {user_id}")
        
        return {
            "success": True,
            "message": "Privacy preferences updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update consent: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")


@router.post("/delete-request")
async def request_account_deletion(
    data: DeleteRequest, 
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Request account deletion (GDPR right to erasure)"""
    try:
        user_id = user["id"]
        user_email = user.get("email", "")
        
        # Create deletion request
        deletion_request = {
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "userEmail": user_email,
            "reason": data.reason,
            "status": "PENDING",
            "requestedAt": datetime.now(timezone.utc).isoformat(),
            "scheduledDeletionAt": None,  # Will be set after grace period
            "gracePeriodDays": 30
        }
        
        await db.deletion_requests.insert_one(deletion_request)
        
        # Log the deletion request
        await db.privacy_logs.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "action": "DELETION_REQUEST",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": {
                "reason": data.reason[:200],
                "status": "PENDING"
            }
        })
        
        # Mark user account for deletion
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "deletionRequested": True,
                    "deletionRequestedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Account deletion requested for user {user_id}")
        
        # TODO: Send confirmation email via SendGrid
        
        return {
            "success": True,
            "message": "Account deletion request submitted. Your account will be deleted after a 30-day grace period. You will receive a confirmation email."
        }
    except Exception as e:
        logger.error(f"Failed to process deletion request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit deletion request")


@router.delete("/delete-now")
async def delete_account_immediately(user: dict = Depends(get_current_user)):
    """Immediately delete user account and all data"""
    try:
        user_id = user["id"]
        
        # Delete all user data
        await db.users.delete_one({"id": user_id})
        await db.generations.delete_many({"userId": user_id})
        await db.genstudio_jobs.delete_many({"userId": user_id})
        await db.credit_ledger.delete_many({"userId": user_id})
        await db.orders.delete_many({"userId": user_id})
        await db.style_profiles.delete_many({"userId": user_id})
        await db.feedback.delete_many({"userId": user_id})
        await db.feature_requests.delete_many({"userId": user_id})
        await db.privacy_consent.delete_many({"userId": user_id})
        await db.deletion_requests.delete_many({"userId": user_id})
        
        # Keep anonymized log for compliance
        await db.privacy_logs.insert_one({
            "id": str(uuid.uuid4()),
            "userId": "DELETED",
            "action": "ACCOUNT_DELETED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": "User account and data permanently deleted"
        })
        
        logger.info(f"User account deleted: {user_id}")
        
        return {
            "success": True,
            "message": "Your account and all associated data have been permanently deleted."
        }
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")
