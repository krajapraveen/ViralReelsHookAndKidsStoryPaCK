"""
Reel Generator PDF Export Module
Creates nicely formatted PDF documents with script, hooks, and captions
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
import uuid
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/reel-export", tags=["Reel Export"])


class ReelExportRequest(BaseModel):
    generation_id: str = Field(..., description="ID of the reel generation to export")
    include_hooks: bool = Field(True, description="Include hook variations")
    include_captions: bool = Field(True, description="Include caption variations")
    include_hashtags: bool = Field(True, description="Include hashtag suggestions")
    paper_size: str = Field("letter", description="Paper size: letter or a4")
    theme: str = Field("professional", description="Theme: professional, creative, minimal")


# Color schemes for different themes
THEMES = {
    "professional": {
        "primary": colors.HexColor("#1a365d"),
        "secondary": colors.HexColor("#2d3748"),
        "accent": colors.HexColor("#4299e1"),
        "background": colors.HexColor("#f7fafc"),
        "text": colors.HexColor("#2d3748"),
        "header_bg": colors.HexColor("#1a365d"),
        "header_text": colors.white,
    },
    "creative": {
        "primary": colors.HexColor("#6b21a8"),
        "secondary": colors.HexColor("#9333ea"),
        "accent": colors.HexColor("#f59e0b"),
        "background": colors.HexColor("#faf5ff"),
        "text": colors.HexColor("#1f2937"),
        "header_bg": colors.HexColor("#6b21a8"),
        "header_text": colors.white,
    },
    "minimal": {
        "primary": colors.HexColor("#111827"),
        "secondary": colors.HexColor("#374151"),
        "accent": colors.HexColor("#6b7280"),
        "background": colors.white,
        "text": colors.HexColor("#1f2937"),
        "header_bg": colors.HexColor("#111827"),
        "header_text": colors.white,
    }
}


def get_styles(theme_name: str):
    """Generate paragraph styles for theme"""
    theme = THEMES.get(theme_name, THEMES["professional"])
    styles = getSampleStyleSheet()
    
    return {
        "title": ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=theme["primary"],
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName="Helvetica-Bold"
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=theme["secondary"],
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName="Helvetica"
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=theme["primary"],
            spaceBefore=20,
            spaceAfter=10,
            fontName="Helvetica-Bold",
            borderColor=theme["accent"],
            borderWidth=2,
            borderPadding=(0, 0, 5, 0)
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=11,
            textColor=theme["text"],
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=16,
            fontName="Helvetica"
        ),
        "script": ParagraphStyle(
            "Script",
            parent=styles["Normal"],
            fontSize=12,
            textColor=theme["text"],
            alignment=TA_LEFT,
            spaceAfter=12,
            leading=18,
            fontName="Helvetica",
            leftIndent=10,
            borderColor=theme["accent"],
            borderWidth=1,
            borderPadding=10,
            backColor=colors.HexColor("#f8fafc")
        ),
        "hook": ParagraphStyle(
            "Hook",
            parent=styles["Normal"],
            fontSize=11,
            textColor=theme["secondary"],
            alignment=TA_LEFT,
            spaceAfter=6,
            leading=14,
            fontName="Helvetica-Oblique",
            leftIndent=20
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=styles["Normal"],
            fontSize=10,
            textColor=theme["text"],
            alignment=TA_LEFT,
            spaceAfter=4,
            leading=13,
            fontName="Helvetica"
        ),
        "hashtag": ParagraphStyle(
            "Hashtag",
            parent=styles["Normal"],
            fontSize=10,
            textColor=theme["accent"],
            alignment=TA_LEFT,
            spaceAfter=2,
            fontName="Helvetica-Bold"
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=theme["secondary"],
            alignment=TA_CENTER,
            fontName="Helvetica"
        ),
        "metadata": ParagraphStyle(
            "Metadata",
            parent=styles["Normal"],
            fontSize=9,
            textColor=theme["secondary"],
            alignment=TA_LEFT,
            spaceAfter=4,
            fontName="Helvetica"
        )
    }


def create_header(canvas, doc, theme_name):
    """Create page header"""
    theme = THEMES.get(theme_name, THEMES["professional"])
    canvas.saveState()
    
    # Header bar
    canvas.setFillColor(theme["header_bg"])
    canvas.rect(0, doc.pagesize[1] - 40, doc.pagesize[0], 40, fill=1)
    
    # Header text
    canvas.setFillColor(theme["header_text"])
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(30, doc.pagesize[1] - 25, "CreatorStudio AI - Reel Script")
    
    # Date
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(doc.pagesize[0] - 30, doc.pagesize[1] - 25, 
                          datetime.now().strftime("%B %d, %Y"))
    
    canvas.restoreState()


def create_footer(canvas, doc, theme_name):
    """Create page footer"""
    theme = THEMES.get(theme_name, THEMES["professional"])
    canvas.saveState()
    
    # Footer line
    canvas.setStrokeColor(theme["accent"])
    canvas.setLineWidth(1)
    canvas.line(30, 30, doc.pagesize[0] - 30, 30)
    
    # Page number
    canvas.setFillColor(theme["secondary"])
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(doc.pagesize[0] / 2, 15, f"Page {doc.page}")
    
    # Branding
    canvas.setFont("Helvetica", 8)
    canvas.drawString(30, 15, "Generated by CreatorStudio AI")
    
    canvas.restoreState()


def build_pdf(generation_data: dict, options: ReelExportRequest) -> bytes:
    """Build PDF from generation data"""
    buffer = io.BytesIO()
    
    page_size = letter if options.paper_size == "letter" else A4
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        topMargin=60,
        bottomMargin=50,
        leftMargin=40,
        rightMargin=40
    )
    
    styles = get_styles(options.theme)
    theme = THEMES.get(options.theme, THEMES["professional"])
    story = []
    
    # Title
    title = generation_data.get("topic", "Untitled Reel")
    story.append(Paragraph(f"Reel Script: {title[:50]}{'...' if len(title) > 50 else ''}", styles["title"]))
    
    # Metadata
    metadata_items = [
        f"Platform: {generation_data.get('platform', 'Instagram')}",
        f"Style: {generation_data.get('style', 'Engaging')}",
        f"Duration: {generation_data.get('duration', '30')} seconds",
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    ]
    for item in metadata_items:
        story.append(Paragraph(item, styles["metadata"]))
    
    story.append(Spacer(1, 20))
    
    # Main Script Section
    story.append(Paragraph("Main Script", styles["section_header"]))
    
    script = generation_data.get("result", {}).get("script", "")
    if script:
        # Split script into paragraphs
        paragraphs = script.split("\n\n")
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), styles["script"]))
                story.append(Spacer(1, 8))
    
    # Hooks Section
    if options.include_hooks:
        hooks = generation_data.get("result", {}).get("hooks", [])
        if hooks:
            story.append(Spacer(1, 15))
            story.append(Paragraph("Hook Variations", styles["section_header"]))
            story.append(Paragraph(
                "Use these attention-grabbing hooks to start your reel:",
                styles["body"]
            ))
            story.append(Spacer(1, 10))
            
            for i, hook in enumerate(hooks, 1):
                hook_text = f"<b>Hook {i}:</b> {hook}"
                story.append(Paragraph(hook_text, styles["hook"]))
    
    # Captions Section
    if options.include_captions:
        captions = generation_data.get("result", {}).get("captions", [])
        if captions:
            story.append(Spacer(1, 15))
            story.append(Paragraph("Caption Variations", styles["section_header"]))
            story.append(Paragraph(
                "Ready-to-use captions for your post:",
                styles["body"]
            ))
            story.append(Spacer(1, 10))
            
            for i, caption in enumerate(captions, 1):
                # Create table for numbered caption
                caption_data = [[f"{i}.", caption]]
                caption_table = Table(caption_data, colWidths=[0.3*inch, 5.5*inch])
                caption_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('TEXTCOLOR', (0, 0), (-1, -1), theme["text"]),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(caption_table)
    
    # Hashtags Section
    if options.include_hashtags:
        hashtags = generation_data.get("result", {}).get("hashtags", [])
        if hashtags:
            story.append(Spacer(1, 15))
            story.append(Paragraph("Suggested Hashtags", styles["section_header"]))
            
            # Format hashtags in groups
            hashtag_text = " ".join([f"#{tag}" if not tag.startswith("#") else tag for tag in hashtags])
            story.append(Paragraph(hashtag_text, styles["hashtag"]))
    
    # Call to Action Section
    cta = generation_data.get("result", {}).get("cta", "")
    if cta:
        story.append(Spacer(1, 15))
        story.append(Paragraph("Call to Action", styles["section_header"]))
        story.append(Paragraph(cta, styles["body"]))
    
    # Tips Section
    story.append(PageBreak())
    story.append(Paragraph("Production Tips", styles["section_header"]))
    
    tips = [
        "Film in good lighting - natural light works best",
        "Use the hook in the first 3 seconds to grab attention",
        "Add captions/subtitles for accessibility",
        "Use trending audio when relevant",
        "Post during peak engagement hours for your audience",
        "Engage with comments quickly after posting",
        "Cross-post to multiple platforms with platform-specific tweaks"
    ]
    
    for tip in tips:
        story.append(Paragraph(f"• {tip}", styles["body"]))
    
    # Build PDF with header/footer
    def add_page_elements(canvas, doc):
        create_header(canvas, doc, options.theme)
        create_footer(canvas, doc, options.theme)
    
    doc.build(story, onFirstPage=add_page_elements, onLaterPages=add_page_elements)
    
    buffer.seek(0)
    return buffer.getvalue()


@router.post("/generate")
async def export_reel_to_pdf(
    request: ReelExportRequest,
    user: dict = Depends(get_current_user)
):
    """Export a reel generation to PDF"""
    # Get the generation data
    generation = await db.generations.find_one(
        {"id": request.generation_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    if generation.get("type") != "reel":
        raise HTTPException(status_code=400, detail="Only reel generations can be exported")
    
    try:
        # Generate PDF
        pdf_bytes = build_pdf(generation, request)
        
        # Log export
        await db.reel_exports.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "generationId": request.generation_id,
            "theme": request.theme,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Return PDF
        filename = f"reel_script_{request.generation_id[:8]}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.post("/preview")
async def preview_reel_export(
    request: ReelExportRequest,
    user: dict = Depends(get_current_user)
):
    """Get preview data for PDF export"""
    generation = await db.generations.find_one(
        {"id": request.generation_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    result = generation.get("result", {})
    
    return {
        "topic": generation.get("topic", ""),
        "platform": generation.get("platform", ""),
        "hasScript": bool(result.get("script")),
        "hookCount": len(result.get("hooks", [])),
        "captionCount": len(result.get("captions", [])),
        "hashtagCount": len(result.get("hashtags", [])),
        "hasCTA": bool(result.get("cta")),
        "estimatedPages": 2,
        "theme": request.theme
    }


@router.get("/history")
async def get_export_history(
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user's PDF export history"""
    exports = await db.reel_exports.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(limit).to_list(limit)
    
    return {"exports": exports, "total": len(exports)}
