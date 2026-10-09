import csv
import io
import json
import os
import re
import urllib.request
import urllib.error
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from ...core.security import get_admin_user, get_tenant_db

router = APIRouter()


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/templates")
async def download_templates():
    """Create a ZIP file containing all CSV templates in csv_templates folder."""
    # Base directory of the backend project
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    templates_dir = os.path.join(base_dir, "csv_templates")

    if not os.path.exists(templates_dir):
        raise HTTPException(status_code=404, detail="csv_templates folder not found.")

    # Create zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                if file.endswith(".csv") or file.lower() == "readme.md":
                    file_path = os.path.join(root, file)
                    # Add file to zip archive under its filename
                    zip_file.write(file_path, arcname=file)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=csv_templates.zip",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


COMMON_ALIASES = {

    "subject_code": [
        "subjectcode",
        "subcode",
        "code",
        "subject_id",
        "sub_id",
        "subject code",
    ],
    "class_name": ["classname", "class", "clsname", "cls_name", "batch", "class name"],
    "class_section": [
        "classsection",
        "section",
        "sec",
        "class_sec",
        "cls_sec",
        "class section",
        "class_section",
    ],
    "faculty_email": [
        "facultyemail",
        "email",
        "facemail",
        "fac_email",
        "instructor_email",
        "teacher_email",
        "faculty email",
        "faculty_email",
    ],
    "department_code": [
        "departmentcode",
        "deptcode",
        "dept_code",
        "department_id",
        "dept_id",
        "department",
        "department code",
        "department_code",
    ],
    "department_codes": [
        "departmentcodes",
        "deptcodes",
        "dept_codes",
        "departments",
        "department codes",
        "department_codes",
    ],
    "batch_name": [
        "batchname",
        "batch",
        "batch_id",
        "semester",
        "batch name",
        "batch_name",
    ],
    "hours_per_week": [
        "hoursperweek",
        "hours",
        "weekly_hours",
        "periods",
        "hours per week",
        "hours_per_week",
    ],
    "requires_lab": [
        "requireslab",
        "lab",
        "islab",
        "is_lab",
        "requires_lab_session",
        "requires lab",
        "requires_lab",
    ],
    "max_hours_per_week": [
        "maxhoursperweek",
        "max_hours",
        "weekly_limit",
        "max hours per week",
        "max_hours_per_week",
    ],
    "student_count": [
        "studentcount",
        "students",
        "strength",
        "size",
        "class_size",
        "student count",
        "student_count",
    ],
    "name": ["name", "title", "full_name", "full name"],
    "code": ["code", "id", "identifier"],
    "email": ["email", "email_address", "email address"],
    "start_time": ["starttime", "start", "start_time", "start time"],
    "end_time": ["endtime", "end", "end_time", "end time"],
    "period_duration": [
        "periodduration",
        "duration",
        "period_duration",
        "period duration",
    ],
    "room_type": ["roomtype", "type", "room_type", "room type"],
    "capacity": ["capacity", "seats", "strength", "room_capacity", "room capacity"],
    "room_code": [
        "roomcode",
        "room",
        "room_id",
        "assigned_room",
        "room code",
        "room_code",
        "default_room",
    ],
    "section": ["section", "sec", "classsection", "class_section", "class section"],
    "semester": ["semester", "sem", "term"],
    "credits": ["credits", "credit", "credit_hours", "credit hours"],
    "break_times": ["breaktimes", "breaks", "break_times", "break times"],
    "lunch_break": ["lunchbreak", "lunch", "lunch_break", "lunch break"],
    "unavailable_slots": [
        "unavailableslots",
        "unavailable",
        "unavailable_slots",
        "unavailable slots",
        "blocked_slots",
        "blocked slots",
    ],

}

EXPECTED_HEADERS = {
    "departments": ["name", "code"],
    "batches": [
        "name",
        "start_time",
        "end_time",
        "period_duration",
        "break_times",
        "lunch_break",
    ],
    "classes": [
        "name",
        "section",
        "semester",
        "student_count",
        "department_code",
        "batch_name",
        "room_code",
    ],
    "rooms": ["name", "code", "room_type", "capacity", "department_code"],
    "subjects": [
        "name",
        "code",
        "hours_per_week",
        "credits",
        "requires_lab",
        "department_codes",
        "batch_name",
    ],
    "faculty": [
        "name",
        "email",
        "department_code",
        "max_hours_per_week",
        "unavailable_slots",
    ],
    "mappings": [
        "subject_code",
        "class_name",
        "class_section",
        "faculty_email",
        "room_code",
    ],
}

ALLOWED_IMPORT_TYPES = {
    "departments",
    "batches",
    "classes",
    "rooms",
    "subjects",
    "faculty",
    "mappings",
}
IMPORT_ORDER = [
    "departments",
    "batches",
    "rooms",
    "classes",
    "subjects",
    "faculty",
    "mappings",
]
MAX_ISSUES = 50

REQUIRED_HEADERS = {
    "departments": ["name", "code"],
    "batches": ["name"],
    "classes": ["name"],
    "rooms": ["name"],
    "subjects": ["name", "code"],
    "faculty": ["name", "email"],
    "mappings": ["subject_code", "class_name", "faculty_email"],
}


def normalize_string(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum())


def similarity_score(s1: str, s2: str) -> float:
    s1_norm, s2_norm = normalize_string(s1), normalize_string(s2)
    if not s1_norm or not s2_norm:
        return 0.0
    if s1_norm == s2_norm:
        return 1.0
    if s1_norm in s2_norm or s2_norm in s1_norm:
        return 0.85

    # Simple edit distance
    len_s1, len_s2 = len(s1_norm), len(s2_norm)
    matrix = [[0] * (len_s2 + 1) for _ in range(len_s1 + 1)]
    for i in range(len_s1 + 1):
        matrix[i][0] = i
    for j in range(len_s2 + 1):
        matrix[0][j] = j
    for i in range(1, len_s1 + 1):
        for j in range(1, len_s2 + 1):
            cost = 0 if s1_norm[i - 1] == s2_norm[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost
            )
    dist = matrix[len_s1][len_s2]
    return 1.0 - (dist / max(len_s1, len_s2))


def map_headers(uploaded_headers: List[str], import_type: str) -> dict:
    """
    Returns a mapping dict: target_header_name -> uploaded_header_name
    or raises HTTPException if a required header is missing.
    """
    expected = EXPECTED_HEADERS.get(import_type, [])
    required = REQUIRED_HEADERS.get(import_type, [])
    mapping = {}
    used_headers = set()

    duplicate_headers = []
    seen_headers = set()
    for header in uploaded_headers:
        normalized = normalize_string(header)
        if not normalized:
            continue
        if normalized in seen_headers:
            duplicate_headers.append(header)
        seen_headers.add(normalized)

    if duplicate_headers:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate CSV column(s): {', '.join(duplicate_headers)}. Please keep each column name unique.",
        )

    for target in expected:
        best_score = 0.0
        best_header = None

        # 1. Match via defined aliases
        target_aliases = COMMON_ALIASES.get(target, [])
        normalized_aliases = {normalize_string(a) for a in target_aliases}
        normalized_aliases.add(normalize_string(target))
        for h in uploaded_headers:
            if h in used_headers:
                continue
            h_norm = normalize_string(h)
            if h_norm in normalized_aliases:
                best_score = 1.0
                best_header = h
                break

        # 2. Fallback to similarity
        if best_score < 1.0:
            for h in uploaded_headers:
                if h in used_headers:
                    continue
                score = similarity_score(h, target)
                if score > best_score:
                    best_score = score
                    best_header = h

        # Apply matched header if confidence is high enough
        if best_header and best_score >= 0.65:
            mapping[target] = best_header
            used_headers.add(best_header)

    # Check for missing required headers
    missing = []
    for req in required:
        if req not in mapping:
            missing.append(req)

    if missing:
        # Provide suggestions
        detail = (
            f"Missing required column(s): {', '.join(missing)} for type '{import_type}'.\n"
            f"Uploaded headers were: {', '.join(uploaded_headers)}.\n"
            "Please ensure your CSV matches the template layout."
        )
        raise HTTPException(status_code=400, detail=detail)

    return mapping


