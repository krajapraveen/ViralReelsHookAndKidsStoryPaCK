"""
Media Proxy — Secure asset access with signed tokens, watermarking, and telemetry.
No raw URLs ever exposed to frontend. All media goes through this proxy.

Layers:
  1. Entitlement Gating — ownership + role checks on token issuance, rate limiting
  2. Telemetry / Abuse Detection — rich logging, anomaly flagging, admin visibility
  3. Forensic Watermarking — visible watermark on previews, metadata forensic ID on downloads
"""
import hmac
import hashlib
import json
import time
import uuid
import os
import io
import logging
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from shared import db, get_current_user, get_admin_user

logger = logging.getLogger("creatorstudio.media_proxy")
router = APIRouter(prefix="/media", tags=["Media Proxy"])

ROOT_DIR = Path(__file__).parent.parent
GENERATED_DIR = ROOT_DIR / "static" / "generated"

# Server-side signing secret
_MEDIA_SECRET = os.environ.get("MEDIA_SIGNING_SECRET", uuid.uuid4().hex + uuid.uuid4().hex)

PREVIEW_TTL = 300
DOWNLOAD_TTL = 120

# Entitlement gating: rate limits
DOWNLOAD_TOKEN_LIMIT_PER_HOUR = 30   # max download tokens per user per hour
STREAM_TOKEN_LIMIT_PER_HOUR = 200    # max stream requests per user per hour
ABUSE_FLAG_THRESHOLD = 50            # flag user if > N download tokens in 1 hour

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


# ==================== FORENSIC WATERMARKING ====================

def _forensic_watermark_image(image_path: Path, user_id: str, user_email: str,
                               asset_id: str, download_event_id: str) -> io.BytesIO:
    """Embed forensic identifier in image EXIF/metadata for leak tracing."""
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    forensic_id = f"UID:{user_id}|AID:{asset_id}|DL:{download_event_id}|TS:{int(time.time())}"
    img = Image.open(image_path)

    buf = io.BytesIO()
    if image_path.suffix.lower() == ".png":
        metadata = PngInfo()
        metadata.add_text("Software", "VisionarySuite")
        metadata.add_text("Description", forensic_id)
        metadata.add_text("Comment", forensic_id)
        img.save(buf, format="PNG", pnginfo=metadata)
    else:
        import piexif
        try:
            exif_dict = piexif.load(img.info.get("exif", b""))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = forensic_id.encode()
        exif_dict["0th"][piexif.ImageIFD.Software] = b"VisionarySuite"
        exif_bytes = piexif.dump(exif_dict)
        img.save(buf, format="JPEG", quality=95, exif=exif_bytes)

    buf.seek(0)
    return buf


def _forensic_watermark_video(video_path: Path, user_id: str, user_email: str,
                               asset_id: str, download_event_id: str) -> Optional[Path]:
    """Embed forensic identifier in video metadata via ffmpeg."""
    forensic_id = f"UID:{user_id}|AID:{asset_id}|DL:{download_event_id}|TS:{int(time.time())}"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.warning("ffmpeg not found, skipping video forensic watermark")
        return None

    output_path = video_path.parent / f"forensic_{video_path.name}"
    try:
        subprocess.run([
            ffmpeg, "-i", str(video_path),
            "-metadata", f"comment={forensic_id}",
            "-metadata", f"description={forensic_id}",
            "-codec", "copy",
            "-y", str(output_path),
        ], capture_output=True, timeout=30)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
    except Exception as e:
        logger.warning(f"Video forensic watermark failed: {e}")
    return None


