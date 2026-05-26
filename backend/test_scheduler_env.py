from pymongo import MongoClient
import os
from dotenv import load_dotenv
from app.services.scheduler import TimetableScheduler

load_dotenv()
uri = os.getenv("MONGODB_URL")
client = MongoClient(uri)
db_name = os.getenv("DB_NAME")
db = client[db_name]

classes = list(db.classes.find())
class_ids = [str(c["_id"]) for c in classes]
print(f"Loaded {len(class_ids)} classes")

# Mock the constraints exactly as the user typed
constraints = [
    {
        "type": "faculty_availability",
        "faculty_name": "Siva Kumar",
        "available_days": [],  # Wait, the parser handles this
    }
]

# Just run with no constraints first to see if it's intrinsically infeasible
scheduler = TimetableScheduler(
    db=db,
    working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    periods_per_day=7,
    time_limit_seconds=30,
    custom_constraints=[] 
)
scheduler.load_data(class_ids=class_ids)
scheduler.create_variables()
scheduler.add_constraints()
result = scheduler.solve()
print("Status:", result["status"])