def _decode_csv_content(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=400, detail="Could not decode CSV file. Please upload a UTF-8 CSV."
    )


def _read_csv_rows(
    content: bytes,
) -> Tuple[List[str], List[Tuple[int, Dict[str, str]]]]:
    text = _decode_csv_content(content)
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = [h.strip() for h in (reader.fieldnames or []) if h and h.strip()]
    rows = []
    for row_number, row in enumerate(reader, start=2):
        cleaned = {}
        for key, value in row.items():
            key = (key or "").strip()
            if not key:
                continue
            if isinstance(value, list):
                value = ";".join(str(item) for item in value if item is not None)
            cleaned[key] = ("" if value is None else str(value)).strip()
        rows.append((row_number, cleaned))
    return headers, rows


def _guess_import_type(filename: str) -> Optional[str]:
    base_name = os.path.basename(filename or "").lower()
    if not base_name.endswith(".csv"):
        return None

    stem = os.path.splitext(base_name)[0]
    stem = re.sub(r"\s*\(\d+\)$", "", stem)
    for suffix in ("_template", "-template", " template"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]

    aliases = {
        "department": "departments",
        "departments": "departments",
        "batch": "batches",
        "batches": "batches",
        "class": "classes",
        "classes": "classes",
        "room": "rooms",
        "rooms": "rooms",
        "subject": "subjects",
        "subjects": "subjects",
        "faculty": "faculty",
        "faculties": "faculty",
        "mapping": "mappings",
        "mappings": "mappings",
        "faculty_mapping": "mappings",
        "faculty_mappings": "mappings",
    }
    normalized_stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    if normalized_stem in aliases:
        return aliases[normalized_stem]

    tokens = [token for token in normalized_stem.split("_") if token]
    token_set = set(tokens)
    if "faculty" in token_set and ({"mapping", "mappings"} & token_set):
        return "mappings"
    for token in tokens:
        if token in aliases:
            return aliases[token]
    return None


def _empty_result(import_type: str) -> Dict[str, Any]:
    return {
        "imported": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "type": import_type,
        "warnings": [],
        "errors": [],
        "warning_count": 0,
        "error_count": 0,
    }


def _record_issue(
    result: Dict[str, Any], bucket: str, row_number: Optional[int], message: str
):
    count_key = "error_count" if bucket == "errors" else "warning_count"
    result[count_key] += 1
    if len(result[bucket]) < MAX_ISSUES:
        issue = {"message": message}
        if row_number is not None:
            issue["row"] = row_number
        result[bucket].append(issue)


