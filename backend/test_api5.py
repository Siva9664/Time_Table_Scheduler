import asyncio
from pymongo import MongoClient
import os
from app.services.scheduler import TimetableScheduler
from app.services.ai_parser import AIConstraintParser
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGODB_URL")
client = MongoClient(uri)
db_name = os.getenv("DB_NAME")
db = client[db_name]

class DummyReq:
    semester = 5
    academic_year = "2024-2028"
    constraints_text = "Siva Kumar Sir Will not Available From 10:15 am to 12.30 pm and 1.15 to 2.45\nSelvi Man Not Available at 10:15 to 12:30 and 3:00 to 4:30"

async def main():
    request = DummyReq()
    # We must call parse_constraints synchronously, because it's not async!
    parser = AIConstraintParser()
    
    # Actually wait, in app/api/endpoints/timetable.py it's called synchronously or asynchronously?
    # I saw: parsed_constraints = await parser.parse_constraints(request.constraints_text)
    # WAIT! In timetable.py it uses `await`? I got an error doing `await` locally. Let me just use `parse_constraints_with_diagnostics` which is used in `timetable.py`.
    
    context = {
        "faculty_names": ["SivaKumar ", "Selvi Mam"],
        "subject_names": ["Software Engineering ", "NLP"],
        "class_names": ["AIML ", "AIML"],
        "periods_per_day": 7,
    }
    parser = AIConstraintParser(context=context)
    parse_result = parser.parse_constraints_with_diagnostics(request.constraints_text)
    parsed_constraints = parse_result["constraints"]
    
    query = {"semester": request.semester, "academic_year": request.academic_year}
    classes = list(db.classes.find(query))
    class_ids = [str(c["_id"]) for c in classes]

    scheduler = TimetableScheduler(
        db=db,
        working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        periods_per_day=7,
        time_limit_seconds=30,
        custom_constraints=parsed_constraints
    )
    result = scheduler.generate_schedule(
        class_ids=class_ids
    )
    print("Result status:", result["status"])

asyncio.run(main())
