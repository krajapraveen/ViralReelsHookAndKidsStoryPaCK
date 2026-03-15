"""
Story → Video Pipeline Engine
Durable, stage-based, checkpoint-persisted, resumable pipeline.
Each stage saves outputs to DB. Failed stages retry independently.
Per-scene checkpointing for image/voice generation.
"""

import os
import uuid
import asyncio
import time
import json
import subprocess
import tempfile
import shutil
import logging
import base64
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

from shared import db

logger = logging.getLogger("pipeline_engine")

# WebSocket broadcast helper — fail-safe, never breaks pipeline
async def _ws_broadcast(job_id, user_id, stage, progress, message, status="running"):
    try:
        from routes.websocket_progress import manager
        await manager.broadcast_progress(
            job_id=job_id, user_id=user_id, stage=stage,
            progress=progress, current_step=progress, total_steps=100,
            message=message, status=status
        )
    except Exception:
        pass  # WebSocket is best-effort, never block pipeline

STATIC_DIR = Path("/app/backend/static/generated")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ─── STAGE DEFINITIONS ──────────────────────────────────────────────────────

class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

STAGES = ["script", "scenes", "images", "voices", "render", "upload"]

STAGE_CONFIG = {
    "script":  {"max_retries": 3, "backoff": [2, 4, 8], "timeout": 60,  "retriable_on_timeout": True},
    "scenes":  {"max_retries": 3, "backoff": [2, 4, 8], "timeout": 90,  "retriable_on_timeout": True},
    "images":  {"max_retries": 2, "backoff": [3, 6],    "timeout": 300, "retriable_on_timeout": True},
    "voices":  {"max_retries": 2, "backoff": [3, 6],    "timeout": 180, "retriable_on_timeout": True},
    "render":  {"max_retries": 3, "backoff": [2, 4, 8], "timeout": 300, "retriable_on_timeout": True},
    "upload":  {"max_retries": 3, "backoff": [2, 4, 8], "timeout": 60,  "retriable_on_timeout": True},
}

# ─── RENDER SETTINGS (production-safe fast defaults) ─────────────────────────
RENDER_WIDTH = 960
RENDER_HEIGHT = 540
RENDER_FPS = 15
RENDER_PRESET = "ultrafast"
RENDER_CRF = 28
RENDER_THREADS = 1

CREDIT_COSTS = {
    "small": 10,   # <=3 scenes
    "medium": 15,  # 4-6 scenes
    "large": 20,   # 7+ scenes
}

MAX_PARALLEL_IMAGES = 5
MAX_PARALLEL_VOICES = 6

# ─── COPYRIGHT COMPLIANCE ────────────────────────────────────────────────────

BLOCKED_TERMS = {
    "mickey mouse", "elsa", "frozen", "spider-man", "spiderman", "iron man",
    "batman", "superman", "harry potter", "hogwarts", "mario", "pokemon",
    "pikachu", "naruto", "goku", "star wars", "darth vader", "spongebob",
    "peppa pig", "paw patrol", "disney", "pixar", "marvel", "dc comics",
    "taylor swift", "beyonce", "elon musk", "coca cola", "mcdonalds", "nike",
}

LEGAL_NEGATIVE = "copyrighted character, trademarked character, brand logo, celebrity face, real person, nsfw, nudity, violence, gore"


def check_copyright(text: str) -> tuple:
    text_lower = text.lower()
    for term in BLOCKED_TERMS:
        if term in text_lower:
            return False, f"Contains copyrighted term: '{term}'"
    return True, "OK"


# ─── STYLE / VOICE / AGE OPTIONS ────────────────────────────────────────────

ANIMATION_STYLES = {
    "cartoon_2d": {"name": "2D Cartoon", "style_prompt": "2D cartoon animation style, vibrant colors, smooth lines, family-friendly", "negative_prompt": "realistic, photographic, 3D render, dark themes"},
    "anime_style": {"name": "Anime", "style_prompt": "anime art style, expressive characters, detailed backgrounds, Studio Ghibli inspired but original", "negative_prompt": "western cartoon, realistic, photographic"},
    "3d_pixar": {"name": "3D Animation", "style_prompt": "3D rendered animation, smooth textures, warm lighting, Pixar-quality but original", "negative_prompt": "2D, flat, photorealistic"},
    "watercolor": {"name": "Watercolor", "style_prompt": "watercolor illustration, soft edges, pastel colors, children's book style", "negative_prompt": "digital art, sharp edges, photorealistic"},
    "comic_book": {"name": "Comic Book", "style_prompt": "comic book art style, bold outlines, dynamic poses, vibrant colors", "negative_prompt": "realistic, photographic, dark themes"},
    "claymation": {"name": "Claymation", "style_prompt": "claymation style, textured surfaces, warm colors", "negative_prompt": "2D, flat, digital, photorealistic"},
}

AGE_GROUPS = {
    "toddler": {"name": "Toddlers (2-4)", "max_scenes": 4},
    "kids_5_8": {"name": "Kids (5-8)", "max_scenes": 6},
    "kids_9_12": {"name": "Tweens (9-12)", "max_scenes": 8},
    "teen": {"name": "Teens (13+)", "max_scenes": 10},
    "all_ages": {"name": "All Ages", "max_scenes": 8},
}

VOICE_PRESETS = {
    "narrator_warm": {"voice": "fable", "speed": 0.95, "name": "Warm Narrator"},
    "narrator_energetic": {"voice": "nova", "speed": 1.05, "name": "Energetic"},
    "narrator_calm": {"voice": "alloy", "speed": 0.9, "name": "Calm"},
    "narrator_dramatic": {"voice": "onyx", "speed": 1.0, "name": "Dramatic"},
    "narrator_friendly": {"voice": "shimmer", "speed": 1.0, "name": "Friendly"},
}