def _row_value(row: Dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _require_value(
    row: Dict[str, str], key: str, row_number: int, result: Dict[str, Any]
) -> Optional[str]:
    value = _row_value(row, key)
    if not value:
        _record_issue(result, "errors", row_number, f"Missing required value '{key}'.")
        return None
    return value


def _parse_int(
    value: str,
    default: int,
    result: Dict[str, Any],
    row_number: int,
    field: str,
    min_value: Optional[int] = None,
) -> int:
    if value == "":
        return default
    try:
        number = float(value)
        if not number.is_integer():
            raise ValueError
        parsed = int(number)
        if min_value is not None and parsed < min_value:
            raise ValueError
        return parsed
    except (TypeError, ValueError):
        min_hint = (
            f" greater than or equal to {min_value}" if min_value is not None else ""
        )
        _record_issue(
            result,
            "warnings",
            row_number,
            f"Invalid integer for '{field}'{min_hint}: '{value}'. Used {default}.",
        )
        return default


def _parse_bool(
    value: str,
    result: Dict[str, Any],
    row_number: int,
    field: str,
    default: bool = False,
) -> bool:
    if value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "lab", "required"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    _record_issue(
        result,
        "warnings",
        row_number,
        f"Invalid boolean for '{field}': '{value}'. Used {default}.",
    )
    return default


def _parse_time(
    value: str, default: str, result: Dict[str, Any], row_number: int, field: str
) -> str:
    if value == "":
        return default
    match = re.match(r"^(\d{1,2}):(\d{2})$", value.strip())
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    _record_issue(
        result,
        "warnings",
        row_number,
        f"Invalid time for '{field}': '{value}'. Used {default}.",
    )
    return default


def _parse_json_field(
    value: str,
    default: Any,
    expected_type: type,
    result: Dict[str, Any],
    row_number: int,
    field: str,
) -> Any:
    if value == "":
        return default
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        _record_issue(
            result,
            "warnings",
            row_number,
            f"Invalid JSON for '{field}'. Used default value.",
        )
        return default
    if not isinstance(parsed, expected_type):
        _record_issue(
            result,
            "warnings",
            row_number,
            f"JSON field '{field}' must be {expected_type.__name__}. Used default value.",
        )
        return default
    return parsed


def _lookup_value(value: str) -> str:
    return (value or "").strip().casefold()


def _find_one_by_any(
    db, collection_name: str, fields: List[str], value: str
) -> Optional[dict]:
    value = (value or "").strip()
    if not value:
        return None
    collection = db[collection_name]
    for field in fields:
        doc = collection.find_one({field: value})
        if doc:
            return doc

    needle = _lookup_value(value)
    for doc in collection.find({}):
        for field in fields:
            if _lookup_value(str(doc.get(field) or "")) == needle:
                return doc
    return None


def _find_department(db, code_or_name: str) -> Optional[dict]:
    return _find_one_by_any(db, "departments", ["code", "name"], code_or_name)


def _find_batch(db, name: str) -> Optional[dict]:
    return _find_one_by_any(db, "batches", ["name"], name)


def _find_room(db, code_or_name: str) -> Optional[dict]:
    return _find_one_by_any(db, "rooms", ["code", "name"], code_or_name)


def _find_faculty(db, email_or_name: str) -> Optional[dict]:
    return _find_one_by_any(db, "faculty", ["email", "name"], email_or_name)


def _find_class(db, name: str, section: str = "") -> Optional[dict]:
    name = (name or "").strip()
    section = (section or "").strip()
    if not name:
        return None

    query = {"name": name}
    if section:
        query["section"] = section
    doc = db["classes"].find_one(query)
    if doc:
        return doc

    name_norm = _lookup_value(name)
    section_norm = _lookup_value(section)
    for class_doc in db["classes"].find({}):
        if _lookup_value(str(class_doc.get("name") or "")) != name_norm:
            continue
        if (
            section
            and _lookup_value(str(class_doc.get("section") or "")) != section_norm
        ):
            continue
        return class_doc
    return None


def _find_core_subject(db, code: str) -> Optional[dict]:
    code = (code or "").strip()
    if not code:
        return None

    exact_queries = [
        {"code": code, "source_subject_id": {"$exists": False}, "class_id": None},
        {"code": code, "source_subject_id": {"$exists": False}},
        {"code": code},
    ]
    for query in exact_queries:
        doc = db["subjects"].find_one(query)
        if doc:
            return doc

    code_norm = _lookup_value(code)
    fallback = None
    for subject in db["subjects"].find({}):
        if _lookup_value(str(subject.get("code") or "")) != code_norm:
            continue
        if subject.get("source_subject_id"):
            continue
        if not subject.get("class_id"):
            return subject
        fallback = fallback or subject
    return fallback


def _find_existing_subject_mapping(
    db, subject: dict, source_id: str, class_id: str
) -> Optional[dict]:
    for existing in db["subjects"].find({"class_id": class_id}):
        if str(existing.get("source_subject_id") or "") == str(source_id):
            return existing
        if str(existing.get("_id")) == str(source_id):
            return existing
        if (
            not existing.get("source_subject_id")
            and existing.get("code") == subject.get("code")
            and existing.get("name") == subject.get("name")
            and existing.get("requires_lab", False)
            == subject.get("requires_lab", False)
        ):
            return existing
    return None


def _mark_saved(result: Dict[str, Any], inserted: bool):
    result["imported"] += 1
    result["inserted" if inserted else "updated"] += 1


def _save_document(
    db,
    collection_name: str,
    existing: Optional[dict],
    document: dict,
    result: Dict[str, Any],
    on_insert: Optional[dict] = None,
):
    now = _utcnow()
    update_doc = {**document, "updated_at": now}
    if existing:
        db[collection_name].update_one({"_id": existing["_id"]}, {"$set": update_doc})
        _mark_saved(result, inserted=False)
        return existing["_id"]

    insert_doc = {**(on_insert or {}), **document, "created_at": now}
    insert_result = db[collection_name].insert_one(insert_doc)
    _mark_saved(result, inserted=True)
    return insert_result.inserted_id


def _split_codes(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[;,]", value) if item.strip()]


def _normalize_rows(
    headers: List[str],
    raw_rows: List[Tuple[int, Dict[str, str]]],
    import_type: str,
    result: Dict[str, Any],
) -> List[Tuple[int, Dict[str, str]]]:
    if not headers:
        raise HTTPException(
            status_code=400, detail="The uploaded CSV has no header row."
        )
    if not raw_rows:
        result["message"] = "The uploaded CSV file is empty."
        return []

    header_mapping = map_headers(headers, import_type)
    rows = []
    for row_number, raw_row in raw_rows:
        norm_row = {}
        for target_key, uploaded_key in header_mapping.items():
            norm_row[target_key] = raw_row.get(uploaded_key, "").strip()
        if not any(value for value in norm_row.values()):
            result["skipped"] += 1
            continue
        rows.append((row_number, norm_row))
    if not rows:
        result["message"] = "The uploaded CSV file has no data rows."
    return rows


def _import_departments(
    db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]
):
    for row_number, row in rows:
        name = _require_value(row, "name", row_number, result)
        code = _require_value(row, "code", row_number, result)
        if not name or not code:
            result["skipped"] += 1
            continue
        existing = _find_department(db, code)
        _save_document(
            db, "departments", existing, {"name": name, "code": code}, result
        )


def _import_batches(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, "name", row_number, result)
        if not name:
            result["skipped"] += 1
            continue
        document = {
            "name": name,
            "start_time": _parse_time(
                _row_value(row, "start_time"), "09:00", result, row_number, "start_time"
            ),
            "end_time": _parse_time(
                _row_value(row, "end_time"), "17:00", result, row_number, "end_time"
            ),
            "period_duration": _parse_int(
                _row_value(row, "period_duration"),
                60,
                result,
                row_number,
                "period_duration",
                min_value=1,
            ),
            "break_times": _parse_json_field(
                _row_value(row, "break_times"),
                [],
                list,
                result,
                row_number,
                "break_times",
            ),
            "lunch_break": _parse_json_field(
                _row_value(row, "lunch_break"),
                {},
                dict,
                result,
                row_number,
                "lunch_break",
            ),
        }
        existing = _find_batch(db, name)
        _save_document(db, "batches", existing, document, result)


def _import_rooms(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, "name", row_number, result)
        if not name:
            result["skipped"] += 1
            continue
        dept = _find_department(db, _row_value(row, "department_code"))
        if _row_value(row, "department_code") and not dept:
            _record_issue(
                result,
                "warnings",
                row_number,
                f"Department '{_row_value(row, 'department_code')}' not found for room '{name}'.",
            )

        room_type = (_row_value(row, "room_type") or "lecture").lower()
        if room_type not in {"lecture", "lab", "seminar"}:
            _record_issue(
                result,
                "warnings",
                row_number,
                f"Invalid room_type '{room_type}' for room '{name}'. Used lecture.",
            )
            room_type = "lecture"

        code = _row_value(row, "code")
        document = {
            "name": name,
            "code": code,
            "room_type": room_type,
            "capacity": _parse_int(
                _row_value(row, "capacity"),
                0,
                result,
                row_number,
                "capacity",
                min_value=0,
            ),
            "department_id": str(dept["_id"]) if dept else None,
        }
        existing = _find_room(db, code or name)
        _save_document(db, "rooms", existing, document, result)


def _import_classes(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, "name", row_number, result)
        if not name:
            result["skipped"] += 1
            continue

        dept = _find_department(db, _row_value(row, "department_code"))
        batch = _find_batch(db, _row_value(row, "batch_name"))
        room = _find_room(db, _row_value(row, "room_code"))
        if _row_value(row, "department_code") and not dept:
            _record_issue(
                result,
                "warnings",
                row_number,
                f"Department '{_row_value(row, 'department_code')}' not found for class '{name}'.",
            )
        if _row_value(row, "batch_name") and not batch:
            _record_issue(
                result,
                "warnings",
                row_number,
                f"Batch '{_row_value(row, 'batch_name')}' not found for class '{name}'.",
            )
        if _row_value(row, "room_code") and not room:
            _record_issue(
                result,
                "warnings",
                row_number,
                f"Room '{_row_value(row, 'room_code')}' not found for class '{name}'.",
            )

        section = _row_value(row, "section")
        document = {
            "name": name,
            "section": section,
            "semester": _parse_int(
                _row_value(row, "semester"),
                1,
                result,
                row_number,
                "semester",
                min_value=1,
            ),
            "student_count": _parse_int(
                _row_value(row, "student_count"),
                0,
                result,
                row_number,
                "student_count",
                min_value=0,
            ),
            "department_id": str(dept["_id"]) if dept else None,
            "batch_id": str(batch["_id"]) if batch else None,
            "room_id": str(room["_id"]) if room else None,
        }
        existing = _find_class(db, name, section)
        _save_document(db, "classes", existing, document, result)


def _import_subjects(
    db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]
):
    for row_number, row in rows:
        name = _require_value(row, "name", row_number, result)
        code = _require_value(row, "code", row_number, result)
        if not name or not code:
            result["skipped"] += 1
            continue

        department_ids = []
        for department_code in _split_codes(_row_value(row, "department_codes")):
            dept = _find_department(db, department_code)
            if dept:
                department_ids.append(str(dept["_id"]))
            else:
                _record_issue(
                    result,
                    "warnings",
                    row_number,
                    f"Department '{department_code}' not found for subject '{code}'.",
                )

        batch = _find_batch(db, _row_value(row, "batch_name"))
        if _row_value(row, "batch_name") and not batch:
            _record_issue(
                result,
                "warnings",
                row_number,
                f"Batch '{_row_value(row, 'batch_name')}' not found for subject '{code}'.",
            )

        document = {
            "name": name,
            "code": code,
            "hours_per_week": _parse_int(
                _row_value(row, "hours_per_week"),
                0,
                result,
                row_number,
                "hours_per_week",
                min_value=0,
            ),
            "credits": _parse_int(
                _row_value(row, "credits"),
                3,
                result,
                row_number,
                "credits",
                min_value=0,
            ),
            "requires_lab": _parse_bool(
                _row_value(row, "requires_lab"), result, row_number, "requires_lab"
            ),
            "department_ids": department_ids,
            "department_id": department_ids[0] if department_ids else None,
            "batch_id": str(batch["_id"]) if batch else None,
        }
        existing = _find_core_subject(db, code)
        _save_document(
            db,
            "subjects",
            existing,
            document,
            result,
            on_insert={"class_id": None, "faculty_id": None},
        )


def _import_faculty(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, "name", row_number, result)
        if not name:
            result["skipped"] += 1
            continue

        email = (_row_value(row, "email") or "").strip().lower()
        dept = _find_department(db, _row_value(row, "department_code"))
        if _row_value(row, "department_code") and not dept:
            _record_issue(
                result,
                "warnings",
                row_number,
                f"Department '{_row_value(row, 'department_code')}' not found for faculty '{name}'.",
            )

        document = {
            "name": name,
            "department_id": str(dept["_id"]) if dept else None,
            "max_hours_per_week": _parse_int(
                _row_value(row, "max_hours_per_week"),
                20,
                result,
                row_number,
                "max_hours_per_week",
                min_value=0,
            ),
            "unavailable_slots": _parse_json_field(
                _row_value(row, "unavailable_slots"),
                [],
                list,
                result,
                row_number,
                "unavailable_slots",
            ),
        }
        if email:
            document["email"] = email

        existing = _find_faculty(db, email) if email else _find_faculty(db, name)
        _save_document(db, "faculty", existing, document, result)


