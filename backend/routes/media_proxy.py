"""R2 Media Proxy — streams R2 objects with Range request support for video playback.

Performance: All boto3 (synchronous) calls run in asyncio.to_thread() to avoid
blocking the FastAPI event loop.  Resized images are cached in-memory (LRU) so
repeated dashboard loads are instant.
"""
import os
import re
import io
import asyncio
import logging
import time
from collections import OrderedDict
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import Response
from urllib.parse import unquote
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media Proxy"])

# ── In-memory LRU cache for resized images ──────────────────────────
_RESIZE_CACHE: OrderedDict = OrderedDict()   # key → (bytes, content_type, timestamp)
_CACHE_MAX = 150          # max entries
_CACHE_TTL = 3600         # 1 hour

def _cache_get(key: str):
    entry = _RESIZE_CACHE.get(key)
    if entry and (time.time() - entry[2]) < _CACHE_TTL:
        _RESIZE_CACHE.move_to_end(key)
        return entry
    if entry:
        _RESIZE_CACHE.pop(key, None)
    return None

def _cache_set(key: str, body: bytes, ct: str):
    if len(_RESIZE_CACHE) >= _CACHE_MAX:
        _RESIZE_CACHE.popitem(last=False)
    _RESIZE_CACHE[key] = (body, ct, time.time())


@router.options("/r2/{path:path}")
async def options_r2(path: str):
    """CORS preflight for cross-origin image/video requests (Safari/mobile)."""
    return Response(
        content=b'',
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
            "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges",
            "Access-Control-Max-Age": "86400",
        }
    )

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
        head = await asyncio.to_thread(_s3_head, client, bucket, key)
        ct = _get_content_type(key)
        return Response(
            content=b'', media_type=ct,
            headers={
                "Content-Length": str(head['ContentLength']),
                "Accept-Ranges": "bytes",
                **_CACHE_HEADERS, **_CORS_HEADERS,
            }
        )
    except Exception as e:
        logger.error(f"R2 HEAD error for {key}: {e}")
        raise HTTPException(status_code=404, detail="Not found")


def _s3_head(client, bucket, key):
    return client.head_object(Bucket=bucket, Key=key)

def _s3_get(client, bucket, key, **kw):
    resp = client.get_object(Bucket=bucket, Key=key, **kw)
    return resp['Body'].read(), resp

def _pillow_resize(body: bytes, w: int, q: int) -> bytes:
    from PIL import Image as PILImage
    img = PILImage.open(io.BytesIO(body))
    ratio = w / img.width
    new_h = int(img.height * ratio)
    img = img.resize((w, new_h), PILImage.LANCZOS)
    if img.mode in ('RGBA', 'P', 'LA'):
        bg = PILImage.new('RGB', img.size, (0, 0, 0))
        if img.mode == 'P':
            img = img.convert('RGBA')
        bg.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=q, optimize=True)
    return buf.getvalue()

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges",
}
_CACHE_HEADERS = {"Cache-Control": "public, max-age=604800, immutable"}


@router.get("/r2/{path:path}")
async def proxy_r2(path: str, request: Request, w: Optional[int] = Query(None, ge=50, le=1920), q: Optional[int] = Query(None, ge=10, le=100)):
    """Stream an R2 object with Range request support for video/audio playback.

    All S3 calls run in asyncio.to_thread() to avoid blocking the event loop.
    Resized images are LRU-cached so repeated dashboard loads are instant.
    """
    key = unquote(path)
    client, bucket = _get_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage not configured")

    try:
        ct = _get_content_type(key)
        is_image = ct.startswith('image/')
        quality = q or 80

        # ── Fast path: check resize cache ────────────────────────────
        if is_image:
            # Auto-resize large images even without ?w (images >500KB get resized to 800)
            effective_w = w
            cache_key = f"{key}:{effective_w}:{quality}"
            cached = _cache_get(cache_key)
            if cached:
                return Response(
                    content=cached[0], media_type=cached[1],
                    headers={"Content-Length": str(len(cached[0])), **_CACHE_HEADERS, **_CORS_HEADERS}
                )

        # ── Get metadata (non-blocking) ──────────────────────────────
        head = await asyncio.to_thread(_s3_head, client, bucket, key)
        total_size = head['ContentLength']

        # ── Image resize path ────────────────────────────────────────
        if is_image:
            effective_w = w
            # Auto-resize oversized images (>300KB) even without explicit ?w
            if not effective_w and total_size > 300_000:
                effective_w = 800

            if effective_w:
                cache_key = f"{key}:{effective_w}:{quality}"
                cached = _cache_get(cache_key)
                if cached:
                    return Response(
                        content=cached[0], media_type=cached[1],
                        headers={"Content-Length": str(len(cached[0])), **_CACHE_HEADERS, **_CORS_HEADERS}
                    )
                body, _ = await asyncio.to_thread(_s3_get, client, bucket, key)
                try:
                    resized = await asyncio.to_thread(_pillow_resize, body, effective_w, quality)
                    _cache_set(cache_key, resized, 'image/jpeg')
                    return Response(
                        content=resized, media_type='image/jpeg',
                        headers={"Content-Length": str(len(resized)), **_CACHE_HEADERS, **_CORS_HEADERS}
                    )
                except Exception as resize_err:
                    logger.warning(f"Image resize failed for {key}: {resize_err}, serving original")
                    return Response(
                        content=body, media_type=ct,
                        headers={"Content-Length": str(len(body)), "Accept-Ranges": "bytes", **_CACHE_HEADERS, **_CORS_HEADERS}
                    )

            # Small image, no resize needed — serve directly
            body, _ = await asyncio.to_thread(_s3_get, client, bucket, key)
            _cache_set(f"{key}:None:{quality}", body, ct)
            return Response(
                content=body, media_type=ct,
                headers={"Content-Length": str(len(body)), "Accept-Ranges": "bytes", **_CACHE_HEADERS, **_CORS_HEADERS}
            )

        # ── Range request path (video/audio) ─────────────────────────
        range_header = request.headers.get('range')

        if range_header:
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else min(start + 2 * 1024 * 1024, total_size - 1)
                end = min(end, total_size - 1)
                length = end - start + 1

                body, _ = await asyncio.to_thread(_s3_get, client, bucket, key, Range=f'bytes={start}-{end}')
                return Response(
                    content=body, status_code=206, media_type=ct,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{total_size}",
                        "Content-Length": str(length),
                        "Accept-Ranges": "bytes",
                        **_CACHE_HEADERS, **_CORS_HEADERS,
                    }
                )

        # ── Full content (non-image, no Range) ───────────────────────
        body, _ = await asyncio.to_thread(_s3_get, client, bucket, key)
        return Response(
            content=body, media_type=ct,
            headers={"Content-Length": str(len(body)), "Accept-Ranges": "bytes", **_CACHE_HEADERS, **_CORS_HEADERS}
        )

    except Exception as e:
        err_str = str(e)
        if 'NoSuchKey' in err_str or '404' in err_str:
            raise HTTPException(status_code=404, detail="Not found")
        logger.error(f"R2 proxy error for {key}: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
