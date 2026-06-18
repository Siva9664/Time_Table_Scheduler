from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import csv
import os
import io
import zipfile
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from ...core.security import get_admin_user, get_tenant_db

router = APIRouter()


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get('/templates')
async def download_templates():
    """Create a ZIP file containing all CSV templates in csv_templates folder."""
    # Base directory of the backend project
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    templates_dir = os.path.join(base_dir, 'csv_templates')
    
    if not os.path.exists(templates_dir):
        raise HTTPException(status_code=404, detail="csv_templates folder not found.")

    # Create zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                if file.endswith('.csv') or file.lower() == 'readme.md':
                    file_path = os.path.join(root, file)
                    # Add file to zip archive under its filename
                    zip_file.write(file_path, arcname=file)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={
            'Content-Disposition': 'attachment; filename=csv_templates.zip',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )



COMMON_ALIASES = {
    'subject_code': ['subjectcode', 'subcode', 'code', 'subject_id', 'sub_id', 'subject code'],
    'class_name': ['classname', 'class', 'clsname', 'cls_name', 'batch', 'class name'],
    'class_section': ['classsection', 'section', 'sec', 'class_sec', 'cls_sec', 'class section', 'class_section'],
    'faculty_email': ['facultyemail', 'email', 'facemail', 'fac_email', 'instructor_email', 'teacher_email', 'faculty email', 'faculty_email'],
    'department_code': ['departmentcode', 'deptcode', 'dept_code', 'department_id', 'dept_id', 'department', 'department code', 'department_code'],
    'department_codes': ['departmentcodes', 'deptcodes', 'dept_codes', 'departments', 'department codes', 'department_codes'],
    'batch_name': ['batchname', 'batch', 'batch_id', 'semester', 'batch name', 'batch_name'],
    'hours_per_week': ['hoursperweek', 'hours', 'weekly_hours', 'periods', 'hours per week', 'hours_per_week'],
    'requires_lab': ['requireslab', 'lab', 'islab', 'is_lab', 'requires_lab_session', 'requires lab', 'requires_lab'],
    'max_hours_per_week': ['maxhoursperweek', 'max_hours', 'weekly_limit', 'max hours per week', 'max_hours_per_week'],
    'student_count': ['studentcount', 'students', 'strength', 'size', 'class_size', 'student count', 'student_count'],
    'name': ['name', 'title', 'full_name', 'full name'],
    'code': ['code', 'id', 'identifier'],
    'email': ['email', 'email_address', 'email address'],
    'start_time': ['starttime', 'start', 'start_time', 'start time'],
    'end_time': ['endtime', 'end', 'end_time', 'end time'],
    'period_duration': ['periodduration', 'duration', 'period_duration', 'period duration'],
    'room_type': ['roomtype', 'type', 'room_type', 'room type'],
    'capacity': ['capacity', 'seats', 'strength', 'room_capacity', 'room capacity'],
    'room_code': ['roomcode', 'room', 'room_id', 'assigned_room', 'room code', 'room_code', 'default_room'],
    'section': ['section', 'sec', 'classsection', 'class_section', 'class section'],
    'semester': ['semester', 'sem', 'term'],
    'credits': ['credits', 'credit', 'credit_hours', 'credit hours'],
    'break_times': ['breaktimes', 'breaks', 'break_times', 'break times'],
    'lunch_break': ['lunchbreak', 'lunch', 'lunch_break', 'lunch break'],
    'unavailable_slots': ['unavailableslots', 'unavailable', 'unavailable_slots', 'unavailable slots', 'blocked_slots', 'blocked slots'],
}

EXPECTED_HEADERS = {
    'departments': ['name', 'code'],
    'batches': ['name', 'start_time', 'end_time', 'period_duration', 'break_times', 'lunch_break'],
    'classes': ['name', 'section', 'semester', 'student_count', 'department_code', 'batch_name', 'room_code'],
    'rooms': ['name', 'code', 'room_type', 'capacity', 'department_code'],
    'subjects': ['name', 'code', 'hours_per_week', 'credits', 'requires_lab', 'department_codes', 'batch_name'],
    'faculty': ['name', 'email', 'department_code', 'max_hours_per_week', 'unavailable_slots'],
    'mappings': ['subject_code', 'class_name', 'class_section', 'faculty_email', 'room_code']
}

