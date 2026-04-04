"""
Media Proxy — Secure asset delivery with DB-backed opaque tokens.

Layers:
  1. Opaque tokens (DB-stored, hashed) — replaces JWT-only signing
  2. Entitlement gating — ownership + role + session checks
  3. Anti-replay — single-use downloads, IP/UA binding
  4. HLS video streaming — tokenized manifest + segments
  5. Forensic watermarking — metadata + pixel/frame-level
  6. Telemetry — every access logged with IP, UA, event details
"""
import hashlib
import io
import logging
import os
import random
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from shared import db, get_current_user, get_admin_user
from services.media_token_service import (
    issue_token, validate_token, revoke_token, revoke_user_tokens,
    check_rate_limit, create_session, touch_session,
    check_and_respond_to_abuse, log_media_event,
    suspend_user_media, unsuspend_user_media,
)

logger = logging.getLogger("creatorstudio.media_proxy")
router = APIRouter(prefix="/media", tags=["Media Proxy"])

ROOT_DIR = Path(__file__).parent.parent
GENERATED_DIR = ROOT_DIR / "static" / "generated"
HLS_CACHE_DIR = GENERATED_DIR / "hls_cache"
HLS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

CONTENT_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".mp4": "video/mp4", ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".zip": "application/zip", ".pdf": "application/pdf",
    ".m3u8": "application/vnd.apple.mpegurl", ".ts": "video/mp2t",
}


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
        raise HTTPException(status_code=404, detail="File not found")
    return resolved


def _get_client_ip(request: Request) -> str:
    ip = request.headers.get("x-forwarded-for", request.headers.get("x-real-ip", request.client.host if request.client else "unknown"))
    if "," in ip:
        ip = ip.split(",")[0].strip()
    return ip


def _get_ua(request: Request) -> str:
    return request.headers.get("user-agent", "unknown")[:200]


# ── LEGACY: generate_secure_url for backend callers (now issues opaque token) ──

def generate_secure_url(file_url: str, asset_id: str, asset_type: str,
                        user_id: str, purpose: str = "preview") -> str:
    """
    Synchronous wrapper for backwards compat with viral_ideas_v2.py.
    Generates a preview token synchronously using a simpler HMAC approach
    for inline URL generation. Full DB-backed tokens used for downloads/HLS.
    """
    import base64
    import json
    import hmac
    secret = os.environ.get("MEDIA_SIGNING_SECRET", _FALLBACK_SECRET)
    payload = {
        "fref": file_url, "aid": asset_id, "atype": asset_type,
        "uid": user_id, "purpose": purpose,
        "exp": int(time.time()) + 300,
    }
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=") + "." + sig
    return f"/api/media/stream/{token}"

_FALLBACK_SECRET = uuid.uuid4().hex + uuid.uuid4().hex


def _verify_legacy_token(token: str) -> dict:
    """Verify HMAC-signed preview tokens (backwards compat)."""
    import base64
    import json
    import hmac
    parts = token.split(".")
    if len(parts) != 2:
        return None
    payload_b64, sig = parts
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
    except Exception:
        return None
    secret = os.environ.get("MEDIA_SIGNING_SECRET", _FALLBACK_SECRET)
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    payload = json.loads(payload_bytes)
    if payload.get("exp", 0) < int(time.time()):
        return None
    return payload


# ── WATERMARKING ──

