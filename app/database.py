"""
Database connection and configuration.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import sys
from config import settings


class Database:
    """Database connection manager."""
    
    client: AsyncIOMotorClient = None
    database = None


db = Database()


async def connect_to_mongo():
    """Create database connection."""
    try:
        db.client = AsyncIOMotorClient(settings.mongodb_url)
        db.database = db.client[settings.mongodb_db_name]
        # Test connection
        await db.client.admin.command('ping')
        print("[OK] Connected to MongoDB")
    except Exception as e:
        print(f"[WARNING] Failed to connect to MongoDB: {e}")
        print("[WARNING] Application will continue but database operations will fail")
        # Don't exit - allow app to start for testing without MongoDB


async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()
        print("[OK] Disconnected from MongoDB")


def get_database():
    """Get database instance."""
    return db.database

