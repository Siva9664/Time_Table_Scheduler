from pymongo import MongoClient
from pymongo.database import Database
from ..core.config import settings

# Module-level client — created once at import time
_client: MongoClient = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGODB_URL)
    return _client

def get_db() -> Database:
    """FastAPI dependency that yields the MongoDB database object."""
    client = get_client()
    db = client[settings.DB_NAME]
    try:
        yield db
    finally:
        pass  # PyMongo connections are pooled; no per-request close needed

def close_mongo_connection():
    global _client
    if _client is not None:
        _client.close()
        _client = None
