# Test Suite Directory & Mapping Guide

This test suite covers all components and purposes of the AI Timetable Scheduler backend and full system.

The primary test modules are located in `backend/tests/` and can be executed from the project root or within the `backend/` directory using pytest.

## Test Files and Component Purposes

| Test File | Component in `app/` | Purpose Covered |
| :--- | :--- | :--- |
| [`test_main_app.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_main_app.py) | `backend/app/main.py` | FastAPI application lifecycle (lifespan), root and health check endpoints, security headers middleware (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy), CORS policy, rate limiting, and database URL credential masking. |
| [`test_auth.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_auth.py) | `backend/app/api/endpoints/auth.py`, `backend/app/core/security.py` | User authentication, password hashing (bcrypt), JWT generation/expiration, login/registration workflows, faculty account management, role verification (admin vs faculty), and tenant database isolation. |
| [`test_config.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_config.py) | `backend/app/core/config.py`, `backend/app/core/logging_config.py` | Environment variable parsing, default settings, CORS allowed origins list resolution, database URL selection (Atlas vs local), AI API key precedence (Qwen, DashScope, OpenAI), and Loguru logging configuration. |
| [`test_database.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_database.py) | `backend/app/database/database.py` | MongoDB client connection pooling, fallback logic, essential unique index creation (`users`, `departments`, `subjects`, `faculty`, etc.), multi-tenant collection schema materialization, and clean connection termination. |
| [`test_models_and_schemas.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_models_and_schemas.py) | `backend/app/models/`, `backend/app/schemas/` | Pydantic data schemas validation for batches, classes, departments, faculty, rooms, subjects, timetables, users, tokens, and MongoDB document helper serializers. |
| [`test_timetable_api.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_timetable_api.py) | `backend/app/api/endpoints/timetable.py` | Academic resource management CRUD endpoints (batches, departments, rooms, classes, subjects, faculty), subject-faculty assignment mappings, ObjectId format validation, and AI constraint context aggregation. |
| [`test_scheduler_engine.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_scheduler_engine.py) | `backend/app/services/scheduler.py` | Google OR-Tools CP-SAT constraint satisfaction engine, credit-to-hours mapping, internal `_Obj` document wrapper, conflict prevention modeling, and schedule solving. |
| [`test_ai_parser.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_ai_parser.py) | `backend/app/services/ai_parser.py` | Natural language constraint parser, supported constraint type enumeration, weekday and number word normalization, fuzzy faculty/subject matching, and rule-based constraint fallback. |
| [`test_csv_imports.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_csv_imports.py) | `backend/app/api/endpoints/imports.py` | CSV/Excel batch imports, dynamic header mapping, document structure guessing, and bulk insertion deduplication. |
| [`test_document_constraints.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_document_constraints.py) | `backend/app/services/document_constraints.py`, `backend/app/services/document_analysis.py` | Document text and table extraction from PDFs/DOCX, schedule constraint translation, and time slot constraint construction. |
| [`test_knowledge_ingestion.py`](file:///h:/Time_Table_Scheduler/backend/tests/test_knowledge_ingestion.py) | `backend/app/services/ingestion/` | Multi-format file ingestion pipeline, MIME validation, ZIP archive safety checks, fuzzy entity deduplication, learning engine alias memory, and review session tracking. |

## Running the Tests

### From Project Root:
```bash
pytest
```

### With Code Coverage:
```bash
pytest --cov=backend/app --cov-report=term-missing
```

### From Backend Directory:
```bash
cd backend
pytest tests/ -v
```
