import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout as RequestsTimeout
from urllib3.util.retry import Retry
from typing import Optional, List, Dict, Any, Callable
from threading import Thread
from config import Config
from .logging_config import setup_logger

# 全局超时设置
REQUEST_TIMEOUT = 10  # 秒
DEFAULT_TIMEOUT = 10
LARGE_RESPONSE_THRESHOLD = 1024 * 1024  # 1MB


class PackageApiError(Exception):
    """包装规格 API 错误基类"""
    pass


class PackageNotFoundError(PackageApiError):
    """包装规格不存在（404）"""
    pass


class PackageNetworkError(PackageApiError):
    """网络错误"""
    pass


class ApiClient:
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or Config.API_BASE_URL).rstrip("/")
        self.session = self._create_session()
        self.db_config = None
        self._logger = setup_logger("ApiClient")

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

    def _calculate_timeout(self, response: requests.Response = None) -> int:
        """根据响应大小动态计算超时时间"""
        timeout = DEFAULT_TIMEOUT

        if response is not None:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > LARGE_RESPONSE_THRESHOLD:
                        timeout = max(30, size // (100 * 1024))
                        self._logger.debug(f"大文件响应 {size} bytes, 超时调整为 {timeout}s")
                except ValueError:
                    pass

        return timeout

    def is_alive(self) -> bool:
        """检查 API 连接是否正常"""
        try:
            response = self.session.get(self.base_url, timeout=5)
            return response.status_code < 500
        except Exception as e:
            self._logger.warning(f"健康检查失败: {str(e)}")
            return False

    def refresh_session(self):
        """刷新会话（断线重连）"""
        self._logger.info("刷新 API 会话...")
        self.session = self._create_session()
        if self.db_config:
            self.set_db_config(self.db_config)
        self._logger.info("API 会话已刷新")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        self._logger.debug(f"GET request: {endpoint}, params: {params}")
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            self._logger.debug(f"GET response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            self._logger.debug(f"GET response: {len(result) if isinstance(result, list) else 'dict'} items")
            return result
        except Exception as e:
            self._logger.error(f"GET request failed: {str(e)}")
            raise

    def post(self, endpoint: str, data: Dict[str, Any] = None, files: Dict = None, json: Dict[str, Any] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        self._logger.debug(f"POST request: {endpoint}")

        if files:
            import requests as req
            if self.token:
                headers = {"Authorization": f"Bearer {self.token}"}
            else:
                headers = {}

            response = req.post(url, files=files, headers=headers, timeout=60)
        else:
            # 优先使用 json 参数发送 JSON body；若未指定则将 data 转为 json
            response = self.session.post(
                url,
                json=json if json is not None else data,
                timeout=REQUEST_TIMEOUT
            )

        self._logger.debug(f"POST response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            self._logger.debug(f"POST response: OK")
            return result
        except Exception as e:
            self._logger.error(f"POST request failed: {str(e)}")
            raise

    def post_raw(self, endpoint: str, data: Dict[str, Any] = None) -> requests.Response:
        """POST 返回原始响应（含二进制内容）"""
        url = self._build_url(endpoint)
        self._logger.debug(f"POST raw request: {endpoint}")
        try:
            response = self.session.post(url, json=data, timeout=REQUEST_TIMEOUT)
            self._logger.debug(f"POST raw response status: {response.status_code}")
            response.raise_for_status()
            return response
        except Exception as e:
            self._logger.error(f"POST raw request failed: {str(e)}")
            raise

    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        self._logger.debug(f"PUT request: {endpoint}")
        response = self.session.put(url, json=data, timeout=REQUEST_TIMEOUT)
        self._logger.debug(f"PUT response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            self._logger.debug(f"PUT response: OK")
            return result
        except Exception as e:
            self._logger.error(f"PUT request failed: {str(e)}")
            raise

    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        self._logger.debug(f"PATCH request: {endpoint}")
        response = self.session.patch(url, json=data, timeout=REQUEST_TIMEOUT)
        self._logger.debug(f"PATCH response status: {response.status_code}")
        try:
            response.raise_for_status()
            result = response.json()
            self._logger.debug(f"PATCH response: OK")
            return result
        except Exception as e:
            self._logger.error(f"PATCH request failed: {str(e)}")
            raise

    def delete(self, endpoint: str) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        self._logger.debug(f"DELETE request: {endpoint}")
        response = self.session.delete(url, timeout=REQUEST_TIMEOUT)
        self._logger.debug(f"DELETE response status: {response.status_code}")
        if response.status_code >= 400:
            self._logger.warning(f"DELETE response body: {response.text}")
        try:
            response.raise_for_status()
            if response.content:
                result = response.json()
                self._logger.debug(f"DELETE response: {result}")
                return result
            return {}
        except Exception as e:
            self._logger.error(f"DELETE request failed: {str(e)}")
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
    
    def search_products(self, keyword: str = "", category_id: int = None, category_code: str = None, status: int = None, customer_id: int = None) -> List[Dict]:
        params = {}
        if keyword:
            params["keyword"] = keyword
        # 2026-06-14 前端下拉框存的是 code 字符串（如 'C01'），不能用 category_id (int) 路径
        if category_code is not None:
            params["category_code"] = category_code
        elif category_id is not None:
            params["category_id"] = category_id
        if status is not None:
            params["status"] = status
        if customer_id is not None:
            params["customer_id"] = customer_id
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

    def confirm_temporary_product(self, product_id: int, product_data: Dict) -> Dict:
        """将临时产品转为正式产品
        
        Args:
            product_id: 产品ID
            product_data: 完整的产品数据字典
            
        Returns:
            更新后的产品数据字典
            
        Raises:
            ValueError: 产品已被其他用户转正或不存在
            requests.exceptions.Timeout: 网络超时
        """
        try:
            response = self.session.post(
                f"{self.base_url}/products/{product_id}/confirm",
                json=product_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 409:
                raise ValueError("该产品已被其他用户转正")
            elif response.status_code == 404:
                raise ValueError("产品不存在")
            else:
                raise Exception(f"转正失败: {response.status_code}")
                
        except requests.exceptions.Timeout:
            raise Exception("网络超时，请检查网络连接")

    def cancel_product_import(self, product_id: int) -> Dict:
        """取消产品导入确认"""
        return self.patch(f"/products/{product_id}/cancel-import")

    def get_customer_product_by_id(self, product_id: int) -> Optional[Dict]:
        """获取单个客户产品（含完整字段）"""
        return self.get(f"/customer-products/{product_id}")

    def delete_product(self, product_id: int) -> Dict:
        """删除客户产品"""
        return self.delete(f"/customer-products/{product_id}")

    def import_products(self, data: List[Dict]) -> Dict:
        return self.post("/products/import", {"products": data})

    def get_product_images(self, product_id: int) -> List[Dict]:
        return self.get(f"/products/{product_id}/images")

    def get_product_detail(self, product_id: int) -> Dict:
        return self.get(f"/products/{product_id}")

    def create_temporary_product(self, data: dict) -> dict:
        return self.post("/products/temporary", data)

    def confirm_temporary_product(self, product_id: int, data: dict) -> dict:
        return self.post(f"/products/{product_id}/confirm", data)

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

    def find_or_create_supplier(self, supplier_name: str, dept_id: str = "S",
                                 contact_person: str = None, phone: str = None,
                                 address: str = None) -> Dict:
        """2026-06-23：按名称查找或创建供应商（用于线上采购自动建立 supplier_id）

        返回：{"id": int, "supplier_name": str, "supplier_code": str, "created": bool}
        """
        payload = {
            "supplier_name": supplier_name,
            "dept_id": dept_id,
            "contact_person": contact_person or "",
            "phone": phone or "",
            "address": address or "",
        }
        return self.post("/suppliers/find-or-create", payload)

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

    def generate_pi(self, order_id: int, force_regenerate: bool = False) -> Dict:
        """为订单生成 PI 号
        
        Args:
            order_id: 订单ID
            force_regenerate: 是否强制重新生成
            
        Returns:
            {"success": bool, "pi_id": int, "pi_no": str, "message": str}
        """
        endpoint = f"/orders/{order_id}/generate-pi?force_regenerate={'true' if force_regenerate else 'false'}"
        return self.post(endpoint)

    def update_pi(self, pi_id: int, data: Dict) -> Dict:
        return self.put(f"/pi/{pi_id}", data)
    
    def update_pi_status(self, pi_id: int, status: int) -> Dict:
        """更新PI单状态"""
        return self.put(f"/pi/{pi_id}/status", {"status": status})

    def update_pi_storage_status(self, pi_id: int, storage_status: str = None) -> Dict:
        """更新PI单库存状态（用于缺货标记）"""
        data = {"storage_status": storage_status}
        return self.patch(f"/pi/{pi_id}/storage-status", data)

    # 注意：get_pi_detail 方法在下方 line 707 重新定义（使用 /pi/detail/{pi_id} 正确路径）
    # 错误版本（/pi/{pi_id} 不返回items）已删除
    # 2026-06-22 修复：原 line 442 的错误实现导致保存后刷新拿不到items

    def get_pi_items(self, pi_id: int) -> List[Dict]:
        """获取PI单的所有产品项"""
        # 🔧 2026-06-22 修复：原代码使用 /pi/{pi_id}，但该路由不返回items
        # 改用 /pi/detail/{pi_id} 正确获取items
        detail = self.get(f"/pi/detail/{pi_id}")
        return detail.get('items', []) if detail else []
    
    def batch_delete_pi(self, pi_ids: List[int]) -> Dict:
        return self.post("/pi/batch-delete", pi_ids)

    # 2026-06-10 新增：PI订单项操作
    def get_pi_item(self, item_id: int) -> Dict:
        """获取PI订单项详情"""
        return self.get(f"/pi/items/{item_id}")

    def update_pi_item(self, item_id: int, data: Dict) -> Dict:
        """更新PI订单项（用于临时产品转正）"""
        return self.put(f"/pi/items/{item_id}", data)

    # 2026-06-12 需求#40：软删除 / 入库 API
    def delete_pi_item(self, item_id: int) -> Dict:
        """软删除 PI 单品"""
        return self.delete(f"/pi/items/{item_id}")

    def inbound_pi_item(self, item_id: int, quantity: float, inspector: str = None, remark: str = None) -> Dict:
        """单品入库"""
        import logging
        logging.getLogger(__name__).info(
            f"[📡CLIENT] POST /pi/items/{item_id}/inbound  payload: quantity={quantity}, inspector={inspector!r}, remark={remark!r}")
        result = self.post(f"/pi/items/{item_id}/inbound", {
            "quantity": quantity,
            "inspector": inspector or "",
            "remark": remark or "",
        })
        logging.getLogger(__name__).info(f"[📡CLIENT] ✅ response: {result}")
        return result

    def inbound_pi_items_batch(self, pi_id: int, items: list, inspector: str = None) -> Dict:
        """批量入库"""
        import logging
        logging.getLogger(__name__).info(
            f"[📡CLIENT] POST /pi/{pi_id}/inbound-batch  items_count={len(items)}, inspector={inspector!r}, items={items}")
        result = self.post(f"/pi/{pi_id}/inbound-batch", {
            "items": items,
            "inspector": inspector or "",
        })
        logging.getLogger(__name__).info(f"[📡CLIENT] ✅ response: {result}")
        return result

    # 2026-06-12 需求#42：历史记录 + 正式纪录 API
    def get_pi_versions(self, pi_id: int) -> List[Dict]:
        """获取 PI 所有历史版本"""
        return self.get(f"/pi/{pi_id}/versions")

    def save_pi_snapshot(self, pi_id: int, change_desc: str, version_no: int) -> Dict:
        """保存新快照（乐观锁）"""
        return self.post(f"/pi/{pi_id}/versions", {"change_desc": change_desc, "version_no": version_no})

    def save_formal_record(self, pi_id: int) -> Dict:
        """保存正式纪录（JSON 文件）"""
        return self.post(f"/pi/{pi_id}/formal-record", {})

    def get_formal_record(self, pi_id: int) -> Dict:
        """读取正式纪录"""
        return self.get(f"/pi/{pi_id}/formal-record")

    def formal_record_exists(self, pi_id: int) -> bool:
        """检查正式纪录是否存在"""
        return self.get(f"/pi/{pi_id}/formal-record/exists").get("exists", False)

    def get_purchase_orders(self) -> List[Dict]:
        return self.get("/purchase-orders")

    def create_purchase(self, data: Dict) -> Dict:
        return self.post("/purchase-orders", data)

    def get_product_latest_purchase(self, product_id: int) -> Dict:
        """获取产品最近一次采购记录（包含费用和发票信息）"""
        return self.get(f"/purchase-orders/product/{product_id}/latest")

    def get_product_latest_purchase_async(
        self,
        product_id: int,
        on_success: Optional[Callable[[Dict], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """2026-06-09 任务 15：异步获取产品最近一次采购记录
        - 在子线程执行 HTTP 请求
        - 回调通过 QTimer.singleShot(0, ...) 回到 Qt 主线程
        - 任一回调为 None 时静默忽略（用于无 UI 上下文场景）
        """
        def _worker():
            try:
                resp = self.get(f"/purchase-orders/product/{product_id}/latest")
            except Exception as exc:
                self._dispatch_to_main(on_error, exc)
                return
            self._dispatch_to_main(on_success, resp)

        Thread(target=_worker, daemon=True).start()

    def _dispatch_to_main(self, callback: Optional[Callable], payload):
        """把回调 marshal 回 Qt 主线程；无 PySide6 或无回调时降级同步调用"""
        if callback is None:
            return
        try:
            from PySide6.QtCore import QTimer  # 局部导入，避免非 Qt 上下文失败
        except Exception:
            callback(payload)
            return
        QTimer.singleShot(0, lambda: callback(payload))

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
        return self.get("/inventory/", params=params)

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
        return self.post("/shipments/", data)

    def update_shipment(self, shipment_id: int, data: Dict) -> Dict:
        return self.put(f"/shipments/{shipment_id}", data)

    def get_purchases_by_supplier(self, supplier_id: int) -> List[Dict]:
        return self.get(f"/purchase-orders/by-supplier/{supplier_id}")

    def get_recent_1688_urls(self, product_id: int, limit: int = 5) -> List[str]:
        """
        获取指定产品最近的 1688 采购链接列表（去重，过滤空值）

        Args:
            product_id: 产品 ID
            limit: 最多取多少条

        Returns:
            URL 字符串列表（按 created_at 倒序，重复 URL 保留首次出现的顺序）
        """
        records = self.get("/purchase/1688", params={"product_id": product_id, "limit": limit})
        urls = []
        seen = set()
        for r in records or []:
            url = (r.get("product_url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def create_inventory(self, data: Dict) -> Dict:
        return self.post("/inventory", data)

    def update_inventory(self, inventory_id: int, data: Dict) -> Dict:
        return self.put(f"/inventory/{inventory_id}", data)
    
    def delete_inventory(self, inventory_id: int) -> Dict:
        return self.delete(f"/inventory/{inventory_id}")
    
    def get_product_inventory(self, product_id: int) -> Dict:
        """获取单个产品的库存信息"""
        inventories = self.get("/inventory/", params={"product_id": product_id})
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
        """导出PI为Excel文件（使用WEINA专业模板）"""
        url = self._build_url(f"/export/pi/{pi_id}")  # 使用模板导出API
        response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content

    def export_ci_excel(self, shipment_id: int) -> bytes:
        """导出CI商业发票为Excel文件"""
        url = self._build_url(f"/export/shipment/{shipment_id}/ci")
        response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content

    def export_pl_excel(self, shipment_id: int) -> bytes:
        """导出PL装箱单为Excel文件"""
        url = self._build_url(f"/export/shipment/{shipment_id}/pl")
        response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content

    def export_contract_excel(self, po_id: int) -> bytes:
        """导出国内采购合同为Excel文件"""
        url = self._build_url(f"/export/purchase/{po_id}/contract")
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

    def get_customer_replies_list(self, pi_id: int) -> Optional[Dict]:
        """获取排序后的回复列表（含序号标签）"""
        return self.get(f"/customer-replies/pi/{pi_id}/list")

    def export_customer_replies(
        self,
        pi_id: int,
        customer_name: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        selected_ids: Optional[List[int]] = None
    ) -> bytes:
        """导出回复记录 Excel"""
        data = {
            "pi_id": pi_id,
            "customer_name": customer_name,
        }
        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date
        if selected_ids:
            data["selected_ids"] = selected_ids

        resp = self.post_raw("/customer-replies/export", data)
        return resp.content if hasattr(resp, 'content') else b""

    def batch_get_replies(self, items: list) -> dict:
        """批量获取多商品回复记录"""
        return self.post("/customer-replies/batch-by-items", json={"items": items})

    def export_batch_replies(self, items: list, selected_ids: list = None) -> bytes:
        """批量导出多商品回复记录为 Excel"""
        params = {}
        if selected_ids:
            params["selected_ids"] = [str(sid) for sid in selected_ids]

        resp = self.session.post(
            f"{self.base_url}/customer-replies/export-batch",
            json={"items": items},
            params=params
        )
        resp.raise_for_status()
        return resp.content

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

    def get_product_categories(self) -> List[Dict]:
        """获取产品类目列表"""
        return self.get("/product-categories/") or []

    # ========== 备忘录 ==========

    def get_memos(self, entity_type: str, entity_id: int, field_name: str = None) -> List[Dict]:
        """获取备忘录列表"""
        params = {"entity_type": entity_type, "entity_id": entity_id}
        if field_name:
            params["field_name"] = field_name
        return self.get("/memos", params=params) or []

    def create_memo(self, data: Dict) -> Dict:
        """创建备忘录"""
        return self.post("/memos", data)

    def update_memo(self, memo_id: int, data: Dict) -> Dict:
        """更新备忘录"""
        return self.put(f"/memos/{memo_id}", data)

    def delete_memo(self, memo_id: int) -> Dict:
        """删除备忘录"""
        return self.delete(f"/memos/{memo_id}")

    # ========== 订单文件 ==========

    def get_order_files(self, pi_id: int, file_type: str = None) -> List[Dict]:
        """获取订单文件列表"""
        params = {}
        if file_type:
            params["file_type"] = file_type
        return self.get(f"/order-files/{pi_id}", params=params) or []

    def upload_order_file(self, pi_id: int, file_type: str, file_path: str) -> Dict:
        """上传订单文件"""
        with open(file_path, 'rb') as f:
            return self.upload(f"/order-files/upload/{pi_id}?file_type={file_type}", f)

    def download_order_file(self, file_id: int, save_path: str):
        """下载订单文件"""
        url = self._build_url(f"/order-files/download/{file_id}")
        response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)

    def delete_order_file(self, file_id: int) -> Dict:
        """删除订单文件"""
        return self.delete(f"/order-files/{file_id}")

    # ========== 采购发票上传 ==========
    def upload_purchase_invoice(self, file_path: str, purchase_id: int) -> Dict:
        """上传采购发票文件
        Args:
            file_path: 本地文件路径
            purchase_id: 采购单ID
        Returns:
            上传结果字典
        """
        with open(file_path, 'rb') as f:
            return self.upload(f"/purchase-orders/{purchase_id}/invoice", f)

    # ========== 付款查询 ==========

    def get_customer_payments_by_pi(self, pi_id: int) -> List[Dict]:
        """按 PI 获取客户付款记录"""
        return self.get(f"/payments/receivables/by-pi/{pi_id}") or []

    def get_supplier_payments_by_pi(self, pi_id: int) -> List[Dict]:
        """按 PI 获取供应商付款记录"""
        return self.get(f"/payments/payables/by-pi/{pi_id}") or []

    # ========== 采购包装规格 ==========

    def get_purchase_item_package(self, po_item_id: int) -> Optional[Dict]:
        """获取采购明细项的包装规格
        
        Raises:
            PackageNotFoundError: 包装规格不存在（404）
            PackageNetworkError: 网络连接失败或请求超时
        """
        try:
            response = self.session.get(
                self._build_url(f"/purchase-items/{po_item_id}/package"),
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 404:
                raise PackageNotFoundError(f"包装规格不存在: po_item_id={po_item_id}")
            response.raise_for_status()
            return response.json()
        except RequestsConnectionError as e:
            raise PackageNetworkError(f"网络连接失败: {e}")
        except RequestsTimeout as e:
            raise PackageNetworkError(f"请求超时: {e}")
        except Exception as e:
            self._logger.error(f"获取包装规格失败: {e}")
            return None

    def save_purchase_item_package(self, po_item_id: int, package_data: Dict) -> Optional[Dict]:
        """保存采购明细项的包装规格（创建或更新）
        
        Raises:
            PackageNetworkError: 网络连接失败或请求超时
        """
        try:
            data = {**package_data, "po_item_id": po_item_id}
            response = self.session.post(
                self._build_url(f"/purchase-items/{po_item_id}/package"),
                json=data,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except RequestsConnectionError as e:
            raise PackageNetworkError(f"网络连接失败: {e}")
        except RequestsTimeout as e:
            raise PackageNetworkError(f"请求超时: {e}")
        except Exception as e:
            self._logger.error(f"保存包装规格失败: {e}")
            return None

    def delete_purchase_item_package(self, po_item_id: int) -> bool:
        """删除采购明细项的包装规格
        
        Raises:
            PackageNotFoundError: 包装规格不存在（404）
            PackageNetworkError: 网络连接失败或请求超时
        """
        try:
            response = self.session.delete(
                self._build_url(f"/purchase-items/{po_item_id}/package"),
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 404:
                raise PackageNotFoundError(f"包装规格不存在: po_item_id={po_item_id}")
            response.raise_for_status()
            return True
        except RequestsConnectionError as e:
            raise PackageNetworkError(f"网络连接失败: {e}")
        except RequestsTimeout as e:
            raise PackageNetworkError(f"请求超时: {e}")
        except Exception as e:
            self._logger.error(f"删除包装规格失败: {e}")
            return False

    def get_history_package(self, customer_id: int, product_id: int) -> Optional[Dict]:
        """获取历史包装规格（智能回填接口）
        
        根据客户+产品组合查询最近一次使用的包装规格，
        用于新订单的智能回填功能。
        
        Raises:
            PackageNetworkError: 网络连接失败或请求超时
        """
        try:
            response = self.session.get(
                self._build_url("/purchase-items/history-package"),
                params={"customer_id": customer_id, "product_id": product_id},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except RequestsConnectionError as e:
            raise PackageNetworkError(f"网络连接失败: {e}")
        except RequestsTimeout as e:
            raise PackageNetworkError(f"请求超时: {e}")
        except Exception as e:
            self._logger.error(f"获取历史包装规格失败: {e}")
            return None
