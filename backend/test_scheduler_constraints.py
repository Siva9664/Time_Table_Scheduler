from pymongo import MongoClient
import os
from dotenv import load_dotenv
from app.services.scheduler import TimetableScheduler

load_dotenv()
uri = os.getenv("MONGODB_URL")
client = MongoClient(uri)
db_name = os.getenv("DB_NAME")
db = client[db_name]

classes = list(db.classes.find({"semester": 5}))
class_ids = [str(c["_id"]) for c in classes]

constraints = [
    {
        "type": "faculty_availability",
        "faculty_name": "SivaKumar ",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "unavailable_slots": [
            {"start": "10:15", "end": "12:30"},
            {"start": "13:15", "end": "14:45"}
        ]
    },
    {
        "type": "faculty_availability",
        "faculty_name": "Selvi Mam",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "unavailable_slots": [
            {"start": "10:15", "end": "12:30"},
            {"start": "15:00", "end": "16:30"}
        ]
    }
]

scheduler = TimetableScheduler(
    db=db,
    working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    periods_per_day=7,
    time_limit_seconds=10,
    custom_constraints=constraints 
)
scheduler.load_data(class_ids=class_ids)
scheduler.create_variables()
scheduler.add_constraints()
result = scheduler.solve()
print("Status:", result["status"])