ALLOWED_IMPORT_TYPES = {'departments','batches','classes','rooms','subjects','faculty','mappings'}
IMPORT_ORDER = ['departments', 'batches', 'rooms', 'classes', 'subjects', 'faculty', 'mappings']
MAX_ISSUES = 50

REQUIRED_HEADERS = {
    'departments': ['name', 'code'],
    'batches': ['name'],
    'classes': ['name'],
    'rooms': ['name'],
    'subjects': ['name', 'code'],
    'faculty': ['name', 'email'],
    'mappings': ['subject_code', 'class_name', 'faculty_email']
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
            cost = 0 if s1_norm[i-1] == s2_norm[j-1] else 1
            matrix[i][j] = min(
                matrix[i-1][j] + 1,
                matrix[i][j-1] + 1,
                matrix[i-1][j-1] + cost
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
            detail=f"Duplicate CSV column(s): {', '.join(duplicate_headers)}. Please keep each column name unique."
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
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252'):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Could not decode CSV file. Please upload a UTF-8 CSV.")


def _read_csv_rows(content: bytes) -> Tuple[List[str], List[Tuple[int, Dict[str, str]]]]:
    text = _decode_csv_content(content)
    reader = csv.DictReader(io.StringIO(text, newline=''))
    headers = [h.strip() for h in (reader.fieldnames or []) if h and h.strip()]
    rows = []
    for row_number, row in enumerate(reader, start=2):
        cleaned = {}
        for key, value in row.items():
            key = (key or '').strip()
            if not key:
                continue
            if isinstance(value, list):
                value = ';'.join(str(item) for item in value if item is not None)
            cleaned[key] = ('' if value is None else str(value)).strip()
        rows.append((row_number, cleaned))
    return headers, rows


def _guess_import_type(filename: str) -> Optional[str]:
    base_name = os.path.basename(filename or '').lower()
    if not base_name.endswith('.csv'):
        return None

    stem = os.path.splitext(base_name)[0]
    stem = re.sub(r'\s*\(\d+\)$', '', stem)
    for suffix in ('_template', '-template', ' template'):
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]

    aliases = {
        'department': 'departments',
        'departments': 'departments',
        'batch': 'batches',
        'batches': 'batches',
        'class': 'classes',
        'classes': 'classes',
        'room': 'rooms',
        'rooms': 'rooms',
        'subject': 'subjects',
        'subjects': 'subjects',
        'faculty': 'faculty',
        'faculties': 'faculty',
        'mapping': 'mappings',
        'mappings': 'mappings',
        'faculty_mapping': 'mappings',
        'faculty_mappings': 'mappings',
    }
    normalized_stem = re.sub(r'[^a-z0-9]+', '_', stem).strip('_')
    if normalized_stem in aliases:
        return aliases[normalized_stem]

    tokens = [token for token in normalized_stem.split('_') if token]
    token_set = set(tokens)
    if 'faculty' in token_set and ({'mapping', 'mappings'} & token_set):
        return 'mappings'
    for token in tokens:
        if token in aliases:
            return aliases[token]
    return None


def _empty_result(import_type: str) -> Dict[str, Any]:
    return {
        'imported': 0,
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'type': import_type,
        'warnings': [],
        'errors': [],
        'warning_count': 0,
        'error_count': 0,
    }


def _record_issue(result: Dict[str, Any], bucket: str, row_number: Optional[int], message: str):
    count_key = 'error_count' if bucket == 'errors' else 'warning_count'
    result[count_key] += 1
    if len(result[bucket]) < MAX_ISSUES:
        issue = {'message': message}
        if row_number is not None:
            issue['row'] = row_number
        result[bucket].append(issue)


def _row_value(row: Dict[str, str], key: str) -> str:
    return (row.get(key) or '').strip()


def _require_value(row: Dict[str, str], key: str, row_number: int, result: Dict[str, Any]) -> Optional[str]:
    value = _row_value(row, key)
    if not value:
        _record_issue(result, 'errors', row_number, f"Missing required value '{key}'.")
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
    if value == '':
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
        min_hint = f" greater than or equal to {min_value}" if min_value is not None else ""
        _record_issue(result, 'warnings', row_number, f"Invalid integer for '{field}'{min_hint}: '{value}'. Used {default}.")
        return default


def _parse_bool(value: str, result: Dict[str, Any], row_number: int, field: str, default: bool = False) -> bool:
    if value == '':
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'y', 'on', 'lab', 'required'}:
        return True
    if normalized in {'0', 'false', 'no', 'n', 'off'}:
        return False
    _record_issue(result, 'warnings', row_number, f"Invalid boolean for '{field}': '{value}'. Used {default}.")
    return default


