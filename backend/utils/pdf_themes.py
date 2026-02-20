"""
Premium PDF Themes for Storybook Generation
Original designs - No copyrighted content
"""
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch

# =============================================================================
# THEME DEFINITIONS (All Original)
# =============================================================================

THEMES = {
    "classic": {
        "name": "Classic Storybook",
        "description": "Timeless elegant design with serif fonts",
        "primary_color": colors.HexColor("#2C3E50"),
        "secondary_color": colors.HexColor("#34495E"),
        "accent_color": colors.HexColor("#E74C3C"),
        "background_color": colors.HexColor("#FDFEFE"),
        "text_color": colors.HexColor("#2C3E50"),
        "border_color": colors.HexColor("#BDC3C7"),
        "font_family": "Times-Roman",
        "title_font": "Times-Bold",
        "border_style": "double",
        "border_radius": 0,
        "header_style": "underline"
    },
    "pastel": {
        "name": "Pastel Dreams",
        "description": "Soft, gentle colors for young readers",
        "primary_color": colors.HexColor("#F8BBD9"),
        "secondary_color": colors.HexColor("#B5EAD7"),
        "accent_color": colors.HexColor("#FFEAA7"),
        "background_color": colors.HexColor("#FFF9FB"),
        "text_color": colors.HexColor("#5D5D5D"),
        "border_color": colors.HexColor("#DDA0DD"),
        "font_family": "Helvetica",
        "title_font": "Helvetica-Bold",
        "border_style": "rounded",
        "border_radius": 15,
        "header_style": "bubble"
    },
    "storybook_deluxe": {
        "name": "Storybook Deluxe",
        "description": "Premium illustrated storybook style",
        "primary_color": colors.HexColor("#8E44AD"),
        "secondary_color": colors.HexColor("#3498DB"),
        "accent_color": colors.HexColor("#F39C12"),
        "background_color": colors.HexColor("#FEFCF3"),
        "text_color": colors.HexColor("#2D3436"),
        "border_color": colors.HexColor("#9B59B6"),
        "font_family": "Helvetica",
        "title_font": "Helvetica-Bold",
        "border_style": "decorative",
        "border_radius": 8,
        "header_style": "banner"
    },
    "adventure": {
        "name": "Adventure Quest",
        "description": "Bold and exciting for adventure stories",
        "primary_color": colors.HexColor("#1ABC9C"),
        "secondary_color": colors.HexColor("#16A085"),
        "accent_color": colors.HexColor("#E67E22"),
        "background_color": colors.HexColor("#F5F6FA"),
        "text_color": colors.HexColor("#2C3A47"),
        "border_color": colors.HexColor("#17A589"),
        "font_family": "Helvetica",
        "title_font": "Helvetica-Bold",
        "border_style": "bold",
        "border_radius": 5,
        "header_style": "flag"
    },
    "nature": {
        "name": "Forest Tales",
        "description": "Natural, earthy tones for nature stories",
        "primary_color": colors.HexColor("#27AE60"),
        "secondary_color": colors.HexColor("#2ECC71"),
        "accent_color": colors.HexColor("#D35400"),
        "background_color": colors.HexColor("#F9FBF2"),
        "text_color": colors.HexColor("#2D3436"),
        "border_color": colors.HexColor("#58D68D"),
        "font_family": "Times-Roman",
        "title_font": "Times-Bold",
        "border_style": "leaf",
        "border_radius": 10,
        "header_style": "nature"
    }
}

# =============================================================================
# SVG DECORATIVE ELEMENTS (Original Designs)
# =============================================================================

