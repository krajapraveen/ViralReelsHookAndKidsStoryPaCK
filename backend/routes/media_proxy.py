"""R2 Media Proxy — Safari-safe streaming with Range/206 support.

Architecture:
  - IMAGES: Buffered + LRU cached (small files, <500KB after resize)
  - VIDEO/AUDIO: True streaming via StreamingResponse (never buffered in memory)
  - ALL responses: Full Safari-compliant headers via _safari_safe_headers()
  - Cache workaround: CDN-Cache-Control + Surrogate-Control bypass ingress override
"""
import os
import re
import io
import asyncio
import logging
import time
import hashlib
from collections import OrderedDict
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import Response, StreamingResponse
from urllib.parse import unquote
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media Proxy"])

# ── In-memory LRU cache for resized images ──────────────────────────
_RESIZE_CACHE: OrderedDict = OrderedDict()
_CACHE_MAX = 150
_CACHE_TTL = 3600

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


# ── R2 Client ───────────────────────────────────────────────────────
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


# ── Content Type Detection ──────────────────────────────────────────
CONTENT_TYPES = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.webp': 'image/webp', '.gif': 'image/gif', '.mp4': 'video/mp4',
    '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
    '.m4a': 'audio/mp4', '.mov': 'video/quicktime',
}

def _get_content_type(key, fallback='application/octet-stream'):
    ext = '.' + key.rsplit('.', 1)[-1] if '.' in key else ''
    return CONTENT_TYPES.get(ext.lower(), fallback)


# ── S3 Operations ───────────────────────────────────────────────────
def _s3_head(client, bucket, key):
    return client.head_object(Bucket=bucket, Key=key)

def _s3_get_bytes(client, bucket, key, **kw):
    """Fetch and READ entire object — for images only (small files)."""
    resp = client.get_object(Bucket=bucket, Key=key, **kw)
    return resp['Body'].read(), resp

def _s3_get_stream(client, bucket, key, **kw):
    """Get object WITHOUT reading — returns StreamingBody for chunked delivery."""
    return client.get_object(Bucket=bucket, Key=key, **kw)


# ── Image Resize ────────────────────────────────────────────────────
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


# ── Safari-Safe Headers ─────────────────────────────────────────────
# Multiple cache directives to survive ingress override:
#   Cache-Control: standard (ingress may strip)
#   CDN-Cache-Control: Cloudflare-specific (survives ingress)
#   Surrogate-Control: Varnish/Fastly/generic CDN (survives ingress)
_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges, ETag",
}

def _safari_safe_headers(content_length: int = None, etag_seed: str = None) -> dict:
    """Build the complete Safari-safe header set."""
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": "inline",
        "X-Content-Type-Options": "nosniff",
        "Vary": "Range, Accept-Encoding",
        # Triple cache strategy to survive ingress override
        "Cache-Control": "public, max-age=31536000, immutable",
        "CDN-Cache-Control": "public, max-age=31536000, immutable",
        "Surrogate-Control": "public, max-age=31536000, immutable",
        **_CORS_HEADERS,
    }
    if content_length is not None:
        headers["Content-Length"] = str(content_length)
    if etag_seed:
        tag = hashlib.md5(etag_seed.encode()).hexdigest()[:16]
        headers["ETag"] = f'W/"{tag}"'
    return headers


def _image_response(body: bytes, content_type: str) -> Response:
    """Buffered response for images (small, cached)."""
    return Response(
        content=body,
        media_type=content_type,
        headers=_safari_safe_headers(
            content_length=len(body),
            etag_seed=f"{len(body)}:{content_type}:{hashlib.md5(body[:1024]).hexdigest()[:8]}"
        ),
    )


# ── CORS Preflight ──────────────────────────────────────────────────
@router.options("/r2/{path:path}")
async def options_r2(path: str):
    return Response(
        content=b'',
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
            "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges, ETag",
            "Access-Control-Max-Age": "86400",
        }
    )


# ── HEAD ────────────────────────────────────────────────────────────
@router.head("/r2/{path:path}")
async def head_r2(path: str):
    """HEAD — returns metadata. Safari sends this before video playback."""
    key = unquote(path)
    client, bucket = _get_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage not configured")
    try:
        head = await asyncio.to_thread(_s3_head, client, bucket, key)
        ct = _get_content_type(key)
        return Response(
            content=b'',
            media_type=ct,
            headers=_safari_safe_headers(
                content_length=head['ContentLength'],
                etag_seed=f"{key}:{head['ContentLength']}"
            ),
        )
    except Exception as e:
        logger.error(f"R2 HEAD error for {key}: {e}")
        raise HTTPException(status_code=404, detail="Not found")


