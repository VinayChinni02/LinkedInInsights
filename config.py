"""
Configuration settings for the LinkedIn Insights Microservice.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "linkedin_insights"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_ttl: int = 300  # 5 minutes in seconds
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    
    # AWS S3 Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    
    # Application Configuration
    app_env: str = "development"
    debug: bool = True
    
    # Scraper Configuration
    max_posts_to_scrape: int = 20
    max_comments_per_post: int = 50
    scraper_timeout: int = 30
    
    # LinkedIn Authentication (Optional - for full data access)
    linkedin_email: Optional[str] = None
    linkedin_password: Optional[str] = None
    
    # LinkedIn API (Optional - alternative to scraping)
    linkedin_api_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

