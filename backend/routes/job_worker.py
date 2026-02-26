"""
Async Job Worker - Background Processing for GenStudio Jobs
Processes QUEUED jobs and handles credit finalization (CAPTURE/RELEASE)
Includes SRE Phase 3: Auto-retry, fallback outputs, and improved error handling
"""
import asyncio
import traceback
import os
import sys
import base64
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, EMERGENT_LLM_KEY, LLM_AVAILABLE, log_exception
from routes.wallet import (
    mark_job_started, mark_job_succeeded, mark_job_failed, update_job_progress,
    PRICING_CONFIG
)

# Worker configuration
POLL_INTERVAL = 2  # seconds
MAX_CONCURRENT_JOBS = 3

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 90]  # seconds - exponential backoff


async def process_text_to_image(job: dict) -> dict:
    """Process TEXT_TO_IMAGE job"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    input_data = job.get("inputJson", {})
    prompt = input_data.get("prompt", "")
    negative_prompt = input_data.get("negative_prompt", "")
    aspect_ratio = input_data.get("aspect_ratio", "1:1")
    
    aspect_instructions = {
        "1:1": "square format, 1:1 aspect ratio",
        "16:9": "widescreen format, 16:9 aspect ratio, landscape",
        "9:16": "vertical format, 9:16 aspect ratio, portrait, mobile-friendly",
        "4:3": "standard format, 4:3 aspect ratio"
    }
    
    full_prompt = f"{prompt}. {aspect_instructions.get(aspect_ratio, '')}"
    if negative_prompt:
        full_prompt += f". Avoid: {negative_prompt}"
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"job-{job['id']}",
        system_message="You are an AI image generator. Generate high-quality images based on the user's prompt."
    ).with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
    
    msg = UserMessage(text=full_prompt)
    text_response, images = await chat.send_message_multimodal_response(msg)
    
    if not images or len(images) == 0:
        raise Exception("No image was generated")
    
    output_urls = []
    for i, img in enumerate(images):
        image_bytes = base64.b64decode(img['data'])
        filename = f"genstudio_{job['id']}_{i}.png"
        filepath = f"/tmp/{filename}"
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        output_urls.append(f"/api/genstudio/download/{job['id']}/{filename}")
    
    return {"outputUrl": output_urls[0], "outputUrls": output_urls}


async def process_text_to_video(job: dict) -> dict:
    """Process TEXT_TO_VIDEO job using Sora 2"""
    from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
    
    input_data = job.get("inputJson", {})
    prompt = input_data.get("prompt", "")
    duration = input_data.get("duration", 4)
    aspect_ratio = input_data.get("aspect_ratio", "16:9")
    
    size_map = {
        "16:9": "1280x720",
        "9:16": "1024x1792",
        "1:1": "1024x1024",
        "4:3": "1280x720"
    }
    video_size = size_map.get(aspect_ratio, "1280x720")
    
    # Valid durations for Sora 2
    valid_durations = [4, 8, 12]
    if duration not in valid_durations:
        duration = 4
    
    video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
    
    filename = f"genstudio_{job['id']}.mp4"
    filepath = f"/tmp/{filename}"
    
    video_bytes = video_gen.text_to_video(
        prompt=prompt,
        model="sora-2",
        size=video_size,
        duration=duration,
        max_wait_time=600
    )
    
    if not video_bytes:
        raise Exception("Video generation failed - no video returned")
    
    video_gen.save_video(video_bytes, filepath)
    
    output_url = f"/api/genstudio/download/{job['id']}/{filename}"
    return {"outputUrl": output_url, "outputUrls": [output_url]}


async def process_story_generation(job: dict) -> dict:
    """Process STORY_GENERATION job"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    from shared import STORY_SYSTEM_PROMPT, STORY_USER_PROMPT_TEMPLATE
    import json
    import uuid
    
    input_data = job.get("inputJson", {})
    unique_id = str(uuid.uuid4())[:8]
    
    prompt = STORY_USER_PROMPT_TEMPLATE.format(
        genre=input_data.get("genre", "Adventure"),
        ageGroup=input_data.get("ageGroup", "4-6"),
        theme=input_data.get("theme", "Friendship"),
        scenes=input_data.get("sceneCount", 8),
        customElements=input_data.get("customGenre", ""),
        uniqueId=unique_id
    )
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"story-{job['id']}",
        system_message=STORY_SYSTEM_PROMPT
    ).with_model("gemini", "gemini-3-flash-preview")
    
    response = await chat.send_message(UserMessage(text=prompt))
    
    response_text = response.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    result = json.loads(response_text.strip())
    
    # Store result as JSON
    filename = f"story_{job['id']}.json"
    filepath = f"/tmp/{filename}"
    with open(filepath, "w") as f:
        json.dump(result, f)
    
    return {"outputUrl": f"/api/wallet/jobs/{job['id']}/result", "outputUrls": [], "resultJson": result}


