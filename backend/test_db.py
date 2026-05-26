from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGODB_URL")
client = MongoClient(uri)
db_name = os.getenv("DB_NAME")
db = client[db_name]

# get semester 5 classes
classes = list(db.classes.find({"semester": 5}))
print("Classes:", [c["name"] for c in classes])

for c in classes:
    subs = list(db.subjects.find({"class_id": str(c["_id"])}))
    print(f"Class {c['name']} has {len(subs)} subjects:")
    for s in subs:
        print(f"  - {s.get('name')}: credits={s.get('credits')}, req_lab={s.get('requires_lab')}, hours={s.get('hours_per_week')}")
