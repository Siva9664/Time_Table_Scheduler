# AI TIMETABLE SCHEDULER - SETUP GUIDE

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.9+ installed
- Node.js 16+ installed
- MySQL 8.0+ installed and running

---

## 📦 STEP 1: Extract Files
1. Extract `ai-timetable-scheduler-complete.zip`
2. You'll get a folder: `ai-timetable-scheduler/`

---

## 🔧 STEP 2: Database Setup

### Create Database (MySQL)
```bash
# Open MySQL command line
mysql -u root -p

# Create database
CREATE DATABASE timetable_db;

# Exit
exit;
```

---

## 🐍 STEP 3: Backend Setup

### Navigate to backend
```bash
cd ai-timetable-scheduler/backend
```

### Create virtual environment
**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies
```bash
pip install -r requirements.txt
```

### Configure environment
Edit `.env` file with your database credentials:
```env
DATABASE_URL=mysql://root:YOUR_PASSWORD@localhost:3306/timetable_db
SECRET_KEY=your-super-secret-key-change-this
```

### Initialize database
```bash
python init_db.py
```

You should see:
```
✓ Admin user created!
  Username: admin
  Password: admin123
```

### Run backend server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend running at: **http://localhost:8000**
API Docs: **http://localhost:8000/docs**

---

## ⚛️  STEP 4: Frontend Setup (New Terminal)

### Navigate to frontend
```bash
cd ai-timetable-scheduler/frontend
```

### Install dependencies
```bash
npm install
```

This will install:
- React 18
- Tailwind CSS
- Vite
- Axios
- React Hook Form
- React Router

### Run frontend
```bash
npm run dev
```

Frontend running at: **http://localhost:3000**

---

## 🎯 STEP 5: Access Application

1. Open browser: **http://localhost:3000**
2. Login with:
   - **Username:** `admin`
   - **Password:** `admin123`
3. ⚠️  **IMPORTANT:** Change password after first login!

---

## 📚 Usage Workflow

### 1. Add Departments
- Click "Departments" tab
- Add departments (e.g., Computer Science, Mechanical)

### 2. Create Classes
- Click "Classes" tab
- Add classes with sections (e.g., B.Tech 2nd Year - Section A)

### 3. Define Subjects
- Click "Subjects" tab
- Add subjects with hours per week and lab requirements

### 4. Add Faculty
- Click "Faculty" tab
- Register faculty members and assign to departments

### 5. Configure Rooms
- Click "Rooms" tab
- Add rooms with capacity and facilities (projector, computers)

### 6. Generate Timetable
- Click "Generate" tab
- Fill in timetable details (name, academic year, semester)
- Click "Generate Timetable"
- Wait 1-5 minutes for OR-Tools solver to find optimal schedule

### 7. View Results
- Generated timetables appear in the list
- Click to view detailed schedules for each class

---

## 🐛 Troubleshooting

### Backend Issues

**Error: "connection refused"**
- Check MySQL is running
- Verify database credentials in `.env`
- Ensure database `timetable_db` exists

**Error: "Module not found"**
- Activate virtual environment
- Reinstall: `pip install -r requirements.txt`

**Error: "Port 8000 already in use"**
- Kill existing process or use different port:
  ```bash
  uvicorn app.main:app --reload --port 8001
  ```

### Frontend Issues

**Error: "npm install fails"**
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Ensure Node.js 16+ is installed

**Error: "Cannot connect to API"**
- Verify backend is running on port 8000
- Check browser console for CORS errors
- Ensure backend ALLOWED_ORIGINS includes frontend URL

**Error: "Page blank/white screen"**
- Open browser DevTools (F12)
- Check Console tab for errors
- Verify all components compiled successfully

---

## 🔐 Security Notes

1. **Change default password immediately**
2. **Use strong SECRET_KEY in production**
3. **Enable HTTPS for production deployment**
4. **Don't commit `.env` file to version control**
5. **Use environment-specific configurations**

---

## 📖 API Documentation

Once backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🏗️  Project Structure

```
ai-timetable-scheduler/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/    # API routes
│   │   ├── core/             # Security & config
│   │   ├── models/           # Database models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # OR-Tools scheduler
│   │   ├── database/         # DB connection
│   │   └── main.py           # FastAPI app
│   ├── requirements.txt      # Python dependencies
│   ├── init_db.py           # DB initialization
│   └── .env                 # Configuration
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API calls
│   │   ├── utils/           # Helpers
│   │   └── App.jsx          # Main app
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite config
└── README.md
```

---

## 🚀 Production Deployment

### Backend
1. Use production MySQL server
2. Set strong `SECRET_KEY`
3. Configure proper CORS origins
4. Use gunicorn: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
5. Set up HTTPS with nginx/Apache

### Frontend
1. Build: `npm run build`
2. Deploy `dist/` folder
3. Configure environment variables
4. Use CDN for static assets

---

## 💡 Tips

- Use **MySQL Workbench** or **phpMyAdmin** for database management
- Use **Postman** to test API endpoints
- Monitor solver performance in backend logs
- Start with small dataset for testing
- Add constraints incrementally

---

## 📞 Support

For issues:
1. Check this setup guide
2. Review API documentation
3. Check backend/frontend logs
4. Verify all prerequisites installed

---

## 🎓 Learning Resources

- FastAPI: https://fastapi.tiangolo.com
- React: https://react.dev
- Tailwind CSS: https://tailwindcss.com
- Google OR-Tools: https://developers.google.com/optimization

---

**Congratulations! Your AI Timetable Scheduler is ready to use! 🎉**
