"""Batch content generation script for Visionary Suite gallery."""
import asyncio
import time
import json
import aiohttp
import sys

API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"

VIDEOS = [
    {"title": "The Brave Puppy Adventure", "story_text": "A tiny golden puppy named Biscuit gets separated from his family during a thunderstorm. Lost in the big wide world, Biscuit meets a wise old cat named Whiskers who teaches him to be brave. Together they cross a rushing stream, climb a steep hill, and finally find their way back home. Biscuit learns that courage means keeping going even when you are scared, and that friends can appear when you need them most.", "animation_style": "cartoon_2d", "age_group": "kids_3_5", "voice_preset": "narrator_warm"},
    {"title": "The Dragon Who Learned to Share", "story_text": "In a kingdom of colorful dragons, young Ember hoards all the golden apples for himself. When a terrible frost threatens the kingdom and only golden apples can keep the dragons warm, Ember must choose between his treasure and his friends. He decides to share every last apple and discovers that generosity creates a warmth greater than any treasure. The frost melts, flowers bloom, and Ember becomes the most beloved dragon in the realm.", "animation_style": "cartoon_2d", "age_group": "kids_5_8", "voice_preset": "narrator_warm"},
    {"title": "Time Travel to the Dinosaur Age", "story_text": "Twelve-year-old Maya accidentally activates her grandfather's time machine and lands in the age of dinosaurs. She befriends a baby triceratops named Trixie and together they must find the special crystal that powers the time machine before a volcanic eruption destroys everything. Racing against time, Maya uses her science knowledge to navigate the prehistoric world and makes it back just in the nick of time, with a dinosaur feather as proof of her incredible journey.", "animation_style": "3d_pixar", "age_group": "kids_8_12", "voice_preset": "narrator_energetic"},
    {"title": "The Secret Society of Animal Heroes", "story_text": "Every night when humans sleep, a secret society of animal heroes protects the city. Fox is the strategist, Owl provides aerial surveillance, Bear handles heavy lifting, and tiny Mouse can sneak into any space. When a mysterious shadow threatens to engulf the city park, the Animal Heroes must work together combining their unique abilities. Mouse discovers the shadow is actually a lonely creature looking for friends, and they welcome it into their society.", "animation_style": "comic_book", "age_group": "kids_5_8", "voice_preset": "narrator_energetic"},
    {"title": "The Pirate Queen and the Singing Whale", "story_text": "Captain Lily sails the seven seas searching for the legendary Singing Whale whose melody can cure any sadness. Her crew of misfit animals includes a parrot who cannot fly, a cat who loves water, and a rabbit who dreams of adventure. After facing stormy seas and solving riddles from a mermaid, they finally hear the whale's beautiful song. The melody fills their hearts with joy and they realize the real treasure was the friendship they built along the way.", "animation_style": "watercolor", "age_group": "kids_5_8", "voice_preset": "narrator_warm"},
    {"title": "Rise Above - A Story of Belief", "story_text": "A young boy named Kai lives in a small village where everyone says he will never amount to anything. But Kai has a dream, to build a bridge connecting his village to the world beyond the mountains. Day after day he studies, practices, and builds small models. People laugh, but Kai keeps going. Years later, when a flood threatens to isolate the village, it is Kai's bridge design that saves everyone. He proves that belief in yourself is the strongest foundation of all.", "animation_style": "anime_style", "age_group": "teens_13_plus", "voice_preset": "narrator_deep"},
    {"title": "The Cloud Painter", "story_text": "In a world above the clouds lives a little girl named Aira whose job is to paint the sunset every evening. One day her magical paintbrushes disappear and the sky turns grey. Aira must journey through rainbow valleys and star fields to find new colors. Along the way she discovers that the most beautiful sunset comes not from magic brushes but from the love and imagination inside her own heart. She paints the most magnificent sunset the world has ever seen.", "animation_style": "watercolor", "age_group": "kids_3_5", "voice_preset": "narrator_warm"},
]

async def login(session):
    async with session.post(f"{API_URL}/api/auth/login", json={
        "email": "test@visionary-suite.com", "password": "Test@2026#"
    }) as resp:
        data = await resp.json()
        return data.get("token")

async def create_video(session, token, video_data, index):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # Wait for slot
    for attempt in range(30):
        async with session.get(f"{API_URL}/api/pipeline/rate-limit-status", headers=headers) as resp:
            status = await resp.json()
            if status.get("can_create"):
                break
            print(f"  V{index}: Waiting for slot (concurrent={status.get('concurrent')})...")
            await asyncio.sleep(10)

    async with session.post(f"{API_URL}/api/pipeline/create", headers=headers, json=video_data) as resp:
        data = await resp.json()
        if data.get("success"):
            job_id = data["job_id"]
            print(f"  V{index}: Created job {job_id[:8]}... ({video_data['title']})")
            # Poll for completion
            for _ in range(60):
                await asyncio.sleep(5)
                async with session.get(f"{API_URL}/api/pipeline/status/{job_id}", headers=headers) as status_resp:
                    status_data = await status_resp.json()
                    job = status_data.get("job", {})
                    s = job.get("status", "")
                    if s == "COMPLETED":
                        print(f"  V{index}: COMPLETED - {video_data['title']}")
                        return True
                    elif s == "FAILED":
                        print(f"  V{index}: FAILED - {job.get('error','')}")
                        return False
            print(f"  V{index}: TIMEOUT")
            return False
        else:
            print(f"  V{index}: Create failed - {data}")
            return False

async def main():
    print(f"\n{'='*60}")
    print(f"  BATCH VIDEO GENERATION: {len(VIDEOS)} videos")
    print(f"  Target: {API_URL}")
    print(f"{'='*60}\n")

    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=600)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        token = await login(session)
        if not token:
            print("Login failed!")
            return

        results = {"completed": 0, "failed": 0}
        # Run 3 at a time
        for batch_start in range(0, len(VIDEOS), 3):
            batch = VIDEOS[batch_start:batch_start+3]
            tasks = [create_video(session, token, v, batch_start + i + 4) for i, v in enumerate(batch)]
            batch_results = await asyncio.gather(*tasks)
            for r in batch_results:
                if r:
                    results["completed"] += 1
                else:
                    results["failed"] += 1

    print(f"\n{'='*60}")
    print(f"  RESULTS: {results['completed']} completed, {results['failed']} failed")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(main())
