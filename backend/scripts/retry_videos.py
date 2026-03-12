"""Retry failed video generations one at a time with retries"""
import asyncio, os, time, json, subprocess, traceback
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
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
    print(f"  [{video_id}] {status}")

RETRY_VIDEOS = [
    {
        "id": "instagram_reel",
        "filename": "visionary_suite_instagram_reel.mp4",
        "duration": 12,
        "prompt": "A hyper-energetic cinematic promotional video for an AI content creation platform. Dark screen explodes with neon purple and blue light. Holographic interfaces showing AI-generated GIFs, storybooks, comics, and social media content materializing with sparkle effects. Quick cuts of amazed person, cartoon characters coming to life, coloring pages drawn by invisible hands. Pulsing neon trails and floating UI. Cinematic, vibrant neon purple, dramatic, high energy.",
        "voiceover": "Stop scrolling. This AI tool is absolutely insane. Visionary Suite creates viral content in 60 seconds flat. Generate Instagram reels with hooks and captions. Create kids story video packs with AI voiceover. Turn photos into comic avatars and reaction GIFs. Build content calendars, YouTube thumbnails, and brand stories. Over 20 AI tools. All in one platform. Get 100 free credits now. Link in bio."
    },
    {
        "id": "instagram_story",
        "filename": "visionary_suite_instagram_story.mp4",
        "duration": 8,
        "prompt": "A stunning cinematic video of a creative person opening a glowing laptop in a dimly lit purple room. Holographic AI content bursts from the screen: animated characters, comic panels, GIF reactions, social media icons raining down. Person transforms from bored to amazed. Room fills with magical purple-blue light and sparkles. Beautiful bokeh, dreamy high-tech aesthetic.",
        "voiceover": "POV: You just discovered the AI tool that does everything. Viral reel scripts. Kids story videos. Comic art. Coloring books. Bio generators. Caption rewriters. All powered by AI. All in one place. Visionary Suite. 100 free credits. No credit card needed."
    },
    {
        "id": "youtube_shorts",
        "filename": "visionary_suite_youtube_shorts.mp4",
        "duration": 12,
        "prompt": "An eye-catching cinematic video of a hand tapping a glowing CREATE button on a glass tablet. AI content flows outward: YouTube thumbnails, animated story videos, reaction GIFs, Instagram reels, coloring pages fluttering like paper airplanes. Camera pulls back showing dozens of floating holographic screens. Social media notifications show millions of views. Content swirls into a supernova of light. Neon purple and blue, cinematic.",
        "voiceover": "What if one tool could replace your entire content team? Meet Visionary Suite. Generate viral reel scripts with 5 hooks in 10 seconds. Create kids story packs with voiceover in under 90 seconds. Transform photos into comic art. Build GIFs, thumbnails, calendars, bios, and more. Over 5,000 creators. 50,000 pieces created. Get started free. 100 credits on signup."
    }
]

async def process_video(v, max_retries=2):
    final_path = os.path.join(OUTPUT_DIR, v["filename"])
    if os.path.exists(final_path):
        print(f"  SKIP: {v['id']} already exists")
        return True
    
    for attempt in range(max_retries):
        print(f"\n  Attempt {attempt+1}/{max_retries} for {v['id']}")
        update_status(v["id"], "GENERATING")
        try:
            # Step 1: Generate video
            vg = OpenAIVideoGeneration(api_key=API_KEY)
            raw = os.path.join(OUTPUT_DIR, f"raw_{v['id']}.mp4")
            vb = vg.text_to_video(prompt=v["prompt"], model="sora-2", size="1280x720", duration=v["duration"], max_wait_time=600)
            if not vb:
                print(f"  No video bytes on attempt {attempt+1}")
                continue
            vg.save_video(vb, raw)
            print(f"  Video: {os.path.getsize(raw)/(1024*1024):.1f}MB")
            
            # Step 2: Convert to vertical
            vert = os.path.join(OUTPUT_DIR, f"vert_{v['id']}.mp4")
            r = subprocess.run(["ffmpeg","-y","-i",raw,"-filter_complex","[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=20:20[bg];[0:v]scale=720:-2:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2","-c:v","libx264","-crf","23","-preset","fast","-an",vert], capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                raise Exception(f"ffmpeg convert failed")
            print(f"  Vertical: {os.path.getsize(vert)/(1024*1024):.1f}MB")
            
            # Step 3: Voice-over
            tts = OpenAITextToSpeech(api_key=API_KEY)
            audio = os.path.join(OUTPUT_DIR, f"vo_{v['id']}.mp3")
            ab = await tts.generate_speech(text=v["voiceover"], model="tts-1-hd", voice="onyx", speed=1.05, response_format="mp3")
            with open(audio, "wb") as f:
                f.write(ab)
            print(f"  Voice: {os.path.getsize(audio)/1024:.0f}KB")
            
            # Step 4: Merge
            r2 = subprocess.run(["ffmpeg","-y","-i",vert,"-i",audio,"-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-map","0:v:0","-map","1:a:0",final_path], capture_output=True, text=True, timeout=60)
            if r2.returncode != 0:
                raise Exception(f"ffmpeg merge failed")
            print(f"  Final: {os.path.getsize(final_path)/(1024*1024):.1f}MB")
            
            update_status(v["id"], "COMPLETED", final_path)
            for f in [raw, vert, audio]:
                if os.path.exists(f): os.remove(f)
            return True
        except Exception as e:
            print(f"  Error: {e}")
            traceback.print_exc()
            if attempt == max_retries - 1:
                update_status(v["id"], "FAILED", error=str(e))
    return False

async def main():
    print("RETRYING FAILED VIDEOS...\n")
    for v in RETRY_VIDEOS:
        await process_video(v)
    
    # Summary
    files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("visionary_suite_") and f.endswith(".mp4")]
    print(f"\nFinal: {len(files)} videos available: {files}")

if __name__ == "__main__":
    asyncio.run(main())
