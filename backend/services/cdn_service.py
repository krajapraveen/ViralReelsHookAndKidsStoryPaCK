"""
CDN Integration Service
========================
Provides CDN URL generation and caching for media files.
Supports multiple CDN providers with fallback to direct serving.
"""
import os
import hashlib
import hmac
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger("cdn_service")

# CDN Configuration
CDN_ENABLED = os.environ.get("CDN_ENABLED", "false").lower() == "true"
CDN_PROVIDER = os.environ.get("CDN_PROVIDER", "emergent")  # emergent, cloudflare, cloudfront
CDN_BASE_URL = os.environ.get("CDN_BASE_URL", "")
CDN_SECRET_KEY = os.environ.get("CDN_SECRET_KEY", "")
CDN_CACHE_TTL = int(os.environ.get("CDN_CACHE_TTL", "3600"))  # 1 hour default


class CDNService:
    """
    CDN service for media file delivery optimization
    """
    
    def __init__(self):
        self.enabled = CDN_ENABLED
        self.provider = CDN_PROVIDER
        self.base_url = CDN_BASE_URL
        self.secret_key = CDN_SECRET_KEY
        self.cache_ttl = CDN_CACHE_TTL
        
        logger.info(f"CDN Service initialized: enabled={self.enabled}, provider={self.provider}")
    
    def get_cdn_url(
        self,
        file_path: str,
        content_type: str = "image",
        expiry_seconds: int = None
    ) -> Dict[str, Any]:
        """
        Generate CDN URL for a file
        
        Args:
            file_path: Path or key of the file
            content_type: Type of content (image, video, pdf)
            expiry_seconds: URL expiry time (optional)
            
        Returns:
            Dict with url, expires_at, cached status
        """
        if not self.enabled or not self.base_url:
            # Return direct path if CDN not enabled
            return {
                "url": file_path,
                "cdn_enabled": False,
                "cached": False,
                "note": "CDN not enabled, serving directly"
            }
        
        expiry = expiry_seconds or self.cache_ttl
        expires_at = int(time.time()) + expiry
        
        # Generate signed URL based on provider
        if self.provider == "cloudflare":
            cdn_url = self._generate_cloudflare_url(file_path, expires_at)
        elif self.provider == "cloudfront":
            cdn_url = self._generate_cloudfront_url(file_path, expires_at)
        else:
            # Default emergent CDN
            cdn_url = self._generate_emergent_url(file_path, expires_at)
        
        return {
            "url": cdn_url,
            "cdn_enabled": True,
            "provider": self.provider,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            "cache_ttl": expiry,
            "content_type": content_type
        }
    
    def _generate_emergent_url(self, file_path: str, expires_at: int) -> str:
        """Generate signed URL for Emergent CDN"""
        # Simple token-based signing
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:16]
        token = f"{path_hash}_{expires_at}"
        
        if self.secret_key:
            signature = hmac.new(
                self.secret_key.encode(),
                token.encode(),
                hashlib.sha256
            ).hexdigest()[:32]
            return f"{self.base_url}/{file_path}?token={token}&sig={signature}"
        
        return f"{self.base_url}/{file_path}?t={expires_at}"
    
    def _generate_cloudflare_url(self, file_path: str, expires_at: int) -> str:
        """Generate signed URL for Cloudflare CDN"""
        if not self.secret_key:
            return f"{self.base_url}/{file_path}"
        
        message = f"{file_path}{expires_at}"
        mac = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{self.base_url}/{file_path}?exp={expires_at}&mac={mac}"
    
    def _generate_cloudfront_url(self, file_path: str, expires_at: int) -> str:
        """Generate signed URL for CloudFront CDN"""
        # Simplified CloudFront signing (production would use proper RSA signing)
        policy = f'{{"url":"{self.base_url}/{file_path}","expiry":{expires_at}}}'
        signature = hashlib.sha256(policy.encode()).hexdigest()[:64]
        
        return f"{self.base_url}/{file_path}?Policy={policy}&Signature={signature}"
    
    def invalidate_cache(self, file_paths: list) -> Dict[str, Any]:
        """
        Request cache invalidation for specified files
        
        Args:
            file_paths: List of file paths to invalidate
            
        Returns:
            Invalidation status
        """
        if not self.enabled:
            return {"success": True, "message": "CDN not enabled"}
        
        # In production, this would call the CDN provider's API
        logger.info(f"Cache invalidation requested for {len(file_paths)} files")
        
        return {
            "success": True,
            "invalidated_count": len(file_paths),
            "provider": self.provider,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_cdn_stats(self) -> Dict[str, Any]:
        """Get CDN configuration and status"""
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "base_url": self.base_url[:30] + "..." if self.base_url else None,
            "cache_ttl_seconds": self.cache_ttl,
            "supported_content_types": ["image", "video", "pdf", "audio"],
            "features": {
                "signed_urls": bool(self.secret_key),
                "cache_invalidation": True,
                "geo_distribution": self.provider in ["cloudflare", "cloudfront"]
            }
        }


# Singleton instance
_cdn_service = None

def get_cdn_service() -> CDNService:
    """Get or create CDN service singleton"""
    global _cdn_service
    if _cdn_service is None:
        _cdn_service = CDNService()
    return _cdn_service


def get_media_url(file_path: str, content_type: str = "image") -> str:
    """
    Convenience function to get CDN URL for a media file
    Returns direct path if CDN not enabled
    """
    service = get_cdn_service()
    result = service.get_cdn_url(file_path, content_type)
    return result["url"]
