"""
Script to delete specific pages from the database.
Deletes the page and all related posts, people, and comments.
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from bson import ObjectId

async def delete_pages():
    """Delete specified pages and all related data."""
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]
    
    # Pages to delete
    page_ids_to_delete = ["google", "atlassian", "deepsolv"]
    
    print("=" * 100)
    print("DELETING PAGES FROM DATABASE")
    print("=" * 100)
    
    for page_id in page_ids_to_delete:
        print(f"\nProcessing page: {page_id}")
        
        # Find the page
        page = await db.pages.find_one({"page_id": page_id})
        if not page:
            print(f"  ❌ Page '{page_id}' not found in database")
            continue
        
        page_db_id = page.get("_id")
        page_name = page.get("name", page_id)
        
        print(f"  ✓ Found page: {page_name} (ID: {str(page_db_id)[:8]}...)")
        
        # Count related data
        posts_count = await db.posts.count_documents({"page_id": page_db_id})
        people_count = await db.users.count_documents({"page_id": page_db_id})
        
        # Get post IDs for this page to delete comments
        post_ids = []
        async for post in db.posts.find({"page_id": page_db_id}, {"_id": 1}):
            post_ids.append(post["_id"])
        
        comments_count = await db.comments.count_documents({"post_id": {"$in": post_ids}}) if post_ids else 0
        
        print(f"  📊 Related data: {posts_count} posts, {people_count} people, {comments_count} comments")
        
        # Delete comments first
        if post_ids:
            comments_result = await db.comments.delete_many({"post_id": {"$in": post_ids}})
            print(f"  ✓ Deleted {comments_result.deleted_count} comments")
        
        # Delete posts
        posts_result = await db.posts.delete_many({"page_id": page_db_id})
        print(f"  ✓ Deleted {posts_result.deleted_count} posts")
        
        # Delete people
        people_result = await db.users.delete_many({"page_id": page_db_id})
        print(f"  ✓ Deleted {people_result.deleted_count} people")
        
        # Delete the page
        page_result = await db.pages.delete_one({"page_id": page_id})
        if page_result.deleted_count > 0:
            print(f"  ✓ Deleted page: {page_name}")
        else:
            print(f"  ❌ Failed to delete page: {page_name}")
    
    print("\n" + "=" * 100)
    print("DELETION COMPLETE")
    print("=" * 100)
    
    # Show remaining pages
    remaining_pages = await db.pages.find({}).to_list(length=100)
    print(f"\nRemaining pages in database: {len(remaining_pages)}")
    for page in remaining_pages:
        print(f"  - {page.get('name', 'Unknown')} ({page.get('page_id', 'N/A')})")
    
    client.close()

if __name__ == "__main__":
    try:
        asyncio.run(delete_pages())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
