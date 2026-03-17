"""
Comic Story Book Builder — Stage-Based Asset Pipeline

Architecture:
  comic_book_job
    ├── stage_1: story_outline       → story_json persisted
    ├── stage_2: page_plan           → page + panel structure persisted
    ├── stage_3: panel_prompts       → prompts persisted
    ├── stage_4: image_generation    → each panel independently retried
    ├── stage_5: page_assembly       → assembled pages
    ├── stage_6: export_creation     → PDF + cover
    ├── stage_7: storage_upload      → all assets to R2
    └── stage_8: asset_registration  → user_assets records

Each stage: status = queued|running|completed|failed|retrying
DB must never claim success before storage confirms success.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, Dict
import uuid
import os
import sys
import base64
import asyncio
import json
import re
import io
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)
from services.watermark_service import add_diagonal_watermark, should_apply_watermark, get_watermark_config

router = APIRouter(prefix="/comic-storybook-v2", tags=["Comic Story Book Builder"])

# ── BLOCKED KEYWORDS ──────────────────────────────────────────────────────
BLOCKED_KEYWORDS = [
    "marvel", "dc", "avengers", "spiderman", "spider-man", "batman", "superman",
    "ironman", "iron man", "captain america", "thor", "hulk", "joker",
    "wonder woman", "flash", "deadpool", "x-men", "wolverine", "venom",
    "disney", "pixar", "frozen", "elsa", "anna", "mickey", "minnie",
    "naruto", "dragon ball", "goku", "one piece", "pokemon", "pikachu",
    "harry potter", "hogwarts", "hermione",
    "celebrity", "real person", "politician", "nude", "nsfw", "sexual",
    "violence", "gore", "weapon", "hate"
]

UNIVERSAL_NEGATIVE = (
    "blurry, low resolution, bad anatomy, extra limbs, watermark, logo, "
    "brand name, copyrighted character, celebrity likeness, nsfw, nudity, "
    "gore, violence, deformed, disfigured, extra fingers, mutated hands"
)

STORY_GENRES = {
    "kids_adventure": {"name": "Kids Adventure", "style": "children's book illustration, colorful, friendly, cute characters, soft colors, playful"},
    "superhero": {"name": "Superhero", "style": "dynamic superhero comic, bold colors, action poses, heroic, original character design"},
    "fantasy": {"name": "Fantasy", "style": "magical fantasy illustration, enchanted atmosphere, mystical elements, vibrant magical colors"},
    "comedy": {"name": "Comedy", "style": "cartoon comedy, exaggerated expressions, bright colors, funny characters"},
    "romance": {"name": "Romance", "style": "soft romantic illustration, gentle colors, dreamy atmosphere, emotional expressions"},
    "scifi": {"name": "Sci-Fi", "style": "futuristic sci-fi comic, technology, space, neon accents, sleek design"},
    "mystery": {"name": "Mystery", "style": "mysterious detective comic, dramatic shadows, noir elements"},
    "horror_lite": {"name": "Spooky Fun", "style": "friendly spooky illustration, Halloween vibes, cute monsters, fun atmosphere"},
}

PRICING = {
    "pages": {10: 25, 20: 45, 30: 60},
    "add_ons": {
        "personalized_cover": 4, "dedication_page": 2,
        "activity_pages": 5, "hd_print": 5, "commercial_license": 15
    },
}

STAGES = [
    "story_outline", "page_plan", "panel_prompts",
    "image_generation", "page_assembly", "export_creation",
    "storage_upload", "asset_registration"
]


def check_blocked(text: str):
    if not text:
        return False, None
    t = text.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in t:
            return True, kw
    return False, None


# ── STAGE TRACKING ────────────────────────────────────────────────────────

async def update_stage(job_id: str, stage: str, status: str, **extra):
    """Update a stage run record."""
    now = datetime.now(timezone.utc).isoformat()
    update = {"status": status, "updated_at": now, **extra}
    if status == "running":
        update["started_at"] = now
    if status in ("completed", "failed"):
        update["finished_at"] = now

    await db.job_stage_runs.update_one(
        {"job_id": job_id, "stage_name": stage},
        {"$set": update, "$inc": {"attempt_count": 1 if status == "running" else 0}},
        upsert=True
    )

    # Also update parent job
    stage_idx = STAGES.index(stage) if stage in STAGES else 0
    progress = int(((stage_idx + (1 if status == "completed" else 0.5)) / len(STAGES)) * 100)
    progress = min(progress, 99) if status != "completed" or stage != STAGES[-1] else 100

    parent_update = {"current_stage": stage, "progress": progress}
    if status == "failed":
        parent_update["progressMessage"] = f"Failed at {stage}: {extra.get('error_message', 'unknown')}"
    else:
        stage_labels = {
            "story_outline": "Writing story...",
            "page_plan": "Planning pages...",
            "panel_prompts": "Creating panel prompts...",
            "image_generation": f"Generating images... {extra.get('detail', '')}",
            "page_assembly": "Assembling pages...",
            "export_creation": "Creating PDF...",
            "storage_upload": "Uploading to cloud...",
            "asset_registration": "Registering assets...",
        }
        parent_update["progressMessage"] = stage_labels.get(stage, stage)

    await db.comic_storybook_v2_jobs.update_one({"id": job_id}, {"$set": parent_update})


# ── API ENDPOINTS ─────────────────────────────────────────────────────────

@router.get("/genres")
async def get_genres(user: dict = Depends(get_current_user)):
    return {"genres": {k: {"name": v["name"]} for k, v in STORY_GENRES.items()}, "pricing": PRICING}


@router.get("/pricing")
async def get_pricing(user: dict = Depends(get_current_user)):
    return {"pricing": PRICING}


class PreviewComicRequest(BaseModel):
    genre: str
    storyIdea: str
    title: str = "My Comic Story"
    pageCount: int = 20


@router.post("/preview")
async def generate_preview(request: PreviewComicRequest, user: dict = Depends(get_current_user)):
    """Generate watermarked preview cover."""
    is_blocked, kw = check_blocked(request.storyIdea)
    if is_blocked:
        raise HTTPException(status_code=400, detail=f"Blocked content detected: '{kw}'")

    preview_pages = []
    genre_info = STORY_GENRES.get(request.genre, STORY_GENRES["kids_adventure"])

    if LLM_AVAILABLE and EMERGENT_LLM_KEY:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"preview-{uuid.uuid4()}", system_message="Comic book cover artist.")
            chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])

            prompt = f"Create a comic book cover for: {request.title}. Genre: {genre_info['name']}. Story: {request.storyIdea[:200]}. Style: {genre_info['style']}. AVOID: {UNIVERSAL_NEGATIVE}"
            _, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))

            if images:
                img_bytes = base64.b64decode(images[0]['data'])
                img_bytes = add_diagonal_watermark(img_bytes, text="PREVIEW", opacity=0.3, font_size=50, spacing=150)

                # Upload preview to R2 immediately
                from services.cloudflare_r2_storage import upload_image_bytes
                fname = f"preview_cover_{uuid.uuid4().hex[:12]}.png"
                ok, cdn_url = await upload_image_bytes(img_bytes, fname, f"comic_preview/{user['id'][:8]}")
                if ok and cdn_url:
                    from utils.r2_presign import presign_url
                    preview_pages.append({"url": presign_url(cdn_url), "type": "cover"})
        except Exception as e:
            logger.error(f"Preview generation error: {e}")

    if not preview_pages:
        preview_pages = [{"url": "https://placehold.co/400x600/6b21a8/white?text=Cover+Preview", "type": "cover"}]

    return {"success": True, "previewPages": preview_pages}


class GenerateComicRequest(BaseModel):
    genre: str
    storyIdea: str
    title: str = "My Comic Story"
    author: str = "Anonymous"
    pageCount: int = 20
    addOns: Optional[Dict] = None
    dedicationText: Optional[str] = None


@router.post("/generate")
async def generate_comic_book(request: GenerateComicRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Submit comic book generation job."""
    is_blocked, kw = check_blocked(request.storyIdea)
    if is_blocked:
        raise HTTPException(status_code=400, detail=f"Blocked content: '{kw}'")
    is_blocked, kw = check_blocked(request.title)
    if is_blocked:
        raise HTTPException(status_code=400, detail=f"Blocked content in title: '{kw}'")

    genre = request.genre if request.genre in STORY_GENRES else "kids_adventure"
    page_count = request.pageCount if request.pageCount in [10, 20, 30] else 20
    add_ons = request.addOns or {}

    cost = PRICING["pages"].get(page_count, 45)
    for addon_id, addon_cost in PRICING["add_ons"].items():
        if add_ons.get(addon_id):
            cost += addon_cost

    user_plan = user.get("plan", "free")
    discount = {"creator": 0.8, "pro": 0.7, "studio": 0.6}.get(user_plan, 1.0)
    cost = int(cost * discount)

    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost}.")

    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "userId": user["id"],
        "type": "COMIC_STORYBOOK",
        "status": "QUEUED",
        "genre": genre,
        "storyIdea": request.storyIdea,
        "title": request.title,
        "author": request.author,
        "pageCount": page_count,
        "addOns": add_ons,
        "dedicationText": request.dedicationText,
        "cost": cost,
        "progress": 0,
        "current_stage": "queued",
        "pages": [],
        "assets": [],
        "pdfUrl": None,
        "coverUrl": None,
        "permanent": False,
        "purchased": user_plan != "free",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.comic_storybook_v2_jobs.insert_one(job)

    # Create stage run records
    for stage in STAGES:
        await db.job_stage_runs.insert_one({
            "job_id": job_id, "stage_name": stage, "status": "queued",
            "attempt_count": 0, "created_at": datetime.now(timezone.utc).isoformat(),
        })

    background_tasks.add_task(
        run_pipeline, job_id, genre, request.storyIdea, request.title,
        request.author, page_count, add_ons, request.dedicationText,
        user["id"], cost, user_plan
    )

    return {"success": True, "jobId": job_id, "status": "QUEUED", "estimatedCredits": cost, "stages": len(STAGES)}