SVG_STICKERS = {
    "star": """<svg viewBox="0 0 24 24" fill="{color}"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>""",
    "heart": """<svg viewBox="0 0 24 24" fill="{color}"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>""",
    "cloud": """<svg viewBox="0 0 24 24" fill="{color}"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/></svg>""",
    "sun": """<svg viewBox="0 0 24 24" fill="{color}"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3" stroke="{color}" stroke-width="2"/><line x1="12" y1="21" x2="12" y2="23" stroke="{color}" stroke-width="2"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="{color}" stroke-width="2"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="{color}" stroke-width="2"/><line x1="1" y1="12" x2="3" y2="12" stroke="{color}" stroke-width="2"/><line x1="21" y1="12" x2="23" y2="12" stroke="{color}" stroke-width="2"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="{color}" stroke-width="2"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="{color}" stroke-width="2"/></svg>""",
    "moon": """<svg viewBox="0 0 24 24" fill="{color}"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>""",
    "flower": """<svg viewBox="0 0 24 24" fill="{color}"><circle cx="12" cy="12" r="3"/><path d="M12 2C12 2 14 6 12 9C10 6 12 2 12 2Z"/><path d="M12 22C12 22 10 18 12 15C14 18 12 22 12 22Z"/><path d="M2 12C2 12 6 10 9 12C6 14 2 12 2 12Z"/><path d="M22 12C22 12 18 14 15 12C18 10 22 12 22 12Z"/></svg>""",
    "butterfly": """<svg viewBox="0 0 24 24" fill="{color}"><ellipse cx="8" cy="10" rx="4" ry="6"/><ellipse cx="16" cy="10" rx="4" ry="6"/><ellipse cx="8" cy="16" rx="3" ry="4"/><ellipse cx="16" cy="16" rx="3" ry="4"/><line x1="12" y1="6" x2="12" y2="20" stroke="{color}" stroke-width="1"/></svg>""",
    "rainbow": """<svg viewBox="0 0 24 24"><path d="M4 18 A8 8 0 0 1 20 18" fill="none" stroke="#E74C3C" stroke-width="2"/><path d="M5 18 A7 7 0 0 1 19 18" fill="none" stroke="#F39C12" stroke-width="2"/><path d="M6 18 A6 6 0 0 1 18 18" fill="none" stroke="#F1C40F" stroke-width="2"/><path d="M7 18 A5 5 0 0 1 17 18" fill="none" stroke="#2ECC71" stroke-width="2"/><path d="M8 18 A4 4 0 0 1 16 18" fill="none" stroke="#3498DB" stroke-width="2"/><path d="M9 18 A3 3 0 0 1 15 18" fill="none" stroke="#9B59B6" stroke-width="2"/></svg>"""
}

# =============================================================================
# BORDER DECORATIONS (Original Designs)
# =============================================================================

def draw_classic_border(canvas, x, y, width, height, theme):
    """Draw classic double-line border"""
    canvas.setStrokeColor(theme["border_color"])
    canvas.setLineWidth(2)
    canvas.rect(x, y, width, height)
    canvas.setLineWidth(1)
    canvas.rect(x + 5, y + 5, width - 10, height - 10)

def draw_rounded_border(canvas, x, y, width, height, theme):
    """Draw rounded pastel border"""
    canvas.setStrokeColor(theme["border_color"])
    canvas.setFillColor(theme["background_color"])
    canvas.setLineWidth(3)
    canvas.roundRect(x, y, width, height, theme["border_radius"], stroke=1, fill=0)

def draw_decorative_border(canvas, x, y, width, height, theme):
    """Draw decorative premium border with corner ornaments"""
    canvas.setStrokeColor(theme["border_color"])
    canvas.setLineWidth(2)
    
    # Main border
    canvas.roundRect(x, y, width, height, 8, stroke=1, fill=0)
    
    # Corner decorations (simple dots)
    corner_size = 8
    canvas.setFillColor(theme["accent_color"])
    corners = [(x, y), (x + width, y), (x, y + height), (x + width, y + height)]
    for cx, cy in corners:
        canvas.circle(cx, cy, corner_size, fill=1)

def draw_nature_border(canvas, x, y, width, height, theme):
    """Draw nature-themed border with leaf corners"""
    canvas.setStrokeColor(theme["border_color"])
    canvas.setLineWidth(2)
    canvas.roundRect(x, y, width, height, 10, stroke=1, fill=0)
    
    # Simple leaf shapes at corners
    canvas.setFillColor(theme["primary_color"])
    leaf_size = 12
    # Top-left leaf
    canvas.ellipse(x - leaf_size/2, y + height - leaf_size/2, 
                   x + leaf_size/2, y + height + leaf_size/2, fill=1)

BORDER_FUNCTIONS = {
    "double": draw_classic_border,
    "rounded": draw_rounded_border,
    "decorative": draw_decorative_border,
    "leaf": draw_nature_border,
    "bold": draw_classic_border  # Use classic for bold
}

# =============================================================================
# TEXT STYLE GENERATORS
# =============================================================================

def get_title_style(theme):
    """Generate title paragraph style for theme"""
    return ParagraphStyle(
        'ThemeTitle',
        fontName=theme["title_font"],
        fontSize=28,
        textColor=theme["primary_color"],
        alignment=TA_CENTER,
        spaceAfter=20,
        spaceBefore=10
    )

def get_chapter_style(theme):
    """Generate chapter heading style for theme"""
    return ParagraphStyle(
        'ThemeChapter',
        fontName=theme["title_font"],
        fontSize=18,
        textColor=theme["secondary_color"],
        alignment=TA_CENTER,
        spaceAfter=15,
        spaceBefore=10
    )

