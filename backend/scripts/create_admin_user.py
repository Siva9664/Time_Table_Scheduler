from app.database.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import sys

def init_db():
    from app.database.database import engine, Base
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print("Admin user already exists!")
            return
        print("Creating admin user...")
        admin_user = User(username="admin", email="admin@timetable.com", full_name="System Administrator",
                         hashed_password=get_password_hash("admin123"), is_active=True, is_admin=True)
        db.add(admin_user)
        db.commit()
        print("✓ Admin user created!")
        print("  Username: admin")
        print("  Password: admin123")
        print("  ⚠️  Change password after first login!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
