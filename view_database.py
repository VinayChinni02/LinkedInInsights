"""
Script to view MongoDB database contents.
Shows all pages, posts, people, and comments with relationships.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
import json


# Database configuration
MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "linkedin_insights"


def format_datetime(dt):
    """Format datetime for display."""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def format_objectid(obj_id):
    """Format ObjectId for display."""
    if isinstance(obj_id, ObjectId):
        return str(obj_id)
    return obj_id


async def view_database():
    """View all database contents."""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DB_NAME]
        
        print("=" * 80)
        print("MongoDB Database Viewer")
        print("=" * 80)
        print(f"Database: {DB_NAME}")
        print(f"Connection: {MONGODB_URL}\n")
        
        # Get collection counts
        pages_count = await db.pages.count_documents({})
        posts_count = await db.posts.count_documents({})
        users_count = await db.users.count_documents({})
        comments_count = await db.comments.count_documents({})
        
        print("Collection Statistics:")
        print(f"  Pages: {pages_count}")
        print(f"  Posts: {posts_count}")
        print(f"  Users/People: {users_count}")
        print(f"  Comments: {comments_count}")
        print()
        
        # View Pages
        print("=" * 80)
        print("PAGES")
        print("=" * 80)
        
        pages = await db.pages.find({}).to_list(length=100)
        
        if not pages:
            print("No pages found in database.")
            print("Tip: Make an API request to scrape a page first:")
            print("  GET http://localhost:8000/api/v1/pages/ocecas-mitblr?force_refresh=true")
        else:
            for i, page in enumerate(pages, 1):
                print(f"\n[{i}] Page: {page.get('name', 'N/A')}")
                print(f"    ID: {format_objectid(page.get('_id'))}")
                print(f"    Page ID: {page.get('page_id', 'N/A')}")
                print(f"    URL: {page.get('url', 'N/A')}")
                print(f"    LinkedIn ID: {page.get('linkedin_id', 'N/A')}")
                print(f"    Description: {page.get('description', 'N/A')[:100]}..." if page.get('description') else "    Description: None")
                print(f"    Followers: {page.get('total_followers', 'N/A')}")
                print(f"    Industry: {page.get('industry', 'N/A')}")
                print(f"    Location: {page.get('location', 'N/A')}")
                print(f"    Website: {page.get('website', 'N/A')}")
                print(f"    Scraped: {format_datetime(page.get('scraped_at'))}")
                print(f"    Updated: {format_datetime(page.get('updated_at'))}")
                
                # Get related posts count
                page_id = page.get('_id')
                posts_for_page = await db.posts.count_documents({"page_id": page_id})
                users_for_page = await db.users.count_documents({"page_id": page_id})
                print(f"    Related: {posts_for_page} posts, {users_for_page} people")
        
        # View Posts
        print("\n" + "=" * 80)
        print("POSTS")
        print("=" * 80)
        
        posts = await db.posts.find({}).to_list(length=50)
        
        if not posts:
            print("No posts found.")
        else:
            for i, post in enumerate(posts, 1):
                print(f"\n[{i}] Post")
                print(f"    ID: {format_objectid(post.get('_id'))}")
                print(f"    Page ID: {format_objectid(post.get('page_id', 'N/A'))}")
                print(f"    Content: {post.get('content', 'N/A')[:100]}..." if post.get('content') else "    Content: None")
                print(f"    Author: {post.get('author_name', 'N/A')}")
                print(f"    Likes: {post.get('likes', 0)}")
                print(f"    Comments: {post.get('comments_count', 0)}")
                print(f"    Shares: {post.get('shares', 0)}")
                print(f"    Created: {format_datetime(post.get('created_at'))}")
                
                # Get comments count
                post_id = post.get('_id')
                comments_for_post = await db.comments.count_documents({"post_id": post_id})
                print(f"    Related: {comments_for_post} comments")
        
        # View Users/People
        print("\n" + "=" * 80)
        print("PEOPLE/USERS")
        print("=" * 80)
        
        users = await db.users.find({}).to_list(length=50)
        
        if not users:
            print("No people found.")
        else:
            for i, user in enumerate(users, 1):
                print(f"\n[{i}] Person: {user.get('name', 'N/A')}")
                print(f"    ID: {format_objectid(user.get('_id'))}")
                print(f"    Page ID: {format_objectid(user.get('page_id', 'N/A'))}")
                print(f"    Profile URL: {user.get('profile_url', 'N/A')}")
                print(f"    Headline: {user.get('headline', 'N/A')}")
                print(f"    Position: {user.get('current_position', 'N/A')}")
                print(f"    Location: {user.get('location', 'N/A')}")
                print(f"    Connections: {user.get('connection_count', 'N/A')}")
        
        # View Comments
        print("\n" + "=" * 80)
        print("COMMENTS")
        print("=" * 80)
        
        comments = await db.comments.find({}).to_list(length=50)
        
        if not comments:
            print("No comments found.")
        else:
            for i, comment in enumerate(comments, 1):
                print(f"\n[{i}] Comment")
                print(f"    ID: {format_objectid(comment.get('_id'))}")
                print(f"    Post ID: {format_objectid(comment.get('post_id', 'N/A'))}")
                print(f"    Author: {comment.get('author_name', 'N/A')}")
                print(f"    Content: {comment.get('content', 'N/A')[:100]}..." if comment.get('content') else "    Content: None")
                print(f"    Likes: {comment.get('likes', 0)}")
                print(f"    Created: {format_datetime(comment.get('created_at'))}")
        
        print("\n" + "=" * 80)
        print("Database view complete!")
        print("=" * 80)
        
        client.close()
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure MongoDB is running: docker-compose ps")
        print("2. Check MongoDB logs: docker-compose logs mongodb")
        print("3. Verify connection: mongodb://localhost:27017")


if __name__ == "__main__":
    asyncio.run(view_database())
