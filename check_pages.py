"""
Script to check pages in database.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

async def check_pages():
    """List all pages with their page_id."""
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]
    
    pages = await db.pages.find({}).to_list(length=100)
    
    print("Pages in database:")
    for page in pages:
        print(f"  - Name: {page.get('name', 'N/A')}")
        print(f"    Page ID: {page.get('page_id', 'N/A')}")
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_pages())

