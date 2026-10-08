# 🎓 AI Timetable Scheduler (Production Edition)

The **AI Timetable Scheduler** is an advanced, fully autonomous constraint-satisfaction scheduling platform. It leverages a FastAPI backend, a React frontend, and an integrated AI Knowledge Ingestion Pipeline to intelligently parse constraints, resolve conflicts, and generate conflict-free academic timetables.

This release represents the **Complete Final Production Version**, fortified with enterprise-grade security, automated testing, comprehensive deduplication logic, and AI prompt injection safeguards.

---

## ✨ Enterprise Features

- **AI-Powered Knowledge Ingestion**: Automatically parse PDFs, DOCX, CSVs, and images using advanced OCR (PaddleOCR, PyMuPDF, pdfplumber) and AI LLMs (Grok/OpenAI).
- **Intelligent Deduplication & Learning Engine**: Detects duplicates using Levenshtein distance and TF-IDF. Remembers user resolutions (e.g., "ML" -> "Machine Learning") for future uploads.
- **Automated Timetable Generation**: Conflict-free scheduling utilizing a deterministic constraint solver.
- **Enterprise Security Hardening**:
  - **Zip Bomb Prevention**: Strict limits on recursive directory traversal, file counts, and memory thresholds.
  - **Prompt Injection Defense**: Specialized systemic safeguards to prevent malicious text in uploads from hijacking the AI parser.
  - **Rate Limiting**: Integrated `slowapi` rate-limiting (e.g., 5 requests/min for login) to prevent brute-force attacks.
  - **Strict HTTP Security Headers**: Comprehensive Content Security Policy (CSP), HSTS, and framing protections.
- **Production Observability**: Structured JSON logging powered by Loguru for centralized telemetry (Datadog/ELK ready).
- **Full Quality Assurance**: 100% compliant with `flake8`, `mypy`, and extensively tested using `pytest` interacting with a segregated, real MongoDB test database.

---

## 🚀 Setup & Run Project

### Option 1: ⚡ Quick Start (Automated Script)

The fastest way to start is using the provided setup script.

1. Install Python 3.12+ and Node.js 18+.
2. Copy the environment template and configure your database connection in `backend/.env`.
3. Run the automated deployment script:
   ```bash
   chmod +x setup_and_run.sh
   ./setup_and_run.sh
   ```
4. Open the app in your browser:
   - **Frontend**: http://localhost:3002
   - **Backend API Docs**: http://localhost:8000/docs

> If the script does not work on your system, follow the manual setup path below.

### Option 2: 🛠️ Manual Setup

#### 1. Prerequisites
- Python 3.12+
- Node.js 18+
- MongoDB (Atlas or local)

#### 2. Configure Environment Variables
Copy `backend/.env.example` to `backend/.env` and configure it:

```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?appName=Scheduler
USE_LOCAL_MONGODB=false
LOCAL_MONGODB_URL=mongodb://localhost:27017
DB_NAME=Time-Table-Scheduler
SECRET_KEY=your-highly-secure-jwt-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=http://localhost:3002,http://127.0.0.1:3002
SOLVER_TIME_LIMIT_SECONDS=300

# AI Configuration
AI_MODEL=grok-1
OPENAI_API_KEY=your-grok-api-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_TIMEOUT_SECONDS=60
```

#### 3. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 4. Start the Frontend

In a separate terminal:
```bash
cd frontend
npm install
npm run build
npm run dev
```

---

---

## 🔄 CI/CD Pipeline & DevOps Automation

This project includes fully automated **GitHub Actions CI/CD workflows** and Docker orchestration:

- **CI Pipeline (`.github/workflows/ci.yml`)**:
  - Automatically triggers on `push` and `pull_request` to `main` and `develop`.
  - Spins up a dedicated **MongoDB 7.0 Service Container**.
  - Runs Python static analysis (`flake8`) and full Pytest suite with code coverage (`pytest-cov`).
  - Installs, lints, and builds the frontend production bundle (`Vite`).
  - Validates container builds for both backend and frontend Docker images.
- **CD Pipeline (`.github/workflows/cd.yml`)**:
  - Automatically triggers on `push` to `main`, git tags (`v*.*.*`), or manual dispatch.
  - Packages production distribution tarballs and uploads build artifacts.
  - Builds and publishes multi-platform container images to **GitHub Container Registry (GHCR)**.
  - Deploys frontend / serverless targets to **Vercel**.
