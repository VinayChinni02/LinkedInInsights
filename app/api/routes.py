"""
API routes for LinkedIn Insights service.
"""
from typing import Optional, List, Any
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel
from bson import ObjectId
from app.services.page_service import page_service, convert_objectid_to_str
from app.repositories.page_repository import page_repository
from app.repositories.post_repository import post_repository
from app.repositories.user_repository import user_repository


router = APIRouter(prefix="/api/v1", tags=["LinkedIn Insights"])


class PageResponse(BaseModel):
    """Response model for page data."""
    success: bool
    data: dict
    message: Optional[str] = None


class PagesListResponse(BaseModel):
    """Response model for pages list."""
    success: bool
    data: List[dict]
    total: int
    page: int
    page_size: int
    message: Optional[str] = None


class PostsResponse(BaseModel):
    """Response model for posts."""
    success: bool
    data: List[dict]
    total: int
    message: Optional[str] = None


class PeopleResponse(BaseModel):
    """Response model for people."""
    success: bool
    data: List[dict]
    total: int
    message: Optional[str] = None


@router.get("/pages/{page_id}", response_model=PageResponse)
async def get_page_details(
    page_id: str,
    force_refresh: bool = Query(False, description="Force refresh by scraping again")
):
    """
    Get details of a LinkedIn page by Page ID.
    
    - If page exists in DB, returns cached data
    - If page doesn't exist, scrapes LinkedIn and stores in DB
    - **page_id**: LinkedIn page ID (e.g., 'deepsolv' from linkedin.com/company/deepsolv/)
    """
    try:
        page_data = await page_service.get_or_scrape_page(page_id, force_refresh=force_refresh)
        
        if not page_data:
            # Check if scraping service is available
            from app.services.scraper_service import scraper_service
            if not scraper_service.browser:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Scraping service is not available. Page '{page_id}' not found in database and cannot be scraped. Please check Docker logs for Playwright initialization errors."
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page '{page_id}' not found and could not be scraped"
            )
        
        # Ensure all ObjectIds are converted to strings
        page_data = convert_objectid_to_str(page_data)
        
        # Check if data is limited
        from app.services.scraper_service import scraper_service
        from config import settings
        message = "Page retrieved successfully"
        
        # Check if critical fields are missing
        missing_fields = []
        if not page_data.get("industry"):
            missing_fields.append("industry")
        if len(page_data.get("posts", [])) == 0:
            missing_fields.append("posts")
        if len(page_data.get("people", [])) == 0:
            missing_fields.append("people")
        
        if missing_fields:
            # Check if credentials are configured
            has_credentials = settings.linkedin_email and settings.linkedin_password
            if has_credentials and not scraper_service.is_authenticated:
                message = f"Page retrieved successfully. Note: Some data may be limited (missing: {', '.join(missing_fields)}). LinkedIn is blocking automated access despite credentials being configured. This is due to LinkedIn's bot detection."
            elif not has_credentials:
                message = f"Page retrieved successfully. Note: Some data may be limited (missing: {', '.join(missing_fields)}). For full data access, configure LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env file."
            else:
                message = f"Page retrieved successfully. Note: Some data may be limited (missing: {', '.join(missing_fields)})."
        
        return PageResponse(
            success=True,
            data=page_data,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving page: {str(e)}"
        )


@router.get("/pages", response_model=PagesListResponse)
async def search_pages(
    follower_min: Optional[int] = Query(None, description="Minimum follower count"),
    follower_max: Optional[int] = Query(None, description="Maximum follower count"),
    name_search: Optional[str] = Query(None, description="Search by page name (partial match)"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page")
):
    """
    Search and filter pages with pagination.
    
    - Filter by follower count range
    - Search by page name (case-insensitive partial match)
    - Filter by industry
    - Results are paginated
    """
    try:
        skip = (page - 1) * page_size
        
        pages = await page_repository.find_with_filters(
            follower_min=follower_min,
            follower_max=follower_max,
            name_search=name_search,
            industry=industry,
            skip=skip,
            limit=page_size
        )
        
        total = await page_repository.count_with_filters(
            follower_min=follower_min,
            follower_max=follower_max,
            name_search=name_search,
            industry=industry
        )
        
        pages_data = [page.model_dump(by_alias=True, mode='json') for page in pages]
        
        return PagesListResponse(
            success=True,
            data=pages_data,
            total=total,
            page=page,
            page_size=page_size,
            message=f"Found {total} page(s)"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching pages: {str(e)}"
        )


@router.get("/pages/{page_id}/followers", response_model=PeopleResponse)
async def get_page_followers(
    page_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """
    Get list of followers/people working at a given page.
    
    - Returns people associated with the page
    - Results are paginated
    """
    try:
        # Find page first
        page_obj = await page_repository.find_by_page_id(page_id)
        if not page_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page '{page_id}' not found"
            )
        
        skip = (page - 1) * page_size
        people = await user_repository.find_by_page_id(
            page_obj.id,
            limit=page_size,
            skip=skip
        )
        
        people_data = [person.model_dump(by_alias=True, mode='json') for person in people]
        
        return PeopleResponse(
            success=True,
            data=people_data,
            total=len(people_data),
            message=f"Retrieved {len(people_data)} people"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving followers: {str(e)}"
        )


@router.get("/pages/{page_id}/posts", response_model=PostsResponse)
async def get_page_posts(
    page_id: str,
    limit: int = Query(15, ge=1, le=25, description="Number of posts to retrieve")
):
    """
    Get recent posts of a page.
    
    - Returns recent 10-15 posts (configurable up to 25)
    - Includes comments on each post
    """
    try:
        # Find page first
        page_obj = await page_repository.find_by_page_id(page_id)
        if not page_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page '{page_id}' not found"
            )
        
        posts = await post_repository.find_recent_by_page_id(
            page_obj.id,
            limit=limit
        )
        
        posts_data = [post.model_dump(by_alias=True, mode='json') for post in posts]
        
        return PostsResponse(
            success=True,
            data=posts_data,
            total=len(posts_data),
            message=f"Retrieved {len(posts_data)} post(s)"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving posts: {str(e)}"
        )


