"""
CreatorStudio AI - Main FastAPI Application
Refactored to use modular routes and services
"""
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

# Import routes
from routes.auth import router as auth_router
from routes.credits import router as credits_router
from routes.generation import router as generate_router
from routes.payments import router as payments_router
from routes.feedback import router as feedback_router
from routes.admin import router as admin_router
from routes.health import router as health_router

# Create FastAPI app
app = FastAPI(
    title="CreatorStudio AI API",
    description="AI-powered content generation platform for viral reels and kids story videos",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create main API router
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(auth_router)
api_router.include_router(credits_router)
api_router.include_router(generate_router)
api_router.include_router(payments_router)
api_router.include_router(feedback_router)
api_router.include_router(admin_router)
api_router.include_router(health_router)

# Include API router in app
app.include_router(api_router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "CreatorStudio AI API",
        "version": "2.0.0",
        "status": "running"
    }


# Health check at root level
@app.get("/health")
async def root_health():
    return {"status": "healthy"}


# Startup event
@app.on_event("startup")
async def startup():
    logger.info("CreatorStudio API starting...")
    logger.info("CreatorStudio API ready!")


# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    logger.info("CreatorStudio API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
