from app.database.database import SessionLocal
from app.models.user import User
import sys

try:
    db = SessionLocal()
    users = db.query(User).all()
    print(f"Total Users: {len(users)}")
    for u in users:
        print(f"User: {u.username}, Active: {u.is_active}")
except Exception as e:
    print(f"Error accessing DB: {e}")
