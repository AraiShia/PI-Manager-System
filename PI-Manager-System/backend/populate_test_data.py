import requests
import json

products = [
    {
        "product_code": "SO2260001",
        "oe_number": "133325525",
        "factory_code": "1325551",
        "brand": "BrandA",
        "detail_desc": "Test product 1 - Engine Part",
        "category_id": 1,
        "status": 1
    },
    {
        "product_code": "SO1260002",
        "oe_number": "12245334453",
        "factory_code": "1443224",
        "brand": "BrandB",
        "detail_desc": "Test product 2 - Brake System",
        "category_id": 2,
        "status": 1
    },
    {
        "product_code": "SO3360003",
        "oe_number": "1325551",
        "factory_code": "998877",
        "brand": "BrandC",
        "detail_desc": "Test product 3 - Electrical Part",
        "category_id": 1,
        "status": 1
    },
    {
        "product_code": "SO4460004",
        "oe_number": "987654321",
        "factory_code": "1325551",
        "brand": "BrandA",
        "detail_desc": "Test product 4 - Suspension",
        "category_id": 3,
        "status": 1
    }
]

print("Adding test products...")
for product in products:
    try:
        response = requests.post("http://localhost:8000/api/products", json=product)
        print(f"Added: {product['product_code']} - Status: {response.status_code}")
    except Exception as e:
        print(f"Error adding {product['product_code']}: {e}")

print("\nTesting search with keyword '1325551':")
response = requests.get("http://localhost:8000/api/products/search", params={"keyword": "1325551"})
print(f"Results: {response.text}")

print("\nTesting search with keyword 'BrandA':")
response = requests.get("http://localhost:8000/api/products/search", params={"keyword": "BrandA"})
print(f"Results: {response.text}")