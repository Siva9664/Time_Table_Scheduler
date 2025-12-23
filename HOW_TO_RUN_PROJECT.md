# How to Run AI Timetable Scheduler (Manual Method)

This method uses a virtual drive (`Z:`) to avoid Windows path length limitations and runs with the existing SQLite database.

## 1. Start Backend Server

1. Open a **Command Prompt** (cmd) terminal.
2. Run the following command to map the backend folder to drive `Z:`:
   ```cmd
   subst Z: "C:\Users\SIVARANJITH\Desktop\AI_Timetable_Scheduler_Complete_With_Frontend_Backend\AI_Timetable_Scheduler_Complete_With_Frontend_Backend\ai-timetable-scheduler\backend"
   ```
3. Start the server using the mapped drive:
   ```cmd
   cmd /c "Z: && set PYTHONPATH=Z:\pkg && Z:\venv_short\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
   ```
   *Wait until you see "Application startup complete".*

## 2. Start Frontend Server

1. Open a **New** Command Prompt terminal.
2. Navigate to the frontend directory:
   ```cmd
   cd "C:\Users\SIVARANJITH\Desktop\AI_Timetable_Scheduler_Complete_With_Frontend_Backend\AI_Timetable_Scheduler_Complete_With_Frontend_Backend\ai-timetable-scheduler\frontend"
   ```
3. Start the application:
   ```cmd
   npm run dev
   ```
   *Wait until you see "Local: http://localhost:3002"*

## 3. Usage

- **URL**: [http://localhost:3002](http://localhost:3002)
- **Login**: `admin` / `admin123`

## Troubleshooting

- **"Could not validate credentials"**: If you see this error, your session has expired. The application is configured to redirect you to login automatically. If stuck, refresh the page and login again.
- **Path not found**: Ensure you ran the `subst` command in Step 1.
