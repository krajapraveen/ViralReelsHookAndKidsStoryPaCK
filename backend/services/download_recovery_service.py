"""
CreatorStudio AI - Download Recovery Service
=============================================
Handles automatic recovery for failed downloads, expired links, and storage issues.

Features:
- Signed URL regeneration
- Storage fallback mechanisms
- Link expiration handling
- Preview rendering fallback
"""
import asyncio
import hashlib
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging
import os
import sys
from urllib.parse import urlparse, urljoin
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger
from services.self_healing_core import metrics, IncidentLogger, CorrelationContext

# ============================================
# CONFIGURATION
# ============================================

# Storage configuration
STORAGE_PRIMARY = os.environ.get("STORAGE_PRIMARY", "local")
STORAGE_FALLBACK = os.environ.get("STORAGE_FALLBACK", "local")
CDN_BASE_URL = os.environ.get("CDN_BASE_URL", "")
SIGNED_URL_EXPIRY_MINUTES = int(os.environ.get("SIGNED_URL_EXPIRY_MINUTES", "30"))
DOWNLOAD_RETRY_ATTEMPTS = int(os.environ.get("DOWNLOAD_RETRY_ATTEMPTS", "3"))


# ============================================
# SIGNED URL SERVICE
# ============================================

class SignedUrlService:
    """
    Generates and validates signed URLs for secure downloads
    """
    
    SECRET_KEY = os.environ.get("URL_SIGNING_SECRET", "default-signing-secret")
    
    @classmethod
    def generate_signed_url(cls, resource_path: str, user_id: str, 
                           expiry_minutes: int = None) -> str:
        """
        Generate a signed URL for secure download
        """
        expiry_minutes = expiry_minutes or SIGNED_URL_EXPIRY_MINUTES
        expires_at = int(time.time()) + (expiry_minutes * 60)
        
        # Create signature
        sign_string = f"{resource_path}:{user_id}:{expires_at}:{cls.SECRET_KEY}"
        signature = hashlib.sha256(sign_string.encode()).hexdigest()[:16]
        
        # Build URL
        base_url = CDN_BASE_URL or os.environ.get("REACT_APP_BACKEND_URL", "")
        signed_url = f"{base_url}/api/download/{resource_path}?expires={expires_at}&sig={signature}&uid={user_id}"
        
        return signed_url
    
    @classmethod
    def validate_signed_url(cls, resource_path: str, user_id: str, 
                           expires: int, signature: str) -> bool:
        """
        Validate a signed URL
        """
        # Check expiration
        if int(time.time()) > expires:
            return False
        
        # Verify signature
        sign_string = f"{resource_path}:{user_id}:{expires}:{cls.SECRET_KEY}"
        expected_signature = hashlib.sha256(sign_string.encode()).hexdigest()[:16]
        
        return signature == expected_signature
    
    @classmethod
    async def regenerate_expired_url(cls, original_url: str, user_id: str) -> Dict[str, Any]:
        """
        Regenerate a new signed URL from an expired one
        """
        try:
            # Parse original URL to get resource path
            parsed = urlparse(original_url)
            path_parts = parsed.path.split("/api/download/")
            
            if len(path_parts) < 2:
                # Try to extract from query or path
                resource_path = parsed.path.replace("/api/static/", "").replace("/static/", "")
            else:
                resource_path = path_parts[1].split("?")[0]
            
            # Verify resource exists
            resource_exists = await cls._verify_resource_exists(resource_path)
            
            if not resource_exists:
                # Try to regenerate from stored data
                regenerated = await cls._regenerate_resource(resource_path, user_id)
                if regenerated:
                    resource_path = regenerated["path"]
                else:
                    return {
                        "success": False,
                        "error": "Resource no longer available",
                        "recovery_options": ["retry_generation", "contact_support"]
                    }
            
            # Generate new signed URL
            new_url = cls.generate_signed_url(resource_path, user_id)
            
            await metrics.increment("download.url_regenerated")
            
            return {
                "success": True,
                "url": new_url,
                "expires_in_minutes": SIGNED_URL_EXPIRY_MINUTES
            }
            
        except Exception as e:
            logger.error(f"URL regeneration error: {e}")
            await metrics.increment("download.regeneration_failed")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def _verify_resource_exists(resource_path: str) -> bool:
        """Check if resource exists in storage"""
        # Check local storage
        local_path = os.path.join("/app/backend/static", resource_path)
        if os.path.exists(local_path):
            return True
        
        # Check database for stored path
        resource = await db.generated_files.find_one({"path": resource_path})
        return resource is not None
    
    @staticmethod
    async def _regenerate_resource(resource_path: str, user_id: str) -> Optional[Dict]:
        """
        Attempt to regenerate resource from stored generation data
        """
        # Find original generation record
        generation = await db.generations.find_one({
            "user_id": user_id,
            "$or": [
                {"result_url": {"$regex": resource_path}},
                {"output_path": resource_path}
            ]
        })
        
        if not generation:
            return None
        
        # Check if we have stored data to regenerate from
        if generation.get("stored_data"):
            # This would trigger re-export from stored data
            # For now, return None to indicate regeneration not possible
            pass
        
        return None


