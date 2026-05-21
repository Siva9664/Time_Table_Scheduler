from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"))
db = client['timetable_db']

cls = db.classes.find_one({"name": {"$regex": "1st AIML", "$options": "i"}})
if not cls:
    cls = db.classes.find_one() # fallback

print(f"Class: {cls['name']} {cls.get('section', '')}")

subjects = list(db.subjects.find({"class_id": str(cls['_id'])}))
if not subjects:
    subjects = list(db.subjects.find({"class_id": cls['_id']}))

print(f"Total subjects assigned to this class: {len(subjects)}")
total_hours = 0
for s in subjects:
    hours = s.get('hours_per_week', 0)
    print(f"- {s.get('name')}: {hours} hours")
    total_hours += hours

print(f"Total hours: {total_hours}")
