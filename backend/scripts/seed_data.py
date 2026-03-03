from sqlalchemy.orm import Session
from app.database.database import SessionLocal, engine
from app.models.timetable import Base, Department, Class, Subject, Faculty, Room, Batch

# Ensure tables exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    print("Seeding data...")
    
    # 1. Departments
    dept_cs = db.query(Department).filter_by(code="CS").first()
    if not dept_cs:
        dept_cs = Department(name="Computer Science", code="CS", description="CS Department")
        db.add(dept_cs)
        print("Added Dept: CS")
    
    dept_ec = db.query(Department).filter_by(code="EC").first()
    if not dept_ec:
        dept_ec = Department(name="Electronics", code="EC", description="EC Department")
        db.add(dept_ec)
        print("Added Dept: EC")
    
    db.commit()
    
    # 2. Batches
    batch = db.query(Batch).first()
    if not batch:
        batch = Batch(name="Morning Batch", start_time="09:00", end_time="16:00", period_duration=60)
        db.add(batch)
        db.commit() # Commit to get ID
        print("Added Batch: Morning")

    # 3. Faculty
    fac_john = db.query(Faculty).filter_by(email="john@test.com").first()
    if not fac_john:
        fac_john = Faculty(name="John Doe", email="john@test.com", department_id=dept_cs.id)
        db.add(fac_john)
        print("Added Faculty: John Doe")

    fac_jane = db.query(Faculty).filter_by(email="jane@test.com").first()
    if not fac_jane:
        fac_jane = Faculty(name="Jane Smith", email="jane@test.com", department_id=dept_ec.id)
        db.add(fac_jane)
        print("Added Faculty: Jane Smith")
    
    db.commit()

    # 4. Classes
    cls_cs1 = db.query(Class).filter_by(name="B.Tech CS 1").first()
    if not cls_cs1:
        cls_cs1 = Class(name="B.Tech CS 1", section="A", department_id=dept_cs.id, batch_id=batch.id)
        db.add(cls_cs1)
        print("Added Class: B.Tech CS 1")
    
    db.commit()

    # 5. Subjects
    sub_py = db.query(Subject).filter_by(code="CS101").first()
    if not sub_py:
        sub_py = Subject(name="Python Programming", code="CS101", hours_per_week=4, requires_lab=False, department_id=dept_cs.id, batch_id=batch.id, faculty_id=fac_john.id)
        db.add(sub_py)
        print("Added Subject: Python")

    sub_lab = db.query(Subject).filter_by(code="CS101L").first()
    if not sub_lab:
        sub_lab = Subject(name="Python Lab", code="CS101L", hours_per_week=3, requires_lab=True, department_id=dept_cs.id, batch_id=batch.id, faculty_id=fac_john.id)
        db.add(sub_lab)
        print("Added Subject: Python Lab")
    
    db.commit()

    # 6. Rooms
    room_101 = db.query(Room).filter_by(name="Room 101").first()
    if not room_101:
        room_101 = Room(name="Room 101", capacity=60, room_type="classroom")
        db.add(room_101)
        print("Added Room: 101")
        
    lab_1 = db.query(Room).filter_by(name="Comp Lab 1").first()
    if not lab_1:
        lab_1 = Room(name="Comp Lab 1", capacity=30, room_type="lab")
        db.add(lab_1)
        print("Added Room: Lab 1")
    
    db.commit()
    print("Seeding complete!")

except Exception as e:
    print(f"Error seeding data: {e}")
    db.rollback()
finally:
    db.close()
