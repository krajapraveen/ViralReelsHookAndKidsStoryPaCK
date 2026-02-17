"""
CreatorStudio AI - Routes Package
All API routes organized by domain
"""

# Import all routers
from .auth import router as auth_router
from .credits import router as credits_router
from .generation import router as generation_router
from .payments import router as payments_router
from .admin import router as admin_router
from .health import router as health_router
from .feedback import router as feedback_router
from .genstudio import genstudio_router
from .content_vault import router as content_router
from .story_tools import router as story_tools_router
from .creator_tools import router as creator_tools_router
from .convert_tools import router as convert_router

__all__ = [
    'auth_router',
    'credits_router',
    'generation_router',
    'payments_router',
    'admin_router',
    'health_router',
    'feedback_router',
    'genstudio_router',
    'content_router',
    'story_tools_router',
    'creator_tools_router',
    'convert_router',
]
