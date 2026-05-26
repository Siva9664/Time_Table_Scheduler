from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URL"))
db = client[os.getenv("DB_NAME")]

print("BATCHES:")
for b in db.batches.find():
    print(b.get("name"), b.get("start_time"), b.get("end_time"), b.get("period_duration_mins"))

print("FACULTY UNAVAILABLE SLOTS:")
for f in db.faculty.find():
    if f.get("unavailable_slots"):
        print(f.get("name"), f.get("unavailable_slots"))
