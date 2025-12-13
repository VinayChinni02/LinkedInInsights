"""
Storage service for uploading images to S3 or similar storage.
"""
from typing import Optional
import httpx
import boto3
from botocore.exceptions import ClientError
from config import settings


class StorageService:
    """Service for storing images and files in cloud storage."""
    
    def __init__(self):
        self.s3_client = None
        self.bucket_name = settings.s3_bucket_name
        
        if (settings.aws_access_key_id and 
            settings.aws_secret_access_key and 
            self.bucket_name):
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
                print("✅ S3 storage service initialized")
            except Exception as e:
                print(f"⚠️  S3 initialization failed: {e}")
    
    async def upload_image(self, image_url: str, key: str) -> Optional[str]:
        """
        Download image from URL and upload to S3.
        
        Args:
            image_url: Source image URL
            key: S3 object key (path)
            
        Returns:
            S3 URL if successful, None otherwise
        """
        if not self.s3_client or not self.bucket_name:
            return None
        
        try:
            # Download image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30)
                response.raise_for_status()
                image_data = response.content
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType=response.headers.get('content-type', 'image/jpeg'),
                ACL='public-read'
            )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"
            return s3_url
            
        except Exception as e:
            print(f"Error uploading image to S3: {e}")
            return None
    
    async def upload_profile_picture(self, page_id: str, image_url: str) -> Optional[str]:
        """Upload profile picture for a page."""
        if not image_url:
            return None
        key = f"profile_pictures/{page_id}.jpg"
        return await self.upload_image(image_url, key)
    
    async def upload_post_image(self, page_id: str, post_id: str, image_url: str) -> Optional[str]:
        """Upload post image."""
        if not image_url:
            return None
        key = f"post_images/{page_id}/{post_id}.jpg"
        return await self.upload_image(image_url, key)


storage_service = StorageService()

