import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, List, Dict, Any
from config import Config

class ApiClient:
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or Config.API_BASE_URL).rstrip("/")
        self.session = self._create_session()
        self.db_config = None

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.timeout = 5  # 设置超时时间为5秒
        return session

    def set_db_config(self, db_config: Dict):
        self.db_config = db_config
        if self.db_config:
            self.session.headers.update({
                "X-DB-Host": self.db_config.get("db_host", ""),
                "X-DB-Port": str(self.db_config.get("db_port", 3306)),
                "X-DB-User": self.db_config.get("db_user", ""),
                "X-DB-Password": self.db_config.get("db_password", ""),
                "X-DB-Name": self.db_config.get("db_name", "")
            })

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        return f"{self.base_url}/api/{endpoint}"

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - GET request: {url}, params: {params}")
        response = self.session.get(url, params=params)
        print(f"DEBUG - GET response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG - GET response data: {result}")
            return result
        except Exception as e:
            print(f"DEBUG - GET request failed: {str(e)}")
            if response.content:
                print(f"DEBUG - Response content: {response.text}")
            raise

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - POST request: {url}")
        print(f"DEBUG - POST data: {data}")
        response = self.session.post(url, json=data)
        print(f"DEBUG - POST response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG - POST response data: {result}")
            return result
        except Exception as e:
            print(f"DEBUG - POST request failed: {str(e)}")
            if response.content:
                print(f"DEBUG - Response content: {response.text}")
            raise

    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - PUT request: {url}")
        print(f"DEBUG - PUT data: {data}")
        response = self.session.put(url, json=data)
        print(f"DEBUG - PUT response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG - PUT response data: {result}")
            return result
        except Exception as e:
            print(f"DEBUG - PUT request failed: {str(e)}")
            if response.content:
                print(f"DEBUG - Response content: {response.text}")
            raise

    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - PATCH request: {url}, data: {data}")
        response = self.session.patch(url, json=data)
        print(f"DEBUG - PATCH response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG - PATCH response data: {result}")
            return result
        except Exception as e:
            print(f"DEBUG - PATCH request failed: {str(e)}")
            if response.content:
                print(f"DEBUG - Response content: {response.text}")
            raise

    def delete(self, endpoint: str) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - DELETE request: {url}")
        response = self.session.delete(url)
        print(f"DEBUG - DELETE response status: {response.status_code}")
        try:
            response.raise_for_status()
            if response.content:
                result = response.json()
                print(f"DEBUG - DELETE response data: {result}")
                return result
            return {}
        except Exception as e:
            print(f"DEBUG - DELETE request failed: {str(e)}")
            if response.content:
                print(f"DEBUG - Response content: {response.text}")
            raise

    def post_files(self, endpoint: str, files: Dict) -> Dict[str, Any]:
        """上传文件"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        response = self.session.post(url, files=files)
        response.raise_for_status()
        return response.json()

    def upload_image(self, file_path: str, product_id: int = None) -> str:
        """上传图片"""
        import os
        # 只提取文件名，避免完整路径导致的问题
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {"files": (filename, f, "image/jpeg")}
            params = {}
            if product_id:
                params["product_id"] = product_id
            url = f"{self.base_url}/api/images/upload"
            # 创建一个临时session用于文件上传，避免Content-Type冲突
            temp_session = requests.Session()
            response = temp_session.post(url, files=files, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result.get("files"):
                return result["files"][0]
        return None

    def set_product_default_image(self, product_id: int, image_url: str) -> Dict:
        """设置产品默认图片"""
        return self.post(f"/images/{product_id}/default", {"image_url": image_url})

    def get_products(self, db_config: Dict = None) -> List[Dict]:
        if db_config:
            self.set_db_config(db_config)
        return self.get("/products")

    def search_products(self, keyword: str = "", category_id: int = None, status: int = None) -> List[Dict]:
        params = {}
        if keyword:
            params["keyword"] = keyword
        if category_id is not None:
            params["category_id"] = category_id
        if status is not None:
            params["status"] = status
        return self.get("/products/search", params=params)

    def create_product(self, data: Dict) -> Dict:
        return self.post("/products", data)

    def update_product(self, product_id: int, data: Dict) -> Dict:
        return self.put(f"/products/{product_id}", data)

    def toggle_product_status(self, product_id: int) -> Dict:
        return self.patch(f"/products/{product_id}/status")

    def confirm_product_import(self, product_id: int) -> Dict:
        """确认产品导入"""
        return self.patch(f"/products/{product_id}/confirm-import")

    def cancel_product_import(self, product_id: int) -> Dict:
        """取消产品导入确认"""
        return self.patch(f"/products/{product_id}/cancel-import")

    def delete_product(self, product_id: int) -> Dict:
        return self.delete(f"/products/{product_id}")

    def import_products(self, data: List[Dict]) -> Dict:
        return self.post("/products/import", {"products": data})

    def get_product_images(self, product_id: int) -> List[Dict]:
        return self.get(f"/products/{product_id}/images")

    def get_product_detail(self, product_id: int) -> Dict:
        return self.get(f"/products/{product_id}")

    def get_customers(self) -> List[Dict]:
        return self.get("/customers")

    def create_customer(self, data: Dict) -> Dict:
        return self.post("/customers", data)

    def update_customer(self, customer_id: int, data: Dict) -> Dict:
        return self.put(f"/customers/{customer_id}", data)

    def delete_customer(self, customer_id: int) -> Dict:
        return self.delete(f"/customers/{customer_id}")

    def search_customers(self, keyword: str = "", country: str = None) -> List[Dict]:
        params = {}
        if keyword:
            params["keyword"] = keyword
        if country:
            params["country"] = country
        return self.get("/customers/search", params=params)

    def toggle_customer_status(self, customer_id: int) -> Dict:
        return self.patch(f"/customers/{customer_id}/status")

    def get_customer_detail(self, customer_id: int) -> Dict:
        return self.get(f"/customers/{customer_id}")

    def get_customer_addresses(self, customer_id: int) -> List[Dict]:
        return self.get(f"/customers/{customer_id}/addresses")

    def create_customer_address(self, customer_id: int, data: Dict) -> Dict:
        return self.post(f"/customers/{customer_id}/addresses", data)

    def update_customer_address(self, customer_id: int, address_id: int, data: Dict) -> Dict:
        return self.put(f"/customers/{customer_id}/addresses/{address_id}", data)

    def delete_customer_address(self, customer_id: int, address_id: int) -> Dict:
        return self.delete(f"/customers/{customer_id}/addresses/{address_id}")

    def get_customer_contacts(self, customer_id: int) -> List[Dict]:
        return self.get(f"/customers/{customer_id}/contacts")

    def create_customer_contact(self, customer_id: int, data: Dict) -> Dict:
        return self.post(f"/customers/{customer_id}/contacts", data)

    def update_customer_contact(self, customer_id: int, contact_id: int, data: Dict) -> Dict:
        return self.put(f"/customers/{customer_id}/contacts/{contact_id}", data)

    def delete_customer_contact(self, customer_id: int, contact_id: int) -> Dict:
        return self.delete(f"/customers/{customer_id}/contacts/{contact_id}")

    def get_customer_pi_list(self, customer_id: int) -> List[Dict]:
        return self.get(f"/customers/{customer_id}/pi-orders")

    def get_suppliers(self) -> List[Dict]:
        return self.get("/suppliers")

    def create_supplier(self, data: Dict) -> Dict:
        return self.post("/suppliers", data)

    def update_supplier(self, supplier_id: int, data: Dict) -> Dict:
        return self.put(f"/suppliers/{supplier_id}", data)

    def delete_supplier(self, supplier_id: int) -> Dict:
        return self.delete(f"/suppliers/{supplier_id}")

    def get_supplier_detail(self, supplier_id: int) -> Dict:
        return self.get(f"/suppliers/{supplier_id}")

    def get_provinces(self) -> List[str]:
        return self.get("/suppliers/provinces")

    def get_cities(self, province: str) -> List[str]:
        return self.get(f"/suppliers/cities/{province}")

    def get_pi_orders(self) -> List[Dict]:
        return self.get("/pi")

    def create_pi(self, data: Dict) -> Dict:
        return self.post("/pi", data)

    def update_pi(self, pi_id: int, data: Dict) -> Dict:
        return self.put(f"/pi/{pi_id}", data)

    def get_purchase_orders(self) -> List[Dict]:
        return self.get("/purchase-orders")

    def create_purchase(self, data: Dict) -> Dict:
        return self.post("/purchase-orders", data)

    def update_purchase(self, po_id: int, data: Dict) -> Dict:
        return self.put(f"/purchase-orders/{po_id}", data)