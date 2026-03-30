from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

# Module-level client — created once at import time
_client: MongoClient = None
_connection_ready: bool = False

def get_client() -> MongoClient:
    """Get or create MongoDB client with fallback logic."""
    global _client, _connection_ready
    
    if _client is not None:
        return _client
    
    # Try MongoDB Atlas first
    try:
        conn_args = {
            "serverSelectionTimeoutMS": 5000,
            "connectTimeoutMS": 10000,
            "retryWrites": True,
            "maxPoolSize": 10
        }
        
        # Check if we should allow invalid certificates (common in some restricted environments)
        _client = MongoClient(settings.MONGODB_URL, **conn_args)
        _client.admin.command('ping')
        _connection_ready = True
        logger.info("✅ Connected to MongoDB Atlas")
        return _client
    except Exception as e:
        logger.warning(f"⚠️ Primary connection failed: {str(e)[:100]}")
        try:
            # Try with SSL verification disabled as fallback
            logger.info("Retrying with SSL verification disabled...")
            _client = MongoClient(settings.MONGODB_URL, tlsAllowInvalidCertificates=True, **conn_args)
            _client.admin.command('ping')
            _connection_ready = True
            logger.info("✅ Connected to MongoDB Atlas (SSL verification disabled)")
            return _client
        except Exception as e2:
            logger.warning(f"⚠️ MongoDB Atlas unavailable: {str(e2)[:100]}")
        
        # Fallback to local MongoDB
        try:
            _client = MongoClient(
                "mongodb://localhost:27017",
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=5000
            )
            _client.admin.command('ping')
            _connection_ready = True
            logger.info("✅ Connected to Local MongoDB")
            return _client
        except Exception as e2:
            logger.error(f"❌ All MongoDB connections failed: {str(e2)[:100]}")
            # Return client anyway - will fail on actual queries
            _client = MongoClient("mongodb://localhost:27017")
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
    """Close the MongoDB connection."""
    global _client, _connection_ready
    if _client is not None:
        try:
            _client.close()
        except:
            pass
        _client = None
        _connection_ready = False
