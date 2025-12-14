"""
Service for managing LinkedIn pages - orchestrates scraping, storage, and database operations.
"""
from typing import Optional, Dict, Any, List
from bson import ObjectId
from app.repositories.page_repository import page_repository
from app.repositories.post_repository import post_repository
from app.repositories.user_repository import user_repository
from app.repositories.comment_repository import comment_repository
from app.services.scraper_service import scraper_service
from app.services.storage_service import storage_service
from app.services.cache_service import cache_service
from app.services.ai_service import ai_service
from app.services.linkedin_api_service import linkedin_api_service
from app.models.page import Page
from app.models.post import Post
from app.models.user import SocialMediaUser


def convert_objectid_to_str(obj: Any) -> Any:
    """Recursively convert ObjectId to string in dictionaries and lists."""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    return obj


class PageService:
    """Service for page-related business logic."""
    
    async def get_or_scrape_page(self, page_id: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get page from database or scrape if not found.
        
        Args:
            page_id: LinkedIn page ID
            force_refresh: If True, scrape even if page exists in DB
            
        Returns:
            Page data dictionary
        """
        # Check cache first
        cache_key = f"page:{page_id}"
        if not force_refresh:
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                return cached_data
        
        # Check database
        if not force_refresh:
            page = await page_repository.find_by_page_id(page_id)
            if page:
                page_dict = page.model_dump(by_alias=True, mode='json')
                # Add related data
                page_dict["posts"] = await self._get_posts_for_page(page.id)
                page_dict["people"] = await self._get_people_for_page(page.id)
                # Convert any remaining ObjectIds to strings
                page_dict = convert_objectid_to_str(page_dict)
                # Cache the result
                await cache_service.set(cache_key, page_dict)
                return page_dict
        
        # Scrape if not in database or force refresh
        return await self.scrape_and_store_page(page_id)
    
    async def scrape_and_store_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Scrape page data and store in database.
        
        Args:
            page_id: LinkedIn page ID
            
        Returns:
            Page data dictionary
        """
        # Initialize scraper if needed
        if not scraper_service.browser:
            await scraper_service.initialize()
        
        # Check if browser is available before scraping
        if not scraper_service.browser:
            print(f"[ERROR] Scraping service not available. Cannot scrape page {page_id}.")
            return None
        
        # Scrape page details
        try:
            page_data = await scraper_service.scrape_page_details(page_id)
            if not page_data:
                print(f"[ERROR] Failed to scrape page details for {page_id}. scrape_page_details returned None.")
                return None
        except Exception as scrape_error:
            print(f"[ERROR] Exception during scraping for {page_id}: {type(scrape_error).__name__}: {str(scrape_error)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return None
        
        # Try to enrich with LinkedIn API data if available
        page_data = await linkedin_api_service.enrich_page_data(page_id, page_data)
        
        # Upload profile picture to storage if available
        if page_data.get("profile_picture"):
            s3_url = await storage_service.upload_profile_picture(
                page_id,
                page_data["profile_picture"]
            )
            if s3_url:
                page_data["profile_picture"] = s3_url
        
        # Check if page already exists
        existing_page = await page_repository.find_by_page_id(page_id)
        
        if existing_page:
            # Update existing page
            page = await page_repository.update(page_id, page_data)
        else:
            # Create new page
            page = await page_repository.create(page_data)
        
        if not page:
            return None
        
        # Scrape and store posts
        await self._scrape_and_store_posts(page.id, page_id)
        
        # Scrape and store people
        await self._scrape_and_store_people(page.id, page_id)
        
        # Generate AI summary
        ai_summary = await ai_service.generate_page_summary(page_data)
        
        # Build response
        result = page.model_dump(by_alias=True, mode='json')
        result["posts"] = await self._get_posts_for_page(page.id)
        result["people"] = await self._get_people_for_page(page.id)
        if ai_summary:
            result["ai_summary"] = ai_summary
        
        # Convert any remaining ObjectIds to strings
        result = convert_objectid_to_str(result)
        
        # Cache the result
        cache_key = f"page:{page_id}"
        await cache_service.set(cache_key, result)
        
        return result
    
    async def _scrape_and_store_posts(self, page_db_id: ObjectId, page_id: str):
        """Scrape and store posts for a page."""
        try:
            print(f"[INFO] Scraping posts for {page_id}...")
            # Delete existing posts
            await post_repository.delete_by_page_id(page_db_id)
            
            # Scrape posts
            posts_data = await scraper_service.scrape_posts(page_id)
            print(f"[INFO] Scraped {len(posts_data)} posts for {page_id}")
            
            if not posts_data:
                print(f"[WARNING] No posts found for {page_id}. This may be due to authentication or page structure.")
            
            # Store posts
            for post_data in posts_data:
                post_data["page_id"] = page_db_id
                
                # Upload post image if available
                if post_data.get("image_url"):
                    s3_url = await storage_service.upload_post_image(
                        page_id,
                        post_data.get("linkedin_post_id", "unknown"),
                        post_data["image_url"]
                    )
                    if s3_url:
                        post_data["image_url"] = s3_url
                
                # Store comments
                comments_data = post_data.pop("comments", [])
                post = await post_repository.create(post_data)
                
                # Store comments
                if comments_data and post.id:
                    # Delete existing comments for this post
                    await comment_repository.delete_by_post_id(post.id)
                    
                    # Create new comments
                    for comment_data in comments_data:
                        comment_data["post_id"] = post.id
                        await comment_repository.create(comment_data)
        except Exception as e:
            print(f"Error scraping/storing posts: {e}")
    
    async def _scrape_and_store_people(self, page_db_id: ObjectId, page_id: str):
        """Scrape and store people for a page."""
        try:
            print(f"[INFO] Scraping people for {page_id}...")
            # Delete existing users
            await user_repository.delete_by_page_id(page_db_id)
            
            # Scrape people
            people_data = await scraper_service.scrape_people(page_id)
            print(f"[INFO] Scraped {len(people_data)} people for {page_id}")
            
            if not people_data:
                print(f"[WARNING] No people found for {page_id}. This may be due to authentication or page structure.")
            
            # Store people
            for person_data in people_data:
                # Ensure page_id is always set
                person_data["page_id"] = page_db_id
                
                # Ensure all required fields are present (even if None)
                # This ensures data structure consistency
                # Note: profile_picture and linkedin_user_id removed per user request
                required_fields = {
                    "name": person_data.get("name", "Unknown"),
                    "profile_url": person_data.get("profile_url"),
                    "headline": person_data.get("headline"),
                    "location": person_data.get("location"),
                    "current_position": person_data.get("current_position"),
                    "connection_count": person_data.get("connection_count"),
                }
                
                # Merge with existing data
                person_data.update(required_fields)
                
                # Upload profile picture if available
                if person_data.get("profile_picture"):
                    # Could upload to S3 here if needed
                    pass
                
                await user_repository.create(person_data)
                print(f"[INFO] Saved person: {person_data.get('name', 'Unknown')} with page_id={page_db_id}")
        except Exception as e:
            print(f"Error scraping/storing people: {e}")
    
    async def _get_posts_for_page(self, page_db_id: ObjectId, limit: int = 15) -> List[Dict[str, Any]]:
        """Get posts for a page with comments."""
        posts = await post_repository.find_recent_by_page_id(page_db_id, limit=limit)
        posts_data = []
        for post in posts:
            post_dict = post.model_dump(by_alias=True, mode='json')
            # Get comments for this post
            comments = await comment_repository.find_by_post_id(post.id)
            post_dict["comments"] = [comment.model_dump(by_alias=True, mode='json') for comment in comments]
            # Convert any remaining ObjectIds to strings
            post_dict = convert_objectid_to_str(post_dict)
            posts_data.append(post_dict)
        return posts_data
    
    async def _get_people_for_page(self, page_db_id: ObjectId, limit: int = 100) -> List[Dict[str, Any]]:
        """Get people for a page."""
        people = await user_repository.find_by_page_id(page_db_id, limit=limit)
        people_data = [person.model_dump(by_alias=True, mode='json') for person in people]
        # Convert any remaining ObjectIds to strings
        return [convert_objectid_to_str(person) for person in people_data]


page_service = PageService()