def _import_mappings(
    db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]
):
    for row_number, row in rows:
        subject_code = _require_value(row, "subject_code", row_number, result)
        class_name = _require_value(row, "class_name", row_number, result)
        if not subject_code or not class_name:
            result["skipped"] += 1
            continue

        faculty_identifier = (_row_value(row, "faculty_email") or _row_value(row, "faculty_name") or "").strip()
        subj = _find_core_subject(db, subject_code)
        cls = _find_class(db, class_name, _row_value(row, "class_section"))
        fac = _find_faculty(db, faculty_identifier) if faculty_identifier else None
        room = (
            _find_room(db, _row_value(row, "room_code"))
            if _row_value(row, "room_code")
            else None
        )

        missing = []
        if not subj:
            missing.append(f"subject '{subject_code}'")
        if not cls:
            missing.append(f"class '{class_name}'")
        if faculty_identifier and not fac:
            missing.append(f"faculty '{faculty_identifier}'")
        if missing:
            result["skipped"] += 1
            _record_issue(
                result,
                "errors",
                row_number,
                f"Could not apply mapping because {', '.join(missing)} was not found.",
            )
            continue
        if _row_value(row, "room_code") and not room:
            _record_issue(
                result,
                "warnings",
                row_number,
                f"Room '{_row_value(row, 'room_code')}' not found for mapping '{subject_code}' -> '{class_name}'.",
            )

        class_id = str(cls["_id"])
        faculty_id = str(fac["_id"]) if fac else None
        if room:
            db["classes"].update_one(
                {"_id": cls["_id"]},
                {"$set": {"room_id": str(room["_id"]), "updated_at": _utcnow()}},
            )

        source_id = subj.get("source_subject_id") or str(subj["_id"])
        document = {
            "name": subj.get("name") or "",
            "code": subj.get("code") or "",
            "hours_per_week": subj.get("hours_per_week"),
            "credits": subj.get("credits", 3),
            "requires_lab": subj.get("requires_lab", False),
            "department_id": subj.get("department_id"),
            "department_ids": subj.get("department_ids")
            or ([subj.get("department_id")] if subj.get("department_id") else []),
            "batch_id": subj.get("batch_id"),
            "class_id": class_id,
            "faculty_id": faculty_id,
            "source_subject_id": source_id,
        }
        existing = _find_existing_subject_mapping(db, subj, source_id, class_id)
        _save_document(db, "subjects", existing, document, result)


IMPORT_HANDLERS = {
    "departments": _import_departments,
    "batches": _import_batches,
    "classes": _import_classes,
    "rooms": _import_rooms,
    "subjects": _import_subjects,
    "faculty": _import_faculty,
    "mappings": _import_mappings,
}


def _import_csv_data(import_type: str, content: bytes, db) -> Dict[str, Any]:
    result = _empty_result(import_type)
    headers, raw_rows = _read_csv_rows(content)
    rows = _normalize_rows(headers, raw_rows, import_type, result)
    if rows:
        IMPORT_HANDLERS[import_type](db, rows, result)
    if result["error_count"] > len(result["errors"]):
        result["message"] = (
            f"{result.get('message', '')} Showing first {MAX_ISSUES} errors.".strip()
        )
    if result["warning_count"] > len(result["warnings"]):
        result["message"] = (
            f"{result.get('message', '')} Showing first {MAX_ISSUES} warnings.".strip()
        )
    if "message" not in result:
        parts = [f"Imported {result['imported']} {import_type} row(s)."]
        if result["skipped"]:
            parts.append(f"Skipped {result['skipped']} row(s).")
        if result["warning_count"]:
            parts.append(f"{result['warning_count']} warning(s).")
        if result["error_count"]:
            parts.append(f"{result['error_count']} error(s).")
        result["message"] = " ".join(parts)
    return result


