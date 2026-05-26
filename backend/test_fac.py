from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGODB_URL")
client = MongoClient(uri)
db_name = os.getenv("DB_NAME")
db = client[db_name]

for s in db.subjects.find({"class_id": "6a0d33e506abfb8a4bba89dc"}): # AIML 
    fac = db.faculty.find_one({"_id": s["faculty_id"]})
    print(f"Sub: {s['name']}, Fac: {fac['name'] if fac else 'None'}, max_h: {fac.get('max_hours_per_week') if fac else 'N/A'}")