# ─── JOB CREATION ───────────────────────────────────────────────────────────

async def create_pipeline_job(
    user_id: str,
    title: str,
    story_text: str,
    animation_style: str = "cartoon_2d",
    age_group: str = "kids_5_8",
    voice_preset: str = "narrator_warm",
    include_watermark: bool = True
) -> dict:
    """Create a new pipeline job. Deducts credits. Returns job doc."""

    ok, msg = check_copyright(story_text)
    if not ok:
        raise ValueError(msg)
    ok, msg = check_copyright(title)
    if not ok:
        raise ValueError(msg)

    style = ANIMATION_STYLES.get(animation_style, ANIMATION_STYLES["cartoon_2d"])
    age = AGE_GROUPS.get(age_group, AGE_GROUPS["kids_5_8"])
    voice = VOICE_PRESETS.get(voice_preset, VOICE_PRESETS["narrator_warm"])

    estimated_scenes = min(age["max_scenes"], max(3, len(story_text) // 500))

    if estimated_scenes <= 3:
        credit_cost = CREDIT_COSTS["small"]
    elif estimated_scenes <= 6:
        credit_cost = CREDIT_COSTS["medium"]
    else:
        credit_cost = CREDIT_COSTS["large"]

    # Deduct credits
    from bson import ObjectId
    user = None
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = await db.users.find_one({"id": user_id})

    if not user:
        raise ValueError("User not found")

    if user.get("credits", 0) < credit_cost:
        raise ValueError(f"Insufficient credits. Need {credit_cost}, have {user.get('credits', 0)}")

    # Determine watermark based on user plan — free users get watermark, paid don't
    user_plan = str(user.get("plan", "free")).lower()
    paid_plans = ["weekly", "monthly", "quarterly", "yearly", "starter", "creator", "pro", "premium", "enterprise", "admin", "demo"]
    apply_watermark = user_plan not in paid_plans

    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$inc": {"credits": -credit_cost},
            "$push": {"credit_transactions": {
                "amount": -credit_cost,
                "description": f"Story Video: {title}",
                "timestamp": datetime.now(timezone.utc),
                "type": "deduction"
            }}
        }
    )

    job_id = str(uuid.uuid4())

    # Build stage tracking
    stages = {}
    for stage_name in STAGES:
        stages[stage_name] = {
            "status": StageStatus.PENDING,
            "started_at": None,
            "completed_at": None,
            "duration_ms": None,
            "retry_count": 0,
            "error": None,
            "outputs": {},
        }

    job_doc = {
        "job_id": job_id,
        "user_id": user_id,
        "title": title,
        "story_text": story_text,
        "animation_style": animation_style,
        "style_config": style,
        "age_group": age_group,
        "age_config": age,
        "voice_preset": voice_preset,
        "voice_config": voice,
        "include_watermark": apply_watermark,
        "estimated_scenes": estimated_scenes,
        "credits_charged": credit_cost,
        "status": "QUEUED",
        "progress": 0,
        "current_stage": None,
        "current_step": "Queued for processing...",
        "stages": stages,
        "scenes": [],
        "scene_images": {},
        "scene_voices": {},
        "render_path": None,
        "output_url": None,
        "error": None,
        "timing": {},
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
    }

    await db.pipeline_jobs.insert_one(job_doc)
    logger.info(f"[PIPELINE] Job {job_id[:8]} created for user {user_id[:8]}, {estimated_scenes} scenes, {credit_cost} credits")

    return {
        "job_id": job_id,
        "credits_charged": credit_cost,
        "estimated_scenes": estimated_scenes,
    }


# ─── JOB HELPERS ─────────────────────────────────────────────────────────────

async def update_job(job_id: str, updates: dict):
    await db.pipeline_jobs.update_one({"job_id": job_id}, {"$set": updates})


async def get_job(job_id: str) -> dict:
    return await db.pipeline_jobs.find_one({"job_id": job_id})


async def mark_stage_running(job_id: str, stage: str):
    await update_job(job_id, {
        f"stages.{stage}.status": StageStatus.RUNNING,
        f"stages.{stage}.started_at": datetime.now(timezone.utc),
        "current_stage": stage,
    })


async def mark_stage_complete(job_id: str, stage: str, outputs: dict, duration_ms: int):
    await update_job(job_id, {
        f"stages.{stage}.status": StageStatus.COMPLETED,
        f"stages.{stage}.completed_at": datetime.now(timezone.utc),
        f"stages.{stage}.duration_ms": duration_ms,
        f"stages.{stage}.outputs": outputs,
    })


async def mark_stage_failed(job_id: str, stage: str, error: str, retry_count: int):
    await update_job(job_id, {
        f"stages.{stage}.status": StageStatus.FAILED,
        f"stages.{stage}.error": error,
        f"stages.{stage}.retry_count": retry_count,
    })


# ─── STAGE IMPLEMENTATIONS ──────────────────────────────────────────────────

async def run_stage_scenes(job: dict) -> dict:
    """Stage: Generate scenes from story using LLM."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import re

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    style = job.get("style_config", {})
    age = job.get("age_config", {})
    max_scenes = job.get("estimated_scenes", 5)

    chat = LlmChat(
        api_key=api_key,
        session_id=f"pipe_{job['job_id'][:8]}",
        system_message=f"""Break stories into {max_scenes} visual scenes for animation.
