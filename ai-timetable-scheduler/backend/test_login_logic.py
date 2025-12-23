from app.database.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password
import sys

def test_login():
    db = SessionLocal()
    try:
        for username in ["admin", "shiva"]:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                print(f"User {username} not found")
                continue
            
            # The password we set was "shiva123" for both in the last run
            password = "shiva123"
            try:
                result = verify_password(password, user.hashed_password)
                print(f"Login test for {username} with password '{password}': {'SUCCESS' if result else 'FAILED'}")
            except Exception as e:
                print(f"Login test for {username} failed with error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_login()
