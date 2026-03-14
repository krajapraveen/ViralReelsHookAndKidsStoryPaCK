"""Generate 5 reel scripts."""
import asyncio, aiohttp, json, sys
API_URL = sys.argv[1]

REELS = [
    {"topic":"5 signs AI will replace your content strategy in 2026","niche":"Technology","tone":"Bold","duration":"30s","goal":"Followers"},
    {"topic":"How to create viral story videos using AI in 60 seconds","niche":"Content Creation","tone":"Excited","duration":"30s","goal":"Engagement"},
    {"topic":"The secret to growing your Instagram to 10K followers fast","niche":"Social Media","tone":"Inspiring","duration":"60s","goal":"Followers"},
    {"topic":"Why bedtime story videos are the next big thing on YouTube","niche":"Parenting","tone":"Casual","duration":"30s","goal":"Subscribers"},
    {"topic":"3 AI tools every content creator needs right now","niche":"Creator Economy","tone":"Bold","duration":"15s","goal":"Engagement"},
]

async def main():
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as s:
        token_resp = await (await s.post(f"{API_URL}/api/auth/login", json={"email":"test@visionary-suite.com","password":"Test@2026#"})).json()
        token = token_resp.get("token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        for i, reel in enumerate(REELS):
            try:
                resp = await s.post(f"{API_URL}/api/generate/reel", headers=headers, json=reel)
                d = await resp.json()
                print(f"Reel {i+1}: success={d.get('success')} topic={reel['topic'][:50]}")
            except Exception as e:
                print(f"Reel {i+1}: ERROR {e}")

asyncio.run(main())