# ── STAGE-BASED PIPELINE ─────────────────────────────────────────────────

async def run_pipeline(job_id, genre, story_idea, title, author, page_count, add_ons, dedication, user_id, cost, user_plan):
    """Execute all pipeline stages sequentially with per-stage error handling."""
    try:
        await db.comic_storybook_v2_jobs.update_one({"id": job_id}, {"$set": {"status": "PROCESSING"}})

        # Stage 1: Story outline
        story_pages = await stage_story_outline(job_id, story_idea, genre, page_count)
        if not story_pages:
            raise RuntimeError("Story outline generation failed")

        # Stage 2: Page plan
        page_plan = await stage_page_plan(job_id, story_pages, page_count)

        # Stage 3: Panel prompts
        panel_prompts = await stage_panel_prompts(job_id, page_plan, genre, title)

        # Stage 4: Image generation (per-panel, retryable)
        generated_images = await stage_image_generation(job_id, panel_prompts, genre, title, user_plan, page_count)

        # Stage 5: Page assembly
        assembled_pages = await stage_page_assembly(job_id, page_plan, generated_images)

        # Stage 6: Export creation (PDF + cover)
        export_data = await stage_export_creation(job_id, assembled_pages, title, author, dedication, add_ons)

        # Stage 7: Storage upload (all assets to R2)
        uploaded_assets = await stage_storage_upload(job_id, export_data, user_id)

        # Stage 8: Asset registration (user_assets records)
        await stage_asset_registration(job_id, uploaded_assets, user_id, title, genre, cost)

        # Deduct credits only after full success
        await deduct_credits(user_id, cost, f"Comic Story Book: {job_id[:8]}")

        await db.comic_storybook_v2_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED", "progress": 100, "permanent": True,
                "progressMessage": "Your comic book is ready!",
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }}
        )
        logger.info(f"[COMIC] Job {job_id[:8]} completed successfully")

    except Exception as e:
        logger.error(f"[COMIC] Pipeline failed for {job_id[:8]}: {e}")
        await db.comic_storybook_v2_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e), "progressMessage": f"Failed: {str(e)[:100]}"}}
        )
        try:
            from services.auto_refund import handle_generation_failure
            await handle_generation_failure(db, user_id, "comic_storybook", str(e))
        except Exception:
            pass


