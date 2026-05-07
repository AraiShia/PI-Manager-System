import sys
import requests

print("Adding test products...")

products = [
    {
        "product_code": "SO2260001",
        "oe_number": "133325525",
        "factory_code": "1325551",
        "brand": "TestBrand",
        "detail_desc": "Test product 1",
        "status": 1
    },
    {
        "product_code": "SO1260002",
        "oe_number": "12245334453",
        "factory_code": "1443224",
        "brand": "BrandB",
        "detail_desc": "Test product 2",
        "status": 1
    },
    {
        "product_code": "SO3360003",
        "oe_number": "1325551",
        "factory_code": "998877",
        "brand": "BrandC",
        "detail_desc": "Test product 3",
        "status": 1
    }
]

for product in products:
    try:
        response = requests.post("http://localhost:8000/api/products", json=product)
        print(f"Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

print("\nTesting search...")
response = requests.get("http://localhost:8000/api/products/search", params={"oe_number": "1325551"})
print(f"Search result: {response.text}")