def _watermark_image(image_path: Path, user_email: str, job_id: str) -> io.BytesIO:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", max(14, img.width // 30))
    except Exception:
        font = ImageFont.load_default()
    email_fragment = user_email.split("@")[0] if "@" in user_email else user_email
    text = f"{email_fragment} | {job_id[:8]}"
    for y in range(0, img.height, max(80, img.height // 5)):
        for x in range(0, img.width, max(200, img.width // 3)):
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 45))
    result = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    if image_path.suffix.lower() == ".png":
        result.save(buf, format="PNG")
    else:
        result.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf


def _forensic_watermark_image(image_path: Path, user_id: str, user_email: str,
                               asset_id: str, download_event_id: str) -> io.BytesIO:
    """Metadata + pixel-level seeded pattern for images."""
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
    import numpy as np

    forensic_id = f"UID:{user_id}|AID:{asset_id}|DL:{download_event_id}|TS:{int(time.time())}"
    img = Image.open(image_path).convert("RGB")

    # Pixel-level: seed PRNG with forensic_id, apply subtle noise to random pixels
    arr = np.array(img)
    rng = random.Random(forensic_id)
    h, w, _ = arr.shape
    num_pixels = max(100, (h * w) // 500)
    for _ in range(num_pixels):
        py, px = rng.randint(0, h - 1), rng.randint(0, w - 1)
        channel = rng.randint(0, 2)
        delta = rng.choice([-1, 1])
        val = int(arr[py, px, channel]) + delta
        arr[py, px, channel] = max(0, min(255, val))
    img = Image.fromarray(arr)

    buf = io.BytesIO()
    if image_path.suffix.lower() == ".png":
        metadata = PngInfo()
        metadata.add_text("Software", "VisionarySuite")
        metadata.add_text("Description", forensic_id)
        metadata.add_text("Comment", forensic_id)
        img.save(buf, format="PNG", pnginfo=metadata)
    else:
        try:
            import piexif
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = forensic_id.encode()
            exif_dict["0th"][piexif.ImageIFD.Software] = b"VisionarySuite"
            exif_bytes = piexif.dump(exif_dict)
            img.save(buf, format="JPEG", quality=95, exif=exif_bytes)
        except Exception:
            img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf


def _forensic_watermark_video(video_path: Path, user_id: str, user_email: str,
                               asset_id: str, download_event_id: str) -> Optional[Path]:
    """Metadata + frame-level overlay for videos."""
    forensic_id = f"UID:{user_id}|AID:{asset_id}|DL:{download_event_id}|TS:{int(time.time())}"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None

    email_frag = user_email.split("@")[0] if "@" in user_email else user_email[:8]
    output_path = video_path.parent / f"forensic_{download_event_id}_{video_path.name}"
    try:
        # Metadata + subtle text overlay in bottom-right corner (nearly invisible)
        subprocess.run([
            ffmpeg, "-i", str(video_path),
            "-vf", f"drawtext=text='{email_frag}':fontsize=8:fontcolor=white@0.03:x=w-tw-5:y=h-th-5",
            "-metadata", f"comment={forensic_id}",
            "-metadata", f"description={forensic_id}",
            "-c:a", "copy",
            "-y", str(output_path),
        ], capture_output=True, timeout=60)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
    except Exception as e:
        logger.warning(f"Video forensic watermark failed: {e}")
    return None


def _forensic_watermark_audio(audio_path: Path, user_id: str, asset_id: str,
                               download_event_id: str) -> Optional[Path]:
    forensic_id = f"UID:{user_id}|AID:{asset_id}|DL:{download_event_id}|TS:{int(time.time())}"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    output_path = audio_path.parent / f"forensic_{download_event_id}_{audio_path.name}"
    try:
        subprocess.run([
            ffmpeg, "-i", str(audio_path),
            "-metadata", f"comment={forensic_id}",
            "-metadata", "artist=VisionarySuite",
            "-codec", "copy", "-y", str(output_path),
        ], capture_output=True, timeout=30)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
    except Exception as e:
        logger.warning(f"Audio forensic watermark failed: {e}")
    return None


# ── HLS GENERATION ──

def _get_hls_dir(asset_id: str) -> Path:
    return HLS_CACHE_DIR / asset_id


def _generate_hls(video_path: Path, asset_id: str) -> bool:
    """Generate HLS segments from an MP4 file. Cached per asset."""
    hls_dir = _get_hls_dir(asset_id)
    manifest = hls_dir / "manifest.m3u8"
    if manifest.exists():
        return True
    hls_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    try:
        subprocess.run([
            ffmpeg, "-i", str(video_path),
            "-c:v", "libx264", "-c:a", "aac",
            "-hls_time", "4", "-hls_list_size", "0",
            "-hls_segment_filename", str(hls_dir / "seg_%03d.ts"),
            "-f", "hls", str(manifest),
        ], capture_output=True, timeout=120)
        return manifest.exists()
    except Exception as e:
        logger.warning(f"HLS generation failed: {e}")
        return False


# ── ENTITLEMENT ──

async def _check_entitlement(user: dict, asset: dict) -> dict:
    user_id = str(user["id"])
    role = user.get("role", "").upper()
    if role in ("ADMIN", "SUPERADMIN"):
        return {"allowed": True, "reason": "admin_bypass", "is_admin": True}
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


# ── REQUEST MODELS ──

class DownloadIssueRequest(BaseModel):
    asset_id: str

class AccessIssueRequest(BaseModel):
    asset_id: str

class HlsIssueRequest(BaseModel):
    asset_id: str

class SessionStartRequest(BaseModel):
    pass


# ── ENDPOINTS ──

@router.post("/session/start")
async def start_media_session(request: Request, user: dict = Depends(get_current_user)):
    ip = _get_client_ip(request)
    ua = _get_ua(request)
    role = user.get("role", "")
    session = await create_session(str(user["id"]), ip, ua, role)
    await log_media_event(str(user["id"]), "session_start", ip, ua, session_id=session["session_id"])
    return session


@router.post("/access/issue")
async def issue_access_token(req: AccessIssueRequest, request: Request, user: dict = Depends(get_current_user)):
    """Issue a preview/stream token (limited uses, short TTL)."""
    user_id = str(user["id"])
    ip = _get_client_ip(request)
    ua = _get_ua(request)

    abuse = await check_and_respond_to_abuse(user_id, ip, "access_issue")
    if abuse["blocked"]:
        raise HTTPException(status_code=429, detail=abuse["reason"])

    asset = await db.viral_assets.find_one({"asset_id": req.asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    result = await issue_token(
        user_id=user_id, asset_id=req.asset_id,
        file_ref=asset.get("file_url", ""), asset_type=asset.get("asset_type", "unknown"),
        purpose="preview", ip=ip, user_agent=ua,
    )
    await log_media_event(user_id, "access_token_issued", ip, ua, asset_id=req.asset_id)
    return {"url": f"/api/media/stream/{result['token']}", "ttl": result["ttl"]}


@router.post("/download/issue")
async def issue_download_token(req: DownloadIssueRequest, request: Request, user: dict = Depends(get_current_user)):
    """Issue a single-use download token with entitlement + rate limit checks."""
    user_id = str(user["id"])
    ip = _get_client_ip(request)
    ua = _get_ua(request)
    role = user.get("role", "").upper()
    is_admin = role in ("ADMIN", "SUPERADMIN")

    abuse = await check_and_respond_to_abuse(user_id, ip, "download_issue")
    if abuse["blocked"]:
        raise HTTPException(status_code=429, detail=abuse["reason"])

    asset = await db.viral_assets.find_one({"asset_id": req.asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    entitlement = await _check_entitlement(user, asset)
    if not entitlement["allowed"]:
        await log_media_event(user_id, "download_denied", ip, ua, asset_id=req.asset_id, reason=entitlement["reason"])
        if entitlement["reason"] == "pack_locked":
            raise HTTPException(status_code=402, detail="Pack is locked. Unlock it first.")
        elif entitlement["reason"] == "not_owner":
            raise HTTPException(status_code=403, detail="You do not own this asset.")
        raise HTTPException(status_code=403, detail="Download not permitted.")

    if not is_admin:
        within = await check_rate_limit(user_id)
        if not within:
            await log_media_event(user_id, "download_rate_limited", ip, ua, asset_id=req.asset_id)
            raise HTTPException(status_code=429, detail="Too many download requests. Try again later.")

    result = await issue_token(
        user_id=user_id, asset_id=req.asset_id,
        file_ref=asset.get("file_url", ""), asset_type=asset.get("asset_type", "unknown"),
        purpose="download", ip=ip, user_agent=ua,
        max_uses=1, ttl_seconds=60,
    )
    await log_media_event(user_id, "download_token_issued", ip, ua, asset_id=req.asset_id,
                          asset_type=asset.get("asset_type"), entitlement=entitlement["reason"])
    return {"url": f"/api/media/stream/{result['token']}", "ttl": result["ttl"], "single_use": True}


@router.post("/download-token")
async def legacy_download_token(req: DownloadIssueRequest, request: Request, user: dict = Depends(get_current_user)):
    """Legacy endpoint — redirects to new download/issue."""
    return await issue_download_token(req, request, user)


@router.post("/hls/issue")
async def issue_hls_token(req: HlsIssueRequest, request: Request, user: dict = Depends(get_current_user)):
    """Issue a tokenized HLS manifest URL for video playback."""
    user_id = str(user["id"])
    ip = _get_client_ip(request)
    ua = _get_ua(request)

    asset = await db.viral_assets.find_one({"asset_id": req.asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.get("asset_type") != "video":
        raise HTTPException(status_code=400, detail="HLS only for video assets")

    file_url = asset.get("file_url", "")
    file_path = _resolve_file_path(file_url)

    # Generate HLS if not cached
    if not _generate_hls(file_path, req.asset_id):
        raise HTTPException(status_code=500, detail="HLS generation failed")

    result = await issue_token(
        user_id=user_id, asset_id=req.asset_id,
        file_ref=file_url, asset_type="video",
        purpose="hls_manifest", ip=ip, user_agent=ua,
    )
    await log_media_event(user_id, "hls_token_issued", ip, ua, asset_id=req.asset_id)
    return {"manifest_url": f"/api/media/hls/manifest/{result['token']}", "ttl": result["ttl"]}


@router.get("/hls/manifest/{token}")
async def hls_manifest(token: str, request: Request):
    """Serve tokenized HLS manifest with tokenized segment URLs."""
    ip = _get_client_ip(request)
    ua = _get_ua(request)

    try:
        doc = await validate_token(token, ip, ua)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    asset_id = doc["asset_id"]
    hls_dir = _get_hls_dir(asset_id)
    manifest_path = hls_dir / "manifest.m3u8"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")

    # Read manifest and replace segment filenames with tokenized URLs
    content = manifest_path.read_text()
    lines = content.split("\n")
    new_lines = []
    for line in lines:
        if line.strip().endswith(".ts"):
            seg_name = line.strip()
            # Issue segment token
            seg_result = await issue_token(
                user_id=doc["user_id"], asset_id=asset_id,
                file_ref=seg_name, asset_type="hls_segment",
                purpose="hls_segment", ip=ip, user_agent=ua,
            )
            new_lines.append(f"/api/media/hls/segment/{seg_result['token']}/{asset_id}/{seg_name}")
        else:
            new_lines.append(line)

    tokenized_manifest = "\n".join(new_lines)
    await log_media_event(doc["user_id"], "hls_manifest_served", ip, ua, asset_id=asset_id)
    return StreamingResponse(
        io.BytesIO(tokenized_manifest.encode()),
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "no-store, private, max-age=0"},
    )


@router.get("/hls/segment/{token}/{asset_id}/{segment_name}")
async def hls_segment(token: str, asset_id: str, segment_name: str, request: Request):
    """Serve a tokenized HLS segment."""
    ip = _get_client_ip(request)
    ua = _get_ua(request)

    try:
        doc = await validate_token(token, ip, ua)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Validate segment exists
    hls_dir = _get_hls_dir(asset_id)
    seg_path = (hls_dir / segment_name).resolve()
    if not str(seg_path).startswith(str(hls_dir)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not seg_path.exists():
        raise HTTPException(status_code=404, detail="Segment not found")

    await log_media_event(doc["user_id"], "hls_segment_served", ip, ua,
                          asset_id=asset_id, segment=segment_name)

    def seg_stream():
        with open(seg_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(seg_stream(), media_type="video/mp2t",
                             headers={"Cache-Control": "no-store, private, max-age=0"})


@router.get("/stream/{token}")
async def stream_media(token: str, request: Request):
    """Stream media via token — supports both opaque DB tokens and legacy HMAC tokens."""
    ip = _get_client_ip(request)
    ua = _get_ua(request)

    # Try opaque DB token first
    doc = None
    try:
        doc = await validate_token(token, ip, ua)
    except ValueError:
        pass

    if doc:
        file_path = _resolve_file_path(doc["file_ref"])
        purpose = doc["purpose"]
        user_id = doc["user_id"]
        asset_type = doc.get("asset_type", "unknown")
        asset_id = doc.get("asset_id", "")
        await touch_session(doc.get("session_id", ""))
    else:
        # Fall back to legacy HMAC token (for preview URLs in API responses)
        payload = _verify_legacy_token(token)
        if not payload:
            raise HTTPException(status_code=403, detail="Invalid or expired token")
        file_path = _resolve_file_path(payload["fref"])
        purpose = payload.get("purpose", "preview")
        user_id = payload.get("uid", "unknown")
        asset_type = payload.get("atype", "unknown")
        asset_id = payload.get("aid", "")

    ext = file_path.suffix.lower()
    content_type = CONTENT_TYPES.get(ext, "application/octet-stream")

    is_admin = False
    user_email = "user"
    if user_id not in ("unknown", "public_share"):
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1, "email": 1})
        if user_doc:
            is_admin = user_doc.get("role", "").upper() in ("ADMIN", "SUPERADMIN")
            user_email = user_doc.get("email", "user")

    await log_media_event(user_id, f"stream_{purpose}", ip, ua,
                          asset_id=asset_id, asset_type=asset_type, purpose=purpose, file_ext=ext)

    # ── DOWNLOAD: forensic watermark ──
    if purpose == "download" and not is_admin:
        download_event_id = uuid.uuid4().hex[:16]

        if ext in (".png", ".jpg", ".jpeg"):
            try:
                buf = _forensic_watermark_image(file_path, user_id, user_email, asset_id, download_event_id)
                await log_media_event(user_id, "forensic_download", ip, ua,
                                      asset_id=asset_id, forensic_id=download_event_id, watermark_type="image_pixel+metadata")
                return StreamingResponse(buf, media_type=content_type, headers={
                    "Cache-Control": "no-store, private, max-age=0",
                    "X-Content-Type-Options": "nosniff",
                    "Content-Disposition": f"attachment; filename=\"{file_path.name}\"",
                })
            except Exception as e:
                logger.warning(f"Image forensic failed: {e}")

        elif ext == ".mp4":
            try:
                fp = _forensic_watermark_video(file_path, user_id, user_email, asset_id, download_event_id)
                if fp:
                    await log_media_event(user_id, "forensic_download", ip, ua,
                                          asset_id=asset_id, forensic_id=download_event_id, watermark_type="video_frame+metadata")
                    fsize = fp.stat().st_size
                    def v_stream():
                        try:
                            with open(fp, "rb") as f:
                                while True:
                                    chunk = f.read(8192)
                                    if not chunk:
                                        break
                                    yield chunk
                        finally:
                            try:
                                fp.unlink(missing_ok=True)
                            except Exception:
                                pass
                    return StreamingResponse(v_stream(), media_type=content_type, headers={
                        "Cache-Control": "no-store, private, max-age=0",
                        "Content-Length": str(fsize),
                        "Content-Disposition": f"attachment; filename=\"{file_path.name}\"",
                    })
            except Exception as e:
                logger.warning(f"Video forensic failed: {e}")

        elif ext in (".mp3", ".wav"):
            try:
                fp = _forensic_watermark_audio(file_path, user_id, asset_id, download_event_id)
                if fp:
                    await log_media_event(user_id, "forensic_download", ip, ua,
                                          asset_id=asset_id, forensic_id=download_event_id, watermark_type="audio_metadata")
                    fsize = fp.stat().st_size
                    def a_stream():
                        try:
                            with open(fp, "rb") as f:
                                while True:
                                    chunk = f.read(8192)
                                    if not chunk:
                                        break
                                    yield chunk
                        finally:
                            try:
                                fp.unlink(missing_ok=True)
                            except Exception:
                                pass
                    return StreamingResponse(a_stream(), media_type=content_type, headers={
                        "Cache-Control": "no-store, private, max-age=0",
                        "Content-Length": str(fsize),
                        "Content-Disposition": f"attachment; filename=\"{file_path.name}\"",
                    })
            except Exception as e:
                logger.warning(f"Audio forensic failed: {e}")

        elif ext == ".zip":
            # For ZIP: inject trace_manifest.json
            try:
                buf = _forensic_watermark_zip(file_path, user_id, user_email, asset_id, download_event_id)
                if buf:
                    await log_media_event(user_id, "forensic_download", ip, ua,
                                          asset_id=asset_id, forensic_id=download_event_id, watermark_type="zip_trace_manifest")
                    return StreamingResponse(buf, media_type="application/zip", headers={
                        "Cache-Control": "no-store, private, max-age=0",
                        "Content-Disposition": f"attachment; filename=\"{file_path.name}\"",
                    })
            except Exception as e:
                logger.warning(f"ZIP forensic failed: {e}")

    # ── PREVIEW: visible watermark on images ──
    if ext in (".png", ".jpg", ".jpeg") and not is_admin:
        try:
            buf = _watermark_image(file_path, user_email, asset_id)
            headers = {"Cache-Control": "no-store, private, max-age=0", "X-Content-Type-Options": "nosniff"}
            if purpose == "download":
                headers["Content-Disposition"] = f"attachment; filename=\"{file_path.name}\""
            else:
                headers["Content-Disposition"] = f"inline; filename=\"preview_{file_path.name}\""
            return StreamingResponse(buf, media_type=content_type, headers=headers)
        except Exception as e:
            logger.warning(f"Watermark failed: {e}")

    # ── RAW STREAM ──
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

    # Range requests for video/audio seeking
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


# ── ZIP FORENSIC WATERMARKING ──

def _forensic_watermark_zip(zip_path: Path, user_id: str, user_email: str,
                             asset_id: str, download_event_id: str) -> Optional[io.BytesIO]:
    """Inject trace_manifest.json into ZIP file."""
    import zipfile
    import json
    forensic_id = f"UID:{user_id}|AID:{asset_id}|DL:{download_event_id}|TS:{int(time.time())}"
    trace = json.dumps({
        "trace_id": forensic_id,
        "user": user_email.split("@")[0] if "@" in user_email else user_email,
        "asset_id": asset_id,
        "download_event": download_event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notice": "This file is licensed. Unauthorized redistribution is prohibited.",
    }, indent=2)

    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_path, "r") as src, zipfile.ZipFile(buf, "w") as dst:
            for item in src.infolist():
                dst.writestr(item, src.read(item.filename))
            dst.writestr("trace_manifest.json", trace)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.warning(f"ZIP forensic failed: {e}")
        return None
