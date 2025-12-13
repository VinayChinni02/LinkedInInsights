"""
Repository for SocialMediaUser database operations.
"""
from typing import List
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.models.user import SocialMediaUser


class UserRepository:
    """Repository for SocialMediaUser CRUD operations."""
    
    def __init__(self):
        self.collection_name = "users"
    
    def _get_collection(self):
        """Get users collection."""
        db = get_database()
        return db[self.collection_name]
    
    async def create(self, user_data: dict) -> SocialMediaUser:
        """Create a new user."""
        user_data["scraped_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_one(user_data)
        user_data["_id"] = result.inserted_id
        
        return SocialMediaUser(**user_data)
    
    async def create_many(self, users_data: List[dict]) -> List[SocialMediaUser]:
        """Create multiple users."""
        if not users_data:
            return []
        
        for user_data in users_data:
            user_data["scraped_at"] = datetime.utcnow()
        
        result = await self._get_collection().insert_many(users_data)
        
        users = []
        for i, user_data in enumerate(users_data):
            user_data["_id"] = result.inserted_ids[i]
            users.append(SocialMediaUser(**user_data))
        
        return users
    
    async def find_by_page_id(
        self,
        page_id: ObjectId,
        limit: int = 100,
        skip: int = 0
    ) -> List[SocialMediaUser]:
        """Find users by page_id."""
        cursor = self._get_collection().find(
            {"page_id": page_id}
        ).skip(skip).limit(limit)
        
        users = []
        async for user_data in cursor:
            users.append(SocialMediaUser(**user_data))
        
        return users
    
    async def delete_by_page_id(self, page_id: ObjectId) -> int:
        """Delete all users for a page."""
        result = await self._get_collection().delete_many({"page_id": page_id})
        return result.deleted_count


user_repository = UserRepository()

