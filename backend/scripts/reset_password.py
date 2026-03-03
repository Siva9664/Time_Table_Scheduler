from app.database.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import sys

def reset_password():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("Admin user not found! Creating one...")
            admin_user = User(username="admin", email="admin@timetable.com", full_name="System Administrator",
                             hashed_password=get_password_hash("admin123"), is_active=True, is_admin=True)
            db.add(admin_user)
        else:
            print("Updating admin password...")
            admin.hashed_password = get_password_hash("admin123")
        
        db.commit()
        print("Admin password reset to: admin123")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    reset_password()
