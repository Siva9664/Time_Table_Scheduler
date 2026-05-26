import asyncio
import os
from pymongo import MongoClient
from app.services.scheduler import TimetableScheduler
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URL"))
db = client[os.getenv("DB_NAME")]

async def main():
    classes = list(db.classes.find({"academic_year": "2024-2028", "semester": 5}))
    class_ids = [str(c["_id"]) for c in classes]
    
    scheduler = TimetableScheduler(
        db=db,
        working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        periods_per_day=7,
        time_limit_seconds=10
    )
    result = scheduler.generate_schedule(class_ids=class_ids)
    if result["status"] == "ERROR":
        print(result["message"])
        return
        
    schedule = result["schedule"]
    for class_id_str, class_data in schedule.items():
        print(f"Class: {class_data['class_name']}")
        timetable = class_data["timetable"]
        for day_name, periods in timetable.items():
            assigned = sum(1 for p in periods if p is not None and getattr(p, "get", lambda x: None)("subject") is not None)
            print(f"  Day {day_name} ({len(periods)} periods): {assigned} subject slots filled")

asyncio.run(main())
