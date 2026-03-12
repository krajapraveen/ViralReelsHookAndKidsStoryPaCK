"""
Generate 4 promotional videos for Visionary Suite with Sora 2 visuals + male voice-over.
Pipeline: Sora 2 (1280x720) -> ffmpeg vertical convert -> OpenAI TTS -> ffmpeg merge
"""
import asyncio
import os
import sys
import time
import json
import subprocess
import traceback
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
from emergentintegrations.llm.openai import OpenAITextToSpeech

OUTPUT_DIR = "/app/backend/static/generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)
STATUS_FILE = os.path.join(OUTPUT_DIR, "video_gen_status.json")
API_KEY = os.environ['EMERGENT_LLM_KEY']


def update_status(video_id, status, path=None, error=None):
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}
    data[video_id] = {"status": status, "path": path, "error": error, "updated": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [{video_id}] {status}" + (f" -> {path}" if path else "") + (f" | ERROR: {error}" if error else ""))


VIDEOS = [
    {
        "id": "instagram_reel",
        "filename": "visionary_suite_instagram_reel.mp4",
        "duration": 12,
        "prompt": (
            "A hyper-energetic, fast-paced cinematic promotional video for a revolutionary AI content creation platform. "
            "Opens with a dramatic dark screen that EXPLODES with neon purple and electric blue light particles. "
            "Show a sleek holographic interface floating in dark space with glowing screens displaying AI-generated animated GIFs, "
            "colorful children's storybook illustrations, comic-style character avatars, and social media reel scripts "
            "all materializing instantly with magical sparkle effects. Quick cinematic cuts between: a person amazed by screen glow, "
            "AI cartoon characters coming to life, coloring book pages being drawn by invisible hands, social media counters climbing. "
            "Pulsing neon light trails and floating holographic UI elements. "
            "Cinematic quality, vibrant neon purple and blue colors, dramatic lighting, high energy."
        ),
        "voiceover": (
            "Stop scrolling. This AI tool is absolutely insane. "
            "Visionary Suite creates viral content in 60 seconds flat. "
            "Generate scroll-stopping Instagram reels with hooks, scripts, captions, and trending hashtags. "
            "Create complete kids story video packs with AI voiceover and illustrations. "
            "Turn any photo into stunning comic avatars and animated reaction GIFs. "
            "Build 30-day content calendars, YouTube thumbnails, brand stories, and so much more. "
            "Over 20 AI-powered tools. All in one platform. "
            "Get 100 free credits right now. Link in bio."
        )
    },
    {
        "id": "instagram_story",
        "filename": "visionary_suite_instagram_story.mp4",
        "duration": 8,
        "prompt": (
            "A stunning cinematic video of a creative person at their desk in a dimly lit room with purple ambient lighting. "
            "They open a glowing laptop and the entire room transforms. Holographic AI-generated content bursts from the screen: "
            "animated storybook characters float through the air, colorful comic panels materialize around them, "
            "animated GIF reactions spin playfully, social media icons with hearts and fire emojis rain down. "
            "The person's face transforms from bored to absolutely amazed, reaching out to touch floating holographic creations. "
            "Room fills with magical purple and blue light with sparkles and particles everywhere. "
            "Cinematic slow-motion mixed with energetic cuts. Beautiful bokeh lighting, dreamy high-tech aesthetic."
        ),
        "voiceover": (
            "POV: You just discovered the AI tool that does everything. "
            "Viral reel scripts. Kids story videos. Comic art. Coloring books. "
            "Bio generators. Caption rewriters. Challenge planners. "
            "All powered by AI. All in one place. "
            "Visionary Suite. 100 free credits. No credit card needed."
        )
    },
    {
        "id": "youtube_shorts",
        "filename": "visionary_suite_youtube_shorts.mp4",
        "duration": 12,
        "prompt": (
            "An eye-catching cinematic video starting with a close-up of a hand tapping a glowing CREATE button on a futuristic glass tablet. "
            "The screen erupts with AI-generated content flowing outward like a fountain of creativity. "
            "Professional YouTube thumbnails materialize, animated kids story videos play in floating frames, "
            "reaction GIFs with expressive faces bounce around, Instagram reels auto-generate with music visualizers, "
            "coloring book pages with intricate designs flutter through air like paper airplanes. "
            "Camera pulls back revealing dozens of floating holographic screens showing different AI creations. "
            "Social media notification badges pop up showing millions of views and likes. "
            "Content swirls into a brilliant supernova of light. Ultra-modern, neon purple and blue, cinematic quality."
        ),
        "voiceover": (
            "What if one tool could replace your entire content team? "
            "Meet Visionary Suite. The AI content creation platform that's changing the game. "
            "Generate viral reel scripts with 5 unique hooks in 10 seconds. "
            "Create kids story packs with voiceover and illustrations in under 90 seconds. "
            "Transform photos into comic art. Build animated GIFs. Design YouTube thumbnails. "
            "Plan 30-day content calendars. Craft Instagram bios. Rewrite captions in any tone. "
            "Generate bedtime stories, brand stories, viral challenge ideas, and offer graphics. "
            "Over 5,000 creators. Over 50,000 pieces of content created. "
            "Get started free today. 100 credits on signup."
        )
    },
    {
        "id": "facebook_reel",
        "filename": "visionary_suite_facebook_reel.mp4",
        "duration": 12,
        "prompt": (
            "A cinematic video showing a dramatic transformation. A frustrated content creator stares at a blank screen "
            "in a gray dull office with harsh fluorescent lighting. Then a glowing purple wave sweeps across the screen "
            "transforming everything. The same person is now in a vibrant colorful creative studio surrounded by floating "
            "holographic AI-generated content: animated story videos on screens, comic book art being generated in real-time, "
            "coloring pages materializing, viral social media posts with engagement metrics floating by. "
            "The person creates content effortlessly with hand gestures. Environment pulses with creative energy, "
            "glowing purple and blue particles, holographic interfaces, floating social media icons showing massive growth. "
            "Cinematic quality, inspirational, warm yet futuristic."
        ),
        "voiceover": (
            "Tired of spending hours creating content that nobody sees? "
            "Visionary Suite is your AI-powered content creation studio. "
            "Create viral Instagram reels, TikToks, and YouTube shorts in seconds. "
            "Generate complete kids story video production packs. "
            "Build comic storybooks, reaction GIFs, and coloring book pages. "
            "Use our creator pro tools. Caption rewriter, tone switcher, "
            "story hook generator, comment reply bank, and daily viral ideas. "
            "Earn free credits daily with login rewards. "
            "Plans start at just 199 rupees. "
            "Join 5,000 plus creators at visionary suite dot com."
        )
    }
]


def generate_video_sora(video_config):
    """Generate video with Sora 2 in landscape 1280x720"""
    print(f"  STEP 1: Generating video with Sora 2 ({video_config['duration']}s, 1280x720)...")
    video_gen = OpenAIVideoGeneration(api_key=API_KEY)
    raw_path = os.path.join(OUTPUT_DIR, f"raw_{video_config['id']}.mp4")

    video_bytes = video_gen.text_to_video(
        prompt=video_config["prompt"],
        model="sora-2",
        size="1280x720",
        duration=video_config["duration"],
        max_wait_time=600
    )

    if not video_bytes:
        raise Exception("Sora 2 returned no video bytes")

    video_gen.save_video(video_bytes, raw_path)
    size_mb = os.path.getsize(raw_path) / (1024 * 1024)
    print(f"  Video saved: {size_mb:.1f}MB")
    return raw_path


def convert_to_vertical(input_path, output_path):
    """Convert landscape 1280x720 to vertical 720x1280 with blurred background"""
    print(f"  STEP 2: Converting to vertical 720x1280 with blurred background...")
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex",
        "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=20:20[bg];"
        "[0:v]scale=720:-2:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-an",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"ffmpeg vertical convert failed: {result.stderr[:300]}")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Vertical video: {size_mb:.1f}MB")
    return output_path


