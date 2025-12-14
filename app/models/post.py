"""
Post and Comment models for LinkedIn posts.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId
from .page import PyObjectId


class Comment(BaseModel):
    """Comment model for LinkedIn posts."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    post_id: Optional[PyObjectId] = Field(..., description="Reference to parent post")
    author_name: Optional[str] = Field(None, description="Comment author name")
    author_profile_url: Optional[str] = Field(None, description="Comment author profile URL")
    content: str = Field(..., description="Comment content")
    likes: Optional[int] = Field(0, description="Number of likes")
    created_at: Optional[datetime] = Field(None, description="Comment creation time")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When comment was scraped")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class Post(BaseModel):
    """LinkedIn post model."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    page_id: Optional[PyObjectId] = Field(..., description="Reference to parent page")
    linkedin_post_id: Optional[str] = Field(None, description="LinkedIn platform specific post ID")
    content: str = Field(..., description="Post content/text")
    author_name: Optional[str] = Field(None, description="Post author name")
    author_profile_url: Optional[str] = Field(None, description="Post author profile URL")
    video_url: Optional[str] = Field(None, description="Post video URL")
    likes: Optional[int] = Field(0, description="Number of likes")
    comments_count: Optional[int] = Field(0, description="Number of comments")
    shares: Optional[int] = Field(0, description="Number of shares")
    post_url: Optional[str] = Field(None, description="Full URL to the post")
    created_at: Optional[datetime] = Field(None, description="Post creation time")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When post was scraped")
    comments: List[Comment] = Field(default_factory=list, description="List of comments on the post")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "page_id": "507f1f77bcf86cd799439011",
                "content": "Exciting news about our new product launch!",
                "likes": 150,
                "comments_count": 25,
                "shares": 10
            }
        }
    }




