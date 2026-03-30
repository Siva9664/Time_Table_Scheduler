from app.database.database import get_db
from app.core.security import get_password_hash
import sys

def init_db():
    try:
        # get_db returns a generator, so we use next() to get the actual db object
        db = next(get_db())
        users_collection = db["users"]
        
        admin = users_collection.find_one({"username": "admin"})
        if admin:
            print("Admin user already exists!")
            return
            
        print("Creating admin user...")
        admin_user = {
            "username": "admin",
            "email": "admin@timetable.com",
            "full_name": "System Administrator",
            "hashed_password": get_password_hash("admin123"),
            "is_active": True,
            "is_admin": True,
            "created_at": __import__('datetime').datetime.utcnow()
        }
        users_collection.insert_one(admin_user)
        print("✓ Admin user created!")
        print("  Username: admin")
        print("  Password: admin123")
        print("  ⚠️  Change password after first login!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