def _parse_time(value: str, default: str, result: Dict[str, Any], row_number: int, field: str) -> str:
    if value == '':
        return default
    match = re.match(r'^(\d{1,2}):(\d{2})$', value.strip())
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    _record_issue(result, 'warnings', row_number, f"Invalid time for '{field}': '{value}'. Used {default}.")
    return default


def _parse_json_field(
    value: str,
    default: Any,
    expected_type: type,
    result: Dict[str, Any],
    row_number: int,
    field: str,
) -> Any:
    if value == '':
        return default
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        _record_issue(result, 'warnings', row_number, f"Invalid JSON for '{field}'. Used default value.")
        return default
    if not isinstance(parsed, expected_type):
        _record_issue(result, 'warnings', row_number, f"JSON field '{field}' must be {expected_type.__name__}. Used default value.")
        return default
    return parsed


def _lookup_value(value: str) -> str:
    return (value or '').strip().casefold()


def _find_one_by_any(db, collection_name: str, fields: List[str], value: str) -> Optional[dict]:
    value = (value or '').strip()
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
            if _lookup_value(str(doc.get(field) or '')) == needle:
                return doc
    return None


def _find_department(db, code_or_name: str) -> Optional[dict]:
    return _find_one_by_any(db, 'departments', ['code', 'name'], code_or_name)


def _find_batch(db, name: str) -> Optional[dict]:
    return _find_one_by_any(db, 'batches', ['name'], name)


def _find_room(db, code_or_name: str) -> Optional[dict]:
    return _find_one_by_any(db, 'rooms', ['code', 'name'], code_or_name)


def _find_faculty(db, email: str) -> Optional[dict]:
    return _find_one_by_any(db, 'faculty', ['email'], email)


def _find_class(db, name: str, section: str = '') -> Optional[dict]:
    name = (name or '').strip()
    section = (section or '').strip()
    if not name:
        return None

    query = {'name': name}
    if section:
        query['section'] = section
    doc = db['classes'].find_one(query)
    if doc:
        return doc

    name_norm = _lookup_value(name)
    section_norm = _lookup_value(section)
    for class_doc in db['classes'].find({}):
        if _lookup_value(str(class_doc.get('name') or '')) != name_norm:
            continue
        if section and _lookup_value(str(class_doc.get('section') or '')) != section_norm:
            continue
        return class_doc
    return None


def _find_core_subject(db, code: str) -> Optional[dict]:
    code = (code or '').strip()
    if not code:
        return None

    exact_queries = [
        {'code': code, 'source_subject_id': {'$exists': False}, 'class_id': None},
        {'code': code, 'source_subject_id': {'$exists': False}},
        {'code': code},
    ]
    for query in exact_queries:
        doc = db['subjects'].find_one(query)
        if doc:
            return doc

    code_norm = _lookup_value(code)
    fallback = None
    for subject in db['subjects'].find({}):
        if _lookup_value(str(subject.get('code') or '')) != code_norm:
            continue
        if subject.get('source_subject_id'):
            continue
        if not subject.get('class_id'):
            return subject
        fallback = fallback or subject
    return fallback


def _find_existing_subject_mapping(db, subject: dict, source_id: str, class_id: str) -> Optional[dict]:
    for existing in db['subjects'].find({'class_id': class_id}):
        if str(existing.get('source_subject_id') or '') == str(source_id):
            return existing
        if str(existing.get('_id')) == str(source_id):
            return existing
        if (
            not existing.get('source_subject_id')
            and existing.get('code') == subject.get('code')
            and existing.get('name') == subject.get('name')
            and existing.get('requires_lab', False) == subject.get('requires_lab', False)
        ):
            return existing
    return None


def _mark_saved(result: Dict[str, Any], inserted: bool):
    result['imported'] += 1
    result['inserted' if inserted else 'updated'] += 1


def _save_document(db, collection_name: str, existing: Optional[dict], document: dict, result: Dict[str, Any], on_insert: Optional[dict] = None):
    now = _utcnow()
    update_doc = {**document, 'updated_at': now}
    if existing:
        db[collection_name].update_one({'_id': existing['_id']}, {'$set': update_doc})
        _mark_saved(result, inserted=False)
        return existing['_id']

    insert_doc = {**(on_insert or {}), **document, 'created_at': now}
    insert_result = db[collection_name].insert_one(insert_doc)
    _mark_saved(result, inserted=True)
    return insert_result.inserted_id


