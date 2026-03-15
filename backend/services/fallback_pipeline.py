"""
Fallback Pipeline Service
When final MP4 rendering stalls or fails, provides alternative deliverables:
1. Lightweight fallback MP4 (slideshow-style)
2. Story Pack ZIP (all assets bundled)
3. Preview data (scene images + audio + text)
4. Individual R2 asset links

Users should always receive at least one useful deliverable.
"""

import os
import io
import json
import uuid
import asyncio
import zipfile
import tempfile
import shutil
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from shared import db

logger = logging.getLogger("fallback_pipeline")

STATIC_DIR = Path("/app/backend/static/generated")
STATIC_DIR.mkdir(parents=True, exist_ok=True)


async def _download_to_bytes(url: str, timeout: int = 30) -> bytes:
    """Download a file from URL and return bytes."""
    import aiohttp
    try:
        # Presign R2 URLs
        presigned_url = url
        if url and url.startswith("http"):
            try:
                from utils.r2_presign import presign_url
                if ".r2.dev/" in url or "r2.cloudflarestorage.com" in url:
                    presigned_url = presign_url(url, expiry=600)
            except Exception:
                pass

        async with aiohttp.ClientSession() as sess:
            async with sess.get(presigned_url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        logger.warning(f"Download failed for {url[:60]}: {e}")
    return b""


async def generate_fallback_mp4(job: dict) -> dict:
    """Generate a lightweight slideshow-style MP4 fallback.
    Static scene images with synced voice narration.
    No heavy transitions, low resolution, fast single-pass encode.
    """
    job_id = job["job_id"]
    scenes = job.get("scenes", [])
    scene_images = job.get("scene_images", {})
    scene_voices = job.get("scene_voices", {})

    sorted_scenes = sorted(scenes, key=lambda s: s.get("scene_number", 0))
    temp_dir = tempfile.mkdtemp()

    try:
        # Collect valid scenes with both image and audio
        valid = []
        for scene in sorted_scenes:
            sn = str(scene.get("scene_number", 0))
            img_info = scene_images.get(sn, {})
            voice_info = scene_voices.get(sn, {})

            img_path = img_info.get("path", "")
            voice_path = voice_info.get("path", "")

            # Try local files first, then download from R2
            local_img = os.path.join(temp_dir, f"img_{sn}.png")
            local_voice = os.path.join(temp_dir, f"voice_{sn}.mp3")

            if img_path and os.path.exists(img_path):
                local_img = img_path
            elif img_info.get("url"):
                data = await _download_to_bytes(img_info["url"])
                if data:
                    with open(local_img, "wb") as f:
                        f.write(data)
                else:
                    continue
            else:
                continue

            if voice_path and os.path.exists(voice_path):
                local_voice = voice_path
            elif voice_info.get("url"):
                data = await _download_to_bytes(voice_info["url"])
                if data:
                    with open(local_voice, "wb") as f:
                        f.write(data)
                else:
                    continue
            else:
                continue

            dur = voice_info.get("duration", 5.0)
            valid.append({"sn": sn, "img": local_img, "voice": local_voice, "duration": dur})

        if not valid:
            return {"success": False, "error": "No valid scenes with assets"}

        # Build lightweight FFmpeg command: 480p, 10fps, veryfast, CRF 32
        n = len(valid)
        inputs = []
        filter_parts = []
        total_duration = 0.0
        W, H, FPS = 640, 360, 10

        for i, v in enumerate(valid):
            dur = v["duration"] + 0.3
            total_duration += dur
            v_idx = i * 2
            a_idx = i * 2 + 1
            inputs.extend(["-loop", "1", "-t", f"{dur:.2f}", "-i", v["img"]])
            inputs.extend(["-i", v["voice"]])
            filter_parts.append(
                f"[{v_idx}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={FPS}[v{i}]"
            )

        v_concat = ''.join(f'[v{i}]' for i in range(n))
        filter_parts.append(f"{v_concat}concat=n={n}:v=1:a=0[vout]")

        for i in range(n):
            a_idx = i * 2 + 1
            filter_parts.append(f"[{a_idx}:a]aresample=44100[a{i}]")

        a_concat = ''.join(f'[a{i}]' for i in range(n))
        filter_parts.append(f"{a_concat}concat=n={n}:v=0:a=1[aout]")

        filter_complex = ';'.join(filter_parts)

        output_fn = f"fallback_{job_id[:12]}.mp4"
        videos_dir = STATIC_DIR / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        final_path = str(videos_dir / output_fn)

        cmd = [
            "ffmpeg", "-nostdin", "-loglevel", "error", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "32",
            "-r", str(FPS), "-threads", "1",
            "-c:a", "aac", "-b:a", "64k",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            final_path,
        ]

        logger.info(f"[FALLBACK {job_id[:8]}] Rendering lightweight MP4: {n} scenes, {W}x{H}, {FPS}fps")

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"success": False, "error": "Fallback render timed out"}

        if proc.returncode != 0:
            return {"success": False, "error": f"FFmpeg failed: {stderr.decode()[:200]}"}

        if not os.path.exists(final_path):
            return {"success": False, "error": "Fallback video file not created"}

        file_size_mb = os.path.getsize(final_path) / (1024 * 1024)

        # Upload to R2
        fallback_url = f"/api/generated/videos/{output_fn}"
        try:
            from services.cloudflare_r2_storage import get_r2_storage
            r2 = get_r2_storage()
            if r2.is_configured:
                ok, pub_url, key = await r2.upload_file_multipart(final_path, "video", job_id, output_fn)
                if ok and pub_url:
                    fallback_url = pub_url
        except Exception as e:
            logger.warning(f"[FALLBACK {job_id[:8]}] R2 upload failed: {e}")

        logger.info(f"[FALLBACK {job_id[:8]}] Lightweight MP4 ready: {file_size_mb:.1f}MB, {n} scenes")

        return {
            "success": True,
            "url": fallback_url,
            "file_size_mb": round(file_size_mb, 1),
            "scenes_included": n,
            "resolution": f"{W}x{H}",
            "type": "slideshow_fallback",
        }

    except Exception as e:
        logger.error(f"[FALLBACK {job_id[:8]}] Fallback MP4 failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def generate_story_pack_zip(job: dict) -> dict:
    """Generate a downloadable ZIP containing all generated assets:
    - Scene images
    - Voice/audio files
    - Story/scenes text
    - Thumbnail (first scene image)
    - manifest.json describing scene order
    """
    job_id = job["job_id"]
    scenes = job.get("scenes", [])
    scene_images = job.get("scene_images", {})
    scene_voices = job.get("scene_voices", {})
    title = job.get("title", "Story")
    story_text = job.get("story_text", "")

    temp_dir = tempfile.mkdtemp()

    try:
        sorted_scenes = sorted(scenes, key=lambda s: s.get("scene_number", 0))
        manifest = {
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_scenes": len(sorted_scenes),
            "scenes": [],
        }

        zip_path = os.path.join(temp_dir, f"story_pack_{job_id[:12]}.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add story text
            zf.writestr("story.txt", f"Title: {title}\n\n{story_text}")

            for scene in sorted_scenes:
                sn = str(scene.get("scene_number", 0))
                scene_entry = {
                    "scene_number": int(sn),
                    "title": scene.get("title", f"Scene {sn}"),
                    "narration": scene.get("narration_text", ""),
                    "visual_prompt": scene.get("visual_prompt", ""),
                    "image_file": None,
                    "audio_file": None,
                }

                # Add scene image
                img_info = scene_images.get(sn, {})
                img_data = None
                img_path = img_info.get("path", "")
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        img_data = f.read()
                elif img_info.get("url"):
                    img_data = await _download_to_bytes(img_info["url"])

                if img_data:
                    img_fn = f"images/scene_{sn}.png"
                    zf.writestr(img_fn, img_data)
                    scene_entry["image_file"] = img_fn

                # Add voice audio
                voice_info = scene_voices.get(sn, {})
                voice_data = None
                voice_path = voice_info.get("path", "")
                if voice_path and os.path.exists(voice_path):
                    with open(voice_path, "rb") as f:
                        voice_data = f.read()
                elif voice_info.get("url"):
                    voice_data = await _download_to_bytes(voice_info["url"])

                if voice_data:
                    voice_fn = f"audio/scene_{sn}.mp3"
                    zf.writestr(voice_fn, voice_data)
                    scene_entry["audio_file"] = voice_fn
                    scene_entry["duration_seconds"] = voice_info.get("duration", 0)

                # Add narration text file per scene
                narration = scene.get("narration_text", "")
                if narration:
                    zf.writestr(f"text/scene_{sn}.txt", f"Scene {sn}: {scene.get('title', '')}\n\n{narration}")

                manifest["scenes"].append(scene_entry)

            # Write manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        if not os.path.exists(zip_path):
            return {"success": False, "error": "ZIP file not created"}

        file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)

        # Upload ZIP to R2
        zip_fn = f"story_pack_{job_id[:12]}.zip"
        zip_url = None
        try:
            from services.cloudflare_r2_storage import get_r2_storage
            r2 = get_r2_storage()
            if r2.is_configured:
                ok, pub_url, key = await r2.upload_file(zip_path, "video", job_id, zip_fn)
                if ok and pub_url:
                    zip_url = pub_url
        except Exception as e:
            logger.warning(f"[STORYPACK {job_id[:8]}] R2 upload failed: {e}")

        # Fallback: copy to local static dir
        if not zip_url:
            local_path = str(STATIC_DIR / "videos" / zip_fn)
            shutil.copy2(zip_path, local_path)
            zip_url = f"/api/generated/videos/{zip_fn}"

        logger.info(f"[STORYPACK {job_id[:8]}] ZIP ready: {file_size_mb:.1f}MB, {len(manifest['scenes'])} scenes")

        return {
            "success": True,
            "url": zip_url,
            "file_size_mb": round(file_size_mb, 1),
            "scenes_included": len(manifest["scenes"]),
            "type": "story_pack_zip",
        }

    except Exception as e:
        logger.error(f"[STORYPACK {job_id[:8]}] ZIP generation failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def get_preview_data(job: dict) -> dict:
    """Build preview data: scene images in order, audio per scene, story text.
    All URLs are presigned for direct access."""
    from utils.r2_presign import presign_url

    job_id = job["job_id"]
    scenes = job.get("scenes", [])
    scene_images = job.get("scene_images", {})
    scene_voices = job.get("scene_voices", {})

    sorted_scenes = sorted(scenes, key=lambda s: s.get("scene_number", 0))

    preview_scenes = []
    for scene in sorted_scenes:
        sn = str(scene.get("scene_number", 0))
        img_info = scene_images.get(sn, {})
        voice_info = scene_voices.get(sn, {})

        img_url = img_info.get("url", "")
        voice_url = voice_info.get("url", "")

        # Presign R2 URLs
        if img_url and ("r2.dev" in img_url or "r2.cloudflarestorage" in img_url):
            try:
                img_url = presign_url(img_url, expiry=3600)
            except Exception:
                pass
        if voice_url and ("r2.dev" in voice_url or "r2.cloudflarestorage" in voice_url):
            try:
                voice_url = presign_url(voice_url, expiry=3600)
            except Exception:
                pass

        preview_scenes.append({
            "scene_number": int(sn),
            "title": scene.get("title", f"Scene {sn}"),
            "narration_text": scene.get("narration_text", ""),
            "visual_prompt": scene.get("visual_prompt", ""),
            "image_url": img_url if img_url else None,
            "audio_url": voice_url if voice_url else None,
            "duration": voice_info.get("duration", 0),
            "has_image": bool(img_url),
            "has_audio": bool(voice_url),
        })

    return {
        "job_id": job_id,
        "title": job.get("title", ""),
        "story_text": job.get("story_text", ""),
        "animation_style": job.get("animation_style", ""),
        "status": job.get("status", ""),
        "progress": job.get("progress", 0),
        "scenes": preview_scenes,
        "total_scenes": len(preview_scenes),
        "scenes_with_images": sum(1 for s in preview_scenes if s["has_image"]),
        "scenes_with_audio": sum(1 for s in preview_scenes if s["has_audio"]),
    }


async def get_asset_links(job: dict) -> dict:
    """Expose safe downloadable URLs for individual assets."""
    from utils.r2_presign import presign_url

    job_id = job["job_id"]
    scene_images = job.get("scene_images", {})
    scene_voices = job.get("scene_voices", {})

    def safe_presign(url):
        if not url:
            return None
        if "r2.dev" in url or "r2.cloudflarestorage" in url:
            try:
                return presign_url(url, expiry=3600)
            except Exception:
                return url
        return url

    image_links = {}
    for sn, info in scene_images.items():
        url = info.get("url", "")
        if url:
            image_links[sn] = safe_presign(url)

    audio_links = {}
    for sn, info in scene_voices.items():
        url = info.get("url", "")
        if url:
            audio_links[sn] = safe_presign(url)

    # Final video
    output_url = job.get("output_url", "")
    video_url = safe_presign(output_url) if output_url else None

    # Fallback outputs
    fallback = job.get("fallback_outputs", {})
    fallback_video_url = safe_presign(fallback.get("fallback_mp4", {}).get("url")) if fallback.get("fallback_mp4") else None
    story_pack_url = safe_presign(fallback.get("story_pack_zip", {}).get("url")) if fallback.get("story_pack_zip") else None

    return {
        "job_id": job_id,
        "images": image_links,
        "audio": audio_links,
        "final_video": video_url,
        "fallback_video": fallback_video_url,
        "story_pack_zip": story_pack_url,
    }


async def run_fallback_pipeline(job_id: str, failed_stage: str):
    """Run fallback outputs when the main pipeline fails at render or upload stage.
    Only runs if scenes/images/voices are already generated.
    """
    job = await db.pipeline_jobs.find_one({"job_id": job_id})
    if not job:
        return

    scenes = job.get("scenes", [])
    scene_images = job.get("scene_images", {})
    scene_voices = job.get("scene_voices", {})

    # Only run fallback if we have actual assets to work with
    if not scenes or not scene_images:
        logger.info(f"[FALLBACK {job_id[:8]}] No assets to create fallback from (stage: {failed_stage})")
        return

    has_images = len(scene_images) > 0
    has_voices = len(scene_voices) > 0

    logger.info(f"[FALLBACK {job_id[:8]}] Starting fallback pipeline. "
                f"Failed at: {failed_stage}, images: {len(scene_images)}, voices: {len(scene_voices)}")

    fallback_outputs = {}

    # 1. Try lightweight fallback MP4 (only if we have both images and voices)
    if has_images and has_voices:
        await db.pipeline_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"current_step": "Generating slideshow fallback video..."}}
        )
        fallback_mp4 = await generate_fallback_mp4(job)
        if fallback_mp4.get("success"):
            fallback_outputs["fallback_mp4"] = fallback_mp4
            logger.info(f"[FALLBACK {job_id[:8]}] Slideshow MP4 generated successfully")

    # 2. Generate Story Pack ZIP (works with any combination of assets)
    await db.pipeline_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"current_step": "Packaging Story Pack ZIP..."}}
    )
    story_pack = await generate_story_pack_zip(job)
    if story_pack.get("success"):
        fallback_outputs["story_pack_zip"] = story_pack
        logger.info(f"[FALLBACK {job_id[:8]}] Story Pack ZIP generated successfully")

    # 3. Build preview data
    preview = await get_preview_data(job)
    fallback_outputs["preview"] = preview

    # Determine the best available deliverable
    has_fallback_video = "fallback_mp4" in fallback_outputs
    has_zip = "story_pack_zip" in fallback_outputs

    deliverable_type = "none"
    if has_fallback_video:
        deliverable_type = "fallback_video"
    elif has_zip:
        deliverable_type = "story_pack"
    elif has_images:
        deliverable_type = "preview_only"

    # Update job with fallback outputs
    status = "PARTIAL" if fallback_outputs else "FAILED"
    step_msg = (
        "Slideshow video ready!" if has_fallback_video else
        "Story Pack ready for download!" if has_zip else
        "Scene preview available" if has_images else
        f"Failed at {failed_stage}"
    )

    await db.pipeline_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "fallback_outputs": fallback_outputs,
            "fallback_status": deliverable_type,
            "status": status,
            "current_step": step_msg,
        }}
    )

    # Broadcast fallback availability via WebSocket
    try:
        from routes.websocket_progress import manager
        await manager.broadcast_progress(
            job_id=job_id,
            user_id=job.get("user_id", ""),
            stage="fallback",
            progress=100,
            current_step=100,
            total_steps=100,
            message=step_msg,
            status="partial" if fallback_outputs else "failed",
        )
    except Exception:
        pass

    # Create notification for the user
    try:
        from services.notification_service import NotificationService
        notif_svc = NotificationService(db)
        await notif_svc.create_notification(
            user_id=job.get("user_id", ""),
            notification_type="generation_complete",
            title=f"Story assets ready: {job.get('title', 'Your Story')}",
            message=step_msg,
            job_id=job_id,
        )
    except Exception as e:
        logger.warning(f"[FALLBACK {job_id[:8]}] Notification failed: {e}")

    logger.info(f"[FALLBACK {job_id[:8]}] Fallback pipeline complete: {deliverable_type}")
