import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URL"))
db = client[os.getenv("DB_NAME")]

classes = {str(c["_id"]): f"{c['name']} {c.get('section', '')}" for c in db.classes.find()}
subjects = db.subjects.find()

for s in subjects:
    print(f"Subject: {s.get('name')} (Class: {classes.get(s.get('class_id'), 'Unknown')}) (Lab: {s.get('requires_lab')})")
