"""
Main FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import connect_to_mongo, close_mongo_connection
from app.services.cache_service import cache_service
from app.services.scraper_service import scraper_service
from app.services.linkedin_api_service import linkedin_api_service
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    print("[START] Starting LinkedIn Insights Microservice...")
    await connect_to_mongo()
    await cache_service.connect()
    
    # Initialize scraper service with timeout to prevent hanging
    import asyncio
    try:
        await asyncio.wait_for(scraper_service.initialize(), timeout=30.0)
    except (asyncio.TimeoutError, NotImplementedError, Exception) as e:
        print(f"[WARNING] Scraper service initialization failed: {type(e).__name__}. Continuing without scraper.")
    
    # Initialize LinkedIn API service
    try:
        await linkedin_api_service.initialize()
    except Exception as e:
        print(f"[WARNING] LinkedIn API service initialization failed: {type(e).__name__}. Continuing without API.")
    
    print("[OK] All services initialized")
    
    yield
    
    # Shutdown
    print("[SHUTDOWN] Shutting down...")
    await close_mongo_connection()
    await cache_service.close()
    await scraper_service.close()
    print("[OK] Shutdown complete")


app = FastAPI(
    title="LinkedIn Insights Microservice",
    description="A microservice to scrape and analyze LinkedIn company page data",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

