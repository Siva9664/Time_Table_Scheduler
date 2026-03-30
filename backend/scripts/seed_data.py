import os
import sys
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Add the parent directory to sys.path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import get_db
from app.models.timetable import (
    department_helper, batch_helper, class_helper,
    subject_helper, faculty_helper, room_helper
)

def seed_data():
    try:
        db = next(get_db())
        print(f"Connected to database: {db.name}")

        # 1. Departments
        if db["departments"].count_documents({}) == 0:
            print("Seeding Departments...")
            depts = [
                {"name": "Computer Science", "code": "CS", "description": "Dept of CS"},
                {"name": "Electronics", "code": "EC", "description": "Dept of ECE"}
            ]
            db["departments"].insert_many(depts)
        
        cs_dept = db["departments"].find_one({"code": "CS"})
        ec_dept = db["departments"].find_one({"code": "EC"})

        # 2. Batches
        if db["batches"].count_documents({}) == 0:
            print("Seeding Batches...")
            batches = [
                {"name": "2024-2028", "is_active": True},
                {"name": "2023-2027", "is_active": True}
            ]
            db["batches"].insert_many(batches)
        
        batch1 = db["batches"].find_one({"name": "2024-2028"})

        # 3. Classes
        if db["classes"].count_documents({}) == 0:
            print("Seeding Classes...")
            classes = [
                {"name": "CS-A", "department_id": str(cs_dept["_id"]), "batch_id": str(batch1["_id"]), "sections": ["A"]},
                {"name": "EC-A", "department_id": str(ec_dept["_id"]), "batch_id": str(batch1["_id"]), "sections": ["A"]}
            ]
            db["classes"].insert_many(classes)
        
        cs_class = db["classes"].find_one({"name": "CS-A"})

        # 4. Subjects
        if db["subjects"].count_documents({}) == 0:
            print("Seeding Subjects...")
            subjects = [
                {"name": "Data Structures", "code": "CS101", "class_id": str(cs_class["_id"]), "weekly_hours": 4},
                {"name": "Algorithms", "code": "CS102", "class_id": str(cs_class["_id"]), "weekly_hours": 3}
            ]
            db["subjects"].insert_many(subjects)

        # 5. Faculty
        if db["faculty"].count_documents({}) == 0:
            print("Seeding Faculty...")
            faculty = [
                {"name": "Dr. Smith", "email": "smith@test.com", "department_id": str(cs_dept["_id"]), "is_active": True, "availability": []},
                {"name": "Dr. Jane", "email": "jane@test.com", "department_id": str(ec_dept["_id"]), "is_active": True, "availability": []}
            ]
            db["faculty"].insert_many(faculty)

        # 6. Rooms
        if db["rooms"].count_documents({}) == 0:
            print("Seeding Rooms...")
            rooms = [
                {"name": "L-101", "capacity": 60, "type": "Theory", "is_active": True},
                {"name": "L-102", "capacity": 60, "type": "Theory", "is_active": True}
            ]
            db["rooms"].insert_many(rooms)

        print("✅ Data seeding complete!")

    except Exception as e:
        print(f"❌ Seeding failed: {e}")

if __name__ == "__main__":
    seed_data()