async def _import_upload_file(import_type: str, file: UploadFile, db) -> Dict[str, Any]:
    import_type = (import_type or "").strip().lower()
    if import_type not in ALLOWED_IMPORT_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported import type: {import_type}"
        )
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    content = await file.read()
    if not content:
        result = _empty_result(import_type)
        result["message"] = "The uploaded CSV file is empty."
        return result

    try:
        return _import_csv_data(import_type, content, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV Parsing Error: {str(e)}")


@router.post("/upload")
async def upload_csv(
    type: str = Form(...),
    file: UploadFile = File(...),
    db=Depends(get_tenant_db),
    _current_user: dict = Depends(get_admin_user),
):
    """Upload a CSV and import data. Form param `type` selects which importer to run.
    Supported types: departments, batches, classes, rooms, subjects, faculty, mappings
    """
    result = await _import_upload_file(type, file, db)
    return JSONResponse(result)


@router.post("/upload-folder")
async def upload_csv_folder(
    files: List[UploadFile] = File(...),
    db=Depends(get_tenant_db),
    _current_user: dict = Depends(get_admin_user),
):
    """Upload a folder worth of CSV files and import recognized files in dependency order."""
    file_by_type = {}
    results = []

    for file in files:
        import_type = _guess_import_type(file.filename)
        if not import_type:
            results.append(
                {
                    "file": file.filename,
                    "type": None,
                    "status": "skipped",
                    "message": "Not a recognized CSV import file.",
                }
            )
            continue
        if import_type in file_by_type:
            results.append(
                {
                    "file": file.filename,
                    "type": import_type,
                    "status": "skipped",
                    "message": f"Duplicate {import_type} CSV. The first matching file was used.",
                }
            )
            continue
        file_by_type[import_type] = file

    total_imported = 0
    processed = 0

    for import_type in IMPORT_ORDER:
        file = file_by_type.get(import_type)
        if not file:
            continue

        try:
            data = await _import_upload_file(import_type, file, db)
            imported = int(data.get("imported") or 0)
            total_imported += imported
            processed += 1
            status = "partial" if data.get("error_count") else "success"
            results.append(
                {
                    "file": file.filename,
                    "type": import_type,
                    "status": status,
                    "imported": imported,
                    "inserted": data.get("inserted", 0),
                    "updated": data.get("updated", 0),
                    "skipped": data.get("skipped", 0),
                    "warnings": data.get("warnings", []),
                    "errors": data.get("errors", []),
                    "warning_count": data.get("warning_count", 0),
                    "error_count": data.get("error_count", 0),
                    "message": data.get("message")
                    or f"Imported {imported} {import_type}.",
                }
            )
        except HTTPException as exc:
            results.append(
                {
                    "file": file.filename,
                    "type": import_type,
                    "status": "failed",
                    "message": exc.detail,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "file": file.filename,
                    "type": import_type,
                    "status": "failed",
                    "message": str(exc),
                }
            )

    missing = [
        import_type for import_type in IMPORT_ORDER if import_type not in file_by_type
    ]
    failed = [item for item in results if item.get("status") == "failed"]
    partial = [item for item in results if item.get("status") == "partial"]

    return JSONResponse(
        {
            "imported": total_imported,
            "processed": processed,
            "failed": len(failed),
            "partial": len(partial),
            "missing": missing,
            "results": results,
        }
    )


# ── Document Entity Extraction and Filling ──────────────────────────────────────

ACADEMIC_EXTRACTOR_SYSTEM_PROMPT = """You are a STRICT academic database entity extractor for a university timetable scheduler.

## OBJECTIVE
Extract ONLY the required academic scheduling entities that DIRECTLY match our database table schemas.
Do NOT fetch or transcribe irrelevant text. Filter out noise so that only clean, database-ready records are returned.

## ABSOLUTE RULES — READ CAREFULLY

1. **MATCH DATABASE SCHEMAS ONLY:**
   Extract ONLY data that belongs to these 7 academic categories:
   - `departments`: Academic teaching departments (e.g., Computer Science, Mechanical).
   - `batches`: Timing/shift groups explicitly defined with hours or timetable column slots.
   - `classes`: Student groups/sections receiving instruction (e.g., 'CSE-A', 'B.Tech Sem 4').
   - `rooms`: Physical lecture halls, classrooms, or laboratories (e.g., 'LH-101', 'CS Lab 2').
   - `subjects`: Courses taught with course codes or titles (e.g., 'Data Structures', 'CS301').
   - `faculty`: Instructors, professors, and lecturers assigned to teach classes.
   - `mappings`: Teaching allocations linking a subject to a class, faculty member, or room.

2. **IGNORE ALL ADMINISTRATIVE & BOILERPLATE NOISE:**
   - DISCARD college/university names, header banners, mottos, and logos.
   - DISCARD exam guidelines, classroom rules, grading policies, textbook lists, syllabus course objectives, and circulars.
   - DISCARD administrative signatories and officers: DO NOT extract "Principal", "Dean", "HOD", "Director", "Controller of Examinations", "Registrar", "Exam Incharge", or "Typist" as faculty members. Only extract actual teaching staff.

3. **STRICT ZERO-MOCK-DATA POLICY:**
   - NEVER invent, guess, assume, or extrapolate ANY value.
   - If an email is NOT written in the document, use "" (empty string). NEVER generate fake emails (e.g. NEVER output "@institution.edu" or any made-up domain).
   - If a numeric field (period_duration, capacity, student_count, semester, hours_per_week, credits) is not explicitly present, use null or "". DO NOT guess 50 or 60 for duration. DO NOT guess 0 for capacity or student counts.
   - If room_type is not specified, use "" (do NOT assume "lecture").
   - If code, section, or department is not specified, use "".
   - If a category is not present in the document, return an empty array [] for that key.

## JSON OUTPUT SCHEMA

Return ONLY a single raw JSON object matching this exact schema:

{
  "departments": [
    {"name": "<exact name>", "code": "<exact code or ''>"}
  ],
  "batches": [
    {"name": "<exact name>", "start_time": "<HH:MM or ''>", "end_time": "<HH:MM or ''>", "period_duration": null, "break_times": "<or ''>", "lunch_break": "<or ''>"}
  ],
  "classes": [
    {"name": "<exact name>", "section": "<exact section or ''>", "department_code": "<exact code or ''>", "batch_name": "<exact name or ''>", "semester": null, "student_count": null, "room_code": "<exact code or ''>"}
  ],
  "rooms": [
    {"name": "<exact name>", "code": "<exact code or ''>", "room_type": "<'lecture'|'lab'|'seminar' or ''>", "capacity": null, "department_code": "<exact code or ''>"}
  ],
  "subjects": [
    {"name": "<exact name>", "code": "<exact code or ''>", "hours_per_week": null, "credits": null, "requires_lab": null, "department_codes": "<exact code or ''>", "batch_name": "<exact name or ''>"}
  ],
  "faculty": [
    {"name": "<exact name>", "email": "<exact email from doc or ''>", "department_code": "<exact code or ''>"}
  ],
  "mappings": [
    {"subject_code": "<exact code or ''>", "class_name": "<exact name or ''>", "class_section": "<exact section or ''>", "faculty_email": "<exact email or teacher name or ''>", "room_code": "<exact code or ''>"}
  ]
}

No markdown fences, no explanations, no commentary. Output ONLY the JSON object.
"""


def _split_text_into_chunks(text: str, max_chars: int = 8000) -> list:
    """Split document text into chunks, preferring to split on 'Sheet:' boundaries.

    For multi-sheet Excel files, the text contains lines like 'Sheet: SheetName'.
    We group text by sheets and create chunks that fit within max_chars,
    combining small sheets together and splitting large sheets if needed.
    """
    import re
    # Split on 'Sheet:' headers (produced by the xlsx extractor)
    sheet_pattern = re.compile(r'^Sheet:\s+', re.MULTILINE)
    parts = sheet_pattern.split(text)
    headers = sheet_pattern.findall(text)

    # If no sheet headers found, just split the text by size
    if len(parts) <= 1:
        chunks = []
        for i in range(0, len(text), max_chars):
            chunks.append(text[i:i + max_chars])
        return chunks if chunks else [text]

    # Rebuild sheet sections: first part is pre-header content, rest are sheets
    sections = []
    if parts[0].strip():
        sections.append(parts[0].strip())
    for i, part in enumerate(parts[1:], 0):
        header = headers[i] if i < len(headers) else "Sheet: "
        sections.append(f"{header}{part}".strip())

    # Group sections into chunks that fit within max_chars
    chunks = []
    current_chunk = ""
    for section in sections:
        if not section.strip():
            continue
        # If adding this section would exceed the limit
        if current_chunk and len(current_chunk) + len(section) + 2 > max_chars:
            chunks.append(current_chunk)
            # If the section itself is too large, split it
            if len(section) > max_chars:
                for i in range(0, len(section), max_chars):
                    chunks.append(section[i:i + max_chars])
                current_chunk = ""
            else:
                current_chunk = section
        else:
            current_chunk = f"{current_chunk}\n\n{section}".strip() if current_chunk else section

    if current_chunk.strip():
        chunks.append(current_chunk)

    return chunks if chunks else [text[:max_chars]]


def _dedupe_extracted_list(items: list) -> list:
    """Remove duplicate dicts from a list, preserving order.

    Uses a JSON serialization of sorted keys for comparison.
    """
    import json
    seen = set()
    unique = []
    for item in items:
        if isinstance(item, dict):
            # Normalize: lowercase name/code fields for comparison
            key_parts = []
            for k in sorted(item.keys()):
                v = item.get(k, "")
                if isinstance(v, str):
                    key_parts.append(f"{k}={v.strip().lower()}")
                else:
                    key_parts.append(f"{k}={v}")
            key = "|".join(key_parts)
        else:
            key = json.dumps(item, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _clean_str(val: Any) -> str:
    """Return stripped string or empty string if None/placeholder."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in {"null", "none", "n/a", "na", "undefined", "-", "--", "''", '""'}:
        return ""
    if s.startswith("<") and s.endswith(">"):
        return ""
    return s


def _clean_int(val: Any) -> Any:
    """Return integer if valid non-negative number, else None."""
    if val is None or val == "":
        return None
    try:
        n = float(val)
        return int(n) if n >= 0 else None
    except (ValueError, TypeError):
        return None


def _clean_bool(val: Any) -> Optional[bool]:
    """Return boolean if valid, else None."""
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in {"true", "1", "yes", "lab"}:
        return True
    if s in {"false", "0", "no", "theory"}:
        return False
    return None


IGNORABLE_SIGNATORIES_AND_BOILERPLATE = {
    "principal", "director", "dean", "hod", "head of department",
    "controller of examinations", "coe", "examination cell", "exam cell",
    "signature", "signatures", "date", "incharge", "in-charge", "coordinator",
    "typist", "staff", "management", "university", "college", "institution",
    "attendance", "rules", "instructions", "general rules", "notice", "notices",
    "time table", "timetable", "notice board", "examination", "semester", "syllabus"
}


def _is_boilerplate_word(text: str) -> bool:
    if not text:
        return True
    norm = re.sub(r'[^a-z0-9 ]', ' ', text.lower()).strip()
    norm = re.sub(r'\s+', ' ', norm)
    return norm in IGNORABLE_SIGNATORIES_AND_BOILERPLATE


def _sanitize_and_filter_extracted_entities(data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Sanitize and filter extracted entities to strictly match database schemas:
    1. Strip all mock data and placeholder values (never synthesize fake emails or numbers).
    2. Discard administrative boilerplate, signatures, and empty/unmatched entities.
    3. Retain only the required/supported database fields for each collection.
    """
    cleaned: Dict[str, List[Dict[str, Any]]] = {
        "departments": [], "batches": [], "classes": [], "rooms": [],
        "subjects": [], "faculty": [], "mappings": []
    }

    # 1. Departments: {name, code}
    for item in data.get("departments", []):
        if not isinstance(item, dict):
            continue
        name = _clean_str(item.get("name"))
        code = _clean_str(item.get("code")).upper()
        if not name and not code:
            continue
        if _is_boilerplate_word(name) or _is_boilerplate_word(code):
            continue
        cleaned["departments"].append({
            "name": name or code,
            "code": code or name[:6].upper().replace(" ", "")
        })

    # 2. Batches: {name, start_time, end_time, period_duration, break_times, lunch_break}
    for item in data.get("batches", []):
        if not isinstance(item, dict):
            continue
        name = _clean_str(item.get("name"))
        if not name or _is_boilerplate_word(name):
            continue
        start_time = _clean_str(item.get("start_time"))
        end_time = _clean_str(item.get("end_time"))
        period_duration = _clean_int(item.get("period_duration"))
        break_times = item.get("break_times")
        if isinstance(break_times, str):
            break_times = _clean_str(break_times)
        lunch_break = item.get("lunch_break")
        if isinstance(lunch_break, str):
            lunch_break = _clean_str(lunch_break)
        cleaned["batches"].append({
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
            "period_duration": period_duration if period_duration is not None else "",
            "break_times": break_times or "",
            "lunch_break": lunch_break or ""
        })

    # 3. Classes: {name, section, semester, student_count, department_code, batch_name, room_code}
    for item in data.get("classes", []):
        if not isinstance(item, dict):
            continue
        name = _clean_str(item.get("name"))
        if not name or _is_boilerplate_word(name):
            continue
        section = _clean_str(item.get("section"))
        dept_code = _clean_str(item.get("department_code")).upper()
        batch_name = _clean_str(item.get("batch_name"))
        room_code = _clean_str(item.get("room_code"))
        semester = _clean_int(item.get("semester"))
        student_count = _clean_int(item.get("student_count"))
        cleaned["classes"].append({
            "name": name,
            "section": section,
            "semester": semester if semester is not None else "",
            "student_count": student_count if student_count is not None else "",
            "department_code": dept_code,
            "batch_name": batch_name,
            "room_code": room_code
        })

    # 4. Rooms: {name, code, room_type, capacity, department_code}
    for item in data.get("rooms", []):
        if not isinstance(item, dict):
            continue
        name = _clean_str(item.get("name"))
        code = _clean_str(item.get("code"))
        if not name and not code:
            continue
        if _is_boilerplate_word(name) or _is_boilerplate_word(code):
            continue
        rtype = _clean_str(item.get("room_type")).lower()
        if rtype not in {"lecture", "lab", "seminar"}:
            rtype = "lecture" if "lab" not in name.lower() else "lab"
        capacity = _clean_int(item.get("capacity"))
        dept_code = _clean_str(item.get("department_code")).upper()
        cleaned["rooms"].append({
            "name": name or code,
            "code": code or name,
            "room_type": rtype,
            "capacity": capacity if capacity is not None else "",
            "department_code": dept_code
        })

    # 5. Subjects: {name, code, hours_per_week, credits, requires_lab, department_codes, batch_name}
    for item in data.get("subjects", []):
        if not isinstance(item, dict):
            continue
        name = _clean_str(item.get("name"))
        code = _clean_str(item.get("code")).upper()
        if not name and not code:
            continue
        if _is_boilerplate_word(name) or _is_boilerplate_word(code):
            continue
        hours = _clean_int(item.get("hours_per_week"))
        credits_val = _clean_int(item.get("credits"))
        req_lab = _clean_bool(item.get("requires_lab"))
        if req_lab is None:
            req_lab = True if "lab" in (name + " " + code).lower() else False
        dept_codes = _clean_str(item.get("department_codes") or item.get("department_code")).upper()
        batch_name = _clean_str(item.get("batch_name"))
        cleaned["subjects"].append({
            "name": name or code,
            "code": code or name[:8].upper().replace(" ", ""),
            "hours_per_week": hours if hours is not None else "",
            "credits": credits_val if credits_val is not None else "",
            "requires_lab": req_lab,
            "department_codes": dept_codes,
            "batch_name": batch_name
        })

    # 6. Faculty: {name, email, department_code}
    # NEVER generate fake @institution.edu or dummy emails!
    for item in data.get("faculty", []):
        if not isinstance(item, dict):
            continue
        name = _clean_str(item.get("name"))
        if not name or len(name) < 2:
            continue
        if _is_boilerplate_word(name):
            continue
        clean_name_tokens = set(re.sub(r'[^a-z ]', ' ', name.lower()).split()) - {"of", "the", "and", "&", "for"}
        if clean_name_tokens and clean_name_tokens.issubset(IGNORABLE_SIGNATORIES_AND_BOILERPLATE):
            continue
        email = _clean_str(item.get("email")).lower()
        if email and ("@" not in email or "." not in email or "institution.edu" in email):
            email = ""
        dept_code = _clean_str(item.get("department_code")).upper()
        cleaned["faculty"].append({
            "name": name,
            "email": email,
            "department_code": dept_code
        })

    # 7. Mappings: {subject_code, class_name, class_section, faculty_email, room_code}
    for item in data.get("mappings", []):
        if not isinstance(item, dict):
            continue
        sub_code = _clean_str(item.get("subject_code") or item.get("subject_name")).upper()
        cls_name = _clean_str(item.get("class_name"))
        if not sub_code and not cls_name:
            continue
        cls_sec = _clean_str(item.get("class_section") or item.get("section"))
        fac_identifier = _clean_str(item.get("faculty_email") or item.get("faculty_name"))
        if "institution.edu" in fac_identifier.lower():
            fac_identifier = ""
        rm_code = _clean_str(item.get("room_code"))
        cleaned["mappings"].append({
            "subject_code": sub_code,
            "class_name": cls_name,
            "class_section": cls_sec,
            "faculty_email": fac_identifier,
            "room_code": rm_code
        })

    # Deduplicate each list
    for key in cleaned:
        cleaned[key] = _dedupe_extracted_list(cleaned[key])

    return cleaned



@router.post('/extract-academic-data')
async def extract_academic_data(
    file: UploadFile = File(...),
    qwen_api_key: Optional[str] = Form(None),
    db=Depends(get_tenant_db),
    _current_user: dict = Depends(get_admin_user),
):
    """
    Extract academic data from a document (image/PDF) using OCR and Qwen API concurrently.
    Returns a stream of NDJSON progress updates and the final merged structured entities.
    """
    from ...core.config import settings
    from ...services.document_constraints import extract_document_text, extract_pdf_tables_and_text
    import urllib.request
    import json
    import asyncio
    import io
    import threading
    from typing import Optional

    content = await file.read()
    if len(content) > settings.DOCUMENT_UPLOAD_MAX_FILE_BYTES:
        limit_mb = settings.DOCUMENT_UPLOAD_MAX_FILE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"{file.filename or 'Uploaded file'} is larger than the {limit_mb} MB limit.",
        )

    async def generate_progress():
        main_queue = asyncio.Queue()
        active_tasks = 0

        ext = (file.filename or "").lower().split(".")[-1]
        doc_text_result = {"text": "", "warnings": [], "extractor": "none"}
        extracted_data_result = {
            "departments": [], "batches": [], "classes": [], "rooms": [],
            "subjects": [], "faculty": [], "mappings": []
        }
        
        async def extraction_task():
            try:
                if ext == 'pdf':
                    await main_queue.put(("data", json.dumps({"status": "progress", "progress": 15, "message": "[PDF Table Extraction] Extracting timetable grids & layout with pdfplumber..."}) + "\n"))
                    table_text, table_warnings = await asyncio.to_thread(extract_pdf_tables_and_text, content)
                    doc_text_result["text"] = table_text
                    doc_text_result["warnings"] = list(table_warnings)
                    doc_text_result["extractor"] = "pdf-table-extractor"
                    await main_queue.put(("data", json.dumps({"status": "log", "text": f"\n[PDF Table Extraction] Extracted {len(table_text)} characters across structured tables.\n"}) + "\n"))
                else:
                    await main_queue.put(("data", json.dumps({"status": "progress", "progress": 15, "message": "[Document Parser] Extracting document text..."}) + "\n"))
                    doc = await asyncio.to_thread(
                        extract_document_text,
                        file.filename or "uploaded-file",
                        content,
                        file.content_type,
                        max_chars=settings.DOCUMENT_TEXT_MAX_CHARS,
                        ocr_max_pages=settings.DOCUMENT_OCR_MAX_PAGES,
                    )
                    doc_text_result["text"] = doc.text
                    doc_text_result["warnings"] = list(doc.warnings)
                    doc_text_result["extractor"] = doc.extractor
                    await main_queue.put(("data", json.dumps({"status": "log", "text": f"\n[Document Parser] Extracted {len(doc.text)} characters.\n"}) + "\n"))
            except Exception as e:
                await main_queue.put(("data", json.dumps({"status": "log", "text": f"\n[Extraction Error] Failed: {e}\n"}) + "\n"))
            finally:
                if not doc_text_result["text"]:
                    doc_text_result["text"] = " " # unblock qwen
                await main_queue.put(("task_done", "extraction"))

        async def qwen_task():
            try:
                active_key = qwen_api_key or settings.active_document_analysis_api_key or "ollama"
                model_name = settings.active_document_analysis_model or "qwen3:1.7b"
                api_base = (settings.active_document_analysis_api_base or "http://localhost:11434/v1").rstrip("/")
                timeout = max(settings.DOCUMENT_ANALYSIS_TIMEOUT_SECONDS, 120)

                # Wait for extraction task to finish
                while not doc_text_result["text"]:
                    await asyncio.sleep(0.3)

                extracted_text = doc_text_result["text"].strip()
                if not extracted_text:
                    await main_queue.put(("data", json.dumps({"status": "log", "text": "\n[Qwen3:1.7B] No timetable data found in document to process.\n"}) + "\n"))
                    return

                chunks = _split_text_into_chunks(extracted_text, 5000)

                for i, chunk in enumerate(chunks):
                    progress_pct = 30 + int(60 * (i / len(chunks)))
                    await main_queue.put(("data", json.dumps({"status": "progress", "progress": progress_pct, "message": f"[Qwen3:1.7B] Analyzing part {i+1}/{len(chunks)}..."}) + "\n"))
                    
                    messages = [
                        {"role": "system", "content": ACADEMIC_EXTRACTOR_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                "Extract ONLY the real academic scheduling entities from the document text below that match our database fields (departments, batches, classes, rooms, subjects, faculty, mappings).\n"
                                "Completely ignore administrative boilerplate, college headers, exam rules, and signatures.\n"
                                "CRITICAL: Leave any empty/missing field as \"\" or null. NEVER generate mock data, placeholder emails, default durations, or dummy values.\n"
                                "Return ONLY valid raw JSON matching the schema.\n\n"
                                f"{chunk}"
                            )
                        }
                    ]

                    payload = {
                        "model": model_name,
                        "stream": True,
                        "temperature": 0.0,
                        "max_tokens": 4096,
                        "response_format": {"type": "json_object"},
                        "messages": messages
                    }
                    endpoint = f"{api_base}/chat/completions" if not api_base.endswith("/chat/completions") else api_base

                    req_data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        endpoint,
                        data=req_data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    if active_key:
                        req.add_header("Authorization", f"Bearer {active_key}")

                    stream_queue = asyncio.Queue()
                    loop = asyncio.get_running_loop()
                    def run_sync_stream():
                        try:
                            with urllib.request.urlopen(req, timeout=timeout) as response:
                                for line in response:
                                    if line.strip():
                                        asyncio.run_coroutine_threadsafe(stream_queue.put(("stream_data", line)), loop)
                            asyncio.run_coroutine_threadsafe(stream_queue.put(("stream_done", None)), loop)
                        except Exception as e:
                            asyncio.run_coroutine_threadsafe(stream_queue.put(("stream_error", e)), loop)

                    threading.Thread(target=run_sync_stream, daemon=True).start()
                    
                    content_str = ""
                    while True:
                        msg_type, data = await stream_queue.get()
                        if msg_type == "stream_done":
                            break
                        elif msg_type == "stream_error":
                            raise data
                        elif msg_type == "stream_data":
                            try:
                                token = ""
                                data_str = data.decode("utf-8").strip() if isinstance(data, bytes) else data.strip()
                                if not data_str:
                                    continue
                                
                                if data_str.startswith("data: "):
                                    data_str = data_str[6:]
                                if data_str == "[DONE]":
                                    continue
                                
                                chunk_obj = json.loads(data_str)
                                choices = chunk_obj.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    token = delta.get("content", "")
                                
                                if token:
                                    content_str += token
                                    await main_queue.put(("data", json.dumps({"status": "log", "text": token}) + "\n"))
                            except Exception:
                                pass

                    content_str = content_str.strip()
                    import re as _re
                    content_str = _re.sub(r'<think>.*?</think>', '', content_str, flags=_re.DOTALL).strip()
                    content_str = _re.sub(r'^```(?:json)?\s*', '', content_str).strip()
                    content_str = _re.sub(r'\s*```$', '', content_str).strip()

                    parsed = None
                    try:
                        parsed = json.loads(content_str)
                    except json.JSONDecodeError:
                        json_start = content_str.find('{')
                        json_end = content_str.rfind('}')
                        if json_start != -1 and json_end != -1:
                            try:
                                parsed = json.loads(content_str[json_start:json_end + 1])
                            except json.JSONDecodeError as inner_e:
                                doc_text_result["warnings"].append(
                                    f"Chunk {i+1}: Qwen3:1.7B returned invalid JSON ({inner_e}). "
                                    "Try again or check file input."
                                )
                                continue
                        else:
                            doc_text_result["warnings"].append(f"Chunk {i+1}: Could not parse JSON from Qwen3:1.7B response.")
                            continue

                    if parsed:
                        for key in extracted_data_result.keys():
                            if key in parsed and isinstance(parsed[key], list):
                                extracted_data_result[key].extend(parsed[key])
                            elif key == "faculty" and "faculties" in parsed and isinstance(parsed["faculties"], list):
                                extracted_data_result["faculty"].extend(parsed["faculties"])
                            
            except urllib.error.HTTPError as http_err:
                error_body = http_err.read().decode("utf-8", errors="replace") if hasattr(http_err, 'read') else str(http_err)
                await main_queue.put(("data", json.dumps({"status": "error", "error": f"[Qwen3:1.7B] HTTP {http_err.code}: {error_body[:400]}"}) + "\n"))
            except urllib.error.URLError as url_err:
                await main_queue.put(("data", json.dumps({"status": "error", "error": f"[Qwen3:1.7B] Cannot connect to Ollama ({api_base}). Make sure Ollama is running (`ollama run qwen3:1.7b`). Reason: {url_err.reason}"}) + "\n"))
            except Exception as e:
                await main_queue.put(("data", json.dumps({"status": "error", "error": f"[Qwen3:1.7B] Error: {e}"}) + "\n"))
            finally:
                await main_queue.put(("task_done", "qwen"))

        try:
            await main_queue.put(("data", json.dumps({"status": "progress", "progress": 5, "message": f"Processing file: {file.filename} ({len(content)} bytes)"}) + "\n"))
            
            # Start Extraction and Qwen Tasks
            asyncio.create_task(extraction_task())
            active_tasks += 1
            
            asyncio.create_task(qwen_task())
            active_tasks += 1
                
            import sys
            # Consume from main_queue
            while active_tasks > 0 or not main_queue.empty():
                try:
                    msg_type, data = await asyncio.wait_for(main_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    if active_tasks == 0:
                        break
                    continue

                if msg_type == "data":
                    try:
                        parsed_data = json.loads(data.strip())
                        status = parsed_data.get("status")
                        if status == "log":
                            sys.stdout.write(parsed_data.get("text", ""))
                            sys.stdout.flush()
                        elif status == "progress":
                            print(f"\n[AI EXTRACTOR {parsed_data.get('progress')}%] {parsed_data.get('message')}", flush=True)
                        elif status == "error":
                            print(f"\n[AI EXTRACTOR ERROR] {parsed_data.get('error')}", flush=True)
                    except Exception:
                        pass
                    yield data
                elif msg_type == "task_done":
                    active_tasks -= 1
                    
            print("\n[AI EXTRACTOR 95%] Sanitizing, filtering, and aligning with database schema...", flush=True)
            yield json.dumps({"status": "progress", "progress": 95, "message": "Sanitizing, filtering, and aligning with database schema..."}) + "\n"

            # Strictly sanitize, filter administrative boilerplate, and align with DB fields (zero mock data)
            extracted_data_result = _sanitize_and_filter_extracted_entities(extracted_data_result)

            total_extracted = sum(len(v) for v in extracted_data_result.values())
            print(f"\n[AI EXTRACTOR SUCCESS] Extracted {total_extracted} valid items from {file.filename}\n", flush=True)

            yield json.dumps({
                "status": "success",
                "data": {
                    "extracted_data": extracted_data_result,
                    "warnings": doc_text_result["warnings"],
                    "filename": file.filename,
                    "extractor": doc_text_result["extractor"]
                }
            }) + "\n"

        except Exception as general_exc:
            print(f"\n[AI EXTRACTOR UNEXPECTED ERROR] {str(general_exc)}\n", flush=True)
            yield json.dumps({"status": "error", "error": f"Unexpected error: {str(general_exc)}"}) + "\n"
            
    return StreamingResponse(generate_progress(), media_type="application/x-ndjson")


@router.post('/download-filled-templates')
async def download_filled_templates(data: dict):
    """
    Generate and download a ZIP file of CSV templates pre-filled with the extracted data.
    """
    import csv
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for import_type in IMPORT_ORDER:
            headers = []
            if import_type == 'departments':
                headers = ['name', 'code']
            elif import_type == 'batches':
                headers = ['name', 'start_time', 'end_time', 'period_duration', 'break_times', 'lunch_break']
            elif import_type == 'rooms':
                headers = ['name', 'code', 'room_type', 'capacity', 'department_code']
            elif import_type == 'classes':
                headers = ['name', 'section', 'semester', 'student_count', 'department_code', 'batch_name', 'room_code']
            elif import_type == 'subjects':
                headers = ['name', 'code', 'hours_per_week', 'requires_lab', 'department_codes', 'batch_name']
            elif import_type == 'faculty':
                headers = ['name', 'email', 'department_code']
            elif import_type == 'mappings':
                headers = ['subject_code', 'class_name', 'class_section', 'faculty_email', 'room_code']

            items = data.get(import_type, [])
            if not items and import_type == 'faculty' and 'faculties' in data:
                items = data.get('faculties', [])

            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(headers)

            for item in items:
                row = []
                for h in headers:
                    val = item.get(h, '')
                    if isinstance(val, bool):
                        val = str(val).lower()
                    row.append(val)
                writer.writerow(row)

            csv_content = csv_buffer.getvalue()
            zip_file.writestr(f"{import_type}_template.csv", csv_content)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={
            'Content-Disposition': 'attachment; filename=extracted_academic_templates.zip',
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        }
    )


