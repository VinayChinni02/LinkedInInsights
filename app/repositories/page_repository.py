"""
Repository for Page database operations.
"""
from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.models.page import Page


class PageRepository:
    """Repository for Page CRUD operations."""
    
    def __init__(self):
        self.collection_name = "pages"
    
    def _get_collection(self):
        """Get pages collection."""
        db = get_database()
        return db[self.collection_name]
    
    async def create(self, page_data: Dict[str, Any]) -> Page:
        """Create a new page."""
        page_data["scraped_at"] = datetime.utcnow()
        page_data["updated_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_one(page_data)
        page_data["_id"] = result.inserted_id
        
        return Page(**page_data)
    
    async def find_by_page_id(self, page_id: str) -> Optional[Page]:
        """Find page by LinkedIn page_id."""
        page_data = await self._get_collection().find_one({"page_id": page_id})
        if page_data:
            return Page(**page_data)
        return None
    
    async def find_by_id(self, page_id: ObjectId) -> Optional[Page]:
        """Find page by MongoDB _id."""
        page_data = await self._get_collection().find_one({"_id": page_id})
        if page_data:
            return Page(**page_data)
        return None
    
    async def update(self, page_id: str, update_data: Dict[str, Any]) -> Optional[Page]:
        """Update page data."""
        update_data["updated_at"] = datetime.utcnow()
        
        result = await self._get_collection().update_one(
            {"page_id": page_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.find_by_page_id(page_id)
        return None
    
    async def find_with_filters(
        self,
        follower_min: Optional[int] = None,
        follower_max: Optional[int] = None,
        name_search: Optional[str] = None,
        industry: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[Page]:
        """Find pages with filters."""
        query = {}
        
        if follower_min is not None or follower_max is not None:
            query["total_followers"] = {}
            if follower_min is not None:
                query["total_followers"]["$gte"] = follower_min
            if follower_max is not None:
                query["total_followers"]["$lte"] = follower_max
        
        if name_search:
            query["name"] = {"$regex": name_search, "$options": "i"}
        
        if industry:
            query["industry"] = {"$regex": industry, "$options": "i"}
        
        cursor = self._get_collection().find(query).skip(skip).limit(limit)
        pages = []
        async for page_data in cursor:
            pages.append(Page(**page_data))
        
        return pages
    
    async def count_with_filters(
        self,
        follower_min: Optional[int] = None,
        follower_max: Optional[int] = None,
        name_search: Optional[str] = None,
        industry: Optional[str] = None
    ) -> int:
        """Count pages with filters."""
        query = {}
        
        if follower_min is not None or follower_max is not None:
            query["total_followers"] = {}
            if follower_min is not None:
                query["total_followers"]["$gte"] = follower_min
            if follower_max is not None:
                query["total_followers"]["$lte"] = follower_max
        
        if name_search:
            query["name"] = {"$regex": name_search, "$options": "i"}
        
        if industry:
            query["industry"] = {"$regex": industry, "$options": "i"}
        
        return await self._get_collection().count_documents(query)


page_repository = PageRepository()

