"""Test MongoDB connection from local machine."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_connection():
    try:
        print("Testing MongoDB connection...")
        client = AsyncIOMotorClient('mongodb://localhost:27017', serverSelectionTimeoutMS=5000)
        
        # Test connection
        await client.admin.command('ping')
        print("[OK] Connected to MongoDB")
        
        # List all databases
        db_list = await client.list_database_names()
        print(f"\nAvailable databases: {db_list}")
        
        # Get database
        db = client['linkedin_insights']
        
        # List collections
        collections = await db.list_collection_names()
        print(f"Collections in 'linkedin_insights': {collections}")
        
        # Count pages
        count = await db.pages.count_documents({})
        print(f"\n[OK] Found {count} pages in database")
        
        # List pages
        if count > 0:
            pages = await db.pages.find({}, {"page_id": 1, "name": 1}).to_list(length=10)
            print("\nPages in database:")
            for page in pages:
                print(f"  - {page.get('page_id')}: {page.get('name')}")
        
        client.close()
        print("\n[OK] Connection test successful!")
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure MongoDB is running: docker-compose ps")
        print("2. Check if port 27017 is exposed: netstat -an | findstr 27017")
        print("3. Try connecting from Docker: docker exec deepsolv-mongodb-1 mongosh")

if __name__ == "__main__":
    asyncio.run(test_connection())