def _split_codes(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r'[;,]', value) if item.strip()]


def _normalize_rows(headers: List[str], raw_rows: List[Tuple[int, Dict[str, str]]], import_type: str, result: Dict[str, Any]) -> List[Tuple[int, Dict[str, str]]]:
    if not headers:
        raise HTTPException(status_code=400, detail="The uploaded CSV has no header row.")
    if not raw_rows:
        result['message'] = 'The uploaded CSV file is empty.'
        return []

    header_mapping = map_headers(headers, import_type)
    rows = []
    for row_number, raw_row in raw_rows:
        norm_row = {}
        for target_key, uploaded_key in header_mapping.items():
            norm_row[target_key] = raw_row.get(uploaded_key, '').strip()
        if not any(value for value in norm_row.values()):
            result['skipped'] += 1
            continue
        rows.append((row_number, norm_row))
    if not rows:
        result['message'] = 'The uploaded CSV file has no data rows.'
    return rows


def _import_departments(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, 'name', row_number, result)
        code = _require_value(row, 'code', row_number, result)
        if not name or not code:
            result['skipped'] += 1
            continue
        existing = _find_department(db, code)
        _save_document(db, 'departments', existing, {'name': name, 'code': code}, result)


def _import_batches(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, 'name', row_number, result)
        if not name:
            result['skipped'] += 1
            continue
        document = {
            'name': name,
            'start_time': _parse_time(_row_value(row, 'start_time'), '09:00', result, row_number, 'start_time'),
            'end_time': _parse_time(_row_value(row, 'end_time'), '17:00', result, row_number, 'end_time'),
            'period_duration': _parse_int(_row_value(row, 'period_duration'), 60, result, row_number, 'period_duration', min_value=1),
            'break_times': _parse_json_field(_row_value(row, 'break_times'), [], list, result, row_number, 'break_times'),
            'lunch_break': _parse_json_field(_row_value(row, 'lunch_break'), {}, dict, result, row_number, 'lunch_break'),
        }
        existing = _find_batch(db, name)
        _save_document(db, 'batches', existing, document, result)


def _import_rooms(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, 'name', row_number, result)
        if not name:
            result['skipped'] += 1
            continue
        dept = _find_department(db, _row_value(row, 'department_code'))
        if _row_value(row, 'department_code') and not dept:
            _record_issue(result, 'warnings', row_number, f"Department '{_row_value(row, 'department_code')}' not found for room '{name}'.")

        room_type = (_row_value(row, 'room_type') or 'lecture').lower()
        if room_type not in {'lecture', 'lab', 'seminar'}:
            _record_issue(result, 'warnings', row_number, f"Invalid room_type '{room_type}' for room '{name}'. Used lecture.")
            room_type = 'lecture'

        code = _row_value(row, 'code')
        document = {
            'name': name,
            'code': code,
            'room_type': room_type,
            'capacity': _parse_int(_row_value(row, 'capacity'), 0, result, row_number, 'capacity', min_value=0),
            'department_id': str(dept['_id']) if dept else None,
        }
        existing = _find_room(db, code or name)
        _save_document(db, 'rooms', existing, document, result)


def _import_classes(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, 'name', row_number, result)
        if not name:
            result['skipped'] += 1
            continue

        dept = _find_department(db, _row_value(row, 'department_code'))
        batch = _find_batch(db, _row_value(row, 'batch_name'))
        room = _find_room(db, _row_value(row, 'room_code'))
        if _row_value(row, 'department_code') and not dept:
            _record_issue(result, 'warnings', row_number, f"Department '{_row_value(row, 'department_code')}' not found for class '{name}'.")
        if _row_value(row, 'batch_name') and not batch:
            _record_issue(result, 'warnings', row_number, f"Batch '{_row_value(row, 'batch_name')}' not found for class '{name}'.")
        if _row_value(row, 'room_code') and not room:
            _record_issue(result, 'warnings', row_number, f"Room '{_row_value(row, 'room_code')}' not found for class '{name}'.")

        section = _row_value(row, 'section')
        document = {
            'name': name,
            'section': section,
            'semester': _parse_int(_row_value(row, 'semester'), 1, result, row_number, 'semester', min_value=1),
            'student_count': _parse_int(_row_value(row, 'student_count'), 0, result, row_number, 'student_count', min_value=0),
            'department_id': str(dept['_id']) if dept else None,
            'batch_id': str(batch['_id']) if batch else None,
            'room_id': str(room['_id']) if room else None,
        }
        existing = _find_class(db, name, section)
        _save_document(db, 'classes', existing, document, result)


