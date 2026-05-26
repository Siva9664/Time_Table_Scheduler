import urllib.request
import json

url = "http://localhost:8000/api/timetables/generate"
data = {
    "name": "Main Test 001",
    "academic_year": "2024-2028",
    "semester": 5,
    "constraints_text": "Siva Kumar Sir Will not Available From 10:15 am to 12.30 pm and 1.15 to 2.45\nSelvi Man Not Available at 10:15 to 12:30 and 3:00 to 4:30"
}
req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print("Error:", getattr(e, 'read', lambda: str(e))().decode() if hasattr(e, 'read') else str(e))
