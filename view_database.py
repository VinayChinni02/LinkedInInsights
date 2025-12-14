"""
Script to view database contents in terminal.
Shows pages, posts, people, and comments with relationships.
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from bson import ObjectId

def format_object_id(obj_id):
    """Format ObjectId for display."""
    if isinstance(obj_id, ObjectId):
        return str(obj_id)[:8] + "..."
    return str(obj_id)[:20] if obj_id else "None"

async def view_database():
    """View database contents in a readable format."""
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]
    
    print("=" * 100)
    print("LINKEDIN INSIGHTS DATABASE - COMPLETE VIEW")
    print("=" * 100)
    
    # 1. PAGES
    print("\n" + "=" * 100)
    print("PAGES (Companies)")
    print("=" * 100)
    pages = await db.pages.find({}).to_list(length=100)
    print(f"\nTotal Pages: {len(pages)}\n")
    
    for i, page in enumerate(pages, 1):
        print(f"\n[{i}] {page.get('name', 'Unknown')}")
        print(f"    ID: {format_object_id(page.get('_id'))}")
        print(f"    Page ID: {page.get('page_id', 'N/A')}")
        print(f"    URL: {page.get('url', 'N/A')[:80]}...")
        print(f"    Followers: {page.get('total_followers', 'N/A')}")
        print(f"    Industry: {page.get('industry', 'N/A')}")
        print(f"    Location: {page.get('location', 'N/A')}")
        print(f"    Scraped: {page.get('scraped_at', 'N/A')}")
        
        # Count related posts
        page_id = page.get('_id')
        posts_count = await db.posts.count_documents({"page_id": page_id})
        people_count = await db.users.count_documents({"page_id": page_id})
        print(f"    -> Has {posts_count} posts, {people_count} people")
    
    # 2. POSTS (Sample)
    print("\n" + "=" * 100)
    print("POSTS (Recent 20)")
    print("=" * 100)
    posts = await db.posts.find({}).sort("scraped_at", -1).limit(20).to_list(length=20)
    print(f"\nShowing {len(posts)} most recent posts (out of {await db.posts.count_documents({})} total)\n")
    
    for i, post in enumerate(posts, 1):
        content = post.get('content', '')[:100] + "..." if len(post.get('content', '')) > 100 else post.get('content', '')
        print(f"\n[{i}] {content}")
        print(f"    Post ID: {format_object_id(post.get('_id'))}")
        print(f"    Page ID: {format_object_id(post.get('page_id'))}")
        print(f"    Author: {post.get('author_name', 'N/A')}")
        print(f"    URL: {post.get('post_url', 'N/A')[:60] if post.get('post_url') else 'N/A'}...")
        print(f"    Likes: {post.get('likes', 0)}, Comments: {post.get('comments_count', 0)}, Shares: {post.get('shares', 0)}")
        print(f"    Image: {'Yes' if post.get('image_url') else 'No'}")
        print(f"    Created: {post.get('created_at', 'N/A')}")
        print(f"    Scraped: {post.get('scraped_at', 'N/A')}")
        
        # Count comments
        post_id = post.get('_id')
        comments_count = await db.comments.count_documents({"post_id": post_id})
        print(f"    -> Has {comments_count} comments")
    
    # 3. PEOPLE (Sample)
    print("\n" + "=" * 100)
    print("PEOPLE (Recent 20)")
    print("=" * 100)
    people = await db.users.find({}).sort("scraped_at", -1).limit(20).to_list(length=20)
    print(f"\nShowing {len(people)} most recent people (out of {await db.users.count_documents({})} total)\n")
    
    for i, person in enumerate(people, 1):
        print(f"\n[{i}] {person.get('name', 'Unknown')}")
        print(f"    User ID: {format_object_id(person.get('_id'))}")
        print(f"    Page ID: {format_object_id(person.get('page_id'))}")
        print(f"    LinkedIn ID: {person.get('linkedin_user_id', 'N/A')}")
        print(f"    Profile URL: {person.get('profile_url', 'N/A')[:60] if person.get('profile_url') else 'N/A'}...")
        print(f"    Headline: {person.get('headline', 'N/A')}")
        print(f"    Location: {person.get('location', 'N/A')}")
        print(f"    Position: {person.get('current_position', 'N/A')}")
        print(f"    Picture: {'Yes' if person.get('profile_picture') else 'No'}")
        print(f"    Scraped: {person.get('scraped_at', 'N/A')}")
    
    # 4. COMMENTS (Sample)
    print("\n" + "=" * 100)
    print("COMMENTS (Recent 10)")
    print("=" * 100)
    comments = await db.comments.find({}).sort("scraped_at", -1).limit(10).to_list(length=10)
    print(f"\nShowing {len(comments)} most recent comments (out of {await db.comments.count_documents({})} total)\n")
    
    for i, comment in enumerate(comments, 1):
        content = comment.get('content', '')[:80] + "..." if len(comment.get('content', '')) > 80 else comment.get('content', '')
        print(f"\n[{i}] {content}")
        print(f"    Comment ID: {format_object_id(comment.get('_id'))}")
        print(f"    Post ID: {format_object_id(comment.get('post_id'))}")
        print(f"    Author: {comment.get('author_name', 'N/A')}")
        print(f"    Likes: {comment.get('likes', 0)}")
        print(f"    Scraped: {comment.get('scraped_at', 'N/A')}")
    
    # 5. STATISTICS
    print("\n" + "=" * 100)
    print("DATABASE STATISTICS")
    print("=" * 100)
    print(f"\nTotal Pages: {await db.pages.count_documents({})}")
    print(f"Total Posts: {await db.posts.count_documents({})}")
    print(f"Total People: {await db.users.count_documents({})}")
    print(f"Total Comments: {await db.comments.count_documents({})}")
    
    # Null value statistics
    posts_null_author = await db.posts.count_documents({"author_name": None})
    posts_null_url = await db.posts.count_documents({"post_url": None})
    people_null_headline = await db.users.count_documents({"headline": None})
    people_null_location = await db.users.count_documents({"location": None})
    
    print(f"\nData Completeness:")
    print(f"  Posts with author_name: {await db.posts.count_documents({'author_name': {'$ne': None}})}/{await db.posts.count_documents({})}")
    print(f"  Posts with post_url: {await db.posts.count_documents({'post_url': {'$ne': None}})}/{await db.posts.count_documents({})}")
    print(f"  People with headline: {await db.users.count_documents({'headline': {'$ne': None}})}/{await db.users.count_documents({})}")
    print(f"  People with location: {await db.users.count_documents({'location': {'$ne': None}})}/{await db.users.count_documents({})}")
    
    print("\n" + "=" * 100)
    print("END OF DATABASE VIEW")
    print("=" * 100)
    
    client.close()

if __name__ == "__main__":
    try:
        asyncio.run(view_database())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
