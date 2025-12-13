"""
Repository for Comment database operations.
"""
from typing import List
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.models.post import Comment


class CommentRepository:
    """Repository for Comment CRUD operations."""
    
    def __init__(self):
        self.collection_name = "comments"
    
    def _get_collection(self):
        """Get comments collection."""
        db = get_database()
        return db[self.collection_name]
    
    async def create(self, comment_data: dict) -> Comment:
        """Create a new comment."""
        comment_data["scraped_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_one(comment_data)
        comment_data["_id"] = result.inserted_id
        
        return Comment(**comment_data)
    
    async def create_many(self, comments_data: List[dict]) -> List[Comment]:
        """Create multiple comments."""
        if not comments_data:
            return []
        
        for comment_data in comments_data:
            comment_data["scraped_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_many(comments_data)
        
        comments = []
        for i, comment_data in enumerate(comments_data):
            comment_data["_id"] = result.inserted_ids[i]
            comments.append(Comment(**comment_data))
        
        return comments
    
    async def find_by_post_id(self, post_id: ObjectId) -> List[Comment]:
        """Find comments by post_id."""
        cursor = self._get_collection().find({"post_id": post_id})
        
        comments = []
        async for comment_data in cursor:
            comments.append(Comment(**comment_data))
        
        return comments
    
    async def delete_by_post_id(self, post_id: ObjectId) -> int:
        """Delete all comments for a post."""
        result = await self._get_collection().delete_many({"post_id": post_id})
        return result.deleted_count


comment_repository = CommentRepository()

