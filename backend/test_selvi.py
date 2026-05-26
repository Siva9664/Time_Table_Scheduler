from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGODB_URL")
client = MongoClient(uri)
db_name = os.getenv("DB_NAME")
db = client[db_name]

fac = db.faculty.find_one({"name": "Selvi Mam"})
if not fac:
    print("Faculty not found")
else:
    subs = db.subjects.find({"faculty_id": str(fac["_id"])})
    for s in subs:
        c = db.classes.find_one({"_id": s["class_id"]})
        print(f"Sub: {s['name']}, Class: {c['name'] if c else 'None'}, Hours: {s.get('hours_per_week')}")
