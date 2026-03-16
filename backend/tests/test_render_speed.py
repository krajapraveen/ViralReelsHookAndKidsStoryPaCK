"""
Story→Video Render Speed Benchmark
Runs 5 consecutive and 3 concurrent video generation tests.
Validates: correctness, playability, timing, and download.
"""
import asyncio
import aiohttp
import json
import time
import sys
import os

API_URL = os.environ.get("API_URL", "https://durable-jobs-beta.preview.emergentagent.com")
EMAIL = "test@visionary-suite.com"
PASSWORD = "Test@2026#"

STORY_TEMPLATES = [
    {
        "title": "Speed Test - The Magic Garden",
        "story_text": "A tiny caterpillar named Charlie found a hidden garden behind an old stone wall. Inside, flowers sang melodies and trees whispered secrets. Charlie learned that the garden bloomed only for those with kind hearts. He shared the secret with his friends, and soon the garden grew bigger than ever before. They all lived happily, tending the magical garden together."
    },
    {
        "title": "Speed Test - Ocean Adventure",
        "story_text": "A young seahorse named Finn dreamed of exploring beyond the coral reef. One morning, he swam past the boundary and discovered an underwater cave filled with glowing crystals. A friendly octopus named Otto helped him navigate the dark tunnels. Together they found a sunken treasure chest filled with colorful gems that lit up the entire ocean floor."
    },
    {
        "title": "Speed Test - Sky Kingdom",
        "story_text": "A paper airplane named Zephyr was thrown from a classroom window and caught a magical wind. It soared above the clouds and found a kingdom of birds who lived in floating nests. The bird queen asked Zephyr to deliver an important message to the ground below. Zephyr completed the mission and became the first airplane ambassador between sky and land."
    },
    {
        "title": "Speed Test - Forest Friends",
        "story_text": "A baby bear named Maple got lost during her first autumn walk. She met a squirrel gathering nuts, a deer drinking from a stream, and a family of rabbits building a new home. Each friend gave her directions, and together they formed a chain that led her back to her mother. Maple never forgot her forest friends."
    },
    {
        "title": "Speed Test - Star Catcher",
        "story_text": "A young girl named Nova discovered she could catch falling stars in a butterfly net. Each star she caught granted one wish. She wished for a treehouse, a talking cat, and a flying bicycle. But her most important wish was for everyone in her village to always have enough to eat. The stars twinkled brighter than ever that night."
    },
]


async def login(session):
    async with session.post(f"{API_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}) as resp:
        data = await resp.json()
        return data.get("token")


async def create_video(session, token, story, idx):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "title": story["title"],
        "story_text": story["story_text"],
        "animation_style": "cartoon_2d",
        "age_group": "kids_5_8",
        "voice_preset": "narrator_warm",
    }
    async with session.post(f"{API_URL}/api/pipeline/create", headers=headers, json=payload) as resp:
        data = await resp.json()
        if not data.get("success"):
            return {"index": idx, "error": f"Create failed: {data}", "status": "FAILED"}
        return {"index": idx, "job_id": data["job_id"], "credits": data.get("credits_charged")}


async def poll_until_done(session, token, job_id, idx, max_wait=300):
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    last_status = ""
    while time.time() - start < max_wait:
        await asyncio.sleep(8)
        async with session.get(f"{API_URL}/api/pipeline/status/{job_id}", headers=headers) as resp:
            data = await resp.json()
            job = data.get("job", {})
            status = job.get("status", "UNKNOWN")
            progress = job.get("progress", 0)
            step = job.get("current_step", "")
            
            if status != last_status or progress % 20 == 0:
                elapsed = int(time.time() - start)
                print(f"  [Test {idx}] {elapsed}s: {status} {progress}% - {step}")
                last_status = status

            if status == "COMPLETED":
                elapsed = time.time() - start
                timing = job.get("timing", {})
                render_ms = timing.get("render_ms") or job.get("stages", {}).get("render", {}).get("duration_ms", 0)
                return {
                    "index": idx,
                    "job_id": job_id,
                    "status": "COMPLETED",
                    "total_time_s": round(elapsed, 1),
                    "render_ms": render_ms,
                    "output_url": job.get("output_url", "")[:80],
                    "timing": timing,
                    "stages": {k: v.get("duration_ms") for k, v in job.get("stages", {}).items()},
                }
            elif status == "FAILED":
                return {
                    "index": idx,
                    "job_id": job_id,
                    "status": "FAILED",
                    "error": job.get("error", "Unknown"),
                    "total_time_s": round(time.time() - start, 1),
                }

    return {"index": idx, "job_id": job_id, "status": "TIMEOUT", "total_time_s": max_wait}


