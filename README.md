# 🎓 AI Timetable Scheduler

AI-powered automated timetable generation system with MongoDB backend and React frontend.

## ⚡ Quick Start (Manual Setup)

### 1. Prerequisites
- Python 3.9+
- Node.js 16+
- MongoDB (Atlas or Local)

### 2. Clone & Setup Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Database
Edit `backend/.env` with your MongoDB connection:
```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?appName=Scheduler
DB_NAME=Time-Table-Scheaduler
SECRET_KEY=your-secret-key
```

### 4. Start Backend
```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

### 6. Access Application
- **Frontend**: http://localhost:3002
- **Backend API**: http://localhost:8000
- **Login**: admin / admin123

## Features
✅ 15 Departments with 276+ faculty  
✅ 150+ subjects with faculty assignments  
✅ 240+ classes organized by year/section  
✅ 100+ rooms across 5 blocks  
✅ AI-powered timetable generation  
✅ Conflict-free scheduling  
✅ Real-time updates  

## Database Status
✅ Pre-populated with:
- 15 departments (CSE, IT, ECE, EE, ME, CE, CHE, BME, AE, PIE, TT, FT, AUT, MATH, PHY)
- 276 faculty members (16-20 per department)
- 150 subjects (10 per department)
- 240 classes (4 years × 4 sections × 15 departments)
- 100 rooms (5 blocks × 4 floors × 5 rooms/floor)
- 5 time batches and 15 time slots
- **Total: ~800+ database records ready**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| MongoDB Connection Error | Check `.env` MONGODB_URL and ensure cluster IP whitelist includes your location |
| Port 8000 in Use | Kill process: `pkill -f uvicorn` |
| Port 3002 in Use | Kill process: `pkill -f "npm run dev"` |
| Dependencies Error | Delete `node_modules` and `.venv`, reinstall |

---
