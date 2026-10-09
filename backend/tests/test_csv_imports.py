import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.endpoints.imports import (IMPORT_ORDER, _guess_import_type,
                                       _import_csv_data, map_headers)


class FakeCollection:
    def __init__(self, name):
        self.name = name
        self.docs = []
        self.next_id = 1

    def insert_one(self, document):
        doc = dict(document)
        doc.setdefault("_id", f"{self.name}_{self.next_id}")
        self.next_id += 1
        self.docs.append(doc)
        return SimpleNamespace(inserted_id=doc["_id"])

    def find_one(self, query):
        for doc in self.docs:
            if self._matches(doc, query):
                return doc
        return None

    def find(self, query=None):
        query = query or {}
        return [doc for doc in self.docs if self._matches(doc, query)]

    def update_one(self, query, update):
        doc = self.find_one(query)
        if not doc:
            return SimpleNamespace(matched_count=0, modified_count=0)
        if "$set" in update:
            doc.update(update["$set"])
        return SimpleNamespace(matched_count=1, modified_count=1)

    def _matches(self, doc, query):
        for key, expected in (query or {}).items():
            if key == "$or":
                if not any(self._matches(doc, branch) for branch in expected):
                    return False
                continue

            if isinstance(expected, dict):
                if "$exists" in expected:
                    if (key in doc) != expected["$exists"]:
                        return False
                    continue
                if "$in" in expected:
                    if doc.get(key) not in expected["$in"]:
                        return False
                    continue

            if expected is None:
                if doc.get(key) is not None:
                    return False
            elif doc.get(key) != expected:
                return False
        return True


class FakeDB:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = FakeCollection(name)
        return self.collections[name]


class CsvImportTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.template_dir = BACKEND_DIR / "csv_templates"

    def import_template(self, import_type):
        filename = f"{import_type}_template.csv"
        if import_type == "faculty":
            filename = "faculty_template.csv"
        result = _import_csv_data(
            import_type, (self.template_dir / filename).read_bytes(), self.db
        )
        self.assertEqual(result["error_count"], 0, result)
        self.assertEqual(result["warning_count"], 0, result)
        return result

    def test_templates_import_cleanly_and_are_idempotent(self):
        for import_type in IMPORT_ORDER:
            self.import_template(import_type)

        collection_counts = {
            name: len(collection.docs)
            for name, collection in self.db.collections.items()
        }
        self.assertEqual(collection_counts["departments"], 5)
        self.assertEqual(collection_counts["batches"], 2)
        self.assertEqual(collection_counts["rooms"], 4)
        self.assertEqual(collection_counts["classes"], 3)
        self.assertEqual(collection_counts["faculty"], 3)
        self.assertEqual(collection_counts["subjects"], 6)

        batch_a = self.db["batches"].find_one({"name": "Batch A"})
        self.assertEqual(batch_a["break_times"], [{"start": "11:00", "end": "11:15"}])
        self.assertEqual(batch_a["lunch_break"], {"start": "13:00", "end": "14:00"})

        class_a = self.db["classes"].find_one(
            {"name": "B.Tech 1st Year", "section": "A"}
        )
        class_b = self.db["classes"].find_one(
            {"name": "B.Tech 1st Year", "section": "B"}
        )
        class_it = self.db["classes"].find_one(
            {"name": "B.Tech 3rd Year", "section": "A"}
        )
        self.assertEqual(
            class_a["room_id"], self.db["rooms"].find_one({"code": "R101"})["_id"]
        )
        self.assertEqual(
            class_b["room_id"], self.db["rooms"].find_one({"code": "R102"})["_id"]
        )
        self.assertEqual(
            class_it["room_id"], self.db["rooms"].find_one({"code": "R301"})["_id"]
        )

        for import_type in IMPORT_ORDER:
            result = self.import_template(import_type)
            self.assertEqual(result["inserted"], 0, result)

        self.assertEqual(
            collection_counts,
            {
                name: len(collection.docs)
                for name, collection in self.db.collections.items()
            },
        )

    def test_bad_rows_return_diagnostics_without_blocking_valid_rows(self):
        _import_csv_data("departments", b"name,code\nComputer Science,CS\n", self.db)

        result = _import_csv_data(
            "rooms",
            b"name,code,room_type,capacity,department_code\n,EMPTY,lecture,10,CS\nRoom Bad,RB,lecture,abc,CS\n",
            self.db,
        )

        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(result["warning_count"], 1)
        self.assertEqual(self.db["rooms"].find_one({"code": "RB"})["capacity"], 0)

    def test_header_mapping_does_not_reuse_one_column_for_optional_fields(self):
        mapping = map_headers(["code", "class", "email"], "mappings")
        self.assertEqual(mapping["subject_code"], "code")
        self.assertEqual(mapping["class_name"], "class")
        self.assertEqual(mapping["faculty_email"], "email")
        self.assertNotIn("room_code", mapping)

    def test_header_mapping_maps_generic_code_to_department_code_for_classes_and_faculty(self):
        mapping_classes = map_headers(['name', 'section', 'semester', 'student_count', 'code', 'batch_name', 'room_code'], 'classes')
        self.assertEqual(mapping_classes['department_code'], 'code')

        mapping_faculty = map_headers(['name', 'email', 'code', 'max_hours_per_week', 'unavailable_slots'], 'faculty')
        self.assertEqual(mapping_faculty['department_code'], 'code')

    def test_sanitize_and_filter_extracted_entities_strips_mock_data_and_boilerplate(self):
        from app.api.endpoints.imports import _sanitize_and_filter_extracted_entities

        raw_extractions = {
            "departments": [
                {"name": "Computer Science & Engineering", "code": "CSE"},
                {"name": "General Rules & Guidelines", "code": ""},  # boilerplate
                {"name": "", "code": ""}  # empty
            ],
            "faculty": [
                {"name": "Dr. Alan Turing", "email": "alan.turing@example.com"},
                {"name": "Prof. Ada Lovelace", "email": ""},  # no email (should stay empty, not mock)
                {"name": "Dr. John Doe", "email": "johndoe@institution.edu"},  # mock domain -> stripped to empty
                {"name": "Principal", "email": ""},  # signatory/boilerplate role -> dropped
                {"name": "Controller of Examinations", "email": ""},  # signatory -> dropped
            ],
            "subjects": [
                {"name": "Algorithms", "code": "CS201", "hours_per_week": "4", "requires_lab": "false"},
                {"name": "Instructions to candidates", "code": ""},  # boilerplate -> dropped
            ],
            "batches": [
                {"name": "Morning Batch", "start_time": "09:00", "end_time": "16:00", "period_duration": "50"},
                {"name": "", "start_time": ""}
            ],
            "mappings": [
                {"subject_code": "CS201", "class_name": "CSE-A", "faculty_email": "Prof. Ada Lovelace"}
            ]
        }

        cleaned = _sanitize_and_filter_extracted_entities(raw_extractions)

        # Departments
        self.assertEqual(len(cleaned["departments"]), 1)
        self.assertEqual(cleaned["departments"][0]["code"], "CSE")

        # Faculty: no fake @institution.edu, signatories dropped
        self.assertEqual(len(cleaned["faculty"]), 3)
        names = [f["name"] for f in cleaned["faculty"]]
        self.assertIn("Dr. Alan Turing", names)
        self.assertIn("Prof. Ada Lovelace", names)
        self.assertIn("Dr. John Doe", names)
        self.assertNotIn("Principal", names)
        self.assertNotIn("Controller of Examinations", names)

        # Ada Lovelace email must be empty string, NOT mock data
        ada = next(f for f in cleaned["faculty"] if f["name"] == "Prof. Ada Lovelace")
        self.assertEqual(ada["email"], "")

        # John Doe mock email must be stripped to empty string
        john = next(f for f in cleaned["faculty"] if f["name"] == "Dr. John Doe")
        self.assertEqual(john["email"], "")

        # Subjects
        self.assertEqual(len(cleaned["subjects"]), 1)
        self.assertEqual(cleaned["subjects"][0]["code"], "CS201")
        self.assertEqual(cleaned["subjects"][0]["hours_per_week"], 4)

        # Mappings
        self.assertEqual(len(cleaned["mappings"]), 1)
        self.assertEqual(cleaned["mappings"][0]["subject_code"], "CS201")

    def test_faculty_import_and_mapping_without_email(self):
        from app.api.endpoints.imports import _import_faculty, _import_mappings, _empty_result

        # Import faculty with name only
        res_fac = _empty_result("faculty")
        _import_faculty(self.db, [(1, {"name": "Dr. Katherine Johnson", "email": ""})], res_fac)
        self.assertEqual(res_fac["imported"], 1)

        saved_fac = self.db["faculty"].find_one({"name": "Dr. Katherine Johnson"})
        self.assertIsNotNone(saved_fac)

        # Import class and subject
        self.db["classes"].insert_one({"_id": "c1", "name": "CSE-A"})
        self.db["subjects"].insert_one({"_id": "s1", "name": "Math", "code": "M101"})

        # Import mapping using faculty name
        res_map = _empty_result("mappings")
        _import_mappings(self.db, [(1, {
            "subject_code": "M101",
            "class_name": "CSE-A",
            "faculty_name": "Dr. Katherine Johnson"
        })], res_map)
        self.assertEqual(res_map["imported"], 1)

        # Subject mapping was updated with the faculty ID
        saved_subj = self.db["subjects"].find_one({"code": "M101", "class_id": "c1"})
        self.assertIsNotNone(saved_subj)
        self.assertEqual(saved_subj["faculty_id"], saved_fac["_id"])


if __name__ == "__main__":
    unittest.main()

