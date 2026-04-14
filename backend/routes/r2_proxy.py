"""
R2 Media Proxy — Serves R2-stored media (images, videos) through the backend.
Required because the R2 bucket is not publicly accessible (403 on direct URLs).
Frontend SafeImage converts R2 CDN URLs to /api/media/r2/{path} which this handles.
"""
import os
import sys
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from cachetools import TTLCache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("r2_proxy")
router = APIRouter(prefix="/media", tags=["Media R2 Proxy"])

# In-memory presigned URL cache (1 hour TTL, max 500 entries)
_url_cache = TTLCache(maxsize=500, ttl=3600)

BUCKET = os.environ.get("CLOUDFLARE_R2_BUCKET_NAME", "visionary-suite-assets-prod")


def _get_r2_client():
    """Lazy-init R2 boto3 client."""
    import boto3
    from botocore.config import Config
    account_id = os.environ.get("CLOUDFLARE_R2_ACCOUNT_ID", "")
    access_key = os.environ.get("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
    secret_key = os.environ.get("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "")
    if not all([account_id, access_key, secret_key]):
        return None
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4", retries={"max_attempts": 2, "mode": "adaptive"}),
        region_name="auto",
    )


_client = None


def get_client():
    global _client
    if _client is None:
        _client = _get_r2_client()
    return _client


CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}


@router.get("/r2/{path:path}")
async def r2_proxy(path: str, request: Request):
    """
    Proxy R2 media content. Generates a presigned URL and redirects (302),
    so the browser fetches directly from R2 with a signed URL.
    Presigned URLs are cached for 1 hour.
    """
    if not path or ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Check cache first
    cached_url = _url_cache.get(path)
    if cached_url:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=cached_url, status_code=302)

    client = get_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage not configured")

    try:
        # Generate presigned URL (valid for 1 hour)
        presigned_url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": path},
            ExpiresIn=3600,
        )
        _url_cache[path] = presigned_url

        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=presigned_url, status_code=302)
    except client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Asset not found")
    except Exception as e:
        logger.error(f"R2 proxy error for {path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch asset")
