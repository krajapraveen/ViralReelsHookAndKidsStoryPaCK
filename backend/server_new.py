"""
CreatorStudio AI - Main Server (Refactored)
Modular architecture with separate route files
"""
import os
import logging
import asyncio
import glob
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import shared dependencies
from shared import db, logger, FILE_EXPIRY_MINUTES

# Import security modules
from security import (
    limiter, rate_limit_exceeded_handler, SECURITY_HEADERS,
    log_security_event, record_suspicious_activity
)
from slowapi.errors import RateLimitExceeded

# Import ML threat detection
from ml_threat_detection import threat_intel

# Import route modules
from routes.style_profiles import style_profile_router
from routes.convert import convert_router

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# =============================================================================
# BACKGROUND TASKS
# =============================================================================
async def cleanup_expired_files():
    """Background task to clean up expired files every minute"""
    while True:
        try:
            logger.info("Running security cleanup task...")
            
            # Delete expired printable books
            result = await db.printable_books.delete_many({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"SECURITY: Cleaned up {result.deleted_count} expired printable book(s)")
            
            # Delete expired GenStudio jobs and files
            expired_jobs = await db.genstudio_jobs.find({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            }).to_list(100)
            
            for job in expired_jobs:
                job_id = job.get("id", "")
                for pattern in [f"/tmp/genstudio_{job_id}*", f"/tmp/genstudio_input_{job_id}*"]:
                    for filepath in glob.glob(pattern):
                        try:
                            os.remove(filepath)
                            logger.info(f"SECURITY: Deleted expired file: {filepath}")
                        except Exception as e:
                            pass
            
            result = await db.genstudio_jobs.delete_many({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"SECURITY: Cleaned up {result.deleted_count} expired GenStudio job(s)")
            
            # Delete expired conversion jobs
            result = await db.conversion_jobs.delete_many({
                "expiresAt": {"$lt": datetime.now(timezone.utc).isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"SECURITY: Cleaned up {result.deleted_count} expired conversion job(s)")
            
            # Aggressive cleanup: Delete old temp files
            current_time = datetime.now(timezone.utc)
            for pattern in ["/tmp/genstudio_*", "/tmp/printable_*", "/tmp/story_*", "/tmp/reel_*"]:
                for filepath in glob.glob(pattern):
                    try:
                        file_age = current_time.timestamp() - os.path.getmtime(filepath)
                        if file_age > (FILE_EXPIRY_MINUTES * 60):
                            os.remove(filepath)
                            logger.info(f"SECURITY: Force-deleted old file: {filepath}")
                    except Exception:
                        pass
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        await asyncio.sleep(60)

# =============================================================================
# APP LIFECYCLE
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    logger.info("CreatorStudio API starting...")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(cleanup_expired_files())
    
    # Create indexes
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("id", unique=True)
        await db.genstudio_jobs.create_index("expiresAt")
        await db.conversion_jobs.create_index("expiresAt")
        await db.style_profiles.create_index([("userId", 1), ("id", 1)])
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")
    
    # Seed admin user
    admin_exists = await db.users.find_one({"email": "admin@creatorstudio.ai"})
    if not admin_exists:
        from shared import hash_password
        import uuid
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "name": "Admin",
            "email": "admin@creatorstudio.ai",
            "password": hash_password("Cr3@t0rStud!o#2026"),
            "role": "ADMIN",
            "credits": 10000,
            "plan": "unlimited",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Admin user created")
    
    logger.info("CreatorStudio API ready!")
    
    yield
    
    # Cleanup
    cleanup_task.cancel()
    logger.info("CreatorStudio API shutting down...")

# =============================================================================
# CREATE APPLICATION
# =============================================================================
app = FastAPI(
    title="CreatorStudio API",
    description="AI-powered content creation platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disabled for security
    redoc_url=None,
    openapi_url=None
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# =============================================================================
# MIDDLEWARE
# =============================================================================
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response

# Threat detection middleware
@app.middleware("http")
async def threat_detection_middleware(request: Request, call_next):
    """ML-based threat detection"""
    import time
    start_time = time.time()
    
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    # Analyze request for threats
    threat_analysis = threat_intel.analyze_request(
        ip=client_ip,
        user_agent=user_agent,
        headers=dict(request.headers)
    )
    
    if threat_analysis["action"] == "BLOCK":
        log_security_event("THREAT_BLOCKED", {
            "ip": client_ip,
            "threats": threat_analysis["threats"],
            "score": threat_analysis["threat_score"]
        }, "WARNING")
        return Response(content="Access denied", status_code=403)
    
    # Attack pattern detection
    path = request.url.path.lower()
    query = str(request.url.query).lower() if request.url.query else ""
    
    attack_patterns = [
        '../', '..\\', '/etc/', '/proc/', '.env', '.git',
        'wp-admin', 'phpinfo', 'eval(', 'exec(', '<script',
        'javascript:', 'vbscript:', 'onload=', 'onerror=',
        'union select', 'drop table', '1=1', "' or '"
    ]
    
    for pattern in attack_patterns:
        if pattern in path or pattern in query:
            record_suspicious_activity(client_ip, f"Attack pattern: {pattern}")
            log_security_event("ATTACK_BLOCKED", {"ip": client_ip, "pattern": pattern}, "WARNING")
            return Response(content="Forbidden", status_code=403)
    
    # Process request
    response = await call_next(request)
    
    # Record request for pattern analysis
    response_time = time.time() - start_time
    threat_intel.record_request(
        ip=client_ip,
        user_id=None,  # Would need to extract from auth
        endpoint=request.url.path,
        response_time=response_time,
        status_code=response.status_code
    )
    
    return response

# =============================================================================
# IMPORT AND INCLUDE LEGACY ROUTES FROM server.py
# =============================================================================
# Note: We're importing the existing routers from the original server.py
# This allows gradual migration while keeping the app functional

# Import the original server module to get all routers
try:
    from server_legacy import (
        api_router as legacy_api_router
    )
    app.include_router(legacy_api_router)
    logger.info("Legacy routes loaded from server_legacy.py")
except ImportError:
    logger.warning("Legacy routes not found, using modular routes only")
    
    # If no legacy, include new modular routes
    from fastapi import APIRouter
    api_router = APIRouter(prefix="/api")
    api_router.include_router(style_profile_router)
    api_router.include_router(convert_router)
    app.include_router(api_router)

# =============================================================================
# HEALTH CHECK (Always available)
# =============================================================================
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "security": "enabled",
        "file_expiry_minutes": FILE_EXPIRY_MINUTES,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# =============================================================================
# RUN
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
