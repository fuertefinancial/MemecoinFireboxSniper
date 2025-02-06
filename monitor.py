# Optional: Create a simple monitoring script
import requests
import time

def check_endpoint(url):
    try:
        response = requests.get(url)
        return response.status_code == 200
    except:
        return False

def main():
    while True:
        if not check_endpoint("http://127.0.0.1:5000"):
            print("Warning: Application appears to be down!")
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main() 