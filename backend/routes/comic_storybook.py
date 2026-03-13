"""
Comic Story Book Generator
CreatorStudio AI

Features:
- Story script input (text or file upload)
- Auto-detect or customizable panels per page
- 10-50 page PDF generation
- Multiple comic styles
- Copyright-safe content
- Online viewing + PDF download
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import os
import sys
import base64
import asyncio
import json
import re
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)

router = APIRouter(prefix="/comic-storybook", tags=["Comic Story Book"])

# Extended comic styles
STORYBOOK_STYLES = {
    "classic": {
        "name": "Classic Comic",
        "description": "Bold lines, vibrant colors, classic superhero style",
        "prompt_modifier": "classic comic book style, bold outlines, vibrant colors, halftone dots, dynamic poses"
    },
    "manga": {
        "name": "Manga Style",
        "description": "Japanese manga-inspired with expressive features",
        "prompt_modifier": "manga style, anime aesthetic, large expressive eyes, clean lines, Japanese comic style"
    },
    "cartoon": {
        "name": "Cartoon Ink",
        "description": "Fun, exaggerated cartoon style",
        "prompt_modifier": "cartoon style, exaggerated features, thick black outlines, bright colors, playful"
    },
    "pixel": {
        "name": "Pixel Comic",
        "description": "Retro pixel art comic style",
        "prompt_modifier": "pixel art style, 16-bit aesthetic, retro gaming style, pixelated comic"
    },
    "kids": {
        "name": "Kids-Friendly",
        "description": "Soft, friendly style for children",
        "prompt_modifier": "children's book illustration style, soft colors, friendly characters, cute style"
    },
    "noir": {
        "name": "Noir Detective",
        "description": "Dark, moody black and white style",
        "prompt_modifier": "film noir style, black and white, high contrast, dramatic shadows, detective comic"
    },
    "superhero": {
        "name": "Superhero",
        "description": "Action-packed superhero comic style",
        "prompt_modifier": "superhero comic style, dynamic action poses, muscular figures, cape flowing, heroic"
    },
    "fantasy": {
        "name": "Fantasy",
        "description": "Magical fantasy world style",
        "prompt_modifier": "fantasy comic style, magical elements, mystical atmosphere, enchanted world"
    },
    "scifi": {
        "name": "Sci-Fi",
        "description": "Futuristic science fiction style",
        "prompt_modifier": "sci-fi comic style, futuristic, technology, space age, cyberpunk elements"
    },
    # Additional styles
    "watercolor": {
        "name": "Watercolor",
        "description": "Soft watercolor painting style",
        "prompt_modifier": "watercolor illustration style, soft edges, flowing colors, artistic brushstrokes"
    },
    "vintage": {
        "name": "Vintage",
        "description": "Retro 1950s comic style",
        "prompt_modifier": "vintage 1950s comic style, retro colors, Ben-Day dots, classic Americana"
    },
    "chibi": {
        "name": "Chibi",
        "description": "Cute big-head small-body style",
        "prompt_modifier": "chibi style, cute oversized heads, small bodies, kawaii aesthetic, adorable"
    },
    "realistic": {
        "name": "Realistic",
        "description": "Photo-realistic comic art",
        "prompt_modifier": "realistic comic art style, detailed rendering, lifelike characters, dramatic lighting"
    },
    "storybook": {
        "name": "Storybook",
        "description": "Classic children's storybook style",
        "prompt_modifier": "classic storybook illustration, warm colors, whimsical, fairy tale aesthetic"
    }
}

# Panel layouts per page
PANEL_LAYOUTS = {
    2: {"grid": "1x2", "description": "2 large panels"},
    3: {"grid": "1x3", "description": "3 horizontal panels"},
    4: {"grid": "2x2", "description": "4 equal panels"},
    6: {"grid": "2x3", "description": "6 panels (standard)"},
    8: {"grid": "2x4", "description": "8 panels"},
    9: {"grid": "3x3", "description": "9 panels (detailed)"}
}

# Credit costs
STORYBOOK_CREDITS = {
    "generate": 3,   # Base cost per page
    "download": 5    # Cost to download PDF
}

# Credit costs based on page count (for generation view)
def calculate_credits(page_count: int) -> int:
    """Calculate credits based on page count for viewing"""
    # 10 credits base + 1 credit per page
    return 10 + page_count

# Download always costs 20 credits
DOWNLOAD_CREDITS = 20

# Blocked content patterns
BLOCKED_PATTERNS = [
    "marvel", "dc comics", "disney", "pixar", "ghibli", "simpsons",
    "batman", "superman", "spiderman", "iron man", "hulk", "thor",
    "mickey mouse", "donald duck", "frozen", "elsa", "moana",
    "naruto", "one piece", "dragon ball", "pokemon", "pikachu",
    "celebrity", "real person", "politician", "nude", "nsfw", "sexual",
    "harry potter", "lord of rings", "star wars", "avengers"
]


def check_content_safety(text: str) -> tuple:
    """Check if content is copyright-safe"""
    text_lower = text.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in text_lower:
            return False, f"Content referencing '{pattern}' is not allowed. Please use original characters only."
    return True, "OK"


def parse_story_to_scenes(story_text: str, target_pages: int = None) -> List[dict]:
    """Parse story text into scenes for comic panels"""
    # Clean the text
    story_text = story_text.strip()
    
    # Try to split by common scene markers
    scene_markers = [
        r'\n\n+',  # Double newlines
        r'(?:Chapter|Scene|Part)\s*\d*[:\.]?\s*',  # Chapter/Scene markers
        r'(?:---+|===+|\*\*\*+)',  # Dividers
    ]
    
    # First try paragraphs
    paragraphs = re.split(r'\n\n+', story_text)
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
    
    # If we have a target page count, adjust
    if target_pages:
        # Aim for 2-4 panels per page on average
        target_scenes = target_pages * 3
        
        if len(paragraphs) < target_scenes:
            # Split longer paragraphs
            expanded = []
            for p in paragraphs:
                sentences = re.split(r'(?<=[.!?])\s+', p)
                if len(sentences) > 3:
                    # Group sentences into chunks
                    chunk_size = max(2, len(sentences) // 3)
                    for i in range(0, len(sentences), chunk_size):
                        chunk = ' '.join(sentences[i:i+chunk_size])
                        if chunk.strip():
                            expanded.append(chunk.strip())
                else:
                    expanded.append(p)
            paragraphs = expanded
        elif len(paragraphs) > target_scenes * 1.5:
            # Combine short paragraphs
            combined = []
            current = ""
            for p in paragraphs:
                if len(current) + len(p) < 500:
                    current = (current + " " + p).strip()
                else:
                    if current:
                        combined.append(current)
                    current = p
            if current:
                combined.append(current)
            paragraphs = combined
    
    # Create scene objects
    scenes = []
    for i, para in enumerate(paragraphs):
        # Generate a short title for the scene
        words = para.split()[:5]
        title = ' '.join(words) + "..." if len(words) >= 5 else para[:30]
        
        scenes.append({
            "scene_number": i + 1,
            "title": title,
            "description": para,
            "dialogue": None  # Will be extracted or generated
        })
    
    return scenes


@router.get("/styles")
async def get_storybook_styles(user: dict = Depends(get_current_user)):
    """Get available comic styles for story books"""
    return {
        "styles": STORYBOOK_STYLES,
        "layouts": PANEL_LAYOUTS,
        "pricing": {
            "generate": 10,  # Base generation cost
            "per_page": 1,   # Additional per page
            "download": DOWNLOAD_CREDITS,  # 20 credits to download PDF
            "example_10_pages": calculate_credits(10),
            "example_20_pages": calculate_credits(20),
            "example_50_pages": calculate_credits(50)
        },
        "limits": {
            "min_pages": 10,
            "max_pages": 50
        }
    }


@router.post("/parse-story")
async def parse_story(
    story_text: Optional[str] = Form(None),
    story_file: Optional[UploadFile] = File(None),
    target_pages: int = Form(20),
    user: dict = Depends(get_current_user)
):
    """Parse story text or file into scenes (preview before generation)"""
    
    if not story_text and not story_file:
        raise HTTPException(status_code=400, detail="Please provide story text or upload a file")
    
    # Get story content
    content = ""
    if story_file:
        file_content = await story_file.read()
        filename = story_file.filename.lower()
        
        if filename.endswith('.txt'):
            content = file_content.decode('utf-8', errors='ignore')
        elif filename.endswith('.md'):
            content = file_content.decode('utf-8', errors='ignore')
        else:
            raise HTTPException(status_code=400, detail="Supported formats: .txt, .md")
    else:
        content = story_text
    
    # Check content safety
    is_safe, message = check_content_safety(content)
    if not is_safe:
        raise HTTPException(status_code=400, detail=message)
    
    # Parse into scenes
    target_pages = max(10, min(50, target_pages))
    scenes = parse_story_to_scenes(content, target_pages)
    
    # Calculate recommended pages
    recommended_pages = max(10, min(50, len(scenes) // 3 + 1))
    
    return {
        "success": True,
        "scene_count": len(scenes),
        "scenes_preview": scenes[:5],  # Show first 5 scenes
        "recommended_pages": recommended_pages,
        "estimated_credits": calculate_credits(recommended_pages),
        "word_count": len(content.split())
    }


@router.post("/generate")
async def generate_storybook(
    background_tasks: BackgroundTasks,
    story_text: Optional[str] = Form(None),
    story_file: Optional[UploadFile] = File(None),
    style: str = Form("storybook"),
    page_count: int = Form(20),
    panels_per_page: str = Form("auto"),  # "auto" or number
    title: str = Form("My Comic Story"),
    author: str = Form(""),
    user: dict = Depends(get_current_user)
):
    """Generate a complete comic story book"""
    
    if not story_text and not story_file:
        raise HTTPException(status_code=400, detail="Please provide story text or upload a file")
    
    # Validate style
    if style not in STORYBOOK_STYLES:
        raise HTTPException(status_code=400, detail=f"Invalid style. Choose from: {list(STORYBOOK_STYLES.keys())}")
    
    # Validate page count
    page_count = max(10, min(50, page_count))
    
    # Get story content
    content = ""
    if story_file:
        file_content = await story_file.read()
        filename = story_file.filename.lower()
        
        if filename.endswith('.txt'):
            content = file_content.decode('utf-8', errors='ignore')
        elif filename.endswith('.md'):
            content = file_content.decode('utf-8', errors='ignore')
        else:
            raise HTTPException(status_code=400, detail="Supported formats: .txt, .md")
    else:
        content = story_text
    
    # Check content safety
    is_safe, message = check_content_safety(content)
    if not is_safe:
        raise HTTPException(status_code=400, detail=message)
    
    # Calculate cost
    cost = calculate_credits(page_count)
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits for {page_count} pages.")
    
    # Create job
    job_id = str(uuid.uuid4())
    
    # Parse panels per page
    if panels_per_page == "auto":
        panels = None  # Will be determined per page
    else:
        try:
            panels = int(panels_per_page)
            if panels not in PANEL_LAYOUTS:
                panels = 6  # Default
        except:
            panels = None
    
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "type": "COMIC_STORYBOOK",
        "status": "QUEUED",
        "title": title,
        "author": author or user.get("name", "Anonymous"),
        "style": style,
        "pageCount": page_count,
        "panelsPerPage": panels,
        "storyWordCount": len(content.split()),
        "cost": cost,
        "progress": 0,
        "currentPage": 0,
        "pages": [],
        "pdfUrl": None,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.storybook_jobs.insert_one(job_data)
    
    # Process in background
    background_tasks.add_task(
        process_storybook_generation,
        job_id, content, style, page_count, panels, title, author or user.get("name", "Anonymous"), user["id"], cost
    )
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "pageCount": page_count,
        "estimatedCredits": cost,
        "message": f"Generating {page_count}-page comic story book..."
    }


async def process_storybook_generation(
    job_id: str,
    story_content: str,
    style: str,
    page_count: int,
    panels_per_page: Optional[int],
    title: str,
    author: str,
    user_id: str,
    cost: int
):
    """Background task to generate complete story book"""
    try:
        await db.storybook_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "progress": 5, "progressMessage": "Parsing story..."}}
        )
        
        style_info = STORYBOOK_STYLES[style]
        
        # Parse story into scenes
        scenes = parse_story_to_scenes(story_content, page_count)
        
        # Distribute scenes across pages
        scenes_per_page = max(1, len(scenes) // page_count)
        pages = []
        
        for page_num in range(page_count):
            start_idx = page_num * scenes_per_page
            end_idx = start_idx + scenes_per_page if page_num < page_count - 1 else len(scenes)
            page_scenes = scenes[start_idx:end_idx]
            
            if not page_scenes and pages:
                # If no more scenes, duplicate last page's scene
                page_scenes = [pages[-1]["scenes"][-1]] if pages[-1]["scenes"] else []
            
            # Determine panels for this page
            if panels_per_page:
                num_panels = panels_per_page
            else:
                # Auto-detect: 2-4 panels based on scene content length
                total_text = sum(len(s.get("description", "")) for s in page_scenes)
                if total_text < 200:
                    num_panels = 2
                elif total_text < 500:
                    num_panels = 4
                else:
                    num_panels = 6
            
            pages.append({
                "page_number": page_num + 1,
                "scenes": page_scenes,
                "num_panels": num_panels,
                "panels": []
            })
        
        await db.storybook_jobs.update_one(
            {"id": job_id},
            {"$set": {"progress": 10, "progressMessage": f"Generating {len(pages)} pages..."}}
        )
        
        # Generate panels for each page
        generated_pages = []
        
        for page_idx, page in enumerate(pages):
            # Update progress
            progress = 10 + int((page_idx / len(pages)) * 80)
            await db.storybook_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "progress": progress,
                    "currentPage": page_idx + 1,
                    "progressMessage": f"Creating page {page_idx + 1} of {len(pages)}..."
                }}
            )
            
            page_panels = []
            
            # Generate image for each scene on this page
            for scene_idx, scene in enumerate(page["scenes"][:page["num_panels"]]):
                panel_data = {
                    "panel_number": scene_idx + 1,
                    "scene_title": scene.get("title", ""),
                    "description": scene.get("description", ""),
                    "imageUrl": None
                }
                
                # Generate image using AI
                if LLM_AVAILABLE and EMERGENT_LLM_KEY:
                    try:
                        from emergentintegrations.llm.chat import LlmChat, UserMessage
                        
                        chat = LlmChat(
                            api_key=EMERGENT_LLM_KEY,
                            session_id=f"storybook-{job_id}-p{page_idx}-s{scene_idx}",
                            system_message="You are a professional comic book illustrator. Create vivid, copyright-free illustrations."
                        )
                        chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                        
                        prompt = f"""Create a comic book panel illustration:
