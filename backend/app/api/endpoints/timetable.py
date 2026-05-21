from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from bson import ObjectId
from typing import List, Optional
from datetime import datetime
from ...database.database import get_db
from ...models.timetable import (
    department_helper, batch_helper, class_helper,
    subject_helper, faculty_helper, timetable_helper
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
    if doc.get("department_ids") and not doc.get("department_id"):
        doc["department_id"] = doc["department_ids"][0]
    if doc.get("department_id") and not doc.get("department_ids"):
        doc["department_ids"] = [doc["department_id"]]
    result = db["subjects"].insert_one(doc)
    return _enrich_subject(db["subjects"].find_one({"_id": result.inserted_id}), db)

@router.get("/subjects", response_model=List[SubjectResponse])
def list_subjects(class_id: Optional[str] = None, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    query = {"class_id": class_id} if class_id else {}
    return [_enrich_subject(d, db) for d in db["subjects"].find(query)]

@router.put("/subjects/{id}", response_model=SubjectResponse)
def update_subject(id: str, subj: SubjectUpdate, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    update_data = {k: v for k, v in subj.dict(exclude_unset=True).items()}
    if update_data.get("department_ids") and not update_data.get("department_id"):
        department_ids = update_data["department_ids"]
        update_data["department_id"] = department_ids[0] if department_ids else None
    if update_data.get("department_id") and not update_data.get("department_ids"):
        update_data["department_ids"] = [update_data["department_id"]]
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
    # Defensive validation: ensure types and shapes to avoid downstream constraint/parser errors
    payload = fac.dict()
    try:
        # max_hours_per_week must be an int >= 0
        max_h = int(payload.get("max_hours_per_week", 0))
        if max_h < 0:
            raise ValueError("max_hours_per_week must be non-negative")
        payload["max_hours_per_week"] = max_h

        # unavailable_slots must be a list of dicts (optional)
        us = payload.get("unavailable_slots", []) or []
        if not isinstance(us, list):
            raise ValueError("unavailable_slots must be a list")
        # shallow validation of each slot
        for s in us:
            if not isinstance(s, dict):
                raise ValueError("each unavailable slot must be an object")
            # optional keys: day, start, end
            # ensure start/end are strings if present
            for k in ("start", "end"):
                if k in s and s[k] is not None and not isinstance(s[k], str):
                    raise ValueError(f"unavailable_slots.{k} must be a string in HH:MM form")

        payload["unavailable_slots"] = us
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid faculty data: {e}")

    doc = {**payload, "created_at": datetime.utcnow()}
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

    # Validate updated fields similarly to create
    if "max_hours_per_week" in update_data:
        try:
            mh = int(update_data["max_hours_per_week"]) if update_data["max_hours_per_week"] is not None else None
            if mh is not None and mh < 0:
                raise ValueError("max_hours_per_week must be non-negative")
            update_data["max_hours_per_week"] = mh
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid max_hours_per_week: {e}")

    if "unavailable_slots" in update_data:
        us = update_data["unavailable_slots"] or []
        if not isinstance(us, list):
            raise HTTPException(status_code=400, detail="unavailable_slots must be a list")
        for s in us:
            if not isinstance(s, dict):
                raise HTTPException(status_code=400, detail="each unavailable slot must be an object")
            for k in ("start", "end"):
                if k in s and s[k] is not None and not isinstance(s[k], str):
                    raise HTTPException(status_code=400, detail=f"unavailable_slots.{k} must be a string")

    result = db["faculty"].update_one({"_id": _oid(id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return faculty_helper(db["faculty"].find_one({"_id": _oid(id)}))


# ── Timetable Generation ──────────────────────────────────────────────────────

@router.post("/generate", response_model=TimetableResponse)
def generate_timetable(request: TimetableGenerateRequest, db: Database = Depends(get_tenant_db), current_user: dict = Depends(get_admin_user)):
    custom_constraints = []
    parse_diagnostics = {"corrections": [], "warnings": [], "unrecognized": []}
    if request.constraints_text:
        try:
            # ── Build context from live DB data so AI can match real names ──
            faculty_docs  = list(db["faculty"].find({}, {"name": 1}))
            subject_docs  = list(db["subjects"].find({}, {"name": 1}))
            class_docs    = list(db["classes"].find({}, {"name": 1, "section": 1}))

            context = {
                "faculty_names": [d["name"] for d in faculty_docs  if d.get("name")],
                "subject_names": [d["name"] for d in subject_docs  if d.get("name")],
                "class_names":   [
                    f"{d.get('name', '')} {d.get('section', '')}".strip()
                    for d in class_docs if d.get("name")
                ],
                "periods_per_day": request.periods_per_day,
            }

            parser = AIConstraintParser(
                model=settings.AI_MODEL,
                timeout_seconds=settings.OPENAI_TIMEOUT_SECONDS,
                api_key=settings.OPENAI_API_KEY,
                api_base=settings.OPENAI_API_BASE,
                context=context,
            )
            parse_result = parser.parse_constraints_with_diagnostics(request.constraints_text)
            custom_constraints = parse_result["constraints"]
            parse_diagnostics = {
                "corrections":   parse_result.get("corrections",   []),
                "warnings":      parse_result.get("warnings",      []),
                "unrecognized":  parse_result.get("unrecognized",  []),
            }
            if custom_constraints:
                print(f"Parsed {len(custom_constraints)} constraints: {custom_constraints}")
            else:
                print("Warning: no constraints parsed — proceeding without custom constraints")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"AI constraint parsing failed: {e}")

    scheduler = TimetableScheduler(db=db, working_days=request.working_days, periods_per_day=request.periods_per_day,
                                   time_limit_seconds=settings.SOLVER_TIME_LIMIT_SECONDS,
                                   custom_constraints=custom_constraints)
    result = scheduler.generate_schedule(
        department_ids=request.department_ids,
        batch_ids=request.batch_ids,
        class_ids=request.class_ids,
        faculty_ids=request.faculty_ids,
    )
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
            "periods_per_day": result.get("effective_periods_per_day", request.periods_per_day),
            "requested_periods_per_day": request.periods_per_day,
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
            "constraints_text": request.constraints_text,
            "custom_constraints": custom_constraints,
            "parse_diagnostics": parse_diagnostics,
            "auto_adjustments": result.get("auto_adjustments", []),
            "constraint_warnings": result.get("constraint_warnings", []),
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
