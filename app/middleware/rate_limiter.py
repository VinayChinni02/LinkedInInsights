"""
Rate limiting middleware to prevent abuse and ensure scalability.
Uses Redis for distributed rate limiting.
"""
import time
from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.cache_service import cache_service
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    Limits requests per IP address to prevent abuse.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limits before processing request."""
        
        # Skip rate limiting for health checks
        if request.url.path in ["/api/v1/health", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check per-minute limit
        minute_key = f"rate_limit:minute:{client_ip}:{int(time.time() / 60)}"
        minute_count_raw = await cache_service.get(minute_key)
        minute_count = int(minute_count_raw) if minute_count_raw else 0
        
        if minute_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded (per minute) for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute."
            )
        
        # Check per-hour limit
        hour_key = f"rate_limit:hour:{client_ip}:{int(time.time() / 3600)}"
        hour_count_raw = await cache_service.get(hour_key)
        hour_count = int(hour_count_raw) if hour_count_raw else 0
        
        if hour_count >= self.requests_per_hour:
            logger.warning(f"Rate limit exceeded (per hour) for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_hour} requests per hour."
            )
        
        # Increment counters
        try:
            await cache_service.set(minute_key, minute_count + 1, ttl=60)
            await cache_service.set(hour_key, hour_count + 1, ttl=3600)
        except Exception as e:
            logger.warning(f"Failed to update rate limit counters: {e}")
            # Continue processing even if rate limit tracking fails
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(self.requests_per_minute - minute_count - 1)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(self.requests_per_hour - hour_count - 1)
        
        return response

