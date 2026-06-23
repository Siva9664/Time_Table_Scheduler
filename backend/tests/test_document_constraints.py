import asyncio
import json
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.endpoints import timetable as timetable_endpoint
from app.services.document_constraints import (
    ExtractedDocument,
    build_constraint_text_from_documents,
    extract_document_text,
)


class DocumentConstraintTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "subject_names": ["Mathematics", "Physics", "ML Lab"],
            "class_names": ["CSE A"],
            "faculty_names": [],
            "periods_per_day": 3,
        }

    def test_csv_timetable_rows_generate_fixed_slot_constraints(self):
        content = (
            "Class CSE A\n"
            "Day,Period 1,Period 2,Period 3\n"
            "Monday,Mathematics,Free,Physics\n"
            "Tuesday,Break,ML Lab,Physics\n"
        ).encode()
        document = extract_document_text("existing.csv", content, "text/csv")

        constraints_text, constraints, warnings = build_constraint_text_from_documents([document], self.context)

        self.assertFalse(warnings)
        self.assertEqual(len(constraints), 4)
        self.assertIn("For Class CSE A, Mathematics must be on Monday period 1.", constraints_text)
        self.assertIn("For Class CSE A, Physics must be on Monday period 3.", constraints_text)
        self.assertIn("For Class CSE A, ML Lab must be on Tuesday period 2.", constraints_text)

    def test_json_schedule_data_generates_fixed_slot_constraints(self):
        payload = {
            "schedule_data": {
                "class_1": {
                    "class_name": "CSE A",
                    "timetable": {
                        "Monday": [
                            {"period": 1, "subject": "Mathematics"},
                            {"slot_type": "break", "label": "Lunch"},
                            {"period": 2, "subject": "Physics"},
                        ]
                    },
                }
            }
        }
        document = ExtractedDocument(
            filename="generated.json",
            content_type="application/json",
            text=json.dumps(payload),
            extractor="json",
        )

        constraints_text, constraints, warnings = build_constraint_text_from_documents([document], self.context)

        self.assertFalse(warnings)
        self.assertEqual(len(constraints), 2)
        self.assertIn("For Class CSE A, Mathematics must be on Monday period 1.", constraints_text)
        self.assertIn("For Class CSE A, Physics must be on Monday period 2.", constraints_text)


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query=None, projection=None):
        return [dict(doc) for doc in self.docs]


class FakeDB:
    def __init__(self):
        self.collections = {
            "faculty": FakeCollection([]),
            "subjects": FakeCollection([
                {"name": "Mathematics", "code": "MATH", "requires_lab": False},
                {"name": "Physics", "code": "PHY", "requires_lab": False},
            ]),
            "classes": FakeCollection([
                {"name": "CSE", "section": "A"},
            ]),
        }

    def __getitem__(self, name):
        return self.collections.get(name, FakeCollection([]))


class FakeUploadFile:
    def __init__(self, filename, content, content_type="text/csv"):
        self.filename = filename
        self._content = content
        self.content_type = content_type

    async def read(self):
        return self._content


class ConstraintUploadEndpointTests(unittest.TestCase):
    def test_upload_endpoint_returns_generated_constraints(self):
        upload = FakeUploadFile(
            "existing.csv",
            b"Class CSE A\nDay,Period 1,Period 2\nMonday,Mathematics,Physics\n",
        )

        payload = asyncio.run(
            timetable_endpoint.generate_constraints_from_files(
                files=[upload],
                periods_per_day=3,
                db=FakeDB(),
                current_user={"id": "admin"},
            )
        )

        self.assertIn("Mathematics must be on Monday period 1", payload["constraints_text"])
        self.assertGreaterEqual(len(payload["custom_constraints"]), 2)
        self.assertEqual(payload["files"][0]["extractor"], "text")


if __name__ == "__main__":
    unittest.main()