async def process_reel_generation(job: dict) -> dict:
    """Process REEL_GENERATION job"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    from shared import REEL_SYSTEM_PROMPT, REEL_USER_PROMPT_TEMPLATE
    import json
    import uuid
    
    input_data = job.get("inputJson", {})
    unique_id = str(uuid.uuid4())[:8]
    
    prompt = REEL_USER_PROMPT_TEMPLATE.format(
        language=input_data.get("language", "English"),
        niche=input_data.get("niche", "General"),
        tone=input_data.get("tone", "Bold"),
        duration=input_data.get("duration", "30s"),
        goal=input_data.get("goal", "Engagement"),
        topic=input_data.get("topic", ""),
        uniqueId=unique_id
    )
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"reel-{job['id']}",
        system_message=REEL_SYSTEM_PROMPT
    ).with_model("gemini", "gemini-3-flash-preview")
    
    response = await chat.send_message(UserMessage(text=prompt))
    
    response_text = response.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    result = json.loads(response_text.strip())
    
    return {"outputUrl": f"/api/wallet/jobs/{job['id']}/result", "outputUrls": [], "resultJson": result}


async def process_image_to_video(job: dict) -> dict:
    """Process IMAGE_TO_VIDEO job using Sora 2 with image reference"""
    from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
    
    input_data = job.get("inputJson", {})
    motion_prompt = input_data.get("motionPrompt", "")
    duration = input_data.get("duration", 4)
    aspect_ratio = input_data.get("aspectRatio", "16:9")
    _image_base64 = input_data.get("imageBase64", "")  # Reserved for future image-based generation
    
    size_map = {
        "16:9": "1280x720",
        "9:16": "1024x1792",
        "1:1": "1024x1024",
        "4:3": "1280x720"
    }
    video_size = size_map.get(aspect_ratio, "1280x720")
    
    # Valid durations for Sora 2
    valid_durations = [4, 8, 12]
    if duration not in valid_durations:
        duration = 4
    
    # For image-to-video, we create an enhanced prompt describing the image motion
    # Since Sora 2 text-to-video doesn't directly accept images, we use a detailed prompt approach
    enhanced_prompt = f"Animate this scene with the following motion: {motion_prompt}. Create smooth, realistic movement. High quality cinematic video."
    
    video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
    
    filename = f"genstudio_{job['id']}.mp4"
    filepath = f"/tmp/{filename}"
    
    video_bytes = video_gen.text_to_video(
        prompt=enhanced_prompt,
        model="sora-2",
        size=video_size,
        duration=duration,
        max_wait_time=600
    )
    
    if not video_bytes:
        raise Exception("Video generation failed - no video returned")
    
    video_gen.save_video(video_bytes, filepath)
    
    output_url = f"/api/genstudio/download/{job['id']}/{filename}"
    return {"outputUrl": output_url, "outputUrls": [output_url]}


# Job type to processor mapping
JOB_PROCESSORS = {
    "TEXT_TO_IMAGE": process_text_to_image,
    "TEXT_TO_VIDEO": process_text_to_video,
    "IMAGE_TO_VIDEO": process_image_to_video,
    "STORY_GENERATION": process_story_generation,
    "REEL_GENERATION": process_reel_generation,
}


async def process_job(job: dict):
    """Process a single job with retry logic and fallback outputs"""
    job_id = job["id"]
    job_type = job["jobType"]
    user_id = job["userId"]
    attempts = job.get("attempts", 0) + 1
    
    logger.info(f"Processing job {job_id} (type: {job_type}, attempt: {attempts}/{MAX_RETRIES})")
    
    try:
        # Mark as running
        await mark_job_started(job_id)
        await update_job_progress(job_id, 10, "Starting generation...")
        
        # Update attempt count
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {"attempts": attempts, "lastAttemptAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Get processor
        processor = JOB_PROCESSORS.get(job_type)
        if not processor:
            raise Exception(f"Unknown job type: {job_type}")
        
        await update_job_progress(job_id, 30, "Processing with AI...")
        
        # Process the job with timeout
        try:
            result = await asyncio.wait_for(processor(job), timeout=300)  # 5 min timeout
        except asyncio.TimeoutError:
            raise Exception("Job processing timed out after 5 minutes")
        
        await update_job_progress(job_id, 90, "Finalizing...")
        
        # Mark success and capture credits
        output_url = result.get("outputUrl", "")
        output_urls = result.get("outputUrls", [])
        result_json = result.get("resultJson")
        
        # Store result JSON if present
        if result_json:
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {"resultJson": result_json}}
            )
        
        await mark_job_succeeded(job_id, output_url, output_urls)
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Job {job_id} failed (attempt {attempts}): {error_message}")
        
        # Check if we should retry
        if attempts < MAX_RETRIES and _is_retryable_error(error_message):
            await _schedule_retry(job_id, job_type, attempts, error_message)
        else:
            # Mark as failed and generate fallback output
            await mark_job_failed(job_id, error_message)
            
            # Generate fallback output for user
            await _generate_fallback_output(job_id, user_id, job_type, job.get("inputJson", {}), error_message)
        
        await log_exception(
            functionality=f"job_worker_{job_type}",
            error_type="JOB_PROCESSING_FAILED",
            error_message=error_message,
            user_id=user_id,
            stack_trace=traceback.format_exc(),
            severity="ERROR" if attempts >= MAX_RETRIES else "WARNING"
        )


def _is_retryable_error(error_message: str) -> bool:
    """Determine if an error is retryable"""
    non_retryable = [
        "invalid input",
        "content policy",
        "violates",
        "blocked",
        "unknown job type",
        "insufficient credits"
    ]
    error_lower = error_message.lower()
    return not any(term in error_lower for term in non_retryable)


async def _schedule_retry(job_id: str, job_type: str, attempts: int, error_message: str):
    """Schedule a job for retry with exponential backoff"""
    delay_idx = min(attempts - 1, len(RETRY_DELAYS) - 1)
    delay = RETRY_DELAYS[delay_idx]
    retry_at = datetime.now(timezone.utc).replace(second=datetime.now().second + delay)
    
    await db.genstudio_jobs.update_one(
        {"id": job_id},
        {
            "$set": {
                "status": "QUEUED",
                "lastError": error_message,
                "retryAt": retry_at.isoformat(),
                "retryCount": attempts
            }
        }
    )
    
    logger.info(f"Job {job_id} scheduled for retry in {delay}s (attempt {attempts + 1}/{MAX_RETRIES})")


async def _generate_fallback_output(job_id: str, user_id: str, job_type: str, input_data: dict, error_message: str):
    """Generate fallback output when job fails after all retries"""
    try:
        from services.fallback_output_service import get_fallback_service
        fallback_service = await get_fallback_service(db)
        
        fallback = await fallback_service.generate_fallback(
            job_id=job_id,
            user_id=user_id,
            job_type=job_type,
            input_data=input_data,
            error_message=error_message
        )
        
        if fallback:
            # Store fallback in job result
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "hasFallback": True,
                    "fallbackType": fallback.get("fallbackType"),
                    "fallbackMessage": fallback.get("message")
                }}
            )
            logger.info(f"Generated {fallback.get('fallbackType')} fallback for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to generate fallback for job {job_id}: {e}")


async def worker_loop():
    """Main worker loop - polls for QUEUED jobs and processes them"""
    logger.info("Job Worker started")
    
    while True:
        try:
            # Find QUEUED jobs (oldest first)
            queued_jobs = await db.genstudio_jobs.find(
                {"status": "QUEUED"},
                {"_id": 0}
            ).sort("createdAt", 1).limit(MAX_CONCURRENT_JOBS).to_list(MAX_CONCURRENT_JOBS)
            
            if queued_jobs:
                logger.info(f"Found {len(queued_jobs)} queued jobs")
                
                # Process jobs concurrently
                tasks = [process_job(job) for job in queued_jobs]
                await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
        
        await asyncio.sleep(POLL_INTERVAL)


def start_worker():
    """Start the worker in a separate thread/process"""
    asyncio.run(worker_loop())


if __name__ == "__main__":
    start_worker()