def _forensic_watermark_audio(audio_path: Path, user_id: str, asset_id: str,
                               download_event_id: str) -> Optional[Path]:
    """Embed forensic identifier in audio metadata via ffmpeg."""
    forensic_id = f"UID:{user_id}|AID:{asset_id}|DL:{download_event_id}|TS:{int(time.time())}"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    output_path = audio_path.parent / f"forensic_{audio_path.name}"
    try:
        subprocess.run([
            ffmpeg, "-i", str(audio_path),
            "-metadata", f"comment={forensic_id}",
            "-metadata", "artist=VisionarySuite",
            "-codec", "copy",
            "-y", str(output_path),
        ], capture_output=True, timeout=30)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
    except Exception as e:
        logger.warning(f"Audio forensic watermark failed: {e}")
    return None


# ==================== ENTITLEMENT & RATE LIMITING ====================

async def _check_rate_limit(user_id: str, action: str, limit: int) -> bool:
    """Check if user has exceeded rate limit. Returns True if WITHIN limit."""
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    count = await db.media_access_log.count_documents({
        "user_id": user_id,
        "action": action,
        "timestamp": {"$gte": one_hour_ago},
    })
    return count < limit


async def _flag_abuse(user_id: str, reason: str, details: dict):
    """Flag a user for suspicious media access behavior."""
    await db.media_abuse_flags.insert_one({
        "flag_id": str(uuid.uuid4()),
        "user_id": user_id,
        "reason": reason,
        "details": details,
        "status": "open",
        "created_at": datetime.now(timezone.utc),
    })
    logger.warning(f"ABUSE FLAG: user={user_id} reason={reason}")


async def _log_media_event(user_id: str, action: str, request: Request, **extra):
    """Rich telemetry logging with IP, user-agent, and extra metadata."""
    ip = request.headers.get("x-forwarded-for", request.headers.get("x-real-ip", request.client.host if request.client else "unknown"))
    if "," in ip:
        ip = ip.split(",")[0].strip()
    await db.media_access_log.insert_one({
        "user_id": user_id,
        "action": action,
        "ip": ip,
        "user_agent": request.headers.get("user-agent", "unknown")[:200],
        "timestamp": datetime.now(timezone.utc),
        **extra,
    })