def _import_subjects(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, 'name', row_number, result)
        code = _require_value(row, 'code', row_number, result)
        if not name or not code:
            result['skipped'] += 1
            continue

        department_ids = []
        for department_code in _split_codes(_row_value(row, 'department_codes')):
            dept = _find_department(db, department_code)
            if dept:
                department_ids.append(str(dept['_id']))
            else:
                _record_issue(result, 'warnings', row_number, f"Department '{department_code}' not found for subject '{code}'.")

        batch = _find_batch(db, _row_value(row, 'batch_name'))
        if _row_value(row, 'batch_name') and not batch:
            _record_issue(result, 'warnings', row_number, f"Batch '{_row_value(row, 'batch_name')}' not found for subject '{code}'.")

        document = {
            'name': name,
            'code': code,
            'hours_per_week': _parse_int(_row_value(row, 'hours_per_week'), 0, result, row_number, 'hours_per_week', min_value=0),
            'credits': _parse_int(_row_value(row, 'credits'), 3, result, row_number, 'credits', min_value=0),
            'requires_lab': _parse_bool(_row_value(row, 'requires_lab'), result, row_number, 'requires_lab'),
            'department_ids': department_ids,
            'department_id': department_ids[0] if department_ids else None,
            'batch_id': str(batch['_id']) if batch else None,
        }
        existing = _find_core_subject(db, code)
        _save_document(db, 'subjects', existing, document, result, on_insert={'class_id': None, 'faculty_id': None})