@router.post('/import-extracted-data')
async def import_extracted_data(data: dict, db=Depends(get_tenant_db), _current_user: dict = Depends(get_admin_user)):
    """
    Directly import the extracted JSON data into the database.
    Runs the existing CSV import handlers sequentially to ensure integrity.
    """
    results = {}
    total_imported = 0
    total_skipped = 0
    total_warnings = 0
    total_errors = 0

    for import_type in IMPORT_ORDER:
        items = data.get(import_type, [])
        if not items and import_type == 'faculty' and 'faculties' in data:
            items = data.get('faculties', [])

        if not items:
            continue

        rows = []
        for index, item in enumerate(items, start=1):
            row_dict = {}
            for k, v in item.items():
                row_dict[str(k)] = str(v) if v is not None else ""
            rows.append((index, row_dict))

        result = _empty_result(import_type)
        try:
            IMPORT_HANDLERS[import_type](db, rows, result)
            total_imported += result.get('imported', 0)
            total_skipped += result.get('skipped', 0)
            total_warnings += result.get('warning_count', 0)
            total_errors += result.get('error_count', 0)
            results[import_type] = result
        except Exception as e:
            results[import_type] = {
                "status": "failed",
                "message": f"Import failed: {str(e)}"
            }
            total_errors += 1

    return {
        "status": "completed",
        "imported": total_imported,
        "skipped": total_skipped,
        "warning_count": total_warnings,
        "error_count": total_errors,
        "results": results
    }

