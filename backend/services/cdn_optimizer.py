"""
CDN & Asset Delivery Optimization Service
Implements caching headers, signed URLs, and fallback handling for generated assets
"""
import os
import hashlib
import hmac
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import logging
from urllib.parse import urlencode
from fastapi import Response, Request
from fastapi.responses import FileResponse, StreamingResponse
import asyncio

logger = logging.getLogger(__name__)

# Asset configuration
ASSET_CONFIG = {
    # Static assets - long cache
    "static": {
        "cache_control": "public, max-age=31536000, immutable",
        "extensions": [".js", ".css", ".woff2", ".woff", ".ttf", ".ico"],
    },
    # Generated images - moderate cache with revalidation
    "images": {
        "cache_control": "public, max-age=86400, stale-while-revalidate=604800",
        "extensions": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    },
    # Generated videos - short cache, allow streaming
    "videos": {
        "cache_control": "public, max-age=3600, stale-while-revalidate=86400",
        "extensions": [".mp4", ".webm", ".mov"],
    },
    # PDF documents - moderate cache
    "documents": {
        "cache_control": "public, max-age=86400, stale-while-revalidate=604800",
        "extensions": [".pdf"],
    },
    # API responses - no cache or short cache
    "api": {
        "cache_control": "no-cache, no-store, must-revalidate",
        "extensions": [],
    }
}

# Secret key for signing URLs (use environment variable in production)
SIGNING_SECRET = os.environ.get("ASSET_SIGNING_SECRET", "default-secret-key-change-me")


