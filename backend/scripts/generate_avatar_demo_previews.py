"""Generate self-hosted 'simulated talking-head preview' demo videos.

Phase-1 illusion: no real AI. Abstract avatar silhouette + rotating
subtitle panels + big SIMULATED PREVIEW header. Clearly a preview of the
user's upcoming avatar — not a random flower.

Strategy:
  1. Pillow renders a base PNG (background + glow + silhouette + banners)
     and one subtitle PNG per line.
  2. ffmpeg composites:  base.png * DURATION → overlay subtitle PNGs
     during their time slice → H.264 baseline MP4 with AAC silence.

Output: 4 variants (one per motion_style) to R2.

Run:  cd /app/backend && python scripts/generate_avatar_demo_previews.py
"""
import asyncio
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

WIDTH, HEIGHT = 720, 1280
DURATION = 18
FPS = 30
FONT_BOLD_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG_PATH  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

VARIANTS = {
    "talking_head": {
        "accent": (139, 92, 246),    # violet
        "lines": [
            "Hi — this is your AI avatar preview.",
            "In the full version, this will be",
            "YOUR face speaking in YOUR voice.",
            "For now, enjoy the simulation.",
        ],
    },
    "gesture": {
        "accent": (236, 72, 153),    # pink
        "lines": [
            "Preview of your AI avatar.",
            "Gestures + body language will match",
            "your real movements in Phase 2.",
            "This is a simulated placeholder.",
        ],
    },
    "full_body": {
        "accent": (6, 182, 212),     # cyan
        "lines": [
            "Full-body avatar preview.",
            "Your walk and posture will be",
            "rendered from your video soon.",
            "Simulated output for now.",
        ],
    },
    "static": {
        "accent": (16, 185, 129),    # emerald
        "lines": [
            "Simulated preview of your avatar.",
            "Your real photo comes alive with",
            "cloned audio in the full version.",
            "Demo / simulated output.",
        ],
    },
}


def _fit_text(draw, text, font, max_w):
    """Shrink font if text wider than max_w."""
    size = font.size
    while size > 18:
        f = ImageFont.truetype(FONT_BOLD_PATH, size)
        w = draw.textlength(text, font=f)
        if w <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(FONT_BOLD_PATH, 18)


def render_base(accent: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (10, 11, 20))
    draw = ImageDraw.Draw(img, "RGBA")

    # Radial glow (3 concentric, largest first)
    cx, cy = WIDTH // 2, HEIGHT // 2 - 80
    for r, alpha in [(340, 40), (240, 70), (170, 130)]:
        draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                     fill=(*accent, alpha))

    # Apply a soft blur for the glow feel
    img = img.filter(ImageFilter.GaussianBlur(radius=18))

    draw = ImageDraw.Draw(img, "RGBA")
    # Silhouette: solid accent circle
    draw.ellipse((cx - 110, cy - 110, cx + 110, cy + 110), fill=(*accent, 220))
    # Inner highlight
    draw.ellipse((cx - 60, cy - 70, cx + 60, cy + 10), fill=(255, 255, 255, 40))

    # Top SIMULATED PREVIEW banner
    draw.rectangle((0, 60, WIDTH, 140), fill=(0, 0, 0, 140))
    font = ImageFont.truetype(FONT_BOLD_PATH, 34)
    t = "SIMULATED PREVIEW"
    w = draw.textlength(t, font=font)
    draw.text(((WIDTH - w) / 2, 80), t, fill=(251, 191, 36), font=font)

    # Demo chip
    chip_w = 360
    draw.rectangle(((WIDTH - chip_w) / 2, 160,
                    (WIDTH + chip_w) / 2, 210), fill=(251, 191, 36, 46))
    font = ImageFont.truetype(FONT_BOLD_PATH, 20)
    t = "DEMO / SIMULATED OUTPUT"
    w = draw.textlength(t, font=font)
    draw.text(((WIDTH - w) / 2, 175), t, fill=(253, 230, 138), font=font)

    # Bottom caption
    font = ImageFont.truetype(FONT_REG_PATH, 20)
    t = "AI-generated avatar · forensic watermark"
    w = draw.textlength(t, font=font)
    draw.text(((WIDTH - w) / 2, HEIGHT - 100), t, fill=(148, 163, 184), font=font)

    return img


