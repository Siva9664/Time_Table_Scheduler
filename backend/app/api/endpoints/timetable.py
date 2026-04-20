from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from bson import ObjectId
from typing import List, Optional
from datetime import datetime
from ...database.database import get_db
from ...models.timetable import (
    department_helper, batch_helper, class_helper,
    subject_helper, faculty_helper, room_helper, timetable_helper
)
from ...schemas.timetable import *
from ...core.security import get_current_user, get_admin_user, get_tenant_db
from ...services.scheduler import TimetableScheduler
from ...services.ai_parser import AIConstraintParser
from ...core.config import settings

router = APIRouter(redirect_slashes=False)

# ── helpers ──────────────────────────────────────────────────────────────────

def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid id: {id_str}")

# ── Batches ───────────────────────────────────────────────────────────────────

@router.post("/batches", response_model=BatchResponse)
def create_batch(batch: BatchCreate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    doc = {**batch.dict(), "created_at": datetime.utcnow()}
    result = db["batches"].insert_one(doc)
    return batch_helper(db["batches"].find_one({"_id": result.inserted_id}))

@router.get("/batches", response_model=List[BatchResponse])
def list_batches(db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    return [batch_helper(d) for d in db["batches"].find()]

@router.delete("/batches/{id}")
def delete_batch(id: str, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    result = db["batches"].delete_one({"_id": _oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}

@router.put("/batches/{id}", response_model=BatchResponse)
def update_batch(id: str, batch: BatchUpdate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    update_data = {k: v for k, v in batch.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db["batches"].update_one({"_id": _oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return batch_helper(db["batches"].find_one({"_id": _oid(id)}))

# ── Departments ───────────────────────────────────────────────────────────────

@router.post("/departments", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    doc = {**dept.dict(), "created_at": datetime.utcnow()}
    result = db["departments"].insert_one(doc)
    return department_helper(db["departments"].find_one({"_id": result.inserted_id}))

@router.get("/departments", response_model=List[DepartmentResponse])
def list_departments(db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    return [department_helper(d) for d in db["departments"].find()]

@router.delete("/departments/{id}")
def delete_department(id: str, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    # Check if any classes or faculty reference this department
    if db["classes"].find_one({"department_id": id}) or db["faculty"].find_one({"department_id": id}):
        raise HTTPException(status_code=400, detail="Cannot delete Department: It has associated Faculty or Classes. Please delete them first.")
    result = db["departments"].delete_one({"_id": _oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}

@router.put("/departments/{id}", response_model=DepartmentResponse)
def update_department(id: str, dept: DepartmentUpdate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    update_data = {k: v for k, v in dept.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db["departments"].update_one({"_id": _oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return department_helper(db["departments"].find_one({"_id": _oid(id)}))

# ── Classes ───────────────────────────────────────────────────────────────────

def _enrich_class(doc: dict, db: Database) -> dict:
    dept = db["departments"].find_one({"_id": _oid(doc["department_id"])}) if doc.get("department_id") else None
    batch = db["batches"].find_one({"_id": _oid(doc["batch_id"])}) if doc.get("batch_id") else None
    return class_helper(doc,
                        department=department_helper(dept) if dept else None,
                        batch=batch_helper(batch) if batch else None)

@router.post("/classes", response_model=ClassResponse)
def create_class(cls: ClassCreate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    doc = {**cls.dict(), "created_at": datetime.utcnow()}
    result = db["classes"].insert_one(doc)
    return _enrich_class(db["classes"].find_one({"_id": result.inserted_id}), db)

@router.get("/classes", response_model=List[ClassResponse])
def list_classes(department_id: Optional[str] = None, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    query = {"department_id": department_id} if department_id else {}
    return [_enrich_class(d, db) for d in db["classes"].find(query)]

@router.delete("/classes/{id}")
def delete_class(id: str, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    result = db["classes"].delete_one({"_id": _oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}

@router.put("/classes/{id}", response_model=ClassResponse)
def update_class(id: str, cls: ClassUpdate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    update_data = {k: v for k, v in cls.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db["classes"].update_one({"_id": _oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return _enrich_class(db["classes"].find_one({"_id": _oid(id)}), db)

# ── Subjects ──────────────────────────────────────────────────────────────────

def _enrich_subject(doc: dict, db: Database) -> dict:
    cls_doc = db["classes"].find_one({"_id": _oid(doc["class_id"])}) if doc.get("class_id") else None
    return subject_helper(doc, assigned_class=_enrich_class(cls_doc, db) if cls_doc else None)

@router.post("/subjects", response_model=SubjectResponse)
def create_subject(subj: SubjectCreate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    doc = {**subj.dict(), "created_at": datetime.utcnow()}
    result = db["subjects"].insert_one(doc)
    return _enrich_subject(db["subjects"].find_one({"_id": result.inserted_id}), db)

@router.get("/subjects", response_model=List[SubjectResponse])
def list_subjects(class_id: Optional[str] = None, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    query = {"class_id": class_id} if class_id else {}
    return [_enrich_subject(d, db) for d in db["subjects"].find(query)]

@router.put("/subjects/{id}", response_model=SubjectResponse)
def update_subject(id: str, subj: SubjectUpdate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    update_data = {k: v for k, v in subj.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db["subjects"].update_one({"_id": _oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return _enrich_subject(db["subjects"].find_one({"_id": _oid(id)}), db)

@router.delete("/subjects/{id}")
def delete_subject(id: str, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    result = db["subjects"].delete_one({"_id": _oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}

# ── Faculty ───────────────────────────────────────────────────────────────────

@router.post("/faculty", response_model=FacultyResponse)
def create_faculty(fac: FacultyCreate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    doc = {**fac.dict(), "created_at": datetime.utcnow()}
    result = db["faculty"].insert_one(doc)
    return faculty_helper(db["faculty"].find_one({"_id": result.inserted_id}))

@router.get("/faculty", response_model=List[FacultyResponse])
def list_faculty(department_id: Optional[str] = None, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    query = {"department_id": department_id} if department_id else {}
    return [faculty_helper(d) for d in db["faculty"].find(query)]

@router.delete("/faculty/{id}")
def delete_faculty(id: str, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    result = db["faculty"].delete_one({"_id": _oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}

@router.put("/faculty/{id}", response_model=FacultyResponse)
def update_faculty(id: str, fac: FacultyUpdate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    update_data = {k: v for k, v in fac.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db["faculty"].update_one({"_id": _oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return faculty_helper(db["faculty"].find_one({"_id": _oid(id)}))

# ── Rooms ─────────────────────────────────────────────────────────────────────

@router.post("/rooms", response_model=RoomResponse)
def create_room(room: RoomCreate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    doc = {**room.dict(), "created_at": datetime.utcnow()}
    result = db["rooms"].insert_one(doc)
    return room_helper(db["rooms"].find_one({"_id": result.inserted_id}))

@router.get("/rooms", response_model=List[RoomResponse])
def list_rooms(db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    return [room_helper(d) for d in db["rooms"].find()]

@router.delete("/rooms/{id}")
def delete_room(id: str, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    result = db["rooms"].delete_one({"_id": _oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}

@router.put("/rooms/{id}", response_model=RoomResponse)
def update_room(id: str, room: RoomUpdate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    update_data = {k: v for k, v in room.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db["rooms"].update_one({"_id": _oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return room_helper(db["rooms"].find_one({"_id": _oid(id)}))

# ── Timetable Generation ──────────────────────────────────────────────────────

@router.post("/generate", response_model=TimetableResponse)
def generate_timetable(request: TimetableGenerateRequest, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    custom_constraints = []
    if request.constraints_text and settings.GEMINI_API_KEY:
        try:
            parser = AIConstraintParser(api_key=settings.GEMINI_API_KEY)
            custom_constraints = parser.parse_constraints(request.constraints_text)
            print(f"Parsed Constraints: {custom_constraints}")
        except Exception as e:
            print(f"AI Parser Warning: {e}")

    scheduler = TimetableScheduler(db=db, working_days=request.working_days, periods_per_day=request.periods_per_day,
                                   time_limit_seconds=settings.SOLVER_TIME_LIMIT_SECONDS,
                                   custom_constraints=custom_constraints)
    result = scheduler.generate_schedule(department_ids=request.department_ids)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    if result["status"] in ["INFEASIBLE", "MODEL_INVALID"]:
        raise HTTPException(status_code=400, detail=f"Could not find valid timetable. Status: {result['status']}")

    doc = {
        "name": request.name,
        "academic_year": request.academic_year,
        "semester": request.semester,
        "schedule_data": result["schedule"],
        "constraints_used": {
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
            "break2_duration_mins": request.break2_duration_mins,
        },
        "solver_status": result["status"],
        "solve_time_seconds": result["solve_time"],
        "created_at": datetime.utcnow(),
    }
    ins = db["timetables"].insert_one(doc)
    return timetable_helper(db["timetables"].find_one({"_id": ins.inserted_id}))

@router.get("/timetables", response_model=List[TimetableResponse])
def list_timetables(db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    return [timetable_helper(d) for d in db["timetables"].find().sort("created_at", -1)]

@router.get("/timetables/{id}", response_model=TimetableResponse)
def get_timetable(id: str, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    doc = db["timetables"].find_one({"_id": _oid(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return timetable_helper(doc)

@router.delete("/timetables/{id}")
def delete_timetable(id: str, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    result = db["timetables"].delete_one({"_id": _oid(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}
