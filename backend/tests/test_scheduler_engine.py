import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.scheduler import CREDITS_TO_HOURS, TimetableScheduler, _Obj


class TestSchedulerHelpersAndStructures:
    def test_credits_to_hours_mapping(self):
        assert CREDITS_TO_HOURS[1] == 1
        assert CREDITS_TO_HOURS[3] == 3
        assert CREDITS_TO_HOURS[4] == 4

    def test_obj_wrapper_access(self):
        oid = ObjectId()
        doc = {"_id": oid, "name": "Computer Networks", "code": "CS401", "credits": 3}
        obj = _Obj(doc)

        assert obj.id == str(oid)
        assert obj.name == "Computer Networks"
        assert obj.code == "CS401"
        assert obj.credits == 3
        assert "Computer Networks" in repr(obj)

        with pytest.raises(AttributeError):
            _ = obj._nonexistent


class TestTimetableSchedulerEngine:
    def test_scheduler_initialization(self):
        mock_db = MagicMock()
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        custom_constraints = [
            {"type": "consecutive_periods", "subject_type": "lab"},
            {"type": "faculty_unavailability", "faculty_name": "Dr. Alan", "unavailable_days": ["Monday"]},
        ]

        scheduler = TimetableScheduler(
            db=mock_db,
            working_days=days,
            periods_per_day=6,
            time_limit_seconds=15,
            custom_constraints=custom_constraints,
        )

        assert scheduler.num_days == 5
        assert scheduler.periods_per_day == 6
        assert scheduler.time_limit_seconds == 15
        assert len(scheduler.custom_constraints) == 2
        assert scheduler.model is not None

    def test_scheduler_wrap_helpers(self):
        mock_db = MagicMock()
        scheduler = TimetableScheduler(
            db=mock_db,
            working_days=["Mon", "Tue"],
            periods_per_day=4,
        )

        oid = ObjectId()
        doc = {"_id": oid, "name": "Algorithms"}
        wrapped = scheduler._wrap(doc)
        assert isinstance(wrapped, _Obj)
        assert wrapped.id == str(oid)
        assert scheduler._id_str(oid) == str(oid)
        assert scheduler._id_str(None) == ""

    def test_load_data_with_empty_tenant(self):
        mock_db = MagicMock()
        # Mock empty database queries
        mock_db["departments"].find.return_value = []
        mock_db["batches"].find.return_value = []
        mock_db["classes"].find.return_value = []
        mock_db["subjects"].find.return_value = []
        mock_db["faculty"].find.return_value = []
        mock_db["rooms"].find.return_value = []

        scheduler = TimetableScheduler(
            db=mock_db,
            working_days=["Monday", "Tuesday"],
            periods_per_day=4,
        )
        scheduler.load_data()

        assert len(scheduler.departments) == 0
        assert len(scheduler.classes) == 0
        assert len(scheduler.subjects) == 0
