"""
Structured logging middleware for request/response tracking.
Essential for debugging and monitoring in production.
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.
    Provides structured logging for observability.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response with timing information."""
        start_time = time.time()
        
        # Extract request information
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        
        # Log request
        logger.info(
            f"Request: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response: {method} {path} - {response.status_code}",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "process_time": round(process_time, 3),
                    "client_ip": client_ip
                }
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(round(process_time, 3))
            
            return response
            
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            logger.error(
                f"Exception in {method} {path}",
                exc_info=True,
                extra={
                    "method": method,
                    "path": path,
                    "process_time": round(process_time, 3),
                    "client_ip": client_ip,
                    "error": str(e)
                }
            )
            raise