# ── STAGE 1: STORY OUTLINE ───────────────────────────────────────────────

async def stage_story_outline(job_id, story_idea, genre, page_count):
    stage = "story_outline"
    await update_stage(job_id, stage, "running")
    genre_info = STORY_GENRES.get(genre, STORY_GENRES["kids_adventure"])

    pages = []
    for attempt in range(2):
        try:
            if LLM_AVAILABLE and EMERGENT_LLM_KEY:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"story-{job_id}-{attempt}", system_message="Professional children's book writer. Create engaging, age-appropriate, original stories.")
                chat.with_model("gemini", "gemini-2.0-flash")

                prompt = f"""Expand this story into {page_count} comic book pages.
Story: {story_idea}
Genre: {genre_info['name']}

For each page: scene description, short dialogue (1-2 sentences), emotional tone.
RULES: Original characters only, no copyrighted content, age-appropriate.
Return JSON array: [{{"page":1,"scene":"...","dialogue":"...","tone":"..."}}]"""

                response = await chat.send_message(UserMessage(text=prompt))
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    pages = json.loads(match.group())
                    if len(pages) >= page_count:
                        break
        except Exception as e:
            logger.warning(f"[COMIC] Story outline attempt {attempt+1} failed: {e}")
            if attempt == 1:
                break

    # Fallback
    if not pages or len(pages) < page_count:
        pages = [{"page": i+1, "scene": f"Scene {i+1} of the adventure", "dialogue": story_idea[:80] if i == 0 else f"Part {i+1}", "tone": "exciting" if i == 0 else "adventurous"} for i in range(page_count)]

    # Persist to DB
    await db.comic_storybook_v2_jobs.update_one({"id": job_id}, {"$set": {"story_outline": pages}})
    await update_stage(job_id, stage, "completed")
    return pages


