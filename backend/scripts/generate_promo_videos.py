"""
Generate 4 promotional videos for Visionary Suite using Sora 2.
Each video targets a different social media platform.
"""
import os
import sys
import time
import json
import traceback
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration

OUTPUT_DIR = "/app/backend/static/generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)

STATUS_FILE = "/app/backend/static/generated/video_gen_status.json"

def update_status(video_id, status, path=None, error=None):
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}
    data[video_id] = {"status": status, "path": path, "error": error, "updated": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[{video_id}] {status}" + (f" -> {path}" if path else "") + (f" ERROR: {error}" if error else ""))

VIDEOS = [
    {
        "id": "instagram_reel",
        "filename": "visionary_suite_instagram_reel.mp4",
        "duration": 12,
        "size": "1024x1792",
        "prompt": (
            "A hyper-energetic, fast-paced vertical promotional video for a revolutionary AI content creation platform called 'Visionary Suite'. "
            "The video opens with a dramatic dark screen that EXPLODES with neon purple and electric blue light particles. "
            "Show a sleek futuristic holographic interface floating in dark space - glowing screens showing AI generating stunning animated GIFs, "
            "colorful children's storybook illustrations, comic-style avatars, and viral social media reels - all appearing instantly with magical sparkle effects. "
            "Quick cuts between: a person's amazed face lit by screen glow, AI-generated cartoon characters coming to life, "
            "colorful coloring book pages being drawn by invisible AI hands, and social media engagement counters rapidly climbing. "
            "The energy builds with pulsing light trails and floating holographic UI elements. "
            "End with a massive glowing text 'GO VIRAL WITH AI' exploding into particles against a deep purple galaxy background. "
            "Cinematic quality, vibrant neon colors, dramatic lighting, high energy, futuristic tech aesthetic."
        )
    },
    {
        "id": "instagram_story",
        "filename": "visionary_suite_instagram_story.mp4",
        "duration": 8,
        "size": "1024x1792",
        "prompt": (
            "A stunning vertical video showing a creative person sitting at their desk in a dimly lit room with purple ambient lighting. "
            "They open a glowing laptop and suddenly the entire room transforms - holographic AI-generated content bursts out of the screen: "
            "beautiful animated storybook characters float through the air, colorful comic panels materialize around them, "
            "animated GIF reactions spin playfully, and social media icons with heart and fire emojis rain down like confetti. "
            "The person's expression goes from bored to absolutely amazed and excited, reaching out to touch the floating holographic creations. "
            "The room fills with magical purple and blue light, with sparkles and particle effects everywhere. "
            "Cinematic slow-motion moments mixed with quick energetic cuts. Beautiful bokeh lighting, "
            "dreamy yet high-tech aesthetic, warm skin tones contrasted with cool neon AI elements."
        )
    },
    {
        "id": "youtube_shorts",
        "filename": "visionary_suite_youtube_shorts.mp4",
        "duration": 12,
        "size": "1024x1792",
        "prompt": (
            "An eye-catching vertical video that starts with a close-up of a hand tapping a glowing 'CREATE' button on a futuristic glass tablet. "
            "Instantly, the screen erupts with AI-generated content flowing outward like a fountain of creativity: "
            "professional YouTube thumbnails with bold text materialize, animated kids story videos play in floating frames, "
            "reaction GIFs with expressive cartoon faces bounce around, Instagram reels auto-generate with trending music visualizers, "
            "and coloring book pages with intricate AI-drawn designs flutter through the air like paper airplanes. "
            "Camera pulls back to reveal dozens of floating holographic screens showing different AI creations - "
            "each one more impressive than the last. Social media notification badges pop up showing millions of views and likes. "
            "Ends with all the floating content swirling together into a brilliant supernova of light. "
            "Ultra-modern, high-energy, neon purple and electric blue color palette, cinematic depth of field."
        )
    },
    {
        "id": "facebook_reel",
        "filename": "visionary_suite_facebook_reel.mp4",
        "duration": 12,
        "size": "1024x1792",
        "prompt": (
            "A cinematic vertical video showing a split-screen transformation. On the left side (representing 'BEFORE'), "
            "a frustrated content creator stares at a blank screen in a gray, dull office with harsh fluorescent lighting. "
            "Then a glowing purple wave sweeps across the screen from left to right, dramatically transforming everything. "
            "On the right side (representing 'AFTER'), the same person is now in a vibrant, colorful creative studio "
            "surrounded by floating holographic AI-generated content: stunning animated story videos playing on multiple screens, "
            "professional comic book art being generated in real-time, beautiful coloring pages materializing from thin air, "
            "viral social media posts with millions of engagement metrics floating by. "
            "The person is now confident, smiling, creating content effortlessly with just hand gestures in the air. "
            "The environment pulses with creative energy - glowing purple and blue particles, holographic interfaces, "
            "and floating social media icons showing massive growth. Cinematic quality, inspirational, warm and inviting yet futuristic."
        )
    }
]


def generate_all_videos():
    print(f"\n{'='*60}")
    print(f"VISIONARY SUITE - SORA 2 VIDEO GENERATION")
    print(f"{'='*60}")
    print(f"Generating {len(VIDEOS)} promotional videos...")
    print(f"Output directory: {OUTPUT_DIR}\n")

    # Initialize status
    for v in VIDEOS:
        update_status(v["id"], "PENDING")

    results = []
    for i, video in enumerate(VIDEOS):
        print(f"\n[{i+1}/{len(VIDEOS)}] Generating: {video['id']}")
        print(f"  Size: {video['size']}, Duration: {video['duration']}s")
        print(f"  Prompt: {video['prompt'][:80]}...")
        
        update_status(video["id"], "GENERATING")
        start_time = time.time()
        
        try:
            video_gen = OpenAIVideoGeneration(api_key=os.environ['EMERGENT_LLM_KEY'])
            output_path = os.path.join(OUTPUT_DIR, video["filename"])
            
            video_bytes = video_gen.text_to_video(
                prompt=video["prompt"],
                model="sora-2",
                size=video["size"],
                duration=video["duration"],
                max_wait_time=600
            )
            
            elapsed = time.time() - start_time
            
            if video_bytes:
                video_gen.save_video(video_bytes, output_path)
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                update_status(video["id"], "COMPLETED", output_path)
                print(f"  DONE in {elapsed:.0f}s | File: {file_size:.1f}MB")
                results.append({"id": video["id"], "status": "COMPLETED", "path": output_path, "time": elapsed})
            else:
                update_status(video["id"], "FAILED", error="No video bytes returned")
                print(f"  FAILED: No video bytes returned ({elapsed:.0f}s)")
                results.append({"id": video["id"], "status": "FAILED", "time": elapsed})
                
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            update_status(video["id"], "FAILED", error=error_msg)
            print(f"  FAILED: {error_msg} ({elapsed:.0f}s)")
            traceback.print_exc()
            results.append({"id": video["id"], "status": "FAILED", "error": error_msg, "time": elapsed})

    print(f"\n{'='*60}")
    print("GENERATION SUMMARY:")
    for r in results:
        status_emoji = "OK" if r["status"] == "COMPLETED" else "FAIL"
        print(f"  [{status_emoji}] {r['id']} - {r['status']} ({r['time']:.0f}s)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    generate_all_videos()
