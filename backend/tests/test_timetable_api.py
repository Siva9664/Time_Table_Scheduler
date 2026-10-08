import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.endpoints.timetable import (
    _build_ai_constraint_context,
    _oid,
    create_batch,
    create_class,
    create_department,
    create_faculty,
    create_room,
    create_subject,
    delete_batch,
    delete_class,
    delete_department,
    delete_faculty,
    delete_room,
    delete_subject,
    list_batches,
    list_classes,
    list_departments,
    list_faculty,
    list_rooms,
    list_subjects,
    map_subject_to_class,
    map_subject_to_faculty,
)
from app.schemas.timetable import (
    BatchCreate,
    ClassCreate,
    DepartmentCreate,
    FacultyCreate,
    RoomCreate,
    SubjectCreate,
    SubjectMapRequest,
)


class FakeCollection:
    def __init__(self, name="collection"):
        self.name = name
        self.docs = []

    def find_one(self, query=None):
        query = query or {}
        for doc in self.docs:
            if self._matches(doc, query):
                return doc
        return None

    def find(self, query=None, projection=None):
        query = query or {}
        results = [doc for doc in self.docs if self._matches(doc, query)]
        if projection:
            projected = []
            for r in results:
                p = {"_id": r["_id"]}
                for k in projection:
                    if k in r:
                        p[k] = r[k]
                projected.append(p)
            return projected
        return results

    def insert_one(self, doc):
        stored = dict(doc)
        if "_id" not in stored:
            stored["_id"] = ObjectId()
        self.docs.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    def update_one(self, query, update):
        doc = self.find_one(query)
        if not doc:
            return SimpleNamespace(matched_count=0, modified_count=0)
        if "$set" in update:
            doc.update(update["$set"])
        return SimpleNamespace(matched_count=1, modified_count=1)

    def update_many(self, query, update):
        matched = [doc for doc in self.docs if self._matches(doc, query)]
        if "$set" in update:
            for doc in matched:
                doc.update(update["$set"])
        return SimpleNamespace(matched_count=len(matched), modified_count=len(matched))

    def delete_one(self, query):
        doc = self.find_one(query)
        if doc and doc in self.docs:
            self.docs.remove(doc)
            return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    def delete_many(self, query):
        to_delete = [doc for doc in self.docs if self._matches(doc, query)]
        for doc in to_delete:
            self.docs.remove(doc)
        return SimpleNamespace(deleted_count=len(to_delete))

    def _matches(self, doc, query):
        if not query:
            return True
        for k, v in query.items():
            if k == "$or":
                if not any(self._matches(doc, cond) for cond in v):
                    return False
                continue
            if isinstance(v, dict) and "$exists" in v:
                exists = k in doc
                if exists != v["$exists"]:
                    return False
                continue
            if doc.get(k) != v:
                return False
        return True


class FakeTenantDB:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = FakeCollection(name)
        return self.collections[name]


class TestTimetableEndpointsAndHelpers:
    def setup_method(self):
        self.db = FakeTenantDB()
        self.admin_user = {"username": "admin", "is_admin": True}
        self.faculty_user = {"username": "prof", "is_admin": False}

    def test_oid_validation(self):
        valid_id = str(ObjectId())
        parsed = _oid(valid_id)
        assert isinstance(parsed, ObjectId)
        assert str(parsed) == valid_id

        with pytest.raises(HTTPException) as exc:
            _oid("not-a-valid-hex-object-id")
        assert exc.value.status_code == 422

    def test_build_ai_constraint_context(self):
        self.db["faculty"].insert_one({"name": "Dr. Shiva"})
        self.db["subjects"].insert_one({"name": "Algorithms", "code": "CS301", "requires_lab": True})
        self.db["classes"].insert_one({"name": "CSE", "section": "A"})

        ctx = _build_ai_constraint_context(self.db, periods_per_day=6)
        assert "Dr. Shiva" in ctx["faculty_names"]
        assert "Algorithms" in ctx["subject_names"]
        assert "Algorithms Lab" in ctx["subject_names"]
        assert "CSE A" in ctx["class_names"]
        assert ctx["periods_per_day"] == 6

    def test_batch_crud(self):
        batch_req = BatchCreate(name="Batch 2026", start_time="09:00", end_time="16:00")
        created = create_batch(batch_req, db=self.db, current_user=self.admin_user)
        assert created["name"] == "Batch 2026"

        all_batches = list_batches(db=self.db, current_user=self.faculty_user)
        assert len(all_batches) == 1

        delete_batch(created["id"], db=self.db, current_user=self.admin_user)
        assert len(list_batches(db=self.db, current_user=self.faculty_user)) == 0

    def test_department_crud(self):
        dept_req = DepartmentCreate(name="Information Technology", code="IT")
        created = create_department(dept_req, db=self.db, current_user=self.admin_user)
        assert created["code"] == "IT"

        all_depts = list_departments(db=self.db, current_user=self.faculty_user)
        assert len(all_depts) == 1

        delete_department(created["id"], db=self.db, current_user=self.admin_user)
        assert len(list_departments(db=self.db, current_user=self.faculty_user)) == 0

    def test_room_crud(self):
        room_req = RoomCreate(name="Auditorium", capacity=250, room_type="seminar")
        created = create_room(room_req, db=self.db, current_user=self.admin_user)
        assert created["capacity"] == 250

        all_rooms = list_rooms(db=self.db, current_user=self.faculty_user)
        assert len(all_rooms) == 1

        delete_room(created["id"], db=self.db, current_user=self.admin_user)
        assert len(list_rooms(db=self.db, current_user=self.faculty_user)) == 0

    def test_subject_crud_and_mapping(self):
        sub_req = SubjectCreate(name="Operating Systems", code="CS302", credits=4)
        created_sub = create_subject(sub_req, db=self.db, current_user=self.admin_user)
        assert created_sub["code"] == "CS302"

        fac_req = FacultyCreate(name="Prof. Linus", email="linus@linux.org")
        created_fac = create_faculty(fac_req, db=self.db, current_user=self.admin_user)

        cls_req = ClassCreate(name="CSE-3A", section="A")
        created_cls = create_class(cls_req, db=self.db, current_user=self.admin_user)

        # Map faculty and class to subject
        map_req = SubjectMapRequest(class_id=created_cls["id"], faculty_id=created_fac["id"])
        mapped = map_subject_to_class(created_sub["id"], map_req, db=self.db, current_user=self.admin_user)
        assert mapped["faculty_id"] == created_fac["id"]
        assert mapped["class_id"] == created_cls["id"]

        # Verify alias map_subject_to_faculty works as well
        mapped_alias = map_subject_to_faculty(created_sub["id"], map_req, db=self.db, current_user=self.admin_user)
        assert mapped_alias["faculty_id"] == created_fac["id"]

        # Delete subject
        delete_subject(created_sub["id"], db=self.db, current_user=self.admin_user)
        assert len(list_subjects(db=self.db, current_user=self.faculty_user)) == 0

