"""
Stress Test Script for Visionary Suite
Simulates concurrent user flows: signup → generate video → check status
"""
import asyncio
import time
import random
import string
import json
import aiohttp
import sys

API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
CONCURRENT_USERS = int(sys.argv[2]) if len(sys.argv) > 2 else 5

STORIES = [
    "A brave little fox discovers a hidden garden behind the old oak tree. Inside, magical flowers that glow at night teach the fox about the secrets of the forest. The fox shares this knowledge with all the animals, becoming a wise guardian of the enchanted garden.",
    "In a world where clouds are made of cotton candy, a young bird named Sky learns to fly by eating the clouds. Each cloud gives Sky a new ability: speed, strength, or the power to sing songs that make the sun shine brighter and paint rainbows across the sky.",
    "A tiny robot named Bolt wakes up in a junkyard and discovers it can make flowers grow from metal scraps. Bolt creates a beautiful garden that brings joy to the entire city. The mayor declares Bolt the official city gardener, and everyone celebrates the mechanical miracle.",
    "Deep in the ocean, a seahorse named Luna discovers a sunken treasure chest filled with glowing pearls. Each pearl contains a memory from an ancient civilization. Luna becomes the keeper of these memories, sharing stories of the old world with all sea creatures.",
    "On a snowy mountain peak, a baby penguin named Frost discovers it can paint pictures in the ice. The paintings come alive at night, dancing under the northern lights. All the animals travel far to see Frost's magical ice gallery high on the mountain.",
]

ANIMATION_STYLES = ["cartoon_2d", "anime_style", "3d_pixar", "watercolor", "comic_book", "claymation"]

results = {
    "total_users": CONCURRENT_USERS,
    "signups": {"success": 0, "failed": 0, "avg_time_ms": 0},
    "video_generations": {"success": 0, "failed": 0, "rate_limited": 0, "avg_time_ms": 0},
    "status_checks": {"success": 0, "failed": 0, "avg_time_ms": 0},
    "errors": [],
    "timings": [],
}


def random_email():
    return f"stress_{random.randint(10000,99999)}_{int(time.time())}@test.com"


async def simulate_user(session, user_num):
    """Simulate a single user flow."""
    user_result = {"user": user_num, "steps": {}}
    email = random_email()
    # Use pre-existing test user to avoid IP signup rate limits
    email = "test@visionary-suite.com"
    password = "Test@2026#"
    token = None

    # Step 1: Login
    t0 = time.time()
    try:
        async with session.post(f"{API_URL}/api/auth/login", json={
            "email": email,
            "password": password,
        }) as resp:
            data = await resp.json()
            elapsed = (time.time() - t0) * 1000
            if resp.status == 200 and data.get("token"):
                token = data["token"]
                results["signups"]["success"] += 1
                user_result["steps"]["login"] = {"status": "ok", "ms": round(elapsed)}
            else:
                results["signups"]["failed"] += 1
                user_result["steps"]["login"] = {"status": "fail", "ms": round(elapsed), "error": str(data)}
    except Exception as e:
        results["signups"]["failed"] += 1
        user_result["steps"]["login"] = {"status": "error", "error": str(e)}

    if not token:
        results["timings"].append(user_result)
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Create video
    story = random.choice(STORIES)
    style = random.choice(ANIMATION_STYLES)
    t0 = time.time()
    job_id = None
    try:
        async with session.post(f"{API_URL}/api/pipeline/create", json={
            "title": f"Stress Test Video {user_num}",
            "story_text": story,
            "animation_style": style,
        }, headers=headers) as resp:
            data = await resp.json()
            elapsed = (time.time() - t0) * 1000
            if resp.status == 200 and data.get("success"):
                job_id = data.get("job_id")
                results["video_generations"]["success"] += 1
                user_result["steps"]["create_video"] = {"status": "ok", "ms": round(elapsed), "job_id": job_id, "credits": data.get("credits_charged")}
            elif resp.status == 429:
                results["video_generations"]["rate_limited"] += 1
                user_result["steps"]["create_video"] = {"status": "rate_limited", "ms": round(elapsed)}
            else:
                results["video_generations"]["failed"] += 1
                user_result["steps"]["create_video"] = {"status": "fail", "ms": round(elapsed), "error": str(data)}
    except Exception as e:
        results["video_generations"]["failed"] += 1
        user_result["steps"]["create_video"] = {"status": "error", "error": str(e)}

    if not job_id:
        results["timings"].append(user_result)
        return

    # Step 3: Poll status (max 5 checks)
    for poll_i in range(5):
        await asyncio.sleep(3)
        t0 = time.time()
        try:
            async with session.get(f"{API_URL}/api/pipeline/status/{job_id}", headers=headers) as resp:
                data = await resp.json()
                elapsed = (time.time() - t0) * 1000
                job_data = data.get("job", {})
                status = job_data.get("status", "UNKNOWN")
                results["status_checks"]["success"] += 1
                user_result["steps"][f"poll_{poll_i}"] = {"status": status, "ms": round(elapsed), "progress": job_data.get("progress", 0)}
                if status in ("COMPLETED", "FAILED"):
                    break
        except Exception as e:
            results["status_checks"]["failed"] += 1
            user_result["steps"][f"poll_{poll_i}"] = {"status": "error", "error": str(e)}

    results["timings"].append(user_result)


async def run_stress_test():
    print(f"\n{'='*60}")
    print(f"  STRESS TEST: {CONCURRENT_USERS} concurrent users")
    print(f"  Target: {API_URL}")
    print(f"{'='*60}\n")

    connector = aiohttp.TCPConnector(limit=50)
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        start = time.time()
        tasks = [simulate_user(session, i) for i in range(CONCURRENT_USERS)]
        await asyncio.gather(*tasks)
        total_time = time.time() - start

    results["total_time_s"] = round(total_time, 1)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  Total time: {results['total_time_s']}s")
    print(f"  Signups: {results['signups']['success']} OK, {results['signups']['failed']} FAIL")
    print(f"  Videos:  {results['video_generations']['success']} OK, {results['video_generations']['failed']} FAIL, {results['video_generations']['rate_limited']} RATE LIMITED")
    print(f"  Polls:   {results['status_checks']['success']} OK, {results['status_checks']['failed']} FAIL")
    print(f"{'='*60}\n")

    # Save report
    report_path = f"/app/test_reports/stress_test_{CONCURRENT_USERS}_users.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Full report saved to: {report_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_stress_test())