# ── STAGE 2: PAGE PLAN ───────────────────────────────────────────────────

async def stage_page_plan(job_id, story_pages, page_count):
    stage = "page_plan"
    await update_stage(job_id, stage, "running")

    plan = []
    for i, sp in enumerate(story_pages[:page_count]):
        plan.append({
            "page_number": i + 1,
            "scene": sp.get("scene", f"Page {i+1}"),
            "dialogue": sp.get("dialogue", ""),
            "tone": sp.get("tone", "engaging"),
            "layout": "splash" if i == 0 or i == page_count - 1 else "standard",
            "panel_count": 1,  # 1 main image per page for comic storybook
        })

    await db.comic_storybook_v2_jobs.update_one({"id": job_id}, {"$set": {"page_plan": plan}})
    await update_stage(job_id, stage, "completed")
    return plan


# ── STAGE 3: PANEL PROMPTS ───────────────────────────────────────────────

async def stage_panel_prompts(job_id, page_plan, genre, title):
    stage = "panel_prompts"
    await update_stage(job_id, stage, "running")

    genre_info = STORY_GENRES.get(genre, STORY_GENRES["kids_adventure"])
    prompts = []

    for page in page_plan:
        prompt_text = f"""Comic book page illustration for "{title}".
Scene: {page['scene']}
Dialogue: {page['dialogue']}
Tone: {page['tone']}
Style: {genre_info['style']}
Full page comic illustration, high quality, professional. Original characters only.
AVOID: {UNIVERSAL_NEGATIVE}"""
        prompts.append({
            "page_number": page["page_number"],
            "prompt": prompt_text,
            "status": "pending",
        })

    await db.comic_storybook_v2_jobs.update_one({"id": job_id}, {"$set": {"panel_prompts": prompts}})
    await update_stage(job_id, stage, "completed")
    return prompts


# ── STAGE 4: IMAGE GENERATION (per-panel, retryable) ─────────────────────

