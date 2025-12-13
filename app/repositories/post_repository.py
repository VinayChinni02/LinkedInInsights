"""
Repository for Post database operations.
"""
from typing import Optional, List
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.models.post import Post


class PostRepository:
    """Repository for Post CRUD operations."""
    
    def __init__(self):
        self.collection_name = "posts"
    
    def _get_collection(self):
        """Get posts collection."""
        db = get_database()
        return db[self.collection_name]
    
    async def create(self, post_data: dict) -> Post:
        """Create a new post."""
        post_data["scraped_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_one(post_data)
        post_data["_id"] = result.inserted_id
        
        return Post(**post_data)
    
    async def create_many(self, posts_data: List[dict]) -> List[Post]:
        """Create multiple posts."""
        if not posts_data:
            return []
        
        for post_data in posts_data:
            post_data["scraped_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_many(posts_data)
        
        posts = []
        for i, post_data in enumerate(posts_data):
            post_data["_id"] = result.inserted_ids[i]
            posts.append(Post(**post_data))
        
        return posts
    
    async def find_by_page_id(
        self,
        page_id: ObjectId,
        limit: int = 15,
        skip: int = 0
    ) -> List[Post]:
        """Find posts by page_id."""
        cursor = self._get_collection().find(
            {"page_id": page_id}
        ).sort("created_at", -1).skip(skip).limit(limit)
        
        posts = []
        async for post_data in cursor:
            posts.append(Post(**post_data))
        
        return posts
    
    async def find_recent_by_page_id(
        self,
        page_id: ObjectId,
        limit: int = 15
    ) -> List[Post]:
        """Find recent posts by page_id."""
        return await self.find_by_page_id(page_id, limit=limit, skip=0)
    
    async def delete_by_page_id(self, page_id: ObjectId) -> int:
        """Delete all posts for a page."""
        result = await self._get_collection().delete_many({"page_id": page_id})
        return result.deleted_count


post_repository = PostRepository()

