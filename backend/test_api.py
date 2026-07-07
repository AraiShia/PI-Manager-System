import requests
import traceback

try:
    r = requests.get('http://localhost:8081/api/products')
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Exception: {e}")
    traceback.print_exc()