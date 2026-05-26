import unittest
from types import SimpleNamespace

from bson import ObjectId

from app.services.scheduler import TimetableScheduler
from app.services.scheduler import _Obj


class CreditSchedulerPolicyTest(unittest.TestCase):
    def setUp(self):
        self.scheduler = TimetableScheduler(
            db=None,
            working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            periods_per_day=7,
        )

    def test_credit_hours_default_to_credit_mapping(self):
        subject = SimpleNamespace(id="s1", hours_per_week=None, credits=4, requires_lab=False)
        self.assertEqual(4, self.scheduler._effective_hours(subject))

    def test_credit_extra_capacity_is_bounded_for_theory(self):
        self.assertEqual(0, self.scheduler._credit_extra_capacity(SimpleNamespace(credits=2, requires_lab=False)))
        self.assertEqual(1, self.scheduler._credit_extra_capacity(SimpleNamespace(credits=3, requires_lab=False)))
        self.assertEqual(2, self.scheduler._credit_extra_capacity(SimpleNamespace(credits=4, requires_lab=False)))
        self.assertEqual(3, self.scheduler._credit_extra_capacity(SimpleNamespace(credits=6, requires_lab=False)))

    def test_labs_do_not_receive_credit_extra_capacity(self):
        subject = SimpleNamespace(credits=5, requires_lab=True)
        self.assertEqual(0, self.scheduler._credit_extra_capacity(subject))

    def test_free_capacity_is_allocated_to_high_credit_subjects_first(self):
        class_obj = SimpleNamespace(id="c1")
        low_credit = SimpleNamespace(id="s_low", class_id="c1", name="Low", code="L", credits=2, hours_per_week=2, requires_lab=False)
        high_credit = SimpleNamespace(id="s_high", class_id="c1", name="High", code="H", credits=5, hours_per_week=2, requires_lab=False)

        self.scheduler.classes = [class_obj]
        self.scheduler.subjects = [low_credit, high_credit]
        self.scheduler.num_days = 1
        self.scheduler.periods_per_day = 6
        self.scheduler.vars_by_subject = {
            "s_low": [object() for _ in range(6)],
            "s_high": [object() for _ in range(6)],
        }
        self.scheduler.variables = {
            f"s{sub.id}_d0_p{period}": object()
            for sub in [low_credit, high_credit]
            for period in range(6)
        }

        capacities = self.scheduler._compute_credit_extra_capacities()

        self.assertEqual(2, capacities["s_high"])
        self.assertNotIn("s_low", capacities)

    def test_solver_fills_free_slot_with_high_credit_subject(self):
        class_id = str(ObjectId())
        high_faculty_id = str(ObjectId())
        low_faculty_id = str(ObjectId())

        high = _Obj({
            "_id": ObjectId(),
            "name": "High Priority",
            "code": "HIGH",
            "class_id": class_id,
            "faculty_id": high_faculty_id,
            "hours_per_week": 1,
            "credits": 5,
            "requires_lab": False,
        })
        low = _Obj({
            "_id": ObjectId(),
            "name": "Low Priority",
            "code": "LOW",
            "class_id": class_id,
            "faculty_id": low_faculty_id,
            "hours_per_week": 1,
            "credits": 2,
            "requires_lab": False,
        })

        scheduler = TimetableScheduler(
            db=None,
            working_days=["Monday"],
            periods_per_day=3,
            time_limit_seconds=5,
        )
        cls = _Obj({"_id": ObjectId(class_id), "name": "AIML", "section": "A", "_batch_obj": None})
        scheduler.classes = [cls]
        scheduler.class_map = {class_id: cls}
        scheduler.subjects = [high, low]
        scheduler.faculty = [
            _Obj({"_id": ObjectId(high_faculty_id), "name": "High Staff", "unavailable_slots": []}),
            _Obj({"_id": ObjectId(low_faculty_id), "name": "Low Staff", "unavailable_slots": []}),
        ]

        scheduler.create_variables()
        scheduler.add_constraints()
        result = scheduler.solve()

        self.assertIn(result["status"], {"OPTIMAL", "FEASIBLE"})
        slots = result["schedule"][f"class_{class_id}"]["timetable"]["Monday"]
        subjects = [slot.get("subject") for slot in slots if slot.get("slot_type") == "period"]
        high_count = subjects.count("High Priority")
        low_count = subjects.count("Low Priority")

        self.assertEqual(2, high_count)
        self.assertEqual(1, low_count)
        self.assertNotIn(None, subjects)


if __name__ == "__main__":
    unittest.main()
