import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
import pytest
from bson import ObjectId
from fastapi import HTTPException, Request

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.endpoints.auth import (
    FacultyCreateRequest,
    LoginRequest,
    RegisterRequest,
    create_access_token,
    create_faculty_account,
    delete_faculty_account,
    get_me,
    hash_password,
    list_faculty_accounts,
    login_user,
    register_user,
    verify_password,
)
from app.core.config import settings
from app.core.security import get_admin_user, get_current_user, get_tenant_db


class FakeCollection:
    def __init__(self, name="collection"):
        self.name = name
        self.docs = []
        self.counter = 1

    def find_one(self, query=None):
        query = query or {}
        for doc in self.docs:
            if self._matches(doc, query):
                return doc
        return None

    def find(self, query=None):
        query = query or {}
        return [doc for doc in self.docs if self._matches(doc, query)]

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

    def delete_one(self, query):
        doc = self.find_one(query)
        if doc and doc in self.docs:
            self.docs.remove(doc)
            return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    def _matches(self, doc, query):
        if "$or" in query:
            return any(self._matches(doc, sub) for sub in query["$or"])
        for k, v in query.items():
            if k == "$or":
                continue
            if doc.get(k) != v:
                return False
        return True


class FakeDB:
    def __init__(self):
        self.collections = {
            "users": FakeCollection("users"),
        }

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = FakeCollection(name)
        return self.collections[name]


class TestPasswordAndTokenSecurity:
    def test_password_hashing_and_verification(self):
        password = "SecurePassword@2026"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword123", hashed) is False

    def test_jwt_token_generation_and_payload(self):
        data = {"sub": "test_user", "role": "admin", "tenant_db_name": "timetable_db_test"}
        token = create_access_token(data, expires_delta=timedelta(minutes=15))

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == "test_user"
        assert decoded["role"] == "admin"
        assert decoded["tenant_db_name"] == "timetable_db_test"
        assert "exp" in decoded


class TestAuthEndpoints:
    def setUp(self):
        self.db = FakeDB()

    def test_register_new_admin_user_success(self):
        db = FakeDB()
        req = RegisterRequest(
            username="admin_hod",
            email="hod@college.edu",
            password="admin_secret_pass",
            full_name="Head of Dept",
            role="admin",
        )
        res = register_user(req, db=db)
        assert res["username"] == "admin_hod"
        assert res["email"] == "hod@college.edu"
        assert res["is_admin"] is True
        assert "timetable_db_admin_hod" in res["tenant_db_name"]

        # Verify password got hashed in storage
        user_in_db = db["users"].find_one({"username": "admin_hod"})
        assert user_in_db is not None
        assert user_in_db["hashed_password"] != "admin_secret_pass"
        assert verify_password("admin_secret_pass", user_in_db["hashed_password"])

    def test_register_duplicate_username_fails(self):
        db = FakeDB()
        req = RegisterRequest(
            username="prof_john",
            email="john@college.edu",
            password="pass1",
            role="faculty",
        )
        register_user(req, db=db)

        duplicate_req = RegisterRequest(
            username="prof_john",
            email="other@college.edu",
            password="pass2",
            role="faculty",
        )
        with pytest.raises(HTTPException) as exc:
            register_user(duplicate_req, db=db)
        assert exc.value.status_code == 400
        assert "already registered" in exc.value.detail

    def test_login_successful_and_invalid(self):
        db = FakeDB()
        # Seed user
        hashed = hash_password("mypassword")
        db["users"].insert_one({
            "username": "shiva",
            "email": "shiva@college.edu",
            "hashed_password": hashed,
            "role": "admin",
            "tenant_db_name": "timetable_db_shiva",
        })

        # Successful login
        req = LoginRequest(username="shiva", password="mypassword")
        dummy_request = Request({
            "type": "http",
            "method": "POST",
            "path": "/api/auth/login",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        })
        response = login_user(request=dummy_request, login_data=req, db=db)
        assert "access_token" in response
        assert response["token_type"] == "bearer"

        # Invalid password
        bad_req = LoginRequest(username="shiva", password="wrongpassword")
        with pytest.raises(HTTPException) as exc:
            login_user(request=dummy_request, login_data=bad_req, db=db)
        assert exc.value.status_code == 401

    def test_get_me_profile(self):
        current_user = {
            "_id": ObjectId(),
            "username": "dr_smith",
            "email": "smith@college.edu",
            "role": "faculty",
            "is_admin": False,
            "is_active": True,
            "tenant_db_name": "timetable_db_main",
            "created_at": datetime.utcnow(),
        }
        res = get_me(current_user=current_user)
        assert res["username"] == "dr_smith"
        assert res["email"] == "smith@college.edu"


class TestFacultyManagementEndpoints:
    def test_create_and_list_faculty_accounts(self):
        db = FakeDB()
        admin_user = {
            "_id": ObjectId(),
            "username": "admin1",
            "role": "admin",
            "is_admin": True,
            "tenant_db_name": "timetable_db_admin1",
        }

        faculty_req = FacultyCreateRequest(
            username="faculty_rao",
            full_name="Prof. Rao",
            email="rao@college.edu",
            password="raoPassword1",
        )
        res = create_faculty_account(faculty_req, db=db, current_user=admin_user)
        assert res["username"] == "faculty_rao"
        assert res["role"] == "faculty"

        # List faculty for this tenant
        faculty_list = list_faculty_accounts(db=db, current_user=admin_user)
        assert len(faculty_list) == 1
        assert faculty_list[0]["username"] == "faculty_rao"

        # Delete faculty
        del_res = delete_faculty_account(res["id"], db=db, current_user=admin_user)
        assert "revoked successfully" in del_res["message"]
        assert len(list_faculty_accounts(db=db, current_user=admin_user)) == 0


class TestSecurityDependencies:
    @pytest.mark.asyncio
    async def test_get_admin_user_rejection(self):
        non_admin = {"username": "student", "is_admin": False}
        with pytest.raises(HTTPException) as exc:
            await get_admin_user(current_user=non_admin)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_admin_user_allowed(self):
        admin = {"username": "principal", "is_admin": True}
        res = await get_admin_user(current_user=admin)
        assert res["username"] == "principal"

    @pytest.mark.asyncio
    async def test_mock_admin_token(self):
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Bearer mock-admin-token-12345"
        db = FakeDB()
        user = await get_current_user(request=mock_request, db=db)
        assert user["username"] == "admin"
        assert user["is_admin"] is True
