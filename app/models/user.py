"""
SocialMediaUser model for people working at LinkedIn pages.
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId
from .page import PyObjectId


class SocialMediaUser(BaseModel):
    """Social media user model for people working at companies."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    page_id: Optional[PyObjectId] = Field(..., description="Reference to company page")
    linkedin_user_id: Optional[str] = Field(None, description="LinkedIn platform specific user ID")
    name: str = Field(..., description="User full name")
    profile_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    headline: Optional[str] = Field(None, description="User headline/title")
    location: Optional[str] = Field(None, description="User location")
    current_position: Optional[str] = Field(None, description="Current position at company")
    connection_count: Optional[int] = Field(None, description="Number of connections")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When user data was scraped")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "page_id": "507f1f77bcf86cd799439011",
                "name": "John Doe",
                "profile_url": "https://www.linkedin.com/in/johndoe/",
                "headline": "Software Engineer at DeepSolv",
                "current_position": "Senior Software Engineer"
            }
        }
    }

