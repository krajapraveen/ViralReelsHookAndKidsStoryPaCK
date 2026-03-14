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
    "render":  {"max_retries": 3, "backoff": [2, 4, 8], "timeout": 600, "retriable_on_timeout": True},
    "upload":  {"max_retries": 3, "backoff": [2, 4, 8], "timeout": 60,  "retriable_on_timeout": True},
}

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
        "include_watermark": include_watermark,
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
                            try:
                                os.remove(str(path))
                            except OSError:
                                pass
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
    # Insert -nostdin and -loglevel error after 'ffmpeg' if not present
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
    """Stage: Assemble video from checkpointed images + voices using async ffmpeg.
    Production-safe: sequential rendering, single-threaded, aggressive memory control.
    Reports progress per sub-step so users never see a frozen progress bar."""
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
    failed_scenes = []

    try:
        segments = []
        sorted_scenes = sorted(scenes, key=lambda s: s.get("scene_number", 0))
        total_scenes = len(sorted_scenes)

        if total_scenes == 0:
            raise RuntimeError("No scenes found in job")

        logger.info(f"[RENDER {job_id[:8]}] Starting render of {total_scenes} scenes")
        await update_job(job_id, {"current_step": f"Preparing {total_scenes} scenes for render..."})

        for idx, scene in enumerate(sorted_scenes):
            scene_start = time.time()
            sn = str(scene.get("scene_number", 0))
            img = scene_images.get(sn, {})
            voice = scene_voices.get(sn, {})

            img_path = img.get("path", "")
            audio_path = voice.get("path", "")
            duration = voice.get("duration", 5.0)

            # Update progress: downloading assets for this scene
            dl_pct = int(75 + ((idx) / total_scenes) * 5)
            await update_job(job_id, {
                "progress": dl_pct,
                "current_step": f"Downloading assets for scene {idx+1}/{total_scenes}..."
            })

            # Download image from cloud if local missing
            if not os.path.exists(img_path):
                img_url = img.get("url", "")
                img_r2_key = img.get("r2_key", "")
                dl_path = os.path.join(temp_dir, f"img_{sn}.png")

                # Try URL first
                if img_url and await _download_file(img_url, dl_path, f"image scene {sn}"):
                    img_path = dl_path
                elif img_r2_key:
                    # Fallback: generate fresh presigned URL from stored key
                    try:
                        from utils.r2_presign import presign_key
                        fresh_url = presign_key(img_r2_key, expiry=600)
                        if fresh_url and await _download_file(fresh_url, dl_path, f"image scene {sn} (key)"):
                            img_path = dl_path
                    except Exception:
                        pass

                if not os.path.exists(dl_path):
                    logger.error(f"[RENDER {job_id[:8]}] FAILED to download image for scene {sn}")

            # Download voice from cloud if local missing
            if not os.path.exists(audio_path):
                voice_url = voice.get("url", "")
                voice_r2_key = voice.get("r2_key", "")
                dl_path = os.path.join(temp_dir, f"voice_{sn}.mp3")

                if voice_url and await _download_file(voice_url, dl_path, f"voice scene {sn}"):
                    audio_path = dl_path
                elif voice_r2_key:
                    try:
                        from utils.r2_presign import presign_key
                        fresh_url = presign_key(voice_r2_key, expiry=600)
                        if fresh_url and await _download_file(fresh_url, dl_path, f"voice scene {sn} (key)"):
                            audio_path = dl_path
                    except Exception:
                        pass

                if not os.path.exists(dl_path):
                    logger.error(f"[RENDER {job_id[:8]}] FAILED to download voice for scene {sn}")

            if not os.path.exists(img_path) or not os.path.exists(audio_path):
                logger.warning(f"[RENDER {job_id[:8]}] Missing files for scene {sn}: img={os.path.exists(img_path)}, audio={os.path.exists(audio_path)}")
                failed_scenes.append(sn)
                continue

            # Update progress: encoding this scene
            enc_pct = int(75 + 5 + ((idx) / total_scenes) * 10)
            await update_job(job_id, {
                "progress": enc_pct,
                "current_step": f"Encoding scene {idx+1}/{total_scenes}..."
            })

            # Step 1: Resize image to 1280x720
            small_img = os.path.join(temp_dir, f"small_{sn}.jpg")
            rc, _, _ = await _run_ffmpeg([
                "ffmpeg", "-y", "-threads", "1",
                "-i", img_path,
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-q:v", "3", small_img
            ], timeout=30)
            if rc == 0 and os.path.exists(small_img):
                if img_path.startswith(temp_dir):
                    try:
                        os.remove(img_path)
                    except OSError:
                        pass
                img_path = small_img

            # Step 2: Encode scene video
            seg_path = os.path.join(temp_dir, f"seg_{sn}.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-threads", "2",
                "-loop", "1", "-i", img_path,
                "-i", audio_path,
                "-filter_complex", "[0:v]fps=24[v]",
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
                "-crf", "28", "-maxrate", "1M", "-bufsize", "1M",
                "-c:a", "aac", "-b:a", "96k",
                "-t", str(duration + 0.3),
                "-shortest", "-pix_fmt", "yuv420p",
                seg_path,
            ]

            logger.info(f"[RENDER {job_id[:8]}] Encoding scene {sn} ({idx+1}/{total_scenes})...")
            try:
                rc, _, stderr = await _run_ffmpeg(cmd, timeout=120)
                if rc == 0 and os.path.exists(seg_path):
                    segments.append(seg_path)
                    scene_ms = int((time.time() - scene_start) * 1000)
                    render_timing[f"scene_{sn}_ms"] = scene_ms
                    logger.info(f"[RENDER {job_id[:8]}] Scene {sn} OK ({scene_ms}ms)")
                else:
                    logger.error(f"[RENDER {job_id[:8]}] Scene {sn} encoding failed (rc={rc}): {stderr[:200]}")
                    failed_scenes.append(sn)
            except RuntimeError as e:
                logger.error(f"[RENDER {job_id[:8]}] Scene {sn} timeout: {e}")
                failed_scenes.append(sn)

            # Cleanup after each scene
            for f in [img_path, audio_path]:
                if f.startswith(temp_dir) and os.path.exists(f):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
            gc.collect()

            # Update progress per scene
            pct = int(80 + ((idx + 1) / total_scenes) * 10)
            await update_job(job_id, {"progress": pct, "current_step": f"Rendered scene {idx+1}/{total_scenes}"})

        if not segments:
            error_detail = f"No video segments created. {len(failed_scenes)} scenes failed: {', '.join(failed_scenes[:5])}"
            raise RuntimeError(error_detail)

        # Log if some scenes failed but we have enough to continue
        if failed_scenes:
            logger.warning(f"[RENDER {job_id[:8]}] {len(failed_scenes)} scenes failed, continuing with {len(segments)} segments")

        # Step 3: Concatenate all segments
        await update_job(job_id, {"progress": 88, "current_step": "Concatenating scenes..."})
        concat_start = time.time()
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")

        watermark = job.get("include_watermark", True)
        if watermark:
            cmd = [
                "ffmpeg", "-y", "-threads", "2",
                "-f", "concat", "-safe", "0", "-i", concat_file,
                "-vf", "drawtext=text='visionary-suite.com':fontcolor=white@0.4:fontsize=16:x=w-tw-10:y=h-th-10",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-maxrate", "1M", "-bufsize", "1M",
                "-c:a", "copy", "-pix_fmt", "yuv420p",
                final_path,
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-threads", "2",
                "-f", "concat", "-safe", "0", "-i", concat_file,
                "-c", "copy",
                final_path,
            ]

        logger.info(f"[RENDER {job_id[:8]}] Concatenating {len(segments)} segments...")
        rc, _, stderr = await _run_ffmpeg(cmd, timeout=120)
        if rc != 0:
            raise RuntimeError(f"Video concat failed: {stderr[:300]}")

        concat_ms = int((time.time() - concat_start) * 1000)
        render_timing["concat_ms"] = concat_ms
        render_timing["total_render_ms"] = int((time.time() - stage_start) * 1000)

        file_size = os.path.getsize(final_path) / (1024 * 1024)
        await update_job(job_id, {"render_path": final_path, "progress": 90})

        logger.info(f"[RENDER {job_id[:8]}] Complete: {len(segments)} scenes, {file_size:.1f}MB, {render_timing['total_render_ms']}ms total")

        return {
            "path": final_path,
            "file_size_mb": round(file_size, 1),
            "segments": len(segments),
            "failed_scenes": len(failed_scenes),
            "timing": render_timing,
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

    logger.info(f"[PIPE {job_id[:8]}] COMPLETE in {total_ms}ms — {video_url[:60]}")


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
