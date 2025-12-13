"""
Page model for LinkedIn company pages.
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId for Pydantic v2."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> ObjectId:
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str):
                if ObjectId.is_valid(value):
                    return ObjectId(value)
                raise ValueError("Invalid ObjectId string")
            raise ValueError("Invalid ObjectId")
        
        from_str_schema = core_schema.str_schema()
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.no_info_plain_validator_function(validate),
            from_str_schema,
        ])
    
    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string"}
    
    def __str__(self) -> str:
        return str(super())


class Page(BaseModel):
    """LinkedIn company page model."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    page_id: str = Field(..., description="LinkedIn page ID (e.g., 'deepsolv')")
    name: str = Field(..., description="Page name")
    url: str = Field(..., description="Full LinkedIn page URL")
    linkedin_id: Optional[str] = Field(None, description="LinkedIn platform specific ID")
    profile_picture: Optional[str] = Field(None, description="URL to profile picture")
    description: Optional[str] = Field(None, description="Page description")
    website: Optional[str] = Field(None, description="Company website")
    industry: Optional[str] = Field(None, description="Page industry")
    total_followers: Optional[int] = Field(None, description="Total number of followers")
    head_count: Optional[str] = Field(None, description="Company head count")
    specialities: Optional[List[str]] = Field(default_factory=list, description="List of specialities")
    location: Optional[str] = Field(None, description="Company location")
    founded: Optional[str] = Field(None, description="Year founded")
    company_type: Optional[str] = Field(None, description="Type of company")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When data was scraped")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "page_id": "deepsolv",
                "name": "DeepSolv",
                "url": "https://www.linkedin.com/company/deepsolv/",
                "linkedin_id": "123456789",
                "profile_picture": "https://example.com/image.jpg",
                "description": "Company description",
                "website": "https://deepsolv.com",
                "industry": "Technology",
                "total_followers": 5000,
                "head_count": "11-50",
                "specialities": ["AI", "Machine Learning"],
                "location": "San Francisco, CA",
                "founded": "2020"
            }
        }
    }