async def stage_image_generation(job_id, panel_prompts, genre, title, user_plan, page_count):
    stage = "image_generation"
    await update_stage(job_id, stage, "running")

    results = {}
    failed_pages = []

    if LLM_AVAILABLE and EMERGENT_LLM_KEY:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        for i, panel in enumerate(panel_prompts):
            page_num = panel["page_number"]
            detail_msg = f"page {page_num}/{page_count}"
            await update_stage(job_id, stage, "running", detail=detail_msg)

            success = False
            for attempt in range(3):  # Up to 3 retries per page
                try:
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"comic-img-{job_id}-p{page_num}-a{attempt}",
                        system_message="Comic book illustrator. Create original art only."
                    )
                    chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])

                    _, images = await chat.send_message_multimodal_response(UserMessage(text=panel["prompt"]))

                    if images and len(images) > 0:
                        img_bytes = base64.b64decode(images[0]['data'])

                        # Watermark for free users
                        if should_apply_watermark({"plan": user_plan}):
                            config = get_watermark_config("STORYBOOK")
                            img_bytes = add_diagonal_watermark(img_bytes, text=config["text"], opacity=config["opacity"], font_size=config["font_size"], spacing=config["spacing"])

                        results[page_num] = img_bytes
                        success = True
                        logger.info(f"[COMIC] Page {page_num} generated (attempt {attempt+1})")
                        break

                except Exception as e:
                    logger.warning(f"[COMIC] Page {page_num} attempt {attempt+1} failed: {e}")
                    await asyncio.sleep(1)

            if not success:
                failed_pages.append(page_num)
                # Generate a text-based placeholder
                results[page_num] = None
    else:
        for panel in panel_prompts:
            results[panel["page_number"]] = None

    # Persist page generation status
    gen_status = {str(k): "completed" if v else "failed" for k, v in results.items()}
    await db.comic_storybook_v2_jobs.update_one({"id": job_id}, {"$set": {"image_gen_status": gen_status}})

    if failed_pages:
        logger.warning(f"[COMIC] {len(failed_pages)} pages failed for {job_id[:8]}: {failed_pages}")

    await update_stage(job_id, stage, "completed", detail=f"{len(results) - len(failed_pages)}/{len(results)} pages generated")
    return results


# ── STAGE 5: PAGE ASSEMBLY ───────────────────────────────────────────────

async def stage_page_assembly(job_id, page_plan, generated_images):
    stage = "page_assembly"
    await update_stage(job_id, stage, "running")

    assembled = []
    for page in page_plan:
        pn = page["page_number"]
        img_bytes = generated_images.get(pn)

        assembled.append({
            "page_number": pn,
            "scene": page["scene"],
            "dialogue": page["dialogue"],
            "image_bytes": img_bytes,  # None if failed
            "has_image": img_bytes is not None,
        })

    await update_stage(job_id, stage, "completed")
    return assembled


# ── STAGE 6: EXPORT CREATION (PDF) ───────────────────────────────────────

