import requests
import time

def test_backend():
    url = "http://localhost:5002/health"
    max_attempts = 3
    
    print("Testing backend connection...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("✅ Backend is running and healthy!")
                print(f"Response: {response.json()}")
                return True
        except requests.exceptions.ConnectionError:
            print(f"Attempt {attempt + 1}/{max_attempts}: Backend not reachable, retrying...")
            time.sleep(2)
    
    print("❌ Could not connect to backend!")
    return False

if __name__ == "__main__":
    test_backend() 