# ============================================
# DOWNLOAD RECOVERY SERVICE
# ============================================

class DownloadRecoveryService:
    """
    Handles download failures and provides recovery options
    """
    
    @staticmethod
    async def handle_download_failure(
        url: str,
        user_id: str,
        error_code: int,
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """
        Handle a failed download and provide recovery options
        """
        correlation_id = correlation_id or CorrelationContext.get_id()
        
        logger.warning(f"Download failure for user {user_id}: {error_code} - {url}")
        await metrics.increment("download.failed", tags={"error_code": str(error_code)})
        
        recovery_result = {
            "success": False,
            "original_url": url,
            "error_code": error_code,
            "recovery_attempted": False,
            "new_url": None,
            "fallback_options": []
        }
        
        # Handle based on error code
        if error_code == 403 or error_code == 410:
            # Forbidden or Gone - likely expired URL
            regen_result = await SignedUrlService.regenerate_expired_url(url, user_id)
            
            if regen_result["success"]:
                recovery_result["success"] = True
                recovery_result["new_url"] = regen_result["url"]
                recovery_result["recovery_attempted"] = True
                recovery_result["message"] = "Link regenerated successfully"
            else:
                recovery_result["fallback_options"].append({
                    "action": "retry_generation",
                    "description": "Regenerate the content"
                })
                
        elif error_code == 404:
            # Not found - try alternative storage
            fallback_url = await DownloadRecoveryService._try_fallback_storage(url, user_id)
            
            if fallback_url:
                recovery_result["success"] = True
                recovery_result["new_url"] = fallback_url
                recovery_result["recovery_attempted"] = True
                recovery_result["message"] = "Retrieved from backup storage"
            else:
                recovery_result["fallback_options"].append({
                    "action": "retry_generation",
                    "description": "Content not found, please regenerate"
                })
                
        elif error_code >= 500:
            # Server error - retry with backoff
            retry_result = await DownloadRecoveryService._retry_download(url)
            
            if retry_result["success"]:
                recovery_result["success"] = True
                recovery_result["new_url"] = url
                recovery_result["recovery_attempted"] = True
                recovery_result["message"] = "Download recovered after retry"
            else:
                recovery_result["fallback_options"].append({
                    "action": "open_direct",
                    "description": "Open in new tab",
                    "url": url
                })
                recovery_result["fallback_options"].append({
                    "action": "contact_support",
                    "description": "Contact support with ID: " + correlation_id
                })
        
        # Log incident if not recovered
        if not recovery_result["success"]:
            await IncidentLogger.log_incident(
                incident_type="download_failure",
                severity="warning",
                description=f"Download failed with code {error_code}",
                user_id=user_id,
                correlation_id=correlation_id,
                context={"url": url, "recovery_attempted": recovery_result["recovery_attempted"]}
            )
        
        return recovery_result
    
    @staticmethod
    async def _try_fallback_storage(url: str, user_id: str) -> Optional[str]:
        """
        Try to find resource in fallback storage
        """
        # Extract resource identifier
        parsed = urlparse(url)
        resource_id = parsed.path.split("/")[-1]
        
        # Check database for alternative paths
        resource = await db.generated_files.find_one({
            "user_id": user_id,
            "$or": [
                {"filename": resource_id},
                {"original_name": resource_id}
            ]
        })
        
        if resource and resource.get("fallback_path"):
            return SignedUrlService.generate_signed_url(resource["fallback_path"], user_id)
        
        return None
    
    @staticmethod
    async def _retry_download(url: str, max_attempts: int = None) -> Dict[str, Any]:
        """
        Retry download with exponential backoff
        """
        max_attempts = max_attempts or DOWNLOAD_RETRY_ATTEMPTS
        
        for attempt in range(1, max_attempts + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(url, timeout=10) as response:
                        if response.status == 200:
                            return {"success": True, "attempt": attempt}
                        
            except Exception as e:
                logger.warning(f"Download retry {attempt} failed: {e}")
            
            if attempt < max_attempts:
                wait_time = 2 ** (attempt - 1)
                await asyncio.sleep(wait_time)
        
        return {"success": False}


# ============================================
# PREVIEW RECOVERY SERVICE
# ============================================

class PreviewRecoveryService:
    """
    Handles preview/modal rendering failures
    """
    
    @staticmethod
    async def get_preview_fallback(
        content_id: str,
        content_type: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Provide fallback options when preview fails to render
        """
        # Get the content record
        content = await db.generations.find_one({
            "_id": content_id,
            "user_id": user_id
        })
        
        if not content:
            return {
                "success": False,
                "error": "Content not found"
            }
        
        fallback_options = []
        
        # Option 1: Direct download URL
        if content.get("result_url"):
            new_url = SignedUrlService.generate_signed_url(
                content["result_url"].replace("/api/static/", ""),
                user_id
            )
            fallback_options.append({
                "type": "direct_download",
                "label": "Download File",
                "url": new_url
            })
        
        # Option 2: Open in new tab
        fallback_options.append({
            "type": "new_tab",
            "label": "Open in New Tab",
            "url": content.get("result_url")
        })
        
        # Option 3: Text/data preview (for applicable types)
        if content_type in ["text", "script", "caption"]:
            fallback_options.append({
                "type": "text_preview",
                "label": "View Text",
                "content": content.get("content", content.get("result_text", ""))
            })
        
        # Option 4: Thumbnail/placeholder
        if content_type in ["image", "video"]:
            fallback_options.append({
                "type": "placeholder",
                "label": "Show Placeholder",
                "thumbnail": content.get("thumbnail_url", "/static/placeholder.png")
            })
        
        return {
            "success": True,
            "content_id": content_id,
            "content_type": content_type,
            "fallback_options": fallback_options,
            "message": "Preview unavailable. Here are alternative ways to access your content:"
        }


# ============================================
# STORAGE HEALTH SERVICE
# ============================================

class StorageHealthService:
    """
    Monitors storage health and handles failover
    """
    
    @staticmethod
    async def check_storage_health() -> Dict[str, Any]:
        """
        Check health of storage systems
        """
        health = {
            "primary": {"status": "unknown", "latency_ms": 0},
            "fallback": {"status": "unknown", "latency_ms": 0},
            "overall": "healthy"
        }
        
        # Check primary storage
        primary_start = time.time()
        try:
            # Check local storage
            test_path = "/app/backend/static/generated"
            if os.path.exists(test_path) and os.access(test_path, os.W_OK):
                health["primary"]["status"] = "healthy"
            else:
                health["primary"]["status"] = "degraded"
        except Exception as e:
            health["primary"]["status"] = "error"
            health["primary"]["error"] = str(e)
        health["primary"]["latency_ms"] = (time.time() - primary_start) * 1000
        
        # Check CDN if configured
        if CDN_BASE_URL:
            cdn_start = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(CDN_BASE_URL, timeout=5) as response:
                        if response.status < 400:
                            health["fallback"]["status"] = "healthy"
                        else:
                            health["fallback"]["status"] = "degraded"
            except Exception as e:
                health["fallback"]["status"] = "error"
                health["fallback"]["error"] = str(e)
            health["fallback"]["latency_ms"] = (time.time() - cdn_start) * 1000
        else:
            health["fallback"]["status"] = "not_configured"
        
        # Determine overall health
        if health["primary"]["status"] == "error":
            health["overall"] = "critical" if health["fallback"]["status"] != "healthy" else "degraded"
        elif health["primary"]["status"] == "degraded":
            health["overall"] = "degraded"
        
        return health
    
    @staticmethod
    async def get_best_storage_url(resource_path: str, user_id: str) -> str:
        """
        Get the best available URL for a resource
        """
        health = await StorageHealthService.check_storage_health()
        
        if health["primary"]["status"] == "healthy":
            return SignedUrlService.generate_signed_url(resource_path, user_id)
        elif health["fallback"]["status"] == "healthy" and CDN_BASE_URL:
            return f"{CDN_BASE_URL}/{resource_path}"
        else:
            # Return primary anyway as last resort
            return SignedUrlService.generate_signed_url(resource_path, user_id)