def get_body_style(theme):
    """Generate body text style for theme"""
    return ParagraphStyle(
        'ThemeBody',
        fontName=theme["font_family"],
        fontSize=12,
        textColor=theme["text_color"],
        alignment=TA_JUSTIFY,
        spaceAfter=10,
        spaceBefore=5,
        leading=16
    )

def get_moral_style(theme):
    """Generate moral/lesson style for theme"""
    return ParagraphStyle(
        'ThemeMoral',
        fontName=theme["title_font"],
        fontSize=14,
        textColor=theme["accent_color"],
        alignment=TA_CENTER,
        spaceAfter=15,
        spaceBefore=15,
        borderColor=theme["accent_color"],
        borderWidth=1,
        borderPadding=10
    )

# =============================================================================
# PAGE LAYOUT TEMPLATES
# =============================================================================

def create_cover_page(canvas, theme, title, author=None, child_name=None):
    """Create themed cover page"""
    width, height = canvas._pagesize
    
    # Background
    canvas.setFillColor(theme["background_color"])
    canvas.rect(0, 0, width, height, fill=1)
    
    # Decorative border
    border_func = BORDER_FUNCTIONS.get(theme["border_style"], draw_classic_border)
    border_func(canvas, 30, 30, width - 60, height - 60, theme)
    
    # Title
    canvas.setFillColor(theme["primary_color"])
    canvas.setFont(theme["title_font"], 36)
    canvas.drawCentredString(width/2, height - 150, title)
    
    # Subtitle/personalization
    if child_name:
        canvas.setFont(theme["font_family"], 16)
        canvas.setFillColor(theme["secondary_color"])
        canvas.drawCentredString(width/2, height - 200, f"A Special Story for {child_name}")
    
    # Author
    if author:
        canvas.setFont(theme["font_family"], 12)
        canvas.setFillColor(theme["text_color"])
        canvas.drawCentredString(width/2, 100, f"Written with love")
    
    # Decorative element
    canvas.setFillColor(theme["accent_color"])
    canvas.circle(width/2, height/2, 30, fill=1)

def create_chapter_page(canvas, theme, chapter_num, chapter_title, content):
    """Create themed chapter page"""
    width, height = canvas._pagesize
    
    # Background
    canvas.setFillColor(theme["background_color"])
    canvas.rect(0, 0, width, height, fill=1)
    
    # Chapter number
    canvas.setFillColor(theme["accent_color"])
    canvas.setFont(theme["title_font"], 14)
    canvas.drawCentredString(width/2, height - 60, f"Chapter {chapter_num}")
    
    # Chapter title
    canvas.setFillColor(theme["primary_color"])
    canvas.setFont(theme["title_font"], 22)
    canvas.drawCentredString(width/2, height - 90, chapter_title)
    
    # Divider line
    canvas.setStrokeColor(theme["border_color"])
    canvas.setLineWidth(1)
    canvas.line(width/4, height - 110, 3*width/4, height - 110)

def create_moral_page(canvas, theme, moral_text):
    """Create themed moral/lesson page"""
    width, height = canvas._pagesize
    
    # Background
    canvas.setFillColor(theme["background_color"])
    canvas.rect(0, 0, width, height, fill=1)
    
    # Header
    canvas.setFillColor(theme["accent_color"])
    canvas.setFont(theme["title_font"], 24)
    canvas.drawCentredString(width/2, height - 150, "The Lesson We Learned")
    
    # Decorative box for moral
    box_x = width/4
    box_y = height/2 - 50
    box_width = width/2
    box_height = 100
    
    canvas.setStrokeColor(theme["accent_color"])
    canvas.setFillColor(colors.HexColor("#FFFBEA"))
    canvas.setLineWidth(3)
    canvas.roundRect(box_x, box_y, box_width, box_height, 10, stroke=1, fill=1)
    
    # Moral text
    canvas.setFillColor(theme["text_color"])
    canvas.setFont(theme["font_family"], 14)
    # Wrap text (simplified)
    canvas.drawCentredString(width/2, height/2, moral_text[:80])

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'THEMES',
    'SVG_STICKERS',
    'BORDER_FUNCTIONS',
    'get_title_style',
    'get_chapter_style',
    'get_body_style',
    'get_moral_style',
    'create_cover_page',
    'create_chapter_page',
    'create_moral_page',
    'draw_classic_border',
    'draw_rounded_border',
    'draw_decorative_border',
    'draw_nature_border'
]
