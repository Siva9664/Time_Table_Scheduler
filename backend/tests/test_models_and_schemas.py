import sys
from datetime import datetime
from pathlib import Path

import pytest
from bson import ObjectId
from pydantic import ValidationError

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.timetable import (
    batch_helper,
    class_helper,
    department_helper,
    faculty_helper,
    room_helper,
    subject_helper,
    timetable_helper,
)
from app.models.user import user_helper
from app.schemas.timetable import (
    BatchCreate,
    ClassCreate,
    DepartmentCreate,
    FacultyCreate,
    RoomCreate,
    SubjectCreate,
    TimetableGenerateRequest,
)
from app.schemas.user import UserCreate, UserResponse


class TestUserModelsAndSchemas:
    def test_user_helper_serialization(self):
        oid = ObjectId()
        doc = {
            "_id": oid,
            "username": "prof_shiva",
            "email": "shiva@college.edu",
            "role": "faculty",
            "is_admin": False,
            "is_active": True,
            "tenant_db_name": "timetable_db_cse",
            "created_at": datetime.utcnow(),
        }
        res = user_helper(doc)
        assert res["id"] == str(oid)
        assert res["username"] == "prof_shiva"
        assert res["email"] == "shiva@college.edu"
        assert res["role"] == "faculty"

    def test_user_create_validation(self):
        valid = UserCreate(
            username="new_user",
            email="valid@college.edu",
            password="securePassword123",
        )
        assert valid.email == "valid@college.edu"

        # Invalid email validation
        with pytest.raises(ValidationError):
            UserCreate(
                username="invalid_user",
                email="not-an-email",
                password="pass",
            )


class TestTimetableModelsAndSchemas:
    def test_department_schemas_and_helper(self):
        oid = ObjectId()
        doc = {"_id": oid, "name": "Computer Science", "code": "CSE", "created_at": datetime.utcnow()}
        res = department_helper(doc)
        assert res["id"] == str(oid)
        assert res["code"] == "CSE"

        valid = DepartmentCreate(name="Mechanical Engineering", code="MECH")
        assert valid.code == "MECH"

    def test_batch_schemas_and_helper(self):
        oid = ObjectId()
        doc = {
            "_id": oid,
            "name": "2024-2028 Batch",
            "start_time": "09:00",
            "end_time": "16:00",
            "period_duration": 50,
            "break_times": [{"start": "11:00", "end": "11:15"}],
            "lunch_break": {"start": "13:00", "end": "14:00"},
            "created_at": datetime.utcnow(),
        }
        res = batch_helper(doc)
        assert res["id"] == str(oid)
        assert res["period_duration"] == 50

        batch = BatchCreate(
            name="Morning Shift",
            start_time="08:30",
            end_time="15:30",
        )
        assert batch.period_duration == 60  # Default 60 mins

    def test_room_schemas_and_helper(self):
        oid = ObjectId()
        doc = {"_id": oid, "name": "Lab 101", "capacity": 60, "room_type": "lab"}
        res = room_helper(doc)
        assert res["id"] == str(oid)
        assert res["room_type"] == "lab"

        room = RoomCreate(name="LH-1", capacity=100)
        assert room.room_type == "lecture"

    def test_subject_schemas_and_helper(self):
        oid = ObjectId()
        doc = {
            "_id": oid,
            "name": "Data Structures",
            "code": "CS201",
            "credits": 4,
            "requires_lab": False,
        }
        res = subject_helper(doc)
        assert res["id"] == str(oid)
        assert res["code"] == "CS201"

    def test_faculty_schemas_and_helper(self):
        oid = ObjectId()
        doc = {
            "_id": oid,
            "name": "Dr. Alan Turing",
            "email": "turing@cs.edu",
            "designation": "Professor",
        }
        res = faculty_helper(doc)
        assert res["id"] == str(oid)
        assert res["name"] == "Dr. Alan Turing"

    def test_timetable_generate_request(self):
        req = TimetableGenerateRequest(
            name="Fall 2026 Timetable",
            academic_year="2026-2027",
            semester=1,
            working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            periods_per_day=7,
        )
        assert len(req.working_days) == 5
        assert req.periods_per_day == 7
        assert req.name == "Fall 2026 Timetable"