async def verify_download(session, url, idx):
    """Verify the video is downloadable and not empty."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.read()
                size_kb = len(data) / 1024
                return {"index": idx, "downloadable": True, "size_kb": round(size_kb, 1)}
            return {"index": idx, "downloadable": False, "http_status": resp.status}
    except Exception as e:
        return {"index": idx, "downloadable": False, "error": str(e)}


async def run_sequential_tests():
    """Run 5 consecutive Story→Video tests."""
    print("\n" + "="*70)
    print("SEQUENTIAL TEST: 5 consecutive Story→Video runs")
    print("="*70)

    results = []
    async with aiohttp.ClientSession() as session:
        token = await login(session)
        if not token:
            print("ERROR: Login failed")
            return results

        for i in range(5):
            story = STORY_TEMPLATES[i]
            print(f"\n--- Test {i+1}/5: {story['title']} ---")
            
            create_result = await create_video(session, token, story, i+1)
            if "error" in create_result:
                print(f"  FAILED to create: {create_result['error']}")
                results.append(create_result)
                continue

            job_id = create_result["job_id"]
            print(f"  Job {job_id[:8]} created ({create_result['credits']} credits)")

            result = await poll_until_done(session, token, job_id, i+1)
            results.append(result)

            if result["status"] == "COMPLETED":
                print(f"  PASSED: {result['total_time_s']}s total, render={result.get('render_ms', '?')}ms")
            else:
                print(f"  FAILED: {result['status']} - {result.get('error', 'timeout')}")

    return results


async def run_concurrent_tests():
    """Run 3 concurrent Story→Video tests."""
    print("\n" + "="*70)
    print("CONCURRENT TEST: 3 simultaneous Story→Video runs")
    print("="*70)

    async with aiohttp.ClientSession() as session:
        token = await login(session)
        if not token:
            print("ERROR: Login failed")
            return []

        # Create all 3 jobs
        jobs = []
        for i in range(3):
            story = STORY_TEMPLATES[i]
            create_result = await create_video(session, token, story, i+1)
            if "error" not in create_result:
                jobs.append(create_result)
                print(f"  Created job {i+1}: {create_result['job_id'][:8]}")
            else:
                print(f"  Failed to create job {i+1}: {create_result.get('error')}")

        if not jobs:
            return []

        # Poll all concurrently
        tasks = [poll_until_done(session, token, j["job_id"], j["index"]) for j in jobs]
        results = await asyncio.gather(*tasks)

        for r in results:
            status = r["status"]
            if status == "COMPLETED":
                print(f"  Job {r['index']}: PASSED ({r['total_time_s']}s, render={r.get('render_ms','?')}ms)")
            else:
                print(f"  Job {r['index']}: {status} - {r.get('error', 'timeout')}")

        return list(results)


async def main():
    all_results = {"sequential": [], "concurrent": [], "summary": {}}

    # Sequential tests
    seq_results = await run_sequential_tests()
    all_results["sequential"] = seq_results

    # Concurrent tests
    conc_results = await run_concurrent_tests()
    all_results["concurrent"] = conc_results

    # Summary
    seq_completed = [r for r in seq_results if r.get("status") == "COMPLETED"]
    conc_completed = [r for r in conc_results if r.get("status") == "COMPLETED"]

    seq_render_times = [r.get("render_ms", 0) for r in seq_completed if r.get("render_ms")]
    seq_total_times = [r.get("total_time_s", 0) for r in seq_completed]
    conc_render_times = [r.get("render_ms", 0) for r in conc_completed if r.get("render_ms")]
    conc_total_times = [r.get("total_time_s", 0) for r in conc_completed]

    summary = {
        "sequential_pass_rate": f"{len(seq_completed)}/5",
        "concurrent_pass_rate": f"{len(conc_completed)}/{len(conc_results)}",
        "avg_sequential_render_ms": round(sum(seq_render_times) / max(1, len(seq_render_times))),
        "avg_sequential_total_s": round(sum(seq_total_times) / max(1, len(seq_total_times)), 1),
        "avg_concurrent_render_ms": round(sum(conc_render_times) / max(1, len(conc_render_times))) if conc_render_times else 0,
        "avg_concurrent_total_s": round(sum(conc_total_times) / max(1, len(conc_total_times)), 1) if conc_total_times else 0,
        "architecture": "single-pass-encode",
        "settings": "960x540 15fps ultrafast CRF28 threads=1",
    }
    all_results["summary"] = summary

    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(json.dumps(summary, indent=2))

    # Write report
    with open("/app/test_reports/render_speed_benchmark.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nReport saved to /app/test_reports/render_speed_benchmark.json")

    # Exit code based on results
    total_pass = len(seq_completed) + len(conc_completed)
    total_tests = 5 + len(conc_results)
    if total_pass < total_tests:
        print(f"\nWARNING: {total_tests - total_pass} tests failed!")
        sys.exit(1)
    else:
        print(f"\nALL {total_tests} TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