def _extract_excel_data(content: bytes) -> dict:
    import openpyxl
    import io

    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    
    extracted_data_result = {
        "departments": [], "batches": [], "classes": [], "rooms": [],
        "subjects": [], "faculty": [], "mappings": []
    }
    warnings = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        
        # Guess import type from sheet name
        import_type = _guess_import_type(sheet_name + ".csv")
        if not import_type or import_type not in extracted_data_result:
            warnings.append(f"Sheet '{sheet_name}' was skipped because it did not match any known import type.")
            continue

        # Extract rows
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            warnings.append(f"Sheet '{sheet_name}' is empty.")
            continue

        # Find header row (first row with any data)
        header_row_idx = -1
        for i, row in enumerate(rows):
            if any(cell is not None and str(cell).strip() != "" for cell in row):
                header_row_idx = i
                break
        
        if header_row_idx == -1:
            warnings.append(f"Sheet '{sheet_name}' has no headers.")
            continue

        headers = [str(cell).strip() if cell is not None else "" for cell in rows[header_row_idx]]
        
        try:
            # map_headers throws HTTPException if required headers are missing
            header_mapping = map_headers(headers, import_type)
        except HTTPException as e:
            warnings.append(f"Sheet '{sheet_name}': {e.detail}")
            continue

        # Process data rows
        for row_idx in range(header_row_idx + 1, len(rows)):
            row = rows[row_idx]
            
            # Skip if row is completely empty
            if not any(cell is not None and str(cell).strip() != "" for cell in row):
                continue

            raw_row = {}
            for col_idx, header in enumerate(headers):
                if col_idx < len(row):
                    cell_val = row[col_idx]
                    raw_row[header] = str(cell_val).strip() if cell_val is not None else ""
                else:
                    raw_row[header] = ""

            norm_row = {}
            for target_key, uploaded_key in header_mapping.items():
                norm_row[target_key] = raw_row.get(uploaded_key, '').strip()

            extracted_data_result[import_type].append(norm_row)

    # Deduplicate and filter extracted lists strictly to database schema
    extracted_data_result = _sanitize_and_filter_extracted_entities(extracted_data_result)

    return {
        "extracted_data": extracted_data_result,
        "warnings": warnings,
        "extractor": "excel"
    }


@router.post('/extract-excel-data')
async def extract_excel_data(
    file: UploadFile = File(...),
    db=Depends(get_tenant_db),
    _current_user: dict = Depends(get_admin_user),
):
    """
    Extract data from an uploaded Excel file, strictly mapping to templates without AI hallucinations.
    Skips empty rows and maps each sheet.
    """
    import asyncio

    if file.filename and not (file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls')):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are supported for Excel extraction.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        data = await asyncio.to_thread(_extract_excel_data, content)
        data["filename"] = file.filename
        
        return {
            "status": "success",
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Excel file: {str(e)}")

