# 🎓 AI Timetable Scheduler

AI-powered automated timetable generation system with MongoDB backend and React frontend.

## 🚀 Setup & Run Project

There are three ways to set up and run this project depending on your needs.

### Option 1: ⚡ Quick Start (Automated Script - Recommended for Linux/Mac)

The easiest way to get everything up and running is using the provided setup script. It will automatically install all dependencies, seed the database, and start both the frontend and backend servers in the background.

1. Ensure you have Python 3.9+ and Node.js 16+ installed.
2. If using MongoDB Atlas, configure your connection in `backend/.env`. (See Option 3 for the `.env` template). If not configured, the app will try to connect to localhost.
3. Make the script executable and run it:
   ```bash
   chmod +x setup_and_run.sh
   ./setup_and_run.sh
   ```
4. Access the application:
   - **Frontend**: http://localhost:3002 *(Opens straight to the Dashboard!)*
   - **Backend API Docs**: http://localhost:8000/docs
   - To stop the servers later, check the PID from the output or run `pkill -f uvicorn` and `pkill -f "npm run dev"`.

### Option 2: 🐳 Local MongoDB using Docker

If you prefer to run a local MongoDB database rather than using MongoDB Atlas, a `docker-compose.yml` file is provided.

1. Ensure Docker and Docker Compose are installed.
2. Start the local MongoDB and Mongo Express instances:
   ```bash
   docker-compose up -d
   ```
3. You can access the Mongo Express web interface at `http://localhost:8081` (Login: admin / pass).
4. Create `backend/.env` (copying from `.env.example`) and use the local database URL:
   ```env
   MONGODB_URL=mongodb://root:example@localhost:27017/
   DB_NAME=Time-Table-Scheduler
   ```
5. Follow Option 1 or Option 3 to start the application servers.

### Option 3: 🛠️ Manual Setup

If you prefer to set up the environments manually or are on Windows:

#### 1. Prerequisites
- Python 3.9+
- Node.js 16+
- MongoDB (Atlas or Local)

#### 2. Configure Database
Copy `.env.example` to `backend/.env` and edit it with your MongoDB connection details:
```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?appName=Scheduler
DB_NAME=Time-Table-Scheduler
SECRET_KEY=your-secret-key-change-this-in-production
```

#### 3. Setup & Start Backend
Open a terminal and run:
```bash
cd backend
python -m venv .venv

# Activate the virtual environment based on your shell:
source .venv/bin/activate       # For Bash / Zsh
source .venv/bin/activate.fish  # For Fish shell users
.venv\Scripts\activate          # For Windows

pip install -r requirements.txt



# Start Backend Server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 4. Setup & Start Frontend
Open a new terminal window and run:
```bash
cd frontend
npm install
npm run dev
```

#### 5. Access Application
- **Frontend**: http://localhost:3002 *(No login required)*
- **Backend API Docs**: http://localhost:8000/docs

## ✨ Features
✅ 15 Departments with 276+ faculty  
✅ 150+ subjects with faculty assignments  
✅ 240+ classes organized by year/section  
✅ 100+ rooms across 5 blocks  
✅ AI-powered timetable generation  
✅ Conflict-free scheduling  
✅ Real-time updates  

## 🗄️ Database Status
✅ Pre-populated with:
- 15 departments (CSE, IT, ECE, EE, ME, CE, CHE, BME, AE, PIE, TT, FT, AUT, MATH, PHY)
- 276 faculty members (16-20 per department)
- 150 subjects (10 per department)
- 240 classes (4 years × 4 sections × 15 departments)
- 100 rooms (5 blocks × 4 floors × 5 rooms/floor)
- 5 time batches and 15 time slots
- **Total: ~800+ database records ready**

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| MongoDB Connection Error | Check `backend/.env` MONGODB_URL and ensure cluster IP whitelist includes your location |
| Port 8000 in Use | Kill process: `pkill -f uvicorn` |
| Port 3002 in Use | Kill process: `pkill -f "npm run dev"` |
| Dependencies Error | Delete `node_modules` and `.venv` folders, then reinstall |

---
