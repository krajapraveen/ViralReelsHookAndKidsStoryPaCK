"""
Image generation benchmark — test different size/quality configurations.
Measures actual wall-clock time per image to find the fastest path.
"""
import asyncio
import os
import time
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from services.image_gen_direct import generate_image_direct

API_KEY = os.environ.get("EMERGENT_LLM_KEY")
if not API_KEY:
    print("ERROR: EMERGENT_LLM_KEY not set")
    exit(1)

TEST_PROMPT = "A brave little firefly glowing brightly in a dark enchanted forest at night, cartoon style, vibrant colors, magical atmosphere"

CONFIGS = [
    {"label": "baseline (no size)", "quality": "low", "size": None},
    {"label": "1024x1024 explicit", "quality": "low", "size": "1024x1024"},
    {"label": "auto size", "quality": "low", "size": "auto"},
    {"label": "1024x1024 medium quality", "quality": "medium", "size": "1024x1024"},
]


async def benchmark():
    print(f"API Key: {API_KEY[:20]}...")
    print(f"Prompt: {TEST_PROMPT[:60]}...")
    print(f"Model: gpt-image-1")
    print(f"Running {len(CONFIGS)} configurations...\n")

    results = []

    for cfg in CONFIGS:
        label = cfg["label"]
        print(f"--- Testing: {label} ---")
        t0 = time.time()
        try:
            imgs = await generate_image_direct(
                api_key=API_KEY,
                prompt=TEST_PROMPT,
                model="gpt-image-1",
                quality=cfg["quality"],
                size=cfg["size"],
                n=1,
            )
            elapsed = time.time() - t0
            img_size_kb = len(imgs[0]) / 1024 if imgs else 0
            results.append({
                "label": label,
                "time_sec": round(elapsed, 2),
                "img_size_kb": round(img_size_kb, 1),
                "success": True,
            })
            print(f"  Time: {elapsed:.2f}s | Image: {img_size_kb:.1f} KB | SUCCESS")
        except Exception as e:
            elapsed = time.time() - t0
            results.append({
                "label": label,
                "time_sec": round(elapsed, 2),
                "error": str(e)[:100],
                "success": False,
            })
            print(f"  Time: {elapsed:.2f}s | ERROR: {e}")
        print()

    # Summary
    print("=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    for r in results:
        status = "OK" if r["success"] else "FAIL"
        time_str = f"{r['time_sec']}s"
        size_str = f"{r.get('img_size_kb', 0)}KB" if r["success"] else r.get("error", "")[:50]
        print(f"  {r['label']:30s} | {time_str:8s} | {size_str} | {status}")

    # Find fastest
    ok_results = [r for r in results if r["success"]]
    if ok_results:
        fastest = min(ok_results, key=lambda x: x["time_sec"])
        print(f"\n  FASTEST: {fastest['label']} at {fastest['time_sec']}s")
        baseline = next((r for r in ok_results if "baseline" in r["label"]), None)
        if baseline and fastest["label"] != baseline["label"]:
            improvement = ((baseline["time_sec"] - fastest["time_sec"]) / baseline["time_sec"]) * 100
            print(f"  vs baseline: {improvement:.1f}% faster")


if __name__ == "__main__":
    asyncio.run(benchmark())
