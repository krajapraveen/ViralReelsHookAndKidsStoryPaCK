"""
CreatorStudio AI - Modular FastAPI Application
Refactored from monolithic server.py to use modular routes
"""
from fastapi import FastAPI, APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import sys
import logging
from pathlib import Path
import asyncio
import uuid
import glob
from datetime import datetime, timezone

# Setup path for imports
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("creatorstudio")

# Import shared modules
from shared import (
    db, client, hash_password, FILE_EXPIRY_MINUTES, get_admin_user, db_name as DB_NAME
)

# Import security modules
from security import (
    limiter, rate_limit_exceeded_handler,
    add_security_headers, security_middleware
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import route modules
from routes.auth import router as auth_router
from routes.credits import router as credits_router
from routes.generation import router as generate_router
# Old Razorpay payments router removed - using Cashfree only
# from routes.payments import router as payments_router
from routes.feedback import router as feedback_router
from routes.admin import router as admin_router
from routes.health import router as health_router
from routes.genstudio import genstudio_router
from routes.creator_pro import router as creator_pro_router
from routes.twin_finder import router as twinfinder_router
from routes.content_vault import router as content_router
from routes.story_tools import router as story_tools_router
from routes.creator_tools import router as creator_tools_router
from routes.convert_tools import router as convert_router
from routes.cashfree_payments import router as cashfree_router
from routes.privacy import router as privacy_router
from routes.wallet import router as wallet_router
from routes.sse import router as sse_router
from routes.coloring_book import router as coloring_book_router
from routes.coloring_book_v2 import router as coloring_book_v2_router
from routes.story_series import router as story_series_router
from routes.challenge_generator import router as challenge_router
from routes.tone_switcher import router as tone_switcher_router
from routes.regional_pricing import router as regional_pricing_router
from routes.analytics import router as analytics_router
from routes.subscriptions import router as subscriptions_router
from routes.user_manual import router as user_manual_router
from routes.feature_requests import router as feature_requests_router
from routes.activity_monitoring import router as activity_router
from routes.reel_export import router as reel_export_router
from routes.cashfree_webhook_handler import router as cashfree_webhook_router
from routes.security_monitoring import router as security_router
from routes.ab_testing import router as ab_testing_router
from routes.push_notifications import router as push_notifications_router
from routes.comix_ai import router as comix_router
from routes.gif_maker import router as gif_maker_router
from routes.comic_storybook import router as comic_storybook_router
from routes.login_activity import router as login_activity_router
from routes.content import router as content_router
from routes.realtime_analytics import router as realtime_analytics_router
from routes.user_analytics import router as user_analytics_router, user_router as user_analytics_user_router
from routes.sre_monitoring import router as sre_monitoring_router
from routes.monetization import router as monetization_router
from routes.share import router as share_router
from routes.photo_to_comic import router as photo_to_comic_router
from routes.referral import router as referral_router
from routes.comic_storybook_v2 import router as comic_storybook_v2_router
from routes.reaction_gif import router as reaction_gif_router

# DAILY REWARDS & GAMIFICATION
from routes.daily_rewards_routes import router as daily_rewards_router

# USER PROFILE ROUTES
from routes.user_routes import router as user_profile_router

# HEALTH AND MONITORING
from routes.health_routes import router as health_router

# CONTENT PROTECTION (PDF Flattening & Video Streaming)
from routes.content_protection_routes import router as content_protection_router

# NEW REBUILT FEATURES
from routes.story_episode_creator import router as story_episode_creator_router
from routes.content_challenge_planner import router as content_challenge_planner_router
from routes.caption_rewriter_pro import router as caption_rewriter_pro_router

# REVENUE PROTECTION & AUDIT SYSTEM
from routes.audit_dashboard import router as audit_dashboard_router
from routes.content_blueprint_library import router as blueprint_library_router
from routes.security_management import router as security_management_router

# NEW FEATURE: Instagram Bio Generator
from routes.instagram_bio_generator import router as instagram_bio_generator_router

# NEW FEATURE: Comment Reply Bank
from routes.comment_reply_bank import router as comment_reply_bank_router

# NEW FEATURE: Bedtime Story Builder
from routes.bedtime_story_builder import router as bedtime_story_builder_router

# NEW FEATURES: 5 Template-Based Tools + Analytics
from routes.youtube_thumbnail_generator import router as youtube_thumbnail_router
from routes.brand_story_builder import router as brand_story_router
from routes.offer_generator import router as offer_generator_router
from routes.story_hook_generator import router as story_hook_router
from routes.daily_viral_ideas import router as daily_viral_ideas_router
from routes.template_analytics import router as template_analytics_router

# NEW: Admin Audit Logs, Protected Downloads, Leaderboard, Versioning
from routes.admin_audit_logs import router as admin_audit_logs_router
from routes.protected_download import router as protected_download_router
from routes.template_leaderboard import router as template_leaderboard_router
from routes.template_versioning import router as template_versioning_router

# Webhook Retry Queue
from services.webhook_retry_queue import WebhookRetryQueue, webhook_queue

# Security middleware
from middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware

# Self-healing system imports
from routes.self_healing_monitoring import router as self_healing_monitoring_router
from routes.recovery_ui import router as recovery_ui_router
from routes.priority_scaling import router as priority_scaling_router
from routes.admin_system_routes import router as admin_system_router
from routes.admin_worker_routes import router as admin_worker_router
from routes.download_expiry_routes import router as download_expiry_router
from routes.notification_routes import router as notification_router
from services.self_healing_middleware import SelfHealingMiddleware
from services.priority_scaling_service import initialize_priority_scaling, shutdown_priority_scaling

# Daily Report Service
from routes.daily_report_routes import router as daily_report_router
from services.daily_report_scheduler import start_scheduler, stop_scheduler

# Account Lock Management
from routes.account_lock_routes import router as account_lock_router

# Environment Monitoring
from routes.environment_monitor_routes import router as environment_monitor_router
from services.environment_monitor_scheduler import start_env_scheduler, stop_env_scheduler

# WebSocket Real-Time Progress
from routes.websocket_progress import router as websocket_progress_router

# Job Queue Routes
from routes.job_queue_routes import router as job_queue_router

# Character Consistency Routes  
from routes.character_routes import router as character_routes_router

# Performance and stability module
from performance import (
    PerformanceMiddleware,
    create_performance_indexes,
    get_performance_report,
    run_health_checks,
    performance_maintenance_loop,
    metrics,
    cache,
    idempotency,
    job_retry,
    stuck_recovery
)

# SRE Phase 2 & 3 Services
from services.database_indexes import create_all_indexes, get_index_status
from services.idempotency_service import get_idempotency_service
from services.fallback_output_service import get_fallback_service

# Create FastAPI app
app = FastAPI(
    title="CreatorStudio AI API",
    description="AI-powered content generation platform for viral reels and kids story videos",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add rate limiter - must add middleware for decorator-based limits to work
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add SlowAPI middleware - CRITICAL for rate limiting to work
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)

# Add Security Headers middleware - OWASP compliance
app.add_middleware(SecurityHeadersMiddleware)

# Add GZip compression middleware for responses
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add Performance middleware for metrics and correlation IDs (before Self-Healing)
app.add_middleware(PerformanceMiddleware)

# Add Self-Healing middleware for request tracking and correlation IDs
app.add_middleware(SelfHealingMiddleware)

# ==================== MIDDLEWARE ====================

# Global rate limiting configuration
RATE_LIMITS = {
    "default": "100/minute",      # General API calls
    "auth": "10/minute",          # Login/Register
    "generation": "20/minute",    # AI generation endpoints
    "admin": "50/minute",         # Admin endpoints
}

@app.middleware("http")
async def global_rate_limit_middleware(request: Request, call_next):
    """Apply global rate limiting based on endpoint type"""
    from slowapi.util import get_remote_address
    
    path = request.url.path
    client_ip = get_remote_address(request)
    
    # Skip rate limiting for health checks and static files
    if path in ["/api/health/", "/api/docs", "/api/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Log request for monitoring
    logger.debug(f"Request from {client_ip}: {request.method} {path}")
    
    return await call_next(request)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add comprehensive security headers to all responses"""
    response = await call_next(request)
    
    # Skip strict security headers for static files (images, downloads)
    path = request.url.path
    if path.startswith("/api/static/"):
        # Allow downloads and image display for static files
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        # Don't set CORS here - let CORSMiddleware handle it
        return response
    
    # Basic Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Content Security Policy (CSP) - Prevents XSS and other injection attacks
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://checkout.razorpay.com https://api.razorpay.com https://sdk.cashfree.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob: https: http:",
        "connect-src 'self' https://api.razorpay.com https://checkout.razorpay.com https://*.cashfree.com https://sdk.cashfree.com https://*.emergentagent.com wss:",
        "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com https://*.cashfree.com https://sdk.cashfree.com https://auth.emergentagent.com",
        "media-src 'self' blob: https:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests"
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
    
    # Additional Security Headers
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(self)"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Cross-Origin-Embedder-Policy"] = "credentialless"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    
    return response

# CORS Configuration - Restricted to specific allowed origins for security
cors_origins_env = os.environ.get('CORS_ORIGINS', '')

# Always include critical domains for production
CRITICAL_ORIGINS = [
    "https://visionary-suite.com",
    "https://www.visionary-suite.com",
    "https://auth.emergentagent.com",
    "https://studio-deploy-2.emergent.host",
    "https://video-job-queue-1.preview.emergentagent.com",
    "http://localhost:3000",
    "http://localhost:8001"
]

# Build allowed origins list
if cors_origins_env:
    # Allow wildcard for development/testing
    if cors_origins_env.strip() == '*':
        ALLOWED_ORIGINS = ['*']
    else:
        # Parse comma-separated list of additional origins
        additional_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
        ALLOWED_ORIGINS = list(set(CRITICAL_ORIGINS + additional_origins))
else:
    ALLOWED_ORIGINS = CRITICAL_ORIGINS

logger.info(f"CORS configured with origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Accept", "Origin"],
    expose_headers=["Content-Disposition", "X-Request-Id"],
    max_age=600,  # Cache preflight for 10 minutes
)

# ==================== ROUTERS ====================

# Create main API router
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(auth_router)
api_router.include_router(credits_router)
api_router.include_router(generate_router)
# Old Razorpay router removed
# api_router.include_router(payments_router)
api_router.include_router(feedback_router)
api_router.include_router(admin_router)
api_router.include_router(health_router)
api_router.include_router(genstudio_router)
api_router.include_router(creator_pro_router)
api_router.include_router(twinfinder_router)
api_router.include_router(content_router)
api_router.include_router(story_tools_router)
api_router.include_router(creator_tools_router)
api_router.include_router(convert_router)
api_router.include_router(cashfree_router)
api_router.include_router(privacy_router)
api_router.include_router(wallet_router)
api_router.include_router(sse_router)
api_router.include_router(coloring_book_router)
api_router.include_router(coloring_book_v2_router)
api_router.include_router(story_series_router)
api_router.include_router(challenge_router)
api_router.include_router(tone_switcher_router)
api_router.include_router(regional_pricing_router)
api_router.include_router(analytics_router)
api_router.include_router(subscriptions_router)
api_router.include_router(user_manual_router)
api_router.include_router(feature_requests_router)
api_router.include_router(activity_router)
api_router.include_router(reel_export_router)
api_router.include_router(cashfree_webhook_router)
api_router.include_router(security_router)
api_router.include_router(ab_testing_router)
api_router.include_router(push_notifications_router)
api_router.include_router(comix_router)
api_router.include_router(gif_maker_router)
api_router.include_router(comic_storybook_router)
api_router.include_router(login_activity_router)
api_router.include_router(content_router)
api_router.include_router(realtime_analytics_router)
api_router.include_router(user_analytics_router)
api_router.include_router(user_analytics_user_router)  # User-facing analytics endpoints

# Self-healing system routes
api_router.include_router(self_healing_monitoring_router)
api_router.include_router(recovery_ui_router)
api_router.include_router(priority_scaling_router)
api_router.include_router(sre_monitoring_router)
api_router.include_router(monetization_router)
api_router.include_router(share_router)
api_router.include_router(photo_to_comic_router)
api_router.include_router(referral_router)
api_router.include_router(comic_storybook_v2_router)
api_router.include_router(reaction_gif_router)

# NEW REBUILT FEATURES
api_router.include_router(story_episode_creator_router)
api_router.include_router(content_challenge_planner_router)
api_router.include_router(caption_rewriter_pro_router)

# REVENUE PROTECTION & AUDIT SYSTEM
api_router.include_router(audit_dashboard_router)
api_router.include_router(blueprint_library_router)
api_router.include_router(security_management_router)

# NEW FEATURE: Instagram Bio Generator
api_router.include_router(instagram_bio_generator_router)

# NEW FEATURE: Comment Reply Bank
api_router.include_router(comment_reply_bank_router)

# NEW FEATURE: Bedtime Story Builder
api_router.include_router(bedtime_story_builder_router)

# NEW FEATURES: 5 Template-Based Tools + Analytics
api_router.include_router(youtube_thumbnail_router)
api_router.include_router(brand_story_router)
api_router.include_router(offer_generator_router)
api_router.include_router(story_hook_router)
api_router.include_router(daily_viral_ideas_router)
api_router.include_router(template_analytics_router)

# NEW: Admin Audit Logs, Protected Downloads, Leaderboard, Versioning
api_router.include_router(admin_audit_logs_router)
api_router.include_router(protected_download_router)
api_router.include_router(template_leaderboard_router)
api_router.include_router(template_versioning_router)
api_router.include_router(admin_system_router)
api_router.include_router(admin_worker_router)
api_router.include_router(download_expiry_router)
api_router.include_router(notification_router)
api_router.include_router(user_profile_router)
api_router.include_router(health_router)
api_router.include_router(content_protection_router)

# Daily Report Service
api_router.include_router(daily_report_router)

# Account Lock Management
api_router.include_router(account_lock_router)

# Environment Monitoring
api_router.include_router(environment_monitor_router)

# Daily Rewards & Gamification
api_router.include_router(daily_rewards_router)

# Live Stats & User Activity Tracking
from routes.live_stats_routes import router as live_stats_router
api_router.include_router(live_stats_router)

# System Health Dashboard
from routes.system_health_routes import router as system_health_router
api_router.include_router(system_health_router)

# Anti-Abuse Protection
from routes.anti_abuse_routes import router as anti_abuse_router
api_router.include_router(anti_abuse_router)

# Organic Reviews System
from routes.reviews import router as reviews_router
api_router.include_router(reviews_router)

# Watermark Service for Social Sharing
from routes.watermark import router as watermark_router
api_router.include_router(watermark_router)

# Blog/Content Pages for SEO
from routes.blog import router as blog_router
api_router.include_router(blog_router)

# Revenue Analytics Dashboard
from routes.revenue_analytics import router as revenue_analytics_router
api_router.include_router(revenue_analytics_router)

# Monitoring & Load Testing
from routes.monitoring import router as monitoring_router
api_router.include_router(monitoring_router)

# Story → Images → Video Studio (NEW FEATURE)
from routes.story_video_studio import router as story_video_studio_router
api_router.include_router(story_video_studio_router)

# Story Video Generation - Phase 2, 3, 4
from routes.story_video_generation import router as story_video_generation_router
api_router.include_router(story_video_generation_router)

# Story Video FAST Generation - Parallel Processing Engine
from routes.story_video_fast import router as story_video_fast_router
api_router.include_router(story_video_fast_router)

# Story Video Analytics & Performance Monitoring
from routes.story_video_analytics import router as story_video_analytics_router
api_router.include_router(story_video_analytics_router)

# Story Video Preview Mode & Character Consistency
from routes.story_video_preview import router as story_video_preview_router
api_router.include_router(story_video_preview_router)

# Story Video Templates, Social Sharing & Waiting Games
from routes.story_video_templates import router as story_video_templates_router
api_router.include_router(story_video_templates_router)

# Pipeline Routes (new durable pipeline)
from routes.pipeline_routes import router as pipeline_router
api_router.include_router(pipeline_router)

# Blog Content for SEO
from routes.blog_content import router as blog_router
api_router.include_router(blog_router)

# Job Queue Routes
api_router.include_router(job_queue_router)

# Character Consistency Routes
api_router.include_router(character_routes_router)

# Include API router in app
app.include_router(api_router)

# WebSocket endpoint - mount both with and without /api prefix for compatibility
app.include_router(websocket_progress_router)

# Also mount WebSocket under /api for frontend compatibility
from fastapi import APIRouter
ws_api_router = APIRouter(prefix="/api")
ws_api_router.include_router(websocket_progress_router)
app.include_router(ws_api_router)

# ==================== STATIC FILE SERVING ====================

# Create static directory for generated images if it doesn't exist
STATIC_DIR = ROOT_DIR / "static" / "generated"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for serving generated images at multiple paths for compatibility
app.mount("/api/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="api_static")
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="static")

# Dedicated route for generated files (works regardless of ingress routing)
from fastapi.responses import FileResponse

@app.get("/api/generated/{filename:path}")
async def serve_generated_file(filename: str):
    filepath = ROOT_DIR / "static" / "generated" / filename
    if filepath.exists() and filepath.is_file():
        return FileResponse(filepath)
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/api/promo-videos/status")
async def get_promo_video_status():
    """Get status of promotional video generation"""
    import json as json_lib
    status_file = ROOT_DIR / "static" / "generated" / "video_gen_status.json"
    videos_info = [
        {"id": "instagram_reel", "label": "Instagram Reel", "filename": "visionary_suite_instagram_reel.mp4", "platform": "Instagram", "format": "Reel (9:16)", "duration": "12s"},
        {"id": "instagram_story", "label": "Instagram Story", "filename": "visionary_suite_instagram_story.mp4", "platform": "Instagram", "format": "Story (9:16)", "duration": "8s"},
        {"id": "youtube_shorts", "label": "YouTube Shorts", "filename": "visionary_suite_youtube_shorts.mp4", "platform": "YouTube", "format": "Shorts (9:16)", "duration": "12s"},
        {"id": "facebook_reel", "label": "Facebook Reel", "filename": "visionary_suite_facebook_reel.mp4", "platform": "Facebook", "format": "Reel (9:16)", "duration": "12s"},
    ]
    status_data = {}
    if status_file.exists():
        with open(status_file, "r") as f:
            status_data = json_lib.load(f)
    result = []
    for v in videos_info:
        s = status_data.get(v["id"], {})
        file_path = ROOT_DIR / "static" / "generated" / v["filename"]
        file_exists = file_path.exists()
        file_size = round(file_path.stat().st_size / (1024 * 1024), 1) if file_exists else 0
        result.append({
            **v,
            "status": "COMPLETED" if file_exists else ("FILE_MISSING" if s.get("status") == "COMPLETED" else s.get("status", "NOT_STARTED")),
            "downloadUrl": f"/api/generated/{v['filename']}" if file_exists else None,
            "fileSizeMB": file_size,
            "error": s.get("error"),
            "updatedAt": s.get("updated")
        })
    return {"videos": result}

# ==================== ROOT ENDPOINTS ====================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "CreatorStudio AI API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/api/docs",
            "health": "/api/health"
        }
    }

@app.get("/health")
async def root_health():
    """Root health check"""
    return {"status": "healthy", "version": "2.0.0"}

# ==================== PERFORMANCE ENDPOINTS ====================

@app.get("/api/performance/metrics")
async def get_metrics():
    """Get current performance metrics"""
    return await get_performance_report()

@app.get("/api/performance/health")
async def get_detailed_health():
    """Get detailed health check with all subsystems"""
    return await run_health_checks()

@app.post("/api/performance/recover-stuck-jobs")
async def trigger_stuck_job_recovery(admin: dict = Depends(get_admin_user)):
    """Manually trigger stuck job recovery"""
    recovered = await stuck_recovery.recover_stuck_jobs()
    return {"recovered_count": recovered, "status": "success"}

@app.get("/api/performance/cache-stats")
async def get_cache_stats():
    """Get cache statistics"""
    return cache.get_stats()

# ==================== STARTUP/SHUTDOWN ====================

async def cleanup_expired_downloads():
    """Background task to clean up expired files every minute - FILES EXPIRE IN 3 MINUTES"""
    while True:
        try:
            logger.info("Running security cleanup task...")
            
            # Delete all expired printable books (3 min expiry)
            result = await db.printable_books.delete_many({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"SECURITY: Cleaned up {result.deleted_count} expired printable book(s)")
            
            # Delete all expired GenStudio jobs (3 min expiry) and their files
            expired_jobs = await db.genstudio_jobs.find({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            }).to_list(100)
            
            for job in expired_jobs:
                job_id = job.get("id", "")
                # Delete associated files - all patterns
                for pattern in [f"/tmp/genstudio_{job_id}*", f"/tmp/genstudio_input_{job_id}*", f"/tmp/genstudio_remix_{job_id}*"]:
                    for filepath in glob.glob(pattern):
                        try:
                            os.remove(filepath)
                            logger.info(f"SECURITY: Deleted expired file: {filepath}")
                        except Exception as e:
                            logger.warning(f"Failed to delete file {filepath}: {e}")
            
            # Delete expired job records
            result = await db.genstudio_jobs.delete_many({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"SECURITY: Cleaned up {result.deleted_count} expired GenStudio job(s)")
            
            # AGGRESSIVE CLEANUP: Delete any temp files older than 3 minutes
            current_time = datetime.now(timezone.utc)
            for pattern in ["/tmp/genstudio_*", "/tmp/printable_*", "/tmp/story_*", "/tmp/reel_*", "/tmp/style_profile_*"]:
                for filepath in glob.glob(pattern):
                    try:
                        file_age = current_time.timestamp() - os.path.getmtime(filepath)
                        if file_age > (FILE_EXPIRY_MINUTES * 60):  # 3 minutes in seconds
                            os.remove(filepath)
                            logger.info(f"SECURITY: Force-deleted old file: {filepath}")
                    except Exception:
                        pass
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        await asyncio.sleep(60)  # Run every minute


@app.on_event("startup")
async def startup():
    """Application startup - create indexes, seed data, start background tasks"""
    logger.info("CreatorStudio API starting...")
    
    # Create database indexes
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("id", unique=True)
        await db.generations.create_index("userId")
        await db.generations.create_index("id", unique=True)
        await db.feedback.create_index("id", unique=True)
        await db.orders.create_index("userId")
        await db.orders.create_index("order_id", unique=True)  # For payment lookups
        await db.orders.create_index([("gateway", 1), ("status", 1)])  # For admin queries
        await db.credit_ledger.create_index("userId")
        await db.credit_ledger.create_index([("userId", 1), ("orderId", 1)])  # For refund verification
        await db.printable_books.create_index("expiresAt")
        await db.genstudio_jobs.create_index("userId")
        await db.genstudio_jobs.create_index("expiresAt")
        await db.style_profiles.create_index("userId")
        await db.twinfinder_analyses.create_index("userId")
        await db.consistency_tracker.create_index("userId")
        await db.webhook_logs.create_index("order_id")  # For webhook deduplication
        await db.webhook_logs.create_index([("gateway", 1), ("event", 1), ("received_at", -1)])
        await db.refund_logs.create_index("orderId")  # For refund tracking
        await db.payment_logs.create_index([("userId", 1), ("timestamp", -1)])
        # Wallet & Job Pipeline indexes
        await db.idempotency_keys.create_index([("userId", 1), ("idempotencyKey", 1)], unique=True)
        await db.idempotency_keys.create_index("expiresAt")
        await db.credit_ledger.create_index([("refId", 1), ("entryType", 1)])  # For job lookups
        
        # New Apps indexes (Story Series, Challenge Generator, Tone Switcher)
        await db.story_series.create_index("userId")
        await db.story_series.create_index([("userId", 1), ("createdAt", -1)])
        await db.content_challenges.create_index("userId")
        await db.content_challenges.create_index([("userId", 1), ("createdAt", -1)])
        await db.tone_rewrites.create_index("userId")
        await db.tone_rewrites.create_index([("userId", 1), ("createdAt", -1)])
        await db.coloring_book_exports.create_index("userId")
        await db.coloring_book_exports.create_index([("userId", 1), ("createdAt", -1)])
        
        # Notification indexes
        await db.notifications.create_index("user_id")
        await db.notifications.create_index([("user_id", 1), ("read", 1)])
        await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
        
        # Live Stats & User Activity indexes (CRITICAL for admin panel performance)
        await db.user_sessions.create_index([("last_active", -1)])
        await db.user_activity_log.create_index([("timestamp", -1)])
        await db.user_activity_log.create_index([("user_id", 1), ("timestamp", -1)])
        await db.reel_generator_jobs.create_index([("created_at", -1)])
        await db.reel_generator_jobs.create_index([("user_id", 1), ("created_at", -1)])
        await db.story_generator_jobs.create_index([("created_at", -1)])
        await db.story_generator_jobs.create_index([("user_id", 1), ("created_at", -1)])
        
        # Pipeline jobs indexes
        await db.pipeline_jobs.create_index("job_id", unique=True)
        await db.pipeline_jobs.create_index([("user_id", 1), ("created_at", -1)])
        await db.pipeline_jobs.create_index("status")
        
        logger.info("Database indexes created")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")
    
    # Create admin user if not exists (ONE-TIME SEED ONLY)
    # SECURITY FIX: Do NOT reset admin password on every restart
    admin = await db.users.find_one({"email": "admin@creatorstudio.ai"})
    if not admin:
        admin_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": admin_id,
            "name": "Admin",
            "email": "admin@creatorstudio.ai",
            "password": hash_password("Cr3@t0rStud!o#2026"),
            "role": "ADMIN",
            "credits": 999999999,  # Unlimited credits for admin
            "plan": "admin",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Admin user created with unlimited credits")
    else:
        # Only update credits and role, NOT password (security fix)
        await db.users.update_one(
            {"email": "admin@creatorstudio.ai"},
            {"$set": {
                "credits": 999999999,  # Unlimited credits for admin
                "plan": "admin",
                "role": "ADMIN"
                # NOTE: Password is NOT reset - preserves manually changed passwords
            }}
        )
        logger.info("Admin user credits verified (password preserved)")
    
    # Create demo user if not exists (ONE-TIME SEED ONLY)
    # SECURITY FIX: Do NOT reset demo password on every restart
    demo = await db.users.find_one({"email": "demo@example.com"})
    if not demo:
        demo_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": demo_id,
            "name": "Demo User",
            "email": "demo@example.com",
            "password": hash_password("Password123!"),
            "role": "USER",
            "credits": 999999999,  # Unlimited credits for demo user
            "plan": "demo",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Demo user created with unlimited credits")
    else:
        # Only update credits and plan, NOT password (security fix)
        await db.users.update_one(
            {"email": "demo@example.com"},
            {"$set": {
                "credits": 999999999,  # Unlimited credits for demo user
                "plan": "demo"
                # NOTE: Password is NOT reset - preserves manually changed passwords
            }}
        )
        logger.info("Demo user credits verified (password preserved)")
    
    # Give 100 free credits to all existing users who have less than 100 credits
    # This is a one-time bonus for production go-live
    result = await db.users.update_many(
        {
            "email": {"$nin": ["admin@creatorstudio.ai", "demo@example.com"]},
            "credits": {"$lt": 100}
        },
        {"$set": {"credits": 100}}
    )
    if result.modified_count > 0:
        logger.info(f"Granted 100 credits to {result.modified_count} existing users")
    
    # Start background cleanup task
    asyncio.create_task(cleanup_expired_downloads())
    
    # Start job worker
    asyncio.create_task(job_worker_loop())
    
    # IMPORTANT: Stagger heavy service startups to prevent OOM on production
    # Start dedicated pipeline workers for Story → Video (delayed for stability)
    async def _delayed_pipeline_start():
        await asyncio.sleep(10)  # Let server stabilize first
        try:
            from services.pipeline_worker import start_workers as start_pipeline_workers
            await start_pipeline_workers()
            logger.info("Pipeline workers started (delayed)")
        except Exception as e:
            logger.warning(f"Pipeline worker startup warning: {e}")
    asyncio.create_task(_delayed_pipeline_start())
    
    # Initialize self-healing system
    try:
        from services.self_healing_core import initialize_self_healing
        await initialize_self_healing()
        logger.info("Self-healing system initialized")
    except Exception as e:
        logger.warning(f"Self-healing initialization warning: {e}")
    
    # Start payment reconciliation background task
    try:
        from services.payment_recovery_service import start_payment_reconciliation_task
        asyncio.create_task(start_payment_reconciliation_task())
        logger.info("Payment reconciliation task started")
    except Exception as e:
        logger.warning(f"Payment reconciliation task warning: {e}")
    
    # Start auto-scaling engine
    try:
        await initialize_priority_scaling()
        logger.info("Auto-scaling and priority lanes initialized")
    except Exception as e:
        logger.warning(f"Auto-scaling initialization warning: {e}")
    
    # Initialize enhanced worker pools (deferred start for stability)
    async def _delayed_worker_system():
        await asyncio.sleep(15)
        try:
            from services.enhanced_worker_system import get_worker_system
            worker_system = get_worker_system(db)
            
            async def comic_avatar_handler(payload): return {"status": "processed"}
            async def comic_strip_handler(payload): return {"status": "processed"}
            async def gif_maker_handler(payload): return {"status": "processed"}
            async def coloring_book_handler(payload): return {"status": "processed"}
            async def reel_generator_handler(payload): return {"status": "processed"}
            async def story_generator_handler(payload): return {"status": "processed"}
            
            worker_system.register_feature("comic_avatar", comic_avatar_handler)
            worker_system.register_feature("comic_strip", comic_strip_handler)
            worker_system.register_feature("gif_maker", gif_maker_handler)
            worker_system.register_feature("coloring_book", coloring_book_handler)
            worker_system.register_feature("reel_generator", reel_generator_handler)
            worker_system.register_feature("story_generator", story_generator_handler)
            
            await worker_system.start()
            logger.info("Enhanced worker pools initialized (delayed)")
        except Exception as e:
            logger.warning(f"Worker system initialization warning: {e}")
    asyncio.create_task(_delayed_worker_system())
    
    # Initialize download expiry service
    try:
        from services.download_expiry_service import get_download_service
        download_service = get_download_service(db)
        await download_service.start()
        logger.info("Download expiry service started (5-minute expiry)")
    except Exception as e:
        logger.warning(f"Download expiry service warning: {e}")
    
    # Initialize generated files cleanup service
    try:
        from services.generated_files_cleanup import start_cleanup_service
        await start_cleanup_service(db)
        logger.info("Generated files cleanup service started (5-minute expiry)")
    except Exception as e:
        logger.warning(f"Generated files cleanup service warning: {e}")
    
    # Create performance indexes
    try:
        await create_performance_indexes()
        logger.info("Performance indexes created")
    except Exception as e:
        logger.warning(f"Performance index creation warning: {e}")
    
    # Initialize Webhook Retry Queue
    try:
        import services.webhook_retry_queue as wrq
        wrq.webhook_queue = WebhookRetryQueue(db)
        await wrq.webhook_queue.initialize()
        asyncio.create_task(wrq.webhook_queue.start_worker(interval=30))
        logger.info("Webhook retry queue initialized and worker started")
    except Exception as e:
        logger.warning(f"Webhook queue initialization warning: {e}")
    
    # Create comprehensive database indexes (SRE Phase 2)
    try:
        index_report = await create_all_indexes(db)
        logger.info(f"Database indexes: {len(index_report.get('created', []))} created, {len(index_report.get('existing', []))} existing")
    except Exception as e:
        logger.warning(f"Database index creation warning: {e}")
    
    # Initialize idempotency service (SRE Phase 3)
    try:
        await get_idempotency_service(db)
        logger.info("Idempotency service initialized")
    except Exception as e:
        logger.warning(f"Idempotency service warning: {e}")
    
    # Initialize fallback output service (SRE Phase 3)
    try:
        await get_fallback_service(db)
        logger.info("Fallback output service initialized")
    except Exception as e:
        logger.warning(f"Fallback output service warning: {e}")
    
    # Start performance maintenance loop
    try:
        asyncio.create_task(performance_maintenance_loop())
        logger.info("Performance maintenance loop started")
    except Exception as e:
        logger.warning(f"Performance maintenance loop warning: {e}")
    
    # Start Daily Report Scheduler
    try:
        start_scheduler(db)
        logger.info("Daily report scheduler started (sends at 23:55 UTC)")
    except Exception as e:
        logger.warning(f"Daily report scheduler warning: {e}")
    
    # Start Environment Monitor Scheduler
    try:
        MONGO_URL = os.environ.get("MONGO_URL", "")
        start_env_scheduler(db, DB_NAME, MONGO_URL)
        logger.info("Environment monitor scheduler started (checks every 5 minutes)")
    except Exception as e:
        logger.warning(f"Environment monitor scheduler warning: {e}")
    
    # Initialize Async Job Queue (deferred for stability)
    async def _delayed_job_queue():
        await asyncio.sleep(20)
        try:
            from services.job_queue_service import init_job_queue
            job_queue = await init_job_queue()
            logger.info("Async job queue initialized (delayed)")
        except Exception as e:
            logger.warning(f"Job queue initialization warning: {e}")
    asyncio.create_task(_delayed_job_queue())
    
    logger.info("CreatorStudio API ready!")


async def job_worker_loop():
    """Background job worker - processes QUEUED jobs"""
    from routes.job_worker import process_job
    
    logger.info("Job Worker started as background task")
    
    POLL_INTERVAL = 3
    MAX_CONCURRENT = 2
    
    while True:
        try:
            queued_jobs = await db.genstudio_jobs.find(
                {"status": "QUEUED"},
                {"_id": 0}
            ).sort("createdAt", 1).limit(MAX_CONCURRENT).to_list(MAX_CONCURRENT)
            
            if queued_jobs:
                logger.info(f"Job Worker: Processing {len(queued_jobs)} queued jobs")
                tasks = [process_job(job) for job in queued_jobs]
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Job Worker error: {e}")
        
        await asyncio.sleep(POLL_INTERVAL)


@app.on_event("shutdown")
async def shutdown():
    """Application shutdown"""
    # Stop daily report scheduler
    try:
        stop_scheduler()
    except Exception as e:
        logger.warning(f"Daily report scheduler shutdown warning: {e}")
    
    # Stop environment monitor scheduler
    try:
        stop_env_scheduler()
    except Exception as e:
        logger.warning(f"Environment monitor scheduler shutdown warning: {e}")
    
    # Shutdown auto-scaling engine
    try:
        await shutdown_priority_scaling()
    except Exception as e:
        logger.warning(f"Auto-scaling shutdown warning: {e}")
    
    # Stop generated files cleanup service
    try:
        from services.generated_files_cleanup import stop_cleanup_service
        await stop_cleanup_service()
    except Exception as e:
        logger.warning(f"Generated files cleanup service shutdown warning: {e}")
    
    client.close()
    logger.info("CreatorStudio API shutdown")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