async def _check_entitlement(user: dict, asset: dict) -> dict:
    """
    Check if user is entitled to download this asset.
    Returns dict with 'allowed' bool and 'reason' string.
    """
    user_id = str(user["id"])
    role = user.get("role", "").upper()

    # Admin bypass
    if role in ("ADMIN", "SUPERADMIN"):
        return {"allowed": True, "reason": "admin_bypass", "is_admin": True}

    # Check ownership: user must own the job this asset belongs to
    job_id = asset.get("job_id")
    if job_id:
        job = await db.viral_jobs.find_one({"job_id": job_id}, {"_id": 0, "user_id": 1, "locked": 1})
        if not job:
            return {"allowed": False, "reason": "job_not_found"}
        if job["user_id"] != user_id:
            return {"allowed": False, "reason": "not_owner"}
        if job.get("locked", False):
            return {"allowed": False, "reason": "pack_locked"}

    return {"allowed": True, "reason": "owner", "is_admin": False}


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
async def get_download_token(req: DownloadTokenRequest, request: Request, user: dict = Depends(get_current_user)):
    user_id = str(user["id"])
    role = user.get("role", "").upper()
    is_admin = role in ("ADMIN", "SUPERADMIN")

    asset = await db.viral_assets.find_one({"asset_id": req.asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    file_url = asset.get("file_url")
    if not file_url:
        raise HTTPException(status_code=404, detail="No file for this asset")

    # --- Entitlement check ---
    entitlement = await _check_entitlement(user, asset)
    if not entitlement["allowed"]:
        await _log_media_event(user_id, "download_denied", request,
                               asset_id=req.asset_id, reason=entitlement["reason"])
        if entitlement["reason"] == "pack_locked":
            raise HTTPException(status_code=402, detail="Pack is locked. Unlock it first to download.")
        elif entitlement["reason"] == "not_owner":
            raise HTTPException(status_code=403, detail="You do not own this asset.")
        raise HTTPException(status_code=403, detail="Download not permitted.")

    # --- Rate limit check ---
    if not is_admin:
        within_limit = await _check_rate_limit(user_id, "download_token", DOWNLOAD_TOKEN_LIMIT_PER_HOUR)
        if not within_limit:
            await _flag_abuse(user_id, "download_rate_exceeded", {
                "asset_id": req.asset_id, "limit": DOWNLOAD_TOKEN_LIMIT_PER_HOUR,
            })
            await _log_media_event(user_id, "download_rate_limited", request, asset_id=req.asset_id)
            raise HTTPException(status_code=429, detail="Too many download requests. Please try again later.")

    url = generate_secure_url(
        file_url=file_url, asset_id=req.asset_id,
        asset_type=asset.get("asset_type", "unknown"),
        user_id=user_id, purpose="download",
    )
    await _log_media_event(user_id, "download_token", request,
                           asset_id=req.asset_id, asset_type=asset.get("asset_type"),
                           entitlement=entitlement["reason"])
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
    if user_id not in ("unknown", "public_share"):
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1, "email": 1})
        if user_doc:
            is_admin = user_doc.get("role", "").upper() in ("ADMIN", "SUPERADMIN")
            user_email = user_doc.get("email", "user")

    # Log every stream with rich telemetry
    await _log_media_event(user_id, f"stream_{purpose}", request,
                           asset_id=payload.get("aid"), asset_type=asset_type,
                           purpose=purpose, file_ext=ext)

    # ── DOWNLOAD PURPOSE: apply forensic watermark ──
    if purpose == "download" and not is_admin:
        download_event_id = uuid.uuid4().hex[:16]
        forensic_path = None

        if ext in (".png", ".jpg", ".jpeg"):
            try:
                forensic_buf = _forensic_watermark_image(
                    file_path, user_id, user_email,
                    payload.get("aid", ""), download_event_id)
                await _log_media_event(user_id, "forensic_download", request,
                                       asset_id=payload.get("aid"), asset_type=asset_type,
                                       forensic_id=download_event_id, watermark_type="image_metadata")
                headers = {
                    "Cache-Control": "no-store, private, max-age=0",
                    "X-Content-Type-Options": "nosniff",
                    "Content-Disposition": f"attachment; filename=\"{file_path.name}\"",
                }
                return StreamingResponse(forensic_buf, media_type=content_type, headers=headers)
            except Exception as e:
                logger.warning(f"Image forensic watermark failed: {e}")

        elif ext == ".mp4":
            try:
                forensic_path = _forensic_watermark_video(
                    file_path, user_id, user_email,
                    payload.get("aid", ""), download_event_id)
                if forensic_path:
                    await _log_media_event(user_id, "forensic_download", request,
                                           asset_id=payload.get("aid"), asset_type=asset_type,
                                           forensic_id=download_event_id, watermark_type="video_metadata")
                    fsize = forensic_path.stat().st_size
                    def forensic_video_stream():
                        try:
                            with open(forensic_path, "rb") as f:
                                while True:
                                    chunk = f.read(8192)
                                    if not chunk:
                                        break
                                    yield chunk
                        finally:
                            try:
                                forensic_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                    headers = {
                        "Cache-Control": "no-store, private, max-age=0",
                        "X-Content-Type-Options": "nosniff",
                        "Content-Length": str(fsize),
                        "Content-Disposition": f"attachment; filename=\"{file_path.name}\"",
                    }
                    return StreamingResponse(forensic_video_stream(), media_type=content_type, headers=headers)
            except Exception as e:
                logger.warning(f"Video forensic watermark failed: {e}")

        elif ext in (".mp3", ".wav"):
            try:
                forensic_path = _forensic_watermark_audio(
                    file_path, user_id, payload.get("aid", ""), download_event_id)
                if forensic_path:
                    await _log_media_event(user_id, "forensic_download", request,
                                           asset_id=payload.get("aid"), asset_type=asset_type,
                                           forensic_id=download_event_id, watermark_type="audio_metadata")
                    fsize = forensic_path.stat().st_size
                    def forensic_audio_stream():
                        try:
                            with open(forensic_path, "rb") as f:
                                while True:
                                    chunk = f.read(8192)
                                    if not chunk:
                                        break
                                    yield chunk
                        finally:
                            try:
                                forensic_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                    headers = {
                        "Cache-Control": "no-store, private, max-age=0",
                        "X-Content-Type-Options": "nosniff",
                        "Content-Length": str(fsize),
                        "Content-Disposition": f"attachment; filename=\"{file_path.name}\"",
                    }
                    return StreamingResponse(forensic_audio_stream(), media_type=content_type, headers=headers)
            except Exception as e:
                logger.warning(f"Audio forensic watermark failed: {e}")

    # ── PREVIEW PURPOSE: visible watermark on images ──
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
            return StreamingResponse(watermarked_buf, media_type=content_type, headers=headers)
        except Exception as e:
            logger.warning(f"Watermark failed, serving raw: {e}")

    # ── RAW STREAM: video/audio/zip/admin ──
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

    return StreamingResponse(file_stream(), media_type=content_type, headers=headers)


