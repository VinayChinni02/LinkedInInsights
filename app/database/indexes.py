"""
Database indexes for performance optimization.
Indexes are critical for scalable database queries.
"""
from app.database.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase


async def create_indexes():
    """
    Create database indexes for optimal query performance.
    This should be called during application startup.
    """
    db: AsyncIOMotorDatabase = get_database()
    
    if not db:
        print("[WARNING] Database not initialized. Skipping index creation.")
        return
    
    try:
        # Pages collection indexes
        pages_collection = db.pages
        
        # Index on page_id (most common query field)
        await pages_collection.create_index("page_id", unique=True, name="page_id_unique")
        
        # Index on linkedin_id for lookups
        await pages_collection.create_index("linkedin_id", name="linkedin_id_idx")
        
        # Index on total_followers for range queries
        await pages_collection.create_index("total_followers", name="followers_idx")
        
        # Index on industry for filtering
        await pages_collection.create_index("industry", name="industry_idx")
        
        # Index on name for text search (case-insensitive)
        await pages_collection.create_index("name", name="name_idx")
        
        # Compound index for common filter combinations
        await pages_collection.create_index(
            [("total_followers", 1), ("industry", 1)],
            name="followers_industry_idx"
        )
        
        # Index on updated_at for sorting
        await pages_collection.create_index("updated_at", name="updated_at_idx")
        
        print("[OK] Created indexes for 'pages' collection")
        
        # Posts collection indexes
        posts_collection = db.posts
        
        # Index on page_id (foreign key - most common query)
        await posts_collection.create_index("page_id", name="post_page_id_idx")
        
        # Index on created_at for sorting recent posts
        await posts_collection.create_index("created_at", name="post_created_at_idx")
        
        # Compound index for page_id + created_at (common query pattern)
        await posts_collection.create_index(
            [("page_id", 1), ("created_at", -1)],
            name="post_page_created_idx"
        )
        
        # Index on linkedin_post_id for uniqueness
        await posts_collection.create_index("linkedin_post_id", name="linkedin_post_id_idx")
        
        print("[OK] Created indexes for 'posts' collection")
        
        # Comments collection indexes
        comments_collection = db.comments
        
        # Index on post_id (foreign key)
        await comments_collection.create_index("post_id", name="comment_post_id_idx")
        
        # Index on created_at for sorting
        await comments_collection.create_index("created_at", name="comment_created_at_idx")
        
        print("[OK] Created indexes for 'comments' collection")
        
        # Users collection indexes
        users_collection = db.users
        
        # Index on page_id (foreign key)
        await users_collection.create_index("page_id", name="user_page_id_idx")
        
        # Index on linkedin_user_id for uniqueness
        await users_collection.create_index("linkedin_user_id", name="linkedin_user_id_idx")
        
        # Index on name for search
        await users_collection.create_index("name", name="user_name_idx")
        
        print("[OK] Created indexes for 'users' collection")
        
        print("[OK] All database indexes created successfully")
        
    except Exception as e:
        print(f"[ERROR] Failed to create indexes: {e}")
        # Don't raise - allow app to continue even if indexes fail
        # Indexes can be created manually later
