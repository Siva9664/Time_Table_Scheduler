from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class DepartmentBase(BaseModel):
    name: str
    code: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class BatchBase(BaseModel):
    name: str
    start_time: str
    end_time: str
    period_duration: int = 60
    break_times: List[Dict[str, str]] = [] 
    lunch_break: Dict[str, str] = {} 

class BatchCreate(BatchBase):
    pass

class BatchResponse(BatchBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ClassBase(BaseModel):
    name: str
    section: Optional[str] = None
    semester: Optional[int] = None
    student_count: Optional[int] = None
    department_id: Optional[int] = None
    batch_id: Optional[int] = None

class ClassCreate(ClassBase):
    pass

class ClassResponse(ClassBase):
    id: int
    created_at: datetime
    department: Optional[DepartmentResponse] = None
    batch: Optional[BatchResponse] = None
    class Config:
        from_attributes = True

class SubjectBase(BaseModel):
    name: str
    code: str
    hours_per_week: int
    requires_lab: bool = False
    department_id: Optional[int] = None
    batch_id: int
    class_id: Optional[int] = None
    faculty_id: Optional[int] = None

class SubjectCreate(SubjectBase):
    pass

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    hours_per_week: Optional[int] = None
    requires_lab: Optional[bool] = None
    required_lab: Optional[bool] = None
    department_id: Optional[int] = None
    batch_id: Optional[int] = None
    class_id: Optional[int] = None
    faculty_id: Optional[int] = None


class SubjectResponse(SubjectBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class FacultyBase(BaseModel):
    name: str
    email: EmailStr
    department_id: Optional[int] = None
    max_hours_per_week: int = 20
    unavailable_slots: List[Dict[str, Any]] = []

class FacultyCreate(FacultyBase):
    pass

class FacultyResponse(FacultyBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class RoomBase(BaseModel):
    name: str
    room_type: str
    capacity: int
    has_projector: bool = False
    has_computers: bool = False

class RoomCreate(RoomBase):
    pass

class RoomResponse(RoomBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class TimetableGenerateRequest(BaseModel):
    name: str
    academic_year: str
    semester: int
    department_ids: Optional[List[int]] = None
    batch_ids: Optional[List[int]] = None
    class_ids: Optional[List[int]] = None
    faculty_ids: Optional[List[int]] = None
    working_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods_per_day: int = 7
    start_time: str = "09:00"
    end_time: Optional[str] = None
    period_duration_mins: int = 60
    break_after_period: Optional[int] = None
    break_duration_mins: int = 15
    lunch_after_period: Optional[int] = None
    lunch_duration_mins: int = 60
    break2_after_period: Optional[int] = None
    break2_duration_mins: int = 15
    break_times: Optional[List[Dict[str, str]]] = None # Global override if needed, but Batch is preferred
    constraints_text: Optional[str] = None

class TimetableResponse(BaseModel):
    id: int
    name: str
    academic_year: str
    semester: int
    schedule_data: Dict[str, Any]
    constraints_used: Dict[str, Any]
    solver_status: str
    solve_time_seconds: int
    created_at: datetime
    class Config:
        from_attributes = True

