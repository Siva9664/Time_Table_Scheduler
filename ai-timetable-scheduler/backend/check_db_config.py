
import sys
import os

# Add current directory to sys.path to allow imports
sys.path.append(os.getcwd())

from app.core.config import settings
from app.database.database import SessionLocal, engine
from app.models.timetable import Faculty, Department
from sqlalchemy import text

print(f"Current Working Directory: {os.getcwd()}")
print(f"DATABASE_URL: {settings.DATABASE_URL}")

try:
    db = SessionLocal()
    print("Database session created.")
    
    # Check if we can connect
    db.execute(text("SELECT 1"))
    print("Database connection successful.")
    
    # List Departments
    depts = db.query(Department).all()
    print(f"Found {len(depts)} departments.")
    for d in depts:
        print(f" - ID: {d.id}, Name: {d.name}")
        
    if not depts:
        print("No departments found. Cannot create faculty without department.")
        # Create a dummy department
        new_dept = Department(name="Debug Dept", code="DBG001")
        db.add(new_dept)
        db.commit()
        db.refresh(new_dept)
        print(f"Created debug department with ID: {new_dept.id}")
        dept_id = new_dept.id
    else:
        dept_id = depts[0].id

    # Try to create a faculty
    test_email = "debug_faculty@example.com"
    existing = db.query(Faculty).filter(Faculty.email == test_email).first()
    if existing:
        print(f"Faculty with email {test_email} already exists. ID: {existing.id}")
        # Clean up
        db.delete(existing)
        db.commit()
        print("Deleted existing debug faculty.")
        
    new_faculty = Faculty(
        name="Debug Faculty",
        email=test_email,
        department_id=dept_id,
        max_hours_per_week=20
    )
    db.add(new_faculty)
    db.commit()
    db.refresh(new_faculty)
    print(f"Successfully created faculty. ID: {new_faculty.id}")
    
    # Verify persistence
    db.close()
    
    db2 = SessionLocal()
    saved_faculty = db2.query(Faculty).filter(Faculty.id == new_faculty.id).first()
    if saved_faculty:
        print(f"VERIFICATION SUCCESS: Faculty found in new session. ID: {saved_faculty.id}, Name: {saved_faculty.name}")
    else:
        print("VERIFICATION FAILED: Faculty not found in new session.")
    
    # Clean up
    db2.delete(saved_faculty)
    db2.commit()
    print("Cleaned up debug faculty.")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

