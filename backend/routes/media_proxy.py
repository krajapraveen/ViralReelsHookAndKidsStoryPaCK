"""
Media Proxy — Secure asset access with signed tokens, watermarking, and telemetry.
No raw URLs ever exposed to frontend. All media goes through this proxy.
"""
import hmac
import hashlib
import json
import time
import uuid
import os
import io
import logging
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List

from shared import db, get_current_user

logger = logging.getLogger("creatorstudio.media_proxy")
router = APIRouter(prefix="/media", tags=["Media Proxy"])

ROOT_DIR = Path(__file__).parent.parent
GENERATED_DIR = ROOT_DIR / "static" / "generated"

# Server-side signing secret
_MEDIA_SECRET = os.environ.get("MEDIA_SIGNING_SECRET", uuid.uuid4().hex + uuid.uuid4().hex)

PREVIEW_TTL = 300
DOWNLOAD_TTL = 120

CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".zip": "application/zip",
    ".pdf": "application/pdf",
}


def _sign_payload(payload: dict) -> str:
    import base64
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    sig = hmac.new(_MEDIA_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=") + "." + sig
    return token


def _verify_token(token: str) -> dict:
    import base64
    parts = token.split(".")
    if len(parts) != 2:
        raise HTTPException(status_code=403, detail="Malformed token")
    payload_b64, sig = parts
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid token encoding")
    expected_sig = hmac.new(_MEDIA_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=403, detail="Invalid token signature")
    payload = json.loads(payload_bytes)
    if time.time() > payload.get("exp", 0):
        raise HTTPException(status_code=403, detail="Token expired")
    return payload


def _resolve_file_path(file_ref: str) -> Path:
    clean = file_ref
    for prefix in ["/api/static/", "/static/", "/"]:
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
            break
    resolved = (ROOT_DIR / "static" / clean).resolve()
    if not str(resolved).startswith(str(ROOT_DIR / "static")):
        raise HTTPException(status_code=403, detail="Access denied")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    return resolved


def _watermark_image(image_path: Path, user_email: str, job_id: str) -> io.BytesIO:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    email_fragment = user_email.split("@")[0] if user_email else "user"
    job_fragment = job_id[:8] if job_id else ""
    wm_text = f"{email_fragment} | {job_fragment}"

    font_size = max(16, img.size[0] // 25)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), wm_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    step_x = text_width + 80
    step_y = text_height + 100

    for y in range(-img.size[1], img.size[1] * 2, step_y):
        for x in range(-img.size[0], img.size[0] * 2, step_x):
            txt_img = Image.new("RGBA", (text_width + 20, text_height + 20), (0, 0, 0, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text((10, 10), wm_text, font=font, fill=(255, 255, 255, 45))
            rotated = txt_img.rotate(30, expand=True, fillcolor=(0, 0, 0, 0))
            overlay.paste(rotated, (x, y), rotated)

    result = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    if image_path.suffix.lower() == ".png":
        result.save(buf, format="PNG")
    else:
        result.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf


def generate_secure_url(file_url: str, asset_id: str, asset_type: str,
                        user_id: str, purpose: str = "preview") -> str:
    ttl = PREVIEW_TTL if purpose == "preview" else DOWNLOAD_TTL
    payload = {
        "uid": user_id,
        "aid": asset_id,
        "fref": file_url,
        "atype": asset_type,
        "purpose": purpose,
        "nonce": uuid.uuid4().hex[:12],
        "exp": int(time.time()) + ttl,
    }
    return f"/api/media/stream/{_sign_payload(payload)}"


class SecureUrlRequest(BaseModel):
    asset_ids: List[str]
    purpose: str = "preview"


@router.post("/secure-urls")
async def get_secure_urls(req: SecureUrlRequest, user: dict = Depends(get_current_user)):
    assets = []
    for aid in req.asset_ids:
        asset = await db.viral_assets.find_one({"asset_id": aid}, {"_id": 0})
        if asset:
            assets.append(asset)
    urls = {}
    for asset in assets:
        aid = asset["asset_id"]
        file_url = asset.get("file_url")
        if not file_url:
            continue
        urls[aid] = generate_secure_url(
            file_url=file_url, asset_id=aid,
            asset_type=asset.get("asset_type", "unknown"),
            user_id=str(user["id"]), purpose=req.purpose,
        )
    await db.media_access_log.insert_one({
        "user_id": str(user["id"]), "action": "token_batch",
        "asset_ids": req.asset_ids, "purpose": req.purpose,
        "count": len(urls), "timestamp": datetime.now(timezone.utc),
    })
    return {"urls": urls, "ttl": PREVIEW_TTL if req.purpose == "preview" else DOWNLOAD_TTL}


class DownloadTokenRequest(BaseModel):
    asset_id: str


@router.post("/download-token")
async def get_download_token(req: DownloadTokenRequest, user: dict = Depends(get_current_user)):
    asset = await db.viral_assets.find_one({"asset_id": req.asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    file_url = asset.get("file_url")
    if not file_url:
        raise HTTPException(status_code=404, detail="No file for this asset")
    url = generate_secure_url(
        file_url=file_url, asset_id=req.asset_id,
        asset_type=asset.get("asset_type", "unknown"),
        user_id=str(user["id"]), purpose="download",
    )
    await db.media_access_log.insert_one({
        "user_id": str(user["id"]), "action": "download_token",
        "asset_id": req.asset_id, "asset_type": asset.get("asset_type"),
        "timestamp": datetime.now(timezone.utc),
    })
    return {"url": url, "ttl": DOWNLOAD_TTL}


@router.get("/stream/{token}")
async def stream_media(token: str, request: Request):
    payload = _verify_token(token)
    file_ref = payload["fref"]
    asset_type = payload.get("atype", "unknown")
    purpose = payload.get("purpose", "preview")
    user_id = payload.get("uid", "unknown")

    file_path = _resolve_file_path(file_ref)
    ext = file_path.suffix.lower()
    content_type = CONTENT_TYPES.get(ext, "application/octet-stream")

    is_admin = False
    user_email = "user"
    if user_id != "unknown":
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1, "email": 1})
        if user_doc:
            is_admin = user_doc.get("role", "").upper() in ("ADMIN", "SUPERADMIN")
            user_email = user_doc.get("email", "user")

    # Watermark images for non-admin users
    if ext in (".png", ".jpg", ".jpeg") and not is_admin:
        try:
            job_id = payload.get("aid", "")
            watermarked_buf = _watermark_image(file_path, user_email, job_id)
            headers = {
                "Cache-Control": "no-store, private, max-age=0",
                "X-Content-Type-Options": "nosniff",
            }
            if purpose == "download":
                headers["Content-Disposition"] = f"attachment; filename=\"{file_path.name}\""
            else:
                headers["Content-Disposition"] = f"inline; filename=\"preview_{file_path.name}\""
            await db.media_access_log.insert_one({
                "user_id": user_id, "action": "stream", "asset_id": payload.get("aid"),
                "asset_type": asset_type, "purpose": purpose, "watermarked": True,
                "timestamp": datetime.now(timezone.utc),
            })
            return StreamingResponse(watermarked_buf, media_type=content_type, headers=headers)
        except Exception as e:
            logger.warning(f"Watermark failed, serving raw: {e}")

    # Stream raw file for video/audio/zip/admin
    file_size = file_path.stat().st_size
    headers = {
        "Cache-Control": "no-store, private, max-age=0",
        "X-Content-Type-Options": "nosniff",
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
    }
    if purpose == "download":
        headers["Content-Disposition"] = f"attachment; filename=\"{file_path.name}\""
    else:
        headers["Content-Disposition"] = f"inline; filename=\"{file_path.name}\""

    # Handle range requests for video/audio seeking
    range_header = request.headers.get("range")
    if range_header and ext in (".mp4", ".mp3", ".wav"):
        try:
            range_spec = range_header.replace("bytes=", "")
            start_str, end_str = range_spec.split("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            end = min(end, file_size - 1)
            length = end - start + 1

            def range_stream():
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = f.read(min(8192, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(length)
            await db.media_access_log.insert_one({
                "user_id": user_id, "action": "stream_range",
                "asset_id": payload.get("aid"), "asset_type": asset_type,
                "timestamp": datetime.now(timezone.utc),
            })
            return StreamingResponse(range_stream(), status_code=206, media_type=content_type, headers=headers)
        except (ValueError, IndexError):
            pass

    def file_stream():
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    await db.media_access_log.insert_one({
        "user_id": user_id, "action": "stream", "asset_id": payload.get("aid"),
        "asset_type": asset_type, "purpose": purpose, "watermarked": False,
        "timestamp": datetime.now(timezone.utc),
    })
    return StreamingResponse(file_stream(), media_type=content_type, headers=headers)
