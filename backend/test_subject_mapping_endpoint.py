import unittest
from copy import deepcopy
from types import SimpleNamespace

from bson import ObjectId

from app.api.endpoints.timetable import map_subject_to_class
from app.schemas.timetable import SubjectMapRequest


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [deepcopy(doc) for doc in docs or []]

    def find_one(self, query):
        for doc in self.docs:
            if self._matches(doc, query):
                return deepcopy(doc)
        return None

    def insert_one(self, doc):
        stored = deepcopy(doc)
        stored.setdefault("_id", ObjectId())
        self.docs.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    def update_one(self, query, update):
        for doc in self.docs:
            if self._matches(doc, query):
                doc.update(update.get("$set", {}))
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)

    def _matches(self, doc, query):
        for key, value in query.items():
            if key == "$or":
                if not any(self._matches(doc, branch) for branch in value):
                    return False
                continue
            if isinstance(value, dict) and "$exists" in value:
                exists = key in doc
                if exists != value["$exists"]:
                    return False
                continue
            if doc.get(key) != value:
                return False
        return True


class FakeDB(dict):
    def __getitem__(self, name):
        return super().__getitem__(name)


class SubjectMappingEndpointTest(unittest.TestCase):
    def setUp(self):
        self.dept_id = str(ObjectId())
        self.batch_id = str(ObjectId())
        self.subject_id = ObjectId()
        self.class_a_id = ObjectId()
        self.class_b_id = ObjectId()
        self.faculty_a_id = ObjectId()
        self.faculty_b_id = ObjectId()
        self.faculty_c_id = ObjectId()
        self.cn_lab_id = ObjectId()

        self.db = FakeDB({
            "subjects": FakeCollection([
                {
                    "_id": self.subject_id,
                    "name": "CN",
                    "code": "21CS424",
                    "hours_per_week": 4,
                    "credits": 4,
                    "requires_lab": False,
                    "department_id": self.dept_id,
                    "department_ids": [self.dept_id],
                    "batch_id": self.batch_id,
                    "class_id": None,
                    "faculty_id": None,
                },
                {
                    "_id": self.cn_lab_id,
                    "name": "CN Lab",
                    "code": "21CS424",
                    "hours_per_week": 2,
                    "credits": 1,
                    "requires_lab": True,
                    "department_id": self.dept_id,
                    "department_ids": [self.dept_id],
                    "batch_id": self.batch_id,
                    "class_id": None,
                    "faculty_id": None,
                },
            ]),
            "classes": FakeCollection([
                {"_id": self.class_a_id, "name": "CSE", "section": "A", "department_id": self.dept_id, "batch_id": self.batch_id},
                {"_id": self.class_b_id, "name": "CSE", "section": "B", "department_id": self.dept_id, "batch_id": self.batch_id},
            ]),
            "faculty": FakeCollection([
                {"_id": self.faculty_a_id, "name": "Staff A", "email": "a@example.com", "department_id": self.dept_id},
                {"_id": self.faculty_b_id, "name": "Staff B", "email": "b@example.com", "department_id": self.dept_id},
                {"_id": self.faculty_c_id, "name": "Staff C", "email": "c@example.com", "department_id": self.dept_id},
            ]),
            "departments": FakeCollection([{"_id": ObjectId(self.dept_id), "name": "Computer Science", "code": "CSE"}]),
            "batches": FakeCollection([{"_id": ObjectId(self.batch_id), "name": "2024-2028", "start_time": "09:00", "end_time": "16:00"}]),
        })

    def test_same_subject_maps_to_separate_rows_for_each_class(self):
        map_subject_to_class(
            str(self.subject_id),
            SubjectMapRequest(class_id=str(self.class_a_id), faculty_id=str(self.faculty_a_id)),
            self.db,
            {"role": "admin"},
        )
        map_subject_to_class(
            str(self.subject_id),
            SubjectMapRequest(class_id=str(self.class_b_id), faculty_id=str(self.faculty_b_id)),
            self.db,
            {"role": "admin"},
        )

        mapped = [doc for doc in self.db["subjects"].docs if doc.get("source_subject_id") == str(self.subject_id)]
        self.assertEqual(2, len(mapped))
        self.assertEqual(
            {str(self.class_a_id), str(self.class_b_id)},
            {doc["class_id"] for doc in mapped},
        )
        self.assertEqual(
            {str(self.faculty_a_id), str(self.faculty_b_id)},
            {doc["faculty_id"] for doc in mapped},
        )

    def test_remapping_same_class_updates_existing_row(self):
        map_subject_to_class(
            str(self.subject_id),
            SubjectMapRequest(class_id=str(self.class_a_id), faculty_id=str(self.faculty_a_id)),
            self.db,
            {"role": "admin"},
        )
        map_subject_to_class(
            str(self.subject_id),
            SubjectMapRequest(class_id=str(self.class_a_id), faculty_id=str(self.faculty_c_id)),
            self.db,
            {"role": "admin"},
        )

        mapped = [
            doc for doc in self.db["subjects"].docs
            if doc.get("source_subject_id") == str(self.subject_id) and doc.get("class_id") == str(self.class_a_id)
        ]
        self.assertEqual(1, len(mapped))
        self.assertEqual(str(self.faculty_c_id), mapped[0]["faculty_id"])

    def test_subject_already_mapped_to_one_class_can_template_another_class(self):
        mapped_subject = map_subject_to_class(
            str(self.subject_id),
            SubjectMapRequest(class_id=str(self.class_b_id), faculty_id=str(self.faculty_b_id)),
            self.db,
            {"role": "admin"},
        )

        map_subject_to_class(
            mapped_subject["id"],
            SubjectMapRequest(class_id=str(self.class_a_id), faculty_id=str(self.faculty_a_id)),
            self.db,
            {"role": "admin"},
        )

        mapped = [doc for doc in self.db["subjects"].docs if doc.get("source_subject_id") == str(self.subject_id)]
        self.assertEqual(2, len(mapped))
        self.assertEqual(
            {str(self.class_a_id), str(self.class_b_id)},
            {doc["class_id"] for doc in mapped},
        )

    def test_same_code_theory_and_lab_map_as_separate_subjects(self):
        map_subject_to_class(
            str(self.subject_id),
            SubjectMapRequest(class_id=str(self.class_a_id), faculty_id=str(self.faculty_a_id)),
            self.db,
            {"role": "admin"},
        )
        map_subject_to_class(
            str(self.cn_lab_id),
            SubjectMapRequest(class_id=str(self.class_a_id), faculty_id=str(self.faculty_b_id)),
            self.db,
            {"role": "admin"},
        )

        mapped = [doc for doc in self.db["subjects"].docs if doc.get("class_id") == str(self.class_a_id)]
        self.assertEqual(2, len(mapped))
        self.assertEqual({"CN", "CN Lab"}, {doc["name"] for doc in mapped})
        self.assertEqual({False, True}, {doc["requires_lab"] for doc in mapped})


if __name__ == "__main__":
    unittest.main()
