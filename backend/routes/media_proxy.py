"""R2 Media Proxy — streams R2 objects through the backend to avoid presigned URL issues."""
import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from urllib.parse import unquote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media Proxy"])

_r2_client = None
_r2_bucket = None

def _get_client():
    global _r2_client, _r2_bucket
    if _r2_client:
        return _r2_client, _r2_bucket
    try:
        import boto3
        from botocore.config import Config
        account_id = os.environ.get("CLOUDFLARE_R2_ACCOUNT_ID", "")
        access_key = os.environ.get("CLOUDFLARE_R2_ACCESS_KEY_ID", "")
        secret_key = os.environ.get("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "")
        if not all([account_id, access_key, secret_key]):
            return None, None
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        _r2_client = boto3.client('s3', endpoint_url=endpoint,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'), region_name='auto')
        _r2_bucket = os.environ.get("CLOUDFLARE_R2_BUCKET_NAME", "visionary-suite-assets-prod")
        return _r2_client, _r2_bucket
    except Exception as e:
        logger.error(f"R2 client init failed: {e}")
        return None, None

CONTENT_TYPES = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.webp': 'image/webp', '.gif': 'image/gif', '.mp4': 'video/mp4',
    '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
}

@router.get("/r2/{path:path}")
async def proxy_r2(path: str):
    """Stream an R2 object directly — no presigned URL needed."""
    key = unquote(path)
    client, bucket = _get_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage not configured")
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        ext = '.' + key.rsplit('.', 1)[-1] if '.' in key else ''
        ct = CONTENT_TYPES.get(ext.lower(), resp.get('ContentType', 'application/octet-stream'))

        def stream():
            body = resp['Body']
            while True:
                chunk = body.read(65536)
                if not chunk:
                    break
                yield chunk

        return StreamingResponse(
            stream(),
            media_type=ct,
            headers={
                "Cache-Control": "public, max-age=86400, immutable",
                "Content-Length": str(resp.get('ContentLength', '')),
            }
        )
    except client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Not found")
    except Exception as e:
        logger.error(f"R2 proxy error for {key}: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