- **Container Orchestration (`docker-compose.yml`)**:
  - 1-command local deployment: `docker-compose up --build -d`.

---

## 🧪 Testing & Quality Assurance

Every purpose and component in the main application has an isolated, purpose-built test file in `backend/tests/`:

| Test File | Component in `app/` | Purpose Covered |
| :--- | :--- | :--- |
| `test_main_app.py` | `app/main.py` | Lifespan events, root/health endpoints, security headers (CSP, HSTS), rate limiting, Mongo URL masking. |
| `test_auth.py` | `app/api/endpoints/auth.py`, `app/core/security.py` | Bcrypt hashing, JWT issuance/validation, user registration, login, `/me`, faculty CRUD, tenant isolation. |
| `test_config.py` | `app/core/config.py`, `app/core/logging_config.py` | Settings parsing, allowed origins list, local/Atlas Mongo toggle, AI keys priority, Loguru logger setup. |
| `test_database.py` | `app/database/database.py` | MongoDB client pooling, unique index creation across 7 collections, tenant collection schema materialization. |
| `test_models_and_schemas.py` | `app/models/`, `app/schemas/` | Pydantic validation (Batch, Class, Dept, Faculty, Room, Subject, Timetable, User) and DB document helpers. |
| `test_timetable_api.py` | `app/api/endpoints/timetable.py` | Academic entities CRUD (Batches, Depts, Rooms, Classes, Subjects, Faculty), subject mappings, AI context builder. |
| `test_scheduler_engine.py` | `app/services/scheduler.py` | OR-Tools CP-SAT solver, credit hours to contact periods conversion, `_Obj` wrapper, conflict prevention modeling. |
| `test_ai_parser.py` | `app/services/ai_parser.py` | NLP constraint parser, 10 supported types, weekday/number normalization, fuzzy entity matching, rule fallbacks. |
| `test_csv_imports.py` | `app/api/endpoints/imports.py` | CSV/Excel batch imports, header column guessing and mapping, deduplication logic. |
| `test_document_constraints.py` | `app/services/document_constraints.py` | Document text extraction (PDF/DOCX/CSV), slot constraint translation, and normalization. |
| `test_knowledge_ingestion.py` | `app/services/ingestion/` | Multi-format ingestion, ZIP safety & traversal defense, MIME verification, fuzzy deduplicator, learning engine. |

### Run Backend Tests (Pytest)
```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Run Static Analysis
Ensure code quality by running formatting and linting:
```bash
cd backend
flake8 app/ tests/ --max-line-length=120 --extend-ignore=E501,E203,E402
mypy app/
```


---

## 🧠 AI Constraint Parsing

This project accepts natural language constraints from uploaded documents and converts them to deterministic schedule rules via LLMs.

**Input text:**
> "Professor Shiva is not available on Tuesday, and all classes should stay with consistent faculty during lunch break."

**AI Engine JSON Output:**
```json
{
  "constraints": [
    {
      "type": "faculty_unavailability",
      "faculty_name": "Professor Shiva",
      "unavailable_days": ["Tuesday"]
    },
    {
      "type": "consecutive_periods",
      "subject_type": "lunch"
    }
  ]
}
```

---

## 🛡️ Architecture & Security 

- **Frontend**: React (Vite), TailwindCSS, React-Hook-Form. Bundled with Esbuild.
- **Backend**: FastAPI, Pydantic v2, PyMongo (Synchronous wrappers).
- **Security Middleware**: X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Strict-Transport-Security (HSTS), Content-Security-Policy (CSP).
- **Authentication**: JWT verification via PyJWT 2.13.0+.
- **Database Initialization**: Pre-computed unique `indexes` initialized on application lifespan startup to strictly prevent duplicate entity insertion at the MongoDB level.

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **MongoDB Permission Error** | Ensure your Atlas user has standard read/write permissions. Dropping databases requires `dbAdminAnyDatabase` (Tests handle teardown safely). |
| **Port 8000 in Use** | Kill running backend process: `pkill -f uvicorn` |
| **Timeout during Pytest** | If `pytest-cov` times out downloading dependencies, wait 1-2 minutes or retry on a faster connection. |
| **Missing Poppler Error** | PyMuPDF and pdf2image require Poppler. Install via `sudo apt-get install poppler-utils`. |
