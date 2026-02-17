"""
PDF Generator Service using Playwright
Renders HTML templates to high-quality PDF for kids' storybooks
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Color themes for different story pages
PAGE_THEMES = [
    {
        "name": "lavender",
        "bg_color": "linear-gradient(180deg, #FAF5FF 0%, #F3E8FF 50%, #EDE9FE 100%)",
        "accent_color": "#8B5CF6",
        "accent_light": "#C4B5FD",
        "text_accent": "#5B21B6",
        "dialogue_bg": "rgba(237, 233, 254, 0.7)"
    },
    {
        "name": "mint",
        "bg_color": "linear-gradient(180deg, #ECFDF5 0%, #D1FAE5 50%, #A7F3D0 100%)",
        "accent_color": "#10B981",
        "accent_light": "#6EE7B7",
        "text_accent": "#047857",
        "dialogue_bg": "rgba(209, 250, 229, 0.7)"
    },
    {
        "name": "peach",
        "bg_color": "linear-gradient(180deg, #FFF7ED 0%, #FFEDD5 50%, #FED7AA 100%)",
        "accent_color": "#F97316",
        "accent_light": "#FDBA74",
        "text_accent": "#C2410C",
        "dialogue_bg": "rgba(254, 215, 170, 0.5)"
    },
    {
        "name": "sky",
        "bg_color": "linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 50%, #BFDBFE 100%)",
        "accent_color": "#3B82F6",
        "accent_light": "#93C5FD",
        "text_accent": "#1D4ED8",
        "dialogue_bg": "rgba(191, 219, 254, 0.6)"
    },
    {
        "name": "rose",
        "bg_color": "linear-gradient(180deg, #FFF1F2 0%, #FFE4E6 50%, #FECDD3 100%)",
        "accent_color": "#F43F5E",
        "accent_light": "#FDA4AF",
        "text_accent": "#BE123C",
        "dialogue_bg": "rgba(254, 205, 211, 0.6)"
    },
    {
        "name": "amber",
        "bg_color": "linear-gradient(180deg, #FFFBEB 0%, #FEF3C7 50%, #FDE68A 100%)",
        "accent_color": "#F59E0B",
        "accent_light": "#FCD34D",
        "text_accent": "#B45309",
        "dialogue_bg": "rgba(253, 230, 138, 0.5)"
    }
]


def get_template_path(template_name: str) -> str:
    """Get full path to template file"""
    base_dir = Path(__file__).parent / "templates" / "pdf"
    return str(base_dir / template_name)


def load_template(template_name: str) -> str:
    """Load HTML template from file"""
    template_path = get_template_path(template_name)
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def render_cover_page(story: Dict) -> str:
    """Render the cover page HTML"""
    template = load_template("cover.html")
    
    return template.replace("{{GENRE}}", story.get("genre", "Adventure")) \
                   .replace("{{TITLE}}", story.get("title", "My Story")) \
                   .replace("{{SYNOPSIS}}", story.get("synopsis", "A magical adventure awaits...")) \
                   .replace("{{AGE_GROUP}}", story.get("ageGroup", "3-8"))


def render_story_page(story: Dict, scene: Dict, scene_number: int, page_number: int) -> str:
    """Render a story content page"""
    template = load_template("story-page.html")
    theme = PAGE_THEMES[(page_number - 1) % len(PAGE_THEMES)]
    
    # Process scene content - support both 'content' and 'narration' fields
    scene_title = scene.get("title", f"Scene {scene_number}")
    scene_content = scene.get("content") or scene.get("narration") or scene.get("text") or ""
    
    # Format paragraphs
    paragraphs = scene_content.split('\n\n') if '\n\n' in scene_content else [scene_content]
    formatted_content = ''.join([f"<p>{p.strip()}</p>" for p in paragraphs if p.strip()])
    
    # Handle dialogue if present - support both 'text' and 'line' fields
    dialogue_section = ""
    dialogue = scene.get("dialogue", [])
    if dialogue:
        dialogue_html = []
        for d in dialogue[:2]:  # Max 2 dialogues per page
            speaker = d.get("speaker", "Character")
            text = d.get("text") or d.get("line") or ""
            if text:
                dialogue_html.append(f'''
                <div class="dialogue-box">
                    <p class="speaker">{speaker}:</p>
                    <p class="dialogue-text">{text}</p>
                </div>
                ''')
        dialogue_section = ''.join(dialogue_html)
    
    return template.replace("{{BG_COLOR}}", theme["bg_color"]) \
                   .replace("{{ACCENT_COLOR}}", theme["accent_color"]) \
                   .replace("{{ACCENT_LIGHT}}", theme["accent_light"]) \
                   .replace("{{TEXT_ACCENT}}", theme["text_accent"]) \
                   .replace("{{DIALOGUE_BG}}", theme["dialogue_bg"]) \
                   .replace("{{STORY_TITLE}}", story.get("title", "My Story")) \
                   .replace("{{SCENE_NUMBER}}", str(scene_number)) \
                   .replace("{{SCENE_TITLE}}", scene_title) \
                   .replace("{{STORY_CONTENT}}", formatted_content) \
                   .replace("{{DIALOGUE_SECTION}}", dialogue_section) \
                   .replace("{{PAGE_NUMBER}}", str(page_number))


def render_moral_page(story: Dict, page_number: int) -> str:
    """Render the moral/lesson page"""
    template = load_template("moral.html")
    moral = story.get("moral", "Every story has a lesson to teach us.")
    
    return template.replace("{{MORAL_TEXT}}", moral) \
                   .replace("{{PAGE_NUMBER}}", str(page_number))


def render_ending_page(page_number: int) -> str:
    """Render the ending/CTA page"""
    template = load_template("ending.html")
    year = datetime.now().year
    
    return template.replace("{{YEAR}}", str(year)) \
                   .replace("{{PAGE_NUMBER}}", str(page_number))


async def generate_pdf_from_story(story: Dict, output_path: str) -> str:
    """
    Generate a professional PDF from story data using Playwright
    
    Args:
        story: Dictionary containing story data (title, scenes, moral, etc.)
        output_path: Path where the PDF will be saved
        
    Returns:
        Path to the generated PDF file
    """
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # Create context with print settings
        context = await browser.new_context(
            viewport={'width': 794, 'height': 1123}  # A4 at 96 DPI
        )
        
        page = await context.new_page()
        
        # Collect all pages HTML
        pages_html = []
        
        # 1. Cover page
        cover_html = render_cover_page(story)
        pages_html.append(cover_html)
        
        # 2. Story pages
        scenes = story.get("scenes", [])
        page_num = 2
        
        for idx, scene in enumerate(scenes):
            scene_html = render_story_page(story, scene, idx + 1, page_num)
            pages_html.append(scene_html)
            page_num += 1
        
        # 3. Moral page
        moral_html = render_moral_page(story, page_num)
        pages_html.append(moral_html)
        page_num += 1
        
        # 4. Ending page
        ending_html = render_ending_page(page_num)
        pages_html.append(ending_html)
        
        # Generate PDFs for each page and merge
        import tempfile
        from PyPDF2 import PdfMerger
        
        merger = PdfMerger()
        temp_files = []
        
        for i, html_content in enumerate(pages_html):
            # Set page content
            await page.set_content(html_content, wait_until='networkidle')
            
            # Wait for fonts to load
            await page.wait_for_timeout(500)
            
            # Generate PDF for this page
            temp_path = f"/tmp/story_page_{i}.pdf"
            temp_files.append(temp_path)
            
            await page.pdf(
                path=temp_path,
                format='A4',
                print_background=True,
                margin={
                    'top': '0mm',
                    'bottom': '0mm',
                    'left': '0mm',
                    'right': '0mm'
                }
            )
            
            merger.append(temp_path)
        
        # Write merged PDF
        merger.write(output_path)
        merger.close()
        
        # Cleanup temp files
        for temp_path in temp_files:
            try:
                os.remove(temp_path)
            except:
                pass
        
        await browser.close()
        
        return output_path


async def generate_pdf_simple(story: Dict, output_path: str) -> str:
    """
    Generate PDF by rendering each page separately and merging them.
    This ensures each page has its own complete styles and renders correctly.
    """
    from playwright.async_api import async_playwright
    import subprocess
    import os
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        # Collect all page HTMLs
        all_pages_html = []
        
        # 1. Cover page
        all_pages_html.append(render_cover_page(story))
        
        # 2. Story scene pages
        scenes = story.get("scenes", [])
        page_num = 2
        for idx, scene in enumerate(scenes):
            all_pages_html.append(render_story_page(story, scene, idx + 1, page_num))
            page_num += 1
        
        # 3. Moral page
        all_pages_html.append(render_moral_page(story, page_num))
        page_num += 1
        
        # 4. Ending page
        all_pages_html.append(render_ending_page(page_num))
        
        # Generate individual PDFs for each page
        temp_pdf_paths = []
        
        for i, html_content in enumerate(all_pages_html):
            temp_path = f"/tmp/story_page_{os.getpid()}_{i}.pdf"
            temp_pdf_paths.append(temp_path)
            
            # Set full HTML content for this page
            await page.set_content(html_content, wait_until='networkidle')
            
            # Wait for fonts and images to load
            await page.wait_for_timeout(800)
            
            # Generate PDF
            await page.pdf(
                path=temp_path,
                format='A4',
                print_background=True,
                margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'}
            )
        
        await browser.close()
        
        # Merge all PDFs using pdftk or fallback to PyPDF2
        try:
            # Try using pdftk (faster)
            cmd = ['pdftk'] + temp_pdf_paths + ['cat', 'output', output_path]
            subprocess.run(cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to PyPDF2
            try:
                from PyPDF2 import PdfMerger
                merger = PdfMerger()
                for pdf_path in temp_pdf_paths:
                    merger.append(pdf_path)
                merger.write(output_path)
                merger.close()
            except ImportError:
                # If PyPDF2 not available, use pdfunite
                try:
                    cmd = ['pdfunite'] + temp_pdf_paths + [output_path]
                    subprocess.run(cmd, check=True, capture_output=True)
                except:
                    # Last resort - just copy the first PDF
                    import shutil
                    shutil.copy(temp_pdf_paths[0], output_path)
        
        # Cleanup temp files
        for temp_path in temp_pdf_paths:
            try:
                os.remove(temp_path)
            except:
                pass
        
        return output_path
