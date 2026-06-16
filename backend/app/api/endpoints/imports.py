from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import csv
import tempfile
import os
import io
import zipfile
from typing import List, Optional, Tuple
from datetime import datetime

from ...database.database import get_db

router = APIRouter()


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
    'room_code': ['roomcode', 'room', 'room_id', 'assigned_room', 'room code', 'room_code', 'default_room']
}

EXPECTED_HEADERS = {
    'departments': ['name', 'code'],
    'batches': ['name', 'start_time', 'end_time', 'period_duration'],
    'classes': ['name', 'section', 'semester', 'student_count', 'department_code', 'batch_name', 'room_code'],
    'rooms': ['name', 'code', 'room_type', 'capacity', 'department_code'],
    'subjects': ['name', 'code', 'hours_per_week', 'requires_lab', 'department_codes', 'batch_name'],
    'faculty': ['name', 'email', 'department_code', 'max_hours_per_week'],
    'mappings': ['subject_code', 'class_name', 'class_section', 'faculty_email', 'room_code']
}

REQUIRED_HEADERS = {
    'departments': ['name', 'code'],
    'batches': ['name'],
    'classes': ['name'],
    'rooms': ['name'],
    'subjects': ['name', 'code'],
    'faculty': ['name', 'email'],
    'mappings': ['subject_code']
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

    for target in expected:
        best_score = 0.0
        best_header = None
        
        # 1. Match via defined aliases
        target_aliases = COMMON_ALIASES.get(target, [])
        for h in uploaded_headers:
            h_norm = normalize_string(h)
            if h_norm in [normalize_string(a) for a in target_aliases] or h_norm == normalize_string(target):
                best_score = 1.0
                best_header = h
                break
        
        # 2. Fallback to similarity
        if best_score < 1.0:
            for h in uploaded_headers:
                score = similarity_score(h, target)
                if score > best_score:
                    best_score = score
                    best_header = h
                    
        # Apply matched header if confidence is high enough
        if best_header and best_score >= 0.65:
            mapping[target] = best_header
            
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


def _read_csv_rows(path: str) -> Tuple[List[str], List[dict]]:
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in (reader.fieldnames or []) if h]
        rows = []
        for row in reader:
            cleaned = { (k or '').strip(): (v or '').strip() for k, v in row.items() }
            rows.append(cleaned)
        return headers, rows


