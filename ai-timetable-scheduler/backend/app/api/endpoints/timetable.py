from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ...database.database import get_db
from ...models.user import User
from ...models.timetable import Department, Class, Subject, Faculty, Room, Timetable, Batch
from ...schemas.timetable import *
from ...core.security import get_current_user
from ...services.scheduler import TimetableScheduler
from ...services.ai_parser import AIConstraintParser
from ...core.config import settings

router = APIRouter()

# Batches
@router.post("/batches", response_model=BatchResponse)
def create_batch(batch: BatchCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_batch = Batch(**batch.dict())
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)
    return db_batch

@router.get("/batches", response_model=List[BatchResponse])
def list_batches(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Batch).all()

@router.delete("/batches/{id}")
def delete_batch(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Batch).filter(Batch.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"message": "Deleted"}

# Departments
@router.post("/departments", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_dept = Department(**dept.dict())
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    return db_dept

@router.get("/departments", response_model=List[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Department).all()

@router.delete("/departments/{id}")
def delete_department(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dept = db.query(Department).filter(Department.id == id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        db.delete(dept)
        db.commit()
    except Exception as e:
        db.rollback()
        # Check for integrity error (generic catch to be safe, but likely foreign key)
        if "foreign key constraint" in str(e).lower() or "integrity" in str(e).lower():
            raise HTTPException(status_code=400, detail="Cannot delete Department: It has associated Faculty or Classes. Please delete them first.")
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Deleted"}

# Classes
@router.post("/classes", response_model=ClassResponse)
def create_class(cls: ClassCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_class = Class(**cls.dict())
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class

@router.get("/classes", response_model=List[ClassResponse])
def list_classes(department_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Class)
    if department_id:
        query = query.filter(Class.department_id == department_id)
    return query.all()

@router.delete("/classes/{id}")
def delete_class(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Class).filter(Class.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"message": "Deleted"}

# Subjects
@router.post("/subjects", response_model=SubjectResponse)
def create_subject(subj: SubjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_subj = Subject(**subj.dict())
    db.add(db_subj)
    db.commit()
    db.refresh(db_subj)
    return db_subj

@router.get("/subjects", response_model=List[SubjectResponse])
def list_subjects(class_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Subject)
    if class_id:
        query = query.filter(Subject.class_id == class_id)
    return query.all()

@router.put("/subjects/{id}", response_model=SubjectResponse)
def update_subject(id: int, subj: SubjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_subj = db.query(Subject).filter(Subject.id == id).first()
    if not db_subj:
        raise HTTPException(status_code=404, detail="Not found")
    
    update_data = subj.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_subj, key, value)
    
    db.commit()
    db.refresh(db_subj)
    return db_subj

@router.delete("/subjects/{id}")
def delete_subject(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Subject).filter(Subject.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"message": "Deleted"}

# Faculty
@router.post("/faculty", response_model=FacultyResponse)
def create_faculty(fac: FacultyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_fac = Faculty(**fac.dict())
    db.add(db_fac)
    db.commit()
    db.refresh(db_fac)
    return db_fac

@router.get("/faculty", response_model=List[FacultyResponse])
def list_faculty(department_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Faculty)
    if department_id:
        query = query.filter(Faculty.department_id == department_id)
    return query.all()

@router.delete("/faculty/{id}")
def delete_faculty(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Faculty).filter(Faculty.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"message": "Deleted"}

# Rooms
@router.post("/rooms", response_model=RoomResponse)
def create_room(room: RoomCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_room = Room(**room.dict())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.get("/rooms", response_model=List[RoomResponse])
def list_rooms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Room).all()

@router.delete("/rooms/{id}")
def delete_room(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Room).filter(Room.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"message": "Deleted"}

# Timetable Generation
@router.post("/generate", response_model=TimetableResponse)
def generate_timetable(request: TimetableGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    custom_constraints = []
    if request.constraints_text and settings.GEMINI_API_KEY:
        try:
            parser = AIConstraintParser(api_key=settings.GEMINI_API_KEY)
            custom_constraints = parser.parse_constraints(request.constraints_text)
            print(f"Parsed Constraints: {custom_constraints}") # Debug log
        except Exception as e:
            print(f"AI Parser Warning: {e}")
            pass

    scheduler = TimetableScheduler(db=db, working_days=request.working_days, periods_per_day=request.periods_per_day,
                                   time_limit_seconds=settings.SOLVER_TIME_LIMIT_SECONDS,
                                   custom_constraints=custom_constraints)
    result = scheduler.generate_schedule(department_ids=request.department_ids)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    if result["status"] in ["INFEASIBLE", "MODEL_INVALID"]:
        raise HTTPException(status_code=400, detail=f"Could not find valid timetable. Status: {result['status']}")
    db_timetable = Timetable(name=request.name, academic_year=request.academic_year, semester=request.semester,
                            schedule_data=result["schedule"], constraints_used={
                                "working_days": request.working_days, 
                                "periods_per_day": request.periods_per_day, 
                                "department_ids": request.department_ids,
                                "start_time": request.start_time,
                                "end_time": request.end_time,
                                "period_duration_mins": request.period_duration_mins,
                                "break_after_period": request.break_after_period,
                                "break_duration_mins": request.break_duration_mins,
                                "lunch_after_period": request.lunch_after_period,
                                "lunch_duration_mins": request.lunch_duration_mins,
                                "break2_after_period": request.break2_after_period,
                                "break2_duration_mins": request.break2_duration_mins
                            },
                            solver_status=result["status"], solve_time_seconds=result["solve_time"])
    db.add(db_timetable)
    db.commit()
    db.refresh(db_timetable)
    return db_timetable

@router.get("/timetables", response_model=List[TimetableResponse])
def list_timetables(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Timetable).order_by(Timetable.created_at.desc()).all()

@router.get("/timetables/{id}", response_model=TimetableResponse)
def get_timetable(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return obj

@router.delete("/timetables/{id}")
def delete_timetable(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = db.query(Timetable).filter(Timetable.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"message": "Deleted"}

