# AI Timetable Scheduler - Complete Project

## 🎯 Overview

An intelligent timetable scheduling system that uses **Google OR-Tools** constraint programming to automatically generate optimal timetables while respecting all constraints.

### Key Features

✅ **Automated Scheduling** - Uses CP-SAT solver for optimal timetable generation  
✅ **Constraint Management** - Configurable hard and soft constraints  
✅ **Conflict Detection** - Automatic detection of scheduling conflicts  
✅ **Faculty Workload** - Balanced teaching load across faculty  
✅ **Room Management** - Efficient room utilization tracking  
✅ **Modern UI** - React-based responsive interface  
✅ **REST API** - FastAPI backend with comprehensive endpoints  

---

## 📦 Package Contents

```
ai-timetable-scheduler/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes and endpoints
│   │   ├── core/              # Core configuration and security
│   │   ├── database/          # Database connection
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # Business logic and scheduler
│   ├── init_db.py             # Database initialization
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Environment variables template
│
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── Admin/         # Admin management pages
│   │   │   ├── Auth/          # Login/authentication
│   │   │   └── Timetable/     # Timetable generation & viewing
│   │   ├── services/          # API client
│   │   ├── styles/            # CSS styles
│   │   └── utils/             # Utility functions
│   ├── package.json           # Node dependencies
│   └── vite.config.js         # Vite configuration
│
├── database/                   # Database files
│   └── schema.sql             # Complete MySQL schema
│
└── docs/                       # Documentation
    ├── SETUP_INSTRUCTIONS.md  # Setup guide
    ├── DATABASE_SCHEMA.txt    # Database structure
    └── INSTALLATION_GUIDE.txt # Installation steps

```

---

## 🚀 Quick Start

### Prerequisites

- **MySQL 8.0+** (database server)
- **Python 3.8+** (backend)
- **Node.js 16+** (frontend)
- **npm** or **yarn** (package manager)

### Installation Steps

#### 1. Setup Database

```bash
# Login to MySQL
mysql -u root -p

# Create database
mysql> source database/schema.sql

# Verify tables created
mysql> USE ai_timetable_scheduler;
mysql> SHOW TABLES;
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit DATABASE_URL and SECRET_KEY

# Initialize database with sample data
python init_db.py

# Run backend server
uvicorn app.main:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

---

## 🔑 Default Credentials

**Username:** `admin`  
**Password:** `admin123`  

⚠️ **IMPORTANT:** Change the default password immediately after first login!

---

## 📊 Database Schema

The system uses **11 tables** for complete timetable management:

### Core Tables
- **users** - Authentication and user profiles
- **departments** - Academic departments
- **classes** - Student batches/sections
- **subjects** - Courses with credit hours
- **faculty** - Teacher information and availability
- **rooms** - Classrooms and labs with capacity

### Scheduling Tables
- **time_slots** - Period definitions (days and times)
- **timetables** - Generated timetable metadata
- **timetable_entries** - Individual schedule assignments
- **constraints** - Scheduling rules (hard/soft)

### Sample Data

The database comes pre-loaded with:
- 2 departments (CSE, ECE)
- 45 time slots (Monday-Friday, 9 AM - 5 PM)
- 9 default constraints
- Admin user account

---

## 🎯 Usage Guide

### 1. Add Your Data

After logging in:

1. **Add Departments** → Go to Admin → Departments
2. **Add Faculty** → Go to Admin → Faculty Members
3. **Add Classes** → Go to Admin → Classes
4. **Add Subjects** → Go to Admin → Subjects (assign to classes and faculty)
5. **Add Rooms** → Go to Admin → Rooms

### 2. Configure Constraints

Go to **Settings → Constraints**:
- Review default constraints
- Add custom constraints if needed
- Set priorities (higher number = higher priority)

### 3. Generate Timetable

1. Go to **Generate Timetable**
2. Fill in details:
   - Timetable name
   - Academic year
   - Semester
3. Click **Generate**
4. Wait for solver to complete (typically 10-60 seconds)
5. Review generated timetable
6. If satisfied, click **Publish**

### 4. View Timetables

- **By Class** - View class schedules
- **By Faculty** - View teacher schedules
- **By Room** - View room utilization
- **Export** - Download as PDF/Excel

---

## 🔧 Configuration

### Backend (.env)

```env
# Database
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/ai_timetable_scheduler

# Security
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server
DEBUG=True
ALLOWED_ORIGINS=http://localhost:5173
```

### Frontend Configuration

Edit `frontend/src/services/api.js` if backend URL changes:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

---

## 📡 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration

### Departments
- `GET /api/departments` - List departments
- `POST /api/departments` - Create department
- `PUT /api/departments/{id}` - Update department
- `DELETE /api/departments/{id}` - Delete department

### Classes
- `GET /api/classes` - List classes
- `POST /api/classes` - Create class
- `PUT /api/classes/{id}` - Update class
- `DELETE /api/classes/{id}` - Delete class

### Subjects
- `GET /api/subjects` - List subjects
- `POST /api/subjects` - Create subject

### Faculty
- `GET /api/faculty` - List faculty
- `POST /api/faculty` - Create faculty

### Rooms
- `GET /api/rooms` - List rooms
- `POST /api/rooms` - Create room

### Timetables
- `POST /api/timetables/generate` - Generate timetable
- `GET /api/timetables` - List timetables
- `GET /api/timetables/{id}` - Get specific timetable
- `PUT /api/timetables/{id}/publish` - Publish timetable

Full API documentation: `http://localhost:8000/docs`

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

---

## 🐛 Troubleshooting

### Database Connection Error

**Problem:** `Can't connect to MySQL server`

**Solution:**
```bash
# Check MySQL is running
sudo systemctl status mysql  # Linux
brew services list          # macOS

# Start MySQL
sudo systemctl start mysql  # Linux
brew services start mysql   # macOS
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'X'`

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Frontend Not Loading

**Problem:** Blank page or errors in browser console

**Solution:**
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Scheduler Fails

**Problem:** Timetable generation returns "INFEASIBLE"

**Solutions:**
1. Check time_slots table has data
2. Verify subjects have faculty assigned
3. Ensure rooms have sufficient capacity
4. Review constraints (may be too restrictive)
5. Check faculty availability settings

---

## 📚 Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - SQL ORM
- **PyMySQL** - MySQL connector
- **OR-Tools** - Google's optimization library
- **Pydantic** - Data validation
- **JWT** - Authentication tokens

### Frontend
- **React** - UI library
- **Vite** - Build tool
- **TailwindCSS** - Utility-first CSS
- **Axios** - HTTP client
- **React Router** - Navigation

### Database
- **MySQL 8.0** - Relational database
- **InnoDB** - Storage engine

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License.

---

## 🆘 Support

For issues or questions:
- Check the `docs/` folder for detailed guides
- Review API documentation at `/docs`
- Check error logs in backend terminal

---

## 🎓 Credits

Built with ❤️ using modern web technologies and Google OR-Tools for intelligent scheduling.

**Happy Scheduling! 🎓📅**
