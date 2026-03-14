"""Utility to convert R2 public URLs to presigned URLs."""
import os
import logging
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)

_r2_client = None

def _get_r2_client():
    """Lazy-initialize and cache the R2 client."""
    global _r2_client
    if _r2_client is not None:
        return _r2_client
    try:
        from services.cloudflare_r2_storage import get_r2_storage
        r2 = get_r2_storage()
        if r2 and hasattr(r2, '_client') and r2._client:
            _r2_client = r2._client
            logger.info("R2 presign client initialized successfully")
            return _r2_client
        elif r2 and hasattr(r2, 'client') and r2.client:
            _r2_client = r2.client
            logger.info("R2 presign client initialized (via .client)")
            return _r2_client
        else:
            logger.warning(f"R2 storage returned but no client found. is_configured={getattr(r2, 'is_configured', 'N/A')}")
    except Exception as e:
        logger.warning(f"Failed to get R2 client: {e}")
    return None


def presign_url(stored_url: str, expiry: int = 14400) -> str:
    """Convert an R2 public URL to a presigned URL. Returns original if conversion fails.
    Handles both .r2.dev/ and r2.cloudflarestorage.com URL formats."""
    if not stored_url:
        return stored_url

    # Extract key from various R2 URL formats
    key = None

    if ".r2.dev/" in stored_url:
        # Format: https://xxx.r2.dev/image/jobid/filename.png?maybe_params
        raw = stored_url.split(".r2.dev/")[1]
        key = raw.split("?")[0]  # Strip any existing query params
    elif "r2.cloudflarestorage.com" in stored_url:
        # Format: https://xxx.r2.cloudflarestorage.com/bucket/key
        parsed = urlparse(stored_url)
        path_parts = parsed.path.lstrip("/").split("/", 1)
        if len(path_parts) > 1:
            key = unquote(path_parts[1])

    if not key:
        return stored_url

    client = _get_r2_client()
    if not client:
        return stored_url

    try:
        bucket = os.environ.get("CLOUDFLARE_R2_BUCKET_NAME", "visionary-suite-assets-prod")
        presigned = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiry
        )
        return presigned
    except Exception as e:
        logger.warning(f"presign_url failed for key={key}: {e}")
        return stored_url


def presign_key(key: str, expiry: int = 14400) -> str:
    """Generate a presigned URL directly from an R2 object key."""
    client = _get_r2_client()
    if not client or not key:
        return ""
    try:
        bucket = os.environ.get("CLOUDFLARE_R2_BUCKET_NAME", "visionary-suite-assets-prod")
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiry
        )
    except Exception as e:
        logger.warning(f"presign_key failed for key={key}: {e}")
        return ""


def presign_dict(doc: dict, *url_fields: str) -> dict:
    """Presign multiple URL fields in a dictionary."""
    for field in url_fields:
        if field in doc and doc[field]:
            doc[field] = presign_url(doc[field])
    return doc
