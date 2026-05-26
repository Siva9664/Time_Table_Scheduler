from pymongo import MongoClient
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv()
uri = os.getenv("MONGODB_URL")
client = MongoClient(uri)
db_name = os.getenv("DB_NAME")
db = client[db_name]

for c in db.classes.find({"semester": 5}):
    print(f"Class: {c['name']}")
    for s in db.subjects.find({"class_id": str(c["_id"])}):
        fid = s.get("faculty_id")
        fac = None
        if fid:
            try:
                fac = db.faculty.find_one({"_id": ObjectId(fid)})
            except:
                fac = db.faculty.find_one({"_id": fid})
        print(f"  Sub: {s['name']}, Fac: {fac['name'] if fac else 'None'}, max_h: {fac.get('max_hours_per_week') if fac else 'N/A'}")
