"""
CDN & Static File Configuration
Handles static file serving and CDN integration
Supports: Cloudflare, CloudFront, Bunny, Emergent CDN
"""
import os
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta
import hashlib
import hmac

# =============================================================================
# CDN CONFIGURATION
# =============================================================================

CDN_PROVIDER = os.environ.get("CDN_PROVIDER", "emergent")

CDN_CONFIG = {
    "enabled": os.environ.get("CDN_ENABLED", "false").lower() == "true",
    "provider": CDN_PROVIDER,
    
    # Emergent CDN Configuration
    "emergent": {
        "enabled": CDN_PROVIDER == "emergent",
        "auto_optimize": True,
        "edge_caching": True,
        "compression": "auto",  # auto, gzip, br
        "image_optimization": True,
        "lazy_loading": True,
    },
    
    # Base URLs
    "base_url": os.environ.get("CDN_BASE_URL", os.environ.get("REACT_APP_BACKEND_URL", "")),
    "fallback_url": os.environ.get("REACT_APP_BACKEND_URL", ""),
    
    # Cache settings (in seconds)
    "cache_control": {
        "images": "public, max-age=31536000, immutable",  # 1 year for static images
        "videos": "public, max-age=2592000",  # 30 days for videos
        "pdfs": "public, max-age=604800",  # 7 days for PDFs
        "generated": "public, max-age=86400",  # 1 day for user-generated content
        "api": "no-cache, no-store, must-revalidate",  # No cache for API
        "static": "public, max-age=31536000, immutable",  # 1 year for static assets
        "html": "no-cache",  # Always revalidate HTML
    },
    
    # Signed URL settings
    "signed_urls": {
        "enabled": os.environ.get("CDN_SIGNED_URLS", "false").lower() == "true",
        "secret": os.environ.get("CDN_SIGNING_SECRET", ""),
        "expiry_seconds": 3600,  # 1 hour default
    },
    
    # Optimization settings
    "optimization": {
        "auto_webp": True,  # Convert images to WebP
        "auto_avif": False,  # AVIF support (experimental)
        "lazy_loading": True,
        "compression": "gzip",  # gzip, br (brotli)
        "minify_js": True,
        "minify_css": True,
        "preload_critical": True,
    },
    
    # Security
    "security": {
        "hotlink_protection": True,
        "allowed_referrers": ["creatorstudio.ai", "*.emergentagent.com"],
    }
}


# =============================================================================
# CDN URL GENERATION
# =============================================================================

def get_cdn_url(path: str, file_type: str = "images") -> str:
    """Get CDN URL for a file path"""
    if not CDN_CONFIG["enabled"] or not CDN_CONFIG["base_url"]:
        return f"{CDN_CONFIG['fallback_url']}{path}"
    
    base = CDN_CONFIG["base_url"].rstrip("/")
    clean_path = path.lstrip("/")
    
    return f"{base}/{clean_path}"


def get_signed_url(path: str, expiry_seconds: Optional[int] = None) -> str:
    """Generate a signed CDN URL with expiration"""
    if not CDN_CONFIG["signed_urls"]["enabled"]:
        return get_cdn_url(path)
    
    expiry = expiry_seconds or CDN_CONFIG["signed_urls"]["expiry_seconds"]
    expires = int((datetime.now(timezone.utc) + timedelta(seconds=expiry)).timestamp())
    
    # Create signature
    secret = CDN_CONFIG["signed_urls"]["secret"]
    message = f"{path}{expires}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    base_url = get_cdn_url(path)
    separator = "&" if "?" in base_url else "?"
    
    return f"{base_url}{separator}expires={expires}&sig={signature}"


def verify_signed_url(path: str, expires: int, signature: str) -> bool:
    """Verify a signed URL is valid"""
    if not CDN_CONFIG["signed_urls"]["enabled"]:
        return True
    
    # Check expiration
    if expires < int(datetime.now(timezone.utc).timestamp()):
        return False
    
    # Verify signature
    secret = CDN_CONFIG["signed_urls"]["secret"]
    message = f"{path}{expires}"
    expected = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    return hmac.compare_digest(signature, expected)


# =============================================================================
# CACHE HEADERS
# =============================================================================

def get_cache_headers(file_type: str) -> Dict[str, str]:
    """Get appropriate cache headers for file type"""
    cache_control = CDN_CONFIG["cache_control"].get(file_type, "no-cache")
    
    headers = {
        "Cache-Control": cache_control,
        "X-Content-Type-Options": "nosniff",
    }
    
    # Add CDN-specific headers
    if CDN_CONFIG["provider"] == "cloudflare":
        headers["CDN-Cache-Control"] = cache_control
    elif CDN_CONFIG["provider"] == "cloudfront":
        headers["X-Cache-Control"] = cache_control
    
    return headers


# =============================================================================
# STATIC FILE OPTIMIZATION
# =============================================================================

def get_optimized_image_url(original_url: str, width: Optional[int] = None, quality: int = 80) -> str:
    """Get optimized image URL with transformations"""
    if not CDN_CONFIG["enabled"]:
        return original_url
    
    params = []
    
    if CDN_CONFIG["optimization"]["auto_webp"]:
        params.append("format=webp")
    
    if width:
        params.append(f"width={width}")
    
    params.append(f"quality={quality}")
    
    separator = "&" if "?" in original_url else "?"
    return f"{original_url}{separator}{'&'.join(params)}"


def get_responsive_image_srcset(base_url: str, widths: list = [320, 640, 960, 1280, 1920]) -> str:
    """Generate srcset for responsive images"""
    if not CDN_CONFIG["enabled"]:
        return base_url
    
    srcset_parts = []
    for width in widths:
        optimized_url = get_optimized_image_url(base_url, width=width)
        srcset_parts.append(f"{optimized_url} {width}w")
    
    return ", ".join(srcset_parts)


# =============================================================================
# MIDDLEWARE HELPER
# =============================================================================

async def add_cdn_headers(response, file_type: str = "api"):
    """Add CDN headers to response"""
    headers = get_cache_headers(file_type)
    for key, value in headers.items():
        response.headers[key] = value
    return response


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'CDN_CONFIG',
    'get_cdn_url',
    'get_signed_url',
    'verify_signed_url',
    'get_cache_headers',
    'get_optimized_image_url',
    'get_responsive_image_srcset',
    'add_cdn_headers'
]
