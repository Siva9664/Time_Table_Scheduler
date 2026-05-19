from fastapi import Depends, HTTPException, status
from pymongo.database import Database
from ..database.database import get_db, get_client
from .config import settings

async def get_current_user(db: Database = Depends(get_db)) -> dict:
    user = db["users"].find_one({"username": "admin"})
    if user is None:
        return {"_id": "mock_admin_id", "username": "admin", "is_admin": True, "tenant_db_name": settings.DB_NAME}
    return user

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensures current user is an admin"""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_tenant_db(current_user: dict = Depends(get_current_user)) -> Database:
    """Provides a database connection isolated to the current user's tenant"""
    tenant_db_name = current_user.get("tenant_db_name")
    if not tenant_db_name:
        tenant_db_name = settings.DB_NAME
    client = get_client()
    db = client[tenant_db_name]
    try:
        yield db
    finally:
        pass