def render_subtitle(text: str) -> Image.Image:
    """One subtitle panel — transparent PNG sized for overlay near bottom."""
    img = Image.new("RGBA", (WIDTH, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_BOLD_PATH, 38)
    font = _fit_text(draw, text, font, WIDTH - 120)
    w = draw.textlength(text, font=font)
    bbox_h = font.size + 36
    box_w = int(w + 60)
    box_x = (WIDTH - box_w) / 2
    box_y = (160 - bbox_h) / 2
    # Shadow + box
    draw.rectangle((box_x, box_y, box_x + box_w, box_y + bbox_h),
                   fill=(0, 0, 0, 170))
    tx = (WIDTH - w) / 2
    ty = box_y + 12
    draw.text((tx, ty), text, fill=(255, 255, 255), font=font)
    return img


def generate(out_path: str, accent: tuple, lines: list[str], workdir: str):
    base_path = os.path.join(workdir, "base.png")
    render_base(accent).save(base_path)

    sub_paths = []
    for i, line in enumerate(lines):
        p = os.path.join(workdir, f"sub_{i}.png")
        render_subtitle(line).save(p)
        sub_paths.append(p)

    per = DURATION / len(lines)
    # ffmpeg: input 0 = base image (looped), input 1 = silence audio,
    #         inputs 2..N = subtitle PNGs
    inputs = [
        "-loop", "1", "-t", str(DURATION), "-i", base_path,
        "-f", "lavfi", "-t", str(DURATION), "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=44100",
    ]
    for p in sub_paths:
        inputs += ["-loop", "1", "-t", str(DURATION), "-i", p]

    # Build filter chain:
    #   [0:v] pass → [v0]
    #   [v0][2:v] overlay y=h-300 enable=... → [v1]
    #   ...
    sub_y = HEIGHT - 260  # near bottom but above caption
    chain = []
    cur = "[0:v]setpts=PTS-STARTPTS[v0]"
    chain.append(cur)
    for i in range(len(sub_paths)):
        start = i * per
        end = (i + 1) * per
        src = f"[{i+2}:v]"
        prev = f"[v{i}]"
        nxt  = f"[v{i+1}]"
        chain.append(
            f"{prev}{src}overlay=x=(W-w)/2:y={sub_y}:"
            f"enable='between(t\\,{start:.2f}\\,{end:.2f})'{nxt}"
        )
    final_label = f"[v{len(sub_paths)}]"
    # Ensure yuv420p
    chain.append(f"{final_label}format=yuv420p[out]")
    fc = ";".join(chain)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        *inputs,
        "-filter_complex", fc,
        "-map", "[out]", "-map", "1:a",
        "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-r", str(FPS),
        "-c:a", "aac", "-b:a", "96k", "-ar", "44100",
        "-shortest", out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-1800:])
        raise SystemExit("ffmpeg failed")
    print(f"    ✔ {os.path.getsize(out_path) / 1024:.0f} KB")


async def main():
    from services.cloudflare_r2_storage import get_r2_storage
    r2 = get_r2_storage()
    if not r2.is_configured:
        print("R2 not configured — aborting.")
        return 1

    urls = {}
    with tempfile.TemporaryDirectory() as td:
        for motion, cfg in VARIANTS.items():
            print(f"[{motion}] accent=rgb{cfg['accent']}")
            out = os.path.join(td, f"{motion}.mp4")
            generate(out, cfg["accent"], cfg["lines"], td)
            ok, pub_url, _ = await r2.upload_file_multipart(
                out, "video", "avatar_demo_v2", f"{motion}.mp4",
            )
            if not ok or not pub_url:
                print(f"[{motion}] UPLOAD FAILED")
                return 2
            urls[motion] = pub_url
            print(f"[{motion}] → {pub_url}")

    print("\n=== Paste into avatar_studio.py DEMO_OUTPUT_URLS ===")
    for k, v in urls.items():
        print(f'    "{k}": "{v}",')
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