class CDNOptimizer:
    """Optimizes asset delivery with caching, compression, and signed URLs"""
    
    def __init__(self, db):
        self.db = db
        self.asset_cache: Dict[str, Dict] = {}  # In-memory cache for asset metadata
    
    def get_cache_headers(self, path: str, content_type: str = None) -> Dict[str, str]:
        """Get appropriate cache headers based on file type"""
        headers = {}
        
        # Determine asset type
        path_lower = path.lower()
        asset_type = "api"  # default
        
        for type_name, config in ASSET_CONFIG.items():
            for ext in config.get("extensions", []):
                if path_lower.endswith(ext):
                    asset_type = type_name
                    break
        
        # Set cache control
        cache_config = ASSET_CONFIG.get(asset_type, ASSET_CONFIG["api"])
        headers["Cache-Control"] = cache_config["cache_control"]
        
        # Add ETag for static and generated assets
        if asset_type in ["static", "images", "documents"]:
            # Generate ETag from path (in production, use file hash)
            etag = hashlib.md5(path.encode()).hexdigest()[:16]
            headers["ETag"] = f'"{etag}"'
        
        # Add Vary header for content negotiation
        headers["Vary"] = "Accept-Encoding"
        
        # Add CDN hints
        headers["CDN-Cache-Control"] = cache_config["cache_control"]
        
        return headers
    
    def generate_signed_url(
        self, 
        base_url: str, 
        asset_path: str, 
        expires_hours: int = 24
    ) -> str:
        """Generate a signed URL with expiration"""
        expires = int((datetime.now(timezone.utc) + timedelta(hours=expires_hours)).timestamp())
        
        # Create signature payload
        payload = f"{asset_path}:{expires}"
        signature = hmac.new(
            SIGNING_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        # Build URL with signature
        params = {
            "expires": expires,
            "sig": signature
        }
        
        return f"{base_url}{asset_path}?{urlencode(params)}"
    
    def verify_signed_url(self, asset_path: str, expires: int, signature: str) -> bool:
        """Verify a signed URL"""
        # Check expiration
        if int(datetime.now(timezone.utc).timestamp()) > expires:
            return False
        
        # Verify signature
        payload = f"{asset_path}:{expires}"
        expected_sig = hmac.new(
            SIGNING_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        return hmac.compare_digest(signature, expected_sig)
    
    async def regenerate_expired_link(
        self, 
        job_id: str, 
        base_url: str
    ) -> Optional[str]:
        """Regenerate expired download link for a job"""
        job = await self.db.genstudio_jobs.find_one(
            {"id": job_id},
            {"_id": 0, "outputUrl": 1, "outputUrls": 1, "status": 1}
        )
        
        if not job or job.get("status") != "COMPLETED":
            return None
        
        # Get the original asset path
        output_url = job.get("outputUrl", "")
        if not output_url:
            output_urls = job.get("outputUrls", [])
            if output_urls:
                output_url = output_urls[0]
        
        if not output_url:
            return None
        
        # Extract asset path from URL
        asset_path = output_url.split("?")[0]  # Remove existing query params
        if asset_path.startswith(base_url):
            asset_path = asset_path[len(base_url):]
        
        # Generate new signed URL
        new_url = self.generate_signed_url(base_url, asset_path)
        
        # Update the job record
        await self.db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "outputUrl": new_url,
                "linkRegeneratedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Regenerated download link for job {job_id}")
        return new_url
    
    async def get_asset_with_fallback(
        self, 
        asset_path: str,
        fallback_message: str = "Asset not available"
    ) -> Response:
        """Get asset with fallback if not found"""
        # Check if asset exists
        full_path = f"/app/frontend/public{asset_path}"
        
        if os.path.exists(full_path):
            # Return the file with appropriate headers
            headers = self.get_cache_headers(asset_path)
            return FileResponse(full_path, headers=headers)
        
        # Return fallback response
        return Response(
            content=fallback_message,
            status_code=404,
            headers={"Cache-Control": "no-cache"}
        )
    
    async def optimize_response(self, request: Request, response: Response) -> Response:
        """Add optimization headers to response"""
        path = request.url.path
        
        # Get cache headers
        headers = self.get_cache_headers(path)
        for key, value in headers.items():
            response.headers[key] = value
        
        # Add compression hint
        if "gzip" in request.headers.get("Accept-Encoding", ""):
            response.headers["Content-Encoding-Hint"] = "gzip"
        
        return response


class AssetReconciliationService:
    """Service for handling expired/missing asset reconciliation"""
    
    def __init__(self, db):
        self.db = db
    
    async def find_expired_assets(self, hours_ago: int = 24) -> List[Dict]:
        """Find jobs with expired download links"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        
        jobs = await self.db.genstudio_jobs.find({
            "status": "COMPLETED",
            "outputUrl": {"$exists": True, "$ne": ""},
            "completedAt": {"$lt": cutoff.isoformat()},
            "$or": [
                {"linkRegeneratedAt": {"$exists": False}},
                {"linkRegeneratedAt": {"$lt": (cutoff - timedelta(hours=24)).isoformat()}}
            ]
        }, {"_id": 0, "id": 1, "userId": 1, "outputUrl": 1}).limit(100).to_list(100)
        
        return jobs
    
    async def reconcile_expired_links(self, base_url: str) -> Dict[str, Any]:
        """Reconcile all expired links"""
        expired_jobs = await self.find_expired_assets()
        
        results = {
            "total": len(expired_jobs),
            "regenerated": 0,
            "failed": 0,
            "errors": []
        }
        
        cdn = CDNOptimizer(self.db)
        
        for job in expired_jobs:
            try:
                new_url = await cdn.regenerate_expired_link(job["id"], base_url)
                if new_url:
                    results["regenerated"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "job_id": job["id"],
                    "error": str(e)
                })
        
        return results
    
    async def find_missing_assets(self) -> List[Dict]:
        """Find jobs where the asset file is missing"""
        jobs = await self.db.genstudio_jobs.find({
            "status": "COMPLETED",
            "outputUrl": {"$exists": True, "$ne": ""},
            "assetVerified": {"$ne": True}
        }, {"_id": 0, "id": 1, "userId": 1, "outputUrl": 1}).limit(50).to_list(50)
        
        missing = []
        for job in jobs:
            output_url = job.get("outputUrl", "")
            if output_url and not await self._verify_asset_exists(output_url):
                missing.append(job)
        
        return missing
    
    async def _verify_asset_exists(self, url: str) -> bool:
        """Verify that an asset URL is accessible"""
        # This would check if the file exists in storage
        # For now, assume external URLs are valid
        return True


# Global instances
_cdn_optimizer: Optional[CDNOptimizer] = None
_reconciliation_service: Optional[AssetReconciliationService] = None


async def get_cdn_optimizer(db) -> CDNOptimizer:
    """Get or create CDN optimizer singleton"""
    global _cdn_optimizer
    if _cdn_optimizer is None:
        _cdn_optimizer = CDNOptimizer(db)
    return _cdn_optimizer


async def get_reconciliation_service(db) -> AssetReconciliationService:
    """Get or create reconciliation service singleton"""
    global _reconciliation_service
    if _reconciliation_service is None:
        _reconciliation_service = AssetReconciliationService(db)
    return _reconciliation_service