@router.post("/pages/{page_id}/refresh")
async def refresh_page_data(page_id: str):
    """
    Force refresh page data by re-scraping.
    
    - Scrapes fresh data from LinkedIn
    - Updates database
    - Clears cache
    """
    try:
        page_data = await page_service.scrape_and_store_page(page_id)
        
        if not page_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not scrape page '{page_id}'"
            )
        
        return PageResponse(
            success=True,
            data=page_data,
            message="Page data refreshed successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing page: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    Checks all critical services (MongoDB, Redis, Scraper).
    Essential for monitoring and load balancer health checks.
    """
    from app.database import get_database
    from app.services.cache_service import cache_service
    from app.services.scraper_service import scraper_service
    
    health_status = {
        "status": "healthy",
        "service": "LinkedIn Insights Microservice",
        "version": "1.0.0",
        "checks": {}
    }
    
    overall_healthy = True
    
    # Check MongoDB
    try:
        db = get_database()
        if db:
            await db.client.admin.command('ping')
            health_status["checks"]["mongodb"] = {
                "status": "healthy",
                "message": "Connected"
            }
        else:
            health_status["checks"]["mongodb"] = {
                "status": "unhealthy",
                "message": "Database not initialized"
            }
            overall_healthy = False
    except Exception as e:
        health_status["checks"]["mongodb"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        overall_healthy = False
    
    # Check Redis
    try:
        if cache_service.redis_client:
            await cache_service.redis_client.ping()
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "message": "Connected"
            }
        else:
            health_status["checks"]["redis"] = {
                "status": "degraded",
                "message": "Cache not available (optional)"
            }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "degraded",
            "message": f"Cache unavailable: {str(e)}"
        }
    
    # Check Scraper Service
    try:
        if scraper_service.browser:
            health_status["checks"]["scraper"] = {
                "status": "healthy",
                "message": "Browser initialized",
                "authenticated": scraper_service.is_authenticated
            }
        else:
            health_status["checks"]["scraper"] = {
                "status": "degraded",
                "message": "Scraper not available"
            }
    except Exception as e:
        health_status["checks"]["scraper"] = {
            "status": "degraded",
            "message": f"Scraper error: {str(e)}"
        }
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    
    status_code = 200 if overall_healthy else 503
    
    return health_status


@router.get("/debug/{page_id}/html")
async def debug_page_html(page_id: str):
    """
    Debug endpoint to see raw HTML and extraction status.
    Helps diagnose why fields are null.
    """
    from app.services.scraper_service import scraper_service
    
    if not scraper_service.browser:
        await scraper_service.initialize()
    
    if not scraper_service.browser:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scraper service not available"
        )
    
    url = f"https://www.linkedin.com/company/{page_id}/"
    
    try:
        if scraper_service.context:
            page = await scraper_service.context.new_page()
        else:
            page = await scraper_service.browser.new_page()
        
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        
        content = await page.content()
        current_url = page.url
        page_title = await page.title()
        
        # Check authentication status
        is_authwall = any(x in current_url.lower() for x in ['login', 'authwall', 'challenge', 'join'])
        
        # Sample of HTML (first 2000 chars)
        html_sample = content[:2000] if len(content) > 2000 else content
        
        await page.close()
        
        return {
            "page_id": page_id,
            "url": url,
            "current_url": current_url,
            "page_title": page_title,
            "is_authenticated": scraper_service.is_authenticated,
            "is_authwall": is_authwall,
            "html_length": len(content),
            "html_sample": html_sample,
            "message": "Use this to debug extraction issues. Check if authwall is detected."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching page: {str(e)}"
        )