@router.post('/upload')
async def upload_csv(type: str = Form(...), file: UploadFile = File(...), db=Depends(get_db)):
    """Upload a CSV and import data. Form param `type` selects which importer to run.
    Supported types: departments, batches, classes, rooms, subjects, faculty, mappings
    """
    allowed = {'departments','batches','classes','rooms','subjects','faculty','mappings'}
    if type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported import type: {type}")

    suffix = os.path.splitext(file.filename)[1] or '.csv'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        headers, raw_rows = _read_csv_rows(tmp_path)
        if not raw_rows:
            return JSONResponse({'imported': 0, 'type': type, 'message': 'The uploaded CSV file is empty.'})
            
        header_mapping = map_headers(headers, type)
        
        # Build normalized rows where keys match standard expected names
        rows = []
        for r in raw_rows:
            norm_row = {}
            for target_key, uploaded_key in header_mapping.items():
                norm_row[target_key] = r.get(uploaded_key, '')
            rows.append(norm_row)
            
        count = 0
        if type == 'departments':
            docs = []
            for row in rows:
                docs.append({'name': row.get('name') or '', 'code': row.get('code') or ''})
            if docs:
                res = db['departments'].insert_many(docs)
                count = len(res.inserted_ids)

        elif type == 'batches':
            docs = []
            for row in rows:
                docs.append({
                    'name': row.get('name') or '',
                    'start_time': row.get('start_time') or '09:00',
                    'end_time': row.get('end_time') or '17:00',
                    'period_duration': int(row.get('period_duration') or 60),
                    'break_times': [],
                    'lunch_break': {},
                })
            if docs:
                res = db['batches'].insert_many(docs)
                count = len(res.inserted_ids)

        elif type == 'classes':
            docs = []
            for row in rows:
                dept = db['departments'].find_one({'code': row.get('department_code')}) or db['departments'].find_one({'name': row.get('department_code')})
                batch = db['batches'].find_one({'name': row.get('batch_name')})
                room = (
                    db['rooms'].find_one({'code': row.get('room_code')})
                    or db['rooms'].find_one({'name': row.get('room_code')})
                )
                docs.append({
                    'name': row.get('name') or '',
                    'section': row.get('section') or '',
                    'semester': int(row.get('semester') or 1),
                    'student_count': int(row.get('student_count') or 0),
                    'department_id': str(dept['_id']) if dept else None,
                    'batch_id': str(batch['_id']) if batch else None,
                    'room_id': str(room['_id']) if room else None,
                })
            if docs:
                res = db['classes'].insert_many(docs)
                count = len(res.inserted_ids)

        elif type == 'rooms':
            docs = []
            for row in rows:
                dept = db['departments'].find_one({'code': row.get('department_code')}) or db['departments'].find_one({'name': row.get('department_code')})
                room_type = (row.get('room_type') or 'lecture').strip().lower()
                if room_type not in ('lecture', 'lab', 'seminar'):
                    room_type = 'lecture'
                docs.append({
                    'name': row.get('name') or '',
                    'code': row.get('code') or '',
                    'room_type': room_type,
                    'capacity': int(row.get('capacity') or 0),
                    'department_id': str(dept['_id']) if dept else None,
                    'created_at': datetime.utcnow(),
                })
            if docs:
                res = db['rooms'].insert_many(docs)
                count = len(res.inserted_ids)

        elif type == 'subjects':
            docs = []
            for row in rows:
                dept_codes = (row.get('department_codes') or '')
                dept_list = [c.strip() for c in dept_codes.split(';') if c.strip()]
                department_ids = []
                for code in dept_list:
                    d = db['departments'].find_one({'code': code}) or db['departments'].find_one({'name': code})
                    if d:
                        department_ids.append(str(d['_id']))
                batch = db['batches'].find_one({'name': row.get('batch_name')})
                docs.append({
                    'name': row.get('name') or '',
                    'code': row.get('code') or '',
                    'hours_per_week': int(row.get('hours_per_week') or 0),
                    'requires_lab': (row.get('requires_lab') or '').lower() in ('1','true','yes','y'),
                    'department_ids': department_ids,
                    'department_id': department_ids[0] if department_ids else None,
                    'batch_id': str(batch['_id']) if batch else None,
                })
            if docs:
                res = db['subjects'].insert_many(docs)
                count = len(res.inserted_ids)

        elif type == 'faculty':
            docs = []
            for row in rows:
                dept = db['departments'].find_one({'code': row.get('department_code')}) or db['departments'].find_one({'name': row.get('department_code')})
                docs.append({
                    'name': row.get('name') or '',
                    'email': row.get('email') or '',
                    'department_id': str(dept['_id']) if dept else None,
                    'max_hours_per_week': int(row.get('max_hours_per_week') or 20),
                })
            if docs:
                res = db['faculty'].insert_many(docs)
                count = len(res.inserted_ids)

        elif type == 'mappings':
            updates = 0
            for row in rows:
                subj = (
                    db['subjects'].find_one({'code': row.get('subject_code'), 'source_subject_id': {'$exists': False}, 'class_id': None})
                    or db['subjects'].find_one({'code': row.get('subject_code'), 'source_subject_id': {'$exists': False}})
                    or db['subjects'].find_one({'code': row.get('subject_code')})
                )
                cls = db['classes'].find_one({'name': row.get('class_name'), 'section': row.get('class_section')})
                fac = db['faculty'].find_one({'email': row.get('faculty_email')})
                room = (
                    db['rooms'].find_one({'code': row.get('room_code')})
                    or db['rooms'].find_one({'name': row.get('room_code')})
                ) if row.get('room_code') else None
                if subj and (cls or fac):
                    class_id = str(cls['_id']) if cls else subj.get('class_id')
                    faculty_id = str(fac['_id']) if fac else subj.get('faculty_id')
                    if cls and room:
                        db['classes'].update_one(
                            {'_id': cls['_id']},
                            {'$set': {'room_id': str(room['_id']), 'updated_at': datetime.utcnow()}}
                        )
                    source_id = subj.get('source_subject_id') or str(subj['_id'])
                    existing = db['subjects'].find_one({
                        'class_id': class_id,
                        '$or': [
                            {'source_subject_id': source_id},
                            {'_id': subj['_id']},
                            {
                                'code': subj.get('code'),
                                'name': subj.get('name'),
                                'requires_lab': subj.get('requires_lab', False),
                                'source_subject_id': {'$exists': False},
                            },
                        ],
                    })
                    if existing:
                        db['subjects'].update_one(
                            {'_id': existing['_id']},
                            {'$set': {'class_id': class_id, 'faculty_id': faculty_id, 'updated_at': datetime.utcnow()}}
                        )
                    else:
                        db['subjects'].insert_one({
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
                            'created_at': datetime.utcnow(),
                        })
                    updates += 1
            count = updates

        return JSONResponse({'imported': count, 'type': type})
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV Parsing Error: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
