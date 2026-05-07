import requests

# 添加测试产品数据
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
        response.raise_for_status()
        print(f"Added product: {product['product_code']}")
    except Exception as e:
        print(f"Error adding product {product['product_code']}: {e}")

print("\nTesting search API:")
response = requests.get("http://localhost:8000/api/products/search", params={"oe_number": "1325551"})
print(f"Search results for '1325551': {response.json()}")