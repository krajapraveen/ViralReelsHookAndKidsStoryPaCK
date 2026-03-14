"""Utility to convert R2 public URLs to presigned URLs."""
import os
import logging

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
        if r2 and r2._client:
            _r2_client = r2._client
            return _r2_client
    except Exception:
        pass
    return None


def presign_url(stored_url: str, expiry: int = 14400) -> str:
    """Convert an R2 public URL to a presigned URL. Returns original if conversion fails."""
    if not stored_url or ".r2.dev/" not in stored_url:
        return stored_url
    client = _get_r2_client()
    if not client:
        return stored_url
    try:
        key = stored_url.split(".r2.dev/")[1]
        bucket = os.environ.get("CLOUDFLARE_R2_BUCKET_NAME", "visionary-suite-assets-prod")
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiry
        )
    except Exception as e:
        logger.warning(f"presign_url failed: {e}")
        return stored_url


def presign_dict(doc: dict, *url_fields: str) -> dict:
    """Presign multiple URL fields in a dictionary."""
    for field in url_fields:
        if field in doc and doc[field]:
            doc[field] = presign_url(doc[field])
    return doc
