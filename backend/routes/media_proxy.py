"""R2 Media Proxy — streams R2 objects with Range request support for video playback."""
import os
import re
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
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

def _get_content_type(key, fallback='application/octet-stream'):
    ext = '.' + key.rsplit('.', 1)[-1] if '.' in key else ''
    return CONTENT_TYPES.get(ext.lower(), fallback)


@router.head("/r2/{path:path}")
async def head_r2(path: str):
    """HEAD request — returns metadata without body (needed by video players)."""
    key = unquote(path)
    client, bucket = _get_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage not configured")
    try:
        head = client.head_object(Bucket=bucket, Key=key)
        ct = _get_content_type(key, head.get('ContentType', 'application/octet-stream'))
        return Response(
            content=b'',
            media_type=ct,
            headers={
                "Content-Length": str(head['ContentLength']),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400, immutable",
            }
        )
    except Exception as e:
        logger.error(f"R2 HEAD error for {key}: {e}")
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/r2/{path:path}")
async def proxy_r2(path: str, request: Request):
    """Stream an R2 object with Range request support for video/audio playback."""
    key = unquote(path)
    client, bucket = _get_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage not configured")

    try:
        # Get file size first
        head = client.head_object(Bucket=bucket, Key=key)
        total_size = head['ContentLength']
        ct = _get_content_type(key, head.get('ContentType', 'application/octet-stream'))

        range_header = request.headers.get('range')

        if range_header:
            # Parse Range: bytes=START-END
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else min(start + 2 * 1024 * 1024, total_size - 1)
                end = min(end, total_size - 1)
                length = end - start + 1

                resp = client.get_object(Bucket=bucket, Key=key, Range=f'bytes={start}-{end}')
                body = resp['Body'].read()

                return Response(
                    content=body,
                    status_code=206,
                    media_type=ct,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{total_size}",
                        "Content-Length": str(length),
                        "Accept-Ranges": "bytes",
                        "Cache-Control": "public, max-age=86400, immutable",
                    }
                )

        # No Range — return full content (fine for images, small files)
        resp = client.get_object(Bucket=bucket, Key=key)
        body = resp['Body'].read()
        return Response(
            content=body,
            media_type=ct,
            headers={
                "Content-Length": str(len(body)),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400, immutable",
            }
        )

    except client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Not found")
    except Exception as e:
        logger.error(f"R2 proxy error for {key}: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
