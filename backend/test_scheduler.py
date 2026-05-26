from pymongo import MongoClient
from app.services.scheduler import TimetableScheduler

client = MongoClient("mongodb://localhost:27017/")
db = client["timetable_db"]

# Attempt to load data and run scheduler for semester 5
# To simulate the frontend, we need the exact class ids or batch ids.
# Let's just find the "Main Test 001" timetable config if it exists, or run it on all semester 5 classes.
classes = list(db.classes.find({"semester": 5}))
class_ids = [str(c["_id"]) for c in classes]

scheduler = TimetableScheduler(
    db=db,
    working_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    periods_per_day=7,
    time_limit_seconds=10,
    custom_constraints=[]  # We'll test without AI constraints first
)
scheduler.load_data(class_ids=class_ids)
scheduler.create_variables()
scheduler.add_constraints()
result = scheduler.solve()
print("Status:", result["status"])
