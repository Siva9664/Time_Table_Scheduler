from app.database.database import SessionLocal
from app.models.user import User
import bcrypt
import sys

def get_hash(password: str) -> str:
    # Manual hash using bcrypt to bypass passlib issues
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def update_passwords():
    db = SessionLocal()
    try:
        # Update admin
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print("Updating admin password to shiva123...")
            admin.hashed_password = get_hash("shiva123")
        else:
            print("Admin user not found!")

        # Update shiva
        shiva = db.query(User).filter(User.username == "shiva").first()
        if shiva:
            print("Updating shiva password to shiva123...")
            shiva.hashed_password = get_hash("shiva123")
        else:
            print("User 'shiva' not found! Creating user 'shiva'...")
            shiva = User(
                username="shiva",
                email="shiva@example.com",
                full_name="Shiva",
                hashed_password=get_hash("shiva123"),
                is_active=True,
                is_admin=True
            )
            db.add(shiva)
            print("Created user 'shiva' with password 'shiva123'.")
        
        db.commit()
        print("Passwords updated successfully.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    update_passwords()
