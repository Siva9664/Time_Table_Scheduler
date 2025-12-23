import urllib.request
import urllib.parse
import json

def test_login_api():
    url = "http://localhost:8000/api/auth/login"
    
    # Test cases
    tests = [
        ("shiva", "shiva123"),
        ("admin", "shiva123")
    ]

    for username, password in tests:
        print(f"\nTesting login for {username}/{password} at {url}...")
        data = urllib.parse.urlencode({"username": username, "password": password}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        try:
            with urllib.request.urlopen(req) as response:
                status = response.getcode()
                body = response.read().decode()
                print(f"Status: {status}")
                print(f"Response: {body}")
        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code}")
            print(f"Response: {e.read().decode()}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    test_login_api()