# ==================== ADMIN TELEMETRY ENDPOINTS ====================

@router.get("/admin/access-log")
async def get_access_log(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    hours: int = 24,
    limit: int = 100,
    admin: dict = Depends(get_admin_user),
):
    """Admin: view media access logs with filters."""
    query = {"timestamp": {"$gte": datetime.now(timezone.utc) - timedelta(hours=hours)}}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action

    logs = await db.media_access_log.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)

    for log in logs:
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()

    return {"logs": logs, "count": len(logs), "hours": hours}


@router.get("/admin/abuse-flags")
async def get_abuse_flags(
    status: str = "open",
    limit: int = 50,
    admin: dict = Depends(get_admin_user),
):
    """Admin: view abuse flags."""
    query = {}
    if status != "all":
        query["status"] = status

    flags = await db.media_abuse_flags.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)

    for flag in flags:
        if isinstance(flag.get("created_at"), datetime):
            flag["created_at"] = flag["created_at"].isoformat()

    return {"flags": flags, "count": len(flags)}


@router.post("/admin/abuse-flags/{flag_id}/resolve")
async def resolve_abuse_flag(flag_id: str, admin: dict = Depends(get_admin_user)):
    """Admin: mark an abuse flag as resolved."""
    result = await db.media_abuse_flags.update_one(
        {"flag_id": flag_id},
        {"$set": {"status": "resolved", "resolved_by": str(admin["id"]),
                  "resolved_at": datetime.now(timezone.utc)}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"success": True}


@router.get("/admin/telemetry-summary")
async def get_telemetry_summary(
    hours: int = 24,
    admin: dict = Depends(get_admin_user),
):
    """Admin: aggregated telemetry summary for media access."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {
            "_id": "$action",
            "count": {"$sum": 1},
            "unique_users": {"$addToSet": "$user_id"},
        }},
    ]
    results = await db.media_access_log.aggregate(pipeline).to_list(50)

    summary = {}
    for r in results:
        summary[r["_id"]] = {
            "count": r["count"],
            "unique_users": len(r["unique_users"]),
        }

    # Top users by download activity
    top_downloaders_pipeline = [
        {"$match": {"timestamp": {"$gte": since}, "action": "download_token"}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_downloaders = await db.media_access_log.aggregate(top_downloaders_pipeline).to_list(10)

    # Failed/denied events
    denied_count = await db.media_access_log.count_documents({
        "timestamp": {"$gte": since},
        "action": {"$in": ["download_denied", "download_rate_limited"]},
    })

    open_flags = await db.media_abuse_flags.count_documents({"status": "open"})

    return {
        "hours": hours,
        "action_summary": summary,
        "top_downloaders": [{"user_id": d["_id"], "downloads": d["count"]} for d in top_downloaders],
        "denied_events": denied_count,
        "open_abuse_flags": open_flags,
    }