async def generate_voiceover(video_config):
    """Generate male voice-over with OpenAI TTS (onyx = deep male voice)"""
    print(f"  STEP 3: Generating male voice-over (onyx, tts-1-hd)...")
    tts = OpenAITextToSpeech(api_key=API_KEY)
    audio_path = os.path.join(OUTPUT_DIR, f"vo_{video_config['id']}.mp3")

    audio_bytes = await tts.generate_speech(
        text=video_config["voiceover"],
        model="tts-1-hd",
        voice="onyx",
        speed=1.05,
        response_format="mp3"
    )

    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    size_kb = os.path.getsize(audio_path) / 1024
    print(f"  Voice-over saved: {size_kb:.0f}KB")
    return audio_path


def merge_video_audio(video_path, audio_path, output_path):
    """Merge vertical video + voice-over with ffmpeg"""
    print(f"  STEP 4: Merging video + voice-over...")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-map", "0:v:0", "-map", "1:a:0",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise Exception(f"ffmpeg merge failed: {result.stderr[:300]}")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Final video: {size_mb:.1f}MB")
    return output_path


async def process_single_video(video_config):
    """Full pipeline: Sora 2 → vertical convert → TTS → merge"""
    video_id = video_config["id"]
    final_path = os.path.join(OUTPUT_DIR, video_config["filename"])

    update_status(video_id, "GENERATING")
    start = time.time()

    try:
        # Step 1: Generate landscape video
        raw_video = generate_video_sora(video_config)

        # Step 2: Convert to vertical
        vertical_path = os.path.join(OUTPUT_DIR, f"vert_{video_id}.mp4")
        convert_to_vertical(raw_video, vertical_path)

        # Step 3: Generate voice-over
        audio = await generate_voiceover(video_config)

        # Step 4: Merge video + audio
        merge_video_audio(vertical_path, audio, final_path)

        elapsed = time.time() - start
        update_status(video_id, "COMPLETED", final_path)
        print(f"  COMPLETE: {video_id} in {elapsed:.0f}s\n")

        # Cleanup temp files
        for f in [raw_video, vertical_path, audio]:
            if os.path.exists(f):
                os.remove(f)

        return True

    except Exception as e:
        elapsed = time.time() - start
        update_status(video_id, "FAILED", error=str(e))
        print(f"  FAILED: {video_id} after {elapsed:.0f}s — {e}")
        traceback.print_exc()
        return False


async def main():
    print(f"\n{'='*60}")
    print("VISIONARY SUITE — PROMO VIDEO GENERATION")
    print("Pipeline: Sora 2 → Vertical Convert → TTS Voice-Over → Merge")
    print(f"{'='*60}\n")

    for v in VIDEOS:
        update_status(v["id"], "PENDING")

    results = []
    for i, video in enumerate(VIDEOS):
        print(f"[{i+1}/{len(VIDEOS)}] Processing: {video['id']}")
        ok = await process_single_video(video)
        results.append((video["id"], ok))

    print(f"\n{'='*60}")
    print("GENERATION SUMMARY:")
    for vid_id, ok in results:
        print(f"  [{'OK' if ok else 'FAIL'}] {vid_id}")
    
    completed = sum(1 for _, ok in results if ok)
    print(f"\n  {completed}/{len(results)} videos generated successfully")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
