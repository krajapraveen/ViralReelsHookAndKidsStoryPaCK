"""Generate TTS voice-overs and create video from images using ffmpeg"""
import asyncio, os, subprocess, json, time
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from emergentintegrations.llm.openai import OpenAITextToSpeech

OUTPUT_DIR = "/app/backend/static/generated"
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

VIDEOS = [
    {
        "id": "instagram_reel",
        "filename": "visionary_suite_instagram_reel.mp4",
        "image": "promo_instagram_reel.png",
        "voiceover": "Stop scrolling. This AI tool is absolutely insane. Visionary Suite creates viral content in 60 seconds flat. Generate scroll-stopping Instagram reels with hooks, scripts, captions, and trending hashtags. Create complete kids story video packs with AI voiceover and illustrations. Turn any photo into stunning comic avatars and animated reaction GIFs. Build 30-day content calendars, YouTube thumbnails, brand stories, and so much more. Over 20 AI-powered tools. All in one platform. Get 100 free credits right now. Link in bio.",
        "duration": 12
    },
    {
        "id": "instagram_story",
        "filename": "visionary_suite_instagram_story.mp4",
        "image": "promo_instagram_story.png",
        "voiceover": "POV: You just discovered the AI tool that does everything. Viral reel scripts. Kids story videos. Comic art. Coloring books. Bio generators. Caption rewriters. Challenge planners. All powered by AI. All in one place. Visionary Suite. 100 free credits. No credit card needed.",
        "duration": 8
    },
    {
        "id": "youtube_shorts",
        "filename": "visionary_suite_youtube_shorts.mp4",
        "image": "promo_youtube_shorts.png",
        "voiceover": "What if one tool could replace your entire content team? Meet Visionary Suite. The AI content creation platform that's changing the game. Generate viral reel scripts with 5 unique hooks in 10 seconds. Create kids story packs with voiceover and illustrations in under 90 seconds. Transform photos into comic art. Build animated GIFs. Design YouTube thumbnails. Plan 30-day content calendars. Craft Instagram bios. Rewrite captions in any tone. Over 5,000 creators. Over 50,000 pieces of content created. Get started free today. 100 credits on signup.",
        "duration": 12
    }
]

async def create_video(v):
    print(f"\n[{v['id']}] Creating promo video...")
    final_path = os.path.join(OUTPUT_DIR, v["filename"])
    image_path = os.path.join(OUTPUT_DIR, v["image"])
    audio_path = os.path.join(OUTPUT_DIR, f"vo_{v['id']}.mp3")
    
    update_status(v["id"], "GENERATING")
    
    # Step 1: Generate voice-over
    print(f"  Generating voice-over...")
    tts = OpenAITextToSpeech(api_key=API_KEY)
    audio_bytes = await tts.generate_speech(
        text=v["voiceover"],
        model="tts-1-hd",
        voice="onyx",
        speed=1.05,
        response_format="mp3"
    )
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
    print(f"  Voice-over: {os.path.getsize(audio_path)/1024:.0f}KB")
    
    # Step 2: Get audio duration
    probe = subprocess.run(
        ["ffprobe", "-i", audio_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
        capture_output=True, text=True
    )
    audio_dur = float(probe.stdout.strip())
    print(f"  Audio duration: {audio_dur:.1f}s")
    
    # Step 3: Create video from image + audio with zoom/pan animation (Ken Burns effect)
    # Zoom from 1.0 to 1.15 over the duration for cinematic feel
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]scale=1080:1920,zoompan=z='min(zoom+0.0008,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(audio_dur*25)}:s=1080x1920:fps=25[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        final_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr[:300]}")
        raise Exception(f"ffmpeg failed: {result.returncode}")
    
    size_mb = os.path.getsize(final_path) / (1024 * 1024)
    print(f"  Final video: {size_mb:.1f}MB")
    
    update_status(v["id"], "COMPLETED", final_path)
    
    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    return True

async def main():
    print("="*60)
    print("CREATING PROMO VIDEOS (Image + TTS + Ken Burns)")
    print("="*60)
    
    for v in VIDEOS:
        try:
            await create_video(v)
        except Exception as e:
            print(f"  FAILED: {e}")
            update_status(v["id"], "FAILED", error=str(e))
    
    # Verify all 4 videos exist
    all_files = ["visionary_suite_instagram_reel.mp4", "visionary_suite_instagram_story.mp4", 
                 "visionary_suite_youtube_shorts.mp4", "visionary_suite_facebook_reel.mp4"]
    available = [f for f in all_files if os.path.exists(os.path.join(OUTPUT_DIR, f))]
    print(f"\nFINAL: {len(available)}/4 videos available")
    for f in all_files:
        exists = os.path.exists(os.path.join(OUTPUT_DIR, f))
        size = os.path.getsize(os.path.join(OUTPUT_DIR, f))/(1024*1024) if exists else 0
        print(f"  {'OK' if exists else 'MISSING'} {f} ({size:.1f}MB)")

if __name__ == "__main__":
    asyncio.run(main())
