import os
from pymongo import MongoClient
import ssl
from dotenv import load_dotenv

load_dotenv()

mongo_url = os.getenv("MONGODB_URL")
print(f"Testing connection to: {mongo_url.split('@')[-1]}")

try:
    # Try standard connection
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ Standard connection successful!")
except Exception as e:
    print(f"❌ Standard connection failed: {e}")
    
    print("\nTrying with SSL certificate verification disabled...")
    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000, tlsAllowInvalidCertificates=True)
        client.admin.command('ping')
        print("✅ Connection successful with tlsAllowInvalidCertificates=True!")
    except Exception as e2:
        print(f"❌ Connection with disabled SSL verification also failed: {e2}")

    print("\nChecking DNS resolution...")
    import socket
    try:
        host = mongo_url.split('@')[-1].split('/')[0].split('?')[0]
        print(f"Resolving {host}...")
        ip = socket.gethostbyname(host)
        print(f"IP: {ip}")
    except Exception as e3:
        print(f"❌ DNS resolution failed: {e3}")