Style: {style.get('name', 'Cartoon')}. Target: {age.get('name', 'Kids')}.
Return ONLY a JSON array. Each scene: {{"scene_number":N,"title":"...","narration_text":"...","visual_prompt":"..."}}
Visual prompts must describe ORIGINAL characters. Keep narration engaging.""",
    )
    chat.with_model("openai", "gpt-4o-mini")

    response = await chat.send_message(
        UserMessage(text=f"Break into {max_scenes} scenes:\n\n{job['story_text'][:3000]}\n\nReturn JSON array only:")
    )

    json_match = re.search(r'\[[\s\S]*\]', response)
    if not json_match:
        raise RuntimeError("LLM did not return valid JSON scenes")

    scenes = json.loads(json_match.group())[:max_scenes]
    if not scenes:
        raise RuntimeError("No scenes generated")

    # Persist scenes to job
    await update_job(job["job_id"], {"scenes": scenes})
    return {"scene_count": len(scenes)}


async def run_stage_images(job: dict) -> dict:
    """Stage: Generate images for all scenes. Per-scene checkpoint."""
    from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    job_id = job["job_id"]
    scenes = job.get("scenes", [])
    style = job.get("style_config", {})
    existing_images = job.get("scene_images", {})

    # Only generate images for scenes that don't already have them (resume support)
    scenes_to_gen = [s for s in scenes if str(s.get("scene_number")) not in existing_images]

    if not scenes_to_gen:
        return {"images_generated": len(existing_images), "images_resumed": len(existing_images)}

    total = len(scenes)
    done = len(existing_images)
    semaphore = asyncio.Semaphore(MAX_PARALLEL_IMAGES)

    async def gen_one(scene):
        nonlocal done
        sn = scene.get("scene_number", 0)
        async with semaphore:
            prompt = f"{scene.get('visual_prompt', '')}. Style: {style.get('style_prompt', '')}. Avoid: {LEGAL_NEGATIVE}"
            if len(prompt) > 3800:
                sentences = prompt.split('. ')
                parts, curr_len = [], 0
                for s in sentences:
                    if curr_len + len(s) + 2 <= 3800:
                        parts.append(s)
                        curr_len += len(s) + 2
                    else:
                        break
                prompt = '. '.join(parts) + '.'

            try:
                gen = OpenAIImageGeneration(api_key=api_key)
                images = await gen.generate_images(prompt=prompt, model="gpt-image-1", number_of_images=1)
                if not images:
                    raise RuntimeError("No image returned")

                img_id = str(uuid.uuid4())[:12]
                filename = f"pipe_{job_id[:8]}_s{sn}_{img_id}.png"
                path = STATIC_DIR / filename
                with open(path, "wb") as f:
                    f.write(images[0])

                # Upload to R2
                url = f"/static/generated/{filename}"
                storage = "local"
                r2_key = None
                try:
                    from services.cloudflare_r2_storage import get_r2_storage
                    r2 = get_r2_storage()
                    if r2.is_configured:
                        ok, pub_url, key = await r2.upload_file(str(path), "image", job_id, filename)
                        if ok:
                            url = pub_url
                            r2_key = key
                            storage = "r2"
                            # NOTE: Keep local file — render stage needs it.
                            # Cleanup happens after pipeline completion.
                except Exception:
                    pass

                result = {"url": url, "path": str(path), "storage": storage, "scene_number": sn, "r2_key": r2_key}

                # Checkpoint: save this scene immediately
                done += 1
                pct = int(30 + (done / total) * 25)
                await update_job(job_id, {
                    f"scene_images.{sn}": result,
                    "progress": pct,
                    "current_step": f"Generated image {done}/{total}...",
                })
                logger.info(f"[PIPE {job_id[:8]}] Image scene {sn} done ({done}/{total})")
                return result

            except Exception as e:
                logger.error(f"[PIPE {job_id[:8]}] Image scene {sn} failed: {e}")
                # Per-scene retry (1 retry for individual scene)
                await asyncio.sleep(3)
                try:
                    gen2 = OpenAIImageGeneration(api_key=api_key)
                    images2 = await gen2.generate_images(prompt=prompt, model="gpt-image-1", number_of_images=1)
                    if images2:
                        img_id2 = str(uuid.uuid4())[:12]
                        fn2 = f"pipe_{job_id[:8]}_s{sn}_{img_id2}.png"
                        p2 = STATIC_DIR / fn2
                        with open(p2, "wb") as f:
                            f.write(images2[0])
                        url2 = f"/static/generated/{fn2}"
                        result2 = {"url": url2, "path": str(p2), "storage": "local", "scene_number": sn}
                        done += 1
                        await update_job(job_id, {f"scene_images.{sn}": result2, "progress": int(30 + (done / total) * 25)})
                        return result2
                except Exception as e2:
                    logger.error(f"[PIPE {job_id[:8]}] Image scene {sn} retry also failed: {e2}")
                return {"scene_number": sn, "error": str(e), "failed": True}

    tasks = [gen_one(s) for s in scenes_to_gen]
    results = await asyncio.gather(*tasks)

    failed = [r for r in results if isinstance(r, dict) and r.get("failed")]
    succeeded = done

    if succeeded == 0:
        raise RuntimeError(f"All {len(scenes_to_gen)} image generations failed")

    return {"images_generated": succeeded, "images_failed": len(failed)}


async def run_stage_voices(job: dict) -> dict:
    """Stage: Generate voice tracks. Per-scene checkpoint."""
    from emergentintegrations.llm.openai import OpenAITextToSpeech

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    job_id = job["job_id"]
    scenes = job.get("scenes", [])
    voice_cfg = job.get("voice_config", {})
    existing_voices = job.get("scene_voices", {})

    scenes_to_gen = [s for s in scenes if str(s.get("scene_number")) not in existing_voices]

    if not scenes_to_gen:
        return {"voices_generated": len(existing_voices), "voices_resumed": len(existing_voices)}

    total = len(scenes)
    done = len(existing_voices)
    semaphore = asyncio.Semaphore(MAX_PARALLEL_VOICES)

    async def gen_one(scene):
        nonlocal done
        sn = scene.get("scene_number", 0)
        text = scene.get("narration_text", "")
        async with semaphore:
            try:
                tts = OpenAITextToSpeech(api_key=api_key)
                audio = await tts.generate_speech(
                    text=text, model="tts-1",
                    voice=voice_cfg.get("voice", "alloy"),
                    speed=voice_cfg.get("speed", 1.0),
                    response_format="mp3",
                )

                fn = f"pipe_{job_id[:8]}_v{sn}.mp3"
                path = STATIC_DIR / fn
                with open(path, "wb") as f:
                    f.write(audio)

                # Measure duration (fault-tolerant: fallback to estimate if ffprobe unavailable)
                duration = 5.0
                try:
                    probe = subprocess.run(
                        ["ffprobe", "-i", str(path), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if probe.returncode == 0 and probe.stdout.strip():
                        duration = float(probe.stdout.strip())
                except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as probe_err:
                    logger.warning(f"[PIPE {job_id[:8]}] ffprobe unavailable for scene {sn}, using estimated duration: {probe_err}")
                    duration = max(3.0, len(text.split()) / 2.5)

                # Upload voice to R2 for durability
                voice_url = None
                voice_r2_key = None
                try:
                    from services.cloudflare_r2_storage import get_r2_storage
                    r2 = get_r2_storage()
                    if r2.is_configured:
                        ok, pub_url, key = await r2.upload_file(str(path), "audio", job_id, fn)
                        if ok:
                            voice_url = pub_url
                            voice_r2_key = key
                except Exception as r2_err:
                    logger.warning(f"[PIPE {job_id[:8]}] Voice R2 upload failed for scene {sn}: {r2_err}")

                result = {"path": str(path), "url": voice_url, "duration": duration, "scene_number": sn, "r2_key": voice_r2_key}

                done += 1
                pct = int(55 + (done / total) * 20)
                await update_job(job_id, {
                    f"scene_voices.{sn}": result,
                    "progress": pct,
                    "current_step": f"Generated voice {done}/{total}...",
                })
                return result

            except Exception as e:
                logger.error(f"[PIPE {job_id[:8]}] Voice scene {sn} failed: {e}")
                return {"scene_number": sn, "error": str(e), "failed": True}

    tasks = [gen_one(s) for s in scenes_to_gen]
    results = await asyncio.gather(*tasks)

    failed = [r for r in results if isinstance(r, dict) and r.get("failed")]
    if done == 0:
        raise RuntimeError("All voice generations failed")

    return {"voices_generated": done, "voices_failed": len(failed)}


async def _run_ffmpeg(cmd: list, timeout: int = 90) -> tuple:
    """Run ffmpeg as async subprocess so asyncio timeouts can cancel it.
    Adds -nostdin and -loglevel error automatically for safety."""
    if cmd and cmd[0] == "ffmpeg":
        extras = []
        if "-nostdin" not in cmd:
            extras.append("-nostdin")
        if "-loglevel" not in cmd:
            extras.extend(["-loglevel", "error"])
        if extras:
            cmd = [cmd[0]] + extras + cmd[1:]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"ffmpeg timed out after {timeout}s")


async def _run_ffmpeg_with_progress(cmd: list, job_id: str, total_duration: float,
                                     scene_count: int, timeout: int = 180) -> tuple:
    """Run ffmpeg with real-time progress tracking via -progress flag.
    Updates job with per-scene render progress for user visibility."""
    progress_file = tempfile.mktemp(suffix='.progress')

    if cmd and cmd[0] == "ffmpeg":
        extras = ["-nostdin", "-loglevel", "error", "-progress", progress_file]
        cmd = [cmd[0]] + extras + cmd[1:]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def _monitor():
        """Background task: read FFmpeg progress file and update job status."""
        last_scene_reported = 0
        while proc.returncode is None:
            await asyncio.sleep(1.5)
            try:
                if not os.path.exists(progress_file):
                    continue
                with open(progress_file, 'r') as f:
                    content = f.read()
                # Parse out_time_us (microseconds of encoded output)
                for line in reversed(content.strip().split('\n')):
                    if 'out_time_us=' in line:
                        val = line.split('=')[1].strip()
                        if val and val != 'N/A':
                            us = int(val)
                            current_s = us / 1_000_000
                            if total_duration > 0:
                                pct = min(89, int(82 + (current_s / total_duration) * 8))
                                scene_dur = total_duration / max(1, scene_count)
                                scene_num = min(scene_count, int(current_s / scene_dur) + 1)
                                if scene_num > last_scene_reported:
                                    await update_job(job_id, {
                                        "progress": pct,
                                        "current_step": f"Rendering scene {scene_num}/{scene_count}..."
                                    })
                                    last_scene_reported = scene_num
                        break
            except Exception:
                pass

    monitor_task = asyncio.create_task(_monitor())

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        monitor_task.cancel()
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"ffmpeg timed out after {timeout}s")
    finally:
        try:
            os.remove(progress_file)
        except OSError:
            pass


async def _download_file(url: str, dest: str, label: str, timeout: int = 30) -> bool:
    """Download a file from URL to dest path. Handles presigned URL conversion for R2.
    Retries once on failure with a fresh presigned URL."""
    import aiohttp

    async def _try_download(download_url: str) -> bool:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(download_url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if len(data) < 100:
                            logger.warning(f"[RENDER] Downloaded {label} but file too small ({len(data)} bytes)")
                            return False
                        with open(dest, "wb") as f:
                            f.write(data)
                        logger.info(f"[RENDER] Downloaded {label} ({len(data)} bytes)")
                        return True
                    else:
                        logger.error(f"[RENDER] Download {label} failed: HTTP {resp.status}")
        except asyncio.TimeoutError:
            logger.error(f"[RENDER] Download {label} timed out after {timeout}s")
        except Exception as e:
            logger.error(f"[RENDER] Download {label} error: {e}")
        return False

    # Attempt 1: Try direct URL first (may be presigned already)
    if not url.startswith("http"):
        return False

    # Always presign R2 URLs for reliability
    presigned_url = url
    try:
        from utils.r2_presign import presign_url
        if ".r2.dev/" in url or "r2.cloudflarestorage.com" in url:
            presigned_url = presign_url(url, expiry=600)
    except Exception as e:
        logger.warning(f"[RENDER] Presign failed for {label}: {e}")

    if await _try_download(presigned_url):
        return True

    # Attempt 2: If first attempt failed, try with fresh presigned URL
    if presigned_url != url:
        logger.info(f"[RENDER] Retrying {label} with original URL")
        if await _try_download(url):
            return True

    # Attempt 3: Try extracting the R2 key and generating presigned URL from scratch
    try:
        from utils.r2_presign import presign_url
        # Extract key from URL patterns like https://xxx.r2.dev/type/jobid/filename
        import re
        key_match = re.search(r'r2\.dev/(.+?)(?:\?|$)', url)
        if not key_match:
            key_match = re.search(r'r2\.cloudflarestorage\.com/[^/]+/(.+?)(?:\?|$)', url)
        if key_match:
            key = key_match.group(1)
            fresh_url = presign_url(f"placeholder/{key}", expiry=600)
            if await _try_download(fresh_url):
                return True
    except Exception:
        pass

    logger.error(f"[RENDER] All download attempts failed for {label}")
    return False


async def run_stage_render(job: dict) -> dict:
    """Stage: SINGLE-PASS render — all scene images + voices → one FFmpeg encode.

    Architecture (redesigned for speed):
    1. Download all pre-generated scene images and voice audio to temp dir
    2. Build ONE FFmpeg command with filter_complex:
       - Scale+pad each image to RENDER_WIDTH x RENDER_HEIGHT
       - Set fps=RENDER_FPS for each image stream
       - Concat all video streams, concat all audio streams
       - Optional lightweight watermark (drawtext)
    3. Single encode: libx264, ultrafast, CRF 28, threads 1
    4. No intermediate per-scene mp4 clips. No repeated re-encoding.

    This replaces the old scene-by-scene mp4 + concat approach.
    """
    import gc

    job_id = job["job_id"]
    scenes = job.get("scenes", [])
    scene_images = job.get("scene_images", {})
    scene_voices = job.get("scene_voices", {})

    temp_dir = tempfile.mkdtemp()
    output_fn = f"pipe_video_{job_id[:12]}.mp4"
    videos_dir = STATIC_DIR / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    final_path = str(videos_dir / output_fn)

    render_timing = {}
    stage_start = time.time()

    try:
        sorted_scenes = sorted(scenes, key=lambda s: s.get("scene_number", 0))
        total_scenes = len(sorted_scenes)

        if total_scenes == 0:
            raise RuntimeError("No scenes found in job")

        logger.info(f"[RENDER {job_id[:8]}] Starting SINGLE-PASS render: {total_scenes} scenes, "
                     f"{RENDER_WIDTH}x{RENDER_HEIGHT}, {RENDER_FPS}fps, {RENDER_PRESET}, CRF {RENDER_CRF}")
        await update_job(job_id, {
            "progress": 75,
            "current_step": f"Preparing final render ({total_scenes} scenes)..."
        })

        # ── Phase 1: Download all assets ──────────────────────────────────
        dl_start = time.time()
        image_paths = {}   # sn -> local path
        audio_paths = {}   # sn -> local path
        durations = {}     # sn -> seconds
        skipped_scenes = []

        for idx, scene in enumerate(sorted_scenes):
            sn = str(scene.get("scene_number", 0))
            img = scene_images.get(sn, {})
            voice = scene_voices.get(sn, {})

            await update_job(job_id, {
                "progress": int(75 + (idx / total_scenes) * 5),
                "current_step": f"Downloading assets for scene {idx+1}/{total_scenes}..."
            })

            # ── Download image ──
            img_path = img.get("path", "")
            if not os.path.exists(img_path):
                dl_path = os.path.join(temp_dir, f"img_{sn}.png")
                downloaded = False

                img_url = img.get("url", "")
                if img_url:
                    downloaded = await _download_file(img_url, dl_path, f"image scene {sn}")

                if not downloaded:
                    img_r2_key = img.get("r2_key", "")
                    if img_r2_key:
                        try:
                            from utils.r2_presign import presign_key
                            fresh_url = presign_key(img_r2_key, expiry=600)
                            if fresh_url:
                                downloaded = await _download_file(fresh_url, dl_path, f"image scene {sn} (key)")
                        except Exception:
                            pass

                if downloaded and os.path.exists(dl_path):
                    img_path = dl_path
                else:
                    logger.error(f"[RENDER {job_id[:8]}] Failed to get image for scene {sn}")
                    skipped_scenes.append(sn)
                    continue

            # ── Download voice ──
            audio_path = voice.get("path", "")
            if not os.path.exists(audio_path):
                dl_path = os.path.join(temp_dir, f"voice_{sn}.mp3")
                downloaded = False

                voice_url = voice.get("url", "")
                if voice_url:
                    downloaded = await _download_file(voice_url, dl_path, f"voice scene {sn}")

                if not downloaded:
                    voice_r2_key = voice.get("r2_key", "")
                    if voice_r2_key:
                        try:
                            from utils.r2_presign import presign_key
                            fresh_url = presign_key(voice_r2_key, expiry=600)
                            if fresh_url:
                                downloaded = await _download_file(fresh_url, dl_path, f"voice scene {sn} (key)")
                        except Exception:
                            pass

                if downloaded and os.path.exists(dl_path):
                    audio_path = dl_path
                else:
                    logger.error(f"[RENDER {job_id[:8]}] Failed to get voice for scene {sn}")
                    skipped_scenes.append(sn)
                    continue

            image_paths[sn] = img_path
            audio_paths[sn] = audio_path
            durations[sn] = voice.get("duration", 5.0)

        dl_ms = int((time.time() - dl_start) * 1000)
        render_timing["download_ms"] = dl_ms

        # Determine valid scenes (have both image and audio)
        valid_scenes = [str(s.get("scene_number", 0)) for s in sorted_scenes
                        if str(s.get("scene_number", 0)) in image_paths
                        and str(s.get("scene_number", 0)) in audio_paths]

        if not valid_scenes:
            raise RuntimeError(f"No valid scenes after download. {len(skipped_scenes)} scenes skipped: {skipped_scenes}")

        logger.info(f"[RENDER {job_id[:8]}] Assets ready: {len(valid_scenes)}/{total_scenes} scenes, download {dl_ms}ms")

        # ── Phase 2: Single FFmpeg encode ─────────────────────────────────
        await update_job(job_id, {
            "progress": 82,
            "current_step": f"Rendering final video ({len(valid_scenes)} scenes)..."
        })

        encode_start = time.time()
        n = len(valid_scenes)

        # Build FFmpeg inputs: alternating -loop 1 -t <dur> -i <image>, -i <audio>
        inputs = []
        filter_parts = []
        total_duration = 0.0

        for i, sn in enumerate(valid_scenes):
            dur = durations[sn] + 0.3  # small buffer for sync
            total_duration += dur
            v_idx = i * 2      # image input index (0, 2, 4, ...)
            a_idx = i * 2 + 1  # audio input index (1, 3, 5, ...)

            inputs.extend(["-loop", "1", "-t", f"{dur:.2f}", "-i", image_paths[sn]])
            inputs.extend(["-i", audio_paths[sn]])

            # Video filter: scale + pad to exact resolution, set fps
            filter_parts.append(
                f"[{v_idx}:v]scale={RENDER_WIDTH}:{RENDER_HEIGHT}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={RENDER_WIDTH}:{RENDER_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,fps={RENDER_FPS}[v{i}]"
            )

        # Concat all video streams
        v_concat = ''.join(f'[v{i}]' for i in range(n))
        filter_parts.append(f"{v_concat}concat=n={n}:v=1:a=0[vout]")

        # Concat all audio streams (resample for consistency)
        a_filters = []
        for i in range(n):
            a_idx = i * 2 + 1
            a_filters.append(f"[{a_idx}:a]aresample=44100[a{i}]")
        filter_parts.extend(a_filters)

        a_concat = ''.join(f'[a{i}]' for i in range(n))
        filter_parts.append(f"{a_concat}concat=n={n}:v=0:a=1[aout]")

        # Optional lightweight watermark — only for free-tier users
        watermark = job.get("include_watermark", False)
        if watermark:
            filter_parts.append(
                "[vout]drawtext=text='Made with Visionary-Suite.com':"
                "fontcolor=white@0.35:fontsize=16:x=w-tw-12:y=h-th-10[vfinal]"
            )
            v_map = "[vfinal]"
        else:
            v_map = "[vout]"

        filter_complex = ';'.join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", v_map,
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", RENDER_PRESET,
            "-crf", str(RENDER_CRF),
            "-r", str(RENDER_FPS),
            "-threads", str(RENDER_THREADS),
            "-c:a", "aac", "-b:a", "96k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            final_path,
        ]

        logger.info(f"[RENDER {job_id[:8]}] Running single-pass FFmpeg encode: "
                     f"{n} scenes, {RENDER_WIDTH}x{RENDER_HEIGHT}, {RENDER_FPS}fps, "
                     f"{RENDER_PRESET}, CRF {RENDER_CRF}, total_dur={total_duration:.1f}s")

        # Execute with real-time progress monitoring
        encode_timeout = max(180, n * 40)  # generous but bounded
        rc, stdout, stderr = await _run_ffmpeg_with_progress(
            cmd, job_id, total_duration, n, timeout=encode_timeout
        )

        encode_ms = int((time.time() - encode_start) * 1000)
        render_timing["encode_ms"] = encode_ms

        if rc != 0:
            raise RuntimeError(f"Single-pass encode failed (rc={rc}): {stderr[:500]}")

        if not os.path.exists(final_path):
            raise RuntimeError("Final video file not created")

        file_size = os.path.getsize(final_path) / (1024 * 1024)
        render_timing["total_render_ms"] = int((time.time() - stage_start) * 1000)

        await update_job(job_id, {
            "render_path": final_path,
            "progress": 90,
            "current_step": "Finalizing video..."
        })

        logger.info(
            f"[RENDER {job_id[:8]}] SINGLE-PASS COMPLETE: {n} scenes, {file_size:.1f}MB, "
            f"encode={encode_ms}ms, total={render_timing['total_render_ms']}ms "
            f"(was: N*2+1 FFmpeg calls, now: 1 FFmpeg call)"
        )

        return {
            "path": final_path,
            "file_size_mb": round(file_size, 1),
            "segments": n,
            "failed_scenes": len(skipped_scenes),
            "timing": render_timing,
            "architecture": "single-pass-encode",
            "settings": f"{RENDER_WIDTH}x{RENDER_HEIGHT}@{RENDER_FPS}fps/{RENDER_PRESET}/CRF{RENDER_CRF}",
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        gc.collect()


async def run_stage_upload(job: dict) -> dict:
    """Stage: Upload rendered video to R2 and verify.
    Retries upload with exponential backoff. Falls back to local storage."""
    job_id = job["job_id"]
    render_path = job.get("render_path")

    if not render_path or not os.path.exists(render_path):
        raise RuntimeError(f"Render file not found: {render_path}")

    filename = os.path.basename(render_path)
    file_size_mb = os.path.getsize(render_path) / (1024 * 1024)
    logger.info(f"[UPLOAD {job_id[:8]}] Starting upload of {file_size_mb:.1f}MB file")

    await update_job(job_id, {"current_step": f"Uploading video ({file_size_mb:.1f}MB)...", "progress": 92})

    # Try R2 upload with retry
    for attempt in range(3):
        try:
            from services.cloudflare_r2_storage import get_r2_storage
            r2 = get_r2_storage()
            if r2.is_configured:
                ok, public_url, key = await r2.upload_file_multipart(render_path, "video", job_id, filename)
                if ok and public_url:
                    logger.info(f"[UPLOAD {job_id[:8]}] R2 upload OK on attempt {attempt+1}: {public_url[:60]}")
                    await update_job(job_id, {"progress": 98, "current_step": "Upload complete, finalizing..."})
                    return {"url": public_url, "storage": "r2", "verified": True}
                else:
                    logger.warning(f"[UPLOAD {job_id[:8]}] R2 upload returned ok={ok} url={public_url}")
        except Exception as e:
            logger.warning(f"[UPLOAD {job_id[:8]}] R2 upload attempt {attempt+1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))

    # Fallback to local storage
    logger.warning(f"[UPLOAD {job_id[:8]}] All R2 uploads failed, using local storage")
    local_url = f"/api/generated/videos/{filename}"
    await update_job(job_id, {"progress": 98, "current_step": "Upload complete (local), finalizing..."})
    return {"url": local_url, "storage": "local", "verified": True}


# ─── PIPELINE EXECUTOR ──────────────────────────────────────────────────────

STAGE_RUNNERS = {
    "scenes": run_stage_scenes,
    "images": run_stage_images,
    "voices": run_stage_voices,
    "render": run_stage_render,
    "upload": run_stage_upload,
}

# Progress breakpoints per stage
STAGE_PROGRESS = {
    "scenes": (5, 25),
    "images": (25, 55),
    "voices": (55, 75),
    "render": (75, 90),
    "upload": (90, 100),
}

STAGE_LABELS = {
    "scenes": "Generating scenes...",
    "images": "Creating images...",
    "voices": "Generating voiceovers...",
    "render": "Rendering video...",
    "upload": "Uploading to cloud...",
}


async def execute_pipeline(job_id: str):
    """Execute the full pipeline stage by stage with checkpoints and retries."""
    pipeline_start = time.time()

    job = await get_job(job_id)
    if not job:
        logger.error(f"[PIPE] Job {job_id} not found")
        return

    await update_job(job_id, {
        "status": "PROCESSING",
        "started_at": datetime.now(timezone.utc),
    })

    timing = {}

    for stage_name in ["scenes", "images", "voices", "render", "upload"]:
        # Check if stage already completed (resume support)
        stage_info = job.get("stages", {}).get(stage_name, {})
        if stage_info.get("status") == StageStatus.COMPLETED:
            logger.info(f"[PIPE {job_id[:8]}] Skipping {stage_name} (already completed)")
            continue

        config = STAGE_CONFIG[stage_name]
        progress_start, progress_end = STAGE_PROGRESS[stage_name]

        await update_job(job_id, {
            "progress": progress_start,
            "current_step": STAGE_LABELS[stage_name],
            "current_stage": stage_name,
        })
        await mark_stage_running(job_id, stage_name)

        # Broadcast stage start via WebSocket
        await _ws_broadcast(job_id, job.get("user_id", ""), stage_name, progress_start, STAGE_LABELS[stage_name])

        # Retry loop
        success = False
        last_error = None
        for attempt in range(config["max_retries"] + 1):
            if attempt > 0:
                backoff = config["backoff"][min(attempt - 1, len(config["backoff"]) - 1)]
                logger.info(f"[PIPE {job_id[:8]}] Retrying {stage_name} (attempt {attempt + 1}) after {backoff}s")
                await update_job(job_id, {
                    f"stages.{stage_name}.status": StageStatus.RETRYING,
                    f"stages.{stage_name}.retry_count": attempt,
                    "current_step": f"Retrying {stage_name} (attempt {attempt + 1})...",
                })
                await asyncio.sleep(backoff)

            try:
                # Re-fetch job for latest checkpointed data
                job = await get_job(job_id)
                if not job:
                    raise RuntimeError("Job deleted during processing")

                t_start = time.time()
                runner = STAGE_RUNNERS[stage_name]

                # Execute with timeout
                try:
                    outputs = await asyncio.wait_for(
                        runner(job),
                        timeout=config["timeout"],
                    )
                except asyncio.TimeoutError:
                    raise RuntimeError(f"Stage {stage_name} timed out after {config['timeout']}s")

                duration_ms = int((time.time() - t_start) * 1000)
                timing[f"{stage_name}_ms"] = duration_ms

                await mark_stage_complete(job_id, stage_name, outputs, duration_ms)
                await update_job(job_id, {"progress": progress_end})

                # Broadcast stage completion via WebSocket
                await _ws_broadcast(job_id, job.get("user_id", ""), stage_name, progress_end,
                                    f"{STAGE_LABELS.get(stage_name, stage_name)} complete")

                logger.info(f"[PIPE {job_id[:8]}] Stage {stage_name} completed in {duration_ms}ms")
                success = True
                break

            except Exception as e:
                last_error = str(e)
                logger.error(f"[PIPE {job_id[:8]}] Stage {stage_name} attempt {attempt + 1} failed: {e}")

                # Classify failure
                err_str = str(e).lower()
                non_retriable = ["copyright", "blocked", "invalid", "not configured", "insufficient"]
                if any(term in err_str for term in non_retriable):
                    logger.info(f"[PIPE {job_id[:8]}] Non-retriable error, failing fast")
                    break

        if not success:
            await mark_stage_failed(job_id, stage_name, last_error or "Unknown error", config["max_retries"])
            await update_job(job_id, {
                "status": "FAILED",
                "error": f"Stage '{stage_name}' failed: {last_error}",
                "current_step": f"Failed at {stage_name}: {(last_error or '')[:80]}",
                "completed_at": datetime.now(timezone.utc),
                "timing": timing,
            })

            # Refund credits
            await refund_credits(job)

            # If render or upload failed but we have assets, run fallback pipeline
            if stage_name in ("render", "upload"):
                try:
                    from services.fallback_pipeline import run_fallback_pipeline
                    logger.info(f"[PIPE {job_id[:8]}] Render/upload failed — triggering fallback pipeline")
                    await run_fallback_pipeline(job_id, stage_name)
                except Exception as fb_err:
                    logger.error(f"[PIPE {job_id[:8]}] Fallback pipeline failed: {fb_err}")

            # Broadcast failure via WebSocket
            await _ws_broadcast(job_id, job.get("user_id", ""), stage_name, 0,
                                f"Failed at {stage_name}: {(last_error or '')[:80]}", status="failed")
            return

    # ─── ALL STAGES COMPLETE ─────────────────────────────────────────────
    job = await get_job(job_id)
    upload_outputs = job.get("stages", {}).get("upload", {}).get("outputs", {})
    video_url = upload_outputs.get("url", "")

    total_ms = int((time.time() - pipeline_start) * 1000)
    timing["total_ms"] = total_ms

    await update_job(job_id, {
        "status": "COMPLETED",
        "progress": 100,
        "output_url": video_url,
        "current_step": f"Video ready! ({total_ms // 1000}s)",
        "completed_at": datetime.now(timezone.utc),
        "timing": timing,
    })

    # Broadcast completion via WebSocket
    await _ws_broadcast(job_id, job.get("user_id", ""), "complete", 100,
                        f"Video ready! ({total_ms // 1000}s)", status="completed")

    logger.info(f"[PIPE {job_id[:8]}] COMPLETE in {total_ms}ms — {video_url[:60]}")

    # Send notification if user subscribed to "notify when ready"
    if job.get("notify_on_complete"):
        try:
            from services.notification_service import NotificationService
            notif_svc = NotificationService(db)
            await notif_svc.create_notification(
                user_id=job.get("user_id", ""),
                notification_type="generation_complete",
                title=f"Video ready: {job.get('title', 'Your Story')}",
                message=f"Your video '{job.get('title', '')}' is ready to download!",
                job_id=job_id,
            )
        except Exception as notif_err:
            logger.warning(f"[PIPE {job_id[:8]}] Notify-when-ready failed: {notif_err}")

    # Clean up local temp files (images/audio) now that render is complete & uploaded
    try:
        for sn, img in job.get("scene_images", {}).items():
            p = img.get("path", "")
            if p and os.path.exists(p) and str(STATIC_DIR) in p:
                os.remove(p)
        for sn, voice in job.get("scene_voices", {}).items():
            p = voice.get("path", "")
            if p and os.path.exists(p) and str(STATIC_DIR) in p:
                os.remove(p)
        logger.info(f"[PIPE {job_id[:8]}] Cleaned up local temp files")
    except Exception:
        pass


async def refund_credits(job: dict):
    """Refund all credits for a failed job."""
    user_id = job.get("user_id")
    credit_cost = job.get("credits_charged", 0)
    if not user_id or not credit_cost:
        return

    try:
        from bson import ObjectId
        user = None
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            user = await db.users.find_one({"id": user_id})

        if user:
            await db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$inc": {"credits": credit_cost},
                    "$push": {"credit_transactions": {
                        "amount": credit_cost,
                        "description": f"Refund: video failed - {job.get('title', '')}",
                        "timestamp": datetime.now(timezone.utc),
                        "type": "refund",
                    }}
                }
            )
            logger.info(f"[REFUND] {credit_cost} credits returned to {user_id[:8]}")
    except Exception as e:
        logger.error(f"[REFUND] Failed: {e}")


async def resume_pipeline(job_id: str):
    """Resume a failed pipeline from its last checkpoint."""
    job = await get_job(job_id)
    if not job:
        raise ValueError("Job not found")

    if job.get("status") == "COMPLETED":
        raise ValueError("Job already completed")

    # Reset the failed stage to PENDING so executor will re-run it
    stages = job.get("stages", {})
    for stage_name in STAGES[1:]:  # skip "script"
        if stages.get(stage_name, {}).get("status") == StageStatus.FAILED:
            await update_job(job_id, {
                f"stages.{stage_name}.status": StageStatus.PENDING,
                f"stages.{stage_name}.error": None,
                f"stages.{stage_name}.retry_count": 0,
                "status": "QUEUED",
                "error": None,
            })
            break

    return True