# ── GET (main handler) ──────────────────────────────────────────────
STREAM_CHUNK_SIZE = 65536  # 64KB chunks for streaming

@router.get("/r2/{path:path}")
async def proxy_r2(
    path: str,
    request: Request,
    w: Optional[int] = Query(None, ge=50, le=1920),
    q: Optional[int] = Query(None, ge=10, le=100),
):
    """Serve R2 media: images buffered+cached, video/audio streamed.

    Images: Fetched, optionally resized, LRU-cached, returned as Response.
    Video/Audio: Streamed in 64KB chunks via StreamingResponse. Never buffered.
    Range requests: Return 206 with Content-Range (Safari video requirement).
    """
    key = unquote(path)
    client, bucket = _get_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage not configured")

    try:
        ct = _get_content_type(key)
        is_image = ct.startswith('image/')
        quality = q or 80

        # ══════════════════════════════════════════════════════════════
        # IMAGE PATH — buffered + LRU cached (small files)
        # ══════════════════════════════════════════════════════════════
        if is_image:
            effective_w = w
            cache_key = f"{key}:{effective_w}:{quality}"
            cached = _cache_get(cache_key)
            if cached:
                return _image_response(cached[0], cached[1])

            head = await asyncio.to_thread(_s3_head, client, bucket, key)
            total_size = head['ContentLength']

            if not effective_w and total_size > 300_000:
                effective_w = 800

            if effective_w:
                cache_key = f"{key}:{effective_w}:{quality}"
                cached = _cache_get(cache_key)
                if cached:
                    return _image_response(cached[0], cached[1])

                body, _ = await asyncio.to_thread(_s3_get_bytes, client, bucket, key)
                try:
                    resized = await asyncio.to_thread(_pillow_resize, body, effective_w, quality)
                    _cache_set(cache_key, resized, 'image/jpeg')
                    return _image_response(resized, 'image/jpeg')
                except Exception as resize_err:
                    logger.warning(f"Resize failed for {key}: {resize_err}")
                    return _image_response(body, ct)

            # Small image, no resize
            body, _ = await asyncio.to_thread(_s3_get_bytes, client, bucket, key)
            _cache_set(f"{key}:None:{quality}", body, ct)
            return _image_response(body, ct)

        # ══════════════════════════════════════════════════════════════
        # VIDEO/AUDIO PATH — true streaming, never buffered
        # ══════════════════════════════════════════════════════════════
        head = await asyncio.to_thread(_s3_head, client, bucket, key)
        total_size = head['ContentLength']
        range_header = request.headers.get('range')

        if range_header:
            # ── Range request → 206 Partial Content (streamed) ────────
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else min(start + 2 * 1024 * 1024, total_size - 1)
                end = min(end, total_size - 1)
                length = end - start + 1

                resp = await asyncio.to_thread(
                    _s3_get_stream, client, bucket, key,
                    Range=f'bytes={start}-{end}'
                )
                s3_body = resp['Body']

                async def stream_range():
                    try:
                        while True:
                            chunk = await asyncio.to_thread(s3_body.read, STREAM_CHUNK_SIZE)
                            if not chunk:
                                break
                            yield chunk
                    finally:
                        await asyncio.to_thread(s3_body.close)

                headers = _safari_safe_headers(
                    content_length=length,
                    etag_seed=f"{key}:{total_size}"
                )
                headers["Content-Range"] = f"bytes {start}-{end}/{total_size}"

                return StreamingResponse(
                    stream_range(),
                    status_code=206,
                    media_type=ct,
                    headers=headers,
                )

        # ── Full file → 200 (streamed) ────────────────────────────────
        resp = await asyncio.to_thread(_s3_get_stream, client, bucket, key)
        s3_body = resp['Body']

        async def stream_full():
            try:
                while True:
                    chunk = await asyncio.to_thread(s3_body.read, STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
            finally:
                await asyncio.to_thread(s3_body.close)

        return StreamingResponse(
            stream_full(),
            status_code=200,
            media_type=ct,
            headers=_safari_safe_headers(
                content_length=total_size,
                etag_seed=f"{key}:{total_size}"
            ),
        )

    except Exception as e:
        err_str = str(e)
        if 'NoSuchKey' in err_str or '404' in err_str:
            raise HTTPException(status_code=404, detail="Not found")
        logger.error(f"R2 proxy error for {key}: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
