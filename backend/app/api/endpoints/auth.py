from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.database import Database
from datetime import timedelta, datetime
from ...database.database import get_db
from ...models.user import user_helper
from ...schemas.user import UserCreate, UserResponse, Token, UserChangePassword
from ...core.security import verify_password, get_password_hash, create_access_token, get_current_user
from ...core.config import settings

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Database = Depends(get_db)):
    if db["users"].find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    if db["users"].find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": get_password_hash(user.password),
        "is_active": True,
        "is_admin": False,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }
    result = db["users"].insert_one(doc)
    created = db["users"].find_one({"_id": result.inserted_id})
    return user_helper(created)

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Database = Depends(get_db)):
    user = db["users"].find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: dict = Depends(get_current_user)):
    return user_helper(current_user)

@router.post("/change-password")
def change_password(password_data: UserChangePassword, current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    if not verify_password(password_data.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")
    db["users"].update_one(
        {"_id": current_user["_id"]},
        {"$set": {"hashed_password": get_password_hash(password_data.new_password), "updated_at": datetime.utcnow()}}
    )
    return {"message": "Password updated successfully"}
