"""
CreatorStudio AI - Self-Healing Middleware
==========================================
Request tracking, correlation IDs, and automatic metrics collection.
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.self_healing_core import (
    CorrelationContext, metrics, generate_correlation_id
)

logger = logging.getLogger("creatorstudio.middleware")


class SelfHealingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds correlation tracking and metrics collection
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        # Extract user ID if available
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                import jwt
                from shared import JWT_SECRET, JWT_ALGORITHM
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("user_id")
            except Exception:
                pass
        
        # Set correlation context
        request_type = self._get_request_type(request.url.path)
        CorrelationContext.set(
            correlation_id=correlation_id,
            user_id=user_id,
            request_type=request_type,
            metadata={
                "path": request.url.path,
                "method": request.method,
                "client_ip": self._get_client_ip(request)
            }
        )
        
        # Track request start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            await metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id
            )
            
            # Add correlation ID to response
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-Duration-Ms"] = str(int(duration_ms))
            
            # Log slow requests
            if duration_ms > 5000:
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {duration_ms:.0f}ms (correlation_id={correlation_id})"
                )
            
            return response
            
        except Exception as e:
            # Record error
            duration_ms = (time.time() - start_time) * 1000
            await metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                duration_ms=duration_ms,
                user_id=user_id
            )
            
            logger.error(
                f"Request error: {request.method} {request.url.path} "
                f"- {str(e)} (correlation_id={correlation_id})"
            )
            raise
            
        finally:
            CorrelationContext.clear()
    
    @staticmethod
    def _get_request_type(path: str) -> str:
        """Determine request type from path"""
        if "/auth" in path:
            return "auth"
        elif "/generate" in path or "/comix" in path or "/gif" in path:
            return "generation"
        elif "/payment" in path or "/cashfree" in path:
            return "payment"
        elif "/admin" in path:
            return "admin"
        elif "/download" in path or "/static" in path:
            return "download"
        else:
            return "api"
    
    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Get client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed request logging (for debugging)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks and static files
        if request.url.path in ["/api/health", "/api/health/"] or "/static/" in request.url.path:
            return await call_next(request)
        
        correlation_id = CorrelationContext.get_id()
        
        # Log request
        logger.debug(
            f"[{correlation_id}] --> {request.method} {request.url.path}"
        )
        
        response = await call_next(request)
        
        # Log response
        logger.debug(
            f"[{correlation_id}] <-- {response.status_code} "
            f"({CorrelationContext.get_duration()*1000:.0f}ms)"
        )
        
        return response


async def log_request_to_db(request: Request, response: Response, duration_ms: float):
    """
    Log request details to database for analytics
    """
    from shared import db
    
    try:
        # Only log API requests
        if not request.url.path.startswith("/api"):
            return
        
        # Skip health checks
        if "health" in request.url.path:
            return
        
        log_entry = {
            "correlation_id": CorrelationContext.get_id(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": duration_ms,
            "user_id": CorrelationContext.get().get("user_id"),
            "client_ip": request.client.host if request.client else None,
            "created_at": time.time()
        }
        
        # Use insert_one with write concern 0 for performance
        await db.request_logs.insert_one(log_entry)
        
    except Exception as e:
        logger.debug(f"Failed to log request: {e}")