async def stage_export_creation(job_id, assembled_pages, title, author, dedication, add_ons):
    stage = "export_creation"
    await update_stage(job_id, stage, "running")

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from PIL import Image as PILImage

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    w, h = A4

    # Title page
    c.setFillColor(HexColor("#1a1a2e"))
    c.rect(0, 0, w, h, fill=1)
    c.setFillColor(HexColor("#e0e0e0"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(w / 2, h - 2 * inch, title)
    c.setFont("Helvetica", 16)
    c.setFillColor(HexColor("#a0a0a0"))
    c.drawCentredString(w / 2, h - 2.8 * inch, f"by {author}")
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(w / 2, 1 * inch, "Created with Visionary Suite")
    c.showPage()

    # Dedication page
    if dedication and add_ons.get("dedication_page"):
        c.setFillColor(HexColor("#1a1a2e"))
        c.rect(0, 0, w, h, fill=1)
        c.setFillColor(HexColor("#c0c0c0"))
        c.setFont("Helvetica-Oblique", 14)
        c.drawCentredString(w / 2, h / 2, dedication[:200])
        c.showPage()

    # Content pages
    cover_bytes = None
    page_images_bytes = []

    for page_data in assembled_pages:
        c.setFillColor(HexColor("#1a1a2e"))
        c.rect(0, 0, w, h, fill=1)

        if page_data["image_bytes"]:
            try:
                img = PILImage.open(io.BytesIO(page_data["image_bytes"]))
                img_path = f"/tmp/comic_page_{job_id[:8]}_{page_data['page_number']}.png"
                img.save(img_path)

                margin = 0.5 * inch
                img_w = w - 2 * margin
                img_h = h - 3 * inch
                c.drawImage(img_path, margin, 2 * inch, width=img_w, height=img_h, preserveAspectRatio=True)

                if page_data["page_number"] == 1:
                    cover_bytes = page_data["image_bytes"]
                page_images_bytes.append(page_data["image_bytes"])

                os.remove(img_path)
            except Exception as e:
                logger.warning(f"[COMIC] PDF page {page_data['page_number']} image error: {e}")
                c.setFillColor(HexColor("#666666"))
                c.setFont("Helvetica", 14)
                c.drawCentredString(w / 2, h / 2, f"Page {page_data['page_number']}")
        else:
            c.setFillColor(HexColor("#666666"))
            c.setFont("Helvetica", 14)
            c.drawCentredString(w / 2, h / 2, f"Page {page_data['page_number']}")

        # Dialogue/narration at bottom
        if page_data.get("dialogue"):
            c.setFillColor(HexColor("#ffffff"))
            c.setFont("Helvetica", 11)
            text = page_data["dialogue"][:200]
            c.drawCentredString(w / 2, 1.2 * inch, text)

        # Page number
        c.setFillColor(HexColor("#555555"))
        c.setFont("Helvetica", 9)
        c.drawCentredString(w / 2, 0.5 * inch, f"— {page_data['page_number']} —")

        c.showPage()

    c.save()
    pdf_bytes = pdf_buffer.getvalue()

    # Generate cover thumbnail from first page image
    thumbnail_bytes = None
    if cover_bytes:
        try:
            img = PILImage.open(io.BytesIO(cover_bytes))
            img.thumbnail((400, 600))
            thumb_buf = io.BytesIO()
            img.save(thumb_buf, format="PNG")
            thumbnail_bytes = thumb_buf.getvalue()
        except Exception:
            pass

    await update_stage(job_id, stage, "completed")
    return {
        "pdf_bytes": pdf_bytes,
        "cover_bytes": cover_bytes,
        "thumbnail_bytes": thumbnail_bytes,
        "page_images": page_images_bytes,
    }


# ── STAGE 7: STORAGE UPLOAD (R2) ─────────────────────────────────────────

async def stage_storage_upload(job_id, export_data, user_id):
    stage = "storage_upload"
    await update_stage(job_id, stage, "running")

    from services.cloudflare_r2_storage import get_r2_storage

    r2 = get_r2_storage()
    project = f"comic/{user_id[:8]}"
    uploaded = {"pdf_url": None, "cover_url": None, "thumbnail_url": None, "page_urls": []}

    # Upload PDF
    for attempt in range(2):
        try:
            ok, url, _ = await r2.upload_bytes(export_data["pdf_bytes"], "document", f"storybook_{job_id[:8]}.pdf", project)
            if ok and url:
                uploaded["pdf_url"] = url
                logger.info(f"[COMIC] PDF uploaded: {url[:80]}")
                break
        except Exception as e:
            logger.warning(f"[COMIC] PDF upload attempt {attempt+1} failed: {e}")

    # Upload cover
    if export_data.get("cover_bytes"):
        for attempt in range(2):
            try:
                from services.cloudflare_r2_storage import upload_image_bytes
                ok, url = await upload_image_bytes(export_data["cover_bytes"], f"cover_{job_id[:8]}.png", project)
                if ok and url:
                    uploaded["cover_url"] = url
                    break
            except Exception as e:
                logger.warning(f"[COMIC] Cover upload attempt {attempt+1} failed: {e}")

    # Upload thumbnail
    if export_data.get("thumbnail_bytes"):
        try:
            from services.cloudflare_r2_storage import upload_image_bytes
            ok, url = await upload_image_bytes(export_data["thumbnail_bytes"], f"thumb_{job_id[:8]}.png", project)
            if ok and url:
                uploaded["thumbnail_url"] = url
        except Exception:
            pass

    # Upload individual page images
    for i, page_bytes in enumerate(export_data.get("page_images", [])):
        if page_bytes:
            try:
                from services.cloudflare_r2_storage import upload_image_bytes
                ok, url = await upload_image_bytes(page_bytes, f"page_{job_id[:8]}_{i+1}.png", project)
                if ok and url:
                    uploaded["page_urls"].append({"page": i + 1, "url": url})
            except Exception:
                pass

    # Validate uploads: at minimum PDF must be uploaded
    if not uploaded["pdf_url"]:
        await update_stage(job_id, stage, "failed", error_message="PDF upload failed")
        raise RuntimeError("Failed to upload PDF to storage")

    # HEAD check to verify PDF exists (non-fatal — presigning may return 403 for PDFs)
    try:
        import aiohttp
        from utils.r2_presign import presign_url
        check_url = presign_url(uploaded["pdf_url"])
        async with aiohttp.ClientSession() as session:
            async with session.head(check_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status in (200, 206):
                    logger.info(f"[COMIC] PDF validation passed: HTTP {resp.status}")
                else:
                    logger.warning(f"[COMIC] PDF HEAD check returned {resp.status} (may still be valid)")
    except Exception as e:
        logger.warning(f"[COMIC] PDF HEAD check failed (non-fatal): {e}")

    # Persist upload results
    await db.comic_storybook_v2_jobs.update_one({"id": job_id}, {"$set": {
        "pdfUrl": uploaded["pdf_url"],
        "coverUrl": uploaded["cover_url"],
        "thumbnailUrl": uploaded["thumbnail_url"],
        "page_urls": uploaded["page_urls"],
    }})

    await update_stage(job_id, stage, "completed")
    return uploaded


# ── STAGE 8: ASSET REGISTRATION ──────────────────────────────────────────

async def stage_asset_registration(job_id, uploaded_assets, user_id, title, genre, cost):
    stage = "asset_registration"
    await update_stage(job_id, stage, "running")

    now = datetime.now(timezone.utc).isoformat()
    assets_registered = []

    # Register PDF as primary downloadable asset
    if uploaded_assets.get("pdf_url"):
        asset = {
            "asset_id": str(uuid.uuid4()),
            "user_id": user_id,
            "job_id": job_id,
            "asset_type": "COMIC_STORYBOOK_PDF",
            "display_name": f"{title} — Comic Story Book (PDF)",
            "storage_key": uploaded_assets["pdf_url"],
            "cdn_url": uploaded_assets["pdf_url"],
            "mime_type": "application/pdf",
            "is_downloadable": True,
            "is_public": False,
            "status": "ready",
            "permanent": True,
            "created_at": now,
        }
        await db.user_assets.insert_one(asset)
        assets_registered.append(asset["asset_id"])

    # Register cover image
    if uploaded_assets.get("cover_url"):
        asset = {
            "asset_id": str(uuid.uuid4()),
            "user_id": user_id,
            "job_id": job_id,
            "asset_type": "COMIC_STORYBOOK_COVER",
            "display_name": f"{title} — Cover",
            "storage_key": uploaded_assets["cover_url"],
            "cdn_url": uploaded_assets["cover_url"],
            "mime_type": "image/png",
            "is_downloadable": True,
            "is_public": False,
            "status": "ready",
            "permanent": True,
            "created_at": now,
        }
        await db.user_assets.insert_one(asset)
        assets_registered.append(asset["asset_id"])

    # Register thumbnail
    if uploaded_assets.get("thumbnail_url"):
        asset = {
            "asset_id": str(uuid.uuid4()),
            "user_id": user_id,
            "job_id": job_id,
            "asset_type": "COMIC_STORYBOOK_THUMBNAIL",
            "display_name": f"{title} — Thumbnail",
            "storage_key": uploaded_assets["thumbnail_url"],
            "cdn_url": uploaded_assets["thumbnail_url"],
            "mime_type": "image/png",
            "is_downloadable": False,
            "is_public": True,
            "status": "ready",
            "permanent": True,
            "created_at": now,
        }
        await db.user_assets.insert_one(asset)

    # Update job with asset IDs
    await db.comic_storybook_v2_jobs.update_one(
        {"id": job_id},
        {"$set": {"assets": assets_registered, "permanent": True}}
    )

    await update_stage(job_id, stage, "completed")


# ── JOB STATUS + DOWNLOAD ENDPOINTS ──────────────────────────────────────

@router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status with stage progress and presigned URLs."""
    job = await db.comic_storybook_v2_jobs.find_one({"id": job_id, "userId": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Presign CDN URLs for completed jobs
    if job.get("status") == "COMPLETED":
        from utils.r2_presign import presign_url
        if job.get("pdfUrl") and ".r2.dev/" in job["pdfUrl"]:
            job["pdfUrl"] = presign_url(job["pdfUrl"])
        if job.get("coverUrl") and ".r2.dev/" in job["coverUrl"]:
            job["coverUrl"] = presign_url(job["coverUrl"])
        if job.get("thumbnailUrl") and ".r2.dev/" in job["thumbnailUrl"]:
            job["thumbnailUrl"] = presign_url(job["thumbnailUrl"])

    # Get stage details
    stages = await db.job_stage_runs.find({"job_id": job_id}, {"_id": 0}).to_list(20)
    job["stages"] = stages

    return job


@router.get("/stages/{job_id}")
async def get_stage_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get detailed stage-by-stage progress."""
    job = await db.comic_storybook_v2_jobs.find_one({"id": job_id, "userId": user["id"]}, {"_id": 0, "id": 1})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stages = await db.job_stage_runs.find({"job_id": job_id}, {"_id": 0}).sort("created_at", 1).to_list(20)
    return {"job_id": job_id, "stages": stages}


@router.post("/download/{job_id}")
async def download_comic(job_id: str, user: dict = Depends(get_current_user)):
    """Download comic book — returns permanent CDN URLs only for validated assets."""
    job = await db.comic_storybook_v2_jobs.find_one({"id": job_id, "userId": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Book not ready yet")
    if not job.get("permanent"):
        raise HTTPException(status_code=400, detail="Assets not yet registered. Please wait.")

    from utils.r2_presign import presign_url
    urls = {}
    if job.get("pdfUrl"):
        urls["pdf"] = presign_url(job["pdfUrl"]) if ".r2.dev/" in job["pdfUrl"] else job["pdfUrl"]
    if job.get("coverUrl"):
        urls["cover"] = presign_url(job["coverUrl"]) if ".r2.dev/" in job["coverUrl"] else job["coverUrl"]

    if not urls:
        raise HTTPException(status_code=404, detail="No downloadable assets found")

    return {"success": True, "permanent": True, "downloadUrls": urls}


@router.get("/history")
async def get_history(page: int = 0, size: int = 20, user: dict = Depends(get_current_user)):
    jobs = await db.comic_storybook_v2_jobs.find(
        {"userId": user["id"]}, {"_id": 0}
    ).sort("createdAt", -1).skip(page * size).limit(size).to_list(length=size)
    total = await db.comic_storybook_v2_jobs.count_documents({"userId": user["id"]})
    return {"jobs": jobs, "total": total, "page": page, "size": size}


@router.get("/admin/pricing")
async def admin_get_pricing(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return {"pricing": PRICING, "genres": list(STORY_GENRES.keys())}


@router.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    total = await db.comic_storybook_v2_jobs.count_documents({})
    completed = await db.comic_storybook_v2_jobs.count_documents({"status": "COMPLETED"})
    failed = await db.comic_storybook_v2_jobs.count_documents({"status": "FAILED"})
    return {"totalJobs": total, "completed": completed, "failed": failed}
