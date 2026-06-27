# 🎓 AI Timetable Scheduler

AI-powered timetable generation system with a FastAPI backend and React frontend.

## 🚀 Setup & Run Project

This project uses Grok/OpenAI-compatible APIs for AI-powered constraint parsing. Follow the steps below to configure and run the backend and frontend.

### Option 1: ⚡ Quick Start (Automated Script)

The fastest way to start is using the provided setup script.

1. Install Python 3.9+ and Node.js 16+.
2. Copy the environment template and configure your database connection in `backend/.env`.
3. Run the script:
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
- Python 3.9+
- Node.js 16+
- MongoDB (Atlas or local)

#### 2. Configure `backend/.env`
Copy `backend/.env.example` to `backend/.env` and update the values.

Example `backend/.env`:
```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?appName=Scheduler
USE_LOCAL_MONGODB=false
LOCAL_MONGODB_URL=mongodb://localhost:27017
DB_NAME=Time-Table-Scheduler
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=http://localhost:3002,http://localhost:3000,http://localhost:5173,http://127.0.0.1:3002
SOLVER_TIME_LIMIT_SECONDS=300
AI_MODEL=grok-1
OPENAI_API_KEY=your-grok-api-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_TIMEOUT_SECONDS=60
DOCUMENT_ANALYSIS_MODEL=qwen3:8b
DOCUMENT_ANALYSIS_API_BASE=http://localhost:11434/v1
DOCUMENT_ANALYSIS_API_KEY=local
```

Set `USE_LOCAL_MONGODB=true` when you want to test with MongoDB Compass/local MongoDB. Set it back to `false` to use Atlas automatically.

`AI_MODEL` should be set to a Grok/OpenAI-compatible model such as `grok-1`.

#### Local Document Analysis

Uploaded timetable, syllabus, and faculty-allocation PDFs are extracted locally first with PDF text extraction, `pdftotext` when available, and OCR for scans/images. For stricter JSON normalization, you can point the backend at any local OpenAI-compatible model server:

```env
DOCUMENT_ANALYSIS_MODEL=qwen3:8b
DOCUMENT_ANALYSIS_API_BASE=http://localhost:11434/v1
DOCUMENT_ANALYSIS_API_KEY=local
```

When `DOCUMENT_ANALYSIS_MODEL` is blank, uploads still work through the deterministic fallback parser. When it is set, the upload response includes a normalized `extracted_timetable` array plus the usual generated scheduler constraints.

#### 3. Start the Backend

From the `backend` folder:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Bash / Zsh
source .venv/bin/activate.fish  # Fish shell
.venv\Scripts\activate        # Windows PowerShell or Command Prompt
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 5. Bulk CSV Import

The backend includes a CSV import tool for fast data loading of departments, batches, classes, subjects, faculty, and subject mappings.

Example imports:
```bash
cd backend
python3 scripts/import_csv.py --type departments
python3 scripts/import_csv.py --type classes
python3 scripts/import_csv.py --type subjects
python3 scripts/import_csv.py --type faculty
python3 scripts/import_csv.py --type mappings
```

Import all supported templates at once:
```bash
python3 scripts/import_csv.py --type all
```

Then start the frontend in a separate terminal.

#### 6. Start the Frontend

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

#### 5. Access the Application
- **Frontend**: http://localhost:3002
- **Backend API Docs**: http://localhost:8000/docs

## 🧠 AI Constraint Parsing

This project accepts natural language constraints and converts them to schedule constraints using Grok/OpenAI.

Example constraint text:
```text
Professor Shiva is not available on Tuesday, and all classes should stay with consistent faculty during lunch break.
```

Example API request body:
```json
{
  "name": "Spring 2026",
  "academic_year": "2025-2026",
  "semester": 2,
  "working_days": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
  "periods_per_day": 7,
  "constraints_text": "Professor Shiva is not available on Tuesday, and all students should stay in the same classroom for lunch break."
}
```

## ✨ Features
- AI-powered timetable generation
- Faculty availability and stable schedule handling
- Conflict-free scheduling
- FastAPI backend with React frontend

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| MongoDB Connection Error | Check `backend/.env` and verify `MONGODB_URL` is correct |
| Port 8000 in Use | Kill any running Uvicorn process: `pkill -f uvicorn` |
| Port 3002 in Use | Kill the frontend process: `pkill -f "npm run dev"` |
| Dependency Errors | Remove `node_modules` and `.venv`, then reinstall |

---
