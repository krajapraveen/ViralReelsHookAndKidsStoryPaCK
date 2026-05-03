"""One-shot seed: download Mozilla CC0 sample MP4s and push them to our R2
bucket so we never depend on external CDNs for the avatar demo.

Run:  cd /app/backend && python scripts/seed_avatar_demo_r2.py

Idempotent — re-runs overwrite the same keys.
"""
import asyncio
import io
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

SAMPLES = {
    "talking_head": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    "gesture":      "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/friday.mp4",
    "full_body":    "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    "static":       "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
}


async def main():
    from services.cloudflare_r2_storage import get_r2_storage
    r2 = get_r2_storage()
    if not r2.is_configured:
        print("R2 not configured — aborting.")
        return 1

    results = {}
    seen_urls = {}
    for motion, url in SAMPLES.items():
        if url in seen_urls:
            results[motion] = seen_urls[url]
            print(f"[{motion}] → reuse {seen_urls[url]}")
            continue
        print(f"[{motion}] downloading {url} ...")
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
        print(f"[{motion}] got {len(data)} bytes, uploading to R2 ...")
        key = f"avatar_demo_samples/{motion}.mp4"
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            ok, pub_url, _ = await r2.upload_file_multipart(
                tmp_path, "video", "avatar_demo", f"{motion}.mp4",
            )
        finally:
            os.unlink(tmp_path)
        if not ok or not pub_url:
            print(f"[{motion}] UPLOAD FAILED")
            return 2
        results[motion] = pub_url
        seen_urls[url] = pub_url
        print(f"[{motion}] → {pub_url}")

    print("\nDone. Paste into avatar_studio.py DEMO_OUTPUT_URLS:")
    for k, v in results.items():
        print(f'    "{k}": "{v}",')
    return 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