def _import_faculty(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        name = _require_value(row, 'name', row_number, result)
        email = _require_value(row, 'email', row_number, result)
        if not name or not email:
            result['skipped'] += 1
            continue

        email = email.lower()
        dept = _find_department(db, _row_value(row, 'department_code'))
        if _row_value(row, 'department_code') and not dept:
            _record_issue(result, 'warnings', row_number, f"Department '{_row_value(row, 'department_code')}' not found for faculty '{email}'.")

        document = {
            'name': name,
            'email': email,
            'department_id': str(dept['_id']) if dept else None,
            'max_hours_per_week': _parse_int(_row_value(row, 'max_hours_per_week'), 20, result, row_number, 'max_hours_per_week', min_value=0),
            'unavailable_slots': _parse_json_field(_row_value(row, 'unavailable_slots'), [], list, result, row_number, 'unavailable_slots'),
        }
        existing = _find_faculty(db, email)
        _save_document(db, 'faculty', existing, document, result)


def _import_mappings(db, rows: List[Tuple[int, Dict[str, str]]], result: Dict[str, Any]):
    for row_number, row in rows:
        subject_code = _require_value(row, 'subject_code', row_number, result)
        class_name = _require_value(row, 'class_name', row_number, result)
        faculty_email = _require_value(row, 'faculty_email', row_number, result)
        if not subject_code or not class_name or not faculty_email:
            result['skipped'] += 1
            continue

        subj = _find_core_subject(db, subject_code)
        cls = _find_class(db, class_name, _row_value(row, 'class_section'))
        fac = _find_faculty(db, faculty_email.lower())
        room = _find_room(db, _row_value(row, 'room_code')) if _row_value(row, 'room_code') else None

        missing = []
        if not subj:
            missing.append(f"subject '{subject_code}'")
        if not cls:
            missing.append(f"class '{class_name}'")
        if not fac:
            missing.append(f"faculty '{faculty_email}'")
        if missing:
            result['skipped'] += 1
            _record_issue(result, 'errors', row_number, f"Could not apply mapping because {', '.join(missing)} was not found.")
            continue
        if _row_value(row, 'room_code') and not room:
            _record_issue(result, 'warnings', row_number, f"Room '{_row_value(row, 'room_code')}' not found for mapping '{subject_code}' -> '{class_name}'.")

        class_id = str(cls['_id'])
        faculty_id = str(fac['_id'])
        if room:
            db['classes'].update_one(
                {'_id': cls['_id']},
                {'$set': {'room_id': str(room['_id']), 'updated_at': _utcnow()}}
            )

        source_id = subj.get('source_subject_id') or str(subj['_id'])
        document = {
            'name': subj.get('name') or '',
            'code': subj.get('code') or '',
            'hours_per_week': subj.get('hours_per_week'),
            'credits': subj.get('credits', 3),
            'requires_lab': subj.get('requires_lab', False),
            'department_id': subj.get('department_id'),
            'department_ids': subj.get('department_ids') or ([subj.get('department_id')] if subj.get('department_id') else []),
            'batch_id': subj.get('batch_id'),
            'class_id': class_id,
            'faculty_id': faculty_id,
            'source_subject_id': source_id,
        }
        existing = _find_existing_subject_mapping(db, subj, source_id, class_id)
        _save_document(db, 'subjects', existing, document, result)


IMPORT_HANDLERS = {
    'departments': _import_departments,
    'batches': _import_batches,
    'classes': _import_classes,
    'rooms': _import_rooms,
    'subjects': _import_subjects,
    'faculty': _import_faculty,
    'mappings': _import_mappings,
}


def _import_csv_data(import_type: str, content: bytes, db) -> Dict[str, Any]:
    result = _empty_result(import_type)
    headers, raw_rows = _read_csv_rows(content)
    rows = _normalize_rows(headers, raw_rows, import_type, result)
    if rows:
        IMPORT_HANDLERS[import_type](db, rows, result)
    if result['error_count'] > len(result['errors']):
        result['message'] = f"{result.get('message', '')} Showing first {MAX_ISSUES} errors.".strip()
    if result['warning_count'] > len(result['warnings']):
        result['message'] = f"{result.get('message', '')} Showing first {MAX_ISSUES} warnings.".strip()
    if 'message' not in result:
        parts = [f"Imported {result['imported']} {import_type} row(s)."]
        if result['skipped']:
            parts.append(f"Skipped {result['skipped']} row(s).")
        if result['warning_count']:
            parts.append(f"{result['warning_count']} warning(s).")
        if result['error_count']:
            parts.append(f"{result['error_count']} error(s).")
        result['message'] = ' '.join(parts)
    return result


async def _import_upload_file(import_type: str, file: UploadFile, db) -> Dict[str, Any]:
    import_type = (import_type or '').strip().lower()
    if import_type not in ALLOWED_IMPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported import type: {import_type}")
    if file.filename and not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    content = await file.read()
    if not content:
        result = _empty_result(import_type)
        result['message'] = 'The uploaded CSV file is empty.'
        return result

    try:
        return _import_csv_data(import_type, content, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV Parsing Error: {str(e)}")


@router.post('/upload')
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


@router.post('/upload-folder')
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
            results.append({
                'file': file.filename,
                'type': None,
                'status': 'skipped',
                'message': 'Not a recognized CSV import file.'
            })
            continue
        if import_type in file_by_type:
            results.append({
                'file': file.filename,
                'type': import_type,
                'status': 'skipped',
                'message': f"Duplicate {import_type} CSV. The first matching file was used."
            })
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
            imported = int(data.get('imported') or 0)
            total_imported += imported
            processed += 1
            status = 'partial' if data.get('error_count') else 'success'
            results.append({
                'file': file.filename,
                'type': import_type,
                'status': status,
                'imported': imported,
                'inserted': data.get('inserted', 0),
                'updated': data.get('updated', 0),
                'skipped': data.get('skipped', 0),
                'warnings': data.get('warnings', []),
                'errors': data.get('errors', []),
                'warning_count': data.get('warning_count', 0),
                'error_count': data.get('error_count', 0),
                'message': data.get('message') or f"Imported {imported} {import_type}."
            })
        except HTTPException as exc:
            results.append({
                'file': file.filename,
                'type': import_type,
                'status': 'failed',
                'message': exc.detail
            })
        except Exception as exc:
            results.append({
                'file': file.filename,
                'type': import_type,
                'status': 'failed',
                'message': str(exc)
            })

    missing = [import_type for import_type in IMPORT_ORDER if import_type not in file_by_type]
    failed = [item for item in results if item.get('status') == 'failed']
    partial = [item for item in results if item.get('status') == 'partial']

    return JSONResponse({
        'imported': total_imported,
        'processed': processed,
        'failed': len(failed),
        'partial': len(partial),
        'missing': missing,
        'results': results
    })
