from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
import csv
import tempfile
import os
from typing import List, Optional

from ...database.database import get_db

router = APIRouter()


def _read_csv_rows(path: str) -> List[dict]:
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            cleaned = { (k or '').strip(): (v or '').strip() for k, v in row.items() }
            rows.append(cleaned)
        return rows


@router.post('/upload')
async def upload_csv(type: str = Form(...), file: UploadFile = File(...), db=Depends(get_db)):
    """Upload a CSV and import data. Form param `type` selects which importer to run.
    Supported types: departments, batches, classes, subjects, faculty, mappings
    """
    allowed = {'departments','batches','classes','subjects','faculty','mappings'}
    if type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported import type: {type}")

    suffix = os.path.splitext(file.filename)[1] or '.csv'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        rows = _read_csv_rows(tmp_path)
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
                    'break_times': [] if not row.get('break_times') else [] ,
                    'lunch_break': {} if not row.get('lunch_break') else {},
                })
            if docs:
                res = db['batches'].insert_many(docs)
                count = len(res.inserted_ids)

        elif type == 'classes':
            docs = []
            for row in rows:
                dept = db['departments'].find_one({'code': row.get('department_code')}) or db['departments'].find_one({'name': row.get('department_code')})
                batch = db['batches'].find_one({'name': row.get('batch_name')})
                docs.append({
                    'name': row.get('name') or '',
                    'section': row.get('section') or '',
                    'semester': int(row.get('semester') or 1),
                    'student_count': int(row.get('student_count') or 0),
                    'department_id': str(dept['_id']) if dept else None,
                    'batch_id': str(batch['_id']) if batch else None,
                })
            if docs:
                res = db['classes'].insert_many(docs)
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

        # legacy import type is disabled

        elif type == 'mappings':
            updates = 0
            for row in rows:
                subj = db['subjects'].find_one({'code': row.get('subject_code')})
                cls = db['classes'].find_one({'name': row.get('class_name'), 'section': row.get('class_section')})
                fac = db['faculty'].find_one({'email': row.get('faculty_email')})
                if subj and (cls or fac):
                    u = {}
                    if cls:
                        u['class_id'] = str(cls['_id'])
                    if fac:
                        u['faculty_id'] = str(fac['_id'])
                    if u:
                        db['subjects'].update_one({'_id': subj['_id']}, {'$set': u})
                        updates += 1
            count = updates

        return JSONResponse({'imported': count, 'type': type})
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
