"""
Database package for data access and indexes.
"""
from app.database.database import (
    connect_to_mongo,
    close_mongo_connection,
    get_database,
    db
)

__all__ = [
    "connect_to_mongo",
    "close_mongo_connection",
    "get_database",
    "db"
]

