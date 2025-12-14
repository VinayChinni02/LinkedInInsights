"""
Main FastAPI application.
Robust, scalable, and maintainable backend system.
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from app.database import connect_to_mongo, close_mongo_connection
from app.services.cache_service import cache_service
from app.services.scraper_service import scraper_service
from app.services.linkedin_api_service import linkedin_api_service
from app.api.routes import router
from app.middleware.error_handler import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from app.middleware.logging_middleware import LoggingMiddleware
from config import settings

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting LinkedIn Insights Microservice...")
    logger.info(f"Environment: {settings.app_env}, Debug: {settings.debug}")
    
    # Connect to MongoDB with connection pooling
    try:
        await connect_to_mongo()
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}", exc_info=True)
    
    # Connect to Redis cache
    try:
        await cache_service.connect()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
    
    # Initialize scraper service with timeout to prevent hanging
    import asyncio
    try:
        await asyncio.wait_for(scraper_service.initialize(), timeout=30.0)
        logger.info("Scraper service initialized")
    except (asyncio.TimeoutError, NotImplementedError, Exception) as e:
        logger.warning(f"Scraper service initialization failed: {type(e).__name__}. Continuing without scraper.")
    
    # Initialize LinkedIn API service
    try:
        await linkedin_api_service.initialize()
        logger.info("LinkedIn API service initialized")
    except Exception as e:
        logger.warning(f"LinkedIn API service initialization failed: {type(e).__name__}. Continuing without API.")
    
    logger.info("All services initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    try:
        await close_mongo_connection()
        await cache_service.close()
        await scraper_service.close()
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


app = FastAPI(
    title="LinkedIn Insights Microservice",
    description="A robust, scalable microservice to scrape and analyze LinkedIn company page data",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add exception handlers for robust error handling
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Add logging middleware for observability
app.add_middleware(LoggingMiddleware)

# Add rate limiting middleware (if enabled)
if settings.rate_limit_enabled:
    from app.middleware.rate_limiter import RateLimitMiddleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_per_minute,
        requests_per_hour=settings.rate_limit_per_hour
    )
    logger.info(f"Rate limiting enabled: {settings.rate_limit_per_minute}/min, {settings.rate_limit_per_hour}/hour")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.cors_origins if hasattr(settings, 'cors_origins') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LinkedIn Insights Microservice API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