Story context: {title}
Scene: {scene.get('description', '')[:500]}
Style: {style_info['prompt_modifier']}

Make it original, copyright-free, visually engaging, and appropriate for all ages."""
                        
                        msg = UserMessage(text=prompt)
                        text_response, images = await chat.send_message_multimodal_response(msg)
                        
                        if images and len(images) > 0:
                            img_data = images[0]
                            image_bytes = base64.b64decode(img_data['data'])
                            
                            import hashlib
                            filename = f"storybook_{hashlib.md5(f'{job_id}_{page_idx}_{scene_idx}'.encode()).hexdigest()[:16]}.png"
                            filepath = f"/app/backend/static/generated/{filename}"
                            
                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                            
                            with open(filepath, 'wb') as f:
                                f.write(image_bytes)
                            
                            panel_data["imageUrl"] = f"/api/generated/{filename}"
                            
                    except Exception as e:
                        logger.error(f"Storybook panel generation error: {e}")
                
                # Placeholder if no AI result
                if not panel_data["imageUrl"]:
                    panel_data["imageUrl"] = f"https://placehold.co/800x600/4a1d96/white?text=Page+{page_idx+1}+Panel+{scene_idx+1}"
                
                page_panels.append(panel_data)
            
            generated_pages.append({
                "page_number": page_idx + 1,
                "panels": page_panels
            })
        
        # Generate PDF
        await db.storybook_jobs.update_one(
            {"id": job_id},
            {"$set": {"progress": 90, "progressMessage": "Creating PDF..."}}
        )
        
        pdf_path = await generate_storybook_pdf(job_id, title, author, style, generated_pages)
        pdf_url = f"/api/comic-storybook/download/{job_id}"
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"Comic Storybook: {title[:20]}")
        
        # Update job with results
        await db.storybook_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "pages": generated_pages,
                "pdfUrl": pdf_url,
                "pdfPath": pdf_path,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"Storybook generation error: {e}")
        await db.storybook_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e)}}
        )


async def generate_storybook_pdf(job_id: str, title: str, author: str, style: str, pages: list) -> str:
    """Generate PDF from comic pages"""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.colors import HexColor
    import requests
    from PIL import Image
    
    pdf_dir = "/app/backend/static/storybooks"
    os.makedirs(pdf_dir, exist_ok=True)
    
    pdf_path = f"{pdf_dir}/storybook_{job_id}.pdf"
    
    # Create PDF
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    
    # Title page
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width/2, height - 200, title)
    c.setFont("Helvetica", 18)
    c.drawCentredString(width/2, height - 250, f"By {author}")
    c.setFont("Helvetica-Oblique", 14)
    c.drawCentredString(width/2, height - 300, f"Style: {STORYBOOK_STYLES.get(style, {}).get('name', style)}")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height - 400, "Generated by CreatorStudio AI")
    c.drawCentredString(width/2, height - 420, "Copyright-free original content")
    c.showPage()
    
    # Content pages
    for page in pages:
        panels = page.get("panels", [])
        num_panels = len(panels)
        
        if num_panels == 0:
            continue
        
        # Calculate panel layout
        margin = 30
        panel_spacing = 10
        available_width = width - 2 * margin
        available_height = height - 2 * margin - 40  # Leave space for page number
        
        # Simple layout: stack panels vertically
        panel_height = (available_height - (num_panels - 1) * panel_spacing) / num_panels
        panel_width = available_width
        
        y_pos = height - margin
        
        for panel in panels:
            y_pos -= panel_height
            
            # Draw panel border
            c.setStrokeColor(HexColor("#333333"))
            c.setLineWidth(2)
            c.rect(margin, y_pos, panel_width, panel_height - panel_spacing)
            
            # Try to load and draw image
            image_url = panel.get("imageUrl", "")
            try:
                if image_url.startswith("/api/static/"):
                    # Local file
                    local_path = image_url.replace("/api/static/", "/app/backend/static/")
                    if os.path.exists(local_path):
                        img = Image.open(local_path)
                        img_reader = ImageReader(img)
                        c.drawImage(img_reader, margin + 5, y_pos + 5, 
                                   panel_width - 10, panel_height - panel_spacing - 10,
                                   preserveAspectRatio=True)
                elif image_url.startswith("http"):
                    # Remote URL - download and embed
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        img = Image.open(io.BytesIO(response.content))
                        img_reader = ImageReader(img)
                        c.drawImage(img_reader, margin + 5, y_pos + 5,
                                   panel_width - 10, panel_height - panel_spacing - 10,
                                   preserveAspectRatio=True)
            except Exception as e:
                logger.warning(f"Failed to embed image: {e}")
                # Draw placeholder
                c.setFillColor(HexColor("#f0f0f0"))
                c.rect(margin + 5, y_pos + 5, panel_width - 10, panel_height - panel_spacing - 10, fill=1)
                c.setFillColor(HexColor("#666666"))
                c.setFont("Helvetica", 10)
                desc = panel.get("description", "")[:100]
                c.drawCentredString(margin + panel_width/2, y_pos + panel_height/2, desc if desc else "Panel")
            
            y_pos -= panel_spacing
        
        # Page number
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#666666"))
        c.drawCentredString(width/2, 20, f"Page {page.get('page_number', 1)}")
        
        c.showPage()
    
    # Final page
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height - 200, "The End")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height - 250, f'"{title}"')
    c.drawCentredString(width/2, height - 280, f"Created with CreatorStudio AI")
    c.drawCentredString(width/2, height - 310, "All content is original and copyright-free")
    c.showPage()
    
    c.save()
    
    return pdf_path


@router.get("/job/{job_id}")
async def get_storybook_job(job_id: str, user: dict = Depends(get_current_user)):
    """Get story book generation job status"""
    job = await db.storybook_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/download/{job_id}")
async def download_storybook_pdf(job_id: str, user: dict = Depends(get_current_user)):
    """Download the generated story book PDF"""
    job = await db.storybook_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Story book is not ready yet")
    
    pdf_path = job.get("pdfPath")
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Generate safe filename
    title = job.get("title", "comic_storybook")
    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)[:50]
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{safe_title}.pdf"
    )


@router.get("/history")
async def get_storybook_history(
    page: int = 0,
    size: int = 10,
    user: dict = Depends(get_current_user)
):
    """Get user's story book generation history"""
    jobs = await db.storybook_jobs.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(page * size).limit(size).to_list(length=size)
    
    total = await db.storybook_jobs.count_documents({"userId": user["id"]})
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "size": size
    }


@router.delete("/job/{job_id}")
async def delete_storybook_job(job_id: str, user: dict = Depends(get_current_user)):
    """Delete a story book job"""
    job = await db.storybook_jobs.find_one(
        {"id": job_id, "userId": user["id"]}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete PDF file if exists
    pdf_path = job.get("pdfPath")
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except:
            pass
    
    # Delete from database
    await db.storybook_jobs.delete_one({"id": job_id, "userId": user["id"]})
    
    return {"success": True, "message": "Story book deleted"}
