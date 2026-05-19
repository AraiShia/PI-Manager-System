import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, List, Dict, Any
from config import Config

# 全局超时设置
REQUEST_TIMEOUT = 10  # 秒

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
        response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        print(f"DEBUG - GET response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG - GET response: {len(result) if isinstance(result, list) else 'dict'} items")
            return result
        except Exception as e:
            print(f"DEBUG - GET request failed: {str(e)}")
            raise

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - POST request: {url}")
        response = self.session.post(url, json=data, timeout=REQUEST_TIMEOUT)
        print(f"DEBUG - POST response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG - POST response: OK")
            return result
        except Exception as e:
            print(f"DEBUG - POST request failed: {str(e)}")
            raise

    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - PUT request: {url}")
        response = self.session.put(url, json=data, timeout=REQUEST_TIMEOUT)
        print(f"DEBUG - PUT response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG - PUT response: OK")
            return result
        except Exception as e:
            print(f"DEBUG - PUT request failed: {str(e)}")
            raise

    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - PATCH request: {url}")
        response = self.session.patch(url, json=data, timeout=REQUEST_TIMEOUT)
        print(f"DEBUG - PATCH response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG - PATCH response: OK")
            return result
        except Exception as e:
            print(f"DEBUG - PATCH request failed: {str(e)}")
            raise

    def delete(self, endpoint: str) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        print(f"DEBUG - DELETE request: {url}")
        response = self.session.delete(url, timeout=REQUEST_TIMEOUT)
        print(f"DEBUG - DELETE response status: {response.status_code}")
        try:
            response.raise_for_status()
            if response.content:
                result = response.json()
                print(f"DEBUG - DELETE response: OK")
                return result
            return {}
        except Exception as e:
            print(f"DEBUG - DELETE request failed: {str(e)}")
            raise

    def post_files(self, endpoint: str, files: Dict) -> Dict[str, Any]:
        """上传文件"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        response = self.session.post(url, files=files, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def upload_image(self, file_path: str, product_id: int = None) -> str:
        """上传图片"""
        import os
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {"files": (filename, f, "image/jpeg")}
            params = {}
            if product_id:
                params["product_id"] = product_id
            url = f"{self.base_url}/api/images/upload"
            # 复制主session的headers到临时session
            temp_session = requests.Session()
            temp_session.headers.update(self.session.headers)
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
    
    def get_product_schemes(self, product_id: int) -> List[Dict]:
        """获取产品的供应商方案列表"""
        return self.get(f"/products/{product_id}/schemes")
    
    def create_product_scheme(self, product_id: int, scheme_data: Dict) -> Dict:
        """为产品创建供应商方案"""
        return self.post(f"/products/{product_id}/schemes", scheme_data)
    
    def delete_product_scheme(self, product_id: int, scheme_id: int) -> Dict:
        """删除供应商方案"""
        return self.delete(f"/products/{product_id}/schemes/{scheme_id}")
    
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
    
    def update_pi_status(self, pi_id: int, status: int) -> Dict:
        """更新PI单状态"""
        return self.put(f"/pi/{pi_id}/status", {"status": status})
    
    def get_pi_detail(self, pi_id: int) -> Dict:
        return self.get(f"/pi/{pi_id}")
    
    def batch_delete_pi(self, pi_ids: List[int]) -> Dict:
        return self.post("/pi/batch-delete", pi_ids)
    
    def get_purchase_orders(self) -> List[Dict]:
        return self.get("/purchase-orders")

    def create_purchase(self, data: Dict) -> Dict:
        return self.post("/purchase-orders", data)

    def update_purchase(self, po_id: int, data: Dict) -> Dict:
        return self.put(f"/purchase-orders/{po_id}", data)

    def get_purchase_order_detail(self, po_id: int) -> Dict:
        return self.get(f"/purchase-orders/{po_id}")

    def inbound_purchase(self, po_id: int, product_id: int, quantity: float, inspector: str = None) -> Dict:
        return self.post(f"/inventory/inbound", {
            "po_id": po_id, "product_id": product_id, "quantity": quantity, "inspector": inspector
        })

    def create_inbound_batch(self, data: Dict) -> Dict:
        return self.post("/inventory/inbound-batch", data)

    def get_inbound_batches(self, po_id: int = None) -> List[Dict]:
        params = {}
        if po_id:
            params["po_id"] = po_id
        return self.get("/inventory/inbound-batch", params=params)

    def confirm_inbound_batch(self, batch_id: int, inspector: str = None) -> Dict:
        return self.post(f"/inventory/inbound-batch/{batch_id}/confirm", {"inspector": inspector})

    def get_inventories(self, product_id: int = None, customer_id: int = None, stock_type: int = None) -> List[Dict]:
        params = {}
        if product_id:
            params["product_id"] = product_id
        if customer_id:
            params["customer_id"] = customer_id
        if stock_type:
            params["stock_type"] = stock_type
        return self.get("/inventory", params=params)

    def get_customer_payments(self, pi_id: int = None, customer_id: int = None) -> List[Dict]:
        params = {}
        if pi_id:
            params["pi_id"] = pi_id
        if customer_id:
            params["customer_id"] = customer_id
        return self.get("/payments/receivables", params=params)

    def create_customer_payment(self, data: Dict) -> Dict:
        return self.post("/payments/receivables", data)

    def update_customer_payment(self, payment_id: int, data: Dict) -> Dict:
        return self.put(f"/payments/receivables/{payment_id}", data)

    def get_supplier_payments(self, po_id: int = None, supplier_id: int = None) -> List[Dict]:
        params = {}
        if po_id:
            params["po_id"] = po_id
        if supplier_id:
            params["supplier_id"] = supplier_id
        return self.get("/payments/payables", params=params)

    def create_supplier_payment(self, data: Dict) -> Dict:
        return self.post("/payments/payables", data)

    def update_supplier_payment(self, payment_id: int, data: Dict) -> Dict:
        return self.put(f"/payments/payables/{payment_id}", data)

    def get_supplier_payment(self, payment_id: int) -> Dict:
        """获取单个供应商付款详情（包含stages）"""
        return self.get(f"/payments/payables/{payment_id}")

    def get_supplier_payment_stages(self, payment_id: int) -> List[Dict]:
        return self.get(f"/payments/payables/{payment_id}/stages")

    def update_supplier_payment_stage(self, stage_id: int, paid_amount: float = None) -> Dict:
        return self.post(f"/payments/payables/stages/{stage_id}", {"paid_amount": paid_amount})

    def get_shipments(self, pi_id: int = None, status: int = None) -> List[Dict]:
        params = {}
        if pi_id:
            params["pi_id"] = pi_id
        if status:
            params["status"] = status
        return self.get("/shipments", params=params)

    def get_shipment(self, shipment_id: int) -> Dict:
        """获取单个出货详情（包含stages）"""
        return self.get(f"/shipments/{shipment_id}")

    def create_shipment(self, data: Dict) -> Dict:
        return self.post("/shipments", data)

    def update_shipment(self, shipment_id: int, data: Dict) -> Dict:
        return self.put(f"/shipments/{shipment_id}", data)

    def get_purchases_by_supplier(self, supplier_id: int) -> List[Dict]:
        return self.get(f"/purchase-orders/by-supplier/{supplier_id}")

    def create_inventory(self, data: Dict) -> Dict:
        return self.post("/inventory", data)

    def update_inventory(self, inventory_id: int, data: Dict) -> Dict:
        return self.put(f"/inventory/{inventory_id}", data)
    
    def delete_inventory(self, inventory_id: int) -> Dict:
        return self.delete(f"/inventory/{inventory_id}")
    
    def get_product_inventory(self, product_id: int) -> Dict:
        """获取单个产品的库存信息"""
        inventories = self.get("/inventory", params={"product_id": product_id})
        total_quantity = 0
        if inventories:
            for inv in inventories:
                total_quantity += float(inv.get('quantity', 0) or 0)
        return {"product_id": product_id, "total_quantity": total_quantity}
    
    def get_all_inventory_summary(self) -> Dict[int, float]:
        """获取所有产品的库存汇总"""
        inventories = self.get("/inventory")
        summary = {}
        if inventories:
            for inv in inventories:
                pid = inv.get('product_id')
                qty = float(inv.get('quantity', 0) or 0)
                if pid:
                    summary[pid] = summary.get(pid, 0) + qty
        return summary
    
    def get_product_logs(self) -> Dict:
        """获取按产品分组的最近变更记录"""
        return self.get("/inventory/product-logs")

    def get_product_suppliers(self, product_id: int) -> List[Dict]:
        return self.get(f"/product-suppliers/{product_id}")

    def add_product_supplier_full(self, data: Dict) -> Dict:
        return self.post("/product-suppliers", data)

    def update_product_supplier(self, ps_id: int, data: Dict) -> Dict:
        return self.put(f"/product-suppliers/{ps_id}", data)

    def delete_product_supplier(self, ps_id: int) -> Dict:
        return self.delete(f"/product-suppliers/{ps_id}")

    # ========== PI 扩展 ==========

    def get_pi_detail(self, pi_id: int) -> Dict:
        """获取PI详情（包含明细和付款阶段）"""
        return self.get(f"/pi/detail/{pi_id}")

    def export_pi_excel(self, pi_id: int) -> bytes:
        """导出PI为Excel文件"""
        url = self._build_url(f"/pi/export/{pi_id}")
        response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content

    def get_price_history(self, customer_id: int, product_id: int) -> Dict:
        """获取历史价格"""
        return self.get(f"/pi/price-history/{customer_id}/{product_id}")

    # ========== 采购扩展 ==========

    def confirm_purchase(self, po_id: int) -> Dict:
        """确认采购单"""
        return self.post(f"/purchase-orders/{po_id}/confirm", {})

    def inbound_purchase_order(self, po_id: int) -> Dict:
        """采购单入库"""
        return self.post(f"/purchase-orders/{po_id}/inbound", {})

    # ========== 出货扩展 ==========

    def confirm_shipment(self, shipment_id: int) -> Dict:
        """确认出货"""
        return self.post(f"/shipments/{shipment_id}/confirm", {})

    def get_shipment_stages(self, shipment_id: int) -> List[Dict]:
        """获取出货阶段列表"""
        return self.get(f"/shipments/{shipment_id}/stages")

    def create_shipment_stage(self, shipment_id: int, data: Dict) -> Dict:
        """独立创建出货阶段"""
        return self.post(f"/shipments/{shipment_id}/stages", data)

    def update_shipment_stage(self, shipment_id: int, stage_id: int, data: Dict) -> Dict:
        """更新出货阶段"""
        return self.put(f"/shipments/{shipment_id}/stages/{stage_id}", data)

    def delete_shipment_stage(self, shipment_id: int, stage_id: int) -> Dict:
        """删除出货阶段"""
        return self.delete(f"/shipments/{shipment_id}/stages/{stage_id}")

    # ========== 库存扩展 ==========

    def transfer_inventory(self, data: Dict) -> Dict:
        """库存调拨"""
        return self.post("/inventory/transfer", data)

    def get_inventory_logs(self, product_id: int = None, customer_id: int = None) -> List[Dict]:
        """获取库存日志"""
        params = {}
        if product_id:
            params["product_id"] = product_id
        if customer_id:
            params["customer_id"] = customer_id
        return self.get("/inventory/logs", params=params)

    def get_inventory_aging(self, days_threshold: int = 60) -> List[Dict]:
        """获取库存账龄"""
        return self.get("/inventory/aging", params={"days_threshold": days_threshold})

    def get_inventory_dashboard(self) -> Dict:
        """获取库存仪表盘数据"""
        return self.get("/inventory/dashboard")

    # ========== 用户 ==========

    def logout(self) -> Dict:
        """退出登录"""
        return self.post("/auth/logout", {})

    # ========== 产品扩展 ==========

    def update_product_status(self, product_id: int, status: int) -> Dict:
        """更新产品状态"""
        return self.patch(f"/products/{product_id}/status", {"status": status})

    # ========== 报价单 ==========

    def get_quotes(self, status: int = None, customer_id: int = None) -> List[Dict]:
        """获取报价单列表"""
        params = {}
        if status is not None:
            params["status"] = status
        if customer_id is not None:
            params["customer_id"] = customer_id
        return self.get("/quotes", params=params)

    def get_quote(self, quote_id: int) -> Dict:
        """获取报价单详情"""
        return self.get(f"/quotes/{quote_id}")

    def create_quote(self, data: Dict) -> Dict:
        """创建报价单"""
        return self.post("/quotes", data)

    def update_quote(self, quote_id: int, data: Dict) -> Dict:
        """更新报价单"""
        return self.put(f"/quotes/{quote_id}", data)

    def delete_quote(self, quote_id: int) -> Dict:
        """删除报价单"""
        return self.delete(f"/quotes/{quote_id}")
    
    def batch_delete_quotes(self, quote_ids: List[int]) -> Dict:
        """批量删除报价单"""
        return self.post("/quotes/batch-delete", quote_ids)

    def convert_quote_to_pi(self, quote_id: int) -> Dict:
        """将报价单转为PI"""
        return self.post(f"/quotes/{quote_id}/convert", {})

    def update_quote_status(self, quote_id: int, status: int) -> Dict:
        """更新报价单状态"""
        return self.post(f"/quotes/{quote_id}/status", {"status": status})

    def get_customer_products(self, customer_id: int) -> List[Dict]:
        """获取客户采购过的产品及其最后一次采购价格"""
        return self.get(f"/quotes/customer/{customer_id}/products")

    def get_latest_price(self, customer_id: int, product_id: int) -> Dict:
        """获取客户采购该产品的最后一次价格"""
        return self.get(f"/quotes/customer/{customer_id}/product/{product_id}/price")

    # ========== 客户回复 ==========

    def get_customer_replies(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """获取所有客户回复"""
        return self.get("/customer-replies", params={"skip": skip, "limit": limit})

    def get_customer_replies_by_pi(self, pi_id: int) -> List[Dict]:
        """获取某PI的所有客户回复"""
        return self.get(f"/customer-replies/pi/{pi_id}")

    def get_latest_customer_reply(self, pi_id: int) -> Optional[Dict]:
        """获取某PI的最新客户回复"""
        return self.get(f"/customer-replies/pi/{pi_id}/latest")

    def get_customer_replies_by_customer(self, customer_id: int) -> List[Dict]:
        """获取某客户的所有回复"""
        return self.get(f"/customer-replies/customer/{customer_id}")

    def create_customer_reply(self, data: Dict) -> Dict:
        """创建客户回复"""
        return self.post("/customer-replies", data)

    def update_customer_reply(self, reply_id: int, data: Dict) -> Dict:
        """更新客户回复"""
        return self.put(f"/customer-replies/{reply_id}", data)

    def delete_customer_reply(self, reply_id: int) -> Dict:
        """删除客户回复"""
        return self.delete(f"/customer-replies/{reply_id}")

    # ========== 产品OE关联 ==========

    def get_product_oes(self, product_id: int) -> List[Dict]:
        """获取产品的所有OE号"""
        return self.get(f"/product-oes/product/{product_id}")

    def get_product_oes_batch(self, product_ids: List[int]) -> List[Dict]:
        """批量获取多个产品的OE号（优化性能）"""
        if not product_ids:
            return []
        ids_str = ",".join(str(x) for x in product_ids)
        return self.get(f"/product-oes/batch?product_ids={ids_str}")

    def get_primary_oe(self, product_id: int) -> Optional[Dict]:
        """获取产品的主OE号"""
        return self.get(f"/product-oes/product/{product_id}/primary")

    def create_product_oe(self, data: Dict) -> Dict:
        """创建产品OE关联"""
        return self.post("/product-oes", data)

    def update_product_oe(self, oe_id: int, data: Dict) -> Dict:
        """更新产品OE"""
        return self.put(f"/product-oes/{oe_id}", data)

    def delete_product_oe(self, oe_id: int) -> Dict:
        """删除产品OE"""
        return self.delete(f"/product-oes/{oe_id}")

    def set_primary_oe(self, product_id: int, oe_id: int) -> Dict:
        """设置主OE号"""
        return self.post(f"/product-oes/product/{product_id}/set-primary/{oe_id}", {})

    # ========== 产品-客户关联 ==========

    def get_product_customers(self, product_id: int) -> List[Dict]:
        """获取产品的所有客户关联"""
        return self.get(f"/product-customers/product/{product_id}")

    def get_product_customers_batch(self, product_ids: List[int]) -> List[Dict]:
        """批量获取多个产品的客户关联（优化性能）"""
        if not product_ids:
            return []
        ids_str = ",".join(str(x) for x in product_ids)
        return self.get(f"/product-customers/batch?product_ids={ids_str}")

    def get_customer_products(self, customer_id: int) -> List[Dict]:
        """获取客户的所有产品关联"""
        return self.get(f"/product-customers/customer/{customer_id}")

    def get_product_customer(self, product_id: int, customer_id: int) -> Optional[Dict]:
        """获取产品-客户的特定关联"""
        return self.get(f"/product-customers/product/{product_id}/customer/{customer_id}")

    def create_product_customer(self, data: Dict) -> Dict:
        """创建产品-客户关联"""
        return self.post("/product-customers", data)

    def update_product_customer(self, pc_id: int, data: Dict) -> Dict:
        """更新产品-客户关联"""
        return self.put(f"/product-customers/{pc_id}", data)

    def delete_product_customer(self, pc_id: int) -> Dict:
        """删除产品-客户关联"""
        return self.delete(f"/product-customers/{pc_id}")

    # ========== 系统设置 ==========

    def get_profit_margin(self) -> Dict:
        """获取毛利率设置"""
        return self.get("/settings/profit-margin/get")

    def set_profit_margin(self, profit_margin: float) -> Dict:
        """设置毛利率"""
        return self.post(f"/settings/profit-margin/set?profit_margin={profit_margin}", {})

    def get_exchange_rate(self) -> Dict:
        """获取汇率设置"""
        return self.get("/settings/exchange-rate/get")

    def set_exchange_rate(self, exchange_rate: float) -> Dict:
        """设置汇率"""
        return self.post(f"/settings/exchange-rate/set?exchange_rate={exchange_rate}", {})

    def get_all_globals(self) -> Dict:
        """获取所有全局变量"""
        return self.get("/settings/all")
