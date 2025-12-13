"""
Quick script to show database statistics.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient


MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "linkedin_insights"


async def show_stats():
    """Show database statistics."""
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DB_NAME]
        
        print("Database Statistics")
        print("=" * 50)
        
        # Counts
        pages = await db.pages.count_documents({})
        posts = await db.posts.count_documents({})
        users = await db.users.count_documents({})
        comments = await db.comments.count_documents({})
        
        print(f"Pages:      {pages}")
        print(f"Posts:      {posts}")
        print(f"People:     {users}")
        print(f"Comments:   {comments}")
        print()
        
        # Sample data
        if pages > 0:
            sample_page = await db.pages.find_one({})
            print("Sample Page:")
            print(f"  Name: {sample_page.get('name', 'N/A')}")
            print(f"  Page ID: {sample_page.get('page_id', 'N/A')}")
            print(f"  Followers: {sample_page.get('total_followers', 'N/A')}")
            print()
        
        if posts > 0:
            sample_post = await db.posts.find_one({})
            print("Sample Post:")
            print(f"  Content: {sample_post.get('content', 'N/A')[:80]}...")
            print(f"  Likes: {sample_post.get('likes', 0)}")
            print()
        
        if users > 0:
            sample_user = await db.users.find_one({})
            print("Sample Person:")
            print(f"  Name: {sample_user.get('name', 'N/A')}")
            print(f"  Headline: {sample_user.get('headline', 'N/A')}")
            print()
        
        # Relationships
        if pages > 0 and posts > 0:
            sample_page = await db.pages.find_one({})
            page_id = sample_page.get('_id')
            posts_count = await db.posts.count_documents({"page_id": page_id})
            users_count = await db.users.count_documents({"page_id": page_id})
            print(f"Relationships for '{sample_page.get('name', 'N/A')}':")
            print(f"  Posts: {posts_count}")
            print(f"  People: {users_count}")
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure MongoDB is running: docker-compose ps")


if __name__ == "__main__":
    asyncio.run(show_stats